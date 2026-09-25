# INV-02 Container Substrate — v5.0.0 annotated checklist

> Annotated copy of the supplied v4.2.0 checklist. Each component carries a v5.0.0 status block (source of truth: `COMPONENT_STATUS.json`). **No box is ticked**: this checklist defines a checked box as implemented, *independently verified* and evidenced, and independent verification has not happened yet.

# INV-02 Container Substrate v4.2.0 — Professional Missing-Component Engineering Checklist

**Scope:** implementation-grade checklist for all 78 missing production components identified by the v4.2.0 audit.

## How to use this checklist

- Each component has a stable identifier (`MC01`–`MC78`) and checklist item IDs suitable for issue trackers, CI evidence, audit references, and release gates.
- A checked box means the requirement is **implemented, independently verified, and evidenced**; implementation alone is not sufficient.
- Recommended evidence root: `evidence/MCxx/<item-id>/` containing test output, configuration samples, design decisions, logs/metrics screenshots or exports, and release-artifact digests as applicable.
- All exceptions should identify owner, justification, compensating control, affected versions/environments, approval, expiry, and a closure issue.
- Security-sensitive defaults should fail closed unless a documented workload class explicitly authorizes degraded operation.
- Treat P0 items as production blockers, P1 items as production-readiness requirements, and P2 items as release/governance requirements.

## Global completion gates

- [ ] **G-01** All 78 components have an accountable owner and lifecycle status (`planned`, `in-progress`, `implemented`, `certified`, `deferred-with-waiver`).
- [ ] **G-02** All P0 components required by the target workload profile are implemented and have no open critical/high-severity security findings without approved, unexpired exceptions.
- [ ] **G-03** Cross-component state ownership and trust boundaries are captured in an architecture model and reviewed for circular authority or ambiguous ownership.
- [ ] **G-04** End-to-end pull → verify → unpack → create → start → observe → stop → delete → GC flows have release evidence on every certified platform tuple.
- [ ] **G-05** Disaster, registry-compromise, metadata-corruption, and runtime-isolation incident exercises have been run and resulting corrective actions are closed or explicitly waived.
- [ ] **G-06** Release evidence is machine-readable and cryptographically bound to source revision and shipped artifact digests.

---

## MC01 — OCI Image Specification implementation

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** full descriptor, config, manifest, index, platform, annotation, media-type, and artifact handling rather than the package's intentionally small private manifest schema.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** oci.py  
> **Evidence:** `tests/test_oci.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC01-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **OCI Image Specification implementation**.
- [ ] **MC01-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC01-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC01-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC01-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC01-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC01-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC01-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC01-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC01-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC01-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC01-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC01-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC01-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC01-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC01-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC01-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC01-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC01-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC01-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC01-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC01-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC01-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC01-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC01-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC01-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC01-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC01-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC01-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC01-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC01-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC01-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC01-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC01-34** Implement and verify **descriptor** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC01-35** Implement and verify **config** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC01-36** Implement and verify **manifest** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC01-37** Implement and verify **index** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC01-38** Implement and verify **platform** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC01-39** Implement and verify **annotation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC01-40** Implement and verify **media-type** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC01-41** Implement and verify **artifact handling** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC01-42** Validate canonical digest and size semantics for every descriptor edge; reject descriptor/content mismatches before state mutation.
- [ ] **MC01-43** Exercise manifest/index recursion limits and cycle/alias edge cases; impose explicit descriptor-depth and aggregate-size bounds.
- [ ] **MC01-44** Preserve unknown-but-valid annotations and media types without silently reinterpreting them; define the policy for unsupported artifacts.

### Definition of done / evidence gate

- [ ] **MC01-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC01-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC01-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC01-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC01-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC02 — OCI Distribution/registry client

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** authenticated HTTPS pull/push, blob upload/download, redirects, range requests, resumability, pagination, and registry error semantics.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** distribution.py  
> **Evidence:** `tests/test_distribution.py`  
> **Open:** push/upload side of the Distribution API; referrers API


### Architecture & requirements

- [ ] **MC02-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **OCI Distribution/registry client**.
- [ ] **MC02-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC02-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC02-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC02-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC02-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC02-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC02-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC02-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC02-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC02-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC02-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC02-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC02-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC02-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC02-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC02-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC02-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC02-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC02-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC02-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC02-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC02-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC02-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC02-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC02-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC02-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC02-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC02-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC02-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC02-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC02-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC02-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC02-34** Implement and verify **authenticated HTTPS pull/push** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC02-35** Implement and verify **blob upload/download** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC02-36** Implement and verify **redirects** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC02-37** Implement and verify **range requests** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC02-38** Implement and verify **resumability** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC02-39** Implement and verify **pagination** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC02-40** Implement and verify **registry error semantics** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC02-41** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC02-42** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC02-43** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.

### Definition of done / evidence gate

- [ ] **MC02-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC02-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC02-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC02-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC02-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC03 — Persistent content-addressable store

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** durable blob/index storage with crash consistency, fsync policy, checksums, leases, garbage collection, compaction, and recovery.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** store.py  
> **Evidence:** `tests/test_store.py`, `tests/test_fuzz_stress.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC03-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Persistent content-addressable store**.
- [ ] **MC03-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC03-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC03-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC03-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC03-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC03-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC03-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC03-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC03-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC03-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC03-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC03-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC03-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC03-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC03-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC03-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC03-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC03-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC03-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC03-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC03-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC03-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC03-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC03-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC03-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC03-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC03-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC03-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC03-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC03-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC03-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC03-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC03-34** Implement and verify **durable blob/index storage with crash consistency** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC03-35** Implement and verify **fsync policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC03-36** Implement and verify **checksums** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC03-37** Implement and verify **leases** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC03-38** Implement and verify **garbage collection** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC03-39** Implement and verify **compaction** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC03-40** Implement and verify **recovery** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC03-41** Use atomic publish semantics for content: write to an isolated temporary object, fsync according to policy, verify digest, then make the blob discoverable.
- [ ] **MC03-42** Ensure garbage collection computes reachability from authoritative roots and honors active leases, in-flight operations, and crash-recovery markers.
- [ ] **MC03-43** Detect hash/path/index divergence and provide a repair path that never converts corrupt bytes into a trusted object.

### Definition of done / evidence gate

- [ ] **MC03-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC03-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC03-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC03-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC03-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC04 — Snapshotter/root filesystem manager

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** overlayfs/native snapshot support, layer unpack, whiteouts, copy-up behavior, mount lifecycle, and snapshot garbage collection.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `partial`  
> **Implementation:** rootfs.py (Snapshotter)  
> **Evidence:** `tests/test_rootfs.py`  
> **Open:** overlayfs snapshotter (copy-based only today)


### Architecture & requirements

- [ ] **MC04-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Snapshotter/root filesystem manager**.
- [ ] **MC04-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC04-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC04-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC04-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC04-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC04-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC04-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC04-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC04-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC04-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC04-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC04-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC04-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC04-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC04-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC04-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC04-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC04-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC04-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC04-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC04-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC04-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC04-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC04-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC04-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC04-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC04-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC04-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC04-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC04-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC04-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC04-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC04-34** Implement and verify **overlayfs/native snapshot support** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC04-35** Implement and verify **layer unpack** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC04-36** Implement and verify **whiteouts** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC04-37** Implement and verify **copy-up behavior** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC04-38** Implement and verify **mount lifecycle** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC04-39** Implement and verify **snapshot garbage collection** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC04-40** Use atomic publish semantics for content: write to an isolated temporary object, fsync according to policy, verify digest, then make the blob discoverable.
- [ ] **MC04-41** Ensure garbage collection computes reachability from authoritative roots and honors active leases, in-flight operations, and crash-recovery markers.
- [ ] **MC04-42** Detect hash/path/index divergence and provide a repair path that never converts corrupt bytes into a trusted object.
- [ ] **MC04-43** Validate every mount source, target, propagation flag, filesystem type, and option against policy before performing privileged mount operations.
- [ ] **MC04-44** Test whiteout, opaque directory, copy-up, hardlink, symlink, xattr, ownership, and permission behavior against the selected snapshotter/filesystem matrix.
- [ ] **MC04-45** Guarantee teardown is idempotent and leak-resistant across process death, lazy/unexpected unmount conditions, and partially constructed snapshots.
- [ ] **MC04-46** Specify a finite-state machine for all lifecycle states and reject illegal transitions with stable, machine-readable error codes.
- [ ] **MC04-47** Make start/stop/delete operations idempotent under retries, controller failover, duplicate messages, and runtime/shim restarts.

### Definition of done / evidence gate

- [ ] **MC04-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC04-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC04-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC04-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC04-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC05 — Container runtime integration

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** OCI Runtime Spec bundle generation and an integration boundary to a runtime such as runc/crun or another approved runtime.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented+runtime-verified`  
> **Implementation:** runtime.py (OCIRuntime, build_spec)  
> **Evidence:** `tests/integration/test_runc.py`  
> **Open:** crun/runsc/kata not exercised on this host


### Architecture & requirements

- [ ] **MC05-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Container runtime integration**.
- [ ] **MC05-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC05-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC05-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC05-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC05-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC05-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC05-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC05-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC05-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC05-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC05-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC05-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC05-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC05-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC05-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC05-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC05-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC05-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC05-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC05-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC05-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC05-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC05-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC05-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC05-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC05-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC05-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC05-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC05-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC05-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC05-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC05-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC05-34** Implement and verify **OCI Runtime Spec bundle generation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC05-35** Implement and verify **an integration boundary to a runtime such as runc/crun or another approved runtime** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC05-36** Generate runtime bundles deterministically from validated state and retain a digestable rendered configuration for audit and incident reconstruction.
- [ ] **MC05-37** Define runtime/shim RPC or process boundaries with explicit version negotiation, timeout behavior, exit semantics, and untrusted-output handling.
- [ ] **MC05-38** Verify that unsupported runtime features fail before workload start rather than degrading silently.

### Definition of done / evidence gate

- [ ] **MC05-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC05-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC05-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC05-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC05-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC06 — Container lifecycle controller

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** create, prepare, start, exec, signal, stop, kill, delete, inspect, wait, restart, and terminal state semantics.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** runtime.py (LifecycleStore)  
> **Evidence:** `tests/test_runtime.py`  
> **Open:** reconciliation loop against live runtime state


### Architecture & requirements

- [ ] **MC06-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Container lifecycle controller**.
- [ ] **MC06-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC06-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC06-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC06-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC06-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC06-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC06-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC06-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC06-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC06-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC06-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC06-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC06-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC06-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC06-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC06-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC06-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC06-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC06-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC06-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC06-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC06-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC06-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC06-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC06-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC06-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC06-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC06-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC06-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC06-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC06-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC06-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC06-34** Implement and verify **create** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC06-35** Implement and verify **prepare** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC06-36** Implement and verify **start** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC06-37** Implement and verify **exec** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC06-38** Implement and verify **signal** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC06-39** Implement and verify **stop** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC06-40** Implement and verify **kill** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC06-41** Implement and verify **delete** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC06-42** Specify a finite-state machine for all lifecycle states and reject illegal transitions with stable, machine-readable error codes.
- [ ] **MC06-43** Make start/stop/delete operations idempotent under retries, controller failover, duplicate messages, and runtime/shim restarts.
- [ ] **MC06-44** Capture exit code, signal, OOM/limit cause, timestamps, and terminal metadata exactly once and make terminal state durable.

### Definition of done / evidence gate

- [ ] **MC06-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC06-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC06-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC06-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC06-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC07 — Linux namespace manager

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** PID, mount, network, IPC, UTS, user, and cgroup namespace construction and teardown.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented+runtime-verified`  
> **Implementation:** runtime.py (build_spec namespaces)  
> **Evidence:** `tests/integration/test_runc.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC07-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Linux namespace manager**.
- [ ] **MC07-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC07-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC07-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC07-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC07-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC07-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC07-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC07-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC07-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC07-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC07-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC07-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC07-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC07-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC07-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC07-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC07-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC07-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC07-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC07-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC07-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC07-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC07-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC07-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC07-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC07-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC07-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC07-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC07-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC07-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC07-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC07-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC07-34** Implement and verify **mount** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC07-35** Implement and verify **network** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC07-36** Implement and verify **user** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC07-37** Implement and verify **cgroup namespace construction** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC07-38** Implement and verify **teardown** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC07-39** Validate every mount source, target, propagation flag, filesystem type, and option against policy before performing privileged mount operations.
- [ ] **MC07-40** Test whiteout, opaque directory, copy-up, hardlink, symlink, xattr, ownership, and permission behavior against the selected snapshotter/filesystem matrix.
- [ ] **MC07-41** Guarantee teardown is idempotent and leak-resistant across process death, lazy/unexpected unmount conditions, and partially constructed snapshots.
- [ ] **MC07-42** Validate namespace ownership and join/create semantics so a workload cannot attach to a more privileged namespace than policy permits.
- [ ] **MC07-43** Verify UID/GID mappings for gaps, overlap, host-root exposure, subordinate-ID exhaustion, and filesystem ownership translation.
- [ ] **MC07-44** Test namespace teardown and orphan cleanup after controller/runtime crashes and host reboot.
- [ ] **MC07-45** Treat network setup as a transaction with rollback of interfaces, addresses, routes, namespaces, firewall/policy state, and IPAM reservations.
- [ ] **MC07-46** Prevent route/address overlap, spoofing, host-network policy bypass, and cross-tenant namespace attachment.

### Definition of done / evidence gate

- [ ] **MC07-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC07-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC07-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC07-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC07-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC08 — cgroups v2 manager

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** CPU, memory, I/O, pids, cpuset, hugetlb, device-related controls, delegation, pressure signals, and cleanup.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `partial`  
> **Implementation:** runtime.py (CgroupV2Manager, Resources)  
> **Evidence:** `tests/test_runtime.py`  
> **Open:** live cgroup v2 host verification (test host is cgroup v1)


### Architecture & requirements

- [ ] **MC08-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **cgroups v2 manager**.
- [ ] **MC08-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC08-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC08-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC08-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC08-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC08-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC08-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC08-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC08-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC08-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC08-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC08-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC08-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC08-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC08-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC08-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC08-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC08-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC08-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC08-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC08-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC08-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC08-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC08-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC08-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC08-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC08-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC08-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC08-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC08-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC08-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC08-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC08-34** Implement and verify **memory** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC08-35** Implement and verify **pids** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC08-36** Implement and verify **cpuset** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC08-37** Implement and verify **hugetlb** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC08-38** Implement and verify **device-related controls** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC08-39** Implement and verify **delegation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC08-40** Implement and verify **pressure signals** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC08-41** Implement and verify **cleanup** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC08-42** Write and verify resource controls in an order that cannot transiently escape configured limits; detect kernel rejection instead of assuming application.
- [ ] **MC08-43** Collect and interpret memory/OOM, PSI, CPU throttling, I/O pressure, and pids-exhaustion signals with workload attribution.
- [ ] **MC08-44** Test delegation boundaries and ensure controllers are not writable by workloads beyond the explicitly delegated subtree.
- [ ] **MC08-45** Mediate device discovery and assignment through policy; never trust a workload-provided host device path without broker validation.
- [ ] **MC08-46** Track device ownership/lease state durably enough to recover from workload or node failure without double assignment.
- [ ] **MC08-47** Test hotplug/removal, driver/runtime mismatch, reset behavior, mediated devices, and cleanup of device-specific state.

### Definition of done / evidence gate

- [ ] **MC08-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC08-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC08-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC08-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC08-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC09 — Container rootfs/mount policy

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** read-only roots, bind mounts, tmpfs, masked/read-only paths, propagation, recursive mount safety, and mount validation.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** rootfs.py (DEFAULT_MOUNTS, validate_bind_mount)  
> **Evidence:** `tests/test_rootfs.py`, `tests/integration/test_runc.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC09-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Container rootfs/mount policy**.
- [ ] **MC09-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC09-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC09-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC09-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC09-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC09-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC09-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC09-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC09-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC09-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC09-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC09-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC09-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC09-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC09-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC09-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC09-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC09-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC09-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC09-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC09-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC09-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC09-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC09-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC09-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC09-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC09-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC09-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC09-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC09-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC09-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC09-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC09-34** Implement and verify **read-only roots** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC09-35** Implement and verify **bind mounts** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC09-36** Implement and verify **tmpfs** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC09-37** Implement and verify **masked/read-only paths** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC09-38** Implement and verify **propagation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC09-39** Implement and verify **recursive mount safety** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC09-40** Implement and verify **mount validation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC09-41** Validate every mount source, target, propagation flag, filesystem type, and option against policy before performing privileged mount operations.
- [ ] **MC09-42** Test whiteout, opaque directory, copy-up, hardlink, symlink, xattr, ownership, and permission behavior against the selected snapshotter/filesystem matrix.
- [ ] **MC09-43** Guarantee teardown is idempotent and leak-resistant across process death, lazy/unexpected unmount conditions, and partially constructed snapshots.

### Definition of done / evidence gate

- [ ] **MC09-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC09-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC09-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC09-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC09-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC10 — Container networking integration

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** network namespace plumbing, veth lifecycle, IPAM, routes, DNS, service connectivity, and policy integration.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `partial`  
> **Implementation:** runtime.py (network modes none/loopback/netns/host-with-grant)  
> **Evidence:** `tests/test_runtime.py`  
> **Open:** CNI plugin invocation and IPAM


### Architecture & requirements

- [ ] **MC10-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Container networking integration**.
- [ ] **MC10-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC10-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC10-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC10-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC10-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC10-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC10-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC10-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC10-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC10-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC10-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC10-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC10-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC10-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC10-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC10-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC10-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC10-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC10-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC10-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC10-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC10-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC10-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC10-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC10-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC10-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC10-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC10-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC10-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC10-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC10-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC10-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC10-34** Implement and verify **network namespace plumbing** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC10-35** Implement and verify **veth lifecycle** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC10-36** Implement and verify **IPAM** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC10-37** Implement and verify **routes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC10-38** Implement and verify **service connectivity** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC10-39** Implement and verify **policy integration** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC10-40** Specify a finite-state machine for all lifecycle states and reject illegal transitions with stable, machine-readable error codes.
- [ ] **MC10-41** Make start/stop/delete operations idempotent under retries, controller failover, duplicate messages, and runtime/shim restarts.
- [ ] **MC10-42** Capture exit code, signal, OOM/limit cause, timestamps, and terminal metadata exactly once and make terminal state durable.
- [ ] **MC10-43** Validate namespace ownership and join/create semantics so a workload cannot attach to a more privileged namespace than policy permits.
- [ ] **MC10-44** Verify UID/GID mappings for gaps, overlap, host-root exposure, subordinate-ID exhaustion, and filesystem ownership translation.
- [ ] **MC10-45** Test namespace teardown and orphan cleanup after controller/runtime crashes and host reboot.
- [ ] **MC10-46** Treat network setup as a transaction with rollback of interfaces, addresses, routes, namespaces, firewall/policy state, and IPAM reservations.
- [ ] **MC10-47** Prevent route/address overlap, spoofing, host-network policy bypass, and cross-tenant namespace attachment.

### Definition of done / evidence gate

- [ ] **MC10-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC10-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC10-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC10-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC10-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC11 — Runtime storage/volume integration

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** volume lifecycle, ownership mapping, SELinux labeling where applicable, mount propagation, quotas, and detach/recovery.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** runtime.py (named volumes, binds)  
> **Evidence:** `tests/test_runtime.py`  
> **Open:** volume lifecycle/quotas


### Architecture & requirements

- [ ] **MC11-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Runtime storage/volume integration**.
- [ ] **MC11-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC11-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC11-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC11-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC11-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC11-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC11-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC11-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC11-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC11-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC11-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC11-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC11-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC11-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC11-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC11-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC11-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC11-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC11-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC11-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC11-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC11-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC11-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC11-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC11-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC11-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC11-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC11-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC11-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC11-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC11-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC11-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC11-34** Implement and verify **volume lifecycle** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC11-35** Implement and verify **ownership mapping** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC11-36** Implement and verify **SELinux labeling where applicable** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC11-37** Implement and verify **mount propagation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC11-38** Implement and verify **quotas** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC11-39** Implement and verify **detach/recovery** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC11-40** Validate every mount source, target, propagation flag, filesystem type, and option against policy before performing privileged mount operations.
- [ ] **MC11-41** Test whiteout, opaque directory, copy-up, hardlink, symlink, xattr, ownership, and permission behavior against the selected snapshotter/filesystem matrix.
- [ ] **MC11-42** Guarantee teardown is idempotent and leak-resistant across process death, lazy/unexpected unmount conditions, and partially constructed snapshots.
- [ ] **MC11-43** Specify a finite-state machine for all lifecycle states and reject illegal transitions with stable, machine-readable error codes.
- [ ] **MC11-44** Make start/stop/delete operations idempotent under retries, controller failover, duplicate messages, and runtime/shim restarts.
- [ ] **MC11-45** Capture exit code, signal, OOM/limit cause, timestamps, and terminal metadata exactly once and make terminal state durable.
- [ ] **MC11-46** Define attach/mount/unmount/detach state separately and reconcile leaked or ambiguous volume state after host or controller failure.
- [ ] **MC11-47** Verify ownership, idmapping, labeling, mount propagation, read-only enforcement, and quota application before workload access.

### Definition of done / evidence gate

- [ ] **MC11-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC11-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC11-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC11-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC11-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC12 — Process supervision

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** init/reaping behavior, stdio/log pipe ownership, exit status capture, orphan cleanup, and runtime-shim failure handling.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** runtime.py (Supervisor)  
> **Evidence:** `tests/test_runtime.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC12-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Process supervision**.
- [ ] **MC12-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC12-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC12-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC12-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC12-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC12-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC12-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC12-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC12-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC12-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC12-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC12-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC12-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC12-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC12-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC12-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC12-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC12-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC12-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC12-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC12-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC12-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC12-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC12-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC12-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC12-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC12-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC12-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC12-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC12-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC12-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC12-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC12-34** Implement and verify **init/reaping behavior** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC12-35** Implement and verify **stdio/log pipe ownership** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC12-36** Implement and verify **exit status capture** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC12-37** Implement and verify **orphan cleanup** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC12-38** Implement and verify **runtime-shim failure handling** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC12-39** Specify a finite-state machine for all lifecycle states and reject illegal transitions with stable, machine-readable error codes.
- [ ] **MC12-40** Make start/stop/delete operations idempotent under retries, controller failover, duplicate messages, and runtime/shim restarts.
- [ ] **MC12-41** Capture exit code, signal, OOM/limit cause, timestamps, and terminal metadata exactly once and make terminal state durable.

### Definition of done / evidence gate

- [ ] **MC12-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC12-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC12-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC12-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC12-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC13 — Image unpack/decompression pipeline

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** streamed decompression, digest verification during transfer/unpack, decompression-bomb limits, whiteout validation, and atomic commit.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** rootfs.py (apply_layer)  
> **Evidence:** `tests/test_rootfs.py`, `tests/test_fuzz_stress.py`  
> **Open:** zstd decompression (refused by design; needs external decoder)


### Architecture & requirements

- [ ] **MC13-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Image unpack/decompression pipeline**.
- [ ] **MC13-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC13-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC13-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC13-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC13-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC13-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC13-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC13-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC13-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC13-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC13-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC13-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC13-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC13-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC13-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC13-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC13-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC13-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC13-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC13-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC13-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC13-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC13-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC13-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC13-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC13-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC13-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC13-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC13-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC13-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC13-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC13-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC13-34** Implement and verify **streamed decompression** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC13-35** Implement and verify **digest verification during transfer/unpack** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC13-36** Implement and verify **decompression-bomb limits** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC13-37** Implement and verify **whiteout validation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC13-38** Implement and verify **atomic commit** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC13-39** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC13-40** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.
- [ ] **MC13-41** Verify layer digest before commit and ensure partial unpack trees cannot become visible as ready snapshots.

### Definition of done / evidence gate

- [ ] **MC13-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC13-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC13-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC13-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC13-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC14 — Multi-platform image selection

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** OS/architecture/variant matching and deterministic rejection of unsupported platform manifests.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** oci.py (select_platform)  
> **Evidence:** `tests/test_oci.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC14-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Multi-platform image selection**.
- [ ] **MC14-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC14-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC14-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC14-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC14-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC14-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC14-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC14-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC14-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC14-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC14-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC14-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC14-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC14-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC14-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC14-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC14-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC14-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC14-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC14-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC14-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC14-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC14-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC14-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC14-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC14-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC14-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC14-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC14-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC14-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC14-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC14-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC14-34** Implement and verify **OS/architecture/variant matching** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC14-35** Implement and verify **deterministic rejection of unsupported platform manifests** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC14-36** Normalize platform matching rules and make selection deterministic when multiple manifests appear equivalent.
- [ ] **MC14-37** Record the selected platform tuple and source manifest digest in durable metadata for reproducibility and incident analysis.
- [ ] **MC14-38** Reject unsupported OS/architecture/variant combinations before download/unpack work that cannot be used.

### Definition of done / evidence gate

- [ ] **MC14-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC14-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC14-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC14-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC14-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC15 — Container metadata/state database

**Priority:** P0  
**Domain:** Core container and OCI substrate  
**Missing capability:** durable image/container/task/snapshot metadata with transactional updates and migrations.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** store.py (meta.json), runtime.py (LifecycleStore)  
> **Evidence:** `tests/test_store.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC15-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Container metadata/state database**.
- [ ] **MC15-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC15-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC15-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC15-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC15-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC15-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC15-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC15-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC15-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC15-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC15-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC15-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC15-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC15-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC15-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC15-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC15-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC15-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC15-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC15-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC15-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC15-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC15-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC15-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC15-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC15-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC15-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC15-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC15-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC15-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC15-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC15-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC15-34** Implement and verify **durable image/container/task/snapshot metadata with transactional updates** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC15-35** Implement and verify **migrations** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC15-36** Validate every mount source, target, propagation flag, filesystem type, and option against policy before performing privileged mount operations.
- [ ] **MC15-37** Test whiteout, opaque directory, copy-up, hardlink, symlink, xattr, ownership, and permission behavior against the selected snapshotter/filesystem matrix.
- [ ] **MC15-38** Guarantee teardown is idempotent and leak-resistant across process death, lazy/unexpected unmount conditions, and partially constructed snapshots.
- [ ] **MC15-39** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC15-40** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC15-41** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.

### Definition of done / evidence gate

- [ ] **MC15-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC15-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC15-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC15-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC15-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC16 — Registry authentication provider

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** credential helpers, short-lived tokens, OIDC/workload identity, token refresh, scope minimization, and secret redaction.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** distribution.py (Bearer/Basic, CredentialProvider)  
> **Evidence:** `tests/test_distribution.py`  
> **Open:** keychain/credential-helper backed provider


### Architecture & requirements

- [ ] **MC16-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Registry authentication provider**.
- [ ] **MC16-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC16-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC16-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC16-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC16-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC16-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC16-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC16-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC16-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC16-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC16-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC16-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC16-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC16-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC16-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC16-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC16-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC16-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC16-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC16-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC16-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC16-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC16-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC16-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC16-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC16-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC16-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC16-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC16-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC16-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC16-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC16-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC16-34** Implement and verify **credential helpers** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC16-35** Implement and verify **short-lived tokens** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC16-36** Implement and verify **OIDC/workload identity** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC16-37** Implement and verify **token refresh** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC16-38** Implement and verify **scope minimization** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC16-39** Implement and verify **secret redaction** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC16-40** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC16-41** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC16-42** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC16-43** Represent credentials as scoped, expiring capabilities; avoid long-lived broad registry credentials in process environment or persisted logs.
- [ ] **MC16-44** Handle challenge/refresh races and token expiry without replaying credentials to an unintended registry or scope.
- [ ] **MC16-45** Redact authorization headers, tokens, helper output, and secret-derived values from logs, traces, crash dumps, and diagnostic bundles.
- [ ] **MC16-46** Keep secret material outside immutable image layers, content-addressable caches, command lines, environment dumps, and persistent logs.
- [ ] **MC16-47** Use atomic secret rotation with clear old/new overlap semantics and explicit revocation behavior for running workloads.

### Definition of done / evidence gate

- [ ] **MC16-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC16-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC16-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC16-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC16-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC17 — Transport security policy

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** CA trust policy, hostname verification, optional mTLS, TLS-version/cipher policy, proxy controls, and insecure-registry denial by default.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** distribution.py (TLSPolicy)  
> **Evidence:** `tests/test_distribution.py`  
> **Open:** mTLS client certificates


### Architecture & requirements

- [ ] **MC17-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Transport security policy**.
- [ ] **MC17-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC17-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC17-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC17-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC17-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC17-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC17-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC17-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC17-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC17-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC17-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC17-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC17-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC17-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC17-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC17-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC17-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC17-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC17-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC17-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC17-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC17-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC17-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC17-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC17-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC17-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC17-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC17-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC17-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC17-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC17-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC17-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC17-34** Implement and verify **CA trust policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC17-35** Implement and verify **hostname verification** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC17-36** Implement and verify **optional mTLS** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC17-37** Implement and verify **TLS-version/cipher policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC17-38** Implement and verify **proxy controls** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC17-39** Implement and verify **insecure-registry denial by default** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC17-40** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC17-41** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC17-42** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC17-43** Enforce certificate chain and hostname validation by default; insecure endpoints require an explicit, narrowly scoped, auditable exception.
- [ ] **MC17-44** Apply trust policy before sending credentials and prevent proxy/redirect behavior from downgrading transport guarantees.
- [ ] **MC17-45** Test certificate rotation, expiry, revocation/trust-store changes, clock skew, mTLS client rotation, and handshake failure telemetry.

### Definition of done / evidence gate

- [ ] **MC17-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC17-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC17-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC17-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC17-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC18 — Artifact signature verification

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** pluggable signature verification tied to resolved digests before admission/execution.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** trust.py (Ed25519, verify_signatures, image_signature_payload)  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** Sigstore/cosign bundle format interop


### Architecture & requirements

- [ ] **MC18-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Artifact signature verification**.
- [ ] **MC18-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC18-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC18-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC18-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC18-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC18-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC18-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC18-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC18-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC18-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC18-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC18-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC18-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC18-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC18-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC18-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC18-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC18-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC18-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC18-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC18-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC18-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC18-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC18-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC18-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC18-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC18-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC18-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC18-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC18-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC18-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC18-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC18-34** Implement and verify **pluggable signature verification tied to resolved digests before admission/execution** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC18-35** Bind every verification decision to the immutable artifact digest, verifier policy version, trusted root set, and verification timestamp.
- [ ] **MC18-36** Fail closed on malformed, ambiguous, expired, revoked, or policy-incompatible evidence when the workload class requires verified trust.
- [ ] **MC18-37** Persist verification evidence and decision rationale so later audits can reproduce the admission result without relying on mutable tags.

### Definition of done / evidence gate

- [ ] **MC18-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC18-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC18-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC18-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC18-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC19 — Provenance/attestation verification

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** SLSA/in-toto-style provenance or equivalent, builder identity checks, predicate policy, and trusted-root management.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** trust.py (DSSE, in-toto, SLSA)  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC19-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Provenance/attestation verification**.
- [ ] **MC19-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC19-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC19-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC19-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC19-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC19-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC19-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC19-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC19-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC19-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC19-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC19-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC19-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC19-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC19-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC19-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC19-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC19-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC19-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC19-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC19-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC19-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC19-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC19-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC19-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC19-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC19-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC19-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC19-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC19-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC19-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC19-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC19-34** Implement and verify **SLSA/in-toto-style provenance or equivalent** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC19-35** Implement and verify **builder identity checks** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC19-36** Implement and verify **predicate policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC19-37** Implement and verify **trusted-root management** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC19-38** Bind every verification decision to the immutable artifact digest, verifier policy version, trusted root set, and verification timestamp.
- [ ] **MC19-39** Fail closed on malformed, ambiguous, expired, revoked, or policy-incompatible evidence when the workload class requires verified trust.
- [ ] **MC19-40** Persist verification evidence and decision rationale so later audits can reproduce the admission result without relying on mutable tags.

### Definition of done / evidence gate

- [ ] **MC19-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC19-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC19-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC19-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC19-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC20 — SBOM ingestion and binding

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** SBOM discovery, digest binding, parsing, retention, and policy correlation.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** trust.py (ingest_sbom)  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC20-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **SBOM ingestion and binding**.
- [ ] **MC20-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC20-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC20-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC20-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC20-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC20-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC20-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC20-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC20-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC20-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC20-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC20-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC20-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC20-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC20-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC20-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC20-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC20-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC20-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC20-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC20-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC20-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC20-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC20-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC20-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC20-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC20-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC20-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC20-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC20-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC20-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC20-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC20-34** Implement and verify **SBOM discovery** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC20-35** Implement and verify **digest binding** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC20-36** Implement and verify **parsing** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC20-37** Implement and verify **retention** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC20-38** Implement and verify **policy correlation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC20-39** Bind SBOM/scanner results to exact image/artifact digests and record scanner database/version/freshness metadata.
- [ ] **MC20-40** Distinguish unscanned, scan-failed, scan-stale, vulnerability-present, and exception-approved states; do not collapse them into a boolean.
- [ ] **MC20-41** Exercise exception expiry and re-evaluation when scanner intelligence, exploitability data, or policy changes.

### Definition of done / evidence gate

- [ ] **MC20-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC20-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC20-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC20-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC20-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC21 — Vulnerability scanning/admission

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** scanner integration, severity/exploitability policy, freshness requirements, exception workflow, and fail-closed behavior where required.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `partial`  
> **Implementation:** trust.py (ScanState, scan_state), policy.py (vulnerabilities rule)  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** scanner integration (e.g. Trivy/Grype) producing ScanResult


### Architecture & requirements

- [ ] **MC21-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Vulnerability scanning/admission**.
- [ ] **MC21-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC21-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC21-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC21-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC21-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC21-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC21-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC21-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC21-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC21-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC21-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC21-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC21-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC21-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC21-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC21-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC21-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC21-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC21-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC21-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC21-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC21-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC21-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC21-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC21-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC21-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC21-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC21-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC21-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC21-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC21-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC21-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC21-34** Implement and verify **scanner integration** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC21-35** Implement and verify **severity/exploitability policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC21-36** Implement and verify **freshness requirements** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC21-37** Implement and verify **exception workflow** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC21-38** Implement and verify **fail-closed behavior where required** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC21-39** Bind SBOM/scanner results to exact image/artifact digests and record scanner database/version/freshness metadata.
- [ ] **MC21-40** Distinguish unscanned, scan-failed, scan-stale, vulnerability-present, and exception-approved states; do not collapse them into a boolean.
- [ ] **MC21-41** Exercise exception expiry and re-evaluation when scanner intelligence, exploitability data, or policy changes.

### Definition of done / evidence gate

- [ ] **MC21-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC21-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC21-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC21-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC21-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC22 — Seccomp profile enforcement

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** default-deny syscall policy, profile selection, validation, audit mode, and compatibility testing.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented+runtime-verified`  
> **Implementation:** runtime.py (seccomp_profile)  
> **Evidence:** `tests/test_runtime.py`, `tests/integration/test_runc.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC22-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Seccomp profile enforcement**.
- [ ] **MC22-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC22-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC22-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC22-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC22-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC22-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC22-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC22-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC22-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC22-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC22-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC22-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC22-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC22-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC22-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC22-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC22-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC22-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC22-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC22-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC22-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC22-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC22-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC22-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC22-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC22-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC22-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC22-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC22-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC22-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC22-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC22-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC22-34** Implement and verify **default-deny syscall policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC22-35** Implement and verify **profile selection** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC22-36** Implement and verify **validation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC22-37** Implement and verify **audit mode** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC22-38** Implement and verify **compatibility testing** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC22-39** Compute effective privilege from all interacting controls rather than validating each control in isolation; reject contradictory configurations.
- [ ] **MC22-40** Provide a secure baseline profile and a narrowly scoped compatibility override mechanism with owner, justification, expiry, and audit trail.
- [ ] **MC22-41** Test representative workloads for privilege escalation attempts, denied syscall/capability behavior, and informative operator telemetry.

### Definition of done / evidence gate

- [ ] **MC22-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC22-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC22-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC22-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC22-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC23 — Linux capability policy

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** drop-by-default capability sets, explicit grants, bounding/ambient-set controls, and validation.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented+runtime-verified`  
> **Implementation:** runtime.py (capability_set)  
> **Evidence:** `tests/test_runtime.py`, `tests/integration/test_runc.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC23-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Linux capability policy**.
- [ ] **MC23-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC23-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC23-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC23-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC23-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC23-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC23-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC23-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC23-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC23-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC23-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC23-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC23-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC23-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC23-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC23-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC23-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC23-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC23-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC23-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC23-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC23-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC23-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC23-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC23-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC23-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC23-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC23-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC23-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC23-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC23-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC23-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC23-34** Implement and verify **drop-by-default capability sets** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC23-35** Implement and verify **grants** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC23-36** Implement and verify **bounding/ambient-set controls** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC23-37** Implement and verify **validation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC23-38** Compute effective privilege from all interacting controls rather than validating each control in isolation; reject contradictory configurations.
- [ ] **MC23-39** Provide a secure baseline profile and a narrowly scoped compatibility override mechanism with owner, justification, expiry, and audit trail.
- [ ] **MC23-40** Test representative workloads for privilege escalation attempts, denied syscall/capability behavior, and informative operator telemetry.

### Definition of done / evidence gate

- [ ] **MC23-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC23-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC23-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC23-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC23-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC24 — User-namespace/rootless execution

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** UID/GID mapping, subordinate-ID management, idmapped mounts where supported, and rootless runtime constraints.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `partial`  
> **Implementation:** runtime.py (IDMap, subid_range, userns spec)  
> **Evidence:** `tests/test_runtime.py`, `tests/integration/test_runc.py`  
> **Open:** user-namespace container run skipped on this host (MS_PRIVATE denied)


### Architecture & requirements

- [ ] **MC24-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **User-namespace/rootless execution**.
- [ ] **MC24-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC24-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC24-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC24-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC24-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC24-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC24-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC24-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC24-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC24-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC24-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC24-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC24-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC24-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC24-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC24-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC24-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC24-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC24-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC24-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC24-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC24-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC24-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC24-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC24-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC24-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC24-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC24-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC24-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC24-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC24-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC24-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC24-34** Implement and verify **UID/GID mapping** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC24-35** Implement and verify **subordinate-ID management** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC24-36** Implement and verify **idmapped mounts where supported** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC24-37** Implement and verify **rootless runtime constraints** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC24-38** Validate namespace ownership and join/create semantics so a workload cannot attach to a more privileged namespace than policy permits.
- [ ] **MC24-39** Verify UID/GID mappings for gaps, overlap, host-root exposure, subordinate-ID exhaustion, and filesystem ownership translation.
- [ ] **MC24-40** Test namespace teardown and orphan cleanup after controller/runtime crashes and host reboot.

### Definition of done / evidence gate

- [ ] **MC24-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC24-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC24-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC24-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC24-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC25 — MAC integration

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** SELinux/AppArmor policy selection, labeling/profile loading, denial telemetry, and rollout compatibility.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented-spec`  
> **Implementation:** runtime.py (apparmorProfile, selinuxLabel)  
> **Evidence:** `tests/test_runtime.py`  
> **Open:** ship/load the inv02-default AppArmor profile; SELinux policy module


### Architecture & requirements

- [ ] **MC25-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **MAC integration**.
- [ ] **MC25-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC25-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC25-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC25-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC25-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC25-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC25-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC25-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC25-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC25-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC25-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC25-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC25-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC25-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC25-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC25-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC25-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC25-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC25-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC25-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC25-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC25-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC25-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC25-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC25-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC25-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC25-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC25-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC25-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC25-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC25-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC25-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC25-34** Implement and verify **SELinux/AppArmor policy selection** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC25-35** Implement and verify **labeling/profile loading** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC25-36** Implement and verify **denial telemetry** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC25-37** Implement and verify **rollout compatibility** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC25-38** Validate profile/label existence and loadability before workload start; do not silently fall back to unconfined execution.
- [ ] **MC25-39** Surface denials with workload identity, rule/profile context, and correlation identifiers without leaking secrets.
- [ ] **MC25-40** Test relabeling/profile rollout and rollback across persistent volumes and existing workloads.

### Definition of done / evidence gate

- [ ] **MC25-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC25-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC25-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC25-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC25-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC26 — No-new-privileges/setuid controls

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** enforcement against privilege amplification inside containers.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented+runtime-verified`  
> **Implementation:** runtime.py (noNewPrivileges); rootfs.py (setuid stripping)  
> **Evidence:** `tests/test_runtime.py`, `tests/test_rootfs.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC26-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **No-new-privileges/setuid controls**.
- [ ] **MC26-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC26-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC26-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC26-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC26-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC26-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC26-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC26-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC26-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC26-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC26-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC26-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC26-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC26-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC26-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC26-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC26-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC26-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC26-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC26-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC26-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC26-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC26-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC26-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC26-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC26-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC26-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC26-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC26-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC26-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC26-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC26-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC26-34** Implement and verify **enforcement against privilege amplification inside containers** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC26-35** Compute effective privilege from all interacting controls rather than validating each control in isolation; reject contradictory configurations.
- [ ] **MC26-36** Provide a secure baseline profile and a narrowly scoped compatibility override mechanism with owner, justification, expiry, and audit trail.
- [ ] **MC26-37** Test representative workloads for privilege escalation attempts, denied syscall/capability behavior, and informative operator telemetry.

### Definition of done / evidence gate

- [ ] **MC26-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC26-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC26-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC26-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC26-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC27 — Device access broker

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** explicit device allowlists, GPU/accelerator mediation, hotplug handling, ownership, and cleanup.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** runtime.py (DEFAULT_DEVICE_RULES, device grants)  
> **Evidence:** `tests/test_runtime.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC27-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Device access broker**.
- [ ] **MC27-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC27-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC27-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC27-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC27-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC27-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC27-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC27-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC27-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC27-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC27-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC27-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC27-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC27-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC27-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC27-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC27-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC27-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC27-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC27-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC27-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC27-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC27-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC27-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC27-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC27-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC27-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC27-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC27-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC27-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC27-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC27-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC27-34** Implement and verify **device allowlists** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC27-35** Implement and verify **GPU/accelerator mediation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC27-36** Implement and verify **hotplug handling** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC27-37** Implement and verify **ownership** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC27-38** Implement and verify **cleanup** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC27-39** Mediate device discovery and assignment through policy; never trust a workload-provided host device path without broker validation.
- [ ] **MC27-40** Track device ownership/lease state durably enough to recover from workload or node failure without double assignment.
- [ ] **MC27-41** Test hotplug/removal, driver/runtime mismatch, reset behavior, mediated devices, and cleanup of device-specific state.

### Definition of done / evidence gate

- [ ] **MC27-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC27-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC27-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC27-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC27-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC28 — Secrets isolation

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** tmpfs/in-memory secret delivery, rotation, revocation, no-image/no-log guarantees, and teardown scrubbing.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented+runtime-verified`  
> **Implementation:** runtime.py (write_secrets, /run/secrets mount, secret-env refusal)  
> **Evidence:** `tests/test_runtime.py`, `tests/integration/test_runc.py`  
> **Open:** tmpfs-backed secrets dir provisioning


### Architecture & requirements

- [ ] **MC28-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Secrets isolation**.
- [ ] **MC28-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC28-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC28-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC28-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC28-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC28-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC28-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC28-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC28-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC28-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC28-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC28-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC28-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC28-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC28-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC28-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC28-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC28-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC28-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC28-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC28-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC28-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC28-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC28-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC28-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC28-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC28-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC28-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC28-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC28-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC28-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC28-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC28-34** Implement and verify **tmpfs/in-memory secret delivery** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC28-35** Implement and verify **rotation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC28-36** Implement and verify **revocation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC28-37** Implement and verify **no-image/no-log guarantees** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC28-38** Implement and verify **teardown scrubbing** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC28-39** Write and verify resource controls in an order that cannot transiently escape configured limits; detect kernel rejection instead of assuming application.
- [ ] **MC28-40** Collect and interpret memory/OOM, PSI, CPU throttling, I/O pressure, and pids-exhaustion signals with workload attribution.
- [ ] **MC28-41** Test delegation boundaries and ensure controllers are not writable by workloads beyond the explicitly delegated subtree.
- [ ] **MC28-42** Keep secret material outside immutable image layers, content-addressable caches, command lines, environment dumps, and persistent logs.
- [ ] **MC28-43** Use atomic secret rotation with clear old/new overlap semantics and explicit revocation behavior for running workloads.
- [ ] **MC28-44** Verify teardown scrubbing and access revocation under normal exit, crash, forced kill, and node recovery.

### Definition of done / evidence gate

- [ ] **MC28-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC28-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC28-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC28-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC28-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC29 — Tenant/workload isolation policy

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** explicit trust domains and rules for namespace, storage, network, device, cache, and metadata sharing.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** policy.py (rule_tenant_isolation)  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC29-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Tenant/workload isolation policy**.
- [ ] **MC29-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC29-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC29-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC29-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC29-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC29-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC29-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC29-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC29-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC29-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC29-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC29-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC29-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC29-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC29-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC29-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC29-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC29-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC29-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC29-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC29-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC29-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC29-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC29-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC29-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC29-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC29-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC29-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC29-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC29-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC29-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC29-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC29-34** Implement and verify **trust domains** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC29-35** Implement and verify **rules for namespace** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC29-36** Implement and verify **storage** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC29-37** Implement and verify **network** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC29-38** Implement and verify **device** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC29-39** Implement and verify **cache** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC29-40** Implement and verify **metadata sharing** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC29-41** Validate namespace ownership and join/create semantics so a workload cannot attach to a more privileged namespace than policy permits.
- [ ] **MC29-42** Verify UID/GID mappings for gaps, overlap, host-root exposure, subordinate-ID exhaustion, and filesystem ownership translation.
- [ ] **MC29-43** Test namespace teardown and orphan cleanup after controller/runtime crashes and host reboot.
- [ ] **MC29-44** Treat network setup as a transaction with rollback of interfaces, addresses, routes, namespaces, firewall/policy state, and IPAM reservations.
- [ ] **MC29-45** Prevent route/address overlap, spoofing, host-network policy bypass, and cross-tenant namespace attachment.
- [ ] **MC29-46** Verify DNS configuration and search-domain behavior under namespace recreation, resolver failure, and policy changes.
- [ ] **MC29-47** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC29-48** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.

### Definition of done / evidence gate

- [ ] **MC29-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC29-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC29-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC29-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC29-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC30 — Durable quarantine/admission store

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** authoritative quarantine state shared across nodes/controllers, not the current process-local dictionary.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** store.py (quarantine/release, two-person release)  
> **Evidence:** `tests/test_store.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC30-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Durable quarantine/admission store**.
- [ ] **MC30-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC30-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC30-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC30-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC30-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC30-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC30-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC30-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC30-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC30-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC30-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC30-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC30-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC30-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC30-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC30-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC30-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC30-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC30-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC30-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC30-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC30-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC30-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC30-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC30-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC30-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC30-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC30-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC30-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC30-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC30-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC30-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC30-34** Implement and verify **authoritative quarantine state shared across nodes/controllers,** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC30-35** Represent quarantine as authoritative durable state keyed by immutable digest plus policy scope, reason, actor, timestamps, and expiry/review fields.
- [ ] **MC30-36** Ensure quarantined content cannot be admitted via alternate tags, mirrors, caches, or stale local metadata.
- [ ] **MC30-37** Require explicit audited release/unquarantine transitions and re-verification when policy/evidence changed.

### Definition of done / evidence gate

- [ ] **MC30-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC30-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC30-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC30-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC30-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC31 — Tamper-evident audit ledger

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** append-only/security-protected events for pushes, tag moves, resolutions, verification failures, quarantine actions, and policy decisions.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** audit.py  
> **Evidence:** `tests/test_ops.py`  
> **Open:** external anchoring of the head hash (remote log/WORM)


### Architecture & requirements

- [ ] **MC31-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Tamper-evident audit ledger**.
- [ ] **MC31-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC31-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC31-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC31-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC31-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC31-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC31-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC31-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC31-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC31-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC31-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC31-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC31-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC31-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC31-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC31-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC31-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC31-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC31-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC31-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC31-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC31-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC31-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC31-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC31-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC31-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC31-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC31-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC31-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC31-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC31-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC31-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC31-34** Implement and verify **append-only/security-protected events for pushes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC31-35** Implement and verify **tag moves** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC31-36** Implement and verify **resolutions** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC31-37** Implement and verify **verification failures** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC31-38** Implement and verify **quarantine actions** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC31-39** Implement and verify **policy decisions** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC31-40** Represent quarantine as authoritative durable state keyed by immutable digest plus policy scope, reason, actor, timestamps, and expiry/review fields.
- [ ] **MC31-41** Ensure quarantined content cannot be admitted via alternate tags, mirrors, caches, or stale local metadata.
- [ ] **MC31-42** Require explicit audited release/unquarantine transitions and re-verification when policy/evidence changed.
- [ ] **MC31-43** Use append-only semantics with integrity chaining/signing or equivalent protection sufficient to detect deletion, reordering, and mutation.
- [ ] **MC31-44** Include actor, workload/tenant, operation, immutable digest/reference, policy version, decision, and correlation identifiers in security-relevant events.
- [ ] **MC31-45** Define retention, export, access control, clock/timestamp trust, and evidence-preservation procedures.

### Definition of done / evidence gate

- [ ] **MC31-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC31-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC31-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC31-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC31-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC32 — Security policy engine integration

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** externalized, versioned policy decisions instead of only local immutable-environment settings.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented`  
> **Implementation:** policy.py (PolicyEngine)  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** OPA/Rego interop (optional)


### Architecture & requirements

- [ ] **MC32-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Security policy engine integration**.
- [ ] **MC32-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC32-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC32-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC32-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC32-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC32-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC32-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC32-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC32-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC32-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC32-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC32-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC32-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC32-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC32-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC32-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC32-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC32-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC32-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC32-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC32-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC32-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC32-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC32-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC32-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC32-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC32-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC32-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC32-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC32-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC32-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC32-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC32-34** Implement and verify **externalized** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC32-35** Implement and verify **versioned policy decisions instead of only local immutable-environment settings** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC32-36** Version policy bundles and evaluation inputs so a decision can be reproduced exactly after policies evolve.
- [ ] **MC32-37** Define fail-open/fail-closed behavior per operation and workload class for policy-engine outage, timeout, malformed response, and version skew.
- [ ] **MC32-38** Cache decisions only with explicit scope, TTL/invalidation rules, and immutable input binding.

### Definition of done / evidence gate

- [ ] **MC32-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC32-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC32-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC32-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC32-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC33 — Sandboxed-runtime option

**Priority:** P0  
**Domain:** Security, trust, and isolation  
**Missing capability:** policy-driven integration with stronger isolation technologies where threat models require it.

**Priority gate:** Release-blocking: the component must be implemented and certified before the substrate is considered production-capable for workloads that depend on it.

> **v5.0.0 status:** `implemented-spec`  
> **Implementation:** runtime.py (RUNTIME_CLASSES, SANDBOXED_CLASSES)  
> **Evidence:** `tests/test_runtime.py`  
> **Open:** runsc/kata execution tests


### Architecture & requirements

- [ ] **MC33-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Sandboxed-runtime option**.
- [ ] **MC33-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC33-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC33-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC33-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC33-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC33-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC33-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC33-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC33-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC33-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC33-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC33-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC33-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC33-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC33-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC33-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC33-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC33-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC33-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC33-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC33-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC33-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC33-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC33-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC33-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC33-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC33-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC33-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC33-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC33-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC33-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC33-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC33-34** Implement and verify **policy-driven integration with stronger isolation technologies where threat models require it** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC33-35** Define workload classes that require stronger isolation and enforce runtime selection as admission policy, not a best-effort hint.
- [ ] **MC33-36** Verify feature compatibility and security boundaries of the sandbox runtime independently from the standard runtime path.
- [ ] **MC33-37** Test fallback behavior so sandbox startup failure cannot silently degrade to a weaker runtime.

### Definition of done / evidence gate

- [ ] **MC33-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC33-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC33-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC33-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC33-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC34 — Compare-and-swap tag updates

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** optimistic concurrency/ETag-style protection so concurrent publishers cannot silently overwrite one another.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** store.py (set_tag expected=)  
> **Evidence:** `tests/test_store.py`, `tests/test_fuzz_stress.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC34-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Compare-and-swap tag updates**.
- [ ] **MC34-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC34-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC34-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC34-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC34-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC34-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC34-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC34-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC34-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC34-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC34-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC34-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC34-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC34-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC34-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC34-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC34-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC34-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC34-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC34-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC34-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC34-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC34-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC34-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC34-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC34-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC34-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC34-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC34-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC34-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC34-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC34-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC34-34** Implement and verify **optimistic concurrency/ETag-style protection so concurrent publishers cannot silently overwrite one another** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC34-35** Require callers to provide the expected prior tag state/version and atomically reject stale writes.
- [ ] **MC34-36** Return conflict metadata sufficient for safe client reconciliation without exposing unrelated tenant state.
- [ ] **MC34-37** Stress concurrent publishers and failover to prove there is no lost-update window.

### Definition of done / evidence gate

- [ ] **MC34-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC34-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC34-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC34-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC34-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC35 — Distributed locking/lease semantics

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** safe multi-process/multi-node ownership for downloads, unpack, GC, snapshots, and metadata mutation.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `partial`  
> **Implementation:** store.py (fcntl lock, leases)  
> **Evidence:** `tests/test_fuzz_stress.py`  
> **Open:** multi-node distributed lock/lease service


### Architecture & requirements

- [ ] **MC35-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Distributed locking/lease semantics**.
- [ ] **MC35-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC35-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC35-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC35-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC35-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC35-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC35-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC35-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC35-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC35-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC35-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC35-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC35-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC35-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC35-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC35-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC35-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC35-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC35-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC35-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC35-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC35-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC35-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC35-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC35-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC35-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC35-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC35-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC35-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC35-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC35-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC35-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC35-34** Implement and verify **safe multi-process/multi-node ownership for downloads** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC35-35** Implement and verify **unpack** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC35-36** Implement and verify **snapshots** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC35-37** Implement and verify **metadata mutation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC35-38** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC35-39** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.
- [ ] **MC35-40** Verify layer digest before commit and ensure partial unpack trees cannot become visible as ready snapshots.
- [ ] **MC35-41** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC35-42** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC35-43** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.
- [ ] **MC35-44** Use fencing tokens/epochs or equivalent protection so a paused or partitioned former owner cannot mutate state after lease loss.
- [ ] **MC35-45** Define lease TTL, renewal, grace, abandonment, and clock assumptions; avoid correctness that depends on synchronized wall clocks where possible.

### Definition of done / evidence gate

- [ ] **MC35-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC35-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC35-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC35-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC35-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC36 — Resumable blob transfer manager

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** partial-download checkpoints, range validation, digest continuity, retry budgeting, and stale-part cleanup.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** store.py (ingest_*); distribution.py (Range resume)  
> **Evidence:** `tests/test_store.py`, `tests/test_distribution.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC36-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Resumable blob transfer manager**.
- [ ] **MC36-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC36-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC36-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC36-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC36-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC36-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC36-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC36-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC36-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC36-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC36-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC36-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC36-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC36-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC36-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC36-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC36-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC36-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC36-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC36-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC36-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC36-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC36-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC36-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC36-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC36-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC36-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC36-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC36-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC36-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC36-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC36-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC36-34** Implement and verify **partial-download checkpoints** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC36-35** Implement and verify **range validation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC36-36** Implement and verify **digest continuity** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC36-37** Implement and verify **retry budgeting** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC36-38** Implement and verify **stale-part cleanup** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC36-39** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC36-40** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC36-41** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC36-42** Propagate a single operation budget across nested calls so retries cannot exceed the caller deadline.
- [ ] **MC36-43** Classify errors into retryable, non-retryable, and retry-after categories; cap attempts and total elapsed retry budget.
- [ ] **MC36-44** Use monotonic clocks for elapsed-time decisions and injectable time sources for deterministic tests.

### Definition of done / evidence gate

- [ ] **MC36-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC36-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC36-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC36-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC36-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC37 — Content leases and garbage collection

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** prevent deletion of blobs/snapshots still referenced by images, containers, or in-flight pulls.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** store.py (lease, gc)  
> **Evidence:** `tests/test_store.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC37-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Content leases and garbage collection**.
- [ ] **MC37-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC37-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC37-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC37-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC37-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC37-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC37-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC37-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC37-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC37-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC37-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC37-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC37-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC37-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC37-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC37-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC37-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC37-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC37-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC37-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC37-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC37-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC37-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC37-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC37-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC37-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC37-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC37-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC37-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC37-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC37-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC37-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC37-34** Implement and verify **prevent deletion of blobs/snapshots still referenced by images** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC37-35** Implement and verify **containers** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC37-36** Implement and verify **or in-flight pulls** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC37-37** Use atomic publish semantics for content: write to an isolated temporary object, fsync according to policy, verify digest, then make the blob discoverable.
- [ ] **MC37-38** Ensure garbage collection computes reachability from authoritative roots and honors active leases, in-flight operations, and crash-recovery markers.
- [ ] **MC37-39** Detect hash/path/index divergence and provide a repair path that never converts corrupt bytes into a trusted object.

### Definition of done / evidence gate

- [ ] **MC37-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC37-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC37-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC37-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC37-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC38 — Corruption repair workflow

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** detect, quarantine, re-fetch, verify, and atomically replace corrupt local content with operator-visible evidence.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** store.py (fsck, repair)  
> **Evidence:** `tests/test_store.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC38-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Corruption repair workflow**.
- [ ] **MC38-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC38-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC38-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC38-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC38-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC38-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC38-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC38-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC38-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC38-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC38-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC38-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC38-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC38-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC38-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC38-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC38-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC38-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC38-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC38-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC38-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC38-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC38-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC38-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC38-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC38-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC38-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC38-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC38-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC38-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC38-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC38-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC38-34** Implement and verify **detect** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC38-35** Implement and verify **quarantine** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC38-36** Implement and verify **re-fetch** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC38-37** Implement and verify **verify** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC38-38** Implement and verify **atomically replace corrupt local content with operator-visible evidence** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC38-39** Represent quarantine as authoritative durable state keyed by immutable digest plus policy scope, reason, actor, timestamps, and expiry/review fields.
- [ ] **MC38-40** Ensure quarantined content cannot be admitted via alternate tags, mirrors, caches, or stale local metadata.
- [ ] **MC38-41** Require explicit audited release/unquarantine transitions and re-verification when policy/evidence changed.

### Definition of done / evidence gate

- [ ] **MC38-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC38-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC38-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC38-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC38-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC39 — Registry mirror/fallback support

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** ordered mirrors, trust-equivalence policy, digest consistency checks, and failover without tag drift.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** distribution.py (mirrors, digest-only)  
> **Evidence:** `tests/test_distribution.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC39-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Registry mirror/fallback support**.
- [ ] **MC39-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC39-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC39-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC39-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC39-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC39-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC39-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC39-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC39-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC39-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC39-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC39-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC39-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC39-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC39-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC39-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC39-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC39-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC39-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC39-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC39-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC39-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC39-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC39-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC39-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC39-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC39-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC39-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC39-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC39-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC39-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC39-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC39-34** Implement and verify **ordered mirrors** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC39-35** Implement and verify **trust-equivalence policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC39-36** Implement and verify **digest consistency checks** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC39-37** Implement and verify **failover without tag drift** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC39-38** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC39-39** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC39-40** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.

### Definition of done / evidence gate

- [ ] **MC39-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC39-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC39-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC39-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC39-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC40 — Disconnected/offline cache mode

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** explicit stale-data policy, pre-seeding, pinned-digest operation, reconnect reconciliation, and storage-pressure behavior.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** distribution.py (offline)  
> **Evidence:** `tests/test_distribution.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC40-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Disconnected/offline cache mode**.
- [ ] **MC40-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC40-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC40-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC40-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC40-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC40-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC40-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC40-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC40-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC40-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC40-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC40-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC40-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC40-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC40-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC40-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC40-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC40-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC40-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC40-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC40-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC40-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC40-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC40-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC40-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC40-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC40-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC40-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC40-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC40-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC40-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC40-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC40-34** Implement and verify **stale-data policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC40-35** Implement and verify **pre-seeding** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC40-36** Implement and verify **pinned-digest operation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC40-37** Implement and verify **reconnect reconciliation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC40-38** Implement and verify **storage-pressure behavior** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC40-39** Write and verify resource controls in an order that cannot transiently escape configured limits; detect kernel rejection instead of assuming application.
- [ ] **MC40-40** Collect and interpret memory/OOM, PSI, CPU throttling, I/O pressure, and pids-exhaustion signals with workload attribution.
- [ ] **MC40-41** Test delegation boundaries and ensure controllers are not writable by workloads beyond the explicitly delegated subtree.
- [ ] **MC40-42** Define which operations are legal without connectivity and require immutable pinned digests for any workload whose tag freshness cannot be proven.
- [ ] **MC40-43** Track cache provenance/freshness and reconcile local decisions against authoritative policy/registry state after reconnect.
- [ ] **MC40-44** Test prolonged offline operation under storage pressure, expired credentials/evidence, and partial pre-seeding.

### Definition of done / evidence gate

- [ ] **MC40-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC40-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC40-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC40-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC40-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC41 — Rate limits and quotas

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** per-tenant/workload/node transfer, storage, concurrent pull, unpack, and metadata limits.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** resilience.py (TokenBucket, QuotaManager)  
> **Evidence:** `tests/test_ops.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC41-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Rate limits and quotas**.
- [ ] **MC41-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC41-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC41-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC41-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC41-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC41-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC41-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC41-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC41-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC41-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC41-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC41-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC41-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC41-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC41-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC41-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC41-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC41-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC41-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC41-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC41-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC41-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC41-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC41-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC41-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC41-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC41-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC41-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC41-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC41-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC41-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC41-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC41-34** Implement and verify **per-tenant/workload/node transfer** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC41-35** Implement and verify **storage** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC41-36** Implement and verify **concurrent pull** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC41-37** Implement and verify **unpack** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC41-38** Implement and verify **metadata limits** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC41-39** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC41-40** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.
- [ ] **MC41-41** Verify layer digest before commit and ensure partial unpack trees cannot become visible as ready snapshots.
- [ ] **MC41-42** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC41-43** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC41-44** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.
- [ ] **MC41-45** Define which caches, namespaces, networks, devices, metadata, and storage may be shared across each trust boundary; default to non-sharing where uncertain.
- [ ] **MC41-46** Attach tenant/workload identity to every state mutation and authorization decision and prevent identity confusion across asynchronous operations.

### Definition of done / evidence gate

- [ ] **MC41-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC41-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC41-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC41-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC41-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC42 — Backpressure/admission control

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** bounded queues and rejection/load-shedding behavior under disk, CPU, memory, network, or registry saturation.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** resilience.py (AdmissionController)  
> **Evidence:** `tests/test_ops.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC42-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Backpressure/admission control**.
- [ ] **MC42-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC42-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC42-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC42-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC42-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC42-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC42-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC42-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC42-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC42-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC42-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC42-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC42-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC42-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC42-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC42-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC42-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC42-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC42-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC42-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC42-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC42-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC42-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC42-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC42-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC42-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC42-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC42-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC42-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC42-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC42-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC42-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC42-34** Implement and verify **bounded queues** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC42-35** Implement and verify **rejection/load-shedding behavior under disk** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC42-36** Implement and verify **memory** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC42-37** Implement and verify **network** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC42-38** Implement and verify **or registry saturation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC42-39** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC42-40** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC42-41** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC42-42** Write and verify resource controls in an order that cannot transiently escape configured limits; detect kernel rejection instead of assuming application.
- [ ] **MC42-43** Collect and interpret memory/OOM, PSI, CPU throttling, I/O pressure, and pids-exhaustion signals with workload attribution.
- [ ] **MC42-44** Test delegation boundaries and ensure controllers are not writable by workloads beyond the explicitly delegated subtree.
- [ ] **MC42-45** Treat network setup as a transaction with rollback of interfaces, addresses, routes, namespaces, firewall/policy state, and IPAM reservations.
- [ ] **MC42-46** Prevent route/address overlap, spoofing, host-network policy bypass, and cross-tenant namespace attachment.

### Definition of done / evidence gate

- [ ] **MC42-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC42-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC42-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC42-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC42-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC43 — Retry/circuit-breaker library

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** bounded exponential backoff with jitter, retry classification, deadline propagation, and dependency circuit state.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** resilience.py (retry, CircuitBreaker)  
> **Evidence:** `tests/test_ops.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC43-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Retry/circuit-breaker library**.
- [ ] **MC43-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC43-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC43-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC43-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC43-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC43-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC43-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC43-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC43-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC43-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC43-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC43-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC43-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC43-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC43-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC43-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC43-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC43-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC43-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC43-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC43-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC43-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC43-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC43-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC43-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC43-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC43-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC43-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC43-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC43-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC43-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC43-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC43-34** Implement and verify **bounded exponential backoff with jitter** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC43-35** Implement and verify **retry classification** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC43-36** Implement and verify **deadline propagation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC43-37** Implement and verify **dependency circuit state** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC43-38** Propagate a single operation budget across nested calls so retries cannot exceed the caller deadline.
- [ ] **MC43-39** Classify errors into retryable, non-retryable, and retry-after categories; cap attempts and total elapsed retry budget.
- [ ] **MC43-40** Use monotonic clocks for elapsed-time decisions and injectable time sources for deterministic tests.

### Definition of done / evidence gate

- [ ] **MC43-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC43-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC43-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC43-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC43-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC44 — Time/deadline abstraction

**Priority:** P1  
**Domain:** Registry/content correctness and concurrency  
**Missing capability:** monotonic deadlines, cancellation propagation, timeout budgets, and deterministic testing hooks.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** timeutil.py  
> **Evidence:** `tests/test_ops.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC44-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Time/deadline abstraction**.
- [ ] **MC44-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC44-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC44-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC44-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC44-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC44-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC44-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC44-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC44-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC44-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC44-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC44-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC44-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC44-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC44-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC44-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC44-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC44-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC44-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC44-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC44-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC44-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC44-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC44-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC44-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC44-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC44-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC44-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC44-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC44-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC44-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC44-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC44-34** Implement and verify **monotonic deadlines** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC44-35** Implement and verify **cancellation propagation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC44-36** Implement and verify **timeout budgets** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC44-37** Implement and verify **deterministic testing hooks** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC44-38** Propagate a single operation budget across nested calls so retries cannot exceed the caller deadline.
- [ ] **MC44-39** Classify errors into retryable, non-retryable, and retry-after categories; cap attempts and total elapsed retry budget.
- [ ] **MC44-40** Use monotonic clocks for elapsed-time decisions and injectable time sources for deterministic tests.

### Definition of done / evidence gate

- [ ] **MC44-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC44-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC44-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC44-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC44-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC45 — Structured metrics exporter

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** pull latency/throughput, cache hit rate, bytes saved, verification failures, tag refusals, saturation, GC, and error classes.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** observability.py (Metrics)  
> **Evidence:** `tests/test_ops.py`  
> **Open:** wire metrics into every component call site


### Architecture & requirements

- [ ] **MC45-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Structured metrics exporter**.
- [ ] **MC45-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC45-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC45-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC45-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC45-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC45-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC45-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC45-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC45-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC45-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC45-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC45-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC45-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC45-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC45-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC45-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC45-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC45-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC45-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC45-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC45-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC45-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC45-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC45-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC45-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC45-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC45-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC45-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC45-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC45-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC45-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC45-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC45-34** Implement and verify **pull latency/throughput** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC45-35** Implement and verify **cache hit rate** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC45-36** Implement and verify **bytes saved** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC45-37** Implement and verify **verification failures** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC45-38** Implement and verify **tag refusals** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC45-39** Implement and verify **saturation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC45-40** Implement and verify **error classes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC45-41** Define low-cardinality metric labels and guard against unbounded tag/digest/tenant values becoming metric dimensions.
- [ ] **MC45-42** Standardize correlation fields across logs, traces, metrics exemplars, audit events, and operator-facing diagnostics.
- [ ] **MC45-43** Verify telemetry failure cannot block critical lifecycle operations and that backpressure/drop behavior is visible.

### Definition of done / evidence gate

- [ ] **MC45-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC45-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC45-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC45-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC45-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC46 — Structured logging pipeline

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** stable operation/request/node/tenant/workload identifiers and strict secret/token redaction.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** observability.py (JsonFormatter, redact)  
> **Evidence:** `tests/test_ops.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC46-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Structured logging pipeline**.
- [ ] **MC46-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC46-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC46-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC46-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC46-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC46-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC46-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC46-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC46-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC46-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC46-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC46-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC46-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC46-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC46-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC46-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC46-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC46-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC46-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC46-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC46-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC46-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC46-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC46-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC46-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC46-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC46-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC46-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC46-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC46-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC46-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC46-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC46-34** Implement and verify **stable operation/request/node/tenant/workload identifiers** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC46-35** Implement and verify **strict secret/token redaction** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC46-36** Represent credentials as scoped, expiring capabilities; avoid long-lived broad registry credentials in process environment or persisted logs.
- [ ] **MC46-37** Handle challenge/refresh races and token expiry without replaying credentials to an unintended registry or scope.
- [ ] **MC46-38** Redact authorization headers, tokens, helper output, and secret-derived values from logs, traces, crash dumps, and diagnostic bundles.
- [ ] **MC46-39** Keep secret material outside immutable image layers, content-addressable caches, command lines, environment dumps, and persistent logs.
- [ ] **MC46-40** Use atomic secret rotation with clear old/new overlap semantics and explicit revocation behavior for running workloads.
- [ ] **MC46-41** Verify teardown scrubbing and access revocation under normal exit, crash, forced kill, and node recovery.
- [ ] **MC46-42** Define which caches, namespaces, networks, devices, metadata, and storage may be shared across each trust boundary; default to non-sharing where uncertain.
- [ ] **MC46-43** Attach tenant/workload identity to every state mutation and authorization decision and prevent identity confusion across asynchronous operations.

### Definition of done / evidence gate

- [ ] **MC46-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC46-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC46-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC46-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC46-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC47 — Distributed tracing

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** trace context over registry, policy, signature, metadata, unpack, and runtime boundaries.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** observability.py (Tracer)  
> **Evidence:** `tests/test_ops.py`  
> **Open:** OTLP exporter


### Architecture & requirements

- [ ] **MC47-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Distributed tracing**.
- [ ] **MC47-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC47-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC47-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC47-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC47-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC47-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC47-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC47-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC47-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC47-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC47-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC47-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC47-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC47-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC47-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC47-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC47-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC47-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC47-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC47-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC47-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC47-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC47-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC47-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC47-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC47-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC47-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC47-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC47-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC47-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC47-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC47-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC47-34** Implement and verify **trace context over registry** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC47-35** Implement and verify **policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC47-36** Implement and verify **signature** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC47-37** Implement and verify **metadata** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC47-38** Implement and verify **unpack** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC47-39** Implement and verify **runtime boundaries** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC47-40** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC47-41** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC47-42** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC47-43** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC47-44** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.
- [ ] **MC47-45** Verify layer digest before commit and ensure partial unpack trees cannot become visible as ready snapshots.
- [ ] **MC47-46** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC47-47** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.

### Definition of done / evidence gate

- [ ] **MC47-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC47-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC47-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC47-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC47-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC48 — Health/readiness endpoints

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** content-store, registry, policy, signer/verifier, snapshotter, runtime, and disk-pressure status.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** observability.py (Health, serve_http)  
> **Evidence:** `tests/test_ops.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC48-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Health/readiness endpoints**.
- [ ] **MC48-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC48-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC48-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC48-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC48-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC48-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC48-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC48-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC48-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC48-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC48-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC48-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC48-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC48-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC48-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC48-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC48-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC48-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC48-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC48-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC48-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC48-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC48-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC48-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC48-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC48-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC48-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC48-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC48-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC48-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC48-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC48-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC48-34** Implement and verify **content-store** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC48-35** Implement and verify **registry** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC48-36** Implement and verify **policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC48-37** Implement and verify **signer/verifier** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC48-38** Implement and verify **snapshotter** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC48-39** Implement and verify **runtime** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC48-40** Implement and verify **disk-pressure status** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC48-41** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC48-42** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC48-43** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC48-44** Write and verify resource controls in an order that cannot transiently escape configured limits; detect kernel rejection instead of assuming application.
- [ ] **MC48-45** Collect and interpret memory/OOM, PSI, CPU throttling, I/O pressure, and pids-exhaustion signals with workload attribution.
- [ ] **MC48-46** Test delegation boundaries and ensure controllers are not writable by workloads beyond the explicitly delegated subtree.
- [ ] **MC48-47** Separate liveness from readiness and dependency health; do not restart healthy processes merely because an external dependency is unavailable.
- [ ] **MC48-48** Return dependency-specific degraded states and reasons suitable for automation without disclosing credentials or sensitive internals.

### Definition of done / evidence gate

- [ ] **MC48-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC48-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC48-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC48-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC48-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC49 — Decision explain API

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** operator-readable explanation for why a reference was accepted/refused/quarantined and which policy/evidence caused it.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** policy.py (Decision.explain)  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC49-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Decision explain API**.
- [ ] **MC49-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC49-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC49-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC49-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC49-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC49-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC49-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC49-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC49-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC49-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC49-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC49-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC49-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC49-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC49-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC49-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC49-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC49-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC49-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC49-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC49-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC49-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC49-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC49-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC49-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC49-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC49-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC49-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC49-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC49-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC49-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC49-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC49-34** Implement and verify **operator-readable explanation for why a reference was accepted/refused/quarantined** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC49-35** Implement and verify **which policy/evidence caused it** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Definition of done / evidence gate

- [ ] **MC49-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC49-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC49-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC49-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC49-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC50 — Dashboards and alerts

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** ordinary load vs. registry outage, corruption, policy rejection, disk pressure, attack indicators, and software defects.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `documented`  
> **Implementation:** docs/operations/OPERATIONS.md §1; docs/operations/alerts.yaml  
> **Evidence:** —  
> **Open:** deploy dashboards; validate alerts in a production-like environment


### Architecture & requirements

- [ ] **MC50-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Dashboards and alerts**.
- [ ] **MC50-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC50-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC50-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC50-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC50-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC50-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC50-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC50-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC50-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC50-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC50-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC50-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC50-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC50-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC50-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC50-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC50-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC50-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC50-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC50-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC50-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC50-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC50-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC50-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC50-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC50-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC50-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC50-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC50-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC50-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC50-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC50-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC50-34** Implement and verify **ordinary load vs. registry outage** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC50-35** Implement and verify **corruption** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC50-36** Implement and verify **policy rejection** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC50-37** Implement and verify **disk pressure** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC50-38** Implement and verify **attack indicators** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC50-39** Implement and verify **software defects** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC50-40** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC50-41** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC50-42** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC50-43** Write and verify resource controls in an order that cannot transiently escape configured limits; detect kernel rejection instead of assuming application.
- [ ] **MC50-44** Collect and interpret memory/OOM, PSI, CPU throttling, I/O pressure, and pids-exhaustion signals with workload attribution.
- [ ] **MC50-45** Test delegation boundaries and ensure controllers are not writable by workloads beyond the explicitly delegated subtree.

### Definition of done / evidence gate

- [ ] **MC50-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC50-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC50-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC50-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC50-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC51 — Capacity/saturation model

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** predictive disk, inode, network, unpack CPU, memory, pull concurrency, and cache-pressure thresholds.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `documented`  
> **Implementation:** docs/operations/OPERATIONS.md §2  
> **Evidence:** `tools/bench.py`, `evidence/bench.json`  
> **Open:** fleet-scale measurements


### Architecture & requirements

- [ ] **MC51-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Capacity/saturation model**.
- [ ] **MC51-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC51-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC51-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC51-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC51-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC51-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC51-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC51-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC51-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC51-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC51-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC51-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC51-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC51-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC51-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC51-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC51-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC51-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC51-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC51-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC51-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC51-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC51-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC51-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC51-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC51-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC51-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC51-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC51-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC51-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC51-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC51-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC51-34** Implement and verify **predictive disk** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC51-35** Implement and verify **inode** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC51-36** Implement and verify **network** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC51-37** Implement and verify **unpack CPU** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC51-38** Implement and verify **memory** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC51-39** Implement and verify **pull concurrency** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC51-40** Implement and verify **cache-pressure thresholds** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC51-41** Write and verify resource controls in an order that cannot transiently escape configured limits; detect kernel rejection instead of assuming application.
- [ ] **MC51-42** Collect and interpret memory/OOM, PSI, CPU throttling, I/O pressure, and pids-exhaustion signals with workload attribution.
- [ ] **MC51-43** Test delegation boundaries and ensure controllers are not writable by workloads beyond the explicitly delegated subtree.
- [ ] **MC51-44** Treat network setup as a transaction with rollback of interfaces, addresses, routes, namespaces, firewall/policy state, and IPAM reservations.
- [ ] **MC51-45** Prevent route/address overlap, spoofing, host-network policy bypass, and cross-tenant namespace attachment.
- [ ] **MC51-46** Verify DNS configuration and search-domain behavior under namespace recreation, resolver failure, and policy changes.
- [ ] **MC51-47** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC51-48** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.

### Definition of done / evidence gate

- [ ] **MC51-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC51-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC51-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC51-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC51-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC52 — Backup/restore/reconstruction procedure

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** metadata recovery, content rehydration, trust-material handling, and disaster validation.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** store.py (backup/restore); OPERATIONS.md §3  
> **Evidence:** `tests/test_store.py`  
> **Open:** restore drill on production-size data


### Architecture & requirements

- [ ] **MC52-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Backup/restore/reconstruction procedure**.
- [ ] **MC52-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC52-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC52-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC52-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC52-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC52-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC52-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC52-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC52-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC52-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC52-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC52-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC52-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC52-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC52-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC52-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC52-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC52-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC52-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC52-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC52-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC52-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC52-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC52-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC52-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC52-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC52-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC52-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC52-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC52-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC52-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC52-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC52-34** Implement and verify **metadata recovery** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC52-35** Implement and verify **content rehydration** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC52-36** Implement and verify **trust-material handling** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC52-37** Implement and verify **disaster validation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC52-38** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC52-39** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC52-40** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.
- [ ] **MC52-41** Classify state into must-back-up, reconstructable, and secret/trust material; define consistency points and restore ordering.
- [ ] **MC52-42** Perform periodic destructive restore drills into an isolated environment and verify recovered referential integrity and trust state.
- [ ] **MC52-43** Record RPO/RTO targets and measure actual recovery behavior under representative dataset size.

### Definition of done / evidence gate

- [ ] **MC52-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC52-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC52-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC52-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC52-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC53 — Rolling upgrade and rollback controller

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** schema/runtime compatibility gates, canarying, rollback, and emergency disable.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `partial`  
> **Implementation:** migrations.py (SchemaTooNew); OPERATIONS.md §4  
> **Evidence:** `tests/test_store.py`  
> **Open:** automated rolling-upgrade controller across nodes


### Architecture & requirements

- [ ] **MC53-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Rolling upgrade and rollback controller**.
- [ ] **MC53-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC53-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC53-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC53-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC53-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC53-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC53-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC53-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC53-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC53-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC53-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC53-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC53-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC53-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC53-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC53-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC53-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC53-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC53-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC53-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC53-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC53-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC53-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC53-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC53-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC53-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC53-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC53-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC53-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC53-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC53-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC53-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC53-34** Implement and verify **schema/runtime compatibility gates** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC53-35** Implement and verify **canarying** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC53-36** Implement and verify **rollback** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC53-37** Implement and verify **emergency disable** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC53-38** Define N/N-1 compatibility for API, metadata, runtime, and node/controller versions and reject unsupported mixed-version states.
- [ ] **MC53-39** Gate irreversible schema or content-format changes behind explicit migration readiness and rollback strategy.
- [ ] **MC53-40** Canary upgrades with health/error/latency/security-policy gates and automated or operator-triggered rollback.

### Definition of done / evidence gate

- [ ] **MC53-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC53-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC53-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC53-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC53-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC54 — Configuration system

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** typed configuration schema, validation, secure defaults, environment/site overlays, provenance, atomic activation, and rollback.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** config.py  
> **Evidence:** `tests/test_ops.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC54-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Configuration system**.
- [ ] **MC54-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC54-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC54-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC54-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC54-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC54-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC54-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC54-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC54-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC54-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC54-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC54-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC54-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC54-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC54-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC54-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC54-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC54-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC54-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC54-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC54-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC54-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC54-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC54-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC54-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC54-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC54-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC54-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC54-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC54-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC54-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC54-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC54-34** Implement and verify **typed configuration schema** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC54-35** Implement and verify **validation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC54-36** Implement and verify **secure defaults** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC54-37** Implement and verify **environment/site overlays** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC54-38** Implement and verify **provenance** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC54-39** Implement and verify **atomic activation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC54-40** Implement and verify **rollback** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC54-41** Bind every verification decision to the immutable artifact digest, verifier policy version, trusted root set, and verification timestamp.
- [ ] **MC54-42** Fail closed on malformed, ambiguous, expired, revoked, or policy-incompatible evidence when the workload class requires verified trust.
- [ ] **MC54-43** Persist verification evidence and decision rationale so later audits can reproduce the admission result without relying on mutable tags.
- [ ] **MC54-44** Use a typed schema with unknown-field handling, cross-field validation, secure defaults, and validation before activation.
- [ ] **MC54-45** Apply configuration atomically or with explicit staged semantics; retain source/provenance, prior version, actor, and rollback capability.
- [ ] **MC54-46** Separate secret references from ordinary configuration values and prevent secret expansion into diagnostics.

### Definition of done / evidence gate

- [ ] **MC54-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC54-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC54-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC54-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC54-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC55 — Credential/key rotation workflow

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** runtime-safe refresh and revocation without process-wide restart where possible.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** trust.py (Keyring.rotate/revoke/expiring); OPERATIONS.md §5  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** HSM/KMS signing integration


### Architecture & requirements

- [ ] **MC55-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Credential/key rotation workflow**.
- [ ] **MC55-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC55-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC55-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC55-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC55-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC55-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC55-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC55-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC55-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC55-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC55-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC55-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC55-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC55-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC55-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC55-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC55-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC55-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC55-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC55-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC55-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC55-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC55-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC55-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC55-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC55-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC55-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC55-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC55-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC55-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC55-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC55-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC55-34** Implement and verify **runtime-safe refresh** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC55-35** Implement and verify **revocation without process-wide restart where possible** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC55-36** Represent credentials as scoped, expiring capabilities; avoid long-lived broad registry credentials in process environment or persisted logs.
- [ ] **MC55-37** Handle challenge/refresh races and token expiry without replaying credentials to an unintended registry or scope.
- [ ] **MC55-38** Redact authorization headers, tokens, helper output, and secret-derived values from logs, traces, crash dumps, and diagnostic bundles.

### Definition of done / evidence gate

- [ ] **MC55-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC55-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC55-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC55-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC55-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC56 — Incident runbook and escalation metadata

**Priority:** P1  
**Domain:** Observability and operations  
**Missing capability:** severity mapping, containment, registry compromise procedures, quarantine, recovery, and evidence preservation.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `documented`  
> **Implementation:** docs/operations/OPERATIONS.md §6  
> **Evidence:** —  
> **Open:** run tabletop exercises (G-05)


### Architecture & requirements

- [ ] **MC56-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Incident runbook and escalation metadata**.
- [ ] **MC56-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC56-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC56-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC56-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC56-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC56-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC56-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC56-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC56-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC56-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC56-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC56-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC56-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC56-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC56-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC56-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC56-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC56-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC56-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC56-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC56-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC56-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC56-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC56-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC56-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC56-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC56-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC56-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC56-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC56-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC56-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC56-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC56-34** Implement and verify **severity mapping** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC56-35** Implement and verify **containment** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC56-36** Implement and verify **registry compromise procedures** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC56-37** Implement and verify **quarantine** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC56-38** Implement and verify **recovery** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC56-39** Implement and verify **evidence preservation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC56-40** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC56-41** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC56-42** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC56-43** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC56-44** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC56-45** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.
- [ ] **MC56-46** Represent quarantine as authoritative durable state keyed by immutable digest plus policy scope, reason, actor, timestamps, and expiry/review fields.
- [ ] **MC56-47** Ensure quarantined content cannot be admitted via alternate tags, mirrors, caches, or stale local metadata.

### Definition of done / evidence gate

- [ ] **MC56-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC56-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC56-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC56-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC56-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC57 — OCI conformance fixtures

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** valid/invalid manifests, indexes, foreign/unknown media types, whiteouts, platform selection, and registry protocol cases.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** tests/fixtures.py  
> **Evidence:** `tests/test_oci.py`  
> **Open:** upstream OCI conformance suite run


### Architecture & requirements

- [ ] **MC57-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **OCI conformance fixtures**.
- [ ] **MC57-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC57-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC57-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC57-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC57-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC57-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC57-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC57-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC57-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC57-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC57-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC57-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC57-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC57-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC57-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC57-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC57-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC57-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC57-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC57-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC57-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC57-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC57-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC57-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC57-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC57-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC57-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC57-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC57-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC57-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC57-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC57-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC57-34** Establish and verify coverage for **valid/invalid manifests** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC57-35** Establish and verify coverage for **indexes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC57-36** Establish and verify coverage for **foreign/unknown media types** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC57-37** Establish and verify coverage for **whiteouts** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC57-38** Establish and verify coverage for **platform selection** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC57-39** Establish and verify coverage for **registry protocol cases** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC57-40** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC57-41** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC57-42** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.

### Definition of done / evidence gate

- [ ] **MC57-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC57-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC57-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC57-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC57-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC58 — Real registry integration tests

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** authenticated TLS registry, mirror, outage, redirect, range, resume, token-expiry, and corruption scenarios.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `partial`  
> **Implementation:** tests/fixtures.py (FakeRegistry over real HTTP)  
> **Evidence:** `tests/test_distribution.py`  
> **Open:** tests against a real registry (distribution/distribution, Harbor, GHCR)


### Architecture & requirements

- [ ] **MC58-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Real registry integration tests**.
- [ ] **MC58-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC58-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC58-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC58-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC58-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC58-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC58-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC58-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC58-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC58-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC58-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC58-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC58-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC58-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC58-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC58-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC58-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC58-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC58-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC58-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC58-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC58-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC58-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC58-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC58-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC58-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC58-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC58-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC58-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC58-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC58-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC58-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC58-34** Establish and verify coverage for **authenticated TLS registry** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC58-35** Establish and verify coverage for **mirror** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC58-36** Establish and verify coverage for **outage** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC58-37** Establish and verify coverage for **redirect** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC58-38** Establish and verify coverage for **range** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC58-39** Establish and verify coverage for **resume** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC58-40** Establish and verify coverage for **token-expiry** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC58-41** Establish and verify coverage for **corruption scenarios** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC58-42** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC58-43** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC58-44** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC58-45** Represent credentials as scoped, expiring capabilities; avoid long-lived broad registry credentials in process environment or persisted logs.
- [ ] **MC58-46** Handle challenge/refresh races and token expiry without replaying credentials to an unintended registry or scope.
- [ ] **MC58-47** Redact authorization headers, tokens, helper output, and secret-derived values from logs, traces, crash dumps, and diagnostic bundles.
- [ ] **MC58-48** Enforce certificate chain and hostname validation by default; insecure endpoints require an explicit, narrowly scoped, auditable exception.
- [ ] **MC58-49** Apply trust policy before sending credentials and prevent proxy/redirect behavior from downgrading transport guarantees.

### Definition of done / evidence gate

- [ ] **MC58-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC58-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC58-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC58-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC58-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC59 — Real runtime integration tests

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** bundle creation and lifecycle tests against supported runtime/runtime versions.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented+runtime-verified`  
> **Implementation:** tests/integration/test_runc.py  
> **Evidence:** `tests/integration/test_runc.py`  
> **Open:** crun/runsc/kata


### Architecture & requirements

- [ ] **MC59-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Real runtime integration tests**.
- [ ] **MC59-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC59-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC59-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC59-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC59-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC59-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC59-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC59-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC59-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC59-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC59-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC59-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC59-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC59-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC59-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC59-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC59-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC59-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC59-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC59-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC59-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC59-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC59-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC59-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC59-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC59-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC59-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC59-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC59-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC59-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC59-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC59-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC59-34** Establish and verify coverage for **bundle creation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC59-35** Establish and verify coverage for **lifecycle tests against supported runtime/runtime versions** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC59-36** Generate runtime bundles deterministically from validated state and retain a digestable rendered configuration for audit and incident reconstruction.
- [ ] **MC59-37** Define runtime/shim RPC or process boundaries with explicit version negotiation, timeout behavior, exit semantics, and untrusted-output handling.
- [ ] **MC59-38** Verify that unsupported runtime features fail before workload start rather than degrading silently.
- [ ] **MC59-39** Specify a finite-state machine for all lifecycle states and reject illegal transitions with stable, machine-readable error codes.
- [ ] **MC59-40** Make start/stop/delete operations idempotent under retries, controller failover, duplicate messages, and runtime/shim restarts.
- [ ] **MC59-41** Capture exit code, signal, OOM/limit cause, timestamps, and terminal metadata exactly once and make terminal state durable.

### Definition of done / evidence gate

- [ ] **MC59-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC59-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC59-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC59-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC59-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC60 — Namespace/cgroup isolation tests

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** privilege, resource, PID, mount, network, and device boundary verification on supported Linux kernels.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `partial`  
> **Implementation:** tests/integration/test_runc.py  
> **Evidence:** `tests/integration/test_runc.py`  
> **Open:** cgroup v2 limit enforcement test; user-namespace run


### Architecture & requirements

- [ ] **MC60-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Namespace/cgroup isolation tests**.
- [ ] **MC60-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC60-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC60-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC60-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC60-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC60-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC60-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC60-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC60-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC60-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC60-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC60-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC60-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC60-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC60-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC60-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC60-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC60-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC60-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC60-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC60-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC60-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC60-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC60-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC60-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC60-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC60-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC60-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC60-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC60-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC60-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC60-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC60-34** Establish and verify coverage for **privilege** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC60-35** Establish and verify coverage for **resource** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC60-36** Establish and verify coverage for **mount** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC60-37** Establish and verify coverage for **network** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC60-38** Establish and verify coverage for **device boundary verification on supported Linux kernels** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC60-39** Validate every mount source, target, propagation flag, filesystem type, and option against policy before performing privileged mount operations.
- [ ] **MC60-40** Test whiteout, opaque directory, copy-up, hardlink, symlink, xattr, ownership, and permission behavior against the selected snapshotter/filesystem matrix.
- [ ] **MC60-41** Guarantee teardown is idempotent and leak-resistant across process death, lazy/unexpected unmount conditions, and partially constructed snapshots.
- [ ] **MC60-42** Validate namespace ownership and join/create semantics so a workload cannot attach to a more privileged namespace than policy permits.
- [ ] **MC60-43** Verify UID/GID mappings for gaps, overlap, host-root exposure, subordinate-ID exhaustion, and filesystem ownership translation.
- [ ] **MC60-44** Test namespace teardown and orphan cleanup after controller/runtime crashes and host reboot.
- [ ] **MC60-45** Treat network setup as a transaction with rollback of interfaces, addresses, routes, namespaces, firewall/policy state, and IPAM reservations.
- [ ] **MC60-46** Prevent route/address overlap, spoofing, host-network policy bypass, and cross-tenant namespace attachment.

### Definition of done / evidence gate

- [ ] **MC60-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC60-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC60-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC60-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC60-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC61 — Fuzzing corpus/harnesses

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** references, manifests, descriptors, registry responses, decompression paths, metadata migrations, and policy inputs.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** tests/test_fuzz_stress.py (FuzzTests)  
> **Evidence:** `tests/test_fuzz_stress.py`  
> **Open:** coverage-guided fuzzing campaign


### Architecture & requirements

- [ ] **MC61-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Fuzzing corpus/harnesses**.
- [ ] **MC61-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC61-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC61-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC61-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC61-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC61-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC61-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC61-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC61-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC61-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC61-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC61-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC61-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC61-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC61-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC61-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC61-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC61-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC61-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC61-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC61-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC61-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC61-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC61-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC61-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC61-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC61-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC61-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC61-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC61-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC61-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC61-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC61-34** Establish and verify coverage for **references** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC61-35** Establish and verify coverage for **manifests** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC61-36** Establish and verify coverage for **descriptors** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC61-37** Establish and verify coverage for **registry responses** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC61-38** Establish and verify coverage for **decompression paths** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC61-39** Establish and verify coverage for **metadata migrations** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC61-40** Establish and verify coverage for **policy inputs** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC61-41** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC61-42** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC61-43** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC61-44** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC61-45** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.
- [ ] **MC61-46** Verify layer digest before commit and ensure partial unpack trees cannot become visible as ready snapshots.
- [ ] **MC61-47** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC61-48** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.

### Definition of done / evidence gate

- [ ] **MC61-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC61-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC61-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC61-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC61-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC62 — Adversarial/escape tests

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** path traversal, symlink/hardlink attacks, malicious layers, decompression bombs, capability escalation, namespace escape attempts, and resource exhaustion.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** tests/test_rootfs.py; tests/integration/test_runc.py  
> **Evidence:** `tests/test_rootfs.py`, `tests/integration/test_runc.py`  
> **Open:** kernel-escape CVE regression corpus


### Architecture & requirements

- [ ] **MC62-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Adversarial/escape tests**.
- [ ] **MC62-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC62-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC62-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC62-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC62-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC62-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC62-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC62-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC62-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC62-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC62-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC62-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC62-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC62-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC62-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC62-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC62-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC62-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC62-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC62-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC62-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC62-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC62-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC62-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC62-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC62-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC62-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC62-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC62-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC62-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC62-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC62-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC62-34** Establish and verify coverage for **path traversal** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC62-35** Establish and verify coverage for **symlink/hardlink attacks** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC62-36** Establish and verify coverage for **malicious layers** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC62-37** Establish and verify coverage for **decompression bombs** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC62-38** Establish and verify coverage for **capability escalation** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC62-39** Establish and verify coverage for **namespace escape attempts** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC62-40** Establish and verify coverage for **resource exhaustion** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC62-41** Validate namespace ownership and join/create semantics so a workload cannot attach to a more privileged namespace than policy permits.
- [ ] **MC62-42** Verify UID/GID mappings for gaps, overlap, host-root exposure, subordinate-ID exhaustion, and filesystem ownership translation.
- [ ] **MC62-43** Test namespace teardown and orphan cleanup after controller/runtime crashes and host reboot.
- [ ] **MC62-44** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC62-45** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.
- [ ] **MC62-46** Verify layer digest before commit and ensure partial unpack trees cannot become visible as ready snapshots.
- [ ] **MC62-47** Compute effective privilege from all interacting controls rather than validating each control in isolation; reject contradictory configurations.
- [ ] **MC62-48** Provide a secure baseline profile and a narrowly scoped compatibility override mechanism with owner, justification, expiry, and audit trail.

### Definition of done / evidence gate

- [ ] **MC62-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC62-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC62-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC62-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC62-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC63 — Race/concurrency stress suite

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** concurrent tag writes, pulls, GC, quarantine, unpack, snapshot operations, and process restarts.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** tests/test_fuzz_stress.py (StressTests, multiprocess CAS)  
> **Evidence:** `tests/test_fuzz_stress.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC63-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Race/concurrency stress suite**.
- [ ] **MC63-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC63-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC63-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC63-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC63-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC63-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC63-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC63-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC63-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC63-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC63-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC63-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC63-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC63-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC63-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC63-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC63-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC63-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC63-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC63-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC63-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC63-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC63-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC63-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC63-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC63-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC63-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC63-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC63-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC63-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC63-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC63-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC63-34** Establish and verify coverage for **concurrent tag writes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC63-35** Establish and verify coverage for **pulls** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC63-36** Establish and verify coverage for **quarantine** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC63-37** Establish and verify coverage for **unpack** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC63-38** Establish and verify coverage for **snapshot operations** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC63-39** Establish and verify coverage for **process restarts** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC63-40** Validate every mount source, target, propagation flag, filesystem type, and option against policy before performing privileged mount operations.
- [ ] **MC63-41** Test whiteout, opaque directory, copy-up, hardlink, symlink, xattr, ownership, and permission behavior against the selected snapshotter/filesystem matrix.
- [ ] **MC63-42** Guarantee teardown is idempotent and leak-resistant across process death, lazy/unexpected unmount conditions, and partially constructed snapshots.
- [ ] **MC63-43** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC63-44** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.
- [ ] **MC63-45** Verify layer digest before commit and ensure partial unpack trees cannot become visible as ready snapshots.
- [ ] **MC63-46** Represent quarantine as authoritative durable state keyed by immutable digest plus policy scope, reason, actor, timestamps, and expiry/review fields.
- [ ] **MC63-47** Ensure quarantined content cannot be admitted via alternate tags, mirrors, caches, or stale local metadata.

### Definition of done / evidence gate

- [ ] **MC63-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC63-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC63-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC63-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC63-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC64 — Fault-injection suite

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** disk-full, ENOSPC/inode exhaustion, torn writes, process kill, network partitions, registry 5xx, TLS failures, and metadata corruption.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** tests/test_fuzz_stress.py (FaultInjectionTests)  
> **Evidence:** `tests/test_fuzz_stress.py`  
> **Open:** network-partition injection at scale


### Architecture & requirements

- [ ] **MC64-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Fault-injection suite**.
- [ ] **MC64-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC64-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC64-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC64-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC64-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC64-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC64-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC64-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC64-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC64-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC64-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC64-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC64-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC64-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC64-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC64-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC64-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC64-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC64-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC64-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC64-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC64-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC64-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC64-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC64-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC64-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC64-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC64-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC64-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC64-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC64-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC64-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC64-34** Establish and verify coverage for **disk-full** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC64-35** Establish and verify coverage for **ENOSPC/inode exhaustion** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC64-36** Establish and verify coverage for **torn writes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC64-37** Establish and verify coverage for **process kill** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC64-38** Establish and verify coverage for **network partitions** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC64-39** Establish and verify coverage for **registry 5xx** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC64-40** Establish and verify coverage for **TLS failures** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC64-41** Establish and verify coverage for **metadata corruption** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC64-42** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC64-43** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC64-44** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC64-45** Treat network setup as a transaction with rollback of interfaces, addresses, routes, namespaces, firewall/policy state, and IPAM reservations.
- [ ] **MC64-46** Prevent route/address overlap, spoofing, host-network policy bypass, and cross-tenant namespace attachment.
- [ ] **MC64-47** Verify DNS configuration and search-domain behavior under namespace recreation, resolver failure, and policy changes.
- [ ] **MC64-48** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC64-49** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.

### Definition of done / evidence gate

- [ ] **MC64-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC64-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC64-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC64-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC64-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC65 — Performance/soak/fleet benchmarks

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** cold/warm pulls, shared-layer density, startup latency, unpack throughput, tail latency, GC impact, and long-duration leak detection.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `partial`  
> **Implementation:** tools/bench.py  
> **Evidence:** `tools/bench.py`, `evidence/bench.json`  
> **Open:** fleet benchmarks; 24h soak


### Architecture & requirements

- [ ] **MC65-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Performance/soak/fleet benchmarks**.
- [ ] **MC65-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC65-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC65-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC65-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC65-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC65-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC65-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC65-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC65-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC65-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC65-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC65-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC65-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC65-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC65-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC65-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC65-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC65-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC65-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC65-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC65-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC65-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC65-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC65-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC65-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC65-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC65-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC65-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC65-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC65-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC65-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC65-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC65-34** Establish and verify coverage for **cold/warm pulls** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC65-35** Establish and verify coverage for **shared-layer density** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC65-36** Establish and verify coverage for **startup latency** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC65-37** Establish and verify coverage for **unpack throughput** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC65-38** Establish and verify coverage for **tail latency** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC65-39** Establish and verify coverage for **GC impact** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC65-40** Establish and verify coverage for **long-duration leak detection** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC65-41** Stream-decompress with independent compressed-size, expanded-size, file-count, path-depth, and per-entry limits to resist decompression bombs.
- [ ] **MC65-42** Reject path traversal, absolute paths, device-node creation, unsafe hardlinks/symlinks, and whiteout constructs that escape the extraction root.
- [ ] **MC65-43** Verify layer digest before commit and ensure partial unpack trees cannot become visible as ready snapshots.
- [ ] **MC65-44** Define workload models and SLO-relevant percentiles before tuning; report cold/warm cache state, hardware, filesystem, kernel, runtime, and registry conditions.
- [ ] **MC65-45** Track throughput, p50/p95/p99 latency, CPU, memory, disk bytes/IOPS, network bytes, inode growth, and long-duration leak indicators.
- [ ] **MC65-46** Fail certification on material regression beyond an approved budget or require an owned, expiring waiver.

### Definition of done / evidence gate

- [ ] **MC65-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC65-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC65-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC65-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC65-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC66 — Cross-architecture/kernel/runtime matrix

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** supported CPU architectures, Linux distributions/kernels, filesystems, cgroup modes, runtimes, and registry versions.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `partial`  
> **Implementation:** COMPATIBILITY.md; .github/workflows/ci.yml  
> **Evidence:** —  
> **Open:** arm64, cgroup v2, crun/runsc/kata, Python 3.10/3.12/3.13 runs


### Architecture & requirements

- [ ] **MC66-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Cross-architecture/kernel/runtime matrix**.
- [ ] **MC66-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC66-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC66-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC66-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC66-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC66-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC66-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC66-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC66-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC66-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC66-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC66-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC66-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC66-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC66-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC66-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC66-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC66-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC66-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC66-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC66-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC66-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC66-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC66-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC66-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC66-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC66-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC66-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC66-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC66-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC66-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC66-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC66-34** Establish and verify coverage for **supported CPU architectures** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC66-35** Establish and verify coverage for **Linux distributions/kernels** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC66-36** Establish and verify coverage for **filesystems** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC66-37** Establish and verify coverage for **cgroup modes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC66-38** Establish and verify coverage for **runtimes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC66-39** Establish and verify coverage for **registry versions** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC66-40** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC66-41** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC66-42** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC66-43** Write and verify resource controls in an order that cannot transiently escape configured limits; detect kernel rejection instead of assuming application.
- [ ] **MC66-44** Collect and interpret memory/OOM, PSI, CPU throttling, I/O pressure, and pids-exhaustion signals with workload attribution.
- [ ] **MC66-45** Test delegation boundaries and ensure controllers are not writable by workloads beyond the explicitly delegated subtree.
- [ ] **MC66-46** Express support as machine-readable tuples where feasible and distinguish certified, best-effort, deprecated, and unsupported combinations.
- [ ] **MC66-47** Run representative positive and negative tests for every certified tuple and retain evidence linked to the release digest.

### Definition of done / evidence gate

- [ ] **MC66-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC66-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC66-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC66-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC66-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC67 — Machine-readable release evidence

**Priority:** P1  
**Domain:** Testing and certification  
**Missing capability:** signed test/gate outputs tied to source/version/artifact digests before production certification.

**Priority gate:** Production-readiness: required for robust multi-node/operational deployment; any deferral needs an owned, expiring risk acceptance.

> **v5.0.0 status:** `implemented`  
> **Implementation:** tools/release_evidence.py  
> **Evidence:** `evidence/release-evidence.json`  
> **Open:** signing the evidence bundle (E-08)


### Architecture & requirements

- [ ] **MC67-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Machine-readable release evidence**.
- [ ] **MC67-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC67-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC67-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC67-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC67-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC67-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC67-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC67-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC67-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC67-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC67-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC67-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC67-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC67-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC67-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC67-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC67-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC67-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC67-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC67-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC67-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC67-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC67-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC67-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC67-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC67-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC67-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC67-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC67-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC67-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC67-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC67-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC67-34** Establish and verify coverage for **signed test/gate outputs tied to source/version/artifact digests before production certification** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC67-35** Make release gates non-bypassable without a named, expiring, audited exception and preserve immutable evidence for each gate.
- [ ] **MC67-36** Bind build provenance, tests, SBOM, signatures, scans, benchmark results, source revision, and artifact digests into the release record.
- [ ] **MC67-37** Verify reproducibility or at minimum deterministic dependency resolution and controlled build environments.

### Definition of done / evidence gate

- [ ] **MC67-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC67-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC67-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC67-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC67-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC68 — `MASTER.md`

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** referenced by the prior README but absent from the supplied archive; restore the authoritative master prompt/workflow artifact or remove it from the distribution contract.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `implemented`  
> **Implementation:** MASTER.md  
> **Evidence:** —  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC68-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **`MASTER.md`**.
- [ ] **MC68-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC68-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC68-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC68-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC68-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC68-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC68-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC68-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC68-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC68-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC68-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC68-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC68-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC68-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC68-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC68-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC68-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC68-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC68-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC68-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC68-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC68-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC68-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC68-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC68-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC68-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC68-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC68-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC68-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC68-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC68-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC68-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC68-34** Resolve and verify **referenced by the prior README but absent from the supplied archive** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC68-35** Resolve and verify **restore the authoritative master prompt/workflow artifact or remove it from the distribution contract** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC68-36** Define the artifact as part of the release contract: authoritative source, owner, review cadence, required approvals, and compatibility/versioning rules.
- [ ] **MC68-37** Add automated release checks that fail when the required governance artifact is absent, stale, malformed, or inconsistent with package metadata.
- [ ] **MC68-38** Retain change history and link material governance changes to release notes and migration/operational impact assessments.

### Definition of done / evidence gate

- [ ] **MC68-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC68-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC68-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC68-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC68-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC69 — Package/build metadata

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** `pyproject.toml` or equivalent with dependency/version constraints, build backend, supported Python versions, and reproducible packaging rules if this component is distributed independently.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `implemented`  
> **Implementation:** pyproject.toml; VERSION  
> **Evidence:** —  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC69-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Package/build metadata**.
- [ ] **MC69-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC69-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC69-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC69-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC69-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC69-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC69-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC69-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC69-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC69-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC69-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC69-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC69-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC69-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC69-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC69-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC69-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC69-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC69-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC69-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC69-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC69-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC69-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC69-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC69-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC69-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC69-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC69-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC69-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC69-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC69-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC69-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC69-34** Resolve and verify **`pyproject.toml` or equivalent with dependency/version constraints** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC69-35** Resolve and verify **build backend** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC69-36** Resolve and verify **supported Python versions** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC69-37** Resolve and verify **reproducible packaging rules if this component is distributed independently** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC69-38** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC69-39** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC69-40** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.

### Definition of done / evidence gate

- [ ] **MC69-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC69-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC69-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC69-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC69-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC70 — Dependency lock/SBOM for the package

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** pinned `pk_core` compatibility plus a generated software bill of materials for release artifacts.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `implemented`  
> **Implementation:** tools/release_evidence.py (sbom.cdx.json)  
> **Evidence:** `evidence/sbom.cdx.json`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC70-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Dependency lock/SBOM for the package**.
- [ ] **MC70-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC70-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC70-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC70-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC70-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC70-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC70-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC70-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC70-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC70-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC70-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC70-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC70-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC70-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC70-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC70-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC70-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC70-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC70-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC70-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC70-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC70-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC70-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC70-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC70-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC70-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC70-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC70-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC70-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC70-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC70-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC70-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC70-34** Resolve and verify **pinned `pk_core` compatibility plus a generated software bill of materials for release artifacts** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC70-35** Bind SBOM/scanner results to exact image/artifact digests and record scanner database/version/freshness metadata.
- [ ] **MC70-36** Distinguish unscanned, scan-failed, scan-stale, vulnerability-present, and exception-approved states; do not collapse them into a boolean.
- [ ] **MC70-37** Exercise exception expiry and re-evaluation when scanner intelligence, exploitability data, or policy changes.

### Definition of done / evidence gate

- [ ] **MC70-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC70-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC70-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC70-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC70-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC71 — License/NOTICE files

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** no license or notice artifact is present in this upload; add the estate-approved legal metadata if this package is distributable.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `owner-action`  
> **Implementation:** NOTICE; LICENSE-STATUS.md  
> **Evidence:** —  
> **Open:** owner must choose and add a LICENSE


### Architecture & requirements

- [ ] **MC71-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **License/NOTICE files**.
- [ ] **MC71-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC71-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC71-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC71-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC71-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC71-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC71-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC71-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC71-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC71-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC71-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC71-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC71-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC71-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC71-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC71-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC71-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC71-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC71-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC71-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC71-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC71-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC71-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC71-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC71-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC71-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC71-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC71-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC71-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC71-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC71-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC71-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC71-34** Resolve and verify **no license or notice artifact is present in this upload** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC71-35** Resolve and verify **add the estate-approved legal metadata if this package is distributable** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC71-36** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC71-37** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC71-38** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.
- [ ] **MC71-39** Define the artifact as part of the release contract: authoritative source, owner, review cadence, required approvals, and compatibility/versioning rules.
- [ ] **MC71-40** Add automated release checks that fail when the required governance artifact is absent, stale, malformed, or inconsistent with package metadata.
- [ ] **MC71-41** Retain change history and link material governance changes to release notes and migration/operational impact assessments.

### Definition of done / evidence gate

- [ ] **MC71-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC71-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC71-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC71-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC71-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC72 — Architecture Decision Record

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** approved technology/scope decision covering OCI/container-runtime choices and rejected alternatives.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `implemented`  
> **Implementation:** docs/adr/ADR-0001-substrate-architecture.md  
> **Evidence:** —  
> **Open:** owner ratification


### Architecture & requirements

- [ ] **MC72-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Architecture Decision Record**.
- [ ] **MC72-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC72-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC72-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC72-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC72-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC72-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC72-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC72-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC72-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC72-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC72-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC72-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC72-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC72-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC72-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC72-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC72-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC72-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC72-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC72-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC72-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC72-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC72-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC72-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC72-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC72-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC72-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC72-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC72-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC72-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC72-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC72-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC72-34** Resolve and verify **approved technology/scope decision covering OCI/container-runtime choices** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC72-35** Resolve and verify **rejected alternatives** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Definition of done / evidence gate

- [ ] **MC72-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC72-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC72-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC72-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC72-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC73 — Named ownership/escalation metadata

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** accountable team/service owner, on-call route, security owner, and escalation path.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `owner-action`  
> **Implementation:** OWNERS.yaml  
> **Evidence:** —  
> **Open:** owner must name service/security/operational owners


### Architecture & requirements

- [ ] **MC73-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Named ownership/escalation metadata**.
- [ ] **MC73-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC73-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC73-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC73-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC73-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC73-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC73-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC73-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC73-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC73-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC73-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC73-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC73-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC73-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC73-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC73-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC73-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC73-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC73-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC73-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC73-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC73-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC73-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC73-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC73-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC73-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC73-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC73-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC73-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC73-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC73-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC73-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC73-34** Resolve and verify **accountable team/service owner** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC73-35** Resolve and verify **on-call route** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC73-36** Resolve and verify **security owner** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC73-37** Resolve and verify **escalation path** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC73-38** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC73-39** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC73-40** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.
- [ ] **MC73-41** Document concrete detection, containment, evidence-preservation, eradication, recovery, and post-incident steps for registry compromise and runtime isolation failure.
- [ ] **MC73-42** Define severity, owner/on-call, communications path, required artifacts, and decision authority for emergency quarantine or service disablement.
- [ ] **MC73-43** Tabletop and periodically exercise the runbook; track gaps to closure.

### Definition of done / evidence gate

- [ ] **MC73-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC73-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC73-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC73-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC73-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC74 — Compatibility matrix

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** supported `pk_core`, Python, OCI spec, runtime, registry, Linux kernel/cgroup, snapshotter, and architecture versions.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `implemented`  
> **Implementation:** COMPATIBILITY.md  
> **Evidence:** —  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC74-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Compatibility matrix**.
- [ ] **MC74-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC74-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC74-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC74-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC74-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC74-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC74-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC74-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC74-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC74-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC74-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC74-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC74-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC74-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC74-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC74-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC74-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC74-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC74-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC74-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC74-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC74-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC74-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC74-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC74-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC74-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC74-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC74-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC74-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC74-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC74-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC74-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC74-34** Resolve and verify **supported `pk_core`** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC74-35** Resolve and verify **Python** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC74-36** Resolve and verify **OCI spec** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC74-37** Resolve and verify **runtime** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC74-38** Resolve and verify **registry** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC74-39** Resolve and verify **Linux kernel/cgroup** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC74-40** Resolve and verify **snapshotter** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC74-41** Resolve and verify **architecture versions** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC74-42** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC74-43** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC74-44** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC74-45** Express support as machine-readable tuples where feasible and distinguish certified, best-effort, deprecated, and unsupported combinations.
- [ ] **MC74-46** Run representative positive and negative tests for every certified tuple and retain evidence linked to the release digest.
- [ ] **MC74-47** Define policy for newly discovered kernel/runtime regressions, emergency de-certification, and customer/operator notification.

### Definition of done / evidence gate

- [ ] **MC74-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC74-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC74-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC74-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC74-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC75 — Release automation/CI

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** compile, unit, integration, fuzz, security, benchmark, packaging, SBOM, signature, and evidence gates.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `implemented`  
> **Implementation:** .github/workflows/ci.yml  
> **Evidence:** —  
> **Open:** enable in a hosted repo; self-hosted runtime runner


### Architecture & requirements

- [ ] **MC75-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Release automation/CI**.
- [ ] **MC75-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC75-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC75-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC75-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC75-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC75-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC75-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC75-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC75-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC75-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC75-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC75-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC75-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC75-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC75-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC75-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC75-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC75-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC75-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC75-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC75-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC75-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC75-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC75-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC75-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC75-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC75-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC75-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC75-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC75-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC75-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC75-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC75-34** Resolve and verify **compile** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC75-35** Resolve and verify **unit** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC75-36** Resolve and verify **integration** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC75-37** Resolve and verify **fuzz** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC75-38** Resolve and verify **security** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC75-39** Resolve and verify **benchmark** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC75-40** Resolve and verify **packaging** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC75-41** Resolve and verify **SBOM** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC75-42** Bind every verification decision to the immutable artifact digest, verifier policy version, trusted root set, and verification timestamp.
- [ ] **MC75-43** Fail closed on malformed, ambiguous, expired, revoked, or policy-incompatible evidence when the workload class requires verified trust.
- [ ] **MC75-44** Persist verification evidence and decision rationale so later audits can reproduce the admission result without relying on mutable tags.
- [ ] **MC75-45** Bind SBOM/scanner results to exact image/artifact digests and record scanner database/version/freshness metadata.
- [ ] **MC75-46** Distinguish unscanned, scan-failed, scan-stale, vulnerability-present, and exception-approved states; do not collapse them into a boolean.
- [ ] **MC75-47** Exercise exception expiry and re-evaluation when scanner intelligence, exploitability data, or policy changes.
- [ ] **MC75-48** Make failures reproducible by retaining seed/corpus/input, environment, build digest, and minimized reproducer where possible.
- [ ] **MC75-49** Run sanitizers/race detectors or platform-equivalent dynamic checks in dedicated jobs where supported.

### Definition of done / evidence gate

- [ ] **MC75-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC75-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC75-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC75-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC75-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC76 — Migration framework

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** forward/backward metadata migrations, rollback compatibility, downgrade policy, and migration evidence.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `implemented`  
> **Implementation:** migrations.py  
> **Evidence:** `tests/test_store.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC76-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Migration framework**.
- [ ] **MC76-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC76-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC76-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC76-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC76-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC76-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC76-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC76-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC76-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC76-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC76-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC76-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC76-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC76-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC76-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC76-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC76-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC76-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC76-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC76-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC76-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC76-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC76-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC76-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC76-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC76-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC76-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC76-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC76-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC76-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC76-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC76-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC76-34** Resolve and verify **forward/backward metadata migrations** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC76-35** Resolve and verify **rollback compatibility** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC76-36** Resolve and verify **downgrade policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC76-37** Resolve and verify **migration evidence** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC76-38** Use transactional updates for related image/container/task/snapshot records and define referential-integrity constraints explicitly.
- [ ] **MC76-39** Add schema-version detection, forward migration, rollback/downgrade policy, migration checkpoints, and crash-recovery testing.
- [ ] **MC76-40** Separate authoritative state from derived/cache state so reconstruction procedures are deterministic.

### Definition of done / evidence gate

- [ ] **MC76-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC76-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC76-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC76-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC76-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC77 — Exception/waiver registry

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** owned, expiring exceptions for unsupported runtimes, registries, security profiles, or operational constraints.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `implemented`  
> **Implementation:** policy.py (Waiver, WaiverRegistry); waivers/waivers.json  
> **Evidence:** `tests/test_trust_policy.py`  
> **Open:** none beyond independent review and DoD gates


### Architecture & requirements

- [ ] **MC77-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **Exception/waiver registry**.
- [ ] **MC77-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC77-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC77-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC77-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC77-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC77-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC77-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC77-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC77-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC77-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC77-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC77-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC77-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC77-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC77-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC77-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC77-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC77-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC77-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC77-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC77-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC77-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC77-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC77-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC77-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC77-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC77-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC77-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC77-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC77-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC77-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC77-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC77-34** Resolve and verify **owned** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC77-35** Resolve and verify **expiring exceptions for unsupported runtimes** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC77-36** Resolve and verify **registries** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC77-37** Resolve and verify **security profiles** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC77-38** Resolve and verify **or operational constraints** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC77-39** Model registry HTTP status/error codes explicitly, including authentication challenges, redirects, range semantics, retryability, and terminal failures.
- [ ] **MC77-40** Bound redirect count and prevent credential forwarding across untrusted origins; verify the final content digest independently of transport success.
- [ ] **MC77-41** Make upload/download progress durable enough to resume safely without accepting stale or mismatched partial content.
- [ ] **MC77-42** Define the artifact as part of the release contract: authoritative source, owner, review cadence, required approvals, and compatibility/versioning rules.
- [ ] **MC77-43** Add automated release checks that fail when the required governance artifact is absent, stale, malformed, or inconsistent with package metadata.
- [ ] **MC77-44** Retain change history and link material governance changes to release notes and migration/operational impact assessments.

### Definition of done / evidence gate

- [ ] **MC77-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC77-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC77-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC77-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC77-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## MC78 — End-of-life/vulnerability SLA

**Priority:** P2  
**Domain:** Packaging, governance, and missing artifacts  
**Missing capability:** patch windows, CVE response, deprecation policy, supported-version lifetime, and emergency release process.

**Priority gate:** Packaging/governance: required to make the component sustainably releasable, supportable, auditable, and maintainable.

> **v5.0.0 status:** `owner-action`  
> **Implementation:** SECURITY.md  
> **Evidence:** —  
> **Open:** owner approval of SLA/EOL defaults


### Architecture & requirements

- [ ] **MC78-01** Write an approved component specification that states scope, non-goals, trust boundaries, authoritative state, dependencies, and the exact production responsibilities of **End-of-life/vulnerability SLA**.
- [ ] **MC78-02** Assign a service/component owner, security owner, operational owner, and escalation path; record review cadence and lifecycle status.
- [ ] **MC78-03** Define externally observable behavior as normative MUST/SHOULD/MAY requirements, including malformed-input behavior and unsupported-feature behavior.
- [ ] **MC78-04** Document the component state machine or lifecycle, invariants, legal transitions, terminal states, and recovery transitions; identify which state is durable vs. derived.
- [ ] **MC78-05** Define compatibility constraints and capability negotiation with adjacent components; reject incompatible peers deterministically before unsafe work begins.

### Interfaces, data model & implementation

- [ ] **MC78-06** Define versioned APIs/RPCs/files/formats with typed request/response schemas, size limits, required/optional fields, stable error codes, and backward-compatibility rules.
- [ ] **MC78-07** Validate all external and persisted inputs before use, including lengths, encodings, identifiers, paths, numeric ranges, enum values, nested object depth, and cross-field invariants.
- [ ] **MC78-08** Make state-changing operations idempotent or explicitly non-idempotent; assign operation/request IDs and specify duplicate/replay semantics.
- [ ] **MC78-09** Design concurrency control for threads, processes, and nodes as applicable; document lock ordering, ownership, race assumptions, atomicity boundaries, and deadlock avoidance.
- [ ] **MC78-10** Bound memory, disk, file descriptors, goroutines/threads/processes, network concurrency, queue depth, and per-request work; define overload behavior rather than relying on host exhaustion.

### Security & trust

- [ ] **MC78-11** Create a component-specific threat model covering malicious images/artifacts, untrusted registry/runtime responses, compromised tenants, confused-deputy paths, privilege escalation, denial of service, and supply-chain tampering as applicable.
- [ ] **MC78-12** Apply least privilege to processes, filesystem paths, sockets, devices, credentials, capabilities, namespaces, and service identities; document every privilege that cannot be removed.
- [ ] **MC78-13** Authenticate and authorize every privileged or cross-trust-boundary operation; bind authorization to immutable workload/tenant identity and the concrete resource being modified.
- [ ] **MC78-14** Ensure secrets, credentials, tokens, private keys, and sensitive metadata are never emitted to ordinary logs, metrics labels, traces, command lines, core dumps, or world-readable files.
- [ ] **MC78-15** Emit tamper-resistant audit events for security-significant state changes and denials with actor, resource, policy/version, reason, correlation ID, and before/after state where safe.

### Reliability, recovery & resource control

- [ ] **MC78-16** Enumerate failure modes for process crash, host reboot, partial writes, dependency timeout, malformed dependency response, network partition, disk/inode exhaustion, permission failure, and version skew; define expected recovery for each.
- [ ] **MC78-17** Use atomic commit/rename/transaction patterns for durable state and prove crash consistency with fault injection at each persistence boundary.
- [ ] **MC78-18** Propagate cancellation and deadlines through nested operations; use bounded retry with classification and jitter only when an operation is safe to repeat.
- [ ] **MC78-19** Define reconciliation logic that can detect and repair orphaned, leaked, partially completed, or contradictory state without deleting live resources.
- [ ] **MC78-20** Specify behavior under degraded dependencies and resource pressure, including backpressure, admission denial, read-only/degraded modes, and operator recovery actions.

### Observability & operations

- [ ] **MC78-21** Publish component SLI metrics for request rate, success/failure classes, latency distributions, saturation/resource pressure, retries, queue depth, and component-specific correctness/security events.
- [ ] **MC78-22** Produce structured logs with timestamp, severity, operation ID, workload/tenant identity, node/component version, resource identity, and stable error code; enforce redaction centrally.
- [ ] **MC78-23** Propagate distributed trace context across relevant calls and annotate spans with immutable artifact/resource identifiers without creating high-cardinality metric labels.
- [ ] **MC78-24** Expose liveness, readiness, dependency/degraded state, and version/build metadata; make health semantics safe for automated remediation.
- [ ] **MC78-25** Write operator runbooks for diagnosis, safe restart, data/state repair, quarantine/containment, rollback, capacity pressure, and evidence collection.

### Verification, certification & release

- [ ] **MC78-26** Add unit tests for normal, boundary, malformed, duplicate, empty, maximum-size, and unsupported inputs; assert stable errors and state invariants rather than only happy-path output.
- [ ] **MC78-27** Add integration tests with real adjacent dependencies or protocol-faithful test fixtures; verify version negotiation, authentication, timeouts, retries, and teardown.
- [ ] **MC78-28** Add negative/security tests for privilege bypass, path/identifier confusion, replay, race conditions, resource exhaustion, malicious dependency responses, and fail-open behavior.
- [ ] **MC78-29** Add fuzz/property tests for parsers, decoders, state transitions, persisted metadata, and policy inputs; retain regression cases for every discovered defect.
- [ ] **MC78-30** Run concurrency/race and fault-injection tests around all mutable state and crash boundaries; include restart/reconciliation verification.
- [ ] **MC78-31** Define performance and soak benchmarks with release budgets for throughput, tail latency, memory, disk/inode growth, CPU, network, and long-duration resource leaks.
- [ ] **MC78-32** Execute the supported platform/runtime/kernel/filesystem/registry matrix and retain machine-readable results tied to the exact source and artifact digest.
- [ ] **MC78-33** Require code review, security review for trust-boundary changes, SBOM/dependency review, vulnerability scan, signed release evidence, and documented exceptions before production certification.

### Component-specific capability controls

- [ ] **MC78-34** Resolve and verify **patch windows** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC78-35** Resolve and verify **CVE response** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC78-36** Resolve and verify **deprecation policy** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC78-37** Resolve and verify **supported-version lifetime** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.
- [ ] **MC78-38** Resolve and verify **emergency release process** end-to-end: define its input/state invariants, reject malformed or unauthorized use before mutation where applicable, bound resource consumption, emit structured telemetry/evidence, cover positive/negative/concurrency cases, and document rollback/recovery behavior.

### Deep technical controls

- [ ] **MC78-39** Bind SBOM/scanner results to exact image/artifact digests and record scanner database/version/freshness metadata.
- [ ] **MC78-40** Distinguish unscanned, scan-failed, scan-stale, vulnerability-present, and exception-approved states; do not collapse them into a boolean.
- [ ] **MC78-41** Exercise exception expiry and re-evaluation when scanner intelligence, exploitability data, or policy changes.
- [ ] **MC78-42** Define the artifact as part of the release contract: authoritative source, owner, review cadence, required approvals, and compatibility/versioning rules.
- [ ] **MC78-43** Add automated release checks that fail when the required governance artifact is absent, stale, malformed, or inconsistent with package metadata.
- [ ] **MC78-44** Retain change history and link material governance changes to release notes and migration/operational impact assessments.

### Definition of done / evidence gate

- [ ] **MC78-DOD-01** Architecture/design review is approved, with trust boundaries, authoritative state, dependency contracts, failure model, and compatibility assumptions recorded.
- [ ] **MC78-DOD-02** Implementation passes unit, integration, negative/security, concurrency, and fault-recovery tests appropriate to this component; all critical invariants are asserted in automation.
- [ ] **MC78-DOD-03** Operational telemetry, health semantics, runbooks, and capacity/resource limits are deployed and validated in a production-like environment.
- [ ] **MC78-DOD-04** Security review confirms least privilege, fail-closed policy where required, secret handling, auditability, and absence of known unmitigated critical/high issues.
- [ ] **MC78-DOD-05** Release evidence identifies source revision, build/artifact digest, dependency/SBOM state, test results, supported-platform results, configuration/policy version, and any approved exceptions.

---

## Estate-wide final certification checklist

- [ ] **E-01** Restore or intentionally remove the `MASTER.md` distribution contract and make the chosen state enforceable in CI/release validation.
- [ ] **E-02** Restore `pk_core` in the complete estate checkout and execute the three skipped conformance tests; no isolated-package pass may substitute for estate-wide certification.
- [ ] **E-03** Re-run the v4.2.0 standalone suite in normal and optimized Python modes and retain immutable output with interpreter/build metadata.
- [ ] **E-04** Execute the complete OCI/registry/runtime conformance and integration matrix for every declared supported tuple.
- [ ] **E-05** Execute security isolation, malicious-layer, fuzzing, race, fault-injection, and resource-exhaustion campaigns against the release candidate.
- [ ] **E-06** Perform backup/restore, node loss, registry outage, policy-engine outage, corrupted-content, and rolling-upgrade/rollback exercises.
- [ ] **E-07** Verify that all P0/P1/P2 exceptions are explicit, owned, approved, expiring, and represented in the release evidence.
- [ ] **E-08** Sign and archive the final certification record, SBOM, provenance, test evidence, compatibility matrix, release notes, migration guidance, and SHA-256 digests.
