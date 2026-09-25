# INV-26 MicroVM Snapshotting v5.0.0
## Comprehensive Missing-Component Engineering Checklist

**Source:** post-hardening `AUDIT_REPORT.md` and `CHECKLIST.json` from `inv26_microvm_snapshotting_v5.0.0_hardened.zip`  
**Scope:** all **87 controls still missing**, **C086 partially satisfied**, and the concrete cross-cutting implementation gaps identified by the updated audit.  
**Purpose:** convert the audit into an implementation-ready production backlog with explicit evidence and acceptance criteria.

### Global completion rules

A checkbox should be marked complete only when the repository contains or references durable evidence. For code-enforced controls, prose alone is not completion. Every production-blocking item should satisfy all applicable conditions below:

- [ ] Requirement and threat/failure rationale are documented with a stable control ID.
- [ ] Machine-readable schema/config/policy exists where the control crosses a software boundary.
- [ ] Runtime enforcement exists and defaults to the safe behavior; insecure bypasses are unavailable in production profiles.
- [ ] Positive, negative, boundary, concurrency, and failure-path tests exist as applicable.
- [ ] CI runs the tests from a clean environment and treats unexpected skips as failure for production gates.
- [ ] Observability identifies the control outcome using stable reason/error codes without leaking secrets or cross-tenant data.
- [ ] Operations/runbook guidance exists for failures requiring human intervention.
- [ ] Machine-readable release evidence links the requirement to source revision, artifact digest, tests, and results.
- [ ] An accountable owner is assigned and any waiver has a risk statement, approver, remediation owner, and expiry.

### Current v5.0.0 baseline that should be preserved

Do not regress the controls already hardened in v5.0.0: full SHA-256 device fingerprints; strict device-ID validation; tenant/workload/environment restore binding; thread-safe in-process capture/restore mutation; read-only snapshot-map exposure; fresh 256-bit entropy generation per successful restore; fail-closed entropy-injector failure; non-secret entropy proof; finite/non-negative timing validation; signed-canonical security metadata support; dependency-independent domain tests; and schema/interface version 2.

---

# Architecture & Scope

## INV-26-C009 — MISSING
**Priority:** P2 - governance / optimization completion  
**Requirement:** Assign an accountable owner and escalation path for MicroVM snapshotting.

### Engineering checklist
- [ ] Create an ownership manifest naming the accountable service owner, engineering owner, security owner, SRE/on-call owner, and backup/delegate; use durable team aliases rather than only individual names.
- [ ] Define escalation tiers for data-isolation violations, snapshot corruption, KMS/signature failure, widespread restore latency regression, and hypervisor incompatibility, including paging destination and acknowledgement targets.
- [ ] Attach ownership to code review rules, release approval, vulnerability triage, production configuration changes, and emergency-disable authority; ensure no critical change can become ownerless.
- [ ] Publish machine-readable ownership metadata (for example CODEOWNERS plus `ops/ownership.yaml`) and validate it in CI against required roles.
- [ ] Test an escalation drill and retain evidence showing the primary path, fallback path, and after-hours path are reachable.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C009, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C009, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C009 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C009.

## INV-26-C010 — MISSING
**Priority:** P2 - governance / optimization completion  
**Requirement:** Approve an architecture decision record for MicroVM snapshotting, its technologies (VM snapshot/restore/cloning), and its function (Reduce effective startup latency).

### Engineering checklist
- [ ] Write an ADR that records why snapshot/restore is used to reduce startup latency, the selected runtime(s), supported CPU architectures, snapshot format ownership, entropy model, storage model, and tenant-boundary assumptions.
- [ ] Compare at least Firecracker, Cloud Hypervisor, and QEMU/KVM (or explicitly document why a candidate is excluded) across snapshot API stability, device-state coverage, dirty-page support, restore latency, security surface, and operational maturity.
- [ ] Record rejected alternatives such as cold boot, pre-booted pools, process checkpointing, and application-level warm state; document trade-offs and reversal criteria.
- [ ] Define irreversible or compatibility-sensitive decisions: snapshot format versioning, device model hashing, CPU feature masks, page-size assumptions, memory backing, and host-kernel dependencies.
- [ ] Obtain architecture/security/operations approval and assign review triggers for runtime upgrades, schema major changes, new hardware architecture, or cross-site restore support.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C010, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C010, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C010 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C010.

# Requirements & Semantics

## INV-26-C012 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define functional requirements for MicroVM snapshotting across cloud, datacenter, near-edge, and far-edge contexts where applicable.

### Engineering checklist
- [ ] Build an applicability matrix for cloud, datacenter, near-edge, and far-edge deployments with columns for supported runtime, CPU architecture, local storage, network dependence, KMS reachability, attestation capability, restore SLO, and operational ownership.
- [ ] For each tier, state whether capture, restore, deletion, replication, and emergency disable are supported, degraded, or prohibited.
- [ ] Define minimum hardware/kernel capabilities and maximum tolerated network/KMS outage per tier; include TPM/TEE availability where trust decisions depend on it.
- [ ] Specify data-residency and snapshot-placement constraints so a restore cannot silently move sensitive state into an unauthorized site or region.
- [ ] Add matrix-driven tests or policy fixtures proving unsupported combinations are rejected rather than best-effort executed.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C012, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C012, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C012 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C012.

## INV-26-C014 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for MicroVM snapshotting.

### Engineering checklist
- [ ] Define a closed outcome taxonomy: success, partial success, degraded success, retryable failure, terminal failure, policy rejection, integrity rejection, and operator-aborted operation.
- [ ] For capture and restore, specify externally visible side effects for every outcome: whether a blob may exist, whether metadata is committed, whether entropy was injected, whether the guest may run, and whether cleanup is required.
- [ ] Map each outcome to stable error codes, retryability, idempotency behavior, log severity, metric labels, and operator action; do not infer retryability from free-form exception text.
- [ ] Make restore fail closed when identity, authorization, fingerprint, signature, decryption, integrity, entropy injection, or compatibility checks fail.
- [ ] Add tests that force every outcome class and assert state cleanup, emitted code, audit event, and absence of unsafe guest execution.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C014, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C014, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C014 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C014.

## INV-26-C015 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define lifecycle states and legal state transitions managed or exposed by MicroVM snapshotting.

### Engineering checklist
- [ ] Define a normative lifecycle state machine covering at minimum ABSENT, CAPTURING, CAPTURED, VERIFYING, RESTORING, RESEEDING, READY, FAILED, QUARANTINED, DELETING, and DELETED.
- [ ] List legal transitions, transition guards, timeout behavior, persistent state written before/after each transition, and which transitions are recoverable after process or node restart.
- [ ] Define concurrency rules for capture-vs-capture, capture-vs-restore, restore-vs-restore, delete-vs-restore, and administrative quarantine; specify lock scope and distributed ownership if multiple controllers exist.
- [ ] Guarantee that READY is unreachable until all trust checks and entropy injection complete successfully.
- [ ] Generate state-transition tests from the model, including invalid transition rejection and crash-at-each-transition recovery tests.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C015, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C015, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C015 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C015.

## INV-26-C016 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define versioning and backward-compatibility requirements for MicroVM snapshotting.

### Engineering checklist
- [ ] Define semantic versioning rules separately for package version, capture schema (`PK_SNAPSHOT/*`), restore schema (`PK_SNAPSHOT_RESTORE/*`), storage manifest, and hypervisor snapshot format.
- [ ] Specify backward/forward compatibility windows, additive vs breaking changes, unknown-field behavior, downgrade policy, and minimum/maximum peer versions.
- [ ] Define migration or re-capture policy for old snapshots that cannot be safely interpreted after a runtime, kernel, CPU feature, or device-model change.
- [ ] Add compatibility negotiation to interfaces and reject unsupported major versions before mutating state.
- [ ] Create golden fixtures for N-1/N/N+1 behavior and release gates preventing undocumented compatibility breaks.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C016, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C016, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C016 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C016.

## INV-26-C017 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define capacity ceilings, quotas, and fairness semantics relevant to MicroVM snapshotting.

### Engineering checklist
- [ ] Define hard and soft quotas per tenant/workload/site for snapshot count, retained bytes, concurrent captures, concurrent restores, restore QPS, staging bytes, and KMS/signature requests.
- [ ] Define fairness policy (weighted fair queueing, token bucket, per-tenant semaphores, or equivalent) so one tenant cannot starve others.
- [ ] Specify admission behavior when quotas are exceeded, including deterministic error code, retry-after metadata, and non-bypassable privileged paths.
- [ ] Bound in-memory metadata, request queues, temporary files, open descriptors, mmap/page-cache pressure, and entropy/KMS concurrency.
- [ ] Load-test quota exhaustion and noisy-neighbor scenarios; prove fairness and that rejection occurs before expensive hypervisor or storage work.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C017, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C017, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C017 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C017.

## INV-26-C018 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define behavior when network connectivity is intermittent or absent.

### Engineering checklist
- [ ] Define which operations are permitted when control plane, identity service, KMS, storage, time source, or network connectivity is unavailable.
- [ ] Classify cached trust/configuration material by maximum staleness and expiry; security-critical expiry must fail closed rather than silently extending trust.
- [ ] Define offline restore rules, including whether locally cached encrypted snapshots may be restored and which authorizations/attestations must already be present.
- [ ] Implement reconnect reconciliation that detects conflicting metadata, duplicate operation IDs, expired leases, and stale policy before resuming work.
- [ ] Create partition/reconnect tests covering long outages, clock discontinuities, partially uploaded artifacts, and controller restarts.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C018, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C018, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C018 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C018.

## INV-26-C019 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define precedence rules when MicroVM snapshotting requirements conflict with security, residency, SLO, or cost constraints.

### Engineering checklist
- [ ] Publish an explicit precedence order for conflicting objectives; recommended baseline: isolation/security and legal residency > integrity/consistency > explicit operator safety controls > SLO/availability > cost/efficiency.
- [ ] Define conflict examples such as “restore SLO vs unavailable KMS,” “capacity pressure vs tenant isolation,” and “failover vs residency restriction,” with deterministic decisions.
- [ ] Encode precedence in policy/config rather than relying on operator interpretation; version and audit all policy changes.
- [ ] Emit decision-reason records containing the inputs, violated constraints, selected rule, and resulting action without exposing secrets.
- [ ] Test every precedence rule with paired contradictory inputs and prove the lower-priority objective cannot override the higher-priority control.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C019, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C019, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C019 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C019.

## INV-26-C020 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Maintain a requirements traceability matrix from each MicroVM snapshotting requirement to implementation and verification evidence.

### Engineering checklist
- [ ] Create a requirements traceability matrix covering C001-C100 plus repository-specific security invariants; each row must map requirement -> design/ADR -> code/config -> test -> runtime evidence -> owner -> status -> release.
- [ ] Use stable identifiers in source comments, tests, CI jobs, dashboards, runbooks, and acceptance evidence so traceability survives file renames.
- [ ] Automatically detect orphan requirements, tests without requirements, evidence without producer, and controls marked satisfied with missing artifacts.
- [ ] Hash or sign the release RTM and archive it with the exact source revision, dependency lock, build provenance, and gate output.
- [ ] Require CI to fail if a production-blocking control lacks current evidence for the candidate release.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C020, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C020, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C020 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C020.

# Interfaces & Integration

## INV-26-C021 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by MicroVM snapshotting.

### Engineering checklist
- [ ] Enumerate every trust and data boundary: public capture/restore API, hypervisor control channel, snapshot storage, KMS/key provider, identity/policy provider, provenance/signing provider, audit sink, metrics/log/trace exporters, and administrative control plane.
- [ ] For each boundary record direction, transport, schema, caller/callee identity, authorization capability, sensitivity classification, expected volume, timeout, retry semantics, and failure modes.
- [ ] Include local files, Unix sockets, device nodes, shared memory, environment variables, process execution, and kernel interfaces; do not inventory only network APIs.
- [ ] Document ownership and version authority for each interface and how incompatible peers are detected.
- [ ] Generate a boundary diagram and keep it synchronized with machine-readable interface metadata in CI.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C021, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C021, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C021 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C021.

## INV-26-C022 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Use versioned typed schemas for all externally visible MicroVM snapshotting contracts.

### Engineering checklist
- [ ] Create version-controlled machine-readable schemas for capture request/response, restore request/response, snapshot manifest, error envelope, audit event, configuration, and any storage/hypervisor adapter contract.
- [ ] Choose an encoding with explicit types and constraints (JSON Schema, Protobuf, WIT, or equivalent); constrain IDs, lengths, enums, numeric ranges, URI/path forms, and unknown fields.
- [ ] Define canonical serialization for any signed/hashed structure so semantically equal records cannot produce ambiguous signatures.
- [ ] Generate validators and typed bindings from schemas where practical; validate at every trust boundary before business logic runs.
- [ ] Add positive/negative schema fixtures, backward-compatibility checks, and CI detection for breaking changes without a major-version bump.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C022, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C022, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C022 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C022.

## INV-26-C023 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define authentication requirements at each MicroVM snapshotting boundary.

### Engineering checklist
- [ ] Define service/node/operator authentication for every boundary, using strong workload identity such as mTLS with SPIFFE/SVID, short-lived certificates, signed service tokens, or an equivalent approved mechanism.
- [ ] Bind credentials to intended audience, environment, site, and service; reject expired, not-yet-valid, wrong-audience, weak-algorithm, or untrusted-chain credentials.
- [ ] Define certificate/token rotation, revocation, clock-skew tolerance, bootstrap trust roots, and behavior when authentication infrastructure is unavailable.
- [ ] Authenticate local privileged channels as well as remote RPC; protect Unix sockets/files with owner/mode/namespace controls and peer credential checks where supported.
- [ ] Add impersonation, stolen-token, expired-cert, wrong-environment, replay, and trust-root-rotation tests.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C023, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C023, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C023 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C023.

## INV-26-C024 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define authorization and explicit capability requirements at each MicroVM snapshotting boundary.

### Engineering checklist
- [ ] Define explicit capabilities such as snapshot.capture, snapshot.restore, snapshot.delete, snapshot.inspect, snapshot.quarantine, snapshot.sign, and snapshot.admin; scope them by tenant/workload/environment/site.
- [ ] Use deny-by-default authorization evaluated before storage access, hypervisor mutation, key unwrap, or entropy injection.
- [ ] Separate operator break-glass authority from routine service authority; require stronger authentication, bounded lifetime, reason capture, and audit for break-glass actions.
- [ ] Prevent confused-deputy behavior by binding authenticated caller identity to request tenant/workload fields rather than trusting user-supplied identifiers.
- [ ] Run matrix tests proving privilege separation, cross-tenant denial, environment-boundary denial, and inability to escalate via optional fields or alternate API versions.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C024, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C024, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C024 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C024.

## INV-26-C025 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define timeout, cancellation, retry, idempotency, and backpressure semantics for MicroVM snapshotting.

### Engineering checklist
- [ ] Assign end-to-end and per-dependency deadlines to capture/restore; propagate cancellation to storage, KMS, and hypervisor calls and define cleanup after cancellation.
- [ ] Define exactly which operations are idempotent and require idempotency keys/generation numbers for mutating requests; persist enough state to deduplicate after restart.
- [ ] Retry only explicitly retryable failures with bounded exponential backoff plus jitter and a retry budget; prohibit retries for policy/integrity failures.
- [ ] Implement queue bounds/backpressure and return deterministic overload responses before resource exhaustion; expose queue depth and rejected-request metrics.
- [ ] Add tests for deadline expiry at each dependency, client disconnect, duplicate requests, retry storms, and cancellation during every lifecycle transition.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C025, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C025, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C025 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C025.

## INV-26-C026 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define structured failure codes and machine-readable error details for MicroVM snapshotting.

### Engineering checklist
- [ ] Create a stable error catalog with numeric/string code, HTTP/RPC mapping if applicable, retryability, security classification, operator action, and public-safe message.
- [ ] Include distinct codes for snapshot-not-found, duplicate snapshot, tenant/workload/environment mismatch, model mismatch, unsupported version, signature failure, decryption/KMS failure, entropy injection failure, storage corruption, timeout, overload, and quarantine.
- [ ] Keep sensitive internal details in protected diagnostics while returning a non-leaking public error envelope with correlation ID.
- [ ] Version the catalog and reserve deprecated codes rather than recycling them.
- [ ] Contract-test every code and prove exceptions cannot escape as unstable implementation-specific text across the public interface.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C026, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C026, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C026 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C026.

## INV-26-C027 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define compatibility behavior when peers use different supported versions.

### Engineering checklist
- [ ] Define a supported peer-version matrix for clients, storage manifests, hypervisor adapters, telemetry schemas, and signing/KMS providers.
- [ ] Implement explicit feature negotiation/capability discovery and major-version rejection before state mutation.
- [ ] Define read-old/write-new rules, snapshot re-capture/migration requirements, and behavior when an older node encounters unknown metadata.
- [ ] Prohibit silent downgrade of security features such as signature verification, encryption, tenant binding, or entropy reseeding.
- [ ] Run mixed-version rolling-upgrade and rollback tests with N-1/N/N+1 nodes and persisted snapshots.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C027, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C027, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C027 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C027.

## INV-26-C028 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Document payload, concurrency, queue, connection, or resource limits at MicroVM snapshotting interfaces.

### Engineering checklist
- [ ] Document request/response size limits, snapshot metadata size, device-count limits, snapshot memory/disk size bounds, maximum concurrent operations, queue depth, open connections, and per-request temporary storage.
- [ ] Enforce limits at the earliest parser/admission layer with overflow-safe arithmetic and explicit errors.
- [ ] Bound decompression ratios, manifest nesting, string lengths, collection cardinality, and any user-controlled path or URI.
- [ ] Expose resource saturation metrics and configurable limits with secure defaults and validated maximums.
- [ ] Fuzz and load-test just-below/at/above every limit and verify rejection does not allocate unbounded memory or block worker pools.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C028, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C028, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C028 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C028.

## INV-26-C029 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Provide reference examples and conformance fixtures for MicroVM snapshotting.

### Engineering checklist
- [ ] Publish minimal and complete capture/restore examples for each supported schema version, including valid security context and representative failure responses.
- [ ] Provide golden snapshot-manifest fixtures, canonical serialization vectors, device fingerprint vectors, signature/encryption vectors, and error-code examples.
- [ ] Provide intentionally invalid fixtures for cross-tenant restore, duplicate devices, malformed IDs, incompatible device models, stale signatures/tokens, and corrupted blobs.
- [ ] Make fixtures executable by conformance tests rather than prose-only documentation.
- [ ] Version fixtures with schemas and verify downstream adapters can consume them in CI.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C029, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C029, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C029 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C029.

## INV-26-C030 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Create automated integration tests proving MicroVM snapshotting interoperates with adjacent architectural layers.

### Engineering checklist
- [ ] Build automated integration suites against every supported hypervisor adapter plus snapshot storage, identity/authz, KMS/signing, telemetry/audit, and the adjacent INV-24/INV-25 contracts.
- [ ] Exercise a full capture -> persist -> verify -> restore -> entropy-inject -> ready path using real process boundaries or containers/VMs, not mocks only.
- [ ] Include negative integration cases: wrong tenant, wrong workload/environment, changed device model, corrupt/truncated blob, revoked signer, unavailable KMS, full storage, and hypervisor failure.
- [ ] Test crash/restart and idempotency with persistent metadata enabled; assert no duplicate or unauthorized restores occur.
- [ ] Run the suite in CI on supported OS/kernel/runtime combinations and attach machine-readable results to release evidence.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C030, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C030, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C030 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C030.

# Implementation & Configuration

## INV-26-C031 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Select and pin approved implementations, versions, or specifications for MicroVM snapshotting: VM snapshot/restore/cloning.

### Engineering checklist
- [ ] Create an approved implementation matrix pinning the snapshot domain package, hypervisor(s), guest/kernel requirements, storage provider, crypto library, KMS/signing provider, and schema/specification versions.
- [ ] Record exact version/range, source repository, checksum or digest, license, security-support status, and owner for every production dependency.
- [ ] Define upgrade criteria and compatibility qualification required before changing a pinned runtime, kernel, CPU model, device model, cryptographic primitive, or storage format.
- [ ] Generate the matrix from lock/manifests where possible and fail CI when production dependencies are unpinned or resolve differently than the approved set.
- [ ] Archive the resolved dependency graph/SBOM with each release and verify it against the approved matrix.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C031, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C031, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C031 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C031.

## INV-26-C032 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Separate immutable artifacts from mutable configuration and state for MicroVM snapshotting.

### Engineering checklist
- [ ] Define immutable artifacts (application package/container/binary, schemas, migrations, policy bundles) separately from mutable configuration, credentials, runtime leases, snapshot metadata, and blob state.
- [ ] Ensure build outputs are content-addressed/read-only at runtime and are not rewritten by configuration activation or snapshot operations.
- [ ] Place mutable data in explicit writable locations with ownership, permissions, retention, backup, and cleanup semantics; prohibit writes into the installed package tree.
- [ ] Document which state must survive process/node restart and which state is ephemeral; version persistent data formats independently.
- [ ] Test a read-only root/package filesystem and verify normal capture/restore operation still succeeds using only declared mutable paths.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C032, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C032, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C032 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C032.

## INV-26-C033 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define declarative configuration and secure defaults for MicroVM snapshotting.

### Engineering checklist
- [ ] Define a versioned declarative configuration schema covering runtime adapter, storage, KMS/signing, authn/authz, quotas, timeouts, concurrency, telemetry, feature gates, and site/environment policy.
- [ ] Provide secure defaults: deny cross-boundary restore, signature/integrity verification enabled, bounded concurrency/queues, no anonymous endpoints, and no plaintext secret fields.
- [ ] Document units and bounds for every numeric setting and avoid ambiguous values such as unitless durations or byte sizes.
- [ ] Support explicit environment/site overlays without hidden environment-variable precedence; define deterministic merge order.
- [ ] Publish a minimal production example and a maximally restrictive example validated by the same schema used at runtime.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C033, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C033, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C033 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C033.

## INV-26-C034 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Validate configuration before activation and fail closed on security-critical errors.

### Engineering checklist
- [ ] Validate configuration syntax, type, range, referential integrity, file/socket paths, endpoint schemes, trust roots, policy references, and adapter compatibility before activation.
- [ ] Perform semantic validation such as restore timeout > dependency timeout budget, queue limits consistent with worker limits, valid key/signature algorithms, and required telemetry/audit sinks present.
- [ ] Fail closed for invalid security-critical settings and retain the last-known-good configuration rather than partially applying a broken update.
- [ ] Return stable validation codes with field paths and redact secrets from errors/logs.
- [ ] Add property/negative tests for malformed, truncated, duplicate, unknown, extreme, and incompatible configuration values.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C034, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C034, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C034 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C034.

## INV-26-C035 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Support site- and environment-specific configuration without rebuilding immutable artifacts.

### Engineering checklist
- [ ] Support environment/site-specific values through layered configuration or policy bundles while keeping the executable artifact identical across deployments.
- [ ] Classify which settings may vary by site (storage endpoint, KMS key alias, capacity, locality policy) and which security invariants are globally fixed/non-overridable.
- [ ] Define deterministic precedence and conflict detection across base, environment, site, and emergency overlays; prevent accidental weakening by lower-trust layers.
- [ ] Validate overlays against the target runtime/device/architecture matrix before rollout.
- [ ] Prove with build hashes that dev/staging/prod or edge/cloud deployments use the same immutable artifact when only configuration differs.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C035, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C035, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C035 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C035.

## INV-26-C036 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Record configuration provenance, version, author, and activation time.

### Engineering checklist
- [ ] Persist configuration version, content digest, signer/author, source, approval reference, activation timestamp, target scope, and previous version for every activation.
- [ ] Use monotonic revision/generation identifiers so stale controllers cannot overwrite newer configuration.
- [ ] Emit an audit event linking each capture/restore to the effective configuration revision and policy version used for the decision.
- [ ] Protect provenance records against tampering using append-only storage, signatures, hash chaining, or an approved audit platform.
- [ ] Provide an operator query that reconstructs exactly which configuration governed any historical operation.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C036, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C036, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C036 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C036.

## INV-26-C037 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Apply atomic or transactional configuration updates where partial application is unsafe.

### Engineering checklist
- [ ] Implement stage -> validate -> prepare -> atomically activate configuration; never expose a mixture of old/new security policy during an update.
- [ ] Use compare-and-swap/generation preconditions or transactional storage to prevent concurrent writers and stale activations.
- [ ] For multi-process/node deployments, define rollout/barrier semantics and what compatibility is required while old and new revisions coexist.
- [ ] On activation failure, automatically retain/revert to last-known-good state and emit a high-severity audit/metric signal.
- [ ] Fault-inject crashes at every activation step and prove the process restarts in either wholly old or wholly new configuration, never a partial state.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C037, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C037, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C037 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C037.

## INV-26-C038 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define automatic and operator-driven rollback for failed MicroVM snapshotting changes.

### Engineering checklist
- [ ] Define automatic rollback triggers for failed health checks, error-rate regression, restore-latency regression, compatibility failure, security-policy failure, and crash loops.
- [ ] Define operator rollback procedure, required authorization, target revision selection, state/schema downgrade constraints, and emergency override controls.
- [ ] Ensure rollback restores compatible configuration and software together where schema or hypervisor format changes are coupled.
- [ ] Preserve audit history during rollback and never roll back trust revocations or critical security controls without explicit break-glass approval.
- [ ] Run rollback drills from canary and partial-fleet states and retain timing/recovery evidence.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C038, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C038, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C038 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C038.

## INV-26-C039 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Keep credentials and secret material out of ordinary MicroVM snapshotting configuration and diagnostics.

### Engineering checklist
- [ ] Prohibit raw credentials, private keys, wrapped/unwrapped DEKs, bearer tokens, entropy seeds, and snapshot plaintext from ordinary config files, CLI arguments, logs, traces, crash dumps, or metrics labels.
- [ ] Integrate a secret provider/KMS/agent interface that returns short-lived handles/material only to the component that requires it.
- [ ] Use locked/zeroizable memory or process isolation where practical for sensitive material; minimize lifetime and copies and explicitly clear temporary buffers/files.
- [ ] Redact structured diagnostics by schema/classification rather than regex-only best effort.
- [ ] Add secret-scanning, log-capture, crash-dump, and error-path tests proving representative secrets never appear in ordinary artifacts.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C039, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C039, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C039 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C039.

## INV-26-C040 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Provide a deterministic bootstrap path from an empty node/environment to healthy MicroVM snapshotting operation.

### Engineering checklist
- [ ] Provide a deterministic bootstrap procedure from an empty supported node: install verified artifact, create least-privilege identity, provision config/trust roots, initialize state/storage namespaces, register adapter, start service, and verify readiness.
- [ ] Pin all bootstrap inputs by version/digest and verify signatures before execution; avoid curl-pipe-shell or mutable “latest” dependencies.
- [ ] Make bootstrap idempotent and safe to re-run after partial failure; record each completed step and its provenance.
- [ ] Include prerequisite checks for kernel/KVM, CPU features, device access, filesystem/mount permissions, time synchronization, KMS/storage connectivity, and required ports/sockets.
- [ ] Automate a clean-node CI test that reaches healthy state and performs a signed/encrypted capture/restore smoke test without undocumented manual steps.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C040, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C040, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C040 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C040.

# Security, Trust & Isolation

## INV-26-C041 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Threat-model MicroVM snapshotting against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.

### Engineering checklist
- [ ] Create a repository-local threat model with assets (guest memory, credentials, RNG state, metadata, keys), actors, trust boundaries, entry points, and abuse cases for malicious tenants, compromised guests, malicious operators, compromised nodes, and supply-chain attackers.
- [ ] Model snapshot-specific threats: memory disclosure, cross-tenant rebinding, device-state confusion, stale/replayed snapshot, malicious/corrupt manifest, rollback to vulnerable guest state, clone RNG duplication, and snapshot exfiltration.
- [ ] Use a structured method such as STRIDE/LINDDUN/attack trees and map every high-risk threat to preventive/detective controls and tests.
- [ ] Explicitly cover local privilege escalation, hypervisor escape assumptions, side channels, speculative-execution exposure, DMA/device state, and temporary-file/memory remanence.
- [ ] Review the threat model on each major runtime/schema/crypto/topology change and fail the production gate for unmitigated unacceptable risks.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C041, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C041, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C041 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C041.

## INV-26-C042 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Apply least privilege to every identity and capability used by MicroVM snapshotting.

### Engineering checklist
- [ ] Inventory every service account, process UID/GID, Linux capability, device permission, socket permission, filesystem path, cloud IAM role, KMS permission, and storage permission used by snapshotting.
- [ ] Split capabilities so capture/restore workers do not automatically gain administrative delete, key-management, policy-edit, or cross-tenant listing privileges.
- [ ] Drop root and unnecessary Linux capabilities after setup; apply namespaces/seccomp/AppArmor/SELinux or equivalent sandboxing appropriate to the runtime.
- [ ] Scope cloud/KMS/storage permissions to exact tenant/site prefixes and operations; use short-lived identities instead of static credentials.
- [ ] Prove with negative tests that a compromised worker cannot read another tenant, enumerate unrestricted storage, rotate keys, alter policy, or access unrelated host devices/files.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C042, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C042, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C042 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C042.

## INV-26-C043 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Eliminate ambient filesystem, network, device, kernel, and secret authority wherever MicroVM snapshotting permits.

### Engineering checklist
- [ ] Enumerate ambient filesystem/network/device/kernel/secret authority currently inherited by the process and eliminate everything not required for capture/restore.
- [ ] Use explicit allowlists for outbound endpoints, filesystem roots, Unix sockets, device nodes, ioctls/syscalls, and subprocess execution; avoid inheriting broad host environment variables or credentials.
- [ ] Run the service with a private temporary directory, restricted umask, no home-directory dependency, no shell PATH dependency, and a minimal read-only filesystem view where feasible.
- [ ] Broker privileged hypervisor/KVM operations through a narrowly scoped adapter/helper rather than granting the entire service host-level authority.
- [ ] Use sandbox tests/policy-denial tests to prove operation fails safely when undeclared authority is unavailable.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C043, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C043, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C043 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C043.

## INV-26-C044 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.

### Engineering checklist
- [ ] Authenticate control-plane actors, worker nodes, hypervisor endpoints, storage providers, KMS/signing providers, and artifact sources before trusting data or commands.
- [ ] Bind node/provider identity to expected environment/site and approved role; reject valid credentials presented from the wrong trust domain.
- [ ] Verify bootstrap trust anchors out of band and define rotation/revocation without requiring a trust-breaking “accept any” maintenance mode.
- [ ] Where node integrity matters, bind identity to hardware-backed or measured attestation evidence and record freshness/nonce semantics.
- [ ] Test spoofed endpoints, cloned node identities, revoked trust anchors, stale attestation, DNS/endpoint substitution, and certificate chain confusion.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C044, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C044, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C044 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C044.

## INV-26-C045 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by MicroVM snapshotting.

### Engineering checklist
- [ ] Make signature/digest/provenance verification mandatory for executable packages, policy bundles, schemas/migrations, hypervisor/helper binaries, and snapshot manifests before use.
- [ ] Define approved algorithms/key types, signer identities, key usage, threshold/multi-party requirements where needed, and explicit rejection of weak/unknown algorithms.
- [ ] Consume verifiable build provenance/SBOM and enforce allowlisted source/build identities rather than validating only a checksum supplied alongside the artifact.
- [ ] Pin or policy-control approved versions and block known-revoked/vulnerable releases.
- [ ] Add tamper, wrong-signer, stale-version, missing-provenance, substitution, and downgrade tests; the default path must fail closed.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C045, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C045, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C045 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C045.

## INV-26-C047 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Encrypt sensitive MicroVM snapshotting data in transit and at rest with managed key rotation.

### Engineering checklist
- [ ] Classify snapshot memory/device state and related metadata as sensitive; encrypt blobs at rest with authenticated encryption and encrypt all network/control traffic in transit.
- [ ] Use envelope encryption with a unique data-encryption key per snapshot or security domain, wrapped by a managed KMS key; bind tenant/workload/environment/snapshot identity and schema version as authenticated associated data.
- [ ] Define key IDs/versions, rotation schedule, rewrap/re-encrypt strategy, revocation, backup, and behavior for deleted/disabled keys.
- [ ] Authenticate ciphertext before exposing it to the hypervisor; reject truncated, reordered, substituted, or wrong-context blobs.
- [ ] Test wrong-key, tampered-tag, ciphertext swap, rotation, revoked-key, TLS downgrade, and plaintext-at-rest scans.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C047, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C047, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C047 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C047.

## INV-26-C048 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.

### Engineering checklist
- [ ] Define explicit dependency-outage policy for identity, authorization/policy, attestation, KMS, signing/provenance, trusted time, storage, and audit services.
- [ ] Classify each dependency as fail-closed, locally cacheable for a bounded TTL, or degradable; security-critical dependencies should not silently become optional.
- [ ] Define maximum cache age, revocation lag, clock-skew handling, and what operations remain allowed under each outage mode.
- [ ] Expose degraded/readiness state so schedulers/operators know why capture/restore is refused or restricted.
- [ ] Inject each outage independently and in combinations, asserting no cross-tenant restore, unsigned restore, unencrypted write, or un-audited privileged action becomes possible.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C048, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C048, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C048 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C048.

## INV-26-C049 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Emit tamper-evident audit events for security-sensitive MicroVM snapshotting operations.

### Engineering checklist
- [ ] Emit security audit events for capture, restore, delete, quarantine, authn/authz decision, signature/integrity verification, key unwrap, policy/config activation, break-glass use, and failed cross-boundary attempts.
- [ ] Include timestamp, monotonic sequence/generation, operation ID, actor identity, node/site, tenant/workload identifiers or privacy-safe references, decision/result code, config/policy version, and artifact digests.
- [ ] Make records tamper-evident/append-only using signed batches, hash chaining, WORM storage, or a trusted audit service; protect against local log deletion by a compromised worker.
- [ ] Define retention, access controls, privacy minimization, export reliability, and behavior when the audit sink is unavailable.
- [ ] Test ordering, dropped-event detection, chain verification, redaction, clock anomalies, and correlation across retries/restarts.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C049, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C049, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C049 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C049.

## INV-26-C050 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.

### Engineering checklist
- [ ] Build adversarial tests directly from the threat model for privilege escalation, parser/command injection, path traversal, symlink/hardlink attacks, malicious manifests, signature confusion, and tenant-identifier spoofing.
- [ ] Test replay of restore requests/tokens, stale snapshots, duplicated operation IDs, reordered events, and rollback to older signed-but-revoked artifacts.
- [ ] Exercise hypervisor/device escape assumptions with malformed device models and hostile guest behavior within a controlled test environment.
- [ ] Run resource-exhaustion attacks covering oversized manifests, decompression bombs, connection floods, restore storms, queue saturation, storage exhaustion, and KMS throttling.
- [ ] Include side-channel-oriented checks where relevant (cross-tenant cache/state leakage, residual temporary files/pages, identifier leakage) and track unresolved risk with explicit acceptance.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C050, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C050, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C050 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C050.

# Resilience & Failure Handling

## INV-26-C051 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting MicroVM snapshotting.

### Engineering checklist
- [ ] Create a failure-mode and effects matrix spanning component/process crash, guest/VM failure, hypervisor failure, host reboot, disk full/corruption, node loss, site loss, network partition, DNS failure, storage outage, KMS outage, identity/policy outage, audit outage, and control-plane failure.
- [ ] For each failure record detection signal, blast radius, safe state, automatic action, retry/failover eligibility, recovery objective, data-loss risk, operator action, and evidence source.
- [ ] Include partial operations such as memory blob written but manifest absent, manifest committed but signature absent, restore started but entropy not injected, and delete partially completed.
- [ ] Define compound failures and dependency-ordering hazards rather than assuming only one dependency fails at a time.
- [ ] Link every high-severity mode to a fault-injection test and a runbook procedure.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C051, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C051, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C051 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C051.

## INV-26-C052 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define automated health and stall detection thresholds for MicroVM snapshotting.

### Engineering checklist
- [ ] Define liveness/readiness/stall criteria for API workers, hypervisor adapter, storage, KMS/signing, audit exporter, queues, and persistent state.
- [ ] Use operation-specific stall timers for capture, upload, verification, restore, and entropy injection; account for snapshot size and known dependency latency rather than one universal timeout.
- [ ] Publish thresholds for consecutive failures, saturation, deadlocks/no-progress, queue age, and dependency health, with hysteresis to avoid flapping.
- [ ] Ensure readiness is false when mandatory security dependencies are unavailable even if the process is alive.
- [ ] Create synthetic hang and slow-dependency tests that prove detection, alerting, cancellation, quarantine, and recovery behavior.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C052, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C052, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C052 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C052.

## INV-26-C053 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Implement bounded retry with backoff and jitter only where operations are safe to retry.

### Engineering checklist
- [ ] Classify every dependency operation as non-retryable, safely retryable, or conditionally retryable with idempotency key/generation precondition.
- [ ] Implement bounded exponential backoff with jitter, max attempts/max elapsed time, and per-operation retry budgets; propagate the original deadline.
- [ ] Never retry policy denial, signature/integrity failure, tenant mismatch, incompatible schema/device model, or permanent authorization failures.
- [ ] Persist idempotency/deduplication state when retries can outlive a process restart, and avoid duplicate hypervisor restore or duplicate blob commit.
- [ ] Test transient faults, permanent faults, retry storms, synchronized clients, deadline exhaustion, and duplicate side-effect prevention.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C053, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C053, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C053 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C053.

## INV-26-C054 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Implement admission control, load shedding, or circuit breaking to prevent MicroVM snapshotting failure cascades.

### Engineering checklist
- [ ] Implement admission control before expensive work using global and per-tenant concurrency limits, token buckets/rate limits, queue depth/age limits, and storage/KMS pressure signals.
- [ ] Define load-shedding priority so safety/control operations such as quarantine/delete/revocation are not starved by bulk capture/restore traffic.
- [ ] Add circuit breakers for unhealthy dependencies with half-open probing and bounded recovery, while preserving fail-closed security checks.
- [ ] Expose saturation and rejection reasons through metrics and stable errors with optional retry-after guidance.
- [ ] Run overload tests proving latency remains bounded, memory/FD/thread counts do not grow without limit, and one tenant cannot cause fleet-wide collapse.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C054, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C054, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C054 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C054.

## INV-26-C055 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define failover behavior without violating isolation, residency, or consistency requirements.

### Engineering checklist
- [ ] Define which state may fail over across process, node, availability zone/site, or region and which state must remain locality/residency bound.
- [ ] Use leases/fencing tokens/consensus-backed ownership so only one controller can commit a snapshot operation after failover.
- [ ] Carry tenant, workload, environment, site, key, and compatibility constraints into failover selection; never trade isolation/residency for availability.
- [ ] Define behavior for in-flight operations at failover: resume, replay, abort+cleanup, or require operator reconciliation.
- [ ] Test node/site failover during each lifecycle phase and prove no duplicate restore, stale write, unauthorized relocation, or lost audit trail.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C055, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C055, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C055 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C055.

## INV-26-C056 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Provide degraded operation when noncritical dependencies are unavailable.

### Engineering checklist
- [ ] Classify dependencies as critical vs noncritical and define supported degraded modes, such as capture disabled while restore of already verified local snapshots remains available only when trust requirements are met.
- [ ] Define exactly which features are disabled, which limits tighten, and which SLOs no longer apply in degraded state.
- [ ] Expose a machine-readable degraded reason/capability set so callers do not assume full functionality.
- [ ] Prevent degraded mode from bypassing signature verification, authorization, entropy reseeding, encryption, or tenant/device binding.
- [ ] Test entry/exit from degraded mode, stale-cache boundaries, dependency recovery, and operator visibility.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C056, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C056, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C056 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C056.

## INV-26-C057 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define crash-consistency, restart, resume, or replay semantics for mutable MicroVM snapshotting state.

### Engineering checklist
- [ ] Define durable state required to reconstruct operations after crash: operation ID, lifecycle state, snapshot manifest digest, blob commit status, key/signature references, leases/fencing tokens, and cleanup obligations.
- [ ] Use write-ahead/transactional state updates so externally visible commits have a recoverable corresponding record; fsync/durability semantics must be explicit.
- [ ] Define replay rules for each lifecycle state and make recovery idempotent; incomplete snapshots must be quarantined or garbage-collected, never treated as valid.
- [ ] Handle host reboot, power loss, torn writes, database rollback, and partially durable filesystem updates.
- [ ] Run crash-at-every-step tests with restart and compare recovered state against an oracle for safety and leak-free cleanup.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C057, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C057, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C057 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C057.

## INV-26-C058 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.

### Engineering checklist
- [ ] Introduce authoritative operation ownership using leases plus monotonic fencing tokens or an equivalent consensus/transactional mechanism.
- [ ] Bind every mutating storage/hypervisor commit to the current generation so stale controllers cannot complete work after losing ownership.
- [ ] Deduplicate client retries and scheduler duplicates using durable operation IDs and request hashes; reject conflicting reuse of an ID.
- [ ] Detect clock/lease anomalies and prefer fencing-token correctness over wall-clock assumptions.
- [ ] Partition-test two active controllers and prove only one can commit capture/restore/delete outcomes.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C058, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C058, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C058 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C058.

## INV-26-C059 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Provide quarantine, freeze, disable, or isolation controls for unsafe MicroVM snapshotting behavior.

### Engineering checklist
- [ ] Implement quarantine/freeze/disable controls at snapshot, tenant/workload, node, adapter, site, and global component scope as appropriate.
- [ ] Ensure quarantine blocks restore before decryption/hypervisor mutation and can be triggered automatically by integrity, security, or compatibility failures.
- [ ] Require explicit privileged authorization and reason for release from quarantine; record immutable audit evidence for both quarantine and release.
- [ ] Provide emergency disable that stops new unsafe work while preserving evidence and allowing safe cleanup/control-plane access.
- [ ] Test controls during in-flight operations, restart, stale-controller scenarios, and degraded dependencies.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C059, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C059, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C059 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C059.

## INV-26-C060 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Run fault-injection tests proving MicroVM snapshotting recovery against documented objectives.

### Engineering checklist
- [ ] Build a deterministic fault-injection harness for process kill, host reboot simulation, network delay/loss/partition, storage errors/corruption, KMS throttling/outage, identity/policy failure, clock skew, disk full, and hypervisor hangs.
- [ ] Inject faults at named lifecycle checkpoints so every transition has coverage rather than relying only on random chaos.
- [ ] Define recovery objectives and invariants for each test: no cross-tenant restore, no READY without entropy, no unsigned/corrupt restore, bounded resource leakage, and recoverable durable state.
- [ ] Run both single-fault and selected compound-fault scenarios repeatedly to expose races.
- [ ] Archive machine-readable fault scenario, seed, build/config digests, timeline, observed recovery, and pass/fail evidence.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C060, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C060, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C060 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C060.

# Performance & Resource Efficiency

## INV-26-C061 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Establish reproducible baselines for MicroVM snapshotting latency, throughput, startup, CPU, memory, storage, network, and power overhead.

### Engineering checklist
- [ ] Create a reproducible benchmark harness measuring capture latency, restore latency, end-to-end time-to-ready, throughput, CPU, RSS/private memory, page faults, storage bytes/IOPS, network bytes, KMS/signing overhead, and host power where relevant.
- [ ] Separate pure domain-model timing from real hypervisor/storage/KMS timing; the current `elapsed_ms` fixture must never be treated as a performance measurement.
- [ ] Pin hardware, CPU governor, kernel, hypervisor, guest image, memory size, device model, storage medium, dataset, concurrency, and warm/cold cache state in benchmark metadata.
- [ ] Run enough repetitions for statistically stable percentiles and report confidence/sample size plus outliers.
- [ ] Version benchmark scenarios and archive raw results so regressions can be reproduced.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C061, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C061, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C061 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C061.

## INV-26-C062 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define p50, p95, p99, and worst-case performance thresholds for MicroVM snapshotting.

### Engineering checklist
- [ ] Define p50/p95/p99 and maximum or bounded worst-case objectives for capture, restore, time-to-ready, storage/KMS substeps, and queue wait at representative snapshot sizes.
- [ ] Clarify whether the existing 10 ms objective measures only hypervisor restore, restore+entropy, or full request-to-ready path; use one canonical SLI definition.
- [ ] Define separate thresholds by hardware/runtime tier if necessary rather than averaging incompatible environments.
- [ ] Assign error budgets and sample eligibility rules; exclude only explicitly documented maintenance/test traffic.
- [ ] Add automated percentile evaluation that fails release/performance gates when thresholds or confidence requirements are not met.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C062, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C062, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C062 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C062.

## INV-26-C063 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Measure MicroVM snapshotting under steady load, burst load, overload, scale-out, scale-in, and recovery.

### Engineering checklist
- [ ] Benchmark steady-state load, short bursts, prolonged overload, scale-out, scale-in, dependency recovery, and mixed capture/restore workloads.
- [ ] Vary snapshot size, tenant count, device count, concurrency, storage latency, KMS latency, and cache state.
- [ ] Measure queueing delay, rejection rate, tail amplification, retry volume, and recovery time after overload stops.
- [ ] Validate no hysteresis path leaves the service permanently throttled or causes retry oscillation after dependencies recover.
- [ ] Publish saturation curves showing throughput/latency/resource behavior through the knee and beyond safe capacity.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C063, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C063, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C063 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C063.

## INV-26-C064 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Measure per-workload and per-tenant overhead introduced by MicroVM snapshotting.

### Engineering checklist
- [ ] Attribute CPU, memory, storage, network, KMS/signing calls, queue occupancy, and operation counts to tenant/workload using privacy-safe stable identifiers.
- [ ] Measure marginal overhead at representative snapshot sizes and concurrency; distinguish shared fixed cost from directly attributable cost.
- [ ] Validate attribution sums against node/service totals within a defined tolerance and account for unattributable system overhead.
- [ ] Use accounting to detect noisy-neighbor behavior and enforce quotas/fairness without exposing one tenant’s identifiers to another.
- [ ] Include overhead accounting in capacity planning and performance regression reports.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C064, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C064, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C064 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C064.

## INV-26-C065 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in MicroVM snapshotting.

### Engineering checklist
- [ ] Profile the complete path for serialization/deserialization, buffer copies, memory mapping, compression/encryption copies, context switches, syscall rate, network/storage hops, and duplicate blob/state generation.
- [ ] Use flamegraphs/profilers/eBPF or platform-appropriate tracing on representative workloads and retain profiles as optimization evidence.
- [ ] Identify unnecessary Python/object copies in metadata handling separately from hypervisor memory-image transfer costs.
- [ ] Quantify each candidate bottleneck before optimization and verify changes do not weaken canonicalization, encryption, integrity, or isolation.
- [ ] Add regression tests/benchmarks for eliminated hot paths where practical.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C065, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C065, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C065 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C065.

## INV-26-C066 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.

### Engineering checklist
- [ ] Evaluate direct I/O/mmap/zero-copy transfer, locality-aware placement, page sharing only within allowed isolation boundaries, batching, prefetching, and safe caching where supported.
- [ ] Use content-addressed deduplication only when confidentiality/tenant-isolation analysis permits; do not introduce cross-tenant side channels for storage savings.
- [ ] Keep cached authorization/key material bounded and freshness-aware; never optimize by skipping mandatory verification or reseeding.
- [ ] Benchmark optimized vs baseline implementations across tail latency, CPU, memory, storage amplification, and failure recovery.
- [ ] Document why rejected optimizations are unsafe or non-beneficial so they are not repeatedly reintroduced.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C066, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C066, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C066 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C066.

## INV-26-C067 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.

### Engineering checklist
- [ ] Define hard ceilings for process RSS, metadata entries, temporary bytes, open files/sockets, threads/tasks, queue depth, concurrent captures/restores, per-operation buffers, and adapter fan-out.
- [ ] Enforce limits before allocation and use streaming/bounded parsing for potentially large manifests/blobs.
- [ ] Implement cleanup for timeout/cancel/crash paths so temporary files, mmap regions, leases, and buffers are released.
- [ ] Expose current/limit/high-water-mark metrics and alerts for approaching saturation.
- [ ] Soak and adversarially load the service to prove memory/FD/task counts remain bounded and return to baseline after work drains.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C067, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C067, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C067 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C067.

## INV-26-C068 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Measure power and thermal impact on constrained edge nodes where relevant.

### Engineering checklist
- [ ] For near-/far-edge targets, measure idle and active power, peak/steady thermal behavior, CPU frequency throttling, and restore performance under constrained power modes.
- [ ] Test representative hardware rather than extrapolating cloud/server measurements to edge devices.
- [ ] Quantify energy per capture/restore and the effect of compression/encryption, storage medium, concurrency, and pre-warming.
- [ ] Define thermal/power guardrails that reduce concurrency or reject noncritical work before instability.
- [ ] Archive hardware/firmware/environment metadata with power results and integrate critical regressions into capacity/release decisions.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C068, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C068, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C068 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C068.

## INV-26-C069 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define capacity models and saturation signals that predict when MicroVM snapshotting needs more resources.

### Engineering checklist
- [ ] Build a capacity model relating snapshot size, capture/restore concurrency, storage throughput/IOPS, KMS/signing QPS, CPU, memory bandwidth, queue depth, and target tail latency.
- [ ] Define leading saturation signals such as queue age, worker occupancy, storage latency, KMS throttle rate, page-fault rate, and memory pressure.
- [ ] Calibrate the model against measured load tests and document error bounds/assumptions.
- [ ] Expose recommended headroom and trigger points for scale-out or admission tightening.
- [ ] Revalidate the model after hardware, runtime, storage, crypto, or major implementation changes.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C069, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C069, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C069 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C069.

## INV-26-C070 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Block releases that regress approved MicroVM snapshotting startup, density, throughput, or tail-latency thresholds.

### Engineering checklist
- [ ] Define release performance baselines and allowed regression budgets for startup/time-to-ready, p95/p99 restore, throughput, density, CPU, memory, and storage amplification.
- [ ] Run controlled comparison against an approved baseline build using identical benchmark manifests and environment fingerprints.
- [ ] Use statistically defensible thresholds to avoid both noisy false failures and acceptance of material tail regressions.
- [ ] Require an explicit reviewed waiver with owner/expiry for any accepted regression and link it to the debt register.
- [ ] Publish machine-readable performance gate results with the release evidence bundle.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C070, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C070, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C070 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C070.

# Observability & Explainability

## INV-26-C071 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Expose MicroVM snapshotting health, readiness, version, configuration, dependency status, and active capability set.

### Engineering checklist
- [ ] Expose a health/readiness/status interface reporting component version, schema versions, configuration revision, supported capabilities, hypervisor adapter/version, persistence status, and mandatory dependency status.
- [ ] Separate liveness from readiness; do not report ready if authorization, required trust/KMS/storage, durable state, or hypervisor access is unavailable.
- [ ] Provide only non-sensitive diagnostics to unprivileged callers; protect detailed dependency/config views with authorization.
- [ ] Include build/source provenance identifiers so an operator can correlate the running instance with release evidence.
- [ ] Contract-test state transitions of health/readiness during startup, dependency outage, degraded mode, quarantine, and shutdown.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C071, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C071, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C071 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C071.

## INV-26-C072 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.

### Engineering checklist
- [ ] Implement structured metrics for request/capture/restore rate, success/error by stable code, latency histograms, queue depth/age, rejections, retries, dependency latency/errors, resource use, and security refusals.
- [ ] Use bounded-cardinality labels; never place snapshot IDs, raw tenant/workload IDs, tokens, paths, or secrets in unbounded metric labels.
- [ ] Define histogram buckets appropriate to sub-10ms and larger end-to-end latency ranges and ensure units are consistent.
- [ ] Expose process/runtime metrics needed to diagnose saturation, including CPU/RSS/FD/task counts and persistent-state/storage health.
- [ ] Add metric-contract tests validating names, units, label sets, reset behavior, and emission on representative success/failure paths.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C072, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C072, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C072 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C072.

## INV-26-C073 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.

### Engineering checklist
- [ ] Emit structured logs with timestamp, severity, component/build, operation ID, node/site, privacy-safe tenant/workload reference, lifecycle state, decision/error code, and relevant artifact/config digests.
- [ ] Use a schema/version for logs and central redaction helpers so secrets, raw entropy, key material, snapshot plaintext, and sensitive paths cannot leak.
- [ ] Distinguish operator-actionable errors from expected policy rejections and avoid stack traces at normal info levels for untrusted input.
- [ ] Ensure retry attempts preserve one correlation/operation lineage while recording attempt number and dependency.
- [ ] Test log schema, redaction, correlation, volume under attacks, and behavior when the logging sink is blocked.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C073, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C073, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C073 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C073.

## INV-26-C074 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Propagate trace context across all relevant MicroVM snapshotting boundaries.

### Engineering checklist
- [ ] Propagate W3C Trace Context or another approved standard across API, storage, KMS/signing, hypervisor adapter, audit, and control-plane boundaries where supported.
- [ ] Create child spans for validation/authz, manifest lookup, integrity/decryption, hypervisor load, entropy injection, and readiness transition.
- [ ] Prevent tenant-controlled trace identifiers from becoming a trust or log-injection vector; validate formats and regenerate invalid context.
- [ ] Apply sampling rules that preserve security/error traces while controlling cost and protecting sensitive attributes.
- [ ] Integration-test trace continuity across retries, async work, process boundaries, and dependency errors.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C074, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C074, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C074 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C074.

## INV-26-C075 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.

### Engineering checklist
- [ ] Design a privileged diagnostics channel capable of high-cardinality details such as snapshot/operation IDs, exact dependency endpoint, manifest digest, and state-transition history without placing them in global metrics.
- [ ] Authorize diagnostics access and separate tenant/operator views; redact or tokenize sensitive identifiers based on role.
- [ ] Apply retention and query-rate limits to diagnostic stores to reduce privacy and DoS risk.
- [ ] Ensure debug mode cannot emit raw memory, entropy, keys, auth tokens, or decrypted snapshot contents.
- [ ] Run data-leakage tests against logs/traces/diagnostic APIs using seeded canary secrets and cross-tenant access attempts.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C075, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C075, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C075 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C075.

## INV-26-C076 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Record the reason for every automated decision made by MicroVM snapshotting.

### Engineering checklist
- [ ] For every automated allow/deny/degrade/quarantine/retry/failover decision, record a stable reason code plus the policy/rule and relevant non-secret inputs.
- [ ] Capture which tenant/workload/environment/device/version/trust constraints were evaluated without recording secret material.
- [ ] Link reason records to operation ID, config/policy revision, runtime capability set, and audit event.
- [ ] Make the reason deterministic enough that the same recorded inputs can be replayed in an offline decision test.
- [ ] Add coverage assertions so new decision branches cannot ship without a reason code and explainability mapping.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C076, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C076, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C076 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C076.

## INV-26-C077 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.

### Engineering checklist
- [ ] Provide an operator explain view or command that reconstructs the operation timeline, effective configuration/policy, trust decisions, device compatibility, dependency health, retries, and final result.
- [ ] Present why an operation was rejected or degraded, not merely the final exception; include links/IDs to relevant runbook and audit evidence.
- [ ] Apply role-based redaction and tenant scoping so the explain surface cannot be used to enumerate other tenants or secret topology.
- [ ] Make the view available for historical completed/failed operations using durable event/state records.
- [ ] Test deterministic reconstruction after restart and across multi-step failures.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C077, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C077, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C077 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C077.

## INV-26-C078 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Correlate MicroVM snapshotting events with application release lineage and the live infrastructure graph.

### Engineering checklist
- [ ] Attach release/build digest, hypervisor/runtime version, host image/kernel version, configuration revision, policy revision, and infrastructure/site/node identity to operational events.
- [ ] Integrate with the authoritative deployment/infrastructure graph so incidents can answer “which restores were affected by release X/runtime Y/node group Z?”.
- [ ] Preserve lineage when an operation fails over or resumes on another node.
- [ ] Use immutable/versioned deployment identifiers rather than mutable labels such as “current” or “prod”.
- [ ] Create incident-reconstruction tests/queries proving affected operations can be selected by release and topology attributes.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C078, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C078, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C078 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C078.

## INV-26-C079 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define telemetry retention, sampling, privacy, and export policy.

### Engineering checklist
- [ ] Define retention for metrics, logs, traces, audit events, operation history, and benchmark/gate evidence based on security, debugging, legal, and cost requirements.
- [ ] Define sampling independently per signal; never sample mandatory security audit events in a way that breaks accountability.
- [ ] Classify fields for privacy/secret sensitivity and define tokenization/redaction/access controls/export destinations.
- [ ] Define backpressure/spooling/drop policy when collectors are unavailable, including which signals may be dropped and which must block/fail closed.
- [ ] Validate retention deletion, access controls, export encryption/authentication, and tenant isolation in telemetry stores.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C079, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C079, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C079 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C079.

## INV-26-C080 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.

### Engineering checklist
- [ ] Create dashboards for throughput, restore/capture latency percentiles, queue/saturation, dependency health, tenant-isolation rejections, integrity/signature/KMS failures, entropy failures, resource use, and version/config distribution.
- [ ] Create distinct alerts for overload, dependency outage, policy/security rejection spikes, corruption/integrity failure, software crash/exception regression, latency regression, and audit/telemetry pipeline failure.
- [ ] Base alerts on actionable symptoms/SLO burn where possible and include runbook links, owner, severity, and deduplication grouping.
- [ ] Test alert routing and thresholds using synthetic signals/fault injection; guard against cardinality or alert storms during attacks.
- [ ] Review dashboards/alerts during release and incident retrospectives and track stale/unowned panels as debt.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C080, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C080, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C080 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C080.

# Testing & Certification

## INV-26-C082 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Create contract tests for every public MicroVM snapshotting interface.

### Engineering checklist
- [ ] Create black-box contract tests for every public capture/restore/status/admin interface and every schema version supported for production.
- [ ] Validate required/optional fields, constraints, canonical serialization, success envelopes, all stable error codes, authentication/authorization requirements, deadlines, idempotency, and compatibility negotiation.
- [ ] Treat implementation internals as opaque: tests should run against a packaged service/adapter and generated fixtures so alternate implementations can be certified.
- [ ] Include malformed/unknown fields, boundary sizes, duplicate fields/IDs, unsupported versions, and security-context mismatch cases.
- [ ] Publish machine-readable contract results and block release when any supported contract drifts without an approved version change.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C082, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C082, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C082 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C082.

## INV-26-C083 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Create integration tests with every supported adjacent layer and execution tier.

### Engineering checklist
- [ ] Create integration suites with every supported hypervisor/runtime, snapshot storage implementation, identity/policy provider, KMS/signing provider, audit/telemetry sink, and adjacent architectural layer.
- [ ] Exercise real capture/restore artifacts across process/service boundaries and verify tenant/workload/environment/device binding survives serialization and persistence.
- [ ] Cover success, dependency outage, corruption, timeout, cancellation, retry, rollback, and restart recovery paths.
- [ ] Run integration tests against pinned dependency versions plus supported upgrade candidates before compatibility claims change.
- [ ] Archive topology/configuration/dependency digests with results so failures are reproducible.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C083, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C083, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C083 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C083.

## INV-26-C084 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to MicroVM snapshotting.

### Engineering checklist
- [ ] Define the support matrix across x86_64/ARM64 or other architectures, CPU feature sets, page sizes, host kernels, hypervisor versions, guest kernel/image versions, device models, storage providers, and protocol/schema versions.
- [ ] Capture CPU model/feature compatibility requirements in snapshot metadata and reject restores that could execute with an incompatible feature set.
- [ ] Run capture on one supported node and restore on every explicitly compatible target class; separately test expected rejection for incompatible targets.
- [ ] Include rolling-upgrade and downgrade scenarios for runtime, kernel, adapter, and schema versions.
- [ ] Release only combinations with current automated evidence; mark untested combinations unsupported rather than implicitly compatible.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C084, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C084, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C084 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C084.

## INV-26-C085 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by MicroVM snapshotting.

### Engineering checklist
- [ ] Fuzz all untrusted parsers and validators: request schemas, snapshot manifests, configuration, error envelopes, provenance/signature metadata, storage object metadata, and any hypervisor adapter responses.
- [ ] Use coverage-guided fuzzing where practical and property-based tests for device normalization/fingerprinting, canonical serialization, numeric bounds, Unicode/ID handling, and state-machine transitions.
- [ ] Include pathological nesting/lengths, duplicate map keys, invalid UTF encodings, NaN/Inf, integer boundary values, decompression bombs, path traversal, and parser differentials.
- [ ] Run fuzzers under sanitizers/native hardening for any C/C++/Rust dependencies or adapters where available and retain crashing corpus/minimized reproducers.
- [ ] Promote every discovered bug to a deterministic regression test and track fuzz duration/coverage in release evidence.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C085, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C085, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C085 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C085.

## INV-26-C086 — PARTIAL - expand existing concurrency coverage
**Priority:** P0 - production blocker (partial)  
**Requirement:** Create concurrency and race-condition tests for shared/distributed MicroVM snapshotting state.

### Engineering checklist
- [ ] Keep the existing duplicate-capture concurrency test, but expand coverage to restore-vs-restore, capture-vs-restore, restore-vs-delete/quarantine, and reads during mutation.
- [ ] Add high-iteration stress tests with randomized scheduling and deterministic seeds; assert uniqueness, monotonic counters/generations, and absence of deadlocks/livelocks.
- [ ] When persistence/multi-controller support is added, test distributed races with competing owners, stale leases, fencing tokens, duplicate client retries, and network partitions.
- [ ] Instrument lock/transaction boundaries and verify no entropy injection or hypervisor mutation happens twice for one committed operation.
- [ ] Run thread/process race detection or stress tooling appropriate to the implementation and keep minimized reproducers for any discovered interleaving.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C086, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C086, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C086 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C086.

## INV-26-C087 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Create security tests derived directly from the MicroVM snapshotting threat model.

### Engineering checklist
- [ ] Derive a security test ID for every threat-model mitigation and maintain bidirectional traceability from threat -> control -> test -> evidence.
- [ ] Cover cross-tenant/workload/environment attacks, confused-deputy calls, authn/authz bypass, signature/provenance downgrade, ciphertext substitution, key misuse, replay, stale policy, and malicious device metadata.
- [ ] Validate fail-closed behavior during KMS/identity/attestation/audit outages and during partial failures after decryption or hypervisor load begins.
- [ ] Run privilege-boundary tests from the perspective of a compromised worker/service account and a hostile guest.
- [ ] Require all critical/high threat tests to pass with no unexpired risk waiver before production certification.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C087, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C087, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C087 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C087.

## INV-26-C088 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Create benchmark, soak, burst, and fleet-scale tests appropriate to MicroVM snapshotting.

### Engineering checklist
- [ ] Create benchmark, soak, burst, and fleet-scale suites using the same packaged build and realistic hypervisor/storage/KMS integrations used in production.
- [ ] Run long-duration soak sufficient to detect memory/FD/task leaks, queue drift, state-table growth, key/token refresh defects, and telemetry backpressure.
- [ ] Run burst tests that exceed planned peak arrival rates and fleet-scale tests with realistic tenant/workload cardinality.
- [ ] Collect latency distributions, throughput, errors/rejections, retries, resource high-water marks, dependency throttling, and recovery-to-baseline time.
- [ ] Compare automatically with approved baselines and archive raw telemetry plus environment fingerprint.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C088, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C088, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C088 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C088.

## INV-26-C089 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Create disaster, partition, reconnect, and degraded-control-plane tests.

### Engineering checklist
- [ ] Test network partitions among controllers/workers/storage/KMS/policy services, full node loss, site isolation, control-plane unavailability, DNS failure, and reconnect after long outage.
- [ ] Exercise in-flight capture/restore at each fault point and verify durable recovery, fencing/deduplication, cleanup, and tenant/security invariants.
- [ ] Test stale caches/credentials/policies crossing their TTL during partition and confirm operations transition to the documented safe state.
- [ ] Simulate disaster restoration of persistent metadata and verify blobs/keys/manifests reconcile without silently accepting orphaned or unverifiable snapshots.
- [ ] Measure RTO/RPO and compare with documented objectives; any manual step must have a validated runbook.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C089, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C089, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C089 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C089.

## INV-26-C090 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Require machine-readable acceptance evidence before certifying a MicroVM snapshotting release for production.

### Engineering checklist
- [ ] Define a signed machine-readable release evidence schema containing source/build digest, SBOM/provenance, config/schema versions, compatibility matrix, test/fuzz/benchmark/fault/security results, waivers, and approvers.
- [ ] Generate evidence from CI/CD directly rather than hand-editing status; attach immutable references/hashes to every artifact.
- [ ] Encode pass/fail/conditional states and expiry for exceptions; production certification must be impossible when required evidence is absent or stale.
- [ ] Verify evidence signatures/hash chain independently and retain results for the support/EOL lifetime required by policy.
- [ ] Make `pk_core gate INV-26` or the chosen gate consume this evidence and emit a deterministic production decision artifact.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C090, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C090, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C090 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C090.

# Operations, Release & Governance

## INV-26-C091 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Define production SLOs, error budgets, and support commitments for MicroVM snapshotting.

### Engineering checklist
- [ ] Define production SLIs/SLOs for successful authorized capture/restore, cross-tenant violations (zero tolerance), restore without entropy (zero tolerance), data integrity, availability, p99 time-to-ready, and dependency/error behavior.
- [ ] Define error budgets, measurement windows, exclusions, burn-rate alerts, and what engineering/release actions occur when a budget is exhausted.
- [ ] Document support hours/on-call coverage, response/restore targets by severity, supported environments, and customer/operator communication expectations.
- [ ] Ensure SLI definitions are implementable from emitted telemetry and align exactly with performance gate measurements.
- [ ] Review SLOs against load/failure evidence and obtain service-owner/SRE/security approval.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C091, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C091, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C091 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C091.

## INV-26-C092 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define canary, staged rollout, rollback, and emergency-disable procedures for MicroVM snapshotting.

### Engineering checklist
- [ ] Define staged rollout rings (test/canary/limited/fleet), promotion criteria, observation windows, maximum blast radius, and automatic halt/rollback signals.
- [ ] Use immutable build/config identifiers and compatibility checks so canaries exercise the exact candidate to be promoted.
- [ ] Define rollback for code, configuration, schemas, and runtime adapters, including cases where snapshot format/state cannot be downgraded safely.
- [ ] Provide emergency disable/quarantine procedures that stop new restores/captures without destroying evidence or making recovery impossible.
- [ ] Run periodic release/rollback/emergency-disable drills and record measured completion/recovery time.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C092, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C092, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C092 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C092.

## INV-26-C093 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Maintain a supported-version compatibility matrix for MicroVM snapshotting and adjacent dependencies.

### Engineering checklist
- [ ] Maintain a machine-readable compatibility matrix for component package, capture/restore schema, hypervisor, host kernel, CPU architecture/features, guest image/kernel, storage, KMS/signing, and adjacent INV-24/INV-25 versions.
- [ ] Distinguish supported, deprecated, test-only, incompatible, and end-of-life combinations with start/end dates.
- [ ] Generate release validation jobs directly from the matrix so every supported combination has current evidence.
- [ ] Block deployment to an unlisted/incompatible environment and provide a deterministic reason rather than attempting best-effort restore.
- [ ] Update the matrix as part of dependency upgrade and vulnerability response workflows.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C093, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C093, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C093 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C093.

## INV-26-C094 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define patching, vulnerability response, and end-of-life SLAs for MicroVM snapshotting.

### Engineering checklist
- [ ] Define vulnerability intake sources, severity model, triage owner, exploitability assessment, patch/mitigation deadlines, and emergency release process.
- [ ] Continuously inventory direct/transitive dependencies and runtime/hypervisor/host components using SBOM plus vulnerability feeds; account for distro/vendor backports.
- [ ] Define EOL/deprecation notices and migration windows for component, schema, hypervisor, and dependency versions.
- [ ] Provide emergency mitigations such as feature disable/quarantine, signer/key revocation, runtime blocklist, or rollout rollback.
- [ ] Test the vulnerability-response process with a tabletop or injected advisory and retain evidence of detection-to-remediation timing.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C094, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C094, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C094 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C094.

## INV-26-C095 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Provide backup, restore, migration, or reconstruction procedures for MicroVM snapshotting state where applicable.

### Engineering checklist
- [ ] Define what state must be backed up or reconstructed: metadata database, manifests/indexes, configuration provenance, audit chain, signing/KMS references, leases/history, and compatibility/gate records; snapshot blobs follow the selected storage durability model.
- [ ] Define RPO/RTO, encryption, access controls, retention, geographic/residency constraints, and key dependencies for backups.
- [ ] Prefer rebuildable indexes and content-addressed verification where possible; document authoritative sources of truth for reconstruction.
- [ ] Provide restore/reconciliation tooling that detects missing blobs, orphan manifests, wrong key references, digest mismatch, and stale ownership.
- [ ] Run periodic clean-environment recovery drills and verify recovered state can safely restore known test snapshots.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C095, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C095, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C095 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C095.

## INV-26-C096 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks.

### Engineering checklist
- [ ] Expand Day-0 into prerequisites, installation, identity/trust bootstrap, storage/KMS provisioning, configuration validation, readiness, smoke test, and baseline evidence capture.
- [ ] Expand Day-1 into deployment/canary, compatibility checks, traffic enablement, SLO/watch criteria, rollback, and change-record requirements.
- [ ] Expand Day-2 into capacity management, upgrades, key/cert rotation, backup/recovery, quarantine, incident triage, performance regression, certificate/KMS failure, and decommission/secure-delete procedures.
- [ ] Make commands/scripts copy-paste safe, versioned, least-privilege, and explicit about expected output and abort conditions.
- [ ] Exercise runbooks in staging/game days and update them from measured operator failures or ambiguous steps.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C096, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C096, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C096 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C096.

## INV-26-C097 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Define incident severity, paging, escalation, containment, and recovery procedures.

### Engineering checklist
- [ ] Define severity levels with concrete snapshotting examples: confirmed/suspected cross-tenant disclosure, unsigned/corrupt restore, widespread restore failure, tail-latency regression, dependency outage, and isolated user error.
- [ ] Define paging targets, acknowledgement/engagement targets, incident commander/security roles, escalation chain, and external communication triggers.
- [ ] Provide containment actions: global/tenant/site restore freeze, signer/key revocation, node quarantine, traffic drain, forensic snapshot preservation, and credential rotation.
- [ ] Define evidence preservation and chain-of-custody requirements without exposing additional snapshot memory during investigation.
- [ ] Run tabletop/technical exercises and verify paging, containment, recovery, post-incident action tracking, and regulatory/customer notification paths where applicable.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C097, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C097, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C097 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C097.

## INV-26-C098 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Perform recurring access, policy, dependency, configuration, and architecture reviews.

### Engineering checklist
- [ ] Schedule recurring reviews for service accounts/IAM, capability grants, break-glass access, trust roots, KMS keys, policies, dependency versions, config drift, supported matrix, threat model, and ADR assumptions.
- [ ] Define cadence and trigger-based reviews after incidents, major runtime/kernel updates, architecture changes, new sites/providers, or security advisories.
- [ ] Automate drift reports where possible and require owners to attest or remediate exceptions.
- [ ] Record reviewer, scope, findings, actions, due dates, and evidence; link unresolved items into the debt/waiver register.
- [ ] Make overdue critical reviews visible in the production exit gate.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C098, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C098, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C098 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C098.

## INV-26-C099 — MISSING
**Priority:** P1 - required before broad production rollout  
**Requirement:** Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.

### Engineering checklist
- [ ] Create a structured exception/waiver/debt register with ID, affected controls, risk statement, scope, compensating controls, owner, approver, creation date, expiry, and remediation plan.
- [ ] Require security/architecture/SRE approval appropriate to the risk and prohibit indefinite waivers; critical isolation/integrity violations should not be waivable for production.
- [ ] Link code/config feature flags and release evidence to the exact waiver so exceptions cannot silently propagate to unrelated environments.
- [ ] Alert before expiry and automatically fail the gate for expired unresolved waivers.
- [ ] Track deprecated behavior/version removal with usage telemetry and explicit migration deadlines.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C099, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C099, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C099 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C099.

## INV-26-C100 — MISSING
**Priority:** P0 - production blocker  
**Requirement:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Engineering checklist
- [ ] Create a formal production exit-gate policy that evaluates architecture, requirements/RTM, interfaces/schemas, implementation/configuration, security, resilience, performance, observability, testing/certification, operations/rollback, and ownership.
- [ ] Define non-waivable P0 criteria: tenant isolation, authn/authz, integrity/provenance, encryption where required, entropy reseeding, durable consistency, safe failure, supported compatibility, emergency disable, and executable release evidence.
- [ ] Have the gate consume machine-readable evidence and compatibility/support matrices and produce a signed immutable result tied to the exact build/config.
- [ ] Define GO/NO_GO/CONDITIONAL_GO semantics, who may approve conditions, expiry, and automatic invalidation when inputs change.
- [ ] Rehearse the gate on both intentionally incomplete and complete candidates to prove it cannot be satisfied by missing/skipped tests or prose-only claims.

### Required evidence / acceptance package
- [ ] Repository artifact(s) implementing or specifying C100, with stable links from the requirements traceability matrix.
- [ ] Automated test evidence for C100, including negative/failure-path coverage where applicable, tied to the exact build digest.
- [ ] Machine-readable gate record showing C100 as satisfied (or, for C086 until complete, explicitly partial) with no unexplained skipped tests.
- [ ] Owner/reviewer sign-off and any operational/runbook update required by C100.

---
# Cross-cutting concrete implementation gaps

These work packages are not substitutes for the controls above; they are the concrete runtime/repository components needed to satisfy them.

## X001 - Production hypervisor adapter

**Priority:** P0 - production blocker  
**Primary control mapping:** C021, C030, C031, C083, C084

- [ ] Define a narrow `HypervisorSnapshotAdapter` port with typed capture, restore, validate-compatibility, cancel, health, and capability-discovery operations; keep hypervisor-specific objects out of core domain types.
- [ ] Implement at least one production adapter (for example Firecracker, Cloud Hypervisor, or QEMU/KVM) using its supported control channel and pinned runtime/API version.
- [ ] Capture/validate the complete compatibility envelope required by that runtime: CPU architecture/features, guest memory/page assumptions, kernel/runtime version, device set/order/configuration, disks, network/vsock state as applicable, and snapshot format version.
- [ ] Run privileged adapter code with the minimum host/KVM/socket/filesystem authority and validate all paths/IDs before crossing the hypervisor boundary.
- [ ] Implement deadlines, cancellation, idempotency/operation IDs, deterministic error translation, health checks, and crash cleanup.
- [ ] Build real-VM integration tests for capture/restore, incompatible device/CPU model, corrupt state, hypervisor crash/hang, and node restart.
- [ ] Acceptance: a packaged build can capture and restore a real supported microVM through the adapter with all core security invariants enforced and machine-readable integration evidence attached.

## X002 - Real guest entropy injection

**Priority:** P0 - production blocker  
**Primary control mapping:** C021, C030, C041, C047-C050, C083, C087

- [ ] Replace `_default_entropy_injector` in production wiring with an adapter that delivers fresh cryptographic material into the restored guest through an approved RNG interface or authenticated guest agent path.
- [ ] Define exactly when the guest can execute relative to entropy injection; the guest must not transition to READY or expose application traffic before successful reseed confirmation.
- [ ] Use a CSPRNG from the host/approved provider, request at least the configured entropy quantity, and never persist/log/return the raw seed; zeroize transient copies where practical.
- [ ] Authenticate/bind the injection channel to the intended VM instance and operation to prevent reseeding the wrong guest or accepting spoofed acknowledgement.
- [ ] Fail closed and quarantine/terminate the restore if injection or acknowledgement fails, times out, or targets a stale instance.
- [ ] Test repeated clone restores for distinct entropy proofs plus guest-level evidence that RNG state diverges; include injector failure, replayed acknowledgement, wrong VM, timeout, and guest-agent compromise assumptions.
- [ ] Acceptance: no production restore path can mark a guest ready without verified fresh entropy delivery to that specific restored VM.

## X003 - Snapshot blob storage port and adapter

**Priority:** P0 - production blocker  
**Primary control mapping:** C021, C025-C030, C032, C047, C051-C060, C083, C095

- [ ] Define a typed storage port for staged write, atomic commit, immutable read, metadata lookup, delete/tombstone, list/reconcile, and health/capability queries.
- [ ] Use content digests and a signed/encrypted manifest that binds blob(s) to snapshot name/ID, tenant/workload/environment, device fingerprint, schema/runtime compatibility, key reference, size, and generation.
- [ ] Ensure publication is atomic: partially uploaded memory/device blobs must never be discoverable as a committed restorable snapshot.
- [ ] Namespace and authorize storage by tenant/security domain; defend against path traversal, object-key confusion, symlink attacks for filesystem implementations, and cross-prefix cloud IAM access.
- [ ] Define durability, replication, consistency, retention, lifecycle deletion, orphan cleanup, checksum verification, and storage-full behavior.
- [ ] Provide at least one real adapter plus corruption/truncation/partial-write/concurrent-writer/restart integration tests.
- [ ] Acceptance: a committed snapshot survives service restart, is integrity-verified before restore, and cannot be read/restored across its authorization boundary.

## X004 - Installable package, dependency lock, SBOM, reproducible build

**Priority:** P0 - release blocker  
**Primary control mapping:** C031, C032, C040, C045, C090, C094

- [ ] Add `pyproject.toml` (or the repository-standard packaging manifest) with package metadata, supported Python versions/platforms, entry points, dependency groups, and build backend pinned to approved versions.
- [ ] Create deterministic dependency locks with hashes for runtime/dev/test tooling and document the update process; avoid unconstrained transitive resolution in production builds.
- [ ] Exclude `__pycache__`, local test artifacts, secrets, and temporary build outputs from source/release packages.
- [ ] Generate an SBOM and source/build provenance; sign release artifacts and record exact source revision plus build environment/container digest.
- [ ] Add clean-environment install/build/sdist-wheel tests and compare output digests or normalized reproducibility evidence across isolated builds.
- [ ] Publish checksum/signature verification instructions and make CI reject unsigned/unprovenanced release artifacts.
- [ ] Acceptance: a clean machine can verify, install, test, and identify the exact dependency/build provenance of v5.x without undeclared local state.

## X005 - Mandatory signing/provenance provider integration

**Priority:** P0 - production blocker  
**Primary control mapping:** C045, C049, C087, C090

- [ ] Replace the optional-only GAP-07 path with a required production trust-provider interface; capture may not publish and restore may not load a snapshot lacking valid integrity/provenance evidence.
- [ ] Define signer identities, trust roots, signature envelope, canonical bytes, algorithm policy, key IDs/versions, timestamp/freshness, revocation, and provenance claims.
- [ ] Bind all security-sensitive metadata already present in `Snapshot.canonical()` plus storage object digests/generation and compatibility metadata into the authenticated manifest.
- [ ] Verify signatures/provenance before decryption/hypervisor load where architecture permits and always before guest execution.
- [ ] Cache verification results only with explicit digest/key/policy-version binding and bounded lifetime.
- [ ] Test tamper, wrong signer, revoked signer, absent provider, malformed envelope, algorithm downgrade, stale provenance, and canonicalization differences.
- [ ] Acceptance: production configuration cannot start or become ready with snapshot-signature enforcement disabled unless an explicitly designed non-production profile is selected.

## X006 - KMS and key lifecycle integration

**Priority:** P0 - production blocker  
**Primary control mapping:** C039, C047-C049, C051-C060, C094-C095

- [ ] Define a KMS abstraction for generate/wrap/unwrap/rewrap/disable and key metadata; production code must not embed long-lived KEKs/private keys.
- [ ] Use envelope encryption with per-snapshot or appropriately scoped DEKs and bind authenticated context to tenant/workload/environment/snapshot/generation.
- [ ] Define key alias/version policy, rotation cadence, cryptoperiod, revocation, KMS IAM, rate limits, regional/residency requirements, and disaster recovery.
- [ ] Minimize plaintext key lifetime and avoid logging/serializing DEKs; use provider handles when possible.
- [ ] Define behavior for KMS outage/throttling/revocation and ensure retries do not cause duplicate publication or unsafe fallback to plaintext.
- [ ] Test rotation/rewrap, revoked/disabled/wrong-context key, KMS outage, cross-tenant unwrap attempt, and key-deletion impact.
- [ ] Acceptance: all sensitive committed snapshot data is decryptable only under authorized KMS policy and remains manageable across planned key rotation.

## X007 - Node/runtime attestation and trust admission

**Priority:** P1 - required where host integrity is a trust assumption  
**Primary control mapping:** C044, C048, C055, C084

- [ ] Define whether node/hypervisor integrity must be attested; if yes, specify TPM/TEE/secure-boot measurements, verifier, nonce/freshness, acceptable reference values, and policy.
- [ ] Bind attested node identity to environment/site/runtime version and the service identity used for restore authorization.
- [ ] Reject stale, replayed, unverifiable, or policy-noncompliant attestation before releasing snapshot keys or sensitive plaintext to the node.
- [ ] Define fallback during verifier outage; do not silently downgrade to unauthenticated hosts.
- [ ] Audit attestation decision and reference/policy version without exposing sensitive measurements unnecessarily.
- [ ] Test replay, wrong nonce, revoked measurement, downgrade, cloned identity, verifier outage, and rolling host-image updates.
- [ ] Acceptance: when attestation is required by deployment policy, key release/restore is cryptographically gated on current compliant node evidence.

## X008 - Anti-replay restore authorization

**Priority:** P0 - production blocker  
**Primary control mapping:** C023-C026, C041, C048-C050, C053, C058, C087

- [ ] Define a signed/authorized restore grant or operation token containing operation ID, snapshot digest/ID, tenant/workload/environment, target node/instance, permitted action, generation, issued-at/expiry, and nonce.
- [ ] Persist consumed operation IDs/nonces or use an authoritative generation/fencing mechanism so a captured request cannot be replayed to start another VM.
- [ ] Bind tokens to intended audience and target security context; reject time-invalid, wrong-target, altered, reused, or downgraded grants.
- [ ] Coordinate anti-replay state with retries so legitimate idempotent retry succeeds without repeating the dangerous side effect.
- [ ] Define cleanup/recovery for token consumption around crash boundaries and distributed controller failover.
- [ ] Test identical request replay, token replay to another node/tenant, concurrent replay, clock skew, restart, and partition.
- [ ] Acceptance: the same authorization cannot produce more than the intended number of committed restores, including across process/node restart.

## X009 - Snapshot confidentiality envelope

**Priority:** P0 - production blocker  
**Primary control mapping:** C047, C049, C095

- [ ] Define an authenticated-encryption envelope and manifest fields for algorithm, nonce/IV, key reference, AAD schema/version, ciphertext digest/size, and chunking strategy for large memory images.
- [ ] Use nonce-unique AEAD and a reviewed chunk/frame scheme that detects truncation, reordering, duplication, and cross-snapshot chunk substitution.
- [ ] Authenticate tenant/workload/environment/device/runtime/generation context as AAD so ciphertext cannot be rebound under different metadata.
- [ ] Encrypt temporary/staging data or guarantee it resides only in protected ephemeral storage with documented wipe/lifetime semantics.
- [ ] Verify authentication before exposing recovered bytes to the hypervisor and avoid unauthenticated streaming that can mutate guest state before final integrity is known.
- [ ] Test ciphertext/tag/nonce/AAD manipulation, chunk reorder/drop/duplication, wrong key/context, and truncated uploads.
- [ ] Acceptance: copied storage objects are unintelligible without authorized keys and cannot be modified/rebound without deterministic restore rejection.

## X010 - Secure erase and data-remanence lifecycle

**Priority:** P1 - required before sensitive production data  
**Primary control mapping:** C039, C041-C043, C047, C050, C095-C097

- [ ] Inventory all locations that may contain plaintext snapshot data or cryptographic material: RAM buffers, mmap/page cache, temp files, crash dumps, swap, staging volumes, logs/traces, backups, and hypervisor working files.
- [ ] Minimize plaintext copies and lifetime; disable or control core dumps/swap for sensitive workers where appropriate and use protected temp locations with restrictive permissions.
- [ ] Implement explicit cleanup on success, failure, cancellation, timeout, and restart recovery; cryptographic erase via DEK destruction should be the primary deletion mechanism for immutable/cloud media.
- [ ] Define delete/tombstone retention and eventual physical deletion semantics for replicated/object storage and backups.
- [ ] Ensure entropy seed/key buffers are not returned and are zeroized where the language/runtime allows meaningful control.
- [ ] Run forensic-oriented tests that seed recognizable canary secrets and scan permitted residual artifacts after operations/deletion.
- [ ] Acceptance: the data lifecycle and residual-risk statement are documented and tested, with no avoidable plaintext persistence outside authorized storage.

## X011 - Durable metadata and restart reconstruction

**Priority:** P0 - production blocker  
**Primary control mapping:** C032, C036-C038, C051-C060, C077, C095

- [ ] Replace process-only `_snapshots` state with a transactional durable metadata repository or an adapter-backed authoritative state store while retaining an in-memory implementation only for tests.
- [ ] Persist snapshot identity/security context, manifest/blob digests, schema/runtime compatibility, state machine state, generation/fencing token, operation IDs, key/signature references, timestamps, quarantine/delete state, and audit linkage.
- [ ] Define atomic commit boundaries relative to blob storage and hypervisor operations and implement reconciliation for orphan blobs/metadata after crash.
- [ ] Use optimistic concurrency/CAS or transactions to prevent lost updates and stale writers; make restart replay idempotent.
- [ ] Create migrations with forward/backward compatibility policy, backups, and corruption detection.
- [ ] Run crash-at-every-transition/restart tests and prove a fresh process reconstructs the same authoritative safe state.
- [ ] Acceptance: service restart/node handoff does not lose committed snapshots, duplicate operations, or make incomplete/corrupt snapshots restorable.

## X012 - Telemetry exporter and operational surface

**Priority:** P1 - production blocker for operability  
**Primary control mapping:** C071-C080, C091, C097

- [ ] Implement concrete health/readiness endpoints and metrics/log/trace exporters rather than contract-only signal names.
- [ ] Define stable telemetry schemas, units, bounded labels, correlation IDs, redaction, sampling, retention, and exporter backpressure behavior.
- [ ] Instrument domain and adapter paths around authorization, compatibility verification, storage/KMS/signing, hypervisor load, entropy injection, lifecycle transitions, retries, and cleanup.
- [ ] Add dashboards and alerts that distinguish ordinary overload from security rejection, dependency outage, data corruption, and software defects.
- [ ] Keep mandatory security audit events separate from best-effort operational telemetry where reliability requirements differ.
- [ ] Run telemetry contract tests and outage/load tests for exporters; ensure blocked collectors cannot deadlock restore workers.
- [ ] Acceptance: an operator can identify why any failed/degraded restore occurred and correlate it to release/config/topology without enabling unsafe debug logging.

## X013 - Executable `pk_core` dependency and release gate

**Priority:** P0 - certification blocker  
**Primary control mapping:** C020, C030, C090, C100

- [ ] Declare/provision the exact compatible `pk_core` version or workspace dependency required by `component.py` and `contract.py`; avoid an undocumented external path-only dependency.
- [ ] Pin its source/version/digest and include it in lock/SBOM/provenance, or vendor it according to the parent repository policy.
- [ ] Run the existing component conformance tests in CI with `pk_core` importable; skipped gate tests must not count as release success.
- [ ] Execute `pk_core run`, `gate`, and `verify` against generated evidence and archive the resulting machine-readable artifacts.
- [ ] Fail release if the gate is NO_GO, if production-blocking checks are skipped, or if evidence-chain verification fails.
- [ ] Test the pipeline with intentionally missing/tampered evidence to prove the gate fails closed.
- [ ] Acceptance: the repository can be cloned/built in a clean environment and execute the complete 100-item gate without manual dependency discovery.

## X014 - Production benchmark/load certification harness

**Priority:** P1 - required before SLO certification  
**Primary control mapping:** C061-C070, C088, C091

- [ ] Create executable benchmark scenarios against real hypervisor/storage/KMS integrations; remove any possibility that test fixture `elapsed_ms` can satisfy performance acceptance.
- [ ] Parameterize guest memory size, device model, cache state, tenant/workload count, concurrency, storage latency, and KMS/signing latency.
- [ ] Capture raw per-operation timing plus host/resource telemetry and environment fingerprint; compute percentiles from raw samples with documented methodology.
- [ ] Add steady/burst/overload/recovery and multi-hour soak profiles plus comparison to cold-boot baseline.
- [ ] Set release thresholds and regression budgets separately by supported hardware/runtime class where necessary.
- [ ] Publish machine-readable results consumed by C070/C090/C100 gates.
- [ ] Acceptance: the p99 restore claim is supported by reproducible real-system measurements on each certified deployment class.

---
# Recommended implementation sequence

## Gate A — Make the repository independently buildable and certifiable
- [ ] X004 packaging/lock/SBOM/reproducible build.
- [ ] X013 executable `pk_core` dependency and full conformance gate.
- [ ] C009/C010/C020 ownership, ADR, and traceability.
- [ ] C021-C029 typed interface/auth/error/compatibility/limit/fixture contracts.

## Gate B — Complete the real secure restore path
- [ ] X001 production hypervisor adapter.
- [ ] X003 durable snapshot blob storage adapter.
- [ ] X005 mandatory signing/provenance.
- [ ] X006 KMS/key lifecycle and X009 confidentiality envelope.
- [ ] X002 real guest entropy injection.
- [ ] X008 anti-replay restore authorization.
- [ ] X011 durable metadata/restart reconstruction.
- [ ] Complete C041-C060 before claiming production safety.

## Gate C — Prove operability and performance
- [ ] X012 telemetry/health/diagnostics plus C071-C080.
- [ ] X014 real benchmark/load harness plus C061-C070.
- [ ] C082-C089 contract/integration/compatibility/fuzz/race/security/load/disaster certification.

## Gate D — Formal production certification
- [ ] C090 machine-readable acceptance bundle.
- [ ] C091-C099 SLO, rollout, support matrix, vulnerability/EOL, recovery, runbooks, incident response, reviews, and waiver governance.
- [ ] C100 formal production exit gate consumes all required evidence and produces a signed deterministic result.

# Final production-complete definition

INV-26 should be considered production-complete only when a clean checkout can be built reproducibly, start with validated secure configuration, use a real supported hypervisor and durable encrypted/integrity-protected storage, authenticate/authorize every boundary, restore only compatible authorized snapshot state, inject fresh entropy before guest readiness, recover safely from crash/partition/dependency failures, expose sufficient telemetry for operations, pass real-system performance/security/fault/compatibility tests, execute the complete `pk_core` gate without unexpected skips, and emit a signed release-evidence bundle proving every applicable C001-C100 requirement.
