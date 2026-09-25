# INV-21 Local Service Chaining v4.2.0
# Comprehensive Missing-Component Remediation Checklist

**Source:** post-hardening audit for INV-21 v4.2.0  
**Audit date:** 2026-09-23  
**Missing/incomplete components:** 42  

This checklist treats each gap as a production-exit work package. A gap is not closed merely because code exists: design/contract, implementation, hardening, negative/fault testing, operational visibility, traceability, and release evidence must all be complete. Mandatory checks that cannot execute are failures, not passes.

## Global production-exit gates

- [ ] All CRITICAL gaps are closed.
- [ ] All HIGH gaps are closed or covered by approved, explicitly time-bounded waivers with compensating controls.
- [ ] `pk_core` conformance executes with zero mandatory skips.
- [ ] C001-C100 each map to code/config/tests/evidence in a machine-readable traceability matrix.
- [ ] Identity, authorization, residency, deadline/cancellation, overload, error, and semantic-equivalence invariants pass negative/fault testing.
- [ ] SBOM, provenance, digests/signatures, vulnerability results, compatibility, integration, benchmark, and release-gate evidence refer to the exact release artifact.
- [ ] Independent post-remediation audit returns no reproducible CRITICAL/HIGH gap and the production-exit verifier returns GO.

## Recommended dependency sequence

1. GAP-001, 002: dependency/package foundation.
2. GAP-003, 040, 041: typed contracts, context, and errors.
3. GAP-005, 004: authenticated identity and authoritative authorization.
4. GAP-010, 006, 007, 008, 009, 011: residency, transport, async, deadline/retry/backpressure, admission, lifecycle.
5. GAP-012 through 016: configuration/governance/traceability/compatibility.
6. GAP-017 through 021, 027, 031, 034-036: supply-chain, audit/telemetry, security/operations.
7. GAP-022 through 026, 030, 032, 033: performance/capacity/correctness/recovery/rollout.
8. GAP-028, 029, 042, 038, 037, 039: integration/platform/parity/CI/evidence/licensing.

---


## GAP-001 — Framework dependency packaging

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C030, INV-21-C090, INV-21-C100  
**Observed gap:** `pk_core` is required by normal imports and conformance/gate execution but is not bundled or declared in a package/dependency manifest; the framework test suite therefore skips in this isolated archive.  
**Required completion:** Add pyproject.toml/lock or workspace manifest with a pinned pk_core source/version; make CI fail if pk_core conformance cannot execute.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Framework dependency packaging** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Framework dependency packaging** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Framework dependency packaging** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Pin `pk_core` to an immutable version/source in `pyproject.toml` or the workspace manifest; do not depend on an undeclared developer-local import path.
- [ ] Produce a lock/constraints file with hashes for `pk_core` and its transitives and verify integrity before test/release execution.
- [ ] Make the conformance job fail when `pk_core` cannot be imported or when its API/version is incompatible; a skip is not an acceptable release result.
- [ ] Run clean-environment install/import/conformance smoke tests from the built artifact, not only from the source tree.
- [ ] Document the supported `pk_core` range, upgrade procedure, trust source, and offline/internal-index behavior.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Framework dependency packaging** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Framework dependency packaging**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Framework dependency packaging**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Framework dependency packaging**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Framework dependency packaging** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Framework dependency packaging** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Framework dependency packaging** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Framework dependency packaging**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C030, INV-21-C090, INV-21-C100** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Framework dependency packaging**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Framework dependency packaging** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C030, INV-21-C090, INV-21-C100 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-001 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-002 — Python package/release metadata

**Severity:** HIGH  
**Mapped controls:** INV-21-C016, INV-21-C031, INV-21-C040, INV-21-C093  
**Observed gap:** No pyproject.toml/setup metadata, Python compatibility declaration, dependency constraints, build backend, wheel/sdist path, or reproducible environment lock.  
**Required completion:** Add PEP 517 metadata, supported Python range, pinned dependencies/hashes, reproducible build and install smoke tests.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Python package/release metadata** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Python package/release metadata** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Python package/release metadata** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Add PEP 517/518 metadata, build backend, supported Python range, runtime/dev/test dependency groups, license metadata, and a single authoritative version source.
- [ ] Build wheel and sdist artifacts and verify both install cleanly in isolated environments.
- [ ] Add dependency locking/hashes and ensure release builds resolve the exact same graph reproducibly.
- [ ] Validate package contents so caches, secrets, local virtual environments, scratch files, and audit-only artifacts are excluded.
- [ ] Add metadata/package validation and version-consistency checks to CI.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Python package/release metadata** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Python package/release metadata**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Python package/release metadata**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Python package/release metadata**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Python package/release metadata** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Python package/release metadata** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Python package/release metadata** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Python package/release metadata**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C016, INV-21-C031, INV-21-C040, INV-21-C093** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Python package/release metadata**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Python package/release metadata** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C016, INV-21-C031, INV-21-C040, INV-21-C093 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-002 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-003 — Versioned typed interface schemas

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C021, INV-21-C022, INV-21-C026, INV-21-C082  
**Observed gap:** PK_LOCAL_CHAIN/1, PK_RESIDENCY/1, and PK_CHAIN_DEPTH/1 are named in prose but have no machine-readable schema/WIT/IDL definitions or schema conformance tests.  
**Required completion:** Add versioned schema files for requests, responses, errors, residency records and depth context; test backward/forward compatibility.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Versioned typed interface schemas** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Versioned typed interface schemas** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Versioned typed interface schemas** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Create machine-readable versioned schemas for `PK_LOCAL_CHAIN/1`, `PK_RESIDENCY/1`, and `PK_CHAIN_DEPTH/1` using the repository-standard IDL/schema format.
- [ ] Specify request/response/error/context/residency/depth fields, requiredness, defaults, limits, normalization, and unknown-field rules.
- [ ] Assign stable enum/error identifiers and prohibit semantic reuse of retired identifiers.
- [ ] Add golden valid/invalid/future-field fixtures plus schema-diff checks that classify breaking changes.
- [ ] Run N/N-1 and documented N+1 compatibility tests against generated/runtime bindings.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Versioned typed interface schemas** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Versioned typed interface schemas**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Versioned typed interface schemas**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Versioned typed interface schemas**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Versioned typed interface schemas** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Versioned typed interface schemas** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Versioned typed interface schemas** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Versioned typed interface schemas**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C021, INV-21-C022, INV-21-C026, INV-21-C082** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Versioned typed interface schemas**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Versioned typed interface schemas** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C021, INV-21-C022, INV-21-C026, INV-21-C082 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-003 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-004 — Authoritative capability-provider integration

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C024, INV-21-C042, INV-21-C048  
**Observed gap:** 4.2 adds a per-hop capability hook, but no authoritative policy/capability provider is wired, versioned, or failover-tested. The compatibility fallback is not equivalent to external capability policy.  
**Required completion:** Define the capability decision contract, inject the system authority in production, specify fail-closed outage behavior, and add integration/security tests.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Authoritative capability-provider integration** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Authoritative capability-provider integration** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Authoritative capability-provider integration** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define a versioned capability-decision contract containing authenticated principal, tenant, caller, callee, operation/resource, requested capabilities, topology context, and a decision correlation ID.
- [ ] Wire the authoritative platform capability provider in production mode; do not treat the local compatibility hook as an authority.
- [ ] Define fail-closed behavior for provider timeout, outage, malformed response, stale policy, unknown decision, and version mismatch.
- [ ] If decision caching is allowed, bound TTL, key dimensions, revocation latency, negative caching, and invalidation behavior.
- [ ] Test denial, revocation, stale policy, provider compromise/failure simulations, tenant crossing, and privilege escalation paths.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Authoritative capability-provider integration** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Authoritative capability-provider integration**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Authoritative capability-provider integration**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Authoritative capability-provider integration**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Authoritative capability-provider integration** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Authoritative capability-provider integration** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Authoritative capability-provider integration** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Authoritative capability-provider integration**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C024, INV-21-C042, INV-21-C048** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Authoritative capability-provider integration**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Authoritative capability-provider integration** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C024, INV-21-C042, INV-21-C048 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-004 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-005 — Authentication and caller identity model

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C023, INV-21-C044, INV-21-C048  
**Observed gap:** Tenant and trace identifiers are caller-supplied strings; there is no authenticated principal, attestation, credential binding, or identity provenance on a local hop.  
**Required completion:** Introduce authenticated call context derived from trusted runtime identity, not request-controlled strings; define attestation/outage semantics.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Authentication and caller identity model** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Authentication and caller identity model** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Authentication and caller identity model** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define an immutable authenticated principal distinct from caller-supplied tenant/trace strings.
- [ ] Bind identity to trusted workload/process credentials or attestation and derive tenant membership from trusted authority.
- [ ] Define credential audience, expiry, freshness, rotation, revocation, delegation/on-behalf-of semantics, and clock-skew handling.
- [ ] Propagate identity provenance across local/remote hops without allowing downstream mutation or self-asserted privilege.
- [ ] Test spoofed tenant IDs, forged/expired credentials, confused-deputy flows, delegated identity, and credential rotation/outage.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Authentication and caller identity model** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Authentication and caller identity model**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Authentication and caller identity model**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Authentication and caller identity model**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Authentication and caller identity model** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Authentication and caller identity model** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Authentication and caller identity model** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Authentication and caller identity model**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C023, INV-21-C044, INV-21-C048** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Authentication and caller identity model**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Authentication and caller identity model** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C023, INV-21-C044, INV-21-C048 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-005 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-006 — Production remote-transport adapter

**Severity:** HIGH  
**Mapped controls:** INV-21-C018, INV-21-C021, INV-21-C030, INV-21-C055, INV-21-C056  
**Observed gap:** 4.2 can inject `remote_dispatch`, but no concrete adapter to the repository's network transport exists and default behavior still returns a compatibility sentinel tuple.  
**Required completion:** Implement/test the adjacent transport adapter, network-unavailable behavior, deadlines, error mapping, and semantic parity with local calls.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Production remote-transport adapter** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Production remote-transport adapter** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Production remote-transport adapter** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Implement the concrete repository network transport adapter and remove the production reliance on the compatibility sentinel tuple.
- [ ] Use the same versioned logical request/response contract for local and remote execution.
- [ ] Propagate identity, tenant, trace/span, deadline, idempotency, depth/path, and capability context across the transport boundary.
- [ ] Normalize connect/TLS/protocol/timeout/remote-application failures into stable INV-21 error categories with retry semantics.
- [ ] Enforce peer authentication, payload/resource bounds, cancellation, backpressure, dependency health, and local/remote parity tests.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Production remote-transport adapter** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Production remote-transport adapter**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Production remote-transport adapter**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Production remote-transport adapter**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Production remote-transport adapter** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Production remote-transport adapter** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Production remote-transport adapter** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Production remote-transport adapter**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C018, INV-21-C021, INV-21-C030, INV-21-C055, INV-21-C056** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Production remote-transport adapter**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Production remote-transport adapter** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C018, INV-21-C021, INV-21-C030, INV-21-C055, INV-21-C056 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-006 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-007 — Async/await chaining path

**Severity:** HIGH  
**Mapped controls:** INV-21-C011, INV-21-C021, INV-21-C025, INV-21-C030  
**Observed gap:** The contract depends on INV-16 Async component functions, but `Chainer.call()` and handlers are synchronous and do not await async handlers or remote dispatchers.  
**Required completion:** Add `call_async`/async handler support with cancellation and context propagation; define sync/async interop and tests.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Async/await chaining path** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Async/await chaining path** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Async/await chaining path** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Add an async call surface that awaits async local handlers and async remote dispatchers without blocking the event loop.
- [ ] Define sync/async interoperability and whether synchronous handlers execute inline, in a worker pool, or are rejected on async paths.
- [ ] Propagate cancellation and a monotonic remaining-deadline budget through policy, residency, handler, and remote operations.
- [ ] Keep depth/cycle/context state task-local and bound task creation/fan-out with async admission controls.
- [ ] Test nested async chains, mixed sync/async handlers, cancellation races, timeouts, remote fallback, and high concurrency.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Async/await chaining path** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Async/await chaining path**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Async/await chaining path**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Async/await chaining path**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Async/await chaining path** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Async/await chaining path** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Async/await chaining path** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Async/await chaining path**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C011, INV-21-C021, INV-21-C025, INV-21-C030** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Async/await chaining path**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Async/await chaining path** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C011, INV-21-C021, INV-21-C025, INV-21-C030 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-007 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-008 — Deadlines, cancellation, retry, idempotency and backpressure

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C025, INV-21-C053, INV-21-C054, INV-21-C067  
**Observed gap:** No deadline/cancellation token, bounded retry policy, idempotency key semantics, queue/backpressure mechanism, or retry safety classification exists.  
**Required completion:** Define hop deadline/cancellation propagation, idempotency metadata, retry policy with backoff/jitter, and bounded queues/admission.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Deadlines, cancellation, retry, idempotency and backpressure** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Deadlines, cancellation, retry, idempotency and backpressure** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Deadlines, cancellation, retry, idempotency and backpressure** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Add monotonic deadlines and explicit cancellation signals to the call context and propagate remaining budget at every hop.
- [ ] Classify operations as non-retriable, retry-safe, or idempotent; require explicit metadata before automated retry.
- [ ] Implement bounded retry attempts/total budget with exponential backoff, jitter, and stable retryable error classes.
- [ ] Add idempotency keys plus bounded deduplication semantics and bounded queues/semaphores for local and remote execution.
- [ ] Test deadline exhaustion, cancellation during each phase, replay/duplicate requests, retry storms, overload, and recovery.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Deadlines, cancellation, retry, idempotency and backpressure** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Deadlines, cancellation, retry, idempotency and backpressure**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Deadlines, cancellation, retry, idempotency and backpressure**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Deadlines, cancellation, retry, idempotency and backpressure**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Deadlines, cancellation, retry, idempotency and backpressure** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Deadlines, cancellation, retry, idempotency and backpressure** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Deadlines, cancellation, retry, idempotency and backpressure** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Deadlines, cancellation, retry, idempotency and backpressure**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C025, INV-21-C053, INV-21-C054, INV-21-C067** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Deadlines, cancellation, retry, idempotency and backpressure**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Deadlines, cancellation, retry, idempotency and backpressure** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C025, INV-21-C053, INV-21-C054, INV-21-C067 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-008 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-009 — Admission control and circuit breaking

**Severity:** HIGH  
**Mapped controls:** INV-21-C017, INV-21-C054, INV-21-C067, INV-21-C069  
**Observed gap:** Depth and telemetry are bounded, but concurrent calls, per-tenant quotas, fan-out, handler saturation and remote failures have no admission/load-shedding/circuit-breaker controls.  
**Required completion:** Add configurable concurrency/tenant limits, saturation signals, load shedding and circuit breaker state with deterministic tests.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Admission control and circuit breaking** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Admission control and circuit breaking** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Admission control and circuit breaking** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define global, per-tenant, per-callee, and optional per-operation concurrency/queue budgets plus fairness/priority rules.
- [ ] Perform admission checks before expensive work and return a stable overload response rather than unbounded queuing.
- [ ] Implement closed/open/half-open circuit breakers for remote/dependent services with deterministic probe/reset behavior.
- [ ] Expose active work, queue depth, rejected calls, saturation ratio, fairness, and circuit state telemetry.
- [ ] Test burst/sustained overload, noisy-neighbor tenants, circuit trip/recovery, half-open races, and remote outage behavior.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Admission control and circuit breaking** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Admission control and circuit breaking**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Admission control and circuit breaking**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Admission control and circuit breaking**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Admission control and circuit breaking** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Admission control and circuit breaking** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Admission control and circuit breaking** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Admission control and circuit breaking**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C017, INV-21-C054, INV-21-C067, INV-21-C069** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Admission control and circuit breaking**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Admission control and circuit breaking** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C017, INV-21-C054, INV-21-C067, INV-21-C069 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-009 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-010 — Residency freshness/lease/watch protocol

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C004, INV-21-C037, INV-21-C051, INV-21-C058  
**Observed gap:** Residency is authoritative but has no TTL/lease, epoch/source provenance, watcher synchronization, stale-entry detection, duplicate-owner arbitration, or reconciliation protocol.  
**Required completion:** Add generation/lease metadata, atomic snapshots, stale detection, ownership rules and reconciliation tests against the placement/control plane.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Residency freshness/lease/watch protocol** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Residency freshness/lease/watch protocol** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Residency freshness/lease/watch protocol** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Extend residency records with authoritative source/owner, generation/epoch, revision, lease/TTL semantics, and observation timestamp.
- [ ] Define conflict resolution for duplicate owners, out-of-order events, stale snapshots, and concurrent updates.
- [ ] Implement atomic snapshot installation, monotonic revision checks, watcher/subscription synchronization, and periodic reconciliation.
- [ ] Define stale-entry behavior (fail closed, re-resolve, or remote route) and make it observable and deterministic.
- [ ] Test lease expiry, ABA/reuse, delayed/reordered events, duplicate placements, partition/reconnect, and concurrent place/unplace.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Residency freshness/lease/watch protocol** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Residency freshness/lease/watch protocol**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Residency freshness/lease/watch protocol**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Residency freshness/lease/watch protocol**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Residency freshness/lease/watch protocol** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Residency freshness/lease/watch protocol** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Residency freshness/lease/watch protocol** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Residency freshness/lease/watch protocol**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C004, INV-21-C037, INV-21-C051, INV-21-C058** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Residency freshness/lease/watch protocol**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Residency freshness/lease/watch protocol** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C004, INV-21-C037, INV-21-C051, INV-21-C058 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-010 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-011 — Lifecycle and state-transition model

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C014, INV-21-C015, INV-21-C057  
**Observed gap:** No explicit initializing/ready/degraded/quarantined/stopped lifecycle or legal transition table exists for the chainer/residency state.  
**Required completion:** Define states, transition guards, restart/recovery semantics and machine-verifiable transition tests.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Lifecycle and state-transition model** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Lifecycle and state-transition model** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Lifecycle and state-transition model** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define `INITIALIZING`, `READY`, `DEGRADED`, `QUARANTINED`, `DRAINING`, and `STOPPED` (or equivalent) states.
- [ ] Publish legal transitions with triggers, guards, side effects, observability, and forbidden transitions.
- [ ] Define request-admission policy and remote-fallback allowance for every lifecycle state.
- [ ] Define startup dependency sequencing, graceful drain, shutdown timeout, restart/recovery, and readiness criteria.
- [ ] Add state-machine, illegal-transition, degradation/recovery, restart, and shutdown-race tests.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Lifecycle and state-transition model** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Lifecycle and state-transition model**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Lifecycle and state-transition model**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Lifecycle and state-transition model**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Lifecycle and state-transition model** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Lifecycle and state-transition model** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Lifecycle and state-transition model** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Lifecycle and state-transition model**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C014, INV-21-C015, INV-21-C057** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Lifecycle and state-transition model**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Lifecycle and state-transition model** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C014, INV-21-C015, INV-21-C057 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-011 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-012 — Declarative configuration schema

**Severity:** HIGH  
**Mapped controls:** INV-21-C033, INV-21-C034, INV-21-C035  
**Observed gap:** Runtime knobs exist only as constructor arguments; there is no declarative config schema for depth, telemetry, policy provider, transport, quotas, or site/environment overrides.  
**Required completion:** Add versioned config schema with secure defaults, validation, environment overlays and activation tests.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Declarative configuration schema** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Declarative configuration schema** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Declarative configuration schema** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Create a versioned declarative configuration schema for depth, telemetry, policy provider, transport, quotas, retries, breakers, residency, and security modes.
- [ ] Define secure production defaults and deterministic environment/site overlay precedence.
- [ ] Validate type/range/relationship/conditional constraints before activation and keep secrets out of ordinary config.
- [ ] Provide an offline config validator/linter and explicit schema migration/deprecation behavior.
- [ ] Test positive/negative fixtures, boundary values, overlays, unknown fields, and secure-default regressions.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Declarative configuration schema** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Declarative configuration schema**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Declarative configuration schema**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Declarative configuration schema**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Declarative configuration schema** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Declarative configuration schema** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Declarative configuration schema** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Declarative configuration schema**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C033, INV-21-C034, INV-21-C035** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Declarative configuration schema**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Declarative configuration schema** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C033, INV-21-C034, INV-21-C035 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-012 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-013 — Configuration provenance and atomic activation

**Severity:** HIGH  
**Mapped controls:** INV-21-C036, INV-21-C037, INV-21-C038  
**Observed gap:** No author/source/version/activation timestamp is recorded for configuration, and there is no transactional config activation or rollback snapshot.  
**Required completion:** Add immutable config revisions, provenance, validate-before-swap activation and previous-revision rollback.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Configuration provenance and atomic activation** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Configuration provenance and atomic activation** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Configuration provenance and atomic activation** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Give every configuration revision a stable ID, schema version, source/author, creation/activation timestamps, and content digest.
- [ ] Make active config immutable and implement validate-before-swap atomic activation.
- [ ] Define whether in-flight calls finish under the old revision or adopt the new one; never mix a partial revision.
- [ ] Retain a previous known-good revision and provide deterministic rollback with audit events.
- [ ] Test invalid activation, concurrent updates, crash during activation, secret-reference failure, and rollback.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Configuration provenance and atomic activation** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Configuration provenance and atomic activation**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Configuration provenance and atomic activation**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Configuration provenance and atomic activation**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Configuration provenance and atomic activation** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Configuration provenance and atomic activation** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Configuration provenance and atomic activation** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Configuration provenance and atomic activation**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C036, INV-21-C037, INV-21-C038** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Configuration provenance and atomic activation**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Configuration provenance and atomic activation** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C036, INV-21-C037, INV-21-C038 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-013 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-014 — Ownership, escalation and ADR artifacts

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C009, INV-21-C010, INV-21-C097  
**Observed gap:** No CODEOWNERS/owner record, escalation path, architecture decision record, or incident contact metadata is present.  
**Required completion:** Add OWNER/CODEOWNERS, ADR for direct composition/local fallback policy, and escalation/runbook ownership.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Ownership, escalation and ADR artifacts** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Ownership, escalation and ADR artifacts** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Ownership, escalation and ADR artifacts** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Add `CODEOWNERS`/owner metadata for runtime, schemas, security policy, CI, release evidence, and runbooks.
- [ ] Publish accountable owner, backup owner, security/operations contacts, escalation route, and dependent-system contacts.
- [ ] Create an ADR for direct local composition versus remote fallback and its invariant/security assumptions.
- [ ] Create/record ADRs for capability authority, residency authority, identity context, overload/failure strategy, and other material choices.
- [ ] Require ownership/architecture review when protected architecture/security files change.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Ownership, escalation and ADR artifacts** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Ownership, escalation and ADR artifacts**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Ownership, escalation and ADR artifacts**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Ownership, escalation and ADR artifacts**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Ownership, escalation and ADR artifacts** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Ownership, escalation and ADR artifacts** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Ownership, escalation and ADR artifacts** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Ownership, escalation and ADR artifacts**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C009, INV-21-C010, INV-21-C097** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Ownership, escalation and ADR artifacts**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Ownership, escalation and ADR artifacts** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C009, INV-21-C010, INV-21-C097 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-014 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-015 — Requirements traceability matrix

**Severity:** HIGH  
**Mapped controls:** INV-21-C020, INV-21-C090, INV-21-C100  
**Observed gap:** The 100-item checklist and master prompts exist, but there is no persisted matrix mapping each item to code/config/test/evidence and release acceptance status.  
**Required completion:** Add machine-readable traceability matrix with evidence paths/hashes and gate status per C001-C100.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Requirements traceability matrix** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Requirements traceability matrix** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Requirements traceability matrix** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Create a machine-readable matrix covering every INV-21-C001 through C100 requirement.
- [ ] Map each requirement to implementation paths, configuration, test IDs, evidence artifacts, current status, and owner.
- [ ] Require reason/owner/expiry for `waived` or `not_applicable` states and validate against expired/missing waivers.
- [ ] Attach evidence hashes/CI artifact IDs and generate the human-readable summary from the same canonical data.
- [ ] Fail production exit when a mandatory requirement is blocked, unverified, or supported only by a skipped test.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Requirements traceability matrix** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Requirements traceability matrix**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Requirements traceability matrix**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Requirements traceability matrix**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Requirements traceability matrix** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Requirements traceability matrix** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Requirements traceability matrix** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Requirements traceability matrix**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C020, INV-21-C090, INV-21-C100** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Requirements traceability matrix**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Requirements traceability matrix** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C020, INV-21-C090, INV-21-C100 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-015 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-016 — Supported-version compatibility matrix

**Severity:** HIGH  
**Mapped controls:** INV-21-C016, INV-21-C027, INV-21-C093  
**Observed gap:** No matrix states supported local-chain schema versions, pk_core version, Python versions, adjacent component versions or downgrade behavior.  
**Required completion:** Add compatibility matrix and automated N/N-1 (and documented N+1 where relevant) tests.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Supported-version compatibility matrix** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Supported-version compatibility matrix** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Supported-version compatibility matrix** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Declare supported Python, OS, architecture, `pk_core`, adjacent-component, protocol, and schema versions.
- [ ] Define N/N-1 rolling upgrade, downgrade, unknown-future-field, and unsupported-peer behavior.
- [ ] Add automated supported-combination tests and negative tests that fail early on unsupported combinations.
- [ ] Document migration ordering and known incompatibilities/deprecation dates.
- [ ] Publish/validate the matrix with each release and ensure fixtures/package metadata match it.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Supported-version compatibility matrix** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Supported-version compatibility matrix**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Supported-version compatibility matrix**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Supported-version compatibility matrix**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Supported-version compatibility matrix** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Supported-version compatibility matrix** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Supported-version compatibility matrix** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Supported-version compatibility matrix**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C016, INV-21-C027, INV-21-C093** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Supported-version compatibility matrix**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Supported-version compatibility matrix** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C016, INV-21-C027, INV-21-C093 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-016 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-017 — Artifact provenance, SBOM and signature verification

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C045, INV-21-C094  
**Observed gap:** No SBOM, dependency hashes, provenance attestation, signed release manifest, artifact digest verification, or vulnerability scan policy exists.  
**Required completion:** Generate SBOM/provenance, pin hashes, sign release artifacts, verify on bootstrap, and define vulnerability response SLAs.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Artifact provenance, SBOM and signature verification** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Artifact provenance, SBOM and signature verification** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Artifact provenance, SBOM and signature verification** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Generate an SBOM for every release artifact with dependencies, sources, licenses, and cryptographic hashes.
- [ ] Produce build provenance identifying source revision, workflow/builder identity, toolchain, inputs, and artifact digests.
- [ ] Sign release manifests/artifacts using the approved mechanism and document key custody/rotation/revocation.
- [ ] Verify dependency/artifact digests before installation and run vulnerability scanning with release-block thresholds.
- [ ] Test tampered artifacts/lockfiles, revoked keys, missing SBOM/provenance, and scanner failure behavior.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Artifact provenance, SBOM and signature verification** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Artifact provenance, SBOM and signature verification**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Artifact provenance, SBOM and signature verification**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Artifact provenance, SBOM and signature verification**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Artifact provenance, SBOM and signature verification** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Artifact provenance, SBOM and signature verification** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Artifact provenance, SBOM and signature verification** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Artifact provenance, SBOM and signature verification**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C045, INV-21-C094** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Artifact provenance, SBOM and signature verification**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Artifact provenance, SBOM and signature verification** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C045, INV-21-C094 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-017 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-018 — Tamper-evident security audit stream

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C049, INV-21-C073, INV-21-C078  
**Observed gap:** `DecisionEvent` is bounded in-process telemetry only; it is mutable runtime state, not a tamper-evident durable audit trail correlated with release/infrastructure lineage.  
**Required completion:** Export security-sensitive decisions to an append-only signed/chained audit sink with stable IDs and release/topology correlation.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Tamper-evident security audit stream** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Tamper-evident security audit stream** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Tamper-evident security audit stream** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define auditable security events including authorization/identity failures, cross-tenant attempts, config/residency changes, quarantine/emergency actions, and release/config revisions.
- [ ] Create an append-only event schema with stable event/sequence IDs, principal/tenant/action/outcome/reason, policy/config/release revision, and topology context.
- [ ] Export out-of-process to a durable audit sink and add tamper evidence using signatures/hash chains/WORM or platform standard.
- [ ] Define buffering/backpressure/failure semantics and privacy/redaction/retention/access-control rules.
- [ ] Test sink outage, buffer exhaustion, dropped/reordered events, tamper detection, clock anomalies, and lineage correlation.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Tamper-evident security audit stream** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Tamper-evident security audit stream**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Tamper-evident security audit stream**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Tamper-evident security audit stream**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Tamper-evident security audit stream** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Tamper-evident security audit stream** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Tamper-evident security audit stream** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Tamper-evident security audit stream**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C049, INV-21-C073, INV-21-C078** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Tamper-evident security audit stream**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Tamper-evident security audit stream** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C049, INV-21-C073, INV-21-C078 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-018 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-019 — Telemetry export, health/readiness and dependency status

**Severity:** HIGH  
**Mapped controls:** INV-21-C071, INV-21-C072, INV-21-C073  
**Observed gap:** Counters and decision records are in-memory only; there is no health/readiness surface, metrics exporter, structured log sink, dependency status, active capability report, or resource telemetry.  
**Required completion:** Add health/readiness snapshot and OpenTelemetry/metrics/log adapters with stable labels and bounded cardinality.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Telemetry export, health/readiness and dependency status** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Telemetry export, health/readiness and dependency status** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Telemetry export, health/readiness and dependency status** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Separate liveness from readiness and include mandatory dependency state in readiness decisions.
- [ ] Expose structured dependency status, last success/error, active versions/revisions, and degradation state without secrets.
- [ ] Export bounded-cardinality metrics for throughput, local/remote decisions, latency, refusals, in-flight/queue, circuit, residency, and resources.
- [ ] Integrate structured logs/OpenTelemetry with trace correlation and exporter failure isolation.
- [ ] Test health transitions, metric correctness, cardinality limits, exporter failure, and dependency degradation.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Telemetry export, health/readiness and dependency status** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Telemetry export, health/readiness and dependency status**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Telemetry export, health/readiness and dependency status**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Telemetry export, health/readiness and dependency status**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Telemetry export, health/readiness and dependency status** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Telemetry export, health/readiness and dependency status** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Telemetry export, health/readiness and dependency status** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Telemetry export, health/readiness and dependency status**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C071, INV-21-C072, INV-21-C073** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Telemetry export, health/readiness and dependency status**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Telemetry export, health/readiness and dependency status** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C071, INV-21-C072, INV-21-C073 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-019 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-020 — Telemetry privacy, retention, sampling and explain view

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C075, INV-21-C076, INV-21-C077, INV-21-C079  
**Observed gap:** Decision reasons are recorded, but no privacy/redaction policy, retention/sampling/export rules, or operator-facing explain view exists.  
**Required completion:** Define redaction/cardinality policy, retention/sampling configuration, and an explain API/view linking decisions to policy/topology inputs.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Telemetry privacy, retention, sampling and explain view** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Telemetry privacy, retention, sampling and explain view** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Telemetry privacy, retention, sampling and explain view** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Classify every telemetry/audit field by sensitivity, cardinality risk, operational value, and allowed destination.
- [ ] Define redaction/tokenization, sampling, retention, and deletion rules; preserve errors/security events while limiting normal volume.
- [ ] Enforce cardinality/size limits for attacker-controlled labels and metadata.
- [ ] Create an authorization-filtered explain API/view correlating decisions to policy/config/residency/topology inputs.
- [ ] Test redaction, sampling, retention, oversized labels, explain authorization, and trace/decision correlation.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Telemetry privacy, retention, sampling and explain view** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Telemetry privacy, retention, sampling and explain view**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Telemetry privacy, retention, sampling and explain view**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Telemetry privacy, retention, sampling and explain view**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Telemetry privacy, retention, sampling and explain view** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Telemetry privacy, retention, sampling and explain view** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Telemetry privacy, retention, sampling and explain view** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Telemetry privacy, retention, sampling and explain view**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C075, INV-21-C076, INV-21-C077, INV-21-C079** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Telemetry privacy, retention, sampling and explain view**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Telemetry privacy, retention, sampling and explain view** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C075, INV-21-C076, INV-21-C077, INV-21-C079 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-020 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-021 — Dashboards and alerting

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C080  
**Observed gap:** No dashboards, SLO alerts, policy-rejection alerts, saturation alerts, dependency-failure alerts, or attack/defect discrimination rules are included.  
**Required completion:** Add dashboard/alert definitions with tested thresholds and runbook links.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Dashboards and alerting** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Dashboards and alerting** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Dashboards and alerting** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Create service dashboards for throughput, local/remote ratio, success/error/refusal rate, p50/p95/p99, in-flight/queue, and residency freshness.
- [ ] Add dependency panels for capability authority, residency source, transport, audit sink, and telemetry exporters.
- [ ] Define SLO/error-budget, saturation, dependency, and security alert rules using sustained windows and tested thresholds.
- [ ] Differentiate likely attack signals from ordinary dependency faults and include triage guidance.
- [ ] Link actionable alerts to runbooks/owners and test firing/clearing behavior against synthetic metric fixtures.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Dashboards and alerting** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Dashboards and alerting**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Dashboards and alerting**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Dashboards and alerting**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Dashboards and alerting** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Dashboards and alerting** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Dashboards and alerting** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Dashboards and alerting**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C080** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Dashboards and alerting**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Dashboards and alerting** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C080 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-021 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-022 — Reproducible benchmark suite and performance evidence

**Severity:** HIGH  
**Mapped controls:** INV-21-C061, INV-21-C062, INV-21-C063, INV-21-C064, INV-21-C068, INV-21-C070  
**Observed gap:** The README states a p99 <20us SLO, but there are no benchmark harnesses, baseline artifacts, percentile distributions, overload/recovery runs, tenant overhead, power/thermal measurements, or regression gate.  
**Required completion:** Add reproducible micro/macro benchmarks, p50/p95/p99/worst thresholds, edge power runs, and CI regression gates.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Reproducible benchmark suite and performance evidence** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Reproducible benchmark suite and performance evidence** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Reproducible benchmark suite and performance evidence** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Build a reproducible benchmark harness with pinned tooling, environment fingerprint, warm-up policy, CPU/runtime controls, and raw sample retention.
- [ ] Measure local and equivalent remote paths over representative payloads/depths and report p50/p95/p99/max plus variability.
- [ ] Measure policy/residency/telemetry/serialization overhead, allocation/copy/context-switch behavior, and concurrency scaling.
- [ ] Run overload/recovery, tenant-overhead, and target edge power/thermal tests where those claims apply.
- [ ] Define statistically defensible regression thresholds for the claimed p99 SLO and archive results with release evidence.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Reproducible benchmark suite and performance evidence** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Reproducible benchmark suite and performance evidence**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Reproducible benchmark suite and performance evidence**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Reproducible benchmark suite and performance evidence**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Reproducible benchmark suite and performance evidence** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Reproducible benchmark suite and performance evidence** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Reproducible benchmark suite and performance evidence** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Reproducible benchmark suite and performance evidence**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C061, INV-21-C062, INV-21-C063, INV-21-C064, INV-21-C068, INV-21-C070** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Reproducible benchmark suite and performance evidence**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Reproducible benchmark suite and performance evidence** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C061, INV-21-C062, INV-21-C063, INV-21-C064, INV-21-C068, INV-21-C070 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-022 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-023 — Capacity model and saturation signals

**Severity:** HIGH  
**Mapped controls:** INV-21-C017, INV-21-C067, INV-21-C069  
**Observed gap:** No capacity formula/model covers concurrent chains, handler fan-out, per-tenant fairness, remote handoff pressure, CPU/memory limits, or saturation thresholds.  
**Required completion:** Document and implement capacity ceilings, fairness rules, saturation metrics and sizing tests.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Capacity model and saturation signals** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Capacity model and saturation signals** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Capacity model and saturation signals** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define a capacity model covering concurrent chains, chain depth/fan-out, handler time, remote ratio, tenant mix, CPU, memory, queues, and remote connections.
- [ ] Translate the model into configurable ceilings and explicit tenant fairness/starvation-prevention rules.
- [ ] Define safe operating headroom and leading saturation signals.
- [ ] Validate the model with burst, sustained, skewed-tenant, deep-chain, and high-remote-ratio load tests.
- [ ] Feed capacity signals into admission control/alerts and review the model whenever dependencies or benchmark baselines change.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Capacity model and saturation signals** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Capacity model and saturation signals**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Capacity model and saturation signals**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Capacity model and saturation signals**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Capacity model and saturation signals** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Capacity model and saturation signals** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Capacity model and saturation signals** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Capacity model and saturation signals**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C017, INV-21-C067, INV-21-C069** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Capacity model and saturation signals**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Capacity model and saturation signals** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C017, INV-21-C067, INV-21-C069 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-023 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-024 — Serialization/zero-copy measurement evidence

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C065, INV-21-C066  
**Observed gap:** Direct handler composition avoids a network hop, but the repository does not measure serialization/copy/context-switch savings or prove zero-copy safety/semantics.  
**Required completion:** Add comparative local-vs-remote profiling and correctness tests for any zero-copy/argument-handoff optimization.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Serialization/zero-copy measurement evidence** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Serialization/zero-copy measurement evidence** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Serialization/zero-copy measurement evidence** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define exactly which serialization, memory-copy, syscall, or context-switch costs the local path claims to eliminate.
- [ ] Instrument equivalent local/remote requests for allocations/copies/context switches and compare against a controlled baseline.
- [ ] Define ownership, lifetime, mutability, aliasing, task/thread safety, and post-call validity for any shared buffers/references.
- [ ] Prove zero-copy optimizations never bypass validation, authorization, tenant isolation, schema checks, or audit semantics.
- [ ] Test large/mutable payloads, handler mutation, cancellation, exception unwinding, concurrency, and copy-fallback behavior.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Serialization/zero-copy measurement evidence** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Serialization/zero-copy measurement evidence**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Serialization/zero-copy measurement evidence**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Serialization/zero-copy measurement evidence**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Serialization/zero-copy measurement evidence** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Serialization/zero-copy measurement evidence** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Serialization/zero-copy measurement evidence** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Serialization/zero-copy measurement evidence**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C065, INV-21-C066** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Serialization/zero-copy measurement evidence**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Serialization/zero-copy measurement evidence** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C065, INV-21-C066 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-024 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-025 — Fuzz/property tests for untrusted inputs

**Severity:** HIGH  
**Mapped controls:** INV-21-C085  
**Observed gap:** No fuzzing/property tests cover callee/tenant/trace/path values, handler failures, policy decisions, schema boundaries, or hostile oversized inputs.  
**Required completion:** Add Hypothesis/Atheris or equivalent fuzz/property suite with corpus and CI budget.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Fuzz/property tests for untrusted inputs** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Fuzz/property tests for untrusted inputs** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Fuzz/property tests for untrusted inputs** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Use property-based generation for identifiers, context, path/depth, metadata, operation names, and boundary-size values.
- [ ] Fuzz malformed/oversized/Unicode/control-character inputs and assert bounded rejection without crash, allocation explosion, or log injection.
- [ ] Fuzz schema decoders and capability/remote adapter responses independently.
- [ ] Assert invariants such as no unauthorized cross-tenant execution, bounded depth, monotonic revisions, and normalized errors.
- [ ] Persist minimized regression corpus cases and run PR smoke plus longer scheduled fuzz campaigns with artifact retention.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Fuzz/property tests for untrusted inputs** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Fuzz/property tests for untrusted inputs**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Fuzz/property tests for untrusted inputs**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Fuzz/property tests for untrusted inputs**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Fuzz/property tests for untrusted inputs** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Fuzz/property tests for untrusted inputs** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Fuzz/property tests for untrusted inputs** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Fuzz/property tests for untrusted inputs**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C085** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Fuzz/property tests for untrusted inputs**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Fuzz/property tests for untrusted inputs** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C085 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-025 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-026 — Concurrency/race test suite

**Severity:** HIGH  
**Mapped controls:** INV-21-C086  
**Observed gap:** Residency was made thread-safe, but there are no race tests for concurrent place/unplace/resolve/call, revision monotonicity, or policy/transport callback concurrency.  
**Required completion:** Add multi-thread stress/race tests and, where supported, sanitizer/instrumented runs.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Concurrency/race test suite** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Concurrency/race test suite** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Concurrency/race test suite** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Stress concurrent place/unplace/resolve/call/remote/telemetry operations with forced interleavings.
- [ ] Assert residency revision monotonicity and snapshot consistency under concurrent readers/writers.
- [ ] Test placement-change check-then-act races and define revalidation/atomicity semantics.
- [ ] Test concurrent injected policy/transport callbacks plus shutdown/config reload/quarantine races.
- [ ] Use platform-appropriate race/instrumented tooling and enforce no-deadlock/no-lost-revision/no-duplicate-completion invariants.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Concurrency/race test suite** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Concurrency/race test suite**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Concurrency/race test suite**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Concurrency/race test suite**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Concurrency/race test suite** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Concurrency/race test suite** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Concurrency/race test suite** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Concurrency/race test suite**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C086** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Concurrency/race test suite**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Concurrency/race test suite** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C086 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-026 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-027 — Threat-model-derived adversarial tests

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C041, INV-21-C050, INV-21-C087  
**Observed gap:** Current tests cover cross-tenant and capability refusal only; no replay/spoofing/injection/resource-exhaustion/side-channel/provider-compromise scenarios are exercised.  
**Required completion:** Create threat model artifact and automated negative tests for each abuse case, including spoofed identity/trace, handler exceptions and exhaustion.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Threat-model-derived adversarial tests** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Threat-model-derived adversarial tests** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Threat-model-derived adversarial tests** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Create a threat model identifying assets, trust boundaries, principals, entry points, assumptions, attacker capabilities, and abuse cases.
- [ ] Cover identity spoofing, tenant confusion, capability bypass, replay, trace/path manipulation, stale residency, compromised providers, and malicious handlers/peers.
- [ ] Cover resource exhaustion, telemetry-cardinality/audit-pressure abuse, and latency/error/residency side channels.
- [ ] Map every threat to preventive/detective controls and named automated negative tests.
- [ ] Review the threat model whenever identity, schemas, policy authority, transport, or deployment topology changes.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Threat-model-derived adversarial tests** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Threat-model-derived adversarial tests**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Threat-model-derived adversarial tests**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Threat-model-derived adversarial tests**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Threat-model-derived adversarial tests** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Threat-model-derived adversarial tests** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Threat-model-derived adversarial tests** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Threat-model-derived adversarial tests**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C041, INV-21-C050, INV-21-C087** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Threat-model-derived adversarial tests**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Threat-model-derived adversarial tests** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C041, INV-21-C050, INV-21-C087 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-027 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-028 — Adjacent-layer integration tests

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C030, INV-21-C083  
**Observed gap:** No executable integration suite proves interoperability with INV-20, INV-10, INV-16, INV-13 or SCH-01; the pk_core conformance test skips when the framework is absent.  
**Required completion:** Create workspace integration fixtures for each declared dependency and make skipped mandatory integration tests a CI failure.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Adjacent-layer integration tests** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Adjacent-layer integration tests** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Adjacent-layer integration tests** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Create executable fixtures for INV-20, INV-10, INV-16, INV-13 (where applicable), SCH-01, and `pk_core` gate infrastructure.
- [ ] Pin fixture versions and exercise local chain, remote fallback, authz denial, cross-tenant refusal, async, timeout/cancel, stale residency, and structured errors end-to-end.
- [ ] Verify identity/trace/deadline/idempotency propagation across every declared boundary.
- [ ] Test rolling-version combinations required by the compatibility matrix and execute from the built artifact.
- [ ] Fail CI if any mandatory dependency/fixture is absent or a required integration test is skipped; retain logs/version inventory as evidence.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Adjacent-layer integration tests** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Adjacent-layer integration tests**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Adjacent-layer integration tests**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Adjacent-layer integration tests**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Adjacent-layer integration tests** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Adjacent-layer integration tests** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Adjacent-layer integration tests** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Adjacent-layer integration tests**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C030, INV-21-C083** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Adjacent-layer integration tests**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Adjacent-layer integration tests** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C030, INV-21-C083 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-028 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-029 — Platform/runtime compatibility tests

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C084  
**Observed gap:** No test matrix covers supported Python versions, CPU architectures, operating systems/runtimes, protocol versions or execution tiers.  
**Required completion:** Declare supported matrix and run CI on representative Windows/Linux and target architectures/runtimes.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Platform/runtime compatibility tests** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Platform/runtime compatibility tests** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Platform/runtime compatibility tests** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Declare supported OS, Python, CPU architecture, execution-tier, and protocol/schema combinations.
- [ ] Run native CI jobs on representative supported combinations and installation tests for each package target.
- [ ] Exercise platform-sensitive path/case, timers, signals/cancellation, threads/event loops, and filesystem behavior.
- [ ] Run core/integration/async/error suites across the matrix or explicitly document sampled versus exhaustive coverage.
- [ ] Add negative startup diagnostics for unsupported environments and retain platform/toolchain fingerprints in release evidence.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Platform/runtime compatibility tests** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Platform/runtime compatibility tests**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Platform/runtime compatibility tests**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Platform/runtime compatibility tests**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Platform/runtime compatibility tests** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Platform/runtime compatibility tests** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Platform/runtime compatibility tests** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Platform/runtime compatibility tests**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C084** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Platform/runtime compatibility tests**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Platform/runtime compatibility tests** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C084 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-029 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-030 — Fault-injection, partition and reconnect testing

**Severity:** HIGH  
**Mapped controls:** INV-21-C051, INV-21-C060, INV-21-C089  
**Observed gap:** No tests inject handler crash/stall, policy-provider outage, stale residency, remote transport failure, node/site partition, reconnect, or degraded control plane.  
**Required completion:** Add deterministic failure injection and recovery objective assertions.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Fault-injection, partition and reconnect testing** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Fault-injection, partition and reconnect testing** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Fault-injection, partition and reconnect testing** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Add deterministic fault points for handler crash/stall, provider timeout/malformed response, stale residency, remote failure, audit/export failure, and config failure.
- [ ] Simulate node/site/control-plane partitions and validate behavior during isolation and after reconnect.
- [ ] Assert deadline/cancellation/retry budgets, circuit breaker, quarantine, readiness, and load-shedding transitions under faults.
- [ ] Define and measure detection/recovery objectives and verify reconciliation after stale/out-of-order updates.
- [ ] Keep fault injection test-only/strongly controlled and archive scenarios plus recovery metrics as CI evidence.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Fault-injection, partition and reconnect testing** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Fault-injection, partition and reconnect testing**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Fault-injection, partition and reconnect testing**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Fault-injection, partition and reconnect testing**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Fault-injection, partition and reconnect testing** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Fault-injection, partition and reconnect testing** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Fault-injection, partition and reconnect testing** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Fault-injection, partition and reconnect testing**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C051, INV-21-C060, INV-21-C089** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Fault-injection, partition and reconnect testing**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Fault-injection, partition and reconnect testing** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C051, INV-21-C060, INV-21-C089 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-030 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-031 — Health/stall detection and quarantine control

**Severity:** HIGH  
**Mapped controls:** INV-21-C052, INV-21-C059  
**Observed gap:** No handler stall thresholds, watchdogs, unhealthy placement suppression, quarantine/freeze control, or runtime emergency-disable switch exists.  
**Required completion:** Add deadline/stall detection, quarantine state, disable switch and operator recovery path.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Health/stall detection and quarantine control** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Health/stall detection and quarantine control** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Health/stall detection and quarantine control** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define stall thresholds from service deadlines and add watchdog/deadline observation for slow handlers/dependencies.
- [ ] Add quarantine for unhealthy handlers/placements and block new local dispatch to quarantined targets.
- [ ] Define automatic/operator quarantine entry/exit, cooldown/probes, and a controlled emergency disable/freeze switch.
- [ ] Integrate quarantine/disable state with readiness, admission, metrics, audit, alerts, and operator runbooks.
- [ ] Test hung/slow handlers, false-positive recovery, concurrent transitions, remote-unavailable safe mode, and rollback/re-enable.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Health/stall detection and quarantine control** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Health/stall detection and quarantine control**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Health/stall detection and quarantine control**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Health/stall detection and quarantine control**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Health/stall detection and quarantine control** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Health/stall detection and quarantine control** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Health/stall detection and quarantine control** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Health/stall detection and quarantine control**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C052, INV-21-C059** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Health/stall detection and quarantine control**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Health/stall detection and quarantine control** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C052, INV-21-C059 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-031 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-032 — Crash consistency / restart / reconstruction procedure

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C057, INV-21-C095  
**Observed gap:** Residency state is memory-only with no explicit reconstruction source, startup reconciliation, snapshot/restore boundary, or restart invariant tests.  
**Required completion:** Document authoritative reconstruction from placement source and test clean restart/reconciliation; explicitly mark backup N/A if derived state.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Crash consistency / restart / reconstruction procedure** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Crash consistency / restart / reconstruction procedure** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Crash consistency / restart / reconstruction procedure** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Classify residency/runtime state as derived or durable and identify the authoritative reconstruction source.
- [ ] Define startup sequencing through config, identity, authority connection, snapshot/revision validation, reconciliation, and readiness.
- [ ] Define unavailable-authority restart behavior and ensure stale cached state cannot silently authorize local execution.
- [ ] Test clean/unclean restart, lost cache, stale snapshot, revision replay/rollback, and placement churn during recovery.
- [ ] Document backup/restore boundaries explicitly, including `N/A — derived state` where appropriate, and record reconciliation evidence.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Crash consistency / restart / reconstruction procedure** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Crash consistency / restart / reconstruction procedure**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Crash consistency / restart / reconstruction procedure**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Crash consistency / restart / reconstruction procedure**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Crash consistency / restart / reconstruction procedure** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Crash consistency / restart / reconstruction procedure** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Crash consistency / restart / reconstruction procedure** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Crash consistency / restart / reconstruction procedure**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C057, INV-21-C095** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Crash consistency / restart / reconstruction procedure**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Crash consistency / restart / reconstruction procedure** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C057, INV-21-C095 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-032 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-033 — Canary/staged rollout and automated rollback

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C038, INV-21-C092  
**Observed gap:** README mentions rerunning gates and removing a registry component, but no canary/staged rollout mechanism, rollback automation, rollback criteria, or versioned migration procedure is supplied.  
**Required completion:** Add rollout/rollback runbook and automation hooks with health/SLO abort criteria.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Canary/staged rollout and automated rollback** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Canary/staged rollout and automated rollback** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Canary/staged rollout and automated rollback** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define rollout stages, canary unit/scope, and explicit promotion criteria.
- [ ] Automate rollback triggers using error rate, SLO regression, authorization anomalies, saturation, health, and crash rate.
- [ ] Ensure rollback atomically restores a schema-compatible package/config state and document irreversible migration constraints.
- [ ] Define rolling schema/config migration order and exercise rollback with the actual release artifact.
- [ ] Link rollout to dashboards/alerts/owners/evidence and prohibit ad-hoc unsigned production replacement.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Canary/staged rollout and automated rollback** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Canary/staged rollout and automated rollback**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Canary/staged rollout and automated rollback**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Canary/staged rollout and automated rollback**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Canary/staged rollout and automated rollback** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Canary/staged rollout and automated rollback** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Canary/staged rollout and automated rollback** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Canary/staged rollout and automated rollback**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C038, INV-21-C092** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Canary/staged rollout and automated rollback**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Canary/staged rollout and automated rollback** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C038, INV-21-C092 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-033 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-034 — Patching, vulnerability and EOL policy

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C094  
**Observed gap:** No supported-version lifecycle, security patch SLA, CVE intake process, EOL timeline, or dependency update policy exists.  
**Required completion:** Add SECURITY.md/support policy with response targets and release lifecycle.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Patching, vulnerability and EOL policy** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Patching, vulnerability and EOL policy** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Patching, vulnerability and EOL policy** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Add `SECURITY.md` with supported versions, reporting channel, triage/disclosure process, and update expectations.
- [ ] Define vulnerability severity classification, patch SLAs, actively exploited issue handling, and release-block thresholds.
- [ ] Cover `pk_core`, Python dependencies, build tooling, runtime/base images, and adjacent components in CVE intake.
- [ ] Define release-line EOL dates/policy and a time-bounded exception process with compensating controls.
- [ ] Audit policy compliance periodically and attach current scan/exception state to release evidence.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Patching, vulnerability and EOL policy** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Patching, vulnerability and EOL policy**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Patching, vulnerability and EOL policy**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Patching, vulnerability and EOL policy**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Patching, vulnerability and EOL policy** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Patching, vulnerability and EOL policy** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Patching, vulnerability and EOL policy** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Patching, vulnerability and EOL policy**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C094** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Patching, vulnerability and EOL policy**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Patching, vulnerability and EOL policy** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C094 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-034 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-035 — Incident severity and response runbook

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C097  
**Observed gap:** No severity taxonomy, paging triggers, containment steps, evidence collection, recovery validation, or escalation workflow exists.  
**Required completion:** Add incident runbook tied to local-chain failure/security signals.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Incident severity and response runbook** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Incident severity and response runbook** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Incident severity and response runbook** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define incident severities based on tenant isolation/authz, availability, integrity, latency/SLO, auditability, and blast radius.
- [ ] Map concrete INV-21 signals to paging/triage triggers.
- [ ] Create containment procedures for disabling local chaining, forcing remote mode, quarantining targets, freezing config, or isolating a site.
- [ ] Define evidence preservation and recovery validation steps, including residency reconciliation and authorization/security checks.
- [ ] Document escalation, post-incident root cause/regression-test requirements, and run tabletop/game-day exercises.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Incident severity and response runbook** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Incident severity and response runbook**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Incident severity and response runbook**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Incident severity and response runbook**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Incident severity and response runbook** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Incident severity and response runbook** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Incident severity and response runbook** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Incident severity and response runbook**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C097** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Incident severity and response runbook**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Incident severity and response runbook** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C097 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-035 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-036 — Recurring review and exception/waiver registry

**Severity:** MEDIUM  
**Mapped controls:** INV-21-C098, INV-21-C099  
**Observed gap:** No scheduled architecture/access/policy/dependency review record or owned exception/waiver/technical-debt registry with expiry exists.  
**Required completion:** Add review cadence/checklist and machine-readable waiver/debt ledger with owner and expiry.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Recurring review and exception/waiver registry** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Recurring review and exception/waiver registry** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Recurring review and exception/waiver registry** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define recurring reviews for architecture, threat model, access/policy, dependencies, compatibility, SLO/capacity, and incident lessons.
- [ ] Create a machine-readable waiver/debt registry with ID, control, rationale, risk, owner/approver, dates, expiry, compensating controls, and remediation plan.
- [ ] Require expiration and CI validation; do not permit indefinite unreviewed production/security waivers.
- [ ] Link waivers to traceability/release evidence and generate upcoming-expiry/overdue reports.
- [ ] Review every waiver at release time and after material architecture/security changes.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Recurring review and exception/waiver registry** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Recurring review and exception/waiver registry**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Recurring review and exception/waiver registry**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Recurring review and exception/waiver registry**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Recurring review and exception/waiver registry** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Recurring review and exception/waiver registry** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Recurring review and exception/waiver registry** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Recurring review and exception/waiver registry**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C098, INV-21-C099** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Recurring review and exception/waiver registry**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Recurring review and exception/waiver registry** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C098, INV-21-C099 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-036 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-037 — Formal production exit evidence bundle

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C090, INV-21-C100  
**Observed gap:** No generated evidence ledger/gate result is present in the archive, and normal gate execution cannot run without pk_core. Therefore production exit cannot be independently verified from this repository alone.  
**Required completion:** Bundle signed machine-readable gate results, evidence ledger, hashes and release manifest produced in CI with all mandatory checks non-skipped.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Formal production exit evidence bundle** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Formal production exit evidence bundle** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Formal production exit evidence bundle** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define a canonical machine-readable production-exit evidence schema.
- [ ] Generate evidence automatically from the exact source/artifact in CI, including pass/fail/skip counts, versions, digests, traceability, security, integration, compatibility, and benchmark results.
- [ ] Block release on any skipped mandatory check, failed mandatory requirement, expired waiver, or missing evidence.
- [ ] Integrity-protect the manifest and retain referenced evidence durably.
- [ ] Provide an offline verifier that emits machine-readable GO/NO_GO with explicit reasons.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Formal production exit evidence bundle** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Formal production exit evidence bundle**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Formal production exit evidence bundle**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Formal production exit evidence bundle**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Formal production exit evidence bundle** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Formal production exit evidence bundle** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Formal production exit evidence bundle** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Formal production exit evidence bundle**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C090, INV-21-C100** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Formal production exit evidence bundle**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Formal production exit evidence bundle** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C090, INV-21-C100 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-037 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-038 — Continuous integration workflow

**Severity:** HIGH  
**Mapped controls:** INV-21-C070, INV-21-C081, INV-21-C082, INV-21-C090  
**Observed gap:** No CI configuration runs compile, runtime tests, full pk_core conformance, security checks, compatibility tests, benchmarks or packaging validation on change.  
**Required completion:** Add CI pipeline with fail-on-skip mandatory gates, test artifacts and release evidence.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Continuous integration workflow** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Continuous integration workflow** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Continuous integration workflow** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Add CI for lint/static/compile, runtime/unit, schema, package build/install, and dependency integrity.
- [ ] Add mandatory `pk_core` conformance and adjacent-layer integration jobs with fail-on-missing-prerequisite behavior.
- [ ] Add async, property/fuzz smoke, concurrency/race, fault-injection, security-negative, semantic-equivalence, compatibility, and benchmark jobs at suitable cadences.
- [ ] Generate SBOM/provenance/checksums/signatures/traceability/test reports/production evidence in release CI.
- [ ] Harden CI with least-privilege credentials, immutable action/tool pinning, secret isolation, protected release jobs, required checks, and retention.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Continuous integration workflow** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Continuous integration workflow**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Continuous integration workflow**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Continuous integration workflow**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Continuous integration workflow** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Continuous integration workflow** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Continuous integration workflow** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Continuous integration workflow**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C070, INV-21-C081, INV-21-C082, INV-21-C090** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Continuous integration workflow**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Continuous integration workflow** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C070, INV-21-C081, INV-21-C082, INV-21-C090 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-038 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-039 — License and notice files

**Severity:** LOW  
**Mapped controls:** INV-21-C031, INV-21-C094  
**Observed gap:** The archive contains no LICENSE/NOTICE file or explicit redistribution terms for the implementation package.  
**Required completion:** Add the project-approved license and notice/provenance metadata.

### 1. Architecture / contract

- [ ] Write and approve a design note for **License and notice files** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **License and notice files** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **License and notice files** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Add the approved root `LICENSE` and keep package metadata consistent with it.
- [ ] Add `NOTICE`/attribution files when required by bundled/vendored/generated materials.
- [ ] Inventory third-party licenses and check compatibility with the distribution model.
- [ ] Include licensing in the SBOM and CI compliance/review gate.
- [ ] Verify wheel/sdist/release ZIP contain all required license/notice materials.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **License and notice files** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **License and notice files**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **License and notice files**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **License and notice files**.
- [ ] Add concurrency/reentrancy/recovery coverage where **License and notice files** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **License and notice files** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **License and notice files** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **License and notice files**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C031, INV-21-C094** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **License and notice files**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **License and notice files** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C031, INV-21-C094 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-039 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-040 — Structured request/call context

**Severity:** HIGH  
**Mapped controls:** INV-21-C023, INV-21-C024, INV-21-C026, INV-21-C073  
**Observed gap:** Caller identity, tenant, trace, deadline, capabilities and operation metadata are separate primitive arguments rather than a validated/versioned context object, increasing spoofing and compatibility risk.  
**Required completion:** Define immutable typed CallContext with authenticated principal, tenant, trace/span, deadline, idempotency and capability claims/proofs.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Structured request/call context** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Structured request/call context** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Structured request/call context** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define immutable versioned `CallContext` with authenticated principal, tenant, trace/span, deadline, idempotency, operation, capabilities/proofs, depth/path, and relevant policy/config revision references.
- [ ] Separate trusted runtime-populated fields from caller metadata and forbid overriding identity/tenant/policy evidence.
- [ ] Define field validation/normalization/limits and monotonic deadline semantics.
- [ ] Define immutable child-hop derivation and guaranteed local/remote propagation without dropping security-critical fields.
- [ ] Test spoofing, oversized context, nested/async hops, remote serialization, expiry, redaction, and N/N-1 compatibility.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Structured request/call context** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Structured request/call context**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Structured request/call context**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Structured request/call context**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Structured request/call context** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Structured request/call context** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Structured request/call context** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Structured request/call context**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C023, INV-21-C024, INV-21-C026, INV-21-C073** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Structured request/call context**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Structured request/call context** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C023, INV-21-C024, INV-21-C026, INV-21-C073 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-040 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-041 — Handler exception and failure-code normalization

**Severity:** HIGH  
**Mapped controls:** INV-21-C014, INV-21-C026, INV-21-C051  
**Observed gap:** Chain-internal refusal errors are structured, but arbitrary local handler exceptions and remote adapter failures pass through without a stable error taxonomy or local/remote semantic normalization.  
**Required completion:** Define error envelope/mapping rules and parity tests across local and remote paths.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Handler exception and failure-code normalization** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Handler exception and failure-code normalization** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Handler exception and failure-code normalization** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Define a versioned public error envelope with stable code/category, sanitized message/details, retriable flag, origin layer, and correlation ID.
- [ ] Map validation/authz/residency/depth/cycle/overload/deadline/cancel/handler/provider/transport/protocol failures to stable codes.
- [ ] Keep raw stack traces, credentials, policy internals, and filesystem/runtime details internal while retaining them in protected diagnostics.
- [ ] Define local/remote parity and retry guidance from error categories rather than string matching.
- [ ] Test arbitrary/nested handler exceptions, cancellation/timeouts, malformed/unknown remote errors, disconnects, and taxonomy compatibility.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Handler exception and failure-code normalization** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Handler exception and failure-code normalization**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Handler exception and failure-code normalization**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Handler exception and failure-code normalization**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Handler exception and failure-code normalization** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Handler exception and failure-code normalization** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Handler exception and failure-code normalization** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Handler exception and failure-code normalization**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C014, INV-21-C026, INV-21-C051** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Handler exception and failure-code normalization**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Handler exception and failure-code normalization** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C014, INV-21-C026, INV-21-C051 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-041 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

## GAP-042 — Semantic-equivalence test suite

**Severity:** CRITICAL  
**Mapped controls:** INV-21-C011, INV-21-C013, INV-21-C029, INV-21-C082  
**Observed gap:** The core promise that local and remote calls are semantically identical is asserted in prose but not tested against the same request corpus, errors, cancellation, authz, serialization and edge cases.  
**Required completion:** Build a shared conformance corpus executed through both local and remote paths and byte/semantic-compare outcomes.

### 1. Architecture / contract

- [ ] Write and approve a design note for **Semantic-equivalence test suite** covering trust boundaries, authoritative inputs, interfaces, state, dependencies, configuration, failure behavior, compatibility, and rollback/recovery.
- [ ] Identify the system of record and owner for **Semantic-equivalence test suite** and distinguish trusted runtime-derived data from caller-controlled data.
- [ ] Define versioning/deprecation rules and stable identifiers needed by **Semantic-equivalence test suite** before declaring the implementation production-ready.

### 2. Component-specific implementation / hardening

- [ ] Build a shared conformance corpus spanning success, return values, validation, identity/authz, tenant isolation, depth/cycles, deadlines/cancel, idempotency, exceptions, and hostile boundaries.
- [ ] Run every applicable case through both local direct dispatch and the concrete remote path with identical logical context/schemas.
- [ ] Compare return schema/value, public error code/category, side effects, idempotency, trace/context propagation, authorization, and cancellation/deadline semantics.
- [ ] Document the narrow set of allowed transport-only differences and include N/N-1 rolling-version cases plus differential/property generation.
- [ ] Make any unexplained semantic divergence release-blocking and store corpus version/results in the production evidence bundle.
- [ ] Bound every workload- or attacker-controlled dimension introduced by **Semantic-equivalence test suite** (size, count, concurrency, depth, retries, retention, time, or cardinality as applicable).
- [ ] Define deterministic fail-open/fail-closed/degraded behavior for **Semantic-equivalence test suite**; security-sensitive uncertainty must never silently become authorization/success.

### 3. Verification / adversarial testing

- [ ] Add focused unit tests for normal behavior and every documented boundary condition of **Semantic-equivalence test suite**.
- [ ] Add malformed, missing, stale, unauthorized, incompatible, oversized, timeout, and dependency-failure cases applicable to **Semantic-equivalence test suite**.
- [ ] Add concurrency/reentrancy/recovery coverage where **Semantic-equivalence test suite** touches shared state or callbacks.
- [ ] Add at least one end-to-end test through the public INV-21 call path; internal-helper-only testing is insufficient.
- [ ] Verify **Semantic-equivalence test suite** cannot cause cross-tenant execution, authorization bypass, partial state, unbounded resource growth, deadlock, or silent semantic drift.
- [ ] Make mandatory tests non-skippable in release CI; missing prerequisites must fail the gate.

### 4. Observability / operations / documentation

- [ ] Add bounded, privacy-safe telemetry showing whether **Semantic-equivalence test suite** is healthy, degraded, refusing work, saturated, or violating budget.
- [ ] Document configuration, secure defaults, failure modes, troubleshooting, recovery, rollback, and operator responsibilities for **Semantic-equivalence test suite**.
- [ ] Correlate runtime behavior with release/config/schema/policy/dependency revisions needed to reproduce incidents.
- [ ] Map implementation, tests, docs, and evidence back to **INV-21-C011, INV-21-C013, INV-21-C029, INV-21-C082** in the requirements traceability matrix.

### 5. Definition of done / release gate

- [ ] Implementation is reviewed and merged with no unresolved CRITICAL/HIGH finding specific to **Semantic-equivalence test suite**.
- [ ] Unit, negative, integration, compatibility, and applicable security/performance tests pass from a clean environment.
- [ ] Release evidence contains machine-readable proof for **Semantic-equivalence test suite** and the exact artifact/config/schema/dependency versions used.
- [ ] INV-21-C011, INV-21-C013, INV-21-C029, INV-21-C082 are marked `verified`, or any exception is explicitly approved, owned, compensated, and unexpired.
- [ ] **Close GAP-042 only after an independent second-pass audit confirms the original gap is no longer reproducible.**

---

# Final independent re-audit

- [ ] Audit a clean extraction of the candidate release, not a developer working tree.
- [ ] Re-run compile/static checks, standalone runtime tests, and full `pk_core` conformance with zero mandatory skips.
- [ ] Re-run adjacent integration, async, semantic-equivalence, security-negative, fuzz/property smoke, race/concurrency, fault-injection, compatibility, and benchmark gates.
- [ ] Install/run the built artifact in a clean environment with no undeclared local paths/dependencies.
- [ ] Verify SBOM/provenance/signatures/checksums against the exact artifact.
- [ ] Verify traceability covers C001-C100 and GAP-001 through GAP-042 with concrete evidence references.
- [ ] Verify all waivers are approved, scoped, compensated, owned, and unexpired.
- [ ] Verify dashboards/alerts/runbooks/rollout/rollback/reconstruction/incident procedures match the shipped version.
- [ ] Produce a new post-remediation audit report and machine-readable GO/NO_GO result.
