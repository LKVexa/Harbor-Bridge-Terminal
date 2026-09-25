# INV-24 MicroVM Runtime v4.2.0 — Missing Component Implementation & Closure Checklist

**Source:** second-pass audit in `MISSING_COMPONENTS.md` after the v4.2.0 hardening pass.  
**Scope:** all 64 component groups that remained absent or not independently verifiable in the supplied archive.  
**Purpose:** turn every gap into an implementation-ready engineering work package with explicit acceptance and evidence requirements.  

## How to use this checklist

- Treat every checkbox as **open** until concrete repository/runtime evidence exists. A prose claim, skipped test, or external framework assumption is not closure.
- **P0** = production-blocking core safety/readiness work; **P1** = required production maturity work; **P2** = conditional/optimization/documentation work that can be scheduled according to deployment profile, but must still be dispositioned.
- Use status values `TODO`, `IN_PROGRESS`, `BLOCKED`, `PASS`, `FAIL`, `NOT_APPLICABLE`, or `WAIVED`. `NOT_APPLICABLE` and `WAIVED` require rationale, owner, approver, and (for waivers) expiry.
- Suggested paths are implementation guidance, not mandatory filenames. If the repository uses different paths, update the traceability matrix so the equivalent artifact is mechanically resolvable.
- Completion requires both **implementation** and **verification evidence** against the immutable release candidate. Skipped tests are `BLOCKED/NOT_TESTED`, never `PASS`.

## Universal definition of done (applies to every one of the 64 components)

- [ ] Assign an accountable implementation owner, reviewer/approver, target release, dependency list, and risk/priority.
- [ ] Add stable requirement/task IDs and link them to affected `INV-24-Cxxx` controls in the traceability matrix.
- [ ] Document public/internal interfaces, state owned, trust boundaries, resource limits, failure modes, and compatibility assumptions introduced by the component.
- [ ] Use explicit validation, bounded inputs/resources, and stable structured errors; do not use Python `assert` for runtime safety/security enforcement.
- [ ] Define safe timeout/cancellation/retry/restart semantics and deterministic cleanup for every side effect introduced.
- [ ] Apply least privilege and fail closed for security-critical missing/invalid identity, authorization, integrity, policy, key, or capability prerequisites.
- [ ] Add unit/contract/integration/negative tests appropriate to the component; add property/fuzz/concurrency/fault tests where the attack/failure surface warrants them.
- [ ] Add metrics/logs/traces/audit events needed to operate and diagnose the component, with cardinality/size/redaction limits.
- [ ] Add operator documentation/runbook changes, rollback/emergency-disable behavior, and incident/escalation references where production operation is affected.
- [ ] Produce machine-readable PASS/FAIL evidence tied to exact source commit, package version, dependency/artifact digests, test environment, and timestamp.
- [ ] Validate on a clean immutable release candidate and run the production exit gate; no component is “done” only because a developer workstation test passed.

## Evidence record minimum fields

Every closed task should be representable by an evidence record containing: `component_id`, `task_id`, `control_ids`, `release_version`, `source_commit`, `artifact_digests`, `environment_profile`, `test_or_review_id`, `result`, `started_at`, `ended_at`, `tool_versions`, `evidence_uri/path`, `evidence_sha256`, `owner`, `approver`, and optional `waiver_id`/`notes`.

---

# Critical external/runtime integration gaps

## MC-001 — Actual Firecracker/VMM adapter and pinned runtime binary

**Priority:** P0  
**Source checks:** `C031, C040`  
**Primary discipline:** Runtime / Platform Engineering  
**Audit gap:** no Firecracker executable, SDK/adapter, version pin, checksum, launch wrapper, or process supervision code. `MicroVM` remains a domain/state model, not a VMM launcher.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/adapters/firecracker.py` — create or map to an equivalent traceable artifact.
- [ ] `inv24_microvm_runtime/supervision/vmm_process.py` — create or map to an equivalent traceable artifact.
- [ ] `artifacts/firecracker/manifest.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/integration/test_firecracker_adapter.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-001-I01** — Pin one approved Firecracker release by immutable version and SHA-256 (or stronger) digest; prohibit floating URLs, `latest`, PATH-only discovery, and unverified replacement binaries.
- [ ] **MC-001-I02** — Implement a typed adapter that translates `MicroVM` configuration into Firecracker machine-config, boot-source, drive, network, vsock, and lifecycle API calls over a bounded Unix-domain socket path.
- [ ] **MC-001-I03** — Add a process supervisor that starts the VMM without `shell=True`, records PID/start time/version, captures bounded stdout/stderr, detects premature exit, terminates on timeout, and reaps children/orphan sockets.
- [ ] **MC-001-I04** — Map VMM states and errors into stable INV-24 lifecycle/error codes; distinguish configuration rejection, host/KVM failure, guest boot failure, timeout, process crash, and cleanup failure.
- [ ] **MC-001-I05** — Keep the existing closed `MINIMAL_DEVICE_MODEL` authoritative: the adapter must never synthesize or pass through undeclared devices and must reject unsupported Firecracker API fields before process launch.
- [ ] **MC-001-I06** — Implement deterministic cleanup for API socket, TAP/vsock resources, temporary config, PID state, and guest process on stop, failed boot, cancellation, and caller crash/restart.
- [ ] **MC-001-Q07** — Define a narrow typed adapter boundary; keep external/runtime-specific behavior out of the pure `MicroVM` domain state machine.
- [ ] **MC-001-Q08** — Make all external calls deadline-bound, cancellation-aware where supported, and mapped to stable machine-readable errors with retryability explicitly declared.
- [ ] **MC-001-Q09** — Fail closed before unsafe side effects when capability/version/identity/integrity prerequisites are not satisfied.
- [ ] **MC-001-Q10** — Instrument lifecycle duration, error reason, dependency health, resource ownership, and cleanup outcome without exposing secrets or unbounded identifiers.
- [ ] **MC-001-Q11** — Add positive, negative, timeout, crash, cleanup, and version-mismatch tests; a skipped test is NOT_TESTED/BLOCKED, not PASS.
- [ ] **MC-001-Q12** — Record dependency versions/digests, host capability profile, test command/result, and artifact hashes in release evidence.

### Verification and acceptance checklist

- [ ] **MC-001-A01** — A real guest can be created, configured, booted, queried, and destroyed through the adapter on a KVM host with no orphaned process/socket/device resources.
- [ ] **MC-001-A02** — A modified/unapproved Firecracker binary and an out-of-model device are both rejected before execution.

### Required closure evidence

- [ ] **MC-001-E01** — Record traceability from `MC-001` and `C031, C040` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-001-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-001-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-001-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-001-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-001` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-002 — Hardware virtualization integration

**Priority:** P0  
**Source checks:** `C003, C030, C083`  
**Primary discipline:** Runtime / Platform Engineering  
**Audit gap:** no executable adapter/test for INV-23/KVM, `/dev/kvm`, CPU feature detection, or virtualization availability/failure handling.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/virtualization/kvm.py` — create or map to an equivalent traceable artifact.
- [ ] `docs/KVM_PREREQUISITES.md` — create or map to an equivalent traceable artifact.
- [ ] `tests/integration/test_kvm_preflight.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-002-I01** — Perform a real `/dev/kvm` preflight: existence, open permissions, KVM API version, required ioctls/capabilities, and actionable error classification; do not treat CPU flags alone as proof of usability.
- [ ] **MC-002-I02** — Validate x86_64/aarch64-specific prerequisites and expose the detected architecture/capability set to admission and health surfaces.
- [ ] **MC-002-I03** — Define behavior for nested virtualization, containers without KVM passthrough, permission-denied, module-unavailable, and incompatible-host cases; security-critical ambiguity must fail closed.
- [ ] **MC-002-I04** — Integrate the INV-23 boundary through a narrow adapter instead of embedding host-specific detection throughout lifecycle code.
- [ ] **MC-002-I05** — Add tests using a real KVM-capable host plus deterministic mocks for no-device, permission-denied, unsupported capability, and revoked-device scenarios.
- [ ] **MC-002-Q06** — Define a narrow typed adapter boundary; keep external/runtime-specific behavior out of the pure `MicroVM` domain state machine.
- [ ] **MC-002-Q07** — Make all external calls deadline-bound, cancellation-aware where supported, and mapped to stable machine-readable errors with retryability explicitly declared.
- [ ] **MC-002-Q08** — Fail closed before unsafe side effects when capability/version/identity/integrity prerequisites are not satisfied.
- [ ] **MC-002-Q09** — Instrument lifecycle duration, error reason, dependency health, resource ownership, and cleanup outcome without exposing secrets or unbounded identifiers.
- [ ] **MC-002-Q10** — Add positive, negative, timeout, crash, cleanup, and version-mismatch tests; a skipped test is NOT_TESTED/BLOCKED, not PASS.
- [ ] **MC-002-Q11** — Record dependency versions/digests, host capability profile, test command/result, and artifact hashes in release evidence.

### Verification and acceptance checklist

- [ ] **MC-002-A01** — KVM-capable hosts are accepted only after ioctl capability checks; unavailable/permission-denied hosts return deterministic non-retryable/retryable classifications as specified.
- [ ] **MC-002-A02** — Host capability data is visible to admission/health and covered by real-host integration evidence.

### Required closure evidence

- [ ] **MC-002-E01** — Record traceability from `MC-002` and `C003, C030, C083` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-002-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-002-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-002-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-002-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-002` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-003 — Device backend integration

**Priority:** P0  
**Source checks:** `C003, C021, C030, C083`  
**Primary discipline:** Runtime / Platform Engineering  
**Audit gap:** no concrete INV-25 virtio-net/block/vsock/serial/RTC backend bindings or end-to-end device tests.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/devices/` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_MICROVM_DEVICE_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/integration/test_device_backends.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-003-I01** — Define a typed device specification for each permitted device (`virtio-net`, `virtio-block`, `virtio-vsock`, `serial`, `rtc`) with required/optional fields, limits, ownership, and lifecycle semantics.
- [ ] **MC-003-I02** — Implement backend binding to INV-25/Firecracker with stable device IDs, deterministic attach order, and no dynamic expansion beyond the permitted device set.
- [ ] **MC-003-I03** — For block devices, validate path ownership, read-only/root semantics, size/format constraints, symlink handling, and cross-tenant reuse; for networking, validate TAP ownership, namespace, MAC/IP uniqueness, and teardown.
- [ ] **MC-003-I04** — For vsock, allocate collision-resistant guest CIDs with release/reconciliation; document serial/RTC behavior and whether they are explicit or implicit VMM capabilities.
- [ ] **MC-003-I05** — Create end-to-end tests that boot a guest with every supported device combination and negative tests for unsupported, duplicate, malformed, cross-tenant, and unavailable backends.
- [ ] **MC-003-Q06** — Define a narrow typed adapter boundary; keep external/runtime-specific behavior out of the pure `MicroVM` domain state machine.
- [ ] **MC-003-Q07** — Make all external calls deadline-bound, cancellation-aware where supported, and mapped to stable machine-readable errors with retryability explicitly declared.
- [ ] **MC-003-Q08** — Fail closed before unsafe side effects when capability/version/identity/integrity prerequisites are not satisfied.
- [ ] **MC-003-Q09** — Instrument lifecycle duration, error reason, dependency health, resource ownership, and cleanup outcome without exposing secrets or unbounded identifiers.
- [ ] **MC-003-Q10** — Add positive, negative, timeout, crash, cleanup, and version-mismatch tests; a skipped test is NOT_TESTED/BLOCKED, not PASS.
- [ ] **MC-003-Q11** — Record dependency versions/digests, host capability profile, test command/result, and artifact hashes in release evidence.

### Verification and acceptance checklist

- [ ] **MC-003-A01** — Every permitted device has at least one real end-to-end guest test and every non-permitted device request is rejected before VMM launch.
- [ ] **MC-003-A02** — Device teardown leaves no tenant-owned TAP/vsock/block attachment available to a later tenant.

### Required closure evidence

- [ ] **MC-003-E01** — Record traceability from `MC-003` and `C003, C021, C030, C083` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-003-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-003-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-003-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-003-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-003` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-004 — Snapshot integration

**Priority:** P1  
**Source checks:** `C003, C030, C057, C083, C095`  
**Primary discipline:** Runtime / Platform Engineering  
**Audit gap:** no INV-26 snapshot/restore API, snapshot format validation, crash consistency, or restore tests.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/snapshot/` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_MICROVM_SNAPSHOT_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/integration/test_snapshot_restore.py` — create or map to an equivalent traceable artifact.
- [ ] `docs/SNAPSHOT_RECOVERY.md` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-004-I01** — Define a versioned snapshot metadata schema containing runtime version, Firecracker version, CPU architecture/features, kernel/rootfs digests, device model, tenant/workload identity, memory/state artifact digests, and creation epoch.
- [ ] **MC-004-I02** — Implement create/load/validate/restore APIs that use temporary files plus atomic rename and verify all metadata/digests before restore.
- [ ] **MC-004-I03** — Bind snapshots to tenant/workload authorization and reject cross-tenant restore, stale ownership epochs, incompatible device models, architecture mismatch, or unsupported Firecracker versions.
- [ ] **MC-004-I04** — Define crash consistency: ordering of pause, flush, snapshot creation, fsync, metadata commit, resume, and cleanup; partially written snapshots must be detectable and unusable.
- [ ] **MC-004-I05** — Exercise cold restore, repeated restore, corrupt metadata, truncated memory file, missing artifact, host crash during snapshot, and incompatible-version cases.
- [ ] **MC-004-Q06** — Define a narrow typed adapter boundary; keep external/runtime-specific behavior out of the pure `MicroVM` domain state machine.
- [ ] **MC-004-Q07** — Make all external calls deadline-bound, cancellation-aware where supported, and mapped to stable machine-readable errors with retryability explicitly declared.
- [ ] **MC-004-Q08** — Fail closed before unsafe side effects when capability/version/identity/integrity prerequisites are not satisfied.
- [ ] **MC-004-Q09** — Instrument lifecycle duration, error reason, dependency health, resource ownership, and cleanup outcome without exposing secrets or unbounded identifiers.
- [ ] **MC-004-Q10** — Add positive, negative, timeout, crash, cleanup, and version-mismatch tests; a skipped test is NOT_TESTED/BLOCKED, not PASS.
- [ ] **MC-004-Q11** — Record dependency versions/digests, host capability profile, test command/result, and artifact hashes in release evidence.

### Verification and acceptance checklist

- [ ] **MC-004-A01** — Snapshot artifacts are digest-verified, version/tenant bound, and recover successfully after a clean restart.
- [ ] **MC-004-A02** — Truncated/corrupt/incompatible/cross-tenant snapshots are rejected without partially launching a guest.

### Required closure evidence

- [ ] **MC-004-E01** — Record traceability from `MC-004` and `C003, C030, C057, C083, C095` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-004-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-004-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-004-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-004-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-004` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-005 — Execution-plane admission integration

**Priority:** P0  
**Source checks:** `C003, C024, C030, C054, C083`  
**Primary discipline:** Runtime / Platform Engineering  
**Audit gap:** no PLN-04 adapter, admission controller, capability token validation, queueing, or load-shedding implementation.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/admission/` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_MICROVM_ADMISSION_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/integration/test_execution_plane_admission.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-005-I01** — Define a PLN-04 admission request/response contract carrying tenant/workload identity, requested resources/devices, environment/site, capability token, deadline, idempotency key, and policy context.
- [ ] **MC-005-I02** — Validate authentication, authorization/capabilities, quotas, host/KVM readiness, artifact approval, resource availability, and device compatibility before any VMM side effect.
- [ ] **MC-005-I03** — Implement bounded admission queues with per-tenant fairness, deadlines, cancellation, overload rejection, and stable machine-readable rejection codes.
- [ ] **MC-005-I04** — Make admission idempotent: retries for the same operation key must not create duplicate microVMs; persist or reconcile the operation result across controller restart.
- [ ] **MC-005-I05** — Add integration tests against the real/stub PLN-04 contract for accepted, rejected, duplicate, timed-out, cancelled, overloaded, and stale-capability requests.
- [ ] **MC-005-Q06** — Define a narrow typed adapter boundary; keep external/runtime-specific behavior out of the pure `MicroVM` domain state machine.
- [ ] **MC-005-Q07** — Make all external calls deadline-bound, cancellation-aware where supported, and mapped to stable machine-readable errors with retryability explicitly declared.
- [ ] **MC-005-Q08** — Fail closed before unsafe side effects when capability/version/identity/integrity prerequisites are not satisfied.
- [ ] **MC-005-Q09** — Instrument lifecycle duration, error reason, dependency health, resource ownership, and cleanup outcome without exposing secrets or unbounded identifiers.
- [ ] **MC-005-Q10** — Add positive, negative, timeout, crash, cleanup, and version-mismatch tests; a skipped test is NOT_TESTED/BLOCKED, not PASS.
- [ ] **MC-005-Q11** — Record dependency versions/digests, host capability profile, test command/result, and artifact hashes in release evidence.

### Verification and acceptance checklist

- [ ] **MC-005-A01** — Admission cannot create duplicate VMs under request retry/controller restart and enforces quota/capability before VMM side effects.
- [ ] **MC-005-A02** — Overload produces bounded queueing plus explicit rejection rather than memory/latency runaway.

### Required closure evidence

- [ ] **MC-005-E01** — Record traceability from `MC-005` and `C003, C024, C030, C054, C083` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-005-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-005-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-005-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-005-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-005` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-006 — High-performance I/O integration

**Priority:** P1  
**Source checks:** `C003, C030, C061-C066, C083`  
**Primary discipline:** Runtime / Platform Engineering  
**Audit gap:** INV-35 remains optional and absent; no local datapath implementation or throughput evidence.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/io/` — create or map to an equivalent traceable artifact.
- [ ] `benchmarks/io/` — create or map to an equivalent traceable artifact.
- [ ] `tests/integration/test_inv35_datapath.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-006-I01** — Define an optional INV-35 datapath capability interface and negotiate it explicitly; absence must produce a documented fallback or admission rejection, never silent partial acceleration.
- [ ] **MC-006-I02** — Validate guest-memory regions, descriptor bounds, queue ownership, IOMMU/virtio assumptions, and maximum queue/descriptor sizes before exposing buffers to the datapath.
- [ ] **MC-006-I03** — Instrument copies, syscalls, context switches, queue occupancy, batch size, bytes/packets per second, and tail latency to prove the acceleration path actually improves the target workload.
- [ ] **MC-006-I04** — Implement teardown/recovery for stalled queues, backend restart, guest termination, and host-network loss without leaking mapped memory or cross-tenant buffers.
- [ ] **MC-006-I05** — Benchmark accelerated versus baseline paths under small/large packets, steady/burst load, saturation, and multi-tenant contention; record when acceleration should be disabled.
- [ ] **MC-006-Q06** — Define a narrow typed adapter boundary; keep external/runtime-specific behavior out of the pure `MicroVM` domain state machine.
- [ ] **MC-006-Q07** — Make all external calls deadline-bound, cancellation-aware where supported, and mapped to stable machine-readable errors with retryability explicitly declared.
- [ ] **MC-006-Q08** — Fail closed before unsafe side effects when capability/version/identity/integrity prerequisites are not satisfied.
- [ ] **MC-006-Q09** — Instrument lifecycle duration, error reason, dependency health, resource ownership, and cleanup outcome without exposing secrets or unbounded identifiers.
- [ ] **MC-006-Q10** — Add positive, negative, timeout, crash, cleanup, and version-mismatch tests; a skipped test is NOT_TESTED/BLOCKED, not PASS.
- [ ] **MC-006-Q11** — Record dependency versions/digests, host capability profile, test command/result, and artifact hashes in release evidence.

### Verification and acceptance checklist

- [ ] **MC-006-A01** — Accelerated mode demonstrates a documented throughput/CPU/latency benefit on at least one approved profile without violating isolation.
- [ ] **MC-006-A02** — INV-35 absence/failure follows the documented fallback/rejection policy and remains observable.

### Required closure evidence

- [ ] **MC-006-E01** — Record traceability from `MC-006` and `C003, C030, C061-C066, C083` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-006-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-006-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-006-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-006-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-006` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Architecture, requirements, ownership, and traceability gaps

## MC-007 — Accountable owner/escalation artifact

**Priority:** P0  
**Source checks:** `C009`  
**Primary discipline:** Architecture / Systems Engineering  
**Audit gap:** no OWNER/CODEOWNERS/on-call/escalation document.

### Suggested repository artifacts

- [ ] `OWNERS.md` — create or map to an equivalent traceable artifact.
- [ ] `CODEOWNERS` — create or map to an equivalent traceable artifact.
- [ ] `docs/ESCALATION.md` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-007-I01** — Name one accountable service owner/team, one code owner, one security owner, and one operational/on-call escalation destination; avoid role placeholders without an accountable identity.
- [ ] **MC-007-I02** — Define ownership boundaries for INV-23/25/26/35 and PLN-04 so cross-component incidents have an unambiguous first responder and handoff path.
- [ ] **MC-007-I03** — Add severity-based escalation timing, backup/secondary owner, after-hours path, and security-incident escalation path.
- [ ] **MC-007-I04** — Configure repository CODEOWNERS/review protection for runtime, security, schemas, CI/release gates, and supply-chain policy paths.
- [ ] **MC-007-I05** — Require periodic owner review and an automated check that owner/escalation documents exist and are non-empty before production release.
- [ ] **MC-007-Q06** — Give the artifact a version/owner/review state and define which source is authoritative when documents disagree.
- [ ] **MC-007-Q07** — Use stable identifiers and machine-readable representations for requirements/interfaces wherever downstream automation depends on them.
- [ ] **MC-007-Q08** — Cross-link the artifact to implementation, tests, evidence, and affected C-checks; eliminate unsupported “covered elsewhere” statements.
- [ ] **MC-007-Q09** — Add CI validation for presence, syntax, broken links/references, stale versions, and required approvals.
- [ ] **MC-007-Q10** — Define a change-control rule: architecture/requirement/interface changes must trigger compatibility, threat-model, test, and runbook review as applicable.
- [ ] **MC-007-Q11** — Archive the exact reviewed artifact revision with each production release.

### Verification and acceptance checklist

- [ ] **MC-007-A01** — Repository and on-call ownership resolve to an active accountable path and protected files require the designated reviewers.
- [ ] **MC-007-A02** — An escalation drill reaches the correct owner for runtime and security incidents.

### Required closure evidence

- [ ] **MC-007-E01** — Record traceability from `MC-007` and `C009` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-007-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-007-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-007-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-007-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-007` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-008 — Approved architecture decision record

**Priority:** P0  
**Source checks:** `C010`  
**Primary discipline:** Architecture / Systems Engineering  
**Audit gap:** no ADR selecting Firecracker with alternatives, rationale, constraints, consequences, and approval record.

### Suggested repository artifacts

- [ ] `docs/adr/ADR-0001-firecracker-runtime.md` — create or map to an equivalent traceable artifact.
- [ ] `docs/adr/README.md` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-008-I01** — Write an ADR that states the decision to use Firecracker, the isolation/startup objectives, and the constraints inherited from the minimal device model and boot budget.
- [ ] **MC-008-I02** — Compare credible alternatives (for example Cloud Hypervisor, QEMU/KVM, Kata-style stacks, or no-VM isolation) against attack surface, startup time, device model, operational complexity, portability, snapshot semantics, and supportability.
- [ ] **MC-008-I03** — Document security assumptions, required host kernel/KVM features, architecture support, failure modes, operational consequences, and conditions that would force reconsideration.
- [ ] **MC-008-I04** — Record decision status, authors, reviewers/approvers, date, supersession rules, and links to benchmark/threat-model evidence rather than treating the ADR as a narrative-only document.
- [ ] **MC-008-I05** — Add an ADR lint/review gate requiring an approved current ADR before Firecracker/runtime version changes are promoted.
- [ ] **MC-008-Q06** — Give the artifact a version/owner/review state and define which source is authoritative when documents disagree.
- [ ] **MC-008-Q07** — Use stable identifiers and machine-readable representations for requirements/interfaces wherever downstream automation depends on them.
- [ ] **MC-008-Q08** — Cross-link the artifact to implementation, tests, evidence, and affected C-checks; eliminate unsupported “covered elsewhere” statements.
- [ ] **MC-008-Q09** — Add CI validation for presence, syntax, broken links/references, stale versions, and required approvals.
- [ ] **MC-008-Q10** — Define a change-control rule: architecture/requirement/interface changes must trigger compatibility, threat-model, test, and runbook review as applicable.
- [ ] **MC-008-Q11** — Archive the exact reviewed artifact revision with each production release.

### Verification and acceptance checklist

- [ ] **MC-008-A01** — ADR is approved, current, linked to measured/threat evidence, and names conditions that trigger reconsideration.
- [ ] **MC-008-A02** — Runtime technology/version changes cannot pass review without ADR impact assessment.

### Required closure evidence

- [ ] **MC-008-E01** — Record traceability from `MC-008` and `C010` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-008-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-008-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-008-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-008-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-008` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-009 — Environment-specific SHALL requirements

**Priority:** P0  
**Source checks:** `C011-C014, C018-C019`  
**Primary discipline:** Architecture / Systems Engineering  
**Audit gap:** no standalone normative requirements specification covering cloud/datacenter/near-edge/far-edge, degraded/network-offline semantics, conflict precedence, and terminal/retryable outcomes.

### Suggested repository artifacts

- [ ] `requirements/INV24_REQUIREMENTS.yaml` — create or map to an equivalent traceable artifact.
- [ ] `requirements/ENVIRONMENT_MATRIX.md` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-009-I01** — Create uniquely identified normative requirements using SHALL/SHALL NOT/MAY language; each requirement must be objectively testable and map to one or more C001-C100 controls.
- [ ] **MC-009-I02** — Define separate cloud, datacenter, near-edge, and far-edge profiles for host assumptions, control-plane reachability, artifact availability, device/network model, boot budget, capacity, and power constraints.
- [ ] **MC-009-I03** — Specify success, partial/degraded success, retryable failure, terminal failure, timeout, cancellation, and operator intervention semantics for every lifecycle operation.
- [ ] **MC-009-I04** — Define precedence when security, residency, isolation, SLO, availability, and cost conflict; security/isolation fail-closed rules must be explicit.
- [ ] **MC-009-I05** — Define offline/intermittent-network behavior, cached-policy validity windows, artifact/key freshness requirements, and what operations are forbidden without control-plane contact.
- [ ] **MC-009-Q06** — Give the artifact a version/owner/review state and define which source is authoritative when documents disagree.
- [ ] **MC-009-Q07** — Use stable identifiers and machine-readable representations for requirements/interfaces wherever downstream automation depends on them.
- [ ] **MC-009-Q08** — Cross-link the artifact to implementation, tests, evidence, and affected C-checks; eliminate unsupported “covered elsewhere” statements.
- [ ] **MC-009-Q09** — Add CI validation for presence, syntax, broken links/references, stale versions, and required approvals.
- [ ] **MC-009-Q10** — Define a change-control rule: architecture/requirement/interface changes must trigger compatibility, threat-model, test, and runbook review as applicable.
- [ ] **MC-009-Q11** — Archive the exact reviewed artifact revision with each production release.

### Verification and acceptance checklist

- [ ] **MC-009-A01** — Every normative requirement is uniquely testable and environment/degraded/conflict semantics contain no undefined “best effort” behavior.
- [ ] **MC-009-A02** — Requirements lint and traceability checks pass with zero orphan P0 SHALLs.

### Required closure evidence

- [ ] **MC-009-E01** — Record traceability from `MC-009` and `C011-C014, C018-C019` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-009-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-009-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-009-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-009-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-009` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-010 — Requirements traceability matrix

**Priority:** P0  
**Source checks:** `C020`  
**Primary discipline:** Architecture / Systems Engineering  
**Audit gap:** no machine-readable mapping from all 100 checks to concrete code/test/evidence artifacts.

### Suggested repository artifacts

- [ ] `requirements/TRACEABILITY.yaml` — create or map to an equivalent traceable artifact.
- [ ] `tools/validate_traceability.py` — create or map to an equivalent traceable artifact.
- [ ] `evidence/traceability-report.json` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-010-I01** — Create one row per C001-C100 requirement with requirement text/ID, design artifact, implementation symbol/file, verification test, evidence artifact, owner, status, and waiver ID when applicable.
- [ ] **MC-010-I02** — Make every path/symbol mechanically resolvable; prohibit entries such as “covered by framework” without a concrete artifact and version.
- [ ] **MC-010-I03** — Validate one-to-many relationships (a requirement may have multiple tests/evidence) and detect orphan code/tests that claim compliance without a requirement link.
- [ ] **MC-010-I04** — Generate traceability coverage metrics and fail the production gate for missing P0 links, stale paths, failed evidence, or expired waivers.
- [ ] **MC-010-I05** — Record the exact repository commit, dependency lock, Firecracker digest, host test profile, and evidence timestamp so traceability is reproducible.
- [ ] **MC-010-Q06** — Give the artifact a version/owner/review state and define which source is authoritative when documents disagree.
- [ ] **MC-010-Q07** — Use stable identifiers and machine-readable representations for requirements/interfaces wherever downstream automation depends on them.
- [ ] **MC-010-Q08** — Cross-link the artifact to implementation, tests, evidence, and affected C-checks; eliminate unsupported “covered elsewhere” statements.
- [ ] **MC-010-Q09** — Add CI validation for presence, syntax, broken links/references, stale versions, and required approvals.
- [ ] **MC-010-Q10** — Define a change-control rule: architecture/requirement/interface changes must trigger compatibility, threat-model, test, and runbook review as applicable.
- [ ] **MC-010-Q11** — Archive the exact reviewed artifact revision with each production release.

### Verification and acceptance checklist

- [ ] **MC-010-A01** — All 100 controls have resolvable implementation/test/evidence mappings or explicit BLOCKED/WAIVED state.
- [ ] **MC-010-A02** — Traceability validator fails on stale paths, missing evidence, expired waivers, or mismatched release identity.

### Required closure evidence

- [ ] **MC-010-E01** — Record traceability from `MC-010` and `C020` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-010-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-010-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-010-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-010-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-010` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-011 — Compatibility/versioning policy

**Priority:** P0  
**Source checks:** `C016, C027, C093`  
**Primary discipline:** Architecture / Systems Engineering  
**Audit gap:** no supported-version matrix for Python, `pk_core`, Firecracker, kernel/KVM, adjacent INV/PLN components, architectures, or schema compatibility.

### Suggested repository artifacts

- [ ] `COMPATIBILITY.md` — create or map to an equivalent traceable artifact.
- [ ] `compatibility/matrix.yaml` — create or map to an equivalent traceable artifact.
- [ ] `tests/compatibility/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-011-I01** — Define supported ranges/exact pins for Python, `pk_core`, Firecracker, host kernel/KVM, CPU architectures, guest kernel/rootfs format, and INV-23/25/26/35 + PLN-04 interface versions.
- [ ] **MC-011-I02** — State compatibility policy for schema major/minor changes, additive fields, deprecated fields, unknown enum values, and peer version skew.
- [ ] **MC-011-I03** — Define upgrade/downgrade sequencing and the maximum supported skew during staged rollout; identify combinations that must hard-fail admission.
- [ ] **MC-011-I04** — Automate matrix validation in CI using representative host/runtime combinations and persist results by release.
- [ ] **MC-011-I05** — Define deprecation and removal windows plus how operators are warned before a supported combination becomes unsupported.
- [ ] **MC-011-Q06** — Give the artifact a version/owner/review state and define which source is authoritative when documents disagree.
- [ ] **MC-011-Q07** — Use stable identifiers and machine-readable representations for requirements/interfaces wherever downstream automation depends on them.
- [ ] **MC-011-Q08** — Cross-link the artifact to implementation, tests, evidence, and affected C-checks; eliminate unsupported “covered elsewhere” statements.
- [ ] **MC-011-Q09** — Add CI validation for presence, syntax, broken links/references, stale versions, and required approvals.
- [ ] **MC-011-Q10** — Define a change-control rule: architecture/requirement/interface changes must trigger compatibility, threat-model, test, and runbook review as applicable.
- [ ] **MC-011-Q11** — Archive the exact reviewed artifact revision with each production release.

### Verification and acceptance checklist

- [ ] **MC-011-A01** — CI publishes a tested support matrix and admission/upgrade procedures reject unsupported version combinations.
- [ ] **MC-011-A02** — At least one mixed-version rollout/downgrade scenario is tested per supported skew policy.

### Required closure evidence

- [ ] **MC-011-E01** — Record traceability from `MC-011` and `C016, C027, C093` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-011-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-011-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-011-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-011-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-011` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-012 — Complete interface inventory

**Priority:** P0  
**Source checks:** `C021`  
**Primary discipline:** Architecture / Systems Engineering  
**Audit gap:** contract lists logical interfaces but no exhaustive boundary catalog covering process, socket, file, device, hypervisor, metadata, control-plane, and host-kernel boundaries.

### Suggested repository artifacts

- [ ] `docs/INTERFACE_INVENTORY.md` — create or map to an equivalent traceable artifact.
- [ ] `interfaces/inventory.yaml` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-012-I01** — Inventory every boundary: Python API, Firecracker UDS API, process/PID, filesystem paths, `/dev/kvm`, TAP/TUN, block images, vsock, serial, metrics/logs/traces, config files, artifact stores, identity/KMS/policy services, PLN-04, and peer INV components.
- [ ] **MC-012-I02** — For each boundary record direction, initiator, authentication, authorization, schema/protocol/version, transport, timeout/retry semantics, resource limits, data classification, and failure behavior.
- [ ] **MC-012-I03** — Document trust-boundary crossings and privilege changes (host root/jailer user, namespaces, device nodes) and link them to threat-model controls.
- [ ] **MC-012-I04** — Mark optional versus mandatory interfaces and startup/admission behavior when each optional dependency is unavailable.
- [ ] **MC-012-I05** — Add a machine-readable inventory and CI check that public schemas/adapters cannot be added without a corresponding inventory entry.
- [ ] **MC-012-Q06** — Give the artifact a version/owner/review state and define which source is authoritative when documents disagree.
- [ ] **MC-012-Q07** — Use stable identifiers and machine-readable representations for requirements/interfaces wherever downstream automation depends on them.
- [ ] **MC-012-Q08** — Cross-link the artifact to implementation, tests, evidence, and affected C-checks; eliminate unsupported “covered elsewhere” statements.
- [ ] **MC-012-Q09** — Add CI validation for presence, syntax, broken links/references, stale versions, and required approvals.
- [ ] **MC-012-Q10** — Define a change-control rule: architecture/requirement/interface changes must trigger compatibility, threat-model, test, and runbook review as applicable.
- [ ] **MC-012-Q11** — Archive the exact reviewed artifact revision with each production release.

### Verification and acceptance checklist

- [ ] **MC-012-A01** — Every externally reachable or privileged boundary appears in both human and machine-readable inventory with trust/limit semantics.
- [ ] **MC-012-A02** — Adding a new adapter/schema/boundary without inventory update fails CI.

### Required closure evidence

- [ ] **MC-012-E01** — Record traceability from `MC-012` and `C021` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-012-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-012-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-012-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-012-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-012` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-013 — Typed external schemas

**Priority:** P0  
**Source checks:** `C022, C026, C029, C082`  
**Primary discipline:** Architecture / Systems Engineering  
**Audit gap:** dicts carry schema names, but no JSON Schema/Protobuf/WIT/OpenAPI definitions, structured error schema, fixtures, or schema conformance tests.

### Suggested repository artifacts

- [ ] `schemas/*.json` — create or map to an equivalent traceable artifact.
- [ ] `schemas/errors/PK_ERROR_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `fixtures/contracts/` — create or map to an equivalent traceable artifact.
- [ ] `tests/contracts/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-013-I01** — Provide versioned JSON Schema/Protobuf/WIT/OpenAPI definitions for create, boot, lifecycle, status, health, errors, admission, device, snapshot, audit, and decision records exposed outside the module.
- [ ] **MC-013-I02** — Define exact types, ranges, max lengths, enum values, required/optional fields, `additionalProperties` policy, canonical identifiers, timestamps, and forward-compatibility rules.
- [ ] **MC-013-I03** — Create a structured error envelope with stable code, retryability, operation ID, human-safe message, machine detail, cause category, and redacted diagnostic reference.
- [ ] **MC-013-I04** — Create golden valid/invalid fixtures and cross-version compatibility fixtures; validate both producer and consumer against them.
- [ ] **MC-013-I05** — Generate or validate runtime serializers from schemas and reject schema drift between hand-written dictionaries and published contracts.
- [ ] **MC-013-Q06** — Give the artifact a version/owner/review state and define which source is authoritative when documents disagree.
- [ ] **MC-013-Q07** — Use stable identifiers and machine-readable representations for requirements/interfaces wherever downstream automation depends on them.
- [ ] **MC-013-Q08** — Cross-link the artifact to implementation, tests, evidence, and affected C-checks; eliminate unsupported “covered elsewhere” statements.
- [ ] **MC-013-Q09** — Add CI validation for presence, syntax, broken links/references, stale versions, and required approvals.
- [ ] **MC-013-Q10** — Define a change-control rule: architecture/requirement/interface changes must trigger compatibility, threat-model, test, and runbook review as applicable.
- [ ] **MC-013-Q11** — Archive the exact reviewed artifact revision with each production release.

### Verification and acceptance checklist

- [ ] **MC-013-A01** — All published records validate against versioned schemas and invalid fixtures fail with stable error codes.
- [ ] **MC-013-A02** — Schema compatibility tests prove the stated supported major/minor evolution policy.

### Required closure evidence

- [ ] **MC-013-E01** — Record traceability from `MC-013` and `C022, C026, C029, C082` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-013-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-013-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-013-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-013-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-013` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-014 — Master prompt evidence file

**Priority:** P2  
**Source checks:** `N/A`  
**Primary discipline:** Architecture / Systems Engineering  
**Audit gap:** README previously claimed `MASTER.md`; it is absent from the archive.

### Suggested repository artifacts

- [ ] `MASTER.md` — create or map to an equivalent traceable artifact.
- [ ] `evidence/master_source.json` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-014-I01** — Recover or recreate the authoritative `MASTER.md` from an approved source; record source URI/revision/hash and who approved its inclusion.
- [ ] **MC-014-I02** — Ensure the file describes how the 100-check workflow is instantiated for INV-24 and does not make unverifiable claims about external components.
- [ ] **MC-014-I03** — Link every master requirement to `CHECKLIST.json`/traceability entries and define precedence if `MASTER.md`, contract, README, and checklist disagree.
- [ ] **MC-014-I04** — Add an integrity hash/evidence record and CI check preventing README from claiming the master is included when it is missing or stale.
- [ ] **MC-014-I05** — Mark generated versus hand-maintained sections so future workflow regeneration is deterministic and reviewable.
- [ ] **MC-014-Q06** — Give the artifact a version/owner/review state and define which source is authoritative when documents disagree.
- [ ] **MC-014-Q07** — Use stable identifiers and machine-readable representations for requirements/interfaces wherever downstream automation depends on them.
- [ ] **MC-014-Q08** — Cross-link the artifact to implementation, tests, evidence, and affected C-checks; eliminate unsupported “covered elsewhere” statements.
- [ ] **MC-014-Q09** — Add CI validation for presence, syntax, broken links/references, stale versions, and required approvals.
- [ ] **MC-014-Q10** — Define a change-control rule: architecture/requirement/interface changes must trigger compatibility, threat-model, test, and runbook review as applicable.
- [ ] **MC-014-Q11** — Archive the exact reviewed artifact revision with each production release.

### Verification and acceptance checklist

- [ ] **MC-014-A01** — `MASTER.md` exists, has recorded provenance/integrity, and README claims match the archive contents.
- [ ] **MC-014-A02** — Master/checklist precedence and regeneration process are documented and validated.

### Required closure evidence

- [ ] **MC-014-E01** — Record traceability from `MC-014` and `N/A` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-014-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-014-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-014-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-014-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-014` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Configuration and supply-chain gaps

## MC-015 — Declarative configuration subsystem

**Priority:** P0  
**Source checks:** `C032-C038`  
**Primary discipline:** Build / Release / Supply-Chain Engineering  
**Audit gap:** no config schema/file loader, environment/site overlays, provenance, author/activation metadata, transactional update, rollback, or dynamic activation mechanism.

### Suggested repository artifacts

- [ ] `config/schema.json` — create or map to an equivalent traceable artifact.
- [ ] `config/defaults.yaml` — create or map to an equivalent traceable artifact.
- [ ] `inv24_microvm_runtime/config/` — create or map to an equivalent traceable artifact.
- [ ] `tests/config/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-015-I01** — Define a strict configuration schema with defaults, types, ranges, enums, mutually exclusive fields, and security invariants; unknown keys must be rejected unless explicitly versioned as extensions.
- [ ] **MC-015-I02** — Separate immutable artifact identity (binary/kernel/rootfs digests) from mutable site/environment configuration and runtime state.
- [ ] **MC-015-I03** — Implement deterministic layered resolution (built-in defaults < environment/site file < approved dynamic overlay) with explicit precedence and no hidden ambient environment-variable overrides for security-sensitive settings.
- [ ] **MC-015-I04** — Validate the full candidate configuration before activation; perform cross-field validation for device model, resource limits, KVM capabilities, network/storage references, and boot budget.
- [ ] **MC-015-I05** — Record config revision, content digest, author/source, approval, activation time, previous revision, and reason; support atomic activation and rollback.
- [ ] **MC-015-I06** — Add dry-run/diff, schema migration, rollback-on-health-failure, concurrent-update conflict detection, and startup behavior for corrupt/missing config.
- [ ] **MC-015-Q07** — Make inputs deterministic, pinned/versioned, provenance-recorded, and reproducible from an empty/clean environment.
- [ ] **MC-015-Q08** — Separate mutable configuration/secrets/state from immutable executable artifacts and prevent ambient host state from silently changing behavior.
- [ ] **MC-015-Q09** — Validate before use and fail closed on signature/digest/schema/security errors; provide actionable safe error codes.
- [ ] **MC-015-Q10** — Define rollback/recovery and test corrupt, missing, stale, incompatible, and partially updated inputs.
- [ ] **MC-015-Q11** — Add CI/release checks for dependency/artifact drift, prohibited secrets, missing legal/provenance metadata, and reproducibility.
- [ ] **MC-015-Q12** — Retain manifests/hashes/SBOM/config revision and verification results in the evidence bundle.

### Verification and acceptance checklist

- [ ] **MC-015-A01** — Config changes are validated and atomically activated/rolled back with revision provenance; partial unsafe activation is impossible.
- [ ] **MC-015-A02** — Corrupt/unknown/security-invalid configuration prevents unsafe startup and produces actionable diagnostics.

### Required closure evidence

- [ ] **MC-015-E01** — Record traceability from `MC-015` and `C032-C038` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-015-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-015-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-015-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-015-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-015` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-016 — Secret separation/enforcement

**Priority:** P0  
**Source checks:** `C039`  
**Primary discipline:** Build / Release / Supply-Chain Engineering  
**Audit gap:** no secret-provider boundary, redaction rules/tests, or diagnostic secret scanning.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/secrets/` — create or map to an equivalent traceable artifact.
- [ ] `docs/SECRETS.md` — create or map to an equivalent traceable artifact.
- [ ] `tests/security/test_secret_redaction.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-016-I01** — Create a secret-provider interface so credentials/keys/tokens are referenced by opaque handles and are never stored in ordinary YAML/JSON config or lifecycle records.
- [ ] **MC-016-I02** — Define secret classes, permitted consumers, TTL/rotation behavior, in-memory lifetime, zeroization expectations where practical, and failure behavior when the provider is unavailable.
- [ ] **MC-016-I03** — Implement centralized redaction for logs/errors/traces/diagnostics including nested structures and common token/key formats; redaction must occur before serialization/export.
- [ ] **MC-016-I04** — Add repository/config/evidence secret scanning and runtime canary-secret leakage tests; block release on detected unapproved secret material.
- [ ] **MC-016-I05** — Ensure exceptions, stack traces, subprocess command lines, `/proc`-visible arguments, temp files, and support bundles cannot expose secrets.
- [ ] **MC-016-Q06** — Make inputs deterministic, pinned/versioned, provenance-recorded, and reproducible from an empty/clean environment.
- [ ] **MC-016-Q07** — Separate mutable configuration/secrets/state from immutable executable artifacts and prevent ambient host state from silently changing behavior.
- [ ] **MC-016-Q08** — Validate before use and fail closed on signature/digest/schema/security errors; provide actionable safe error codes.
- [ ] **MC-016-Q09** — Define rollback/recovery and test corrupt, missing, stale, incompatible, and partially updated inputs.
- [ ] **MC-016-Q10** — Add CI/release checks for dependency/artifact drift, prohibited secrets, missing legal/provenance metadata, and reproducibility.
- [ ] **MC-016-Q11** — Retain manifests/hashes/SBOM/config revision and verification results in the evidence bundle.

### Verification and acceptance checklist

- [ ] **MC-016-A01** — Seeded secrets never appear in config dumps, logs, traces, errors, diagnostics, subprocess argv, or evidence bundles.
- [ ] **MC-016-A02** — Secret-provider outage/rotation behavior is tested and follows the documented safe policy.

### Required closure evidence

- [ ] **MC-016-E01** — Record traceability from `MC-016` and `C039` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-016-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-016-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-016-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-016-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-016` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-017 — Reproducible bootstrap/install packaging

**Priority:** P0  
**Source checks:** `C040`  
**Primary discipline:** Build / Release / Supply-Chain Engineering  
**Audit gap:** no `pyproject.toml`/lockfile, install metadata, bootstrap script, pinned dependency manifest, or offline/bootstrap verification.

### Suggested repository artifacts

- [ ] `pyproject.toml` — create or map to an equivalent traceable artifact.
- [ ] `requirements.lock` — create or map to an equivalent traceable artifact.
- [ ] `bootstrap/` — create or map to an equivalent traceable artifact.
- [ ] `tests/bootstrap/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-017-I01** — Add `pyproject.toml` with explicit package metadata, supported Python versions, deterministic entry points, optional dependency groups, and build backend; eliminate ad-hoc import-path assumptions.
- [ ] **MC-017-I02** — Create a lock/constraints file with exact dependency versions and hashes where supported, and document how it is regenerated/reviewed.
- [ ] **MC-017-I03** — Provide bootstrap scripts that verify host prerequisites, install into an isolated environment, validate package/import integrity, and run a health self-test from an empty node.
- [ ] **MC-017-I04** — Create offline/bootstrap mode using a pre-populated artifact wheel/binary cache with digest verification and no unexpected network access.
- [ ] **MC-017-I05** — Test clean install, upgrade, downgrade/rollback, reinstall, path-with-spaces, non-root operation where supported, and failure on missing/incompatible prerequisites.
- [ ] **MC-017-Q06** — Make inputs deterministic, pinned/versioned, provenance-recorded, and reproducible from an empty/clean environment.
- [ ] **MC-017-Q07** — Separate mutable configuration/secrets/state from immutable executable artifacts and prevent ambient host state from silently changing behavior.
- [ ] **MC-017-Q08** — Validate before use and fail closed on signature/digest/schema/security errors; provide actionable safe error codes.
- [ ] **MC-017-Q09** — Define rollback/recovery and test corrupt, missing, stale, incompatible, and partially updated inputs.
- [ ] **MC-017-Q10** — Add CI/release checks for dependency/artifact drift, prohibited secrets, missing legal/provenance metadata, and reproducibility.
- [ ] **MC-017-Q11** — Retain manifests/hashes/SBOM/config revision and verification results in the evidence bundle.

### Verification and acceptance checklist

- [ ] **MC-017-A01** — A clean supported node can install/bootstrap offline or online from pinned artifacts and reach healthy self-test deterministically.
- [ ] **MC-017-A02** — Re-running bootstrap is idempotent and version/hash output uniquely identifies installed bytes.

### Required closure evidence

- [ ] **MC-017-E01** — Record traceability from `MC-017` and `C040` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-017-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-017-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-017-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-017-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-017` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-018 — Artifact integrity/provenance

**Priority:** P0  
**Source checks:** `C031, C045`  
**Primary discipline:** Build / Release / Supply-Chain Engineering  
**Audit gap:** no Firecracker/kernel/rootfs signature/digest verification, SBOM, provenance attestation, approved-artifact policy, or dependency lock.

### Suggested repository artifacts

- [ ] `supply_chain/ARTIFACT_POLICY.md` — create or map to an equivalent traceable artifact.
- [ ] `supply_chain/manifest.json` — create or map to an equivalent traceable artifact.
- [ ] `sbom/inv24.spdx.json` — create or map to an equivalent traceable artifact.
- [ ] `attestations/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-018-I01** — Maintain an approved artifact manifest for Firecracker, jailer, guest kernel, rootfs/base images, Python distributions/dependencies, policy/config bundles, and helper binaries with immutable digests.
- [ ] **MC-018-I02** — Verify digest/signature/provenance before first use and again when materializing from cache; mismatch must fail closed and emit an audit event.
- [ ] **MC-018-I03** — Generate SBOMs for the Python package plus bundled/downloaded native artifacts and record license/CVE provenance sufficient to reproduce the release.
- [ ] **MC-018-I04** — Produce build/provenance attestations tying source commit, build environment, dependency lock, artifact digests, and release identifier; store them immutably with release evidence.
- [ ] **MC-018-I05** — Define approved registries/signers, key rotation/revocation, emergency artifact blocklist, and behavior when provenance/signature services are unavailable.
- [ ] **MC-018-Q06** — Make inputs deterministic, pinned/versioned, provenance-recorded, and reproducible from an empty/clean environment.
- [ ] **MC-018-Q07** — Separate mutable configuration/secrets/state from immutable executable artifacts and prevent ambient host state from silently changing behavior.
- [ ] **MC-018-Q08** — Validate before use and fail closed on signature/digest/schema/security errors; provide actionable safe error codes.
- [ ] **MC-018-Q09** — Define rollback/recovery and test corrupt, missing, stale, incompatible, and partially updated inputs.
- [ ] **MC-018-Q10** — Add CI/release checks for dependency/artifact drift, prohibited secrets, missing legal/provenance metadata, and reproducibility.
- [ ] **MC-018-Q11** — Retain manifests/hashes/SBOM/config revision and verification results in the evidence bundle.

### Verification and acceptance checklist

- [ ] **MC-018-A01** — Release artifacts, dependencies, Firecracker, kernel/rootfs, and policies are all digest/provenance checked before use.
- [ ] **MC-018-A02** — SBOM/attestation/manifest verifier reproduces the approved release identity and rejects substituted bytes.

### Required closure evidence

- [ ] **MC-018-E01** — Record traceability from `MC-018` and `C031, C045` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-018-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-018-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-018-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-018-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-018` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-019 — License/legal metadata

**Priority:** P1  
**Source checks:** `N/A`  
**Primary discipline:** Build / Release / Supply-Chain Engineering  
**Audit gap:** no LICENSE/NOTICE file in the supplied archive.

### Suggested repository artifacts

- [ ] `LICENSE` — create or map to an equivalent traceable artifact.
- [ ] `NOTICE` — create or map to an equivalent traceable artifact.
- [ ] `THIRD_PARTY_NOTICES.md` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-019-I01** — Add the intended project license text only after authorization from the repository owner; ensure package metadata declares the same license expression.
- [ ] **MC-019-I02** — Create NOTICE/third-party notices covering Firecracker and all redistributed libraries/binaries/assets, including attribution obligations and source/license locations.
- [ ] **MC-019-I03** — Add SPDX identifiers/expressions to source or package metadata where appropriate and generate an automated third-party license inventory from the dependency lock/SBOM.
- [ ] **MC-019-I04** — Define a CI policy that rejects dependencies/artifacts with missing, unknown, or disallowed license metadata pending explicit review/waiver.
- [ ] **MC-019-I05** — Reconcile README/legal statements with actual distribution contents so the archive never claims licensing files that are absent.
- [ ] **MC-019-Q06** — Make inputs deterministic, pinned/versioned, provenance-recorded, and reproducible from an empty/clean environment.
- [ ] **MC-019-Q07** — Separate mutable configuration/secrets/state from immutable executable artifacts and prevent ambient host state from silently changing behavior.
- [ ] **MC-019-Q08** — Validate before use and fail closed on signature/digest/schema/security errors; provide actionable safe error codes.
- [ ] **MC-019-Q09** — Define rollback/recovery and test corrupt, missing, stale, incompatible, and partially updated inputs.
- [ ] **MC-019-Q10** — Add CI/release checks for dependency/artifact drift, prohibited secrets, missing legal/provenance metadata, and reproducibility.
- [ ] **MC-019-Q11** — Retain manifests/hashes/SBOM/config revision and verification results in the evidence bundle.

### Verification and acceptance checklist

- [ ] **MC-019-A01** — Distributed archive contains authorized LICENSE/NOTICE/third-party metadata consistent with package/SBOM contents.
- [ ] **MC-019-A02** — CI detects missing/unknown/disallowed dependency license metadata.

### Required closure evidence

- [ ] **MC-019-E01** — Record traceability from `MC-019` and `N/A` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-019-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-019-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-019-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-019-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-019` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Security and isolation gaps

## MC-020 — Threat model

**Priority:** P0  
**Source checks:** `C041, C050, C087`  
**Primary discipline:** Security Engineering + Runtime Engineering  
**Audit gap:** no threat-model document with assets, trust boundaries, attack trees/scenarios, mitigations, residual risk, and test linkage.

### Suggested repository artifacts

- [ ] `security/THREAT_MODEL.md` — create or map to an equivalent traceable artifact.
- [ ] `security/threats.yaml` — create or map to an equivalent traceable artifact.
- [ ] `security/mitigation-matrix.yaml` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-020-I01** — Document assets, actors, entry points, trust zones, privileged components, data classes, control-plane dependencies, and attacker capabilities for malicious tenant, compromised guest, hostile host input, supply-chain, and insider/control-plane abuse cases.
- [ ] **MC-020-I02** — Model attacks for device emulation, Firecracker API socket, jailer/filesystem, KVM/kernel, TAP/network, block/rootfs, vsock, snapshots, metadata, artifact substitution, denial of service, side channels, and stale control-plane decisions.
- [ ] **MC-020-I03** — For each threat assign preconditions, impact, likelihood/severity methodology, preventive/detective controls, residual risk, owner, and verification test IDs.
- [ ] **MC-020-I04** — Define security invariants such as “no out-of-model device,” “no cross-tenant memory/state reuse,” “unverified artifact never executes,” and “loss of identity/policy/key service fails according to documented safe mode.”
- [ ] **MC-020-I05** — Review the threat model when Firecracker/kernel/device surface, privilege model, or control-plane boundaries change; link changes to adversarial tests and production gate evidence.
- [ ] **MC-020-Q06** — State the security invariant and trust boundary that this component enforces; do not treat logging or documentation as the control itself.
- [ ] **MC-020-Q07** — Apply least privilege, explicit authorization, bounded inputs/resources, and fail-closed behavior for missing trust prerequisites.
- [ ] **MC-020-Q08** — Emit security-relevant audit events with correlation to actor, tenant/workload, operation, policy/config/artifact version, and result.
- [ ] **MC-020-Q09** — Create negative/adversarial tests and map them to threat IDs; include replay, malformed input, privilege boundary, and resource-exhaustion cases where relevant.
- [ ] **MC-020-Q10** — Define secure failure/recovery behavior so retries, restarts, diagnostics, or degraded mode cannot weaken isolation.
- [ ] **MC-020-Q11** — Retain threat/control/test/evidence links and require security-owner review before production acceptance.

### Verification and acceptance checklist

- [ ] **MC-020-A01** — Every high-priority threat has an implemented control, owner, residual-risk disposition, and executable verification test.
- [ ] **MC-020-A02** — Threat-model review is required when privilege/device/Firecracker/kernel/control-plane boundaries change.

### Required closure evidence

- [ ] **MC-020-E01** — Record traceability from `MC-020` and `C041, C050, C087` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-020-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-020-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-020-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-020-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-020` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-021 — Identity/authentication layer

**Priority:** P0  
**Source checks:** `C023, C044, C048`  
**Primary discipline:** Security Engineering + Runtime Engineering  
**Audit gap:** no node/peer/control-plane identity mechanism, certificate/attestation verification, or unavailable-identity fail-closed behavior.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/identity/` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_IDENTITY_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/security/test_identity.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-021-I01** — Define cryptographic identities for node/host, runtime agent, control-plane caller, peer services, and optionally workload/guest; specify root of trust and enrollment/rotation/revocation.
- [ ] **MC-021-I02** — Authenticate every remote/service boundary before processing privileged requests; bind authenticated identity to tenant/site/environment and authorization context.
- [ ] **MC-021-I03** — Where attestation is required, validate attestation freshness, nonce/challenge, expected measurements/policy, verifier identity, and replay prevention before admission.
- [ ] **MC-021-I04** — Fail closed for create/restore/privileged lifecycle operations when required identity or attestation cannot be validated; separately define any safe read-only/degraded status behavior.
- [ ] **MC-021-I05** — Test expired/revoked certs, wrong SAN/identity, unknown CA, stale attestation, clock skew, replayed token, verifier outage, and rotation without service interruption.
- [ ] **MC-021-Q06** — State the security invariant and trust boundary that this component enforces; do not treat logging or documentation as the control itself.
- [ ] **MC-021-Q07** — Apply least privilege, explicit authorization, bounded inputs/resources, and fail-closed behavior for missing trust prerequisites.
- [ ] **MC-021-Q08** — Emit security-relevant audit events with correlation to actor, tenant/workload, operation, policy/config/artifact version, and result.
- [ ] **MC-021-Q09** — Create negative/adversarial tests and map them to threat IDs; include replay, malformed input, privilege boundary, and resource-exhaustion cases where relevant.
- [ ] **MC-021-Q10** — Define secure failure/recovery behavior so retries, restarts, diagnostics, or degraded mode cannot weaken isolation.
- [ ] **MC-021-Q11** — Retain threat/control/test/evidence links and require security-owner review before production acceptance.

### Verification and acceptance checklist

- [ ] **MC-021-A01** — Unauthenticated, expired, revoked, replayed, or wrongly scoped identities cannot perform privileged operations.
- [ ] **MC-021-A02** — Identity/attestation service outage follows documented fail-closed/degraded rules without silent bypass.

### Required closure evidence

- [ ] **MC-021-E01** — Record traceability from `MC-021` and `C023, C044, C048` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-021-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-021-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-021-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-021-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-021` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-022 — Authorization/capability layer

**Priority:** P0  
**Source checks:** `C024, C042-C043`  
**Primary discipline:** Security Engineering + Runtime Engineering  
**Audit gap:** no capability model, host filesystem/network/device/kernel authority reduction, seccomp/jailer/cgroup/namespace policy, or least-privilege execution wrapper.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/authz/` — create or map to an equivalent traceable artifact.
- [ ] `security/seccomp/` — create or map to an equivalent traceable artifact.
- [ ] `security/jailer/` — create or map to an equivalent traceable artifact.
- [ ] `tests/security/test_authorization.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-022-I01** — Define explicit capabilities for create, boot, pause/resume, stop/destroy, snapshot/restore, inspect diagnostics, alter config, quarantine, and emergency operations; deny by default.
- [ ] **MC-022-I02** — Run the VMM under the minimum practical UID/GID and jailer/chroot/namespace/cgroup boundary; restrict filesystem mounts, Linux capabilities, device nodes, syscalls/seccomp, network namespaces, and inherited file descriptors.
- [ ] **MC-022-I03** — Authorize access to `/dev/kvm`, TAP, block artifacts, vsock endpoints, config, keys, and API sockets by narrow service roles rather than ambient root authority.
- [ ] **MC-022-I04** — Bind authorization decisions to authenticated identity, tenant/workload, site/environment, resource, action, policy version, and expiry; log reason and policy revision.
- [ ] **MC-022-I05** — Add negative tests proving unauthorized actors cannot cross tenant boundaries, inject devices/paths, modify policy/config, access diagnostics, or bypass the jailer through symlinks/file descriptors.
- [ ] **MC-022-Q06** — State the security invariant and trust boundary that this component enforces; do not treat logging or documentation as the control itself.
- [ ] **MC-022-Q07** — Apply least privilege, explicit authorization, bounded inputs/resources, and fail-closed behavior for missing trust prerequisites.
- [ ] **MC-022-Q08** — Emit security-relevant audit events with correlation to actor, tenant/workload, operation, policy/config/artifact version, and result.
- [ ] **MC-022-Q09** — Create negative/adversarial tests and map them to threat IDs; include replay, malformed input, privilege boundary, and resource-exhaustion cases where relevant.
- [ ] **MC-022-Q10** — Define secure failure/recovery behavior so retries, restarts, diagnostics, or degraded mode cannot weaken isolation.
- [ ] **MC-022-Q11** — Retain threat/control/test/evidence links and require security-owner review before production acceptance.

### Verification and acceptance checklist

- [ ] **MC-022-A01** — The runtime/VMM executes with a documented minimal privilege set and denied capabilities/syscalls/paths are verified by tests.
- [ ] **MC-022-A02** — Every privileged operation requires an explicit capability bound to actor/resource/action/tenant.

### Required closure evidence

- [ ] **MC-022-E01** — Record traceability from `MC-022` and `C024, C042-C043` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-022-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-022-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-022-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-022-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-022` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-023 — Tenant isolation enforcement below the model

**Priority:** P0  
**Source checks:** `C046`  
**Primary discipline:** Security Engineering + Runtime Engineering  
**Audit gap:** immutable tenant labels help the domain object, but there is no actual VM memory, process, network, storage, cgroup, jailer, or device isolation implementation/evidence.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/isolation/` — create or map to an equivalent traceable artifact.
- [ ] `security/ISOLATION_MODEL.md` — create or map to an equivalent traceable artifact.
- [ ] `tests/security/test_tenant_isolation.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-023-I01** — Enforce one-tenant-per-microVM below the Python model using process/jailer separation, cgroups, namespaces, VM memory ownership, unique storage/network namespaces, and device/backend ownership.
- [ ] **MC-023-I02** — Define memory scrubbing/destruction semantics for normal stop, failed boot, VMM crash, host-agent crash, snapshot restore, and resource pool reuse; do not rely solely on an in-memory `destroyed` flag.
- [ ] **MC-023-I03** — Prevent cross-tenant disk/rootfs writes through copy-on-write or per-tenant volumes and verify block device teardown before reuse; prevent TAP/vsock namespace/CID reuse until cleanup is confirmed.
- [ ] **MC-023-I04** — Constrain CPU/memory/I/O resource consumption per tenant to prevent noisy-neighbor and exhaustion attacks, and ensure host-level limits cannot be raised by guest-controlled input.
- [ ] **MC-023-I05** — Create isolation tests attempting cross-VM memory/state/network/storage/vsock access, stale resource reuse, symlink/path traversal, and post-crash residual access.
- [ ] **MC-023-Q06** — State the security invariant and trust boundary that this component enforces; do not treat logging or documentation as the control itself.
- [ ] **MC-023-Q07** — Apply least privilege, explicit authorization, bounded inputs/resources, and fail-closed behavior for missing trust prerequisites.
- [ ] **MC-023-Q08** — Emit security-relevant audit events with correlation to actor, tenant/workload, operation, policy/config/artifact version, and result.
- [ ] **MC-023-Q09** — Create negative/adversarial tests and map them to threat IDs; include replay, malformed input, privilege boundary, and resource-exhaustion cases where relevant.
- [ ] **MC-023-Q10** — Define secure failure/recovery behavior so retries, restarts, diagnostics, or degraded mode cannot weaken isolation.
- [ ] **MC-023-Q11** — Retain threat/control/test/evidence links and require security-owner review before production acceptance.

### Verification and acceptance checklist

- [ ] **MC-023-A01** — Cross-tenant state/memory/storage/network/device reuse tests show no residual access after stop/crash/restart.
- [ ] **MC-023-A02** — Host isolation primitives are measured/inspected in evidence, not inferred from Python object immutability.

### Required closure evidence

- [ ] **MC-023-E01** — Record traceability from `MC-023` and `C046` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-023-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-023-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-023-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-023-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-023` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-024 — Encryption/key management

**Priority:** P0  
**Source checks:** `C047-C048`  
**Primary discipline:** Security Engineering + Runtime Engineering  
**Audit gap:** no transport encryption, at-rest encryption, key rotation, KMS integration, or failure policy.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/crypto/` — create or map to an equivalent traceable artifact.
- [ ] `docs/KEY_MANAGEMENT.md` — create or map to an equivalent traceable artifact.
- [ ] `tests/security/test_crypto_fail_closed.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-024-I01** — Define data-classification rules and determine which control-plane traffic, config/state, snapshot, rootfs/workload data, logs, and audit records require encryption in transit and/or at rest.
- [ ] **MC-024-I02** — Use managed keys with explicit key IDs/versions, least-privilege access, rotation schedule, revocation, audit logging, and separation between tenant data keys and service/control-plane keys where applicable.
- [ ] **MC-024-I03** — Authenticate encrypted channels, verify peer identity, enforce modern protocol/cipher policy, and prohibit silent plaintext fallback.
- [ ] **MC-024-I04** — Encrypt persisted sensitive state/snapshots/support bundles with integrity protection and bind ciphertext metadata to tenant/workload identity to prevent swap/replay.
- [ ] **MC-024-I05** — Define fail-closed/degraded behavior for KMS/key unavailability, expired keys, clock uncertainty, rotation mid-operation, and revoked credentials; test each path.
- [ ] **MC-024-Q06** — State the security invariant and trust boundary that this component enforces; do not treat logging or documentation as the control itself.
- [ ] **MC-024-Q07** — Apply least privilege, explicit authorization, bounded inputs/resources, and fail-closed behavior for missing trust prerequisites.
- [ ] **MC-024-Q08** — Emit security-relevant audit events with correlation to actor, tenant/workload, operation, policy/config/artifact version, and result.
- [ ] **MC-024-Q09** — Create negative/adversarial tests and map them to threat IDs; include replay, malformed input, privilege boundary, and resource-exhaustion cases where relevant.
- [ ] **MC-024-Q10** — Define secure failure/recovery behavior so retries, restarts, diagnostics, or degraded mode cannot weaken isolation.
- [ ] **MC-024-Q11** — Retain threat/control/test/evidence links and require security-owner review before production acceptance.

### Verification and acceptance checklist

- [ ] **MC-024-A01** — Sensitive transports/storage use approved encryption/key versions and plaintext downgrade is impossible.
- [ ] **MC-024-A02** — Key loss/revocation/rotation/outage tests produce the defined safe outcome and auditable reason.

### Required closure evidence

- [ ] **MC-024-E01** — Record traceability from `MC-024` and `C047-C048` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-024-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-024-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-024-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-024-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-024` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-025 — Tamper-evident security audit log

**Priority:** P0  
**Source checks:** `C049`  
**Primary discipline:** Security Engineering + Runtime Engineering  
**Audit gap:** no append-only/hash-chained audit event implementation.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/audit/` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_AUDIT_EVENT_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/security/test_audit_chain.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-025-I01** — Define a versioned security audit event schema with event ID, sequence/chain metadata, UTC timestamp, actor identity, tenant/workload, node, operation ID, action, target, policy/config version, result, reason code, and safe metadata.
- [ ] **MC-025-I02** — Implement append-only persistence or remote write with cryptographic hash chaining/signatures so deletion, insertion, reordering, or mutation is detectable.
- [ ] **MC-025-I03** — Cover security-sensitive events: admission, authn/authz denial, artifact verification, config activation/rollback, lifecycle changes, snapshot/restore, quarantine, secret/key failures, privilege changes, and evidence-gate decisions.
- [ ] **MC-025-I04** — Ensure audit logging is non-bypassable by ordinary workload code, bounded under overload, redacted, and has explicit behavior if the sink becomes unavailable.
- [ ] **MC-025-I05** — Build verification tooling/tests that detect tampered/missing events, chain discontinuity, clock anomalies, replay, and tenant leakage; retain verifier output as release/incident evidence.
- [ ] **MC-025-Q06** — State the security invariant and trust boundary that this component enforces; do not treat logging or documentation as the control itself.
- [ ] **MC-025-Q07** — Apply least privilege, explicit authorization, bounded inputs/resources, and fail-closed behavior for missing trust prerequisites.
- [ ] **MC-025-Q08** — Emit security-relevant audit events with correlation to actor, tenant/workload, operation, policy/config/artifact version, and result.
- [ ] **MC-025-Q09** — Create negative/adversarial tests and map them to threat IDs; include replay, malformed input, privilege boundary, and resource-exhaustion cases where relevant.
- [ ] **MC-025-Q10** — Define secure failure/recovery behavior so retries, restarts, diagnostics, or degraded mode cannot weaken isolation.
- [ ] **MC-025-Q11** — Retain threat/control/test/evidence links and require security-owner review before production acceptance.

### Verification and acceptance checklist

- [ ] **MC-025-A01** — Audit-chain verifier detects mutation, deletion, reordering, and replay in generated event sequences.
- [ ] **MC-025-A02** — Security-sensitive actions emit audit records even on denied/failed paths.

### Required closure evidence

- [ ] **MC-025-E01** — Record traceability from `MC-025` and `C049` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-025-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-025-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-025-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-025-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-025` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-026 — Adversarial security suite

**Priority:** P0  
**Source checks:** `C050, C087`  
**Primary discipline:** Security Engineering + Runtime Engineering  
**Audit gap:** no tests for escape, privilege escalation, injection, replay, spoofing, side channels, malicious device descriptors, or resource exhaustion.

### Suggested repository artifacts

- [ ] `tests/security/adversarial/` — create or map to an equivalent traceable artifact.
- [ ] `security/attack-cases.yaml` — create or map to an equivalent traceable artifact.
- [ ] `evidence/security/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-026-I01** — Derive adversarial cases directly from the threat model and assign a test ID to every mitigated threat so security coverage can be measured mechanically.
- [ ] **MC-026-I02** — Test VMM/guest escape assumptions, jailer/seccomp bypass attempts, malicious Firecracker API/config fields, path/symlink injection, hostile block images, malformed virtio descriptors, vsock/TAP spoofing, and control-plane payload injection.
- [ ] **MC-026-I03** — Test replay/spoofing for identity/capability/admission operations and artifact/snapshot substitution; verify stale epochs/tokens/config revisions are rejected.
- [ ] **MC-026-I04** — Exercise resource exhaustion: VM creation flood, boot timeout flood, queue/memory/file-descriptor exhaustion, log/metric cardinality attacks, disk-full, and oversized diagnostics/config payloads.
- [ ] **MC-026-I05** — Include side-channel-oriented isolation tests/measurements appropriate to supported hardware and document residual risks that cannot be fully eliminated in software.
- [ ] **MC-026-I06** — Run the suite on hardened builds in CI/periodic dedicated environments, archive tool versions/seeds/results, and block release on exploitable regressions.
- [ ] **MC-026-Q07** — State the security invariant and trust boundary that this component enforces; do not treat logging or documentation as the control itself.
- [ ] **MC-026-Q08** — Apply least privilege, explicit authorization, bounded inputs/resources, and fail-closed behavior for missing trust prerequisites.
- [ ] **MC-026-Q09** — Emit security-relevant audit events with correlation to actor, tenant/workload, operation, policy/config/artifact version, and result.
- [ ] **MC-026-Q10** — Create negative/adversarial tests and map them to threat IDs; include replay, malformed input, privilege boundary, and resource-exhaustion cases where relevant.
- [ ] **MC-026-Q11** — Define secure failure/recovery behavior so retries, restarts, diagnostics, or degraded mode cannot weaken isolation.
- [ ] **MC-026-Q12** — Retain threat/control/test/evidence links and require security-owner review before production acceptance.

### Verification and acceptance checklist

- [ ] **MC-026-A01** — Threat-linked adversarial suite has no exploitable P0/P1 failures for the release candidate.
- [ ] **MC-026-A02** — New security defects add permanent regression cases and archived seeds/artifacts.

### Required closure evidence

- [ ] **MC-026-E01** — Record traceability from `MC-026` and `C050, C087` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-026-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-026-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-026-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-026-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-026` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Resilience and failure-handling gaps

## MC-027 — Health/stall detector

**Priority:** P0  
**Source checks:** `C051-C052, C071`  
**Primary discipline:** Reliability / Runtime Engineering  
**Audit gap:** `status()` exposes local state but no active liveness/readiness probes, VMM heartbeat, guest stall detector, dependency health, or thresholds.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/health/` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_HEALTH_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/resilience/test_health_stall.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-027-I01** — Define separate liveness, readiness, startup, dependency, and per-instance/guest health signals rather than overloading `status()` as proof of health.
- [ ] **MC-027-I02** — Actively monitor Firecracker process/PID, API-socket responsiveness, KVM/device backend availability, guest heartbeat or boot progress, critical control-plane dependencies, disk/resource saturation, and telemetry pipeline health.
- [ ] **MC-027-I03** — Specify thresholds, consecutive-failure counts, grace periods, hysteresis, and state transitions to avoid flapping while still detecting hangs within the recovery objective.
- [ ] **MC-027-I04** — Classify health failures into local recoverable, guest/workload failure, dependency degradation, host unsafe, and terminal/quarantine-required conditions.
- [ ] **MC-027-I05** — Test stuck VMM, unresponsive API socket, guest boot stall, dead backend, saturated host, missing KVM, clock jump, and dependency outage; verify alert/recovery actions and false-positive rate.
- [ ] **MC-027-Q06** — Define the authoritative state, failure detector, timeout, retryability, and terminal/degraded states before implementing automatic recovery.
- [ ] **MC-027-Q07** — Bound queues/retries/resources and preserve idempotency/fencing so recovery cannot create duplicate execution or stale ownership.
- [ ] **MC-027-Q08** — Make cleanup/reconciliation explicit for process, socket, device, reservation, and persistent state after every failure boundary.
- [ ] **MC-027-Q09** — Expose detection/recovery/quarantine metrics and stable reason codes suitable for SLOs and incident response.
- [ ] **MC-027-Q10** — Test failures at multiple timing points, including failures during recovery itself, and assert isolation/resource invariants.
- [ ] **MC-027-Q11** — Record recovery objective versus observed detection/recovery time and any residual operator action in evidence.

### Verification and acceptance checklist

- [ ] **MC-027-A01** — Configured stalls/dependency failures are detected within thresholds with bounded false positives and correct recovery/quarantine.
- [ ] **MC-027-A02** — Health output exposes version/config/dependency/capability state required for operator diagnosis.

### Required closure evidence

- [ ] **MC-027-E01** — Record traceability from `MC-027` and `C051-C052, C071` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-027-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-027-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-027-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-027-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-027` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-028 — Retry/backoff/cancellation/idempotency layer

**Priority:** P1  
**Source checks:** `C025, C053`  
**Primary discipline:** Reliability / Runtime Engineering  
**Audit gap:** no operation IDs, cancellation, bounded retry, backoff/jitter, or idempotency keys.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/operations/retry.py` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_OPERATION_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/resilience/test_retry_idempotency.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-028-I01** — Assign globally unique operation IDs plus caller-supplied idempotency keys to create/boot/lifecycle/snapshot operations and persist the completed result long enough to deduplicate retries.
- [ ] **MC-028-I02** — Define per-operation deadlines and cancellation semantics, including whether cancellation guarantees no side effect, attempts best-effort teardown, or returns “outcome unknown.”
- [ ] **MC-028-I03** — Classify errors as retryable/non-retryable and permit retry only for operations proven idempotent or protected by fencing/idempotency state.
- [ ] **MC-028-I04** — Implement bounded exponential backoff with jitter, maximum attempts/elapsed time, retry budget, and propagation of upstream deadlines; never retry tight loops on security/policy rejection.
- [ ] **MC-028-I05** — Test duplicate request storms, cancellation racing process start, controller restart between side effect/result persistence, timeout after successful VMM creation, and stale retry after ownership transfer.
- [ ] **MC-028-Q06** — Define the authoritative state, failure detector, timeout, retryability, and terminal/degraded states before implementing automatic recovery.
- [ ] **MC-028-Q07** — Bound queues/retries/resources and preserve idempotency/fencing so recovery cannot create duplicate execution or stale ownership.
- [ ] **MC-028-Q08** — Make cleanup/reconciliation explicit for process, socket, device, reservation, and persistent state after every failure boundary.
- [ ] **MC-028-Q09** — Expose detection/recovery/quarantine metrics and stable reason codes suitable for SLOs and incident response.
- [ ] **MC-028-Q10** — Test failures at multiple timing points, including failures during recovery itself, and assert isolation/resource invariants.
- [ ] **MC-028-Q11** — Record recovery objective versus observed detection/recovery time and any residual operator action in evidence.

### Verification and acceptance checklist

- [ ] **MC-028-A01** — Duplicate/retried/cancelled operations never create duplicate VM side effects and outcome-unknown states are explicitly surfaced/reconciled.
- [ ] **MC-028-A02** — Backoff/retry budgets are bounded and non-retryable policy/security errors are never retried.

### Required closure evidence

- [ ] **MC-028-E01** — Record traceability from `MC-028` and `C025, C053` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-028-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-028-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-028-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-028-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-028` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-029 — Admission/load shedding/circuit breaking

**Priority:** P0  
**Source checks:** `C054`  
**Primary discipline:** Reliability / Runtime Engineering  
**Audit gap:** no concurrency admission, queue cap, overload shedding, or dependency breaker.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/admission/limits.py` — create or map to an equivalent traceable artifact.
- [ ] `inv24_microvm_runtime/resilience/circuit_breaker.py` — create or map to an equivalent traceable artifact.
- [ ] `tests/resilience/test_overload.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-029-I01** — Define admission ceilings for concurrent create/boot operations, total/running VMs, queued requests, per-tenant shares, memory/vCPU commitments, open file descriptors, TAP/vsock resources, and backend connections.
- [ ] **MC-029-I02** — Implement deterministic queue bounds and per-tenant fairness; reject before expensive allocation when the system is saturated and return retry-after/capacity reason where safe.
- [ ] **MC-029-I03** — Add circuit breakers around failing dependencies (artifact, identity/policy, KVM/backend/control-plane) with closed/open/half-open behavior, error thresholds, recovery probes, and no bypass of security prerequisites.
- [ ] **MC-029-I04** — Prefer load shedding to unbounded latency/memory growth; distinguish overload rejection from policy/auth/security failure in errors and metrics.
- [ ] **MC-029-I05** — Stress test burst/overload/tenant-hog scenarios and prove queue/memory/FD counts remain within configured bounds and healthy tenants retain their documented fairness share.
- [ ] **MC-029-Q06** — Define the authoritative state, failure detector, timeout, retryability, and terminal/degraded states before implementing automatic recovery.
- [ ] **MC-029-Q07** — Bound queues/retries/resources and preserve idempotency/fencing so recovery cannot create duplicate execution or stale ownership.
- [ ] **MC-029-Q08** — Make cleanup/reconciliation explicit for process, socket, device, reservation, and persistent state after every failure boundary.
- [ ] **MC-029-Q09** — Expose detection/recovery/quarantine metrics and stable reason codes suitable for SLOs and incident response.
- [ ] **MC-029-Q10** — Test failures at multiple timing points, including failures during recovery itself, and assert isolation/resource invariants.
- [ ] **MC-029-Q11** — Record recovery objective versus observed detection/recovery time and any residual operator action in evidence.

### Verification and acceptance checklist

- [ ] **MC-029-A01** — Overload testing remains within queue/memory/FD/concurrency ceilings and preserves documented fairness.
- [ ] **MC-029-A02** — Dependency failure opens breakers/load shedding without weakening security prerequisites.

### Required closure evidence

- [ ] **MC-029-E01** — Record traceability from `MC-029` and `C054` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-029-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-029-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-029-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-029-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-029` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-030 — Failover/degraded-mode implementation

**Priority:** P1  
**Source checks:** `C055-C056, C089`  
**Primary discipline:** Reliability / Runtime Engineering  
**Audit gap:** no scheduler/failover policy, degraded control-plane behavior, offline semantics, partition/reconnect implementation, or tests.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/resilience/degraded.py` — create or map to an equivalent traceable artifact.
- [ ] `docs/DEGRADED_MODE.md` — create or map to an equivalent traceable artifact.
- [ ] `tests/resilience/test_partition_modes.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-030-I01** — Define which state is node-local versus durable/authoritative and what can fail over without violating tenant isolation, residency, snapshot compatibility, or single-owner semantics.
- [ ] **MC-030-I02** — Document behavior when PLN-04/control-plane, artifact store, identity/policy, KMS, telemetry, or optional INV-35 becomes unavailable; classify dependencies as critical or degradable.
- [ ] **MC-030-I03** — Implement explicit degraded modes with capability reduction, expiry/freshness limits for cached policy/artifacts, and operator-visible health; never silently weaken authentication/authorization/isolation.
- [ ] **MC-030-I04** — Define reconnect reconciliation: authoritative owner wins, stale operations are fenced, duplicate instances are detected, and queued requests are either resumed safely or failed deterministically.
- [ ] **MC-030-I05** — Test network partitions of varying duration, asymmetric reachability, dependency brownouts, stale caches, recovery ordering, and site failover with residency constraints.
- [ ] **MC-030-Q06** — Define the authoritative state, failure detector, timeout, retryability, and terminal/degraded states before implementing automatic recovery.
- [ ] **MC-030-Q07** — Bound queues/retries/resources and preserve idempotency/fencing so recovery cannot create duplicate execution or stale ownership.
- [ ] **MC-030-Q08** — Make cleanup/reconciliation explicit for process, socket, device, reservation, and persistent state after every failure boundary.
- [ ] **MC-030-Q09** — Expose detection/recovery/quarantine metrics and stable reason codes suitable for SLOs and incident response.
- [ ] **MC-030-Q10** — Test failures at multiple timing points, including failures during recovery itself, and assert isolation/resource invariants.
- [ ] **MC-030-Q11** — Record recovery objective versus observed detection/recovery time and any residual operator action in evidence.

### Verification and acceptance checklist

- [ ] **MC-030-A01** — Partition/dependency-outage tests enter only documented degraded states and reconcile without duplicate ownership/execution.
- [ ] **MC-030-A02** — Cached trust/config/artifact inputs expire according to freshness policy.

### Required closure evidence

- [ ] **MC-030-E01** — Record traceability from `MC-030` and `C055-C056, C089` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-030-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-030-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-030-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-030-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-030` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-031 — Crash/restart/duplicate ownership protections

**Priority:** P0  
**Source checks:** `C057-C058`  
**Primary discipline:** Reliability / Runtime Engineering  
**Audit gap:** no persistent ownership lease, fencing, generation/epoch, replay journal, duplicate execution prevention, or restart reconciliation.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/ownership/` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_OWNERSHIP_LEASE_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/resilience/test_restart_fencing.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-031-I01** — Persist a lease/ownership record containing instance ID, owner node/controller, generation/epoch/fencing token, tenant/workload, state, and expiry/heartbeat metadata.
- [ ] **MC-031-I02** — Require the current fencing token for destructive or mutating actions so stale controllers cannot resume/stop/snapshot an instance after ownership moves.
- [ ] **MC-031-I03** — Design a write-ahead/replay journal or equivalent for create/boot/stop side effects with explicit commit points and idempotent reconciliation after agent/VMM/host restart.
- [ ] **MC-031-I04** — On restart, inventory actual VMM processes, API sockets, network/block resources, and durable ownership records; classify each as adopted, cleaned, quarantined, or orphaned.
- [ ] **MC-031-I05** — Test crashes at every lifecycle commit boundary, duplicate controllers, lease expiry, delayed/stale messages, PID reuse, and orphaned resources; assert at most one authoritative running instance per workload identity.
- [ ] **MC-031-Q06** — Define the authoritative state, failure detector, timeout, retryability, and terminal/degraded states before implementing automatic recovery.
- [ ] **MC-031-Q07** — Bound queues/retries/resources and preserve idempotency/fencing so recovery cannot create duplicate execution or stale ownership.
- [ ] **MC-031-Q08** — Make cleanup/reconciliation explicit for process, socket, device, reservation, and persistent state after every failure boundary.
- [ ] **MC-031-Q09** — Expose detection/recovery/quarantine metrics and stable reason codes suitable for SLOs and incident response.
- [ ] **MC-031-Q10** — Test failures at multiple timing points, including failures during recovery itself, and assert isolation/resource invariants.
- [ ] **MC-031-Q11** — Record recovery objective versus observed detection/recovery time and any residual operator action in evidence.

### Verification and acceptance checklist

- [ ] **MC-031-A01** — Crash-at-every-boundary tests converge to exactly one authoritative instance state and no stale controller can mutate it.
- [ ] **MC-031-A02** — Reconciliation finds and resolves orphaned processes/resources with auditable decisions.

### Required closure evidence

- [ ] **MC-031-E01** — Record traceability from `MC-031` and `C057-C058` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-031-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-031-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-031-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-031-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-031` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-032 — Quarantine/freeze/emergency isolation control

**Priority:** P0  
**Source checks:** `C059`  
**Primary discipline:** Reliability / Runtime Engineering  
**Audit gap:** stop/destroy exists per object, but no fleet/operator quarantine, freeze, deny-admission, or node isolation control.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/quarantine/` — create or map to an equivalent traceable artifact.
- [ ] `docs/EMERGENCY_ISOLATION.md` — create or map to an equivalent traceable artifact.
- [ ] `tests/resilience/test_quarantine.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-032-I01** — Provide fleet-, node-, tenant-, workload-, and instance-scoped quarantine/deny-admission controls with explicit reason, actor, start/expiry, and audit trail.
- [ ] **MC-032-I02** — Define freeze semantics separately from stop/destroy: what guest execution, network, storage writes, API mutations, and diagnostics are allowed while frozen/quarantined.
- [ ] **MC-032-I03** — Implement an emergency kill/disable path that remains available when the normal control plane is degraded while still requiring strong operator authorization and producing tamper-evident audit evidence.
- [ ] **MC-032-I04** — Make quarantine sticky across service restart and reconciliation; prevent automated retry/failover from resurrecting a quarantined workload until a deliberate release action succeeds.
- [ ] **MC-032-I05** — Test emergency isolation during boot, running, paused, snapshot, dependency failure, and controller restart; verify bounded completion time and no cross-tenant collateral impact.
- [ ] **MC-032-Q06** — Define the authoritative state, failure detector, timeout, retryability, and terminal/degraded states before implementing automatic recovery.
- [ ] **MC-032-Q07** — Bound queues/retries/resources and preserve idempotency/fencing so recovery cannot create duplicate execution or stale ownership.
- [ ] **MC-032-Q08** — Make cleanup/reconciliation explicit for process, socket, device, reservation, and persistent state after every failure boundary.
- [ ] **MC-032-Q09** — Expose detection/recovery/quarantine metrics and stable reason codes suitable for SLOs and incident response.
- [ ] **MC-032-Q10** — Test failures at multiple timing points, including failures during recovery itself, and assert isolation/resource invariants.
- [ ] **MC-032-Q11** — Record recovery objective versus observed detection/recovery time and any residual operator action in evidence.

### Verification and acceptance checklist

- [ ] **MC-032-A01** — Authorized emergency quarantine completes within the documented objective and survives restart/reconciliation.
- [ ] **MC-032-A02** — Quarantined workloads cannot be automatically re-admitted or failed over until explicitly released.

### Required closure evidence

- [ ] **MC-032-E01** — Record traceability from `MC-032` and `C059` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-032-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-032-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-032-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-032-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-032` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-033 — Fault-injection suite

**Priority:** P1  
**Source checks:** `C060, C089`  
**Primary discipline:** Reliability / Runtime Engineering  
**Audit gap:** no process kill, VMM crash, node loss, network partition, disk/full, dependency outage, or recovery-objective tests.

### Suggested repository artifacts

- [ ] `tests/fault_injection/` — create or map to an equivalent traceable artifact.
- [ ] `faults/scenarios.yaml` — create or map to an equivalent traceable artifact.
- [ ] `evidence/fault-injection/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-033-I01** — Build a controlled fault-injection harness capable of killing the VMM/runtime process, denying `/dev/kvm`, failing API sockets, dropping network, stalling/delaying dependencies, filling disks, exhausting FDs/memory, corrupting snapshots, and rebooting the host test node.
- [ ] **MC-033-I02** — Define expected recovery objective and invariant for every scenario: data/state outcome, ownership, cleanup, retry behavior, alert, and operator action.
- [ ] **MC-033-I03** — Inject faults at deterministic lifecycle boundaries (pre-side-effect, post-side-effect/pre-commit, post-commit, teardown) to validate crash consistency and idempotency.
- [ ] **MC-033-I04** — Measure time-to-detect and time-to-recover/quarantine plus orphaned resource counts; fail tests on silent recovery that violates isolation or duplicates execution.
- [ ] **MC-033-I05** — Archive scenario definition, seed/timing, environment, logs/traces/metrics, and result in machine-readable evidence so regressions can be compared across releases.
- [ ] **MC-033-Q06** — Define the authoritative state, failure detector, timeout, retryability, and terminal/degraded states before implementing automatic recovery.
- [ ] **MC-033-Q07** — Bound queues/retries/resources and preserve idempotency/fencing so recovery cannot create duplicate execution or stale ownership.
- [ ] **MC-033-Q08** — Make cleanup/reconciliation explicit for process, socket, device, reservation, and persistent state after every failure boundary.
- [ ] **MC-033-Q09** — Expose detection/recovery/quarantine metrics and stable reason codes suitable for SLOs and incident response.
- [ ] **MC-033-Q10** — Test failures at multiple timing points, including failures during recovery itself, and assert isolation/resource invariants.
- [ ] **MC-033-Q11** — Record recovery objective versus observed detection/recovery time and any residual operator action in evidence.

### Verification and acceptance checklist

- [ ] **MC-033-A01** — Every defined fault scenario meets its recovery/quarantine objective or produces a release-blocking failure.
- [ ] **MC-033-A02** — Fault results include invariant checks for isolation, duplicates, leaks, and recovery time.

### Required closure evidence

- [ ] **MC-033-E01** — Record traceability from `MC-033` and `C060, C089` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-033-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-033-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-033-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-033-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-033` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Performance/capacity gaps

## MC-034 — Benchmark harness and baselines

**Priority:** P1  
**Source checks:** `C061-C064, C088`  
**Primary discipline:** Performance / Capacity Engineering  
**Audit gap:** no measured startup distribution, throughput, CPU/memory/storage/network overhead, density, steady/burst/overload/scale/recovery, soak, or fleet-scale results.

### Suggested repository artifacts

- [ ] `benchmarks/` — create or map to an equivalent traceable artifact.
- [ ] `benchmarks/baselines/` — create or map to an equivalent traceable artifact.
- [ ] `tools/run_benchmarks.py` — create or map to an equivalent traceable artifact.
- [ ] `evidence/performance/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-034-I01** — Create a reproducible benchmark harness that records host CPU/model, kernel/KVM, architecture, Firecracker build, guest kernel/rootfs digests, runtime/config versions, CPU governor, NUMA, storage/network setup, and background-load controls.
- [ ] **MC-034-I02** — Measure cold boot and restore distributions, create/stop throughput, lifecycle API latency, CPU/memory overhead, disk/network throughput/latency, file descriptors, host page/cache impact, and maximum stable density.
- [ ] **MC-034-I03** — Run steady, burst, overload, scale-out, scale-in, recovery, and long soak scenarios with per-tenant/per-workload attribution.
- [ ] **MC-034-I04** — Use statistically defensible sample counts/warmup, report p50/p95/p99/max and confidence/variance where practical, and retain raw measurements—not only summary charts.
- [ ] **MC-034-I05** — Create immutable baseline artifacts per approved hardware profile and compare every candidate release under equivalent conditions.
- [ ] **MC-034-Q06** — Define a reproducible environment profile and measurement methodology before accepting benchmark numbers.
- [ ] **MC-034-Q07** — Measure distributions and saturation, not averages alone; retain raw data and environment/artifact fingerprints.
- [ ] **MC-034-Q08** — Attribute resource use by workload/tenant where possible and enforce hard ceilings before host-level failure.
- [ ] **MC-034-Q09** — Correlate performance with correctness/security—no optimization may bypass validation, isolation, integrity, or auditing.
- [ ] **MC-034-Q10** — Automate regression comparison against approved baselines and require explicit waiver for release-gate exceptions.
- [ ] **MC-034-Q11** — Archive raw results, summarized thresholds, tool versions, and baseline/candidate hashes as evidence.

### Verification and acceptance checklist

- [ ] **MC-034-A01** — Baselines contain raw reproducible results for all approved profiles and required load modes.
- [ ] **MC-034-A02** — Re-running an approved baseline on equivalent hardware produces variance within the defined tolerance.

### Required closure evidence

- [ ] **MC-034-E01** — Record traceability from `MC-034` and `C061-C064, C088` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-034-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-034-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-034-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-034-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-034` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-035 — Tail-latency thresholds beyond boot ceiling

**Priority:** P1  
**Source checks:** `C062`  
**Primary discipline:** Performance / Capacity Engineering  
**Audit gap:** no p50/p95/p99/worst-case targets and evidence for lifecycle/control/data paths.

### Suggested repository artifacts

- [ ] `performance/thresholds.yaml` — create or map to an equivalent traceable artifact.
- [ ] `benchmarks/latency/` — create or map to an equivalent traceable artifact.
- [ ] `tests/performance/test_latency_gates.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-035-I01** — Define explicit p50/p95/p99/max targets for create, cold boot, snapshot restore, pause, resume, stop, status/health, admission, and critical device/data paths; keep cold-boot p99 compatible with the declared 125 ms ceiling or formally revise the contract.
- [ ] **MC-035-I02** — Specify the measurement start/stop points and whether queue time, artifact fetch, host setup, guest readiness, or control-plane latency is included for each metric.
- [ ] **MC-035-I03** — Define separate targets per environment/hardware profile and overload/degraded conditions instead of one misleading global number.
- [ ] **MC-035-I04** — Add statistically stable latency tests that fail on both absolute threshold violation and material regression against the approved baseline.
- [ ] **MC-035-I05** — Correlate tail spikes with queue depth, CPU steal, page faults, I/O, dependency latency, and guest image state so the limit is diagnostically useful.
- [ ] **MC-035-Q06** — Define a reproducible environment profile and measurement methodology before accepting benchmark numbers.
- [ ] **MC-035-Q07** — Measure distributions and saturation, not averages alone; retain raw data and environment/artifact fingerprints.
- [ ] **MC-035-Q08** — Attribute resource use by workload/tenant where possible and enforce hard ceilings before host-level failure.
- [ ] **MC-035-Q09** — Correlate performance with correctness/security—no optimization may bypass validation, isolation, integrity, or auditing.
- [ ] **MC-035-Q10** — Automate regression comparison against approved baselines and require explicit waiver for release-gate exceptions.
- [ ] **MC-035-Q11** — Archive raw results, summarized thresholds, tool versions, and baseline/candidate hashes as evidence.

### Verification and acceptance checklist

- [ ] **MC-035-A01** — All required operations have measurable percentile/max thresholds and release tests enforce them.
- [ ] **MC-035-A02** — Cold-boot target is reconciled with the 125 ms contract budget using an explicit measurement definition.

### Required closure evidence

- [ ] **MC-035-E01** — Record traceability from `MC-035` and `C062` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-035-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-035-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-035-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-035-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-035` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-036 — Optimization analysis/evidence

**Priority:** P2  
**Source checks:** `C065-C066`  
**Primary discipline:** Performance / Capacity Engineering  
**Audit gap:** no profiling/copy/context-switch/network-hop analysis or demonstrated zero-copy/batching/kernel-bypass choices.

### Suggested repository artifacts

- [ ] `performance/PROFILING.md` — create or map to an equivalent traceable artifact.
- [ ] `profiles/` — create or map to an equivalent traceable artifact.
- [ ] `benchmarks/optimization/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-036-I01** — Profile CPU cycles, syscalls, context switches, page faults, allocations, copies, serialization, lock contention, network hops, disk I/O, image duplication, and queueing across create/boot/data-path/teardown flows.
- [ ] **MC-036-I02** — Quantify each candidate optimization before implementation and record semantic/security constraints so performance work cannot bypass validation, isolation, auditing, or integrity checks.
- [ ] **MC-036-I03** — Where justified, implement locality, immutable artifact caching, batched API/device operations, direct composition, zero-copy buffers, shared read-only image layers, or kernel-bypass features with bounded resource ownership.
- [ ] **MC-036-I04** — Measure before/after effects on p50/p99, throughput, CPU, memory, density, power, and failure recovery; reject optimizations that improve averages while worsening unacceptable tails or isolation.
- [ ] **MC-036-I05** — Keep optimization feature flags/versioned config reversible and include fallback behavior plus regression tests for both optimized and baseline paths.
- [ ] **MC-036-Q06** — Define a reproducible environment profile and measurement methodology before accepting benchmark numbers.
- [ ] **MC-036-Q07** — Measure distributions and saturation, not averages alone; retain raw data and environment/artifact fingerprints.
- [ ] **MC-036-Q08** — Attribute resource use by workload/tenant where possible and enforce hard ceilings before host-level failure.
- [ ] **MC-036-Q09** — Correlate performance with correctness/security—no optimization may bypass validation, isolation, integrity, or auditing.
- [ ] **MC-036-Q10** — Automate regression comparison against approved baselines and require explicit waiver for release-gate exceptions.
- [ ] **MC-036-Q11** — Archive raw results, summarized thresholds, tool versions, and baseline/candidate hashes as evidence.

### Verification and acceptance checklist

- [ ] **MC-036-A01** — Each accepted optimization has before/after evidence and a reversible fallback.
- [ ] **MC-036-A02** — No optimization increases attack surface or bypasses validation/integrity/isolation controls without formal review.

### Required closure evidence

- [ ] **MC-036-E01** — Record traceability from `MC-036` and `C065-C066` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-036-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-036-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-036-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-036-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-036` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-037 — Full resource fan-out limits

**Priority:** P0  
**Source checks:** `C017, C028, C067, C069`  
**Primary discipline:** Performance / Capacity Engineering  
**Audit gap:** per-instance vCPU/memory are now bounded, but no fleet instance quota, per-tenant fairness, queue/connection/buffer/concurrency limits, density model, or saturation predictor.

### Suggested repository artifacts

- [ ] `config/resource_limits.yaml` — create or map to an equivalent traceable artifact.
- [ ] `inv24_microvm_runtime/capacity/` — create or map to an equivalent traceable artifact.
- [ ] `tests/resilience/test_resource_limits.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-037-I01** — Define hard and soft limits for total/running/starting VMs, vCPU and memory commitments, per-tenant quotas, create concurrency, admission queue depth, API connections, TAP/vsock allocations, open files, logs/diagnostics buffers, snapshot operations, and backend queues.
- [ ] **MC-037-I02** — Implement checked arithmetic and overflow-safe accounting with reservations before allocation and guaranteed release on every failure/cancellation/cleanup path.
- [ ] **MC-037-I03** — Define fairness policy (for example weighted shares/minimum guarantees) so one tenant cannot consume all create slots, queue entries, memory, or I/O capacity.
- [ ] **MC-037-I04** — Expose saturation ratios and predicted exhaustion time for every critical resource, with admission/load shedding before host OOM/FD/network collapse.
- [ ] **MC-037-I05** — Test boundary values, concurrent reserve/release, leak after failed boot, quota changes, tenant churn, overload, and restart reconciliation; prove counters converge to actual host resources.
- [ ] **MC-037-Q06** — Define a reproducible environment profile and measurement methodology before accepting benchmark numbers.
- [ ] **MC-037-Q07** — Measure distributions and saturation, not averages alone; retain raw data and environment/artifact fingerprints.
- [ ] **MC-037-Q08** — Attribute resource use by workload/tenant where possible and enforce hard ceilings before host-level failure.
- [ ] **MC-037-Q09** — Correlate performance with correctness/security—no optimization may bypass validation, isolation, integrity, or auditing.
- [ ] **MC-037-Q10** — Automate regression comparison against approved baselines and require explicit waiver for release-gate exceptions.
- [ ] **MC-037-Q11** — Archive raw results, summarized thresholds, tool versions, and baseline/candidate hashes as evidence.

### Verification and acceptance checklist

- [ ] **MC-037-A01** — All configured resources remain bounded during long/overload/concurrent tests and accounting has no leak.
- [ ] **MC-037-A02** — Saturation signals trigger admission/load shedding before hard host exhaustion.

### Required closure evidence

- [ ] **MC-037-E01** — Record traceability from `MC-037` and `C017, C028, C067, C069` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-037-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-037-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-037-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-037-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-037` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-038 — Power/thermal characterization

**Priority:** P2  
**Source checks:** `C068`  
**Primary discipline:** Performance / Capacity Engineering  
**Audit gap:** no edge-node power or thermal measurements.

### Suggested repository artifacts

- [ ] `benchmarks/power/` — create or map to an equivalent traceable artifact.
- [ ] `docs/POWER_THERMAL.md` — create or map to an equivalent traceable artifact.
- [ ] `evidence/power/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-038-I01** — Define representative constrained edge hardware profiles, ambient/thermal conditions, CPU governor/frequency policy, power measurement method, and instrumentation calibration.
- [ ] **MC-038-I02** — Measure idle runtime overhead, per-VM startup energy, steady guest energy, network/storage load, snapshot/restore, burst creation, and maximum-density thermal behavior.
- [ ] **MC-038-I03** — Record sustained temperature, throttling frequency/duration, package/system power where available, battery/UPS impact where relevant, and performance degradation under thermal throttling.
- [ ] **MC-038-I04** — Define power/thermal admission or derating thresholds if the far-edge profile can become unsafe/unreliable under sustained load.
- [ ] **MC-038-I05** — Persist raw measurement data and hardware/firmware identifiers; make this gate conditional only for profiles where C068 is applicable, not silently skipped.
- [ ] **MC-038-Q06** — Define a reproducible environment profile and measurement methodology before accepting benchmark numbers.
- [ ] **MC-038-Q07** — Measure distributions and saturation, not averages alone; retain raw data and environment/artifact fingerprints.
- [ ] **MC-038-Q08** — Attribute resource use by workload/tenant where possible and enforce hard ceilings before host-level failure.
- [ ] **MC-038-Q09** — Correlate performance with correctness/security—no optimization may bypass validation, isolation, integrity, or auditing.
- [ ] **MC-038-Q10** — Automate regression comparison against approved baselines and require explicit waiver for release-gate exceptions.
- [ ] **MC-038-Q11** — Archive raw results, summarized thresholds, tool versions, and baseline/candidate hashes as evidence.

### Verification and acceptance checklist

- [ ] **MC-038-A01** — Applicable edge profiles have repeatable power/thermal data and documented derating/admission behavior.
- [ ] **MC-038-A02** — Thermal throttling does not silently violate required SLOs without health/alert indication.

### Required closure evidence

- [ ] **MC-038-E01** — Record traceability from `MC-038` and `C068` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-038-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-038-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-038-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-038-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-038` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-039 — Performance regression release gate

**Priority:** P1  
**Source checks:** `C070`  
**Primary discipline:** Performance / Capacity Engineering  
**Audit gap:** no automated benchmark threshold gate in CI/release tooling.

### Suggested repository artifacts

- [ ] `ci/performance_gate.py` — create or map to an equivalent traceable artifact.
- [ ] `performance/approved_baseline.json` — create or map to an equivalent traceable artifact.
- [ ] `evidence/performance/gate.json` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-039-I01** — Create approved baseline files containing threshold values, tolerated regression percentage, benchmark profile ID, sample methodology, and provenance.
- [ ] **MC-039-I02** — Run the required benchmark subset on release candidates in a controlled environment and compare startup, density, throughput, CPU/memory overhead, and tail latency against both absolute and relative gates.
- [ ] **MC-039-I03** — Distinguish measurement noise from regression using repetition and predefined significance/variance rules; prohibit manual cherry-picking of runs.
- [ ] **MC-039-I04** — Emit a machine-readable PASS/FAIL/WAIVED result with exact baseline/candidate commits, environment fingerprint, metric deltas, and links to raw data.
- [ ] **MC-039-I05** — Wire failure into the release/production gate; any override must reference an unexpired exception with owner, rationale, risk, and approval.
- [ ] **MC-039-Q06** — Define a reproducible environment profile and measurement methodology before accepting benchmark numbers.
- [ ] **MC-039-Q07** — Measure distributions and saturation, not averages alone; retain raw data and environment/artifact fingerprints.
- [ ] **MC-039-Q08** — Attribute resource use by workload/tenant where possible and enforce hard ceilings before host-level failure.
- [ ] **MC-039-Q09** — Correlate performance with correctness/security—no optimization may bypass validation, isolation, integrity, or auditing.
- [ ] **MC-039-Q10** — Automate regression comparison against approved baselines and require explicit waiver for release-gate exceptions.
- [ ] **MC-039-Q11** — Archive raw results, summarized thresholds, tool versions, and baseline/candidate hashes as evidence.

### Verification and acceptance checklist

- [ ] **MC-039-A01** — Candidate release automatically fails when an approved absolute/relative performance threshold regresses.
- [ ] **MC-039-A02** — Any override is traceable to an unexpired approved exception and preserves the underlying failed metric.

### Required closure evidence

- [ ] **MC-039-E01** — Record traceability from `MC-039` and `C070` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-039-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-039-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-039-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-039-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-039` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Observability gaps

## MC-040 — Runtime metrics exporter

**Priority:** P0  
**Source checks:** `C071-C072`  
**Primary discipline:** Observability / SRE  
**Audit gap:** contract names metrics, but no counter/gauge/histogram implementation, exporter, scrape endpoint, or dependency/capability/version health surface.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/telemetry/metrics.py` — create or map to an equivalent traceable artifact.
- [ ] `schemas/metrics.yaml` — create or map to an equivalent traceable artifact.
- [ ] `tests/observability/test_metrics.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-040-I01** — Implement metrics for instance counts by state, create/boot/stop rates, failures by stable reason code, boot/operation latency histograms, admission queue/backlog, resource saturation, device refusals, budget breaches, VMM crashes, cleanup failures, dependency health, and capability/version state.
- [ ] **MC-040-I02** — Define metric names, units, labels, histogram buckets, monotonicity, reset behavior, and cardinality budgets; avoid tenant/workload IDs as unrestricted metric labels.
- [ ] **MC-040-I03** — Expose metrics through a bounded authenticated/local scrape endpoint or approved exporter and ensure exporter failure cannot block VM lifecycle.
- [ ] **MC-040-I04** — Provide build/runtime/config/Firecracker/kernel version info and active capability gauges suitable for fleet inventory and compatibility diagnosis.
- [ ] **MC-040-I05** — Test exact metric changes for lifecycle transitions and error paths, cardinality bounds under attacker-controlled identifiers, scrape failure, and concurrent updates.
- [ ] **MC-040-Q06** — Define signal schemas, stable event/metric names, units, cardinality limits, and correlation identifiers before instrumenting.
- [ ] **MC-040-Q07** — Keep telemetry non-blocking/bounded and specify behavior for exporter/sink outage, backpressure, disk-full, and high-rate error storms.
- [ ] **MC-040-Q08** — Apply redaction/data classification before export and test with seeded secrets/tenant data.
- [ ] **MC-040-Q09** — Correlate signals to runtime/config/artifact version and operation/instance identity so production behavior is explainable.
- [ ] **MC-040-Q10** — Create automated tests for emitted signal content and alert/dashboard semantics rather than relying only on visual inspection.
- [ ] **MC-040-Q11** — Document retention/access/sampling and retain representative telemetry evidence for release/fault-injection scenarios.

### Verification and acceptance checklist

- [ ] **MC-040-A01** — Lifecycle/error/load tests produce expected metrics with bounded cardinality and correct units/histograms.
- [ ] **MC-040-A02** — Metrics exporter outage cannot stall or crash lifecycle operations.

### Required closure evidence

- [ ] **MC-040-E01** — Record traceability from `MC-040` and `C071-C072` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-040-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-040-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-040-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-040-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-040` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-041 — Structured logging

**Priority:** P0  
**Source checks:** `C073`  
**Primary discipline:** Observability / SRE  
**Audit gap:** no logger/event schema with stable node/tenant/workload/component/operation correlation IDs.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/telemetry/logging.py` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_LOG_EVENT_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/observability/test_logging.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-041-I01** — Define a versioned structured log event schema with timestamp, severity, component, node, tenant/workload (when permitted), instance, operation/trace IDs, event code, state transition, reason code, and redacted structured details.
- [ ] **MC-041-I02** — Use stable event codes rather than parsing free text for alerts/automation; separate operator-safe message from internal diagnostic fields.
- [ ] **MC-041-I03** — Centralize redaction and length limits before serialization; reject newline/control-character/log-injection payloads and bound nested/untrusted data.
- [ ] **MC-041-I04** — Define log levels/rate limits/sampling for noisy paths and a backpressure/drop policy so logging cannot exhaust disk/memory or stall lifecycle operations.
- [ ] **MC-041-I05** — Test correlation completeness, schema validity, secret/tenant leakage, injection, oversized fields, disk-full/sink failure, and high-rate error storms.
- [ ] **MC-041-Q06** — Define signal schemas, stable event/metric names, units, cardinality limits, and correlation identifiers before instrumenting.
- [ ] **MC-041-Q07** — Keep telemetry non-blocking/bounded and specify behavior for exporter/sink outage, backpressure, disk-full, and high-rate error storms.
- [ ] **MC-041-Q08** — Apply redaction/data classification before export and test with seeded secrets/tenant data.
- [ ] **MC-041-Q09** — Correlate signals to runtime/config/artifact version and operation/instance identity so production behavior is explainable.
- [ ] **MC-041-Q10** — Create automated tests for emitted signal content and alert/dashboard semantics rather than relying only on visual inspection.
- [ ] **MC-041-Q11** — Document retention/access/sampling and retain representative telemetry evidence for release/fault-injection scenarios.

### Verification and acceptance checklist

- [ ] **MC-041-A01** — All production log events validate against schema and contain required correlation/reason fields without seeded secrets.
- [ ] **MC-041-A02** — Log sink failure/high-rate storms remain bounded and observable.

### Required closure evidence

- [ ] **MC-041-E01** — Record traceability from `MC-041` and `C073` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-041-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-041-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-041-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-041-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-041` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-042 — Distributed tracing

**Priority:** P1  
**Source checks:** `C074`  
**Primary discipline:** Observability / SRE  
**Audit gap:** no trace context propagation or spans.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/telemetry/tracing.py` — create or map to an equivalent traceable artifact.
- [ ] `docs/TRACING.md` — create or map to an equivalent traceable artifact.
- [ ] `tests/observability/test_trace_propagation.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-042-I01** — Adopt one trace-context format and propagate it across PLN-04 admission, runtime adapter, Firecracker supervision, device/snapshot backends, artifact/policy/identity/KMS calls, and operator actions where protocols allow.
- [ ] **MC-042-I02** — Create spans for admission, validation, artifact resolution, VMM launch/configure, guest boot readiness, lifecycle operations, snapshot/restore, cleanup, and dependency calls with stable status/reason attributes.
- [ ] **MC-042-I03** — Define sampling policy and attribute allowlist/cardinality limits; never place secrets or unrestricted guest/tenant content in baggage/spans.
- [ ] **MC-042-I04** — Preserve parent/child linkage through retries and async operations while giving each retry/attempt its own span and operation attempt number.
- [ ] **MC-042-I05** — Test context propagation, missing/invalid context handling, exporter outage, sampling, and cross-component trace correlation in integration environments.
- [ ] **MC-042-Q06** — Define signal schemas, stable event/metric names, units, cardinality limits, and correlation identifiers before instrumenting.
- [ ] **MC-042-Q07** — Keep telemetry non-blocking/bounded and specify behavior for exporter/sink outage, backpressure, disk-full, and high-rate error storms.
- [ ] **MC-042-Q08** — Apply redaction/data classification before export and test with seeded secrets/tenant data.
- [ ] **MC-042-Q09** — Correlate signals to runtime/config/artifact version and operation/instance identity so production behavior is explainable.
- [ ] **MC-042-Q10** — Create automated tests for emitted signal content and alert/dashboard semantics rather than relying only on visual inspection.
- [ ] **MC-042-Q11** — Document retention/access/sampling and retain representative telemetry evidence for release/fault-injection scenarios.

### Verification and acceptance checklist

- [ ] **MC-042-A01** — End-to-end integration test shows a trace across admission → runtime → dependencies/VMM lifecycle with correct parentage.
- [ ] **MC-042-A02** — Invalid/missing trace context cannot cause operation failure or data leakage, and exporter outage is non-blocking.

### Required closure evidence

- [ ] **MC-042-E01** — Record traceability from `MC-042` and `C074` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-042-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-042-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-042-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-042-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-042` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-043 — Safe high-cardinality diagnostics/redaction

**Priority:** P0  
**Source checks:** `C075`  
**Primary discipline:** Observability / SRE  
**Audit gap:** no bounded diagnostics endpoint, redaction policy, or leakage tests.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/diagnostics/` — create or map to an equivalent traceable artifact.
- [ ] `docs/REDACTION_POLICY.md` — create or map to an equivalent traceable artifact.
- [ ] `tests/security/test_diagnostic_redaction.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-043-I01** — Define a bounded diagnostics API/support bundle that can expose process/VMM state, sanitized config, dependency versions, health, recent stable event codes, resource counters, and selected host capability data without arbitrary file/process access.
- [ ] **MC-043-I02** — Create a field-level data classification/redaction policy for tenant IDs, workload metadata, paths, IP/MAC, snapshot data, credentials, tokens, keys, environment variables, command lines, and guest output.
- [ ] **MC-043-I03** — Apply size/time/rate limits, authorization, audit logging, and pagination/stream bounds so diagnostics cannot become a DoS or exfiltration channel.
- [ ] **MC-043-I04** — Use opaque diagnostic references in ordinary errors; require elevated capability for detailed support bundles and record who accessed/exported them.
- [ ] **MC-043-I05** — Run seeded canary-secret/PII leakage tests across logs, metrics labels, traces, errors, diagnostics, crash dumps, and archived evidence.
- [ ] **MC-043-Q06** — Define signal schemas, stable event/metric names, units, cardinality limits, and correlation identifiers before instrumenting.
- [ ] **MC-043-Q07** — Keep telemetry non-blocking/bounded and specify behavior for exporter/sink outage, backpressure, disk-full, and high-rate error storms.
- [ ] **MC-043-Q08** — Apply redaction/data classification before export and test with seeded secrets/tenant data.
- [ ] **MC-043-Q09** — Correlate signals to runtime/config/artifact version and operation/instance identity so production behavior is explainable.
- [ ] **MC-043-Q10** — Create automated tests for emitted signal content and alert/dashboard semantics rather than relying only on visual inspection.
- [ ] **MC-043-Q11** — Document retention/access/sampling and retain representative telemetry evidence for release/fault-injection scenarios.

### Verification and acceptance checklist

- [ ] **MC-043-A01** — Diagnostics reveal enough bounded state to debug common failures while canary secret/tenant leakage tests remain clean.
- [ ] **MC-043-A02** — Unauthorized diagnostics/support-bundle access is denied and audited.

### Required closure evidence

- [ ] **MC-043-E01** — Record traceability from `MC-043` and `C075` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-043-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-043-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-043-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-043-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-043` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-044 — Decision/explain records

**Priority:** P1  
**Source checks:** `C076-C078`  
**Primary discipline:** Observability / SRE  
**Audit gap:** no reason records, topology/policy linkage, release lineage correlation, or live infrastructure graph linkage.

### Suggested repository artifacts

- [ ] `inv24_microvm_runtime/explain/` — create or map to an equivalent traceable artifact.
- [ ] `schemas/PK_DECISION_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `tests/observability/test_explain_records.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-044-I01** — Define a versioned decision record for admission, rejection, retry, failover, quarantine, degraded-mode entry, config rollback, and automated cleanup decisions.
- [ ] **MC-044-I02** — Record inputs by immutable references/digests: policy/config version, host capacity/saturation, dependency health, topology/site/residency, artifact version, capability identity, and relevant thresholds.
- [ ] **MC-044-I03** — Capture deterministic reason codes and ordered rule/policy evaluations sufficient for an operator to reproduce why the action occurred without exposing secrets.
- [ ] **MC-044-I04** — Correlate decisions with release lineage (runtime commit/version, Firecracker/kernel/rootfs digests) and infrastructure graph identifiers/node generation.
- [ ] **MC-044-I05** — Provide an operator explain view/query and tests proving a decision can be reconstructed from stored records even after a rollout or topology change.
- [ ] **MC-044-Q06** — Define signal schemas, stable event/metric names, units, cardinality limits, and correlation identifiers before instrumenting.
- [ ] **MC-044-Q07** — Keep telemetry non-blocking/bounded and specify behavior for exporter/sink outage, backpressure, disk-full, and high-rate error storms.
- [ ] **MC-044-Q08** — Apply redaction/data classification before export and test with seeded secrets/tenant data.
- [ ] **MC-044-Q09** — Correlate signals to runtime/config/artifact version and operation/instance identity so production behavior is explainable.
- [ ] **MC-044-Q10** — Create automated tests for emitted signal content and alert/dashboard semantics rather than relying only on visual inspection.
- [ ] **MC-044-Q11** — Document retention/access/sampling and retain representative telemetry evidence for release/fault-injection scenarios.

### Verification and acceptance checklist

- [ ] **MC-044-A01** — Operators can reconstruct sampled automated decisions from immutable input/policy/config/topology/release references.
- [ ] **MC-044-A02** — Reason records survive rollout and remain correlated to the exact runtime/artifact lineage.

### Required closure evidence

- [ ] **MC-044-E01** — Record traceability from `MC-044` and `C076-C078` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-044-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-044-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-044-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-044-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-044` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-045 — Telemetry governance

**Priority:** P1  
**Source checks:** `C079`  
**Primary discipline:** Observability / SRE  
**Audit gap:** no retention, sampling, privacy, access, or export policy.

### Suggested repository artifacts

- [ ] `docs/TELEMETRY_GOVERNANCE.md` — create or map to an equivalent traceable artifact.
- [ ] `telemetry/policy.yaml` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-045-I01** — Define retention periods per telemetry class (metrics/logs/traces/audit/diagnostics), legal/security rationale, storage tier, deletion process, and exceptions for incidents/investigations.
- [ ] **MC-045-I02** — Define sampling rules by signal/severity/tenant, minimum unsampled security/error events, and how sampling changes are authorized/audited.
- [ ] **MC-045-I03** — Document data classification, tenant isolation, access roles, export destinations, residency constraints, encryption, and third-party processor restrictions.
- [ ] **MC-045-I04** — Set cardinality and volume budgets plus overload behavior so telemetry cannot cause runtime failure or uncontrolled cost.
- [ ] **MC-045-I05** — Create periodic governance checks for retention enforcement, access review, exporter configuration drift, redaction effectiveness, and orphaned telemetry stores.
- [ ] **MC-045-Q06** — Define signal schemas, stable event/metric names, units, cardinality limits, and correlation identifiers before instrumenting.
- [ ] **MC-045-Q07** — Keep telemetry non-blocking/bounded and specify behavior for exporter/sink outage, backpressure, disk-full, and high-rate error storms.
- [ ] **MC-045-Q08** — Apply redaction/data classification before export and test with seeded secrets/tenant data.
- [ ] **MC-045-Q09** — Correlate signals to runtime/config/artifact version and operation/instance identity so production behavior is explainable.
- [ ] **MC-045-Q10** — Create automated tests for emitted signal content and alert/dashboard semantics rather than relying only on visual inspection.
- [ ] **MC-045-Q11** — Document retention/access/sampling and retain representative telemetry evidence for release/fault-injection scenarios.

### Verification and acceptance checklist

- [ ] **MC-045-A01** — Retention/sampling/access/export controls are documented, enforced, reviewable, and tested for deletion/access drift.
- [ ] **MC-045-A02** — Security/audit events retain the minimum required fidelity independent of ordinary telemetry sampling.

### Required closure evidence

- [ ] **MC-045-E01** — Record traceability from `MC-045` and `C079` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-045-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-045-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-045-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-045-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-045` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-046 — Dashboards/alerts

**Priority:** P1  
**Source checks:** `C080`  
**Primary discipline:** Observability / SRE  
**Audit gap:** no dashboard definitions or alert rules distinguishing overload, policy rejection, dependency failure, attack, and defect.

### Suggested repository artifacts

- [ ] `observability/dashboards/` — create or map to an equivalent traceable artifact.
- [ ] `observability/alerts/` — create or map to an equivalent traceable artifact.
- [ ] `tests/observability/test_alert_rules.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-046-I01** — Create dashboards for fleet/node/tenant workload counts, boot latency and budget breaches, admission/backlog/saturation, VMM/guest failures, dependency health, resource usage/density, artifact/config versions, and quarantine/degraded states.
- [ ] **MC-046-I02** — Define alert rules that distinguish overload/capacity, policy/auth rejection, dependency outage, artifact-integrity failure, suspected attack, VMM/kernel defect, and SLO burn instead of using one generic failure alert.
- [ ] **MC-046-I03** — Attach severity, owner, runbook URL/identifier, deduplication key, inhibition relationship, and clear/resolve condition to every page-producing alert.
- [ ] **MC-046-I04** — Test alert rules against synthetic metric/log fixtures for firing, non-firing, recovery, flapping/hysteresis, and duplicate suppression.
- [ ] **MC-046-I05** — Review dashboard/alert usefulness during fault-injection and incident exercises; remove alerts that cannot drive an actionable response.
- [ ] **MC-046-Q06** — Define signal schemas, stable event/metric names, units, cardinality limits, and correlation identifiers before instrumenting.
- [ ] **MC-046-Q07** — Keep telemetry non-blocking/bounded and specify behavior for exporter/sink outage, backpressure, disk-full, and high-rate error storms.
- [ ] **MC-046-Q08** — Apply redaction/data classification before export and test with seeded secrets/tenant data.
- [ ] **MC-046-Q09** — Correlate signals to runtime/config/artifact version and operation/instance identity so production behavior is explainable.
- [ ] **MC-046-Q10** — Create automated tests for emitted signal content and alert/dashboard semantics rather than relying only on visual inspection.
- [ ] **MC-046-Q11** — Document retention/access/sampling and retain representative telemetry evidence for release/fault-injection scenarios.

### Verification and acceptance checklist

- [ ] **MC-046-A01** — Synthetic scenarios fire the correct distinct alerts with actionable runbook/owner and clear correctly on recovery.
- [ ] **MC-046-A02** — Alert/load tests avoid uncontrolled duplicate pages and dashboard queries respect cardinality budgets.

### Required closure evidence

- [ ] **MC-046-E01** — Record traceability from `MC-046` and `C080` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-046-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-046-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-046-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-046-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-046` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Testing and certification gaps

## MC-047 — Framework-independent contract tests for every interface

**Priority:** P0  
**Source checks:** `C082`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** standalone unit tests cover the domain object, but there are no formal schema/consumer contract tests for all external boundaries.

### Suggested repository artifacts

- [ ] `tests/contracts/` — create or map to an equivalent traceable artifact.
- [ ] `fixtures/contracts/` — create or map to an equivalent traceable artifact.
- [ ] `tools/contract_test.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-047-I01** — Create consumer/provider contract tests for every published schema and boundary, independent of `pk_core`, so local certification does not collapse to skipped tests when the framework is absent.
- [ ] **MC-047-I02** — Validate canonical success and every stable error/retryability code for create, boot, lifecycle, status/health, admission, device, snapshot, audit, diagnostics, and explain APIs.
- [ ] **MC-047-I03** — Use golden fixtures to assert required fields, type/range limits, unknown-field/version behavior, deterministic serialization, and backward/forward compatibility expectations.
- [ ] **MC-047-I04** — Run tests against both in-process serializers and actual transport adapters (for example Firecracker UDS wrapper/control-plane RPC) to detect translation drift.
- [ ] **MC-047-I05** — Fail CI when a schema/interface changes without corresponding version change, fixture update, compatibility decision, and traceability entry.
- [ ] **MC-047-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-047-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-047-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-047-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-047-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-047-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-047-A01** — Every public interface has independent provider/consumer contract tests runnable without `pk_core`.
- [ ] **MC-047-A02** — Schema/interface drift or a silently skipped required test fails CI.

### Required closure evidence

- [ ] **MC-047-E01** — Record traceability from `MC-047` and `C082` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-047-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-047-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-047-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-047-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-047` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-048 — Adjacent-layer integration tests

**Priority:** P0  
**Source checks:** `C030, C083`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** none are bundled.

### Suggested repository artifacts

- [ ] `tests/integration/` — create or map to an equivalent traceable artifact.
- [ ] `tests/integration/environment/` — create or map to an equivalent traceable artifact.
- [ ] `evidence/integration/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-048-I01** — Build integration environments for INV-23 KVM, INV-25 devices, PLN-04 admission, INV-26 snapshotting, optional INV-35 I/O, plus identity/policy/artifact/KMS/telemetry dependencies used by the production profile.
- [ ] **MC-048-I02** — Test the full create → configure → boot → health → pause/resume → stop/destroy path and snapshot restore path where enabled using real adapters rather than only mocks.
- [ ] **MC-048-I03** — Exercise boundary failures and version mismatch for each adjacent layer and verify stable error mapping, cleanup, retries, degradation, and audit/telemetry behavior.
- [ ] **MC-048-I04** — Run at least one real guest workload that proves network/block/vsock behavior and one hostile/invalid workload/config path that proves enforcement.
- [ ] **MC-048-I05** — Persist environment manifests, dependency versions/digests, logs/traces, and test results as machine-readable release evidence.
- [ ] **MC-048-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-048-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-048-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-048-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-048-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-048-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-048-A01** — All mandatory adjacent layers complete end-to-end lifecycle tests on an immutable release candidate.
- [ ] **MC-048-A02** — Each integration dependency has at least one failure/version-mismatch cleanup test with retained evidence.

### Required closure evidence

- [ ] **MC-048-E01** — Record traceability from `MC-048` and `C030, C083` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-048-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-048-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-048-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-048-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-048` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-049 — Architecture/provider compatibility matrix tests

**Priority:** P1  
**Source checks:** `C084`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** no x86_64/aarch64, kernel/KVM, Firecracker-version, provider, or protocol-version matrix.

### Suggested repository artifacts

- [ ] `compatibility/matrix.yaml` — create or map to an equivalent traceable artifact.
- [ ] `tests/compatibility/` — create or map to an equivalent traceable artifact.
- [ ] `evidence/compatibility/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-049-I01** — Define the supported test matrix across x86_64/aarch64, host kernel/KVM versions, Firecracker versions, Python versions, guest kernel/rootfs formats, cloud/on-prem/edge provider profiles, and protocol/schema versions.
- [ ] **MC-049-I02** — Identify mandatory combinations (release-blocking) versus extended/periodic combinations and document why unsupported cells are intentionally excluded.
- [ ] **MC-049-I03** — Automate provisioning and capability detection so a skipped cell is reported as NOT_TESTED with reason rather than PASS.
- [ ] **MC-049-I04** — Test peer-version skew, upgrade/downgrade order, mixed-version fleet behavior, snapshot compatibility, and configuration/schema migrations.
- [ ] **MC-049-I05** — Publish per-release matrix results linked to the compatibility policy and block unsupported/unverified combinations at admission where practical.
- [ ] **MC-049-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-049-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-049-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-049-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-049-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-049-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-049-A01** — All mandatory matrix cells are PASS; unsupported/untested cells are explicit and enforced operationally.
- [ ] **MC-049-A02** — Mixed-version and snapshot/config migration scenarios match the published compatibility policy.

### Required closure evidence

- [ ] **MC-049-E01** — Record traceability from `MC-049` and `C084` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-049-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-049-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-049-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-049-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-049` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-050 — Fuzz/property testing

**Priority:** P1  
**Source checks:** `C085`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** no fuzzers/property tests for configuration, schemas, identifiers, timing inputs, lifecycle sequences, device requests, or external payloads.

### Suggested repository artifacts

- [ ] `tests/fuzz/` — create or map to an equivalent traceable artifact.
- [ ] `tests/property/` — create or map to an equivalent traceable artifact.
- [ ] `corpus/` — create or map to an equivalent traceable artifact.
- [ ] `evidence/fuzz/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-050-I01** — Fuzz configuration/schema parsers, identifier/text validation, error envelopes, Firecracker request translation, snapshot metadata, device requests, admission payloads, and any protocol/WIT/RPC decoder handling untrusted bytes/structures.
- [ ] **MC-050-I02** — Add property-based lifecycle tests that generate legal/illegal transition sequences and assert invariants: no boot after terminal destroy, no state resurrection, no mutable tenant/resources, no unknown device, and bounded resources.
- [ ] **MC-050-I03** — Fuzz numeric boundaries, Unicode/control characters, oversized collections, duplicate keys/IDs, pathological nesting, malformed paths, and timeout/budget values.
- [ ] **MC-050-I04** — Persist minimized regression corpus and fixed seeds for every discovered crash/invariant violation; add them to deterministic CI tests before closing the bug.
- [ ] **MC-050-I05** — Use sanitizer/instrumented native dependencies where feasible in dedicated jobs and set explicit time/memory limits so fuzz infrastructure itself is safe.
- [ ] **MC-050-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-050-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-050-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-050-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-050-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-050-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-050-A01** — Fuzz/property campaigns meet configured run budget with no untriaged crash/invariant violation.
- [ ] **MC-050-A02** — Every discovered issue has a minimized corpus case and deterministic regression test.

### Required closure evidence

- [ ] **MC-050-E01** — Record traceability from `MC-050` and `C085` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-050-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-050-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-050-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-050-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-050` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-051 — Concurrency/race tests

**Priority:** P0  
**Source checks:** `C086`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** none; the current in-memory object is not designed for concurrent mutation, and no synchronization contract is specified.

### Suggested repository artifacts

- [ ] `tests/concurrency/` — create or map to an equivalent traceable artifact.
- [ ] `docs/CONCURRENCY_MODEL.md` — create or map to an equivalent traceable artifact.
- [ ] `evidence/concurrency/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-051-I01** — Document the concurrency model: which runtime objects are single-thread confined, which state is shared, lock/transaction ordering, atomicity guarantees, and whether concurrent lifecycle calls are rejected or serialized.
- [ ] **MC-051-I02** — Introduce synchronization or an actor/event-loop ownership model for shared state; never rely on the current dataclass mutation guards as a thread-safety mechanism.
- [ ] **MC-051-I03** — Test create/stop, boot/cancel, pause/resume/stop, duplicate admission, config update, quota reserve/release, health reconciliation, and ownership transfer races with deterministic barriers.
- [ ] **MC-051-I04** — Run high-iteration stress under thread/process concurrency and, where applicable, lock/race tooling; assert no duplicate VMM, leaked reservation, invalid state, deadlock, lost update, or stale-owner mutation.
- [ ] **MC-051-I05** — Define lock timeout/deadlock diagnostics and ensure crash/restart reconciliation handles partially completed concurrent operations.
- [ ] **MC-051-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-051-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-051-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-051-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-051-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-051-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-051-A01** — Stress/barrier tests find no invalid transition, duplicate VMM, leaked reservation, deadlock, or stale-owner mutation.
- [ ] **MC-051-A02** — Concurrency guarantees are documented and enforced by design, not assumed from single-threaded unit tests.

### Required closure evidence

- [ ] **MC-051-E01** — Record traceability from `MC-051` and `C086` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-051-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-051-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-051-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-051-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-051` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-052 — Benchmark/soak/burst/fleet tests

**Priority:** P1  
**Source checks:** `C088`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** absent.

### Suggested repository artifacts

- [ ] `tests/performance/soak/` — create or map to an equivalent traceable artifact.
- [ ] `tests/performance/fleet/` — create or map to an equivalent traceable artifact.
- [ ] `evidence/performance/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-052-I01** — Create workload profiles for steady operation, burst creation, sustained high churn, maximum supported density, multi-tenant contention, and long-duration soak with realistic guest/network/storage activity.
- [ ] **MC-052-I02** — Run enough duration/iterations to expose descriptor/FD/socket/process/memory leaks, allocator/cache growth, metric-cardinality growth, timer drift, and performance degradation.
- [ ] **MC-052-I03** — Capture throughput, p50/p95/p99/max latency, host/guest CPU/memory, I/O, queue depth, failures/retries, cleanup latency, and resource counts throughout the run.
- [ ] **MC-052-I04** — Inject routine maintenance and dependency restarts during soak to measure recovery without turning the test into a purely steady happy path.
- [ ] **MC-052-I05** — Define pass/fail thresholds for error rate, SLO, leak slope, density, recovery, and tail latency and retain raw time-series plus environment manifest.
- [ ] **MC-052-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-052-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-052-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-052-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-052-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-052-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-052-A01** — Soak/burst/fleet runs satisfy leak/error/SLO/density thresholds for the defined duration and scale.
- [ ] **MC-052-A02** — Raw time-series proves resource counts return to baseline after churn/recovery.

### Required closure evidence

- [ ] **MC-052-E01** — Record traceability from `MC-052` and `C088` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-052-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-052-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-052-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-052-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-052` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-053 — Disaster/partition/reconnect tests

**Priority:** P1  
**Source checks:** `C089`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** absent.

### Suggested repository artifacts

- [ ] `tests/disaster/` — create or map to an equivalent traceable artifact.
- [ ] `disaster/scenarios.yaml` — create or map to an equivalent traceable artifact.
- [ ] `evidence/disaster/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-053-I01** — Define disaster scenarios for host loss/reboot, runtime agent crash, Firecracker crash, control-plane partition, site partition, artifact/identity/policy/KMS outage, storage corruption/full, snapshot loss/corruption, and network reconnection.
- [ ] **MC-053-I02** — For each scenario specify RTO/RPO or explicit “reconstruct only” semantics, ownership/fencing expectations, tenant isolation invariants, data-loss expectation, and operator intervention.
- [ ] **MC-053-I03** — Test short/long/asymmetric partitions and reconnect ordering to prove stale controllers/requests do not duplicate execution or override newer state.
- [ ] **MC-053-I04** — Exercise degraded-mode expiry and recovery: cached credentials/policy/artifacts must not remain trusted beyond documented freshness limits.
- [ ] **MC-053-I05** — Archive timeline, fault injection, detection, automated action, operator steps, final reconciliation, and objective result as release/DR evidence.
- [ ] **MC-053-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-053-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-053-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-053-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-053-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-053-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-053-A01** — Required disaster scenarios meet documented RTO/RPO/reconstruction outcomes and preserve single ownership/isolation.
- [ ] **MC-053-A02** — Reconnect tests reject stale controllers/requests and converge to authoritative state.

### Required closure evidence

- [ ] **MC-053-E01** — Record traceability from `MC-053` and `C089` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-053-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-053-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-053-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-053-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-053` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-054 — Machine-readable acceptance evidence

**Priority:** P0  
**Source checks:** `C090, C100`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** no generated gate result/evidence ledger is included; original conformance tests require external `pk_core` and skip when it is missing.

### Suggested repository artifacts

- [ ] `evidence/schema/PK_GATE_RESULTS_V1.json` — create or map to an equivalent traceable artifact.
- [ ] `evidence/ledger.jsonl` — create or map to an equivalent traceable artifact.
- [ ] `tools/verify_evidence.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-054-I01** — Define a versioned machine-readable gate result schema with release identity, commit/digests, environment profile, all C001-C100 statuses, evidence references/hashes, waivers, owners, timestamps, and overall verdict.
- [ ] **MC-054-I02** — Generate an append-only evidence ledger from tests/scans/benchmarks/reviews instead of relying on manually edited status claims; hash/sign the ledger or store it in an integrity-protected system.
- [ ] **MC-054-I03** — Represent PASS, FAIL, NOT_TESTED/BLOCKED, NOT_APPLICABLE (with rationale), and WAIVED distinctly; skipped tests must never become PASS.
- [ ] **MC-054-I04** — Build a verifier that resolves every evidence reference, validates hashes/schema/expiry/signature, checks traceability completeness, and recalculates the verdict independently.
- [ ] **MC-054-I05** — Bundle the verified gate result with each release artifact so production certification is reproducible without hidden external state.
- [ ] **MC-054-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-054-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-054-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-054-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-054-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-054-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-054-A01** — Independent verifier recalculates the same release verdict and rejects tampered/missing/stale evidence.
- [ ] **MC-054-A02** — Skipped/BLOCKED tests cannot be represented as PASS, and every verdict references exact release bytes.

### Required closure evidence

- [ ] **MC-054-E01** — Record traceability from `MC-054` and `C090, C100` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-054-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-054-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-054-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-054-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-054` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-055 — CI pipeline

**Priority:** P0  
**Source checks:** `C070, C090, C100`  
**Primary discipline:** Quality / Systems Test / Release Engineering  
**Audit gap:** no GitHub Actions/other CI definition enforcing compile, unit, security, compatibility, benchmark, artifact-integrity, and release gates.

### Suggested repository artifacts

- [ ] `.github/workflows/ci.yml` — create or map to an equivalent traceable artifact.
- [ ] `ci/` — create or map to an equivalent traceable artifact.
- [ ] `evidence/ci/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-055-I01** — Create CI stages for formatting/static checks, import/compile, unit tests, schema validation, contract tests, security lint/scans, dependency/SBOM/provenance checks, package/bootstrap tests, integration tests, compatibility, fuzz regression, and evidence generation.
- [ ] **MC-055-I02** — Run `python -O` and normal-mode safety tests because prior audit work specifically found assert-stripping risk; prohibit security/lifecycle enforcement that exists only inside `assert`.
- [ ] **MC-055-I03** — Use protected, pinned CI actions/images/toolchains and least-privilege tokens; verify downloaded artifacts and avoid untrusted pull-request code receiving production secrets.
- [ ] **MC-055-I04** — Gate merges/releases on required jobs; report unavailable dedicated-hardware jobs as BLOCKED/NOT_TESTED rather than silently skipping KVM/performance/security coverage.
- [ ] **MC-055-I05** — Create release jobs that produce immutable package/archive, SBOM, checksums/signatures/provenance, test evidence ledger, performance comparison, and production-gate input.
- [ ] **MC-055-Q06** — Make test prerequisites explicit and classify unavailable hardware/dependencies as BLOCKED/NOT_TESTED rather than PASS or silent skip.
- [ ] **MC-055-Q07** — Use deterministic fixtures/seeds where possible and preserve minimized failure artifacts for regression.
- [ ] **MC-055-Q08** — Cover success, boundary, invalid input, timeout, cancellation, crash/restart, security, and cleanup behavior relevant to the target boundary.
- [ ] **MC-055-Q09** — Run tests against the immutable release candidate with pinned tool/dependency versions and record environment fingerprints.
- [ ] **MC-055-Q10** — Emit machine-readable results with test IDs mapped to requirements/traceability; CI must fail on required-test failure or missing evidence.
- [ ] **MC-055-Q11** — Archive logs/traces/metrics needed to diagnose a failure while applying redaction and retention policy.

### Verification and acceptance checklist

- [ ] **MC-055-A01** — Protected CI makes required jobs mandatory and produces a complete signed/hashed release evidence bundle.
- [ ] **MC-055-A02** — Untrusted contributions cannot access release secrets or alter pinned build dependencies without review.

### Required closure evidence

- [ ] **MC-055-E01** — Record traceability from `MC-055` and `C070, C090, C100` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-055-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-055-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-055-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-055-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-055` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Operations/release/governance gaps

## MC-056 — Production SLO/support policy

**Priority:** P0  
**Source checks:** `C091`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** contract has three SLO statements, but no service support commitments, measurement windows, burn-rate/error-budget policy, ownership, or paging criteria.

### Suggested repository artifacts

- [ ] `docs/SLO_SUPPORT_POLICY.md` — create or map to an equivalent traceable artifact.
- [ ] `slo/slo.yaml` — create or map to an equivalent traceable artifact.
- [ ] `slo/error-budget-policy.yaml` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-056-I01** — Convert the three contract SLO statements into measurable SLIs with exact numerator/denominator, event source, aggregation window, exclusions, and per-environment targets.
- [ ] **MC-056-I02** — Define error-budget policy and burn-rate thresholds for boot latency, device-model violations, tenant-isolation events, availability/admission success, and other supported operational objectives.
- [ ] **MC-056-I03** — Specify support hours/on-call coverage, severity response/restore targets, maintenance windows, escalation, and which deployment profiles receive which commitment.
- [ ] **MC-056-I04** — Define what happens when error budget is exhausted (release freeze, mitigation, capacity increase, rollback, exception approval) and who can authorize exceptions.
- [ ] **MC-056-I05** — Validate SLO queries against synthetic data and dashboards and review actual SLO/error-budget results at a defined cadence.
- [ ] **MC-056-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-056-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-056-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-056-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-056-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-056-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-056-A01** — SLO dashboards/queries reproduce documented SLIs/error budgets and trigger defined burn-rate actions.
- [ ] **MC-056-A02** — Support/paging commitments have owners and are exercised during incident/fault drills.

### Required closure evidence

- [ ] **MC-056-E01** — Record traceability from `MC-056` and `C091` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-056-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-056-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-056-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-056-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-056` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-057 — Canary/staged rollout/rollback procedures

**Priority:** P0  
**Source checks:** `C038, C092`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** README gives only a conceptual gate; no executable deployment/rollback runbook or emergency-disable mechanism.

### Suggested repository artifacts

- [ ] `runbooks/ROLLOUT_ROLLBACK.md` — create or map to an equivalent traceable artifact.
- [ ] `deployment/canary/` — create or map to an equivalent traceable artifact.
- [ ] `deployment/emergency-disable/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-057-I01** — Define rollout stages (dev/test/canary/site/percentage/fleet) with entry/exit criteria, minimum observation windows, health/SLO/security checks, and automatic stop conditions.
- [ ] **MC-057-I02** — Support rollback of runtime package, Firecracker/kernel/rootfs artifact set, schema/config revision, and feature flags while respecting version/snapshot compatibility constraints.
- [ ] **MC-057-I03** — Implement emergency disable/deny-admission controls independent of normal rollout automation and test that they remain usable during partial control-plane failure.
- [ ] **MC-057-I04** — Define rollback triggers and maximum decision/rollback time for boot regression, crash loop, isolation/security anomaly, artifact integrity failure, or capacity collapse.
- [ ] **MC-057-I05** — Rehearse forward rollout, automatic rollback, manual rollback, failed rollback, and mixed-version recovery; capture evidence and operator timings.
- [ ] **MC-057-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-057-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-057-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-057-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-057-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-057-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-057-A01** — Canary failure automatically/manual rollback restores an approved version within objective and leaves no incompatible state.
- [ ] **MC-057-A02** — Emergency disable is tested under degraded-control-plane conditions.

### Required closure evidence

- [ ] **MC-057-E01** — Record traceability from `MC-057` and `C038, C092` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-057-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-057-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-057-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-057-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-057` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-058 — Patching/vulnerability/EOL policy

**Priority:** P0  
**Source checks:** `C094`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** no SLA/process for CVEs, Firecracker/kernel updates, coordinated disclosure, supported branches, or EOL.

### Suggested repository artifacts

- [ ] `SECURITY.md` — create or map to an equivalent traceable artifact.
- [ ] `docs/PATCHING_EOL.md` — create or map to an equivalent traceable artifact.
- [ ] `security/support-matrix.yaml` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-058-I01** — Define vulnerability intake from Firecracker, Linux/KVM, guest kernel/base image, Python/runtime dependencies, and internal reports with asset/version mapping to deployed fleet.
- [ ] **MC-058-I02** — Establish severity-based triage/patch SLAs, emergency out-of-band release path, coordinated disclosure/contact, and documented compensating controls when immediate patching is impossible.
- [ ] **MC-058-I03** — Maintain supported release branches and an EOL schedule with advance notice, upgrade path, and behavior when an EOL runtime attempts admission/registration.
- [ ] **MC-058-I04** — Continuously scan SBOMs/artifact manifests for newly disclosed vulnerabilities and distinguish affected/not-affected with evidence rather than package-name matching alone.
- [ ] **MC-058-I05** — Test patch rollouts and rollback for Firecracker/kernel/runtime updates, including snapshot/schema compatibility and mixed-version fleet behavior.
- [ ] **MC-058-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-058-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-058-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-058-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-058-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-058-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-058-A01** — Vulnerability-to-deployed-version mapping and patch/EOL SLA are measurable and tested in a release drill.
- [ ] **MC-058-A02** — EOL/unpatched prohibited versions are visible and prevented from new production admission according to policy.

### Required closure evidence

- [ ] **MC-058-E01** — Record traceability from `MC-058` and `C094` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-058-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-058-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-058-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-058-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-058` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-059 — Backup/restore/reconstruction runbook

**Priority:** P1  
**Source checks:** `C095`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** absent; contract says snapshot is external but does not define operational reconstruction.

### Suggested repository artifacts

- [ ] `runbooks/BACKUP_RESTORE.md` — create or map to an equivalent traceable artifact.
- [ ] `recovery/` — create or map to an equivalent traceable artifact.
- [ ] `tests/disaster/test_reconstruction.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-059-I01** — Classify durable state that actually requires backup (ownership/admission journals, config/policy references, audit/evidence, snapshot metadata) versus reconstructible node-local process state.
- [ ] **MC-059-I02** — Define backup frequency, retention, encryption, integrity, access control, geographic/residency constraints, and immutable/offline protection where required.
- [ ] **MC-059-I03** — Document bare-node reconstruction from approved artifacts/config plus reconciliation of running/orphaned instances when no snapshot is available.
- [ ] **MC-059-I04** — For snapshot-enabled profiles, define catalog recovery, artifact/digest verification, restore authorization, compatibility checks, and behavior when snapshot data is missing/corrupt.
- [ ] **MC-059-I05** — Run restore/reconstruction drills to a clean node/site and measure RTO/RPO, correctness, tenant isolation, ownership fencing, and evidence completeness.
- [ ] **MC-059-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-059-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-059-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-059-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-059-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-059-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-059-A01** — Clean-node/site restore or reconstruction drill meets stated RTO/RPO and produces authoritative fenced state.
- [ ] **MC-059-A02** — Corrupt/missing backup/snapshot cases fail safely and are diagnosable.

### Required closure evidence

- [ ] **MC-059-E01** — Record traceability from `MC-059` and `C095` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-059-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-059-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-059-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-059-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-059` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-060 — Day-0/day-1/day-2 runbooks

**Priority:** P0  
**Source checks:** `C096`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** README has a short outline, not executable/operator-grade procedures with prerequisites, verification, rollback, failure branches, and escalation.

### Suggested repository artifacts

- [ ] `runbooks/DAY0_BOOTSTRAP.md` — create or map to an equivalent traceable artifact.
- [ ] `runbooks/DAY1_DEPLOYMENT.md` — create or map to an equivalent traceable artifact.
- [ ] `runbooks/DAY2_OPERATIONS.md` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-060-I01** — Write Day-0 prerequisites and bootstrap commands/checks for host OS/kernel/KVM, users/groups/permissions, artifact trust roots, networking/storage, config, package install, and initial health/certification.
- [ ] **MC-060-I02** — Write Day-1 deployment procedures for capacity/admission checks, canary rollout, config activation, version verification, smoke/integration checks, and rollback decision points.
- [ ] **MC-060-I03** — Write Day-2 procedures for health/SLO review, capacity, logs/diagnostics, certificate/key rotation, patching, config changes, backup/restore, quarantine, incident support, and evidence maintenance.
- [ ] **MC-060-I04** — For every step include expected output, success criterion, timeout, common failure branches, rollback/recovery action, required privilege, and escalation destination.
- [ ] **MC-060-I05** — Test runbooks by having an operator unfamiliar with implementation execute them in a clean/staging environment; record defects and update before production gate.
- [ ] **MC-060-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-060-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-060-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-060-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-060-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-060-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-060-A01** — Operators can execute Day-0/1/2 runbooks successfully with expected outputs, rollback branches, and escalation.
- [ ] **MC-060-A02** — Runbook validation is part of release/readiness evidence and stale procedures fail review.

### Required closure evidence

- [ ] **MC-060-E01** — Record traceability from `MC-060` and `C096` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-060-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-060-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-060-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-060-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-060` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-061 — Incident response plan

**Priority:** P0  
**Source checks:** `C097`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** no severity taxonomy, paging, escalation, containment, evidence collection, recovery, or post-incident process.

### Suggested repository artifacts

- [ ] `runbooks/INCIDENT_RESPONSE.md` — create or map to an equivalent traceable artifact.
- [ ] `incident/severity.yaml` — create or map to an equivalent traceable artifact.
- [ ] `incident/evidence-template.md` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-061-I01** — Define incident severities using impact/security/isolation/SLO criteria and concrete examples such as cross-tenant exposure, VMM escape suspicion, artifact compromise, widespread boot failure, site capacity loss, and telemetry-only degradation.
- [ ] **MC-061-I02** — Define paging routes, acknowledgement/escalation times, incident commander/ops/security roles, communication channels, and handoff to adjacent INV/PLN owners.
- [ ] **MC-061-I03** — Create containment procedures for deny-admission, quarantine/freeze, artifact/config rollback, credential/key revocation, host isolation, and evidence preservation.
- [ ] **MC-061-I04** — Define forensic/evidence collection that preserves audit chain, process/VMM metadata, release/config/artifact identities, relevant logs/traces without exposing secrets or destroying evidence.
- [ ] **MC-061-I05** — Include recovery validation, tenant/customer impact assessment, post-incident review, corrective-action ownership, and verification that fixes are added to tests/gates.
- [ ] **MC-061-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-061-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-061-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-061-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-061-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-061-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-061-A01** — Tabletop/technical drill validates paging, containment, evidence preservation, recovery, and post-incident actions.
- [ ] **MC-061-A02** — Security/isolation incidents have explicit host/workload quarantine and artifact/key revocation paths.

### Required closure evidence

- [ ] **MC-061-E01** — Record traceability from `MC-061` and `C097` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-061-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-061-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-061-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-061-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-061` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-062 — Recurring review controls

**Priority:** P1  
**Source checks:** `C098`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** no scheduled access/policy/dependency/configuration/architecture review process or evidence template.

### Suggested repository artifacts

- [ ] `governance/REVIEW_POLICY.md` — create or map to an equivalent traceable artifact.
- [ ] `governance/review-template.yaml` — create or map to an equivalent traceable artifact.
- [ ] `evidence/reviews/` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-062-I01** — Define scheduled reviews for privileged access/identities, authorization policy, artifact/dependency vulnerabilities, runtime/config drift, architecture/ADR validity, threat model, telemetry governance, SLOs, and exception registry.
- [ ] **MC-062-I02** — Assign frequency, owner, reviewers, required input evidence, decision outcomes, and overdue escalation for each review type.
- [ ] **MC-062-I03** — Use versioned review templates that capture scope, findings, risk, action owner, due date, evidence links, and explicit approval/rejection rather than informal meeting notes.
- [ ] **MC-062-I04** — Automate reminders and production-gate checks for overdue critical reviews or unresolved high-risk findings.
- [ ] **MC-062-I05** — Retain historical review evidence and trend recurring findings to identify systemic control failure or technical-debt accumulation.
- [ ] **MC-062-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-062-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-062-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-062-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-062-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-062-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-062-A01** — All required periodic reviews produce signed/versioned evidence on schedule and overdue critical reviews block the gate.
- [ ] **MC-062-A02** — Findings have accountable owners/dates and recurrence trends are reviewed.

### Required closure evidence

- [ ] **MC-062-E01** — Record traceability from `MC-062` and `C098` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-062-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-062-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-062-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-062-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-062` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-063 — Exception/waiver/debt registry

**Priority:** P1  
**Source checks:** `C099`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** no owners, rationale, risk acceptance, expiry, or review dates.

### Suggested repository artifacts

- [ ] `governance/EXCEPTIONS.yaml` — create or map to an equivalent traceable artifact.
- [ ] `governance/TECH_DEBT.md` — create or map to an equivalent traceable artifact.
- [ ] `tools/check_exception_expiry.py` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-063-I01** — Create a machine-readable registry for each exception/waiver/debt item with unique ID, affected C-checks/components, description, rationale, risk, compensating controls, owner, approver, creation date, expiry/review date, and remediation plan.
- [ ] **MC-063-I02** — Distinguish time-bounded production waivers from ordinary technical debt; prohibit indefinite P0 security/isolation waivers without explicit higher-level risk acceptance.
- [ ] **MC-063-I03** — Make CI/production gate validate expiry and required approvals and fail on missing/expired waivers referenced by evidence.
- [ ] **MC-063-I04** — Link waivers to affected tests/gates without converting FAIL/NOT_TESTED into PASS; reporting must preserve the underlying unmet control.
- [ ] **MC-063-I05** — Review the registry periodically, notify owners before expiry, and require closure evidence when an exception is remediated.
- [ ] **MC-063-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-063-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-063-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-063-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-063-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-063-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-063-A01** — Every active waiver has owner/approver/risk/expiry/compensating control and is machine-checked by CI/gate.
- [ ] **MC-063-A02** — Expired waivers fail the gate and closure preserves evidence that the underlying control is now satisfied.

### Required closure evidence

- [ ] **MC-063-E01** — Record traceability from `MC-063` and `C099` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-063-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-063-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-063-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-063-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-063` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

## MC-064 — Formal production exit gate

**Priority:** P0  
**Source checks:** `C100`  
**Primary discipline:** SRE / Release / Governance  
**Audit gap:** no local machine-readable gate that aggregates architecture, security, resilience, performance, observability, tests, rollback, and ownership; production readiness cannot be established from this archive alone.

### Suggested repository artifacts

- [ ] `release/PRODUCTION_EXIT_GATE.yaml` — create or map to an equivalent traceable artifact.
- [ ] `tools/production_gate.py` — create or map to an equivalent traceable artifact.
- [ ] `evidence/production-gate.json` — create or map to an equivalent traceable artifact.

### Engineering implementation checklist

- [ ] **MC-064-I01** — Define an explicit production-gate policy covering architecture/ownership, normative requirements/traceability, interfaces/schemas, implementation/config/supply chain, security/isolation, resilience, performance/capacity, observability, testing/evidence, operations/rollback, and outstanding waivers.
- [ ] **MC-064-I02** — Ingest only machine-verifiable evidence with hashes and freshness; require all mandatory P0 controls to be PASS or explicitly blocked from production, never inferred from prose or skipped tests.
- [ ] **MC-064-I03** — Validate version consistency among `VERSION`, package metadata, Firecracker/artifact manifest, compatibility matrix, schemas, config, SBOM/provenance, benchmark baseline, and evidence ledger.
- [ ] **MC-064-I04** — Produce deterministic GO/NO_GO/CONDITIONAL-style data with failed control IDs, evidence references, waiver IDs/expiry, approvers, and release identifier; do not allow a human-edited overall verdict to bypass failed inputs.
- [ ] **MC-064-I05** — Re-run the gate after the final immutable release artifact is built so certification applies to the exact bytes being deployed, then archive gate result/checksum/signature alongside the release.
- [ ] **MC-064-Q06** — Assign owner, approver, review cadence, and escalation path; operational controls without ownership are not considered closed.
- [ ] **MC-064-Q07** — Define prerequisites, exact action/decision points, expected outcomes, failure branches, rollback/containment, and evidence to capture.
- [ ] **MC-064-Q08** — Exercise the procedure in staging/tabletop/chaos as appropriate and measure whether operators can complete it within the stated objective.
- [ ] **MC-064-Q09** — Version the artifact with release/config/schema changes and make stale or missing critical operational artifacts fail the production gate.
- [ ] **MC-064-Q10** — Link procedures/policies to dashboards/alerts, incident response, traceability, exceptions, and adjacent-component handoffs.
- [ ] **MC-064-Q11** — Retain drill/review/approval evidence and unresolved actions with owners/due dates.

### Verification and acceptance checklist

- [ ] **MC-064-A01** — Production gate is deterministic, machine-readable, independently verifiable, and tied to exact immutable release bytes.
- [ ] **MC-064-A02** — No mandatory P0 gap, skipped test, stale evidence, or expired waiver can yield a production GO result.

### Required closure evidence

- [ ] **MC-064-E01** — Record traceability from `MC-064` and `C100` to the exact implementation symbols/files, tests, and evidence artifacts.
- [ ] **MC-064-E02** — Capture machine-readable test/review results with exact release candidate commit/version and all relevant dependency/artifact digests.
- [ ] **MC-064-E03** — Capture negative-path evidence proving the component fails safely when its key prerequisite is missing, malformed, unauthorized, incompatible, exhausted, or unavailable.
- [ ] **MC-064-E04** — Document residual risks, operational limitations, and any `NOT_APPLICABLE`/waiver decision with owner, approval, and expiry.
- [ ] **MC-064-E05** — Re-run the final production exit gate after packaging; archive the gate output and evidence hashes with the release.

**Closure rule:** `MC-064` is closed only when all applicable implementation, acceptance, and evidence items above are satisfied and no unresolved P0/P1 finding remains for this gap.

---

# Program-level sequencing and dependency guidance

## Recommended critical path

1. **Foundation/authority:** MC-007 through MC-013, MC-015 through MC-020, MC-054, MC-055, and MC-064 establish ownership, requirements, schemas, configuration/supply-chain controls, evidence, CI, and the production gate.
2. **Executable runtime:** MC-001 through MC-005 plus MC-021 through MC-025 and MC-037 establish a real Firecracker/KVM/device/admission/isolation implementation with bounded resources and trusted artifacts.
3. **Correct recovery:** MC-027 through MC-033 plus MC-059 establish health, idempotency, overload control, fencing/reconciliation, emergency isolation, fault injection, and reconstruction.
4. **Production telemetry/performance:** MC-034 through MC-046 establish measurable performance/capacity and safe observable operation.
5. **Certification breadth:** MC-047 through MC-053 establish independent contract/integration/compatibility/fuzz/concurrency/load/disaster evidence.
6. **Operational readiness:** MC-056 through MC-063 establish SLOs, rollout, security servicing, runbooks, incident response, reviews, and exception governance.
7. **Conditional/optional capabilities:** MC-004 snapshotting, MC-006 accelerated I/O, and MC-038 power/thermal can be gated by deployment profile, but must have an explicit `NOT_APPLICABLE` rationale if omitted from a particular certified profile.

## Repository-wide completion gate

- [ ] All 64 component IDs have an explicit final status; none are silently omitted.
- [ ] Every P0 component is `PASS` for the target production profile; no P0 `BLOCKED`, `FAIL`, or expired waiver remains.
- [ ] Every P1 component is `PASS` or has an approved time-bounded waiver with compensating controls and a tracked remediation release.
- [ ] Every P2 component is either `PASS` or has a documented profile-specific disposition (`NOT_APPLICABLE` or scheduled debt) with evidence.
- [ ] `tests/test_runtime.py` continues to pass in normal and `python -O` modes after all integrations are added.
- [ ] Framework-dependent `pk_core` checks execute with the approved pinned framework version; no production verdict is based on skipped tests.
- [ ] Independent contract/integration/security/resilience/performance test suites run against the exact packaged release bytes.
- [ ] SBOM, provenance, artifact digests, compatibility matrix, configuration revision, benchmark baseline, evidence ledger, and production gate all name the same release identity.
- [ ] Rollback/emergency-disable and reconstruction procedures are exercised successfully before production approval.
- [ ] Final machine-readable production gate can be independently verified and produces no unresolved mandatory control failure.

**Generated checklist items:** 1351 component-level checkboxes, plus the universal and program-level gates above.
