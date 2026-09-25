> **v4.3.0 evidence snapshot (generated).** Boxes stay `[ ]`: completion requires reviewable evidence *and* review, and no independent reviewer exists for this build. Each item carries the status assigned mechanically by `evidence/run_evidence.py`.

# GAP-05 State Replication Consistency Model
# Missing Components — Professional Engineering Checklist

**Checklist version:** 1.0.0  
**Baseline package:** GAP-05 v4.2.0 audited/hardened  
**Scope:** 50 missing production components identified after the v4.2.0 audit  
**Purpose:** architecture, implementation, hardening, verification, certification, operations, and release-readiness tracking.

---

## How to use this checklist

- `[ ]` = not started / not evidenced.
- `[~]` = in progress (use only in working copies; convert to `[ ]` or `[x]` for formal evidence snapshots).
- `[x]` = completed **and** backed by reviewable evidence.
- Every completed item should link to a design record, source change, test, benchmark, runbook, security review, or release artifact.
- P0 items are production-blocking. P1 items are required for reliable distributed operation/certification. P2 items are scale/operability maturity items and should be scheduled with explicit risk acceptance if deferred.

### Recommended evidence fields

For engineering trackers, append these fields to each requirement: **Owner · Status · Target Release · Evidence URI/Path · Reviewer · Review Date · Residual Risk · Exception/Waiver ID**.

### Global completion gates

- [ ] **GAP05-GATE-001** — All P0 component checklists are complete with no unresolved critical/high-severity correctness or security findings.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-GATE-002** — All state-mutating paths preserve causal maximality, deterministic overflow behavior, quarantine preservation, dedupe/idempotency, tenant isolation, and membership fencing.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-GATE-003** — Crash/restart, restore/reseed, partition/heal, membership churn, replay, and dependency-outage tests meet the documented durability and convergence contracts.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-GATE-004** — Wire schemas, persistence formats, compatibility matrix, release metadata, SBOM, provenance, checksums/signatures, and operator documentation are version-consistent.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-GATE-005** — Observability and runbooks can diagnose every P0/P1 failure class without requiring direct mutation of internal state or unaudited file edits.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-GATE-006** — Performance/capacity results demonstrate bounded behavior at defined production limits with documented operating headroom.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED

---

## P0 — Required before production use

### 1. Authenticated replica identity

**Priority:** P0  
**Requirement family:** `GAP05-MC01`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC01-001** — Define the authoritative replica identity namespace and a canonical identity format that is stable across process restarts, host renames, IP changes, and transport reconnects.  
  `PARTIAL` — second-pass tag review: Only format; stability across restarts/renames/IP changes not shown — evidence: test_canonical_identity
- [ ] **GAP05-MC01-002** — Bind every accepted replication session to a cryptographically authenticated workload or node identity; prohibit caller-supplied replica names from being treated as authentication.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_authenticated_session_maps_to_one_replica
- [ ] **GAP05-MC01-003** — Select and document the trust mechanism (for example mTLS with workload certificates, SPIFFE/SPIRE-equivalent workload identity, or a platform-native attested identity provider).  
  `BLOCKED` — requires real workload-identity infrastructure (mTLS/SPIRE) not present in this build
- [ ] **GAP05-MC01-004** — Map the authenticated transport identity to exactly one active replica membership record for the current membership epoch.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_authenticated_session_maps_to_one_replica
- [ ] **GAP05-MC01-005** — Reject identities that are unknown, disabled, expired, revoked, mapped to multiple replicas, or valid only for a stale membership epoch.  
  `PARTIAL` — second-pass tag review: Disabled, multi-mapped, stale-epoch identities not tested — evidence: test_expired_revoked_untrusted_unknown
- [ ] **GAP05-MC01-006** — Define certificate or credential issuance, renewal, rotation, revocation, grace-period, and emergency-revocation behavior.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_expired_revoked_untrusted_unknown
- [ ] **GAP05-MC01-007** — Enforce peer-name/SAN/workload-ID validation and prevent wildcard identity acceptance unless explicitly justified and bounded.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_canonical_identity
- [ ] **GAP05-MC01-008** — Pin or validate the issuing trust domain and certificate chain; define trust-bundle rollout and rollback procedures.  
  `PARTIAL` — second-pass tag review: Trust-bundle rollback procedure not exercised — evidence: test_trust_bundle_rotation
- [ ] **GAP05-MC01-009** — Propagate the verified replica identity into write provenance, audit records, metrics, traces, and authorization decisions.  
  `PARTIAL` — second-pass tag review: Propagation into provenance, audit, metrics, traces not asserted — evidence: test_authenticated_session_maps_to_one_replica
- [ ] **GAP05-MC01-010** — Add replay-safe session establishment and channel binding so a captured authentication artifact cannot be reused on a different transport context.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_replay_and_channel_binding
- [ ] **GAP05-MC01-011** — Test replica spoofing, credential theft simulation, expired credentials, revoked credentials, duplicate identities, stale memberships, and trust-bundle rotation.  
  `PARTIAL` — second-pass tag review: Duplicate identities and stale memberships not tested — evidence: test_expired_revoked_untrusted_unknown; test_replay_and_channel_binding; test_stolen_credential_without_key_fails
- [ ] **GAP05-MC01-012** — Define an acceptance test proving that changing an untrusted `replica_id` field cannot alter the identity attributed to an authenticated peer.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_untrusted_replica_field_cannot_change_attribution

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC01-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC01-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC01-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 7}
- [ ] **GAP05-MC01-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC01-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC01-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01
- [ ] **GAP05-MC01-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc01

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 2. Signed/attested write provenance

**Priority:** P0  
**Requirement family:** `GAP05-MC02`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC02-001** — Define a canonical byte representation for the provenance envelope so signatures are deterministic across runtimes and language implementations.  
  `PARTIAL` — second-pass tag review: No cross-runtime/language determinism shown — evidence: test_valid_signature
- [ ] **GAP05-MC02-002** — Cryptographically bind writer identity, tenant, environment, logical key, value digest, causal vector, operation/write ID, schema version, membership epoch, issuance metadata, and policy-relevant attributes.  
  `PARTIAL` — second-pass tag review: Valid signature only; binding of schema, issuance, policy attrs not asserted — evidence: test_valid_signature
- [ ] **GAP05-MC02-003** — Select signature algorithms and key sizes from the organization’s approved cryptographic profile; document algorithm agility and deprecation rules.  
  `PARTIAL` — second-pass tag review: No approved profile or agility/deprecation rules asserted — evidence: test_valid_signature
- [ ] **GAP05-MC02-004** — Specify whether signatures are per write, per batch, or hierarchically chained, and define the verification boundary for each mode.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Per-batch/hierarchical signing not implemented; historical-key retirement policy not defined.
- [ ] **GAP05-MC02-005** — Verify provenance before a write can mutate active frontier, quarantine, durable dedupe state, or audit-derived state.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_untrusted_replica_field_cannot_change_attribution; test_verification_before_mutation
- [ ] **GAP05-MC02-006** — Reject provenance envelopes with missing fields, ambiguous canonicalization, unsupported algorithms, malformed signatures, or identity/signing-key mismatches.  
  `PARTIAL` — second-pass tag review: Ambiguous canonicalization and missing individual fields not tested — evidence: test_malformed_and_downgrade
- [ ] **GAP05-MC02-007** — Bind signing keys to authenticated replica identities through a verifiable certificate/attestation chain.  
  `PARTIAL` — second-pass tag review: Certificate/attestation chain binding of signing key not asserted — evidence: test_valid_signature
- [ ] **GAP05-MC02-008** — Define key rotation so in-flight and historical writes remain verifiable without accepting obsolete keys indefinitely.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Per-batch/hierarchical signing not implemented; historical-key retirement policy not defined.
- [ ] **GAP05-MC02-009** — Persist sufficient verification metadata to support later audit without persisting private signing material.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_verification_before_mutation
- [ ] **GAP05-MC02-010** — Define handling for unverifiable historical records during restore, migration, or trust-store rollover.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Per-batch/hierarchical signing not implemented; historical-key retirement policy not defined.
- [ ] **GAP05-MC02-011** — Add signature forgery, field-substitution, vector-substitution, value-digest substitution, downgrade, and cross-tenant replay tests.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_cross_tenant_replay; test_malformed_and_downgrade; test_single_bit_mutation_detected
- [ ] **GAP05-MC02-012** — Require an acceptance vector demonstrating that any single-bit mutation of a signed security-relevant field is detected.  
  `PARTIAL` — second-pass tag review: Only first byte of some fields; not every signed field/bit — evidence: test_single_bit_mutation_detected

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC02-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC02-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC02-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 6}
- [ ] **GAP05-MC02-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC02-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC02-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02
- [ ] **GAP05-MC02-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc02

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 3. Trusted monotonic counter allocation

**Priority:** P0  
**Requirement family:** `GAP05-MC03`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC03-001** — Define the authoritative per-replica causal counter and whether allocation is local-durable, lease-based, consensus-backed, hardware-backed, or delegated to another trusted service.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_monotonic_across_restart_and_no_reuse
- [ ] **GAP05-MC03-002** — Guarantee strict monotonicity across process crash, node reboot, storage replay, failover, and replica reseed.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_monotonic_across_restart_and_no_reuse
- [ ] **GAP05-MC03-003** — Persist allocated or committed high-water marks with crash-safe semantics so previously issued counters cannot be silently reused.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_monotonic_across_restart_and_no_reuse
- [ ] **GAP05-MC03-004** — Define counter reservation windows if batching is used and specify how unused reserved values are treated after crash or failover.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_monotonic_across_restart_and_no_reuse
- [ ] **GAP05-MC03-005** — Detect and reject counter rollback, duplicate counter reuse for divergent writes, and unreasonably large counter jumps according to a configurable policy.  
  `PARTIAL` — second-pass tag review: Counter rollback (lower value) not explicitly tested — evidence: test_equivocation_detected_and_audited; test_guard_jump_rollback
- [ ] **GAP05-MC03-006** — Bind counter authority to replica identity and current membership epoch so a removed replica cannot continue allocating accepted counters.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_fencing_rules
- [ ] **GAP05-MC03-007** — Define recovery behavior when durable counter state is missing, corrupt, stale, or restored from backup.  
  `PARTIAL` — second-pass tag review: Counter missing/corrupt/stale state not tested — evidence: test_backup_verify_restore_fenced_until_sync
- [ ] **GAP05-MC03-008** — Specify maximum counter width, overflow behavior, serialization type, and cross-language numeric compatibility.  
  `PARTIAL` — second-pass tag review: Cross-language compatibility and overflow behavior not shown — evidence: test_numeric_and_vector_edges
- [ ] **GAP05-MC03-009** — Expose current high-water mark, reservation state, rollback detections, jump detections, and allocation failures through diagnostics.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: An authenticated but compromised replica can still jump within max_gap; no external counter authority (lease/consensus).
- [ ] **GAP05-MC03-010** — Ensure concurrent local writers cannot allocate the same causal counter under thread/process contention.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_multiprocess_contention_documented_limit; test_thread_contention_unique
- [ ] **GAP05-MC03-011** — Test crash points before and after reservation/commit, multi-process contention, restore from stale backup, epoch changes, and near-overflow values.  
  `PARTIAL` — second-pass tag review: Only multiprocess contention; crash points, stale backup, epochs, overflow absent — evidence: test_multiprocess_contention_documented_limit
- [ ] **GAP05-MC03-012** — Require a monotonicity proof/test showing no accepted execution can produce two distinct writes with the same trusted `(replica, counter, epoch)` identity.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_monotonic_across_restart_and_no_reuse

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC03-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC03-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC03-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 8}
- [ ] **GAP05-MC03-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC03-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC03-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03
- [ ] **GAP05-MC03-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc03

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 4. Durable write-ahead log and recovery

**Priority:** P0  
**Requirement family:** `GAP05-MC04`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC04-001** — Define the WAL record types required to reconstruct active frontier, quarantine, dedupe identity, conflict resolution, membership epoch, and required audit linkage.  
  `PARTIAL` — second-pass tag review: Generic 'apply' records; required record types not asserted — evidence: test_framing_and_sequence
- [ ] **GAP05-MC04-002** — Use append semantics with record framing, checksums, sequence numbers, format version, and explicit transaction/commit markers.  
  `PARTIAL` — second-pass tag review: Transaction/commit markers and checksum not asserted — evidence: test_framing_and_sequence
- [ ] **GAP05-MC04-003** — Specify the exact durability point for an accepted write and ensure success is not reported before the configured durability contract is satisfied.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_crash_matrix_no_acked_loss
- [ ] **GAP05-MC04-004** — Make recovery deterministic: replaying a valid WAL from the same checkpoint must produce byte-equivalent or logically equivalent state.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_snapshot_plus_wal_restores_same_state
- [ ] **GAP05-MC04-005** — Handle torn writes, partial records, duplicate records, reordered storage visibility, truncated tails, and checksum failures without silently losing accepted writes.  
  `PARTIAL` — second-pass tag review: Duplicate WAL records and reordered storage visibility untested — evidence: test_duplicate_across_restart; test_mid_log_corruption_fails_closed; test_torn_tail_truncated_prior_kept
- [ ] **GAP05-MC04-006** — Define fsync/fdatasync/flush policy and its performance/durability trade-off; expose configuration only where operationally safe.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Single WAL file (no segment rotation); group commit only per record.
- [ ] **GAP05-MC04-007** — Bound WAL growth through checkpointing, segment rotation, retention, compaction, and safe deletion rules.  
  `PARTIAL` — second-pass tag review: Only compaction; no segment rotation/retention bound — evidence: test_compaction_keeps_uncovered
- [ ] **GAP05-MC04-008** — Ensure WAL deletion never removes the only durable representation of unresolved, quarantined, deduplicated, or audit-required state.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_compaction_keeps_uncovered
- [ ] **GAP05-MC04-009** — Encrypt WAL contents at rest when replication payloads or metadata are sensitive and integrate with managed key rotation.  
  `PARTIAL` — second-pass tag review: Managed key rotation with WAL not tested — evidence: test_encrypted_wal_recovers_and_fails_closed_without_key
- [ ] **GAP05-MC04-010** — Record recovery diagnostics including last valid sequence, truncated/corrupt segment, replay duration, and recovered object counts.  
  `PARTIAL` — second-pass tag review: Last valid seq, replay duration, recovered counts not asserted — evidence: test_wal_durable_write_is_audited_after_crash; test_torn_tail_truncated_prior_kept
- [ ] **GAP05-MC04-011** — Inject process termination at every persistence boundary and validate post-restart state against the pre-crash durability contract.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_crash_matrix_no_acked_loss
- [ ] **GAP05-MC04-012** — Require acceptance evidence showing no acknowledged write disappears across repeated crash/restart cycles.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_crash_matrix_no_acked_loss

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC04-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC04-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC04-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 9}
- [ ] **GAP05-MC04-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC04-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC04-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04
- [ ] **GAP05-MC04-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc04

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 5. Crash-consistent snapshots/checkpoints

**Priority:** P0  
**Requirement family:** `GAP05-MC05`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC05-001** — Define a versioned checkpoint manifest containing generation ID, creation time, membership epoch, schema versions, content hashes, and WAL cut position.  
  `PARTIAL` — second-pass tag review: Only generation asserted; creation time, epoch, schemas, hashes, WAL cut absent — evidence: test_atomic_validated_fallback
- [ ] **GAP05-MC05-002** — Produce snapshots from a logically consistent state boundary; prohibit mixtures of state from different apply transactions or membership epochs.  
  `PARTIAL` — second-pass tag review: No mixed-transaction/epoch prevention asserted — evidence: test_snapshot_plus_wal_restores_same_state
- [ ] **GAP05-MC05-003** — Write checkpoint data to a temporary generation and atomically publish it only after all files and hashes are durably committed.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_atomic_validated_fallback
- [ ] **GAP05-MC05-004** — Use strong checksums or cryptographic hashes for every checkpoint artifact plus a manifest-level integrity hash/signature.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_atomic_validated_fallback
- [ ] **GAP05-MC05-005** — Validate all checkpoint invariants before activation during restore, including causal-frontier maximality and dedupe consistency.  
  `PARTIAL` — second-pass tag review: Constructor check only, not restore path; dedupe consistency absent — evidence: test_restore_rejects_dominated_frontier
- [ ] **GAP05-MC05-006** — Retain at least one previously known-good generation until the replacement checkpoint is fully validated and recoverable.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_atomic_validated_fallback
- [ ] **GAP05-MC05-007** — Define behavior for missing files, hash mismatch, unsupported format, partial generation, stale generation, and storage exhaustion.  
  `PARTIAL` — second-pass tag review: Missing files, unsupported format, stale, storage exhaustion untested — evidence: test_atomic_validated_fallback; test_mid_log_corruption_fails_closed
- [ ] **GAP05-MC05-008** — Ensure quarantine and unresolved conflict state is preserved exactly and not normalized away during checkpoint creation.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_snapshot_plus_wal_restores_same_state
- [ ] **GAP05-MC05-009** — Define snapshot/WAL handoff rules so there is no gap or overlap ambiguity in recovery ordering.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_snapshot_plus_wal_restores_same_state; test_compaction_keeps_uncovered
- [ ] **GAP05-MC05-010** — Support deterministic offline validation tooling for checkpoint inspection without mutating production state.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_cli_read_only_tools
- [ ] **GAP05-MC05-011** — Test power-loss-style interruption at each snapshot phase and verify automatic fallback to the latest valid generation.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_crash_matrix_no_acked_loss; test_atomic_validated_fallback
- [ ] **GAP05-MC05-012** — Require a restore drill proving snapshot plus residual WAL reproduces the expected logical state and audit positions.  
  `PARTIAL` — second-pass tag review: Audit positions not asserted — evidence: test_snapshot_plus_wal_restores_same_state

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC05-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC05-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC05-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 7}
- [ ] **GAP05-MC05-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC05-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC05-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05
- [ ] **GAP05-MC05-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc05

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 6. Tenant/environment namespace enforcement

**Priority:** P0  
**Requirement family:** `GAP05-MC06`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC06-001** — Extend the canonical state key to include immutable tenant and environment identifiers in addition to the logical application key.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_same_key_two_tenants_isolated
- [ ] **GAP05-MC06-002** — Bind tenant/environment to authenticated identity and authorization context instead of trusting payload-supplied namespace fields.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_separator_injection_and_unauthorized_tenant
- [ ] **GAP05-MC06-003** — Make tenant/environment part of dedupe identity, write provenance, persistence partitioning, metrics labels or safe aggregates, and audit correlation.  
  `PARTIAL` — second-pass tag review: Dedupe, provenance, persistence, metrics, audit namespacing not asserted — evidence: test_same_key_two_tenants_isolated
- [ ] **GAP05-MC06-004** — Reject cross-tenant vectors, writes, resolution requests, restore artifacts, or membership references unless an explicitly authorized migration workflow exists.  
  `PARTIAL` — second-pass tag review: Only writes; vectors, resolutions, restore artifacts, membership refs absent — evidence: test_separator_injection_and_unauthorized_tenant; test_cross_tenant_replay
- [ ] **GAP05-MC06-005** — Define canonical normalization rules for namespace identifiers to prevent case, Unicode, separator, or encoding aliasing.  
  `PARTIAL` — second-pass tag review: Case and Unicode normalization aliasing not tested — evidence: test_separator_injection_and_unauthorized_tenant; test_duplicate_keys_unicode_extremes
- [ ] **GAP05-MC06-006** — Prevent one tenant’s hot keys, quarantine growth, or replay storms from exhausting another tenant’s configured resource allocation.  
  `PARTIAL` — second-pass tag review: Only hot-key isolation; quarantine growth and replay storms not tested — evidence: test_admission_hot_key_and_tenant_isolation
- [ ] **GAP05-MC06-007** — Enforce namespace boundaries in administrative APIs, operator tools, exports, backups, and observability queries.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Unicode normalisation (NFC) of identifiers not enforced - identifiers compared byte-exact.
- [ ] **GAP05-MC06-008** — Define environment isolation rules for development, test, staging, disaster-recovery, and production trust domains.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Unicode normalisation (NFC) of identifiers not enforced - identifiers compared byte-exact.
- [ ] **GAP05-MC06-009** — Prevent backup/restore or reseed operations from importing state into the wrong tenant/environment without an explicit verified mapping.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Unicode normalisation (NFC) of identifiers not enforced - identifiers compared byte-exact.
- [ ] **GAP05-MC06-010** — Add negative tests for namespace confusion, path/key injection, mixed-tenant batches, and privileged-operator mistakes.  
  `PARTIAL` — second-pass tag review: Mixed-tenant batches, operator mistakes untested — evidence: test_separator_injection_and_unauthorized_tenant
- [ ] **GAP05-MC06-011** — Audit every rejected cross-boundary operation with redacted but sufficient forensic context.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_separator_injection_and_unauthorized_tenant
- [ ] **GAP05-MC06-012** — Require an acceptance test proving identical logical keys in two tenants/environments never share causal, dedupe, persistence, or resolution state.  
  `PARTIAL` — second-pass tag review: Dedupe, persistence, resolution separation not asserted — evidence: test_same_key_two_tenants_isolated

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC06-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC06-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC06-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 5}
- [ ] **GAP05-MC06-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC06-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC06-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06
- [ ] **GAP05-MC06-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc06

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 7. Concrete wire schemas

**Priority:** P0  
**Requirement family:** `GAP05-MC07`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC07-001** — Author machine-readable schemas for `PK_REPLICATED_WRITE/1`, `PK_MERGE_RESULT/1`, and `PK_CONFLICT_SET/1` with normative field types, requiredness, bounds, and semantics.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_machine_readable_schemas_shipped
- [ ] **GAP05-MC07-002** — Define canonical serialization and deterministic field ordering/canonicalization rules where signatures or hashes depend on serialized bytes.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_canonical_and_opid
- [ ] **GAP05-MC07-003** — Specify integer widths, vector-entry representation, identifier formats, byte/string encoding, Unicode normalization, and maximum payload sizes.  
  `PARTIAL` — second-pass tag review: Unicode normalization, identifier formats, payload sizes not asserted — evidence: test_numeric_and_vector_edges
- [ ] **GAP05-MC07-004** — Define explicit one-of/union semantics for accepted, duplicate, superseded, quarantined, conflict, and resolved outcomes.  
  `PARTIAL` — second-pass tag review: Only invalid outcome rejected; union members not enumerated — evidence: test_merge_and_conflict_union
- [ ] **GAP05-MC07-005** — Prohibit unknown security-critical fields from altering semantics without a schema-version change.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_unknown_and_missing_fields
- [ ] **GAP05-MC07-006** — Define unknown-field behavior separately for strict ingress validation and forward-compatible pass-through scenarios.  
  `PARTIAL` — second-pass tag review: Forward-compatible pass-through not defined/tested — evidence: test_unknown_and_missing_fields
- [ ] **GAP05-MC07-007** — Ship generated or hand-written validators for all supported runtime languages and verify consistent accept/reject behavior.  
  `BLOCKED` — only a Python implementation exists
- [ ] **GAP05-MC07-008** — Encode tenant, environment, membership epoch, write ID, provenance references, and policy metadata explicitly rather than relying on side channels.  
  `PARTIAL` — second-pass tag review: Provenance references and policy metadata not asserted — evidence: test_machine_readable_schemas_shipped
- [ ] **GAP05-MC07-009** — Document normative examples and invalid examples, including oversized vectors, duplicate replica entries, malformed IDs, and unsupported encodings.  
  `PARTIAL` — second-pass tag review: Specific invalid example categories not asserted — evidence: test_published_corpus
- [ ] **GAP05-MC07-010** — Add corpus-based compatibility tests across serializer/deserializer implementations.  
  `PARTIAL` — second-pass tag review: Single implementation; no cross-implementation comparison — evidence: test_published_corpus
- [ ] **GAP05-MC07-011** — Fuzz parsers for truncation, nesting abuse, duplicate fields, integer extremes, Unicode edge cases, and malicious allocation patterns.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_duplicate_keys_unicode_extremes; test_json_decoder_fuzz
- [ ] **GAP05-MC07-012** — Require a schema conformance gate that rejects any release whose validators disagree on the published corpus.  
  `PARTIAL` — second-pass tag review: Single validator; no disagreement gate — evidence: test_published_corpus

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC07-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC07-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC07-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 8}
- [ ] **GAP05-MC07-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC07-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC07-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07
- [ ] **GAP05-MC07-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC07-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc07

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 8. Schema/version negotiation

**Priority:** P0  
**Requirement family:** `GAP05-MC08`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC08-001** — Define supported schema-version ranges for each peer and message type, including explicit minimum, maximum, and preferred versions.  
  `PARTIAL` — second-pass tag review: Minimum/maximum/preferred per message type not asserted — evidence: test_negotiation
- [ ] **GAP05-MC08-002** — Perform capability negotiation before accepting state-mutating replication traffic.  
  `PARTIAL` — second-pass tag review: Negotiation not enforced before node accepts traffic — evidence: test_negotiation
- [ ] **GAP05-MC08-003** — Specify downgrade rules and reject negotiation that would remove required security, provenance, tenancy, or causal semantics.  
  `BLOCKED` — no graphical UI exists (read-only CLI only) — evidence: test_negotiation
- [ ] **GAP05-MC08-004** — Define forward-compatible behavior for optional fields and strict rejection for unknown mandatory semantics.  
  `PARTIAL` — second-pass tag review: Optional-field forward compatibility not tested — evidence: test_unknown_and_missing_fields
- [ ] **GAP05-MC08-005** — Include negotiated versions in session diagnostics, traces, audit records, and error responses.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only version 1 exists; N+1 behaviour is tested only as rejection.
- [ ] **GAP05-MC08-006** — Bind schema negotiation to authenticated peer identity and current membership epoch to prevent unauthenticated downgrade manipulation.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only version 1 exists; N+1 behaviour is tested only as rejection.
- [ ] **GAP05-MC08-007** — Define mixed-version rolling-upgrade sequences and the point at which older peers become read-only, quarantined, or disconnected.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only version 1 exists; N+1 behaviour is tested only as rejection.
- [ ] **GAP05-MC08-008** — Ensure persisted state records retain enough version metadata for later migration and forensic interpretation.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only version 1 exists; N+1 behaviour is tested only as rejection.
- [ ] **GAP05-MC08-009** — Provide deterministic error codes for no-common-version, deprecated-version, malformed negotiation, and policy-prohibited downgrade.  
  `PARTIAL` — second-pass tag review: Deprecated, malformed, policy-prohibited codes not asserted — evidence: test_negotiation
- [ ] **GAP05-MC08-010** — Maintain a machine-readable compatibility matrix consumed by CI and deployment tooling.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only version 1 exists; N+1 behaviour is tested only as rejection.
- [ ] **GAP05-MC08-011** — Test N/N-1/N+1 combinations, unsupported future versions, legacy downgrade attempts, reconnects during upgrade, and partial fleet rollouts.  
  `PARTIAL` — second-pass tag review: No reconnects during upgrade or partial fleet rollout; N+1 limited — evidence: test_downgrade_fuzz; test_negotiation
- [ ] **GAP05-MC08-012** — Require release evidence demonstrating safe rolling upgrade and rollback between every supported adjacent version.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC08-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC08-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC08-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC08-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC08-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC08-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC08-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08
- [ ] **GAP05-MC08-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC08-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc08

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 9. Durable deduplication identity

**Priority:** P0  
**Requirement family:** `GAP05-MC09`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC09-001** — Define a globally stable write/operation identifier independent of transport retries, process lifetime, and checkpoint compaction.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_duplicate_across_restart; test_canonical_and_opid
- [ ] **GAP05-MC09-002** — Bind the dedupe identifier cryptographically or semantically to replica identity, counter, tenant/environment, membership epoch, and payload digest as appropriate.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_canonical_and_opid
- [ ] **GAP05-MC09-003** — Persist dedupe state before or atomically with acknowledging a newly accepted operation.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_duplicate_across_restart
- [ ] **GAP05-MC09-004** — Detect the security-significant case where the same dedupe ID is presented with different causal or payload content.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_equivocation_detected_and_audited
- [ ] **GAP05-MC09-005** — Separate benign retransmission from equivocation and route equivocation to security/audit handling.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_equivocation_detected_and_audited
- [ ] **GAP05-MC09-006** — Define retention/compaction rules that do not re-enable replay of operations that peers may legitimately retransmit after long outages.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Dedupe window not coordinated with an anti-entropy horizon setting.
- [ ] **GAP05-MC09-007** — Coordinate dedupe compaction with anti-entropy horizons, tombstone retention, backup/restore, and membership changes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Dedupe window not coordinated with an anti-entropy horizon setting.
- [ ] **GAP05-MC09-008** — Use bounded lookup structures and quantify false-positive/false-negative behavior if probabilistic structures are considered.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Dedupe window not coordinated with an anti-entropy horizon setting.
- [ ] **GAP05-MC09-009** — Expose dedupe-hit, equivocation, state-size, compaction, and lookup-latency metrics.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC09-010** — Ensure restored nodes do not forget dedupe identities still required by the supported replay/anti-entropy horizon.  
  `BLOCKED` — no graphical UI exists (read-only CLI only) — evidence: test_backup_verify_restore_fenced_until_sync
- [ ] **GAP05-MC09-011** — Test duplicate delivery across restart, checkpoint, restore, reseed, membership epoch change, and transport reconnect.  
  `PARTIAL` — second-pass tag review: No restore, reseed, epoch change, reconnect duplicates — evidence: test_duplicate_across_restart
- [ ] **GAP05-MC09-012** — Require acceptance evidence that exact replay is idempotent and divergent reuse of an identity is rejected and auditable.  
  `PARTIAL` — second-pass tag review: Divergent identity reuse not in cited test — evidence: test_duplicate_across_restart

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC09-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC09-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC09-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC09-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC09-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC09-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09
- [ ] **GAP05-MC09-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC09-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc09

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 10. Tamper-evident audit ledger

**Priority:** P0  
**Requirement family:** `GAP05-MC10`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC10-001** — Define an append-only audit event model covering accepted, duplicate, superseded, quarantined, rejected, resolved, restored, reconfigured, and administrative actions.  
  `PARTIAL` — second-pass tag review: Only 'apply' events exercised; duplicate/quarantined/resolved/restored/admin events absent — evidence: test_chain_verifies_across_segments
- [ ] **GAP05-MC10-002** — Chain records using cryptographic hashes or signatures so deletion, insertion, reordering, or modification is detectable.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_chain_verifies_across_segments; test_tamper_insert_delete_truncate
- [ ] **GAP05-MC10-003** — Include stable event sequence, authenticated actor/replica, tenant/environment, key digest, write/provenance ID, outcome, reason code, policy version, and membership epoch.  
  `PARTIAL` — second-pass tag review: Sequence, reason code, policy version, membership epoch not asserted in audit record — evidence: test_audit_no_raw_values
- [ ] **GAP05-MC10-004** — Separate audit evidence from mutable operational logs and define retention appropriate to compliance/forensics requirements.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC10-005** — Protect audit signing/chaining keys with managed key services or hardware-backed mechanisms where required.  
  `BLOCKED` — requires a KMS/HSM integration not present in this build
- [ ] **GAP05-MC10-006** — Define segment sealing, rollover, export, verification, and long-term archival formats.  
  `PARTIAL` — second-pass tag review: Export and long-term archival formats not defined/asserted; only chain verify — evidence: test_archive_handoff_verified; test_chain_verifies_across_segments
- [ ] **GAP05-MC10-007** — Provide an offline verifier that validates the full chain and reports the first integrity break without modifying evidence.  
  `PARTIAL` — second-pass tag review: Reporting of first integrity break not asserted — evidence: test_chain_verifies_across_segments; test_cli_read_only_tools
- [ ] **GAP05-MC10-008** — Prevent sensitive values or credentials from leaking into the ledger; store digests/references where raw data is not required.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_audit_no_raw_values
- [ ] **GAP05-MC10-009** — Make audit write failure semantics explicit: fail closed, buffer within a bounded durable queue, or enter a safe degraded mode according to policy.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_node_refuses_write_when_audit_full; test_retention_refuses_when_full_without_archive; test_wal_durable_write_is_audited_after_crash
- [ ] **GAP05-MC10-010** — Correlate ledger entries with traces, policy decisions, transport sessions, and recovery events.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_audit_no_raw_values; test_trace_correlation
- [ ] **GAP05-MC10-011** — Test tampering, truncation, duplicated segments, missing segments, key rotation, clock anomalies, and partial storage failure.  
  `PARTIAL` — second-pass tag review: No duplicated/missing segments, key rotation, clock anomalies, partial storage failure — evidence: test_tamper_insert_delete_truncate
- [ ] **GAP05-MC10-012** — Require an acceptance artifact containing a successfully verified exported audit chain plus deliberate-tamper detection evidence.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_chain_verifies_across_segments; test_tamper_insert_delete_truncate

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC10-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC10-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC10-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 9}
- [ ] **GAP05-MC10-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC10-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC10-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10
- [ ] **GAP05-MC10-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc10

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 11. Bounded audit/quarantine retention policy

**Priority:** P0  
**Requirement family:** `GAP05-MC11`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC11-001** — Define independent retention classes for active quarantine, resolved conflicts, operational audit, security audit, and exported archives.  
  `BLOCKED` — requires independent human review, approval or an exercise with people — evidence: test_archive_handoff_verified
- [ ] **GAP05-MC11-002** — Establish hard and soft byte/object quotas per tenant, key, node, and system with deterministic pressure behavior.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_retention_refuses_when_full_without_archive
- [ ] **GAP05-MC11-003** — Preserve unresolved writes according to the system’s write-preservation invariant even when local retention limits are reached.  
  `PARTIAL` — second-pass tag review: Only refusal asserted; preservation of unresolved writes not checked — evidence: test_node_refuses_write_when_audit_full
- [ ] **GAP05-MC11-004** — Specify safe refusal/backpressure behavior before storage exhaustion can corrupt the active frontier or WAL.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_node_refuses_write_when_audit_full; test_retention_refuses_when_full_without_archive
- [ ] **GAP05-MC11-005** — Define archival/export handoff with integrity verification before local deletion.  
  `PARTIAL` — second-pass tag review: Verification-before-deletion not asserted; only archive presence and active segment count — evidence: test_archive_handoff_verified
- [ ] **GAP05-MC11-006** — Use watermarks and hysteresis to prevent oscillation between normal and pressure modes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No hysteresis/watermarks; no per-tenant byte quotas.
- [ ] **GAP05-MC11-007** — Expose age, bytes, item count, oldest unresolved item, quota percentage, export lag, and deletion-failure metrics.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No hysteresis/watermarks; no per-tenant byte quotas.
- [ ] **GAP05-MC11-008** — Define privileged and audited operator overrides without permitting silent deletion of causally relevant state.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No hysteresis/watermarks; no per-tenant byte quotas.
- [ ] **GAP05-MC11-009** — Coordinate retention with dedupe horizon, tombstones, backups, legal/compliance retention, and anti-entropy repair windows.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No hysteresis/watermarks; no per-tenant byte quotas.
- [ ] **GAP05-MC11-010** — Handle archive destination unavailability through bounded buffering and explicit degraded health.  
  `PARTIAL` — second-pass tag review: No archive-outage buffering or degraded health asserted; only no-archive refusal — evidence: test_retention_refuses_when_full_without_archive
- [ ] **GAP05-MC11-011** — Test sustained conflict floods, archive outages, quota exhaustion, recovery after pressure, and restart while retention cleanup is in progress.  
  `PARTIAL` — second-pass tag review: No conflict floods, recovery after pressure, or restart during cleanup — evidence: test_retention_refuses_when_full_without_archive
- [ ] **GAP05-MC11-012** — Require acceptance evidence that reaching configured limits causes bounded, observable, invariant-preserving behavior rather than uncontrolled growth.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_retention_refuses_when_full_without_archive

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC11-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC11-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC11-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC11-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC11-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC11-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC11-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11
- [ ] **GAP05-MC11-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc11

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 12. Encryption and managed key rotation

**Priority:** P0  
**Requirement family:** `GAP05-MC12`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC12-001** — Classify replication payloads, causal metadata, identities, audit data, snapshots, WAL, and backups by confidentiality requirement.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC12-002** — Require authenticated encryption for replication transport and prohibit obsolete protocol/cipher versions according to the organization’s crypto baseline.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC12-003** — Encrypt WAL, snapshots, quarantine exports, and backups at rest when they contain protected information.  
  `PARTIAL` — second-pass tag review: Only WAL; snapshots, exports, backups not encrypted/tested — evidence: test_encrypted_wal_recovers_and_fails_closed_without_key
- [ ] **GAP05-MC12-004** — Use centrally managed data-encryption keys or envelope encryption rather than embedding long-lived secrets in configuration.  
  `PARTIAL` — second-pass tag review: In-process keyring; no central management — evidence: test_roundtrip_rotation_rewrap_retire
- [ ] **GAP05-MC12-005** — Separate keys by environment and, where required, tenant or data class to limit blast radius.  
  `PARTIAL` — second-pass tag review: AAD binding only; keys not separated per environment/tenant — evidence: test_wrong_namespace_and_corruption
- [ ] **GAP05-MC12-006** — Define automated key creation, distribution, caching, rotation, revocation, compromise response, and destruction.  
  `PARTIAL` — second-pass tag review: Distribution, caching, compromise response, destruction absent — evidence: test_roundtrip_rotation_rewrap_retire
- [ ] **GAP05-MC12-007** — Persist key identifiers/version references needed to decrypt historical state without retaining plaintext key material.  
  `PARTIAL` — second-pass tag review: Persistence of key IDs without key material not asserted — evidence: test_roundtrip_rotation_rewrap_retire
- [ ] **GAP05-MC12-008** — Design rotation to support mixed key versions during rolling transition and long-running recovery.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_roundtrip_rotation_rewrap_retire
- [ ] **GAP05-MC12-009** — Make inability to decrypt required state a hard, diagnosable recovery/readiness failure rather than silently skipping records.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_encrypted_wal_recovers_and_fails_closed_without_key; test_wrong_namespace_and_corruption
- [ ] **GAP05-MC12-010** — Redact keys, tokens, plaintext sensitive values, and crypto internals from logs, traces, crash dumps, and diagnostics.  
  `PARTIAL` — second-pass tag review: Only log emitter; traces, crash dumps, diagnostics not tested — evidence: test_log_redaction_injection_sampling
- [ ] **GAP05-MC12-011** — Test revoked keys, missing keys, rotated keys, corrupt ciphertext, wrong-tenant keys, and rollback to a snapshot encrypted under older keys.  
  `PARTIAL` — second-pass tag review: Revoked, missing, rotated keys, old-snapshot rollback not in cited tests — evidence: test_wrong_namespace_and_corruption
- [ ] **GAP05-MC12-012** — Require an acceptance drill that rotates keys under load and then proves both new writes and authorized historical restore remain functional.  
  `PARTIAL` — second-pass tag review: No rotation under load or historical restore — evidence: test_roundtrip_rotation_rewrap_retire

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC12-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC12-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC12-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC12-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC12-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC12-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC12-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12
- [ ] **GAP05-MC12-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc12

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 13. Authorization policy integration

**Priority:** P0  
**Requirement family:** `GAP05-MC13`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC13-001** — Define distinct permissions for replicate/write, inspect conflict metadata, inspect values, quarantine, resolve, export, restore, membership change, configuration change, and audit access.  
  `PARTIAL` — second-pass tag review: No distinct inspect-values, export, restore, membership vs config, audit-access permissions — evidence: test_default_deny_and_codes; test_replicate_vs_write_separation
- [ ] **GAP05-MC13-002** — Authorize using authenticated actor/replica identity plus tenant/environment, resource key scope, membership epoch, and operation type.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_policy_outage_denies_and_versions_audited
- [ ] **GAP05-MC13-003** — Default deny all privileged or administrative operations and require explicit grants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_default_deny_and_codes
- [ ] **GAP05-MC13-004** — Keep authorization evaluation separate from conflict-resolution policy so security access decisions cannot be overridden by merge logic.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No attribute-based conditions (key scope, epoch) in grants.
- [ ] **GAP05-MC13-005** — Version authorization policies and include the effective policy identifier in audit evidence for privileged actions.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_policy_outage_denies_and_versions_audited
- [ ] **GAP05-MC13-006** — Define service-to-service and human/operator authorization models separately, including break-glass procedures.  
  `PARTIAL` — second-pass tag review: Only wildcard restriction; separate service vs human models and break-glass procedure absent — evidence: test_wildcards_only_break_glass
- [ ] **GAP05-MC13-007** — Prevent confused-deputy behavior by propagating original caller context where one subsystem acts on behalf of another.  
  `PARTIAL` — second-pass tag review: Only WRITE vs REPLICATE separation; caller-context propagation not asserted — evidence: test_replicate_vs_write_separation
- [ ] **GAP05-MC13-008** — Cache authorization decisions only with bounded TTL and revocation-aware invalidation.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_revoked_grant_takes_effect_immediately
- [ ] **GAP05-MC13-009** — Return non-sensitive, stable denial reason codes while avoiding information disclosure across tenants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_default_deny_and_codes
- [ ] **GAP05-MC13-010** — Instrument authorization allow/deny/error/latency metrics without high-cardinality leakage.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No attribute-based conditions (key scope, epoch) in grants.
- [ ] **GAP05-MC13-011** — Test privilege escalation, cross-tenant access, stale cached grants, revoked actors, policy backend outage, and break-glass expiry.  
  `PARTIAL` — second-pass tag review: Privilege escalation, stale cached grants, break-glass expiry not tested — evidence: test_policy_outage_denies_and_versions_audited
- [ ] **GAP05-MC13-012** — Require acceptance evidence proving every externally reachable state-mutating operation has an explicit authorization decision.  
  `PARTIAL` — second-pass tag review: Authorizer unit test only; no enumeration of all external mutating operations — evidence: test_default_deny_and_codes

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC13-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC13-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC13-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC13-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 5}
- [ ] **GAP05-MC13-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC13-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC13-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13
- [ ] **GAP05-MC13-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc13

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 14. Atomic configuration/membership store

**Priority:** P0  
**Requirement family:** `GAP05-MC14`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC14-001** — Define a versioned membership record containing replica identities, statuses, roles, membership epoch, provenance, activation time, and compatibility metadata.  
  `PARTIAL` — second-pass tag review: Only epoch/parent asserted; statuses, roles, activation time, compat absent — evidence: test_cas_and_chain
- [ ] **GAP05-MC14-002** — Use compare-and-swap or equivalent atomic activation so concurrent controllers cannot publish divergent membership generations.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_cas_and_chain; test_concurrent_controllers_one_winner
- [ ] **GAP05-MC14-003** — Cryptographically authenticate or sign membership changes and record the initiating authorized principal.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Changes are not signed by the controller; distribution across nodes is out of scope (store is per node).
- [ ] **GAP05-MC14-004** — Persist current and previous known-good membership generations to support controlled rollback.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_cas_and_chain; test_rollback_keeps_retirements
- [ ] **GAP05-MC14-005** — Make every replication decision reference an explicit membership epoch rather than ambient mutable configuration.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Changes are not signed by the controller; distribution across nodes is out of scope (store is per node).
- [ ] **GAP05-MC14-006** — Prevent partial visibility of membership updates across threads/processes on the same node.  
  `PARTIAL` — second-pass tag review: Partial visibility not checked; threads only, no processes — evidence: test_concurrent_controllers_one_winner
- [ ] **GAP05-MC14-007** — Define quorum/authority ownership for membership publication and avoid local ad hoc edits in production.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Changes are not signed by the controller; distribution across nodes is out of scope (store is per node).
- [ ] **GAP05-MC14-008** — Validate that replica IDs are unique, identity mappings are unambiguous, and required schema/security capabilities are present before activation.  
  `PARTIAL` — second-pass tag review: Schema/security capability presence not validated — evidence: test_validation
- [ ] **GAP05-MC14-009** — Expose current epoch, configuration hash, publisher, activation status, rollback status, and peer agreement diagnostics.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Changes are not signed by the controller; distribution across nodes is out of scope (store is per node).
- [ ] **GAP05-MC14-010** — Define startup behavior when membership state is missing, corrupt, ahead of local software capability, or older than persisted replicated state.  
  `PARTIAL` — second-pass tag review: Only corrupt; missing, ahead, older state untested — evidence: test_corrupt_chain_detected_on_load
- [ ] **GAP05-MC14-011** — Test concurrent update races, failed activation, rollback, stale writers, corrupt configuration, and fleet propagation delays.  
  `PARTIAL` — second-pass tag review: Failed activation, rollback, stale writers, propagation delays absent — evidence: test_concurrent_controllers_one_winner; test_corrupt_chain_detected_on_load
- [ ] **GAP05-MC14-012** — Require acceptance evidence that exactly one membership generation is active per node and stale generations cannot authorize new writes.  
  `PARTIAL` — second-pass tag review: Stale generations authorizing writes not tested here — evidence: test_cas_and_chain

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC14-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC14-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC14-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC14-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 5}
- [ ] **GAP05-MC14-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC14-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC14-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14
- [ ] **GAP05-MC14-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc14

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 15. Replica membership-change protocol

**Priority:** P0  
**Requirement family:** `GAP05-MC15`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC15-001** — Define explicit lifecycle states such as joining, seeding, active, draining, removed, fenced, and retired.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Joining/draining are not explicit states (only active/retired); drain protocol computing high_water is the operator's.
- [ ] **GAP05-MC15-002** — Specify how a joining replica obtains a trusted baseline snapshot plus subsequent WAL/anti-entropy delta before it may author writes.  
  `PARTIAL` — second-pass tag review: No refusal to author before baseline sync asserted — evidence: test_join_during_writes_and_rejoin_via_sync
- [ ] **GAP05-MC15-003** — Fence removed replicas using membership epochs or tokens so previously valid credentials alone cannot continue authoring accepted writes.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_removed_replica_cannot_write_after_fencing; test_fencing_rules
- [ ] **GAP05-MC15-004** — Define treatment of historical vector entries for removed replicas and the conditions under which they may be compacted.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Joining/draining are not explicit states (only active/retired); drain protocol computing high_water is the operator's.
- [ ] **GAP05-MC15-005** — Ensure a replica ID is never ambiguously reused for a logically new replica incarnation without a new epoch/incarnation identifier.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_reseed_creates_new_incarnation
- [ ] **GAP05-MC15-006** — Define drain semantics so in-flight writes and anti-entropy sessions complete or are safely retried before removal.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Joining/draining are not explicit states (only active/retired); drain protocol computing high_water is the operator's.
- [ ] **GAP05-MC15-007** — Specify reseed behavior after disk loss or corruption and prevent stale local state from re-entering the cluster.  
  `PARTIAL` — second-pass tag review: Stale local state re-entry not tested — evidence: test_reseed_creates_new_incarnation
- [ ] **GAP05-MC15-008** — Coordinate membership transition with counter allocation, provenance verification, authorization, schema compatibility, and transport discovery.  
  `PARTIAL` — second-pass tag review: Counter, schema, discovery coordination not asserted — evidence: test_join_during_writes_and_rejoin_via_sync
- [ ] **GAP05-MC15-009** — Audit every lifecycle transition with old/new membership generations and operator/controller identity.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Joining/draining are not explicit states (only active/retired); drain protocol computing high_water is the operator's.
- [ ] **GAP05-MC15-010** — Expose per-replica lifecycle state and transition progress through health/administrative APIs.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Joining/draining are not explicit states (only active/retired); drain protocol computing high_water is the operator's.
- [ ] **GAP05-MC15-011** — Test join during active writes, remove during partitions, reseed with stale backup, duplicate replica identities, and rapid add/remove churn.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Joining/draining are not explicit states (only active/retired); drain protocol computing high_water is the operator's.
- [ ] **GAP05-MC15-012** — Require acceptance evidence that no removed or stale incarnation can create an accepted write after its fencing point.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_fencing_rules

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC15-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC15-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC15-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC15-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC15-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC15-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC15-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC15-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC15-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15
- [ ] **GAP05-MC15-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc15

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 16. Production conflict-resolution adapter

**Priority:** P0  
**Requirement family:** `GAP05-MC16`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC16-001** — Define a stable request/response contract to the external policy owner (`GAP-13`) including conflict set, causal metadata, tenant/environment, schema, and policy context.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_valid_decision_carries_digest_and_version
- [ ] **GAP05-MC16-002** — Version every policy decision and persist the policy version, decision ID, input digest, output digest, and relevant evidence.  
  `PARTIAL` — second-pass tag review: No persistence of decision ID, input/output digests asserted — evidence: test_valid_decision_carries_digest_and_version
- [ ] **GAP05-MC16-003** — Make resolution idempotent so retries of the same policy decision cannot create divergent state.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_end_to_end_resolution_dominates_quarantine
- [ ] **GAP05-MC16-004** — Require a resolution result to causally dominate every unresolved sibling/quarantined write it resolves, including overflow-hidden frontier members.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_end_to_end_resolution_dominates_quarantine
- [ ] **GAP05-MC16-005** — Validate policy output before state mutation; reject malformed, stale, partially covering, or unauthorized resolutions.  
  `PARTIAL` — second-pass tag review: Partially covering and unauthorized resolutions not tested — evidence: test_stale_decision_rejected; test_valid_decision_carries_digest_and_version
- [ ] **GAP05-MC16-006** — Define timeout, retry, circuit-breaker, and safe-unavailable behavior that preserves conflicts rather than guessing a winner.  
  `PARTIAL` — second-pass tag review: No circuit breaker; conflict preservation on node not asserted — evidence: test_timeout_retry_then_unavailable_keeps_conflict
- [ ] **GAP05-MC16-007** — Separate deterministic automatic policies from operator-assisted/manual resolution and audit both paths.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No circuit breaker; no dry-run/explain mode; no live GAP-13 engine tested.
- [ ] **GAP05-MC16-008** — Prevent policy service compromise from bypassing authorization, tenancy, provenance, or membership fencing.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No circuit breaker; no dry-run/explain mode; no live GAP-13 engine tested.
- [ ] **GAP05-MC16-009** — Support dry-run/explain mode that returns proposed resolution evidence without mutating replicated state.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No circuit breaker; no dry-run/explain mode; no live GAP-13 engine tested.
- [ ] **GAP05-MC16-010** — Instrument decision latency, timeout rate, retry rate, invalid response rate, policy-version distribution, and unresolved age.  
  `PARTIAL` — second-pass tag review: Only call count; latency, rates, version distribution, unresolved age absent — evidence: test_timeout_retry_then_unavailable_keeps_conflict
- [ ] **GAP05-MC16-011** — Test policy outage, duplicate responses, contradictory responses, old policy versions, delayed results after membership change, and oversized conflict sets.  
  `PARTIAL` — second-pass tag review: Only outage; duplicate/contradictory/old/delayed/oversized responses untested — evidence: test_timeout_retry_then_unavailable_keeps_conflict
- [ ] **GAP05-MC16-012** — Require acceptance evidence that identical validated policy inputs under a deterministic policy produce the same resolution artifact across nodes.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_valid_decision_carries_digest_and_version

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC16-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC16-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC16-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC16-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC16-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC16-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16
- [ ] **GAP05-MC16-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc16

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

## P1 — Required for reliable distributed operation

### 17. Anti-entropy/reconciliation engine

**Priority:** P1  
**Requirement family:** `GAP05-MC17`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC17-001** — Define reconciliation scope by tenant/environment, key range/partition, membership epoch, and schema compatibility.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_converge_after_divergence
- [ ] **GAP05-MC17-002** — Select digest structures such as Merkle trees, rolling hashes, range digests, or version summaries with quantified collision/integrity properties.  
  `PARTIAL` — second-pass tag review: No quantified collision/integrity properties — evidence: test_converge_after_divergence
- [ ] **GAP05-MC17-003** — Compare both active frontier and required dedupe/tombstone metadata so a peer cannot appear converged while missing replay-prevention state.  
  `PARTIAL` — second-pass tag review: Only frontier compared; dedupe/tombstone metadata not — evidence: test_converge_after_divergence
- [ ] **GAP05-MC17-004** — Use bounded incremental sessions rather than unbounded full-state scans for large datasets.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_leaf_level_scoping
- [ ] **GAP05-MC17-005** — Authenticate every peer and authorize the reconciled namespace before exchanging digests or state.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_repair_is_authenticated_and_idempotent
- [ ] **GAP05-MC17-006** — Verify provenance and schema on repaired records exactly as on normal replication ingress.  
  `PARTIAL` — second-pass tag review: Only authz rejection; provenance/schema check on repair not asserted — evidence: test_repair_is_authenticated_and_idempotent
- [ ] **GAP05-MC17-007** — Make repair idempotent under duplicated, reordered, and interrupted reconciliation sessions.  
  `PARTIAL` — second-pass tag review: Only repeated session; duplicated/reordered/interrupted not tested — evidence: test_repair_is_authenticated_and_idempotent
- [ ] **GAP05-MC17-008** — Prioritize gaps based on age, key criticality, backlog, and resource pressure without starving cold partitions.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Full scan to build the tree each call (no incremental maintenance); no scheduling/prioritisation.
- [ ] **GAP05-MC17-009** — Expose last-successful reconciliation, lag, differing ranges, bytes scanned/repaired, retry state, and peer health.  
  `PARTIAL` — second-pass tag review: Only differing leaves/sent; last success, lag, bytes, retry, peer health absent — evidence: test_leaf_level_scoping
- [ ] **GAP05-MC17-010** — Coordinate reconciliation with compaction, tombstone GC, membership changes, and backup/restore horizons.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Full scan to build the tree each call (no incremental maintenance); no scheduling/prioritisation.
- [ ] **GAP05-MC17-011** — Test long partitions, asymmetric loss, divergent checkpoints, duplicate repairs, repair during upgrade, and peer restart mid-session.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Full scan to build the tree each call (no incremental maintenance); no scheduling/prioritisation.
- [ ] **GAP05-MC17-012** — Require acceptance evidence that two healthy replicas with eventual connectivity converge to the same causal frontier after arbitrary supported delivery loss/reordering.  
  `PARTIAL` — second-pass tag review: Cited test has no delivery loss or reordering — evidence: test_converge_after_divergence

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC17-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC17-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC17-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC17-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC17-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC17-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17
- [ ] **GAP05-MC17-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc17

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 18. Replication transport adapter

**Priority:** P1  
**Requirement family:** `GAP05-MC18`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC18-001** — Define framed protocol messages with explicit type, length, schema version, session ID, membership epoch, tenant/environment scope, and integrity protections.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_lossy_reordering_duplicating_link_converges
- [ ] **GAP05-MC18-002** — Use authenticated encrypted transport and bind the channel identity to replica identity validation.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No real sockets/TLS; no keepalive or session state machine; no jitter in backoff.
- [ ] **GAP05-MC18-003** — Implement bounded send/receive queues, flow control, and backpressure so slow peers cannot exhaust memory.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_backpressure_bounded_queues; test_lossy_reordering_duplicating_link_converges
- [ ] **GAP05-MC18-004** — Separate transport retry from model idempotency; retries must preserve stable write identities and provenance.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_lossy_reordering_duplicating_link_converges
- [ ] **GAP05-MC18-005** — Support batching with deterministic per-item outcomes and clear partial-failure semantics.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No real sockets/TLS; no keepalive or session state machine; no jitter in backoff.
- [ ] **GAP05-MC18-006** — Define connection establishment, capability/schema negotiation, keepalive, reconnect, draining, and shutdown state machines.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No real sockets/TLS; no keepalive or session state machine; no jitter in backoff.
- [ ] **GAP05-MC18-007** — Apply limits before allocation for frame size, batch size, vector size, compression ratio, and decompressed payload size.  
  `BLOCKED` — no compression is implemented, so compression-specific checks cannot run
- [ ] **GAP05-MC18-008** — Use retry budgets, exponential backoff with jitter, and peer-specific circuit breaking to avoid retry storms.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC18-009** — Propagate trace context and stable operation/session correlation without trusting peer-controlled trace fields for authorization.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No real sockets/TLS; no keepalive or session state machine; no jitter in backoff.
- [ ] **GAP05-MC18-010** — Expose connection count, queue depth, bytes, retransmits, RTT, backpressure time, failures, and per-peer compatibility status.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No real sockets/TLS; no keepalive or session state machine; no jitter in backoff.
- [ ] **GAP05-MC18-011** — Test malformed frames, slowloris behavior, disconnect mid-batch, duplicate frames, reordering, compression bombs, and simultaneous reconnect storms.  
  `PARTIAL` — second-pass tag review: Only mutation fuzz; slowloris, disconnect, bombs, reconnect storms absent — evidence: test_binary_and_frame_fuzz
- [ ] **GAP05-MC18-012** — Require acceptance evidence that transport faults never alter causal semantics beyond delay/duplication and never create silent write loss.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_lossy_reordering_duplicating_link_converges

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC18-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC18-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC18-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC18-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC18-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC18-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18
- [ ] **GAP05-MC18-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc18

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 19. Delete/tombstone semantics

**Priority:** P1  
**Requirement family:** `GAP05-MC19`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC19-001** — Define delete as an explicit causally ordered operation rather than physical absence.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_delete_is_causal_and_no_resurrection
- [ ] **GAP05-MC19-002** — Specify tombstone payload, write identity, provenance, vector, schema version, membership epoch, and retention metadata.  
  `PARTIAL` — second-pass tag review: Only deleted flag asserted; retention metadata/epoch etc. not — evidence: test_delete_is_causal_and_no_resurrection
- [ ] **GAP05-MC19-003** — Ensure concurrent update versus delete is represented as a real conflict unless a declared deterministic data-type policy says otherwise.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_concurrent_update_vs_delete_is_conflict
- [ ] **GAP05-MC19-004** — Prevent stale replicas from resurrecting values after a tombstone has causally dominated them.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_delete_is_causal_and_no_resurrection
- [ ] **GAP05-MC19-005** — Define tombstone garbage-collection only when the system can prove no supported peer/recovery source can reintroduce pre-delete state.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_gc_only_when_all_active_acked_and_floor_blocks_resurrection
- [ ] **GAP05-MC19-006** — Coordinate tombstone retention with anti-entropy horizon, offline-replica limits, backup retention, dedupe, and membership retirement.  
  `PARTIAL` — second-pass tag review: No backup retention, offline-replica, retirement coordination — evidence: test_gc_only_when_all_active_acked_and_floor_blocks_resurrection
- [ ] **GAP05-MC19-007** — Preserve deletion evidence in audit even after operational tombstone GC.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_gc_only_when_all_active_acked_and_floor_blocks_resurrection
- [ ] **GAP05-MC19-008** — Define restore semantics: restoring an old backup must not accidentally resurrect data deleted after the backup point.  
  `PARTIAL` — second-pass tag review: Uses reopen, not backup restore — evidence: test_gc_only_when_all_active_acked_and_floor_blocks_resurrection
- [ ] **GAP05-MC19-009** — Handle repeated deletes and duplicate tombstones idempotently.  
  `NOT_EVIDENCED` — second-pass tag review: Repeated deletes/duplicate tombstones not submitted — evidence: test_delete_is_causal_and_no_resurrection
- [ ] **GAP05-MC19-010** — Expose tombstone counts, age distribution, GC eligibility, GC lag, and resurrection-prevention violations.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Acknowledgement collection is supplied by the caller.
- [ ] **GAP05-MC19-011** — Test delete/update races, long partitions, node restore from stale snapshot, membership removal, repeated deletes, and GC boundary conditions.  
  `PARTIAL` — second-pass tag review: No long partitions, stale snapshot restore, membership removal, repeated deletes — evidence: test_concurrent_update_vs_delete_is_conflict
- [ ] **GAP05-MC19-012** — Require acceptance evidence that any causally dominated pre-delete write remains deleted after all supported repair and restore paths.  
  `PARTIAL` — second-pass tag review: Restore paths not exercised — evidence: test_delete_is_causal_and_no_resurrection

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC19-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC19-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC19-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC19-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC19-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC19-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC19-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC19-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC19-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19
- [ ] **GAP05-MC19-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc19

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 20. Vector compaction strategy

**Priority:** P1  
**Requirement family:** `GAP05-MC20`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC20-001** — Quantify expected replica-history growth and establish hard metadata budgets for vectors per write/key.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No dotted version vectors; live vectors are not compacted.
- [ ] **GAP05-MC20-002** — Select a compaction model such as dotted version vectors, incarnation epochs, retired-replica summaries, or another formally defined equivalent.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_gc_only_when_all_active_acked_and_floor_blocks_resurrection
- [ ] **GAP05-MC20-003** — Preserve the ability to determine causal dominance/concurrency for all events within the supported reconciliation and recovery horizon.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_gc_only_when_all_active_acked_and_floor_blocks_resurrection
- [ ] **GAP05-MC20-004** — Never compact away information still needed to reject stale writes from removed replicas or restored backups.  
  `PARTIAL` — second-pass tag review: Removed-replica and restored-backup stale writes not tested — evidence: test_gc_only_when_all_active_acked_and_floor_blocks_resurrection
- [ ] **GAP05-MC20-005** — Bind compaction decisions to membership epochs and authoritative replica-retirement evidence.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No dotted version vectors; live vectors are not compacted.
- [ ] **GAP05-MC20-006** — Define deterministic compaction so equivalent logical histories compact to compatible representations across replicas.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC20-007** — Version compacted vector formats and provide migration logic for persisted state and wire messages.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No dotted version vectors; live vectors are not compacted.
- [ ] **GAP05-MC20-008** — Reject vectors that exceed configured limits before unbounded allocation or comparison work occurs.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No dotted version vectors; live vectors are not compacted.
- [ ] **GAP05-MC20-009** — Expose raw/compacted vector sizes, compaction frequency, retired-entry counts, and compaction failures.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No dotted version vectors; live vectors are not compacted.
- [ ] **GAP05-MC20-010** — Benchmark comparison cost and serialized size before/after compaction across realistic fleet churn.  
  `BLOCKED` — requires production-scale data or multi-hour runs outside this build's budget
- [ ] **GAP05-MC20-011** — Property-test causal relations before and after compaction over randomized histories and membership changes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No dotted version vectors; live vectors are not compacted.
- [ ] **GAP05-MC20-012** — Require acceptance evidence that compaction does not change the result of dominance/concurrency queries within the documented support horizon.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_gc_only_when_all_active_acked_and_floor_blocks_resurrection

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC20-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC20-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc20
- [ ] **GAP05-MC20-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `NOT_EVIDENCED` — registry field 'api' empty
- [ ] **GAP05-MC20-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `NOT_EVIDENCED` — registry field 'api' empty
- [ ] **GAP05-MC20-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC20-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC20-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc20
- [ ] **GAP05-MC20-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc20
- [ ] **GAP05-MC20-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc20
- [ ] **GAP05-MC20-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC20-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc20
- [ ] **GAP05-MC20-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC20-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC20-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC20-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC20-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC20-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC20-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc20

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 21. CRDT/commutative type registry

**Priority:** P1  
**Requirement family:** `GAP05-MC21`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC21-001** — Define an explicit registry of supported mergeable data types rather than treating arbitrary values as commutative.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_algebraic_laws
- [ ] **GAP05-MC21-002** — Specify canonical type identifiers, schema versions, merge functions, identity elements, and validation rules.  
  `PARTIAL` — second-pass tag review: Identity elements, schema versions, validation rules not asserted — evidence: test_algebraic_laws
- [ ] **GAP05-MC21-003** — Require merge functions to satisfy the intended algebraic properties (associativity, commutativity, idempotence where applicable).  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_algebraic_laws
- [ ] **GAP05-MC21-004** — Separate state-based, operation-based, and delta CRDT semantics and do not mix their delivery assumptions.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No delta/op-based CRDTs; no cross-language vectors.
- [ ] **GAP05-MC21-005** — Bind each replicated value to a declared type/schema so peers cannot choose different merge functions for the same key.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_unregistered_type_never_merges
- [ ] **GAP05-MC21-006** — Reject unsupported or incompatible CRDT versions instead of falling back to silent last-writer behavior.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_unregistered_type_never_merges
- [ ] **GAP05-MC21-007** — Define causal-context retention required by each CRDT and integrate it with vector compaction/tombstones.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC21-008** — Sandbox or otherwise constrain plugin-defined merge code if third-party/custom types are allowed.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No delta/op-based CRDTs; no cross-language vectors.
- [ ] **GAP05-MC21-009** — Record type/version and merge outcome evidence in audit and trace data.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No delta/op-based CRDTs; no cross-language vectors.
- [ ] **GAP05-MC21-010** — Provide deterministic cross-language conformance vectors for every registered type.  
  `BLOCKED` — only a Python implementation exists
- [ ] **GAP05-MC21-011** — Property-test algebraic laws with randomized value/order/duplication sequences and malformed state.  
  `PARTIAL` — second-pass tag review: Malformed state not tested — evidence: test_algebraic_laws
- [ ] **GAP05-MC21-012** — Require acceptance evidence that every declared automatically mergeable type converges under arbitrary supported message order and duplication.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_algebraic_laws

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC21-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC21-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC21-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21
- [ ] **GAP05-MC21-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC21-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 2}
- [ ] **GAP05-MC21-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC21-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC21-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC21-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC21-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc21

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 22. Quarantine operator API

**Priority:** P1  
**Requirement family:** `GAP05-MC22`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC22-001** — Expose read-only enumeration of quarantined conflicts with stable pagination, filtering, tenant scoping, and deterministic ordering.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_list_export_freeze
- [ ] **GAP05-MC22-002** — Provide detail retrieval containing provenance, vectors, value digests/redacted values, reason codes, timestamps, and related active-frontier context.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_list_export_freeze
- [ ] **GAP05-MC22-003** — Require explicit authorization scopes for inspect metadata, inspect values, export, freeze, retry, and resolve.  
  `BLOCKED` — no graphical UI exists (read-only CLI only) — evidence: test_list_export_freeze
- [ ] **GAP05-MC22-004** — Use immutable quarantine item IDs so operator actions remain traceable after restart or compaction.  
  `NOT_EVIDENCED` — second-pass tag review: Test checks freeze persistence, not immutable quarantine item IDs — evidence: test_freeze_survives_restart
- [ ] **GAP05-MC22-005** — Implement optimistic concurrency/version preconditions on mutation commands to prevent acting on stale conflict views.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_stale_decision_rejected
- [ ] **GAP05-MC22-006** — Support export with integrity metadata and audit linkage without silently removing local state.  
  `PARTIAL` — second-pass tag review: No integrity metadata or audit linkage asserted on export — evidence: test_list_export_freeze
- [ ] **GAP05-MC22-007** — Define freeze/hold semantics that block automated cleanup/resolution where policy requires human review.  
  `PARTIAL` — second-pass tag review: Freeze blocks writes but resolution still allowed; no auto-cleanup/resolution block — evidence: test_list_export_freeze
- [ ] **GAP05-MC22-008** — Route retry/resolve through the same invariant checks as normal model operations; prohibit direct list mutation.  
  `PARTIAL` — second-pass tag review: Retry path and invariant routing not exercised — evidence: test_views_immutable
- [ ] **GAP05-MC22-009** — Return stable machine-readable error codes for stale item, unauthorized, policy unavailable, conflict changed, and persistence failure.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No pagination cursor; no per-item immutable IDs beyond op_id.
- [ ] **GAP05-MC22-010** — Audit every operator view of sensitive values and every state-changing action where required.  
  `BLOCKED` — no graphical UI exists (read-only CLI only) — evidence: test_list_export_freeze
- [ ] **GAP05-MC22-011** — Test concurrent operators, stale pagination cursors, repeated commands, restart between request and commit, and cross-tenant access attempts.  
  `PARTIAL` — second-pass tag review: Only restart; concurrent operators, stale cursors, cross-tenant missing — evidence: test_freeze_survives_restart
- [ ] **GAP05-MC22-012** — Require acceptance evidence that no API operation can bypass causal dominance, provenance, authorization, or durable audit requirements.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC22-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC22-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC22-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC22-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC22-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC22-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC22-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC22-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22
- [ ] **GAP05-MC22-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc22

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 23. Immutable/read-only state views

**Priority:** P1  
**Requirement family:** `GAP05-MC23`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC23-001** — Replace externally exposed mutable collections with immutable snapshots, tuples, frozen records, iterators, or defensive copies.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_views_immutable
- [ ] **GAP05-MC23-002** — Ensure returned value objects cannot mutate internal vectors, provenance, payload metadata, or nested structures by reference.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_views_immutable
- [ ] **GAP05-MC23-003** — Define snapshot consistency: one state-view call must represent a coherent model generation rather than a torn mix of mutations.  
  `PARTIAL` — second-pass tag review: Concurrent writes hit other keys; only antichain checked, not generation coherence — evidence: test_reader_threads_see_coherent_views
- [ ] **GAP05-MC23-004** — Attach generation/version metadata to views used by administrative compare-and-act workflows.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Core ReplicatedKey still exposes mutable lists (kept for v4.2.0 compatibility).
- [ ] **GAP05-MC23-005** — Keep all state mutation behind invariant-enforcing methods with documented locking/transaction boundaries.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Core ReplicatedKey still exposes mutable lists (kept for v4.2.0 compatibility).
- [ ] **GAP05-MC23-006** — Prevent subclassing or reflection-based bypasses where the runtime/API exposure makes that a realistic threat.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Core ReplicatedKey still exposes mutable lists (kept for v4.2.0 compatibility).
- [ ] **GAP05-MC23-007** — Define serialization of state views separately from internal storage objects to avoid accidentally exposing implementation details.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Core ReplicatedKey still exposes mutable lists (kept for v4.2.0 compatibility).
- [ ] **GAP05-MC23-008** — Make sensitive fields subject to authorization/redaction before constructing a caller-visible view.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Core ReplicatedKey still exposes mutable lists (kept for v4.2.0 compatibility).
- [ ] **GAP05-MC23-009** — Measure memory overhead of defensive copies and use immutable structural sharing where safe and justified.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Core ReplicatedKey still exposes mutable lists (kept for v4.2.0 compatibility).
- [ ] **GAP05-MC23-010** — Add tests that attempt mutation of every exposed collection and nested object.  
  `PARTIAL` — second-pass tag review: Only one view object; nested vector list is mutable, not every collection — evidence: test_views_immutable
- [ ] **GAP05-MC23-011** — Run threaded tests proving readers never observe structurally invalid intermediate state.  
  `PARTIAL` — second-pass tag review: Only antichain check; viewed key barely mutated during readers — evidence: test_reader_threads_see_coherent_views
- [ ] **GAP05-MC23-012** — Require acceptance evidence that external callers can inspect but cannot mutate authoritative model state without invoking a validated mutation API.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_views_immutable

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC23-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC23-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc23
- [ ] **GAP05-MC23-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc23
- [ ] **GAP05-MC23-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc23
- [ ] **GAP05-MC23-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc23
- [ ] **GAP05-MC23-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc23
- [ ] **GAP05-MC23-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC23-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC23-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC23-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc23
- [ ] **GAP05-MC23-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC23-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC23-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 2}
- [ ] **GAP05-MC23-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC23-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC23-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC23-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC23-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc23

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 24. Persistence migration framework

**Priority:** P1  
**Requirement family:** `GAP05-MC24`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC24-001** — Assign explicit format versions to WAL records, checkpoints, dedupe indexes, audit metadata, and any auxiliary durable stores.  
  `PARTIAL` — second-pass tag review: Only WAL and snapshot formats; dedupe index and audit metadata not — evidence: test_migration_v1_to_v2_and_downgrade_refused; test_framing_and_sequence
- [ ] **GAP05-MC24-002** — Define supported upgrade and downgrade paths, including versions that require one-way migration.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_migration_v1_to_v2_and_downgrade_refused
- [ ] **GAP05-MC24-003** — Make migrations restartable/idempotent with durable progress markers and no ambiguous half-migrated state.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only one hop (1->2); WAL format has no migration yet.
- [ ] **GAP05-MC24-004** — Take or verify a recoverable backup/checkpoint before any destructive or one-way migration step.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_migration_v1_to_v2_and_downgrade_refused
- [ ] **GAP05-MC24-005** — Validate causal, dedupe, quarantine, membership, and audit invariants after each migration phase.  
  `PARTIAL` — second-pass tag review: Only frontier length; dedupe, quarantine, membership, audit invariants not — evidence: test_migration_v1_to_v2_and_downgrade_refused
- [ ] **GAP05-MC24-006** — Support offline preflight that estimates disk space, time, unsupported records, and required software compatibility.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_migration_v1_to_v2_and_downgrade_refused
- [ ] **GAP05-MC24-007** — Define rolling-upgrade interaction when nodes with different persistence readers/writers coexist.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only one hop (1->2); WAL format has no migration yet.
- [ ] **GAP05-MC24-008** — Prevent newer software from writing a format that would make an approved rollback impossible unless the rollout explicitly crosses a point of no return.  
  `BLOCKED` — requires independent human review, approval or an exercise with people
- [ ] **GAP05-MC24-009** — Record migration actor/version, source/target formats, counts, hashes, warnings, and completion status in audit evidence.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only one hop (1->2); WAL format has no migration yet.
- [ ] **GAP05-MC24-010** — Provide tooling to inspect and validate old formats without modifying them.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_migration_v1_to_v2_and_downgrade_refused; test_cli_read_only_tools
- [ ] **GAP05-MC24-011** — Test interrupted migrations at every phase, insufficient disk, corrupt source records, downgrade rejection, and restore of pre-migration backups.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Only one hop (1->2); WAL format has no migration yet.
- [ ] **GAP05-MC24-012** — Require acceptance evidence for every supported version hop using production-representative durable fixtures.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_migration_v1_to_v2_and_downgrade_refused

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC24-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC24-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC24-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC24-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC24-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC24-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC24-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC24-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC24-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24
- [ ] **GAP05-MC24-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc24

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 25. Backup/restore/reseed workflow

**Priority:** P1  
**Requirement family:** `GAP05-MC25`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC25-001** — Define backup scope covering checkpoints, required WAL segments, membership/configuration, key references, dedupe horizon, audit anchors, and schema metadata.  
  `PARTIAL` — second-pass tag review: Backup scope contents not asserted — evidence: test_backup_verify_restore_fenced_until_sync
- [ ] **GAP05-MC25-002** — Create backups from a consistency point that can be independently verified before retention is considered successful.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_backup_verify_restore_fenced_until_sync
- [ ] **GAP05-MC25-003** — Encrypt backups and authenticate manifests; store keys separately from backup media according to recovery policy.  
  `PARTIAL` — second-pass tag review: No backup encryption or key separation — evidence: test_backup_tamper_detected
- [ ] **GAP05-MC25-004** — Assign backup IDs, source cluster/environment, membership epoch, checkpoint generation, WAL range, and content hashes.  
  `PARTIAL` — second-pass tag review: Backup ID, source, epoch, generation, WAL range not asserted — evidence: test_backup_verify_restore_fenced_until_sync
- [ ] **GAP05-MC25-005** — Implement restore preflight that rejects wrong tenant/environment, incompatible schema, stale membership assumptions, missing keys, or corrupt artifacts.  
  `PARTIAL` — second-pass tag review: Wrong tenant, schema, stale membership, missing keys not tested — evidence: test_backup_verify_restore_fenced_until_sync
- [ ] **GAP05-MC25-006** — Fence a restored node until it has reconciled stale state and obtained the current membership epoch.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_backup_verify_restore_fenced_until_sync
- [ ] **GAP05-MC25-007** — Define point-in-time recovery semantics and how later tombstones/deletes are protected against accidental resurrection.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Backups are not encrypted as a set (values inside are, if a keyring is used); no RPO/RTO measurement at scale.
- [ ] **GAP05-MC25-008** — Specify reseed workflow for a replica that lost local durable state, including identity/incarnation handling.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_reseed_creates_new_incarnation
- [ ] **GAP05-MC25-009** — Automate post-restore verification of frontier invariants, dedupe state, audit chain anchors, and anti-entropy completion.  
  `PARTIAL` — second-pass tag review: Only convergence/value; dedupe, audit anchors not verified — evidence: test_backup_verify_restore_fenced_until_sync
- [ ] **GAP05-MC25-010** — Measure RPO/RTO and restore throughput using realistic dataset sizes, not only tiny fixtures.  
  `BLOCKED` — requires production-scale data or multi-hour runs outside this build's budget
- [ ] **GAP05-MC25-011** — Test backups during active writes, partial backup upload, corrupted archive, key rotation, stale backup, and disaster-region restore.  
  `PARTIAL` — second-pass tag review: Only corruption; active writes, partial upload, key rotation, stale, region untested — evidence: test_backup_tamper_detected
- [ ] **GAP05-MC25-012** — Require periodic restore drills whose artifacts prove data integrity and successful safe rejoin.  
  `PARTIAL` — second-pass tag review: No periodic drill artifact — evidence: test_backup_verify_restore_fenced_until_sync

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC25-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC25-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC25-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC25-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC25-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC25-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC25-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC25-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25
- [ ] **GAP05-MC25-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc25

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 26. Observability package

**Priority:** P1  
**Requirement family:** `GAP05-MC26`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC26-001** — Define a metric taxonomy covering correctness, durability, convergence, performance, capacity, security-relevant anomalies, and dependency health.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No SLO definitions agreed; no dashboards.
- [ ] **GAP05-MC26-002** — Instrument apply outcomes by stable reason class: accepted, duplicate, superseded, concurrent, quarantined, rejected, and resolved.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_metrics_bounded_and_exposed
- [ ] **GAP05-MC26-003** — Measure active frontier width, quarantine depth/bytes/age, vector size, dedupe size, WAL lag, checkpoint age, and anti-entropy lag.  
  `PARTIAL` — second-pass tag review: Only frontier width/quarantine depth; bytes/age, vector, dedupe, WAL lag, checkpoint age, AE lag missing — evidence: test_metrics_bounded_and_exposed
- [ ] **GAP05-MC26-004** — Measure conflict resolution latency, policy failures, persistence latency, transport backpressure, recovery duration, and membership propagation.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_rejections_observable
- [ ] **GAP05-MC26-005** — Use bounded-cardinality labels; never label metrics directly with arbitrary keys, write IDs, raw tenant IDs, or replica-controlled data.  
  `PARTIAL` — second-pass tag review: Series cap only; no check that keys/IDs are never labels — evidence: test_metrics_bounded_and_exposed
- [ ] **GAP05-MC26-006** — Define SLI/SLO calculations and alert thresholds for availability, durability risk, convergence lag, and saturation.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No SLO definitions agreed; no dashboards.
- [ ] **GAP05-MC26-007** — Export runtime/process/storage metrics needed to diagnose lock contention, memory growth, file-descriptor pressure, and queue saturation.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No SLO definitions agreed; no dashboards.
- [ ] **GAP05-MC26-008** — Separate per-tenant diagnostics from global metrics when cardinality or privacy requires an authenticated query path.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC26-009** — Document metric units, types, monotonicity, aggregation, and reset behavior.  
  `NOT_EVIDENCED` — second-pass tag review: No metric documentation of units/types/reset asserted — evidence: test_metrics_bounded_and_exposed
- [ ] **GAP05-MC26-010** — Add dashboard reference panels for normal operation, partition recovery, conflict flood, storage pressure, and restore.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No SLO definitions agreed; no dashboards.
- [ ] **GAP05-MC26-011** — Test metric emission during failures and verify instrumentation itself cannot cause unbounded allocation or deadlock.  
  `PARTIAL` — second-pass tag review: No emission during failures or deadlock test; only series cap — evidence: test_metrics_bounded_and_exposed
- [ ] **GAP05-MC26-012** — Require release evidence that critical failure modes have an observable signal and actionable threshold.  
  `PARTIAL` — second-pass tag review: Single rejection counter; no failure-mode coverage or thresholds — evidence: test_rejections_observable

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC26-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC26-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26
- [ ] **GAP05-MC26-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC26-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 2}
- [ ] **GAP05-MC26-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC26-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC26-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC26-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC26-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc26

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 27. Structured logs/tracing

**Priority:** P1  
**Requirement family:** `GAP05-MC27`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC27-001** — Define a structured event schema with timestamp, severity, event code, component, authenticated replica, membership epoch, operation/write ID, trace ID, and redacted tenant/key references.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_log_redaction_injection_sampling
- [ ] **GAP05-MC27-002** — Use stable event codes rather than relying on free-form message text for automation and alert correlation.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_rejections_observable
- [ ] **GAP05-MC27-003** — Propagate distributed trace context across transport, model apply, persistence, policy, anti-entropy, and operator actions.  
  `PARTIAL` — second-pass tag review: Trace only linked log and audit; transport, persistence, policy, AE, operator not — evidence: test_trace_correlation
- [ ] **GAP05-MC27-004** — Treat incoming trace headers as correlation data only; never use them for authentication or authorization.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_trace_correlation
- [ ] **GAP05-MC27-005** — Define redaction/tokenization rules for values, credentials, keys, certificates, tenant identifiers, and sensitive provenance.  
  `PARTIAL` — second-pass tag review: Only value and sig redacted; credentials, certs, tenant IDs, provenance not — evidence: test_log_redaction_injection_sampling
- [ ] **GAP05-MC27-006** — Prevent log injection by encoding untrusted strings as structured fields rather than concatenated message fragments.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_log_redaction_injection_sampling
- [ ] **GAP05-MC27-007** — Apply sampling that preserves errors, security anomalies, and rare correctness events even under high throughput.  
  `PARTIAL` — second-pass tag review: Only error-level preservation; security anomalies/rare events not asserted — evidence: test_log_redaction_injection_sampling
- [ ] **GAP05-MC27-008** — Correlate conflict lifecycle events from initial concurrent apply through quarantine and final resolution.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_trace_correlation
- [ ] **GAP05-MC27-009** — Include persistence sequence/checkpoint references needed to investigate crash-recovery incidents.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No OpenTelemetry export.
- [ ] **GAP05-MC27-010** — Set log volume budgets and rotation/forwarding backpressure behavior so logging cannot exhaust local storage.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No OpenTelemetry export.
- [ ] **GAP05-MC27-011** — Test malformed Unicode, oversized fields, secret scanning, trace fan-out, collector outage, and high-volume conflict storms.  
  `PARTIAL` — second-pass tag review: Oversized fields, secret scan, trace fan-out, collector outage, storms untested — evidence: test_log_redaction_injection_sampling
- [ ] **GAP05-MC27-012** — Require an incident-reconstruction exercise proving one write/conflict can be followed across all participating subsystems without exposing protected payload data.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC27-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC27-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC27-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC27-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC27-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC27-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC27-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC27-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27
- [ ] **GAP05-MC27-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC27-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc27

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 28. Health/readiness endpoints

**Priority:** P1  
**Requirement family:** `GAP05-MC28`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC28-001** — Separate liveness from readiness; a process may be live while unsafe to accept replication traffic.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_health_readiness
- [ ] **GAP05-MC28-002** — Report durable-store availability, WAL/checkpoint health, recovery mode, corruption flags, and persistence backlog.  
  `PARTIAL` — second-pass tag review: Durable-store availability, WAL health, corruption flags, persistence backlog not asserted — evidence: test_health_readiness
- [ ] **GAP05-MC28-003** — Report authenticated identity readiness, key/trust-store status, membership epoch, configuration generation, and schema compatibility.  
  `PARTIAL` — second-pass tag review: Identity readiness, trust-store status, config generation not asserted — evidence: test_health_readiness
- [ ] **GAP05-MC28-004** — Report transport dependency health, anti-entropy lag, quarantine pressure, policy adapter availability, and resource saturation.  
  `PARTIAL` — second-pass tag review: Transport health, anti-entropy lag, policy adapter availability not asserted — evidence: test_health_readiness
- [ ] **GAP05-MC28-005** — Fail readiness when invariant-preserving operation cannot be guaranteed, not merely when a dependency is slow.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_health_readiness
- [ ] **GAP05-MC28-006** — Use reason codes and bounded diagnostic detail suitable for automation without leaking tenant data or secrets.  
  `PARTIAL` — second-pass tag review: Readiness reason codes not asserted — evidence: test_health_readiness
- [ ] **GAP05-MC28-007** — Authenticate detailed diagnostic endpoints; expose only minimal non-sensitive liveness information unauthenticated if required.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC28-008** — Define startup readiness progression through identity, durable recovery, membership load, schema validation, and peer synchronization stages.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No HTTP server/authentication; no startup progression states.
- [ ] **GAP05-MC28-009** — Define graceful shutdown/draining state so orchestration stops new traffic before termination.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No HTTP server/authentication; no startup progression states.
- [ ] **GAP05-MC28-010** — Include monotonic generation or startup ID to distinguish stale cached health responses.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC28-011** — Test dependency failures, corrupt checkpoint, missing keys, stale membership, policy outage, disk-full pressure, and recovering state.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_health_readiness
- [ ] **GAP05-MC28-012** — Require deployment gates to wait for the documented readiness condition rather than process-start completion.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC28-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC28-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc28
- [ ] **GAP05-MC28-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc28
- [ ] **GAP05-MC28-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc28
- [ ] **GAP05-MC28-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc28
- [ ] **GAP05-MC28-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc28
- [ ] **GAP05-MC28-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC28-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC28-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC28-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC28-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc28
- [ ] **GAP05-MC28-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC28-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC28-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC28-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC28-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC28-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc28
- [ ] **GAP05-MC28-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc28

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 29. Admission control/backpressure

**Priority:** P1  
**Requirement family:** `GAP05-MC29`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC29-001** — Define independent budgets for writes, replication frames, conflict creation, policy resolutions, anti-entropy repair, operator exports, and recovery bursts.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_admission_hot_key_and_tenant_isolation
- [ ] **GAP05-MC29-002** — Apply admission checks before expensive parsing, decompression, signature verification batches, large allocations, or lock acquisition where possible.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC29-003** — Use bounded queues with explicit overload outcomes rather than unbounded buffering.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_admission_bounded_metadata; test_backpressure_bounded_queues
- [ ] **GAP05-MC29-004** — Enforce per-tenant, per-peer, per-key/partition, and global limits to contain noisy-neighbor behavior.  
  `PARTIAL` — second-pass tag review: Per-peer and global limits not exercised — evidence: test_admission_hot_key_and_tenant_isolation
- [ ] **GAP05-MC29-005** — Detect hot-key conflict floods and apply targeted throttling without unnecessarily blocking unrelated keys.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_admission_hot_key_and_tenant_isolation
- [ ] **GAP05-MC29-006** — Coordinate backpressure with transport flow control so overload propagates to senders instead of shifting memory growth between layers.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_backpressure_bounded_queues
- [ ] **GAP05-MC29-007** — Define retry-after/backoff guidance and stable overload reason codes for cooperating peers.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_admission_hot_key_and_tenant_isolation
- [ ] **GAP05-MC29-008** — Reserve capacity for correctness-critical control traffic such as membership fencing and recovery metadata.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No reserved control-traffic class; buckets tick logically, not by time.
- [ ] **GAP05-MC29-009** — Expose rejection/throttle counts, queue wait time, queue depth, budget utilization, and top pressure sources.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No reserved control-traffic class; buckets tick logically, not by time.
- [ ] **GAP05-MC29-010** — Prevent admission-control metadata itself from becoming a high-cardinality or memory-exhaustion vector.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_admission_bounded_metadata
- [ ] **GAP05-MC29-011** — Test burst traffic, replay storms, many slow peers, one pathological tenant, conflict floods, and recovery under saturation.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No reserved control-traffic class; buckets tick logically, not by time.
- [ ] **GAP05-MC29-012** — Require acceptance evidence that sustained overload produces bounded resource usage and graceful throughput reduction without invariant violation.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_admission_hot_key_and_tenant_isolation

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC29-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC29-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC29-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC29-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC29-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC29-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC29-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC29-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29
- [ ] **GAP05-MC29-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc29

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 30. Resource limits

**Priority:** P1  
**Requirement family:** `GAP05-MC30`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC30-001** — Set explicit maximum serialized and decoded key/value sizes and validate before allocation/copy wherever possible.  
  `PARTIAL` — second-pass tag review: Only key size; value and decoded sizes not tested — evidence: test_limits_boundaries
- [ ] **GAP05-MC30-002** — Set maximum vector entries, identifier lengths, metadata fields, provenance size, batch count/bytes, and nesting depth.  
  `PARTIAL` — second-pass tag review: Identifier, metadata, provenance, batch, nesting limits not tested — evidence: test_limits_boundaries
- [ ] **GAP05-MC30-003** — Set per-key unresolved sibling/quarantine bounds with invariant-preserving overflow handling.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No decompression (no compression implemented).
- [ ] **GAP05-MC30-004** — Set per-tenant and global WAL, checkpoint, quarantine, audit, dedupe, and in-memory cache budgets.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No decompression (no compression implemented).
- [ ] **GAP05-MC30-005** — Define maximum concurrent sessions, reconciliation jobs, policy calls, restore jobs, and administrative exports.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No decompression (no compression implemented).
- [ ] **GAP05-MC30-006** — Centralize limit definitions with versioned configuration and reject unsafe/contradictory combinations at startup.  
  `PARTIAL` — second-pass tag review: Versioned limit configuration not asserted — evidence: test_limits_boundaries
- [ ] **GAP05-MC30-007** — Use overflow-safe arithmetic for size/count calculations and protect against integer truncation across languages.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_numeric_and_vector_edges
- [ ] **GAP05-MC30-008** — Apply decompression and parsing expansion ratios to prevent small inputs from causing disproportionate memory/CPU use.  
  `BLOCKED` — no compression is implemented, so compression-specific checks cannot run
- [ ] **GAP05-MC30-009** — Define what happens when each limit is reached: reject, throttle, spill durably, quarantine, or degrade readiness.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No decompression (no compression implemented).
- [ ] **GAP05-MC30-010** — Expose current configured limits plus utilization and limit-hit reason metrics.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No decompression (no compression implemented).
- [ ] **GAP05-MC30-011** — Boundary-test every limit at N-1/N/N+1 and fuzz extreme numeric encodings.  
  `PARTIAL` — second-pass tag review: Only key limit at N-1/N/N+1 — evidence: test_limits_boundaries; test_numeric_and_vector_edges
- [ ] **GAP05-MC30-012** — Require capacity tests showing configured maxima keep CPU, memory, disk, and latency within documented safety envelopes.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC30-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC30-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc30
- [ ] **GAP05-MC30-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc30
- [ ] **GAP05-MC30-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc30
- [ ] **GAP05-MC30-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc30
- [ ] **GAP05-MC30-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc30
- [ ] **GAP05-MC30-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC30-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc30
- [ ] **GAP05-MC30-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC30-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC30-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC30-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC30-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 2}
- [ ] **GAP05-MC30-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC30-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC30-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc30
- [ ] **GAP05-MC30-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC30-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc30

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 31. Time-independent expiry semantics

**Priority:** P1  
**Requirement family:** `GAP05-MC31`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC31-001** — Decide which lifecycle decisions, if any, may depend on wall clock versus causal state, durable sequence, or explicitly replicated logical time.  
  `PARTIAL` — second-pass tag review: Only EpochExpiry unit and core grep; no documented decision set — evidence: test_expiry_is_logical
- [ ] **GAP05-MC31-002** — Do not use local wall-clock ordering to determine causal winner/loser semantics.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_expiry_is_logical
- [ ] **GAP05-MC31-003** — Define TTL start point unambiguously: creation, acceptance, policy decision, replicated logical timestamp, or another authoritative event.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_expiry_is_logical
- [ ] **GAP05-MC31-004** — Specify behavior under clock skew, clock rollback, NTP step, leap seconds, suspended hosts, and restored snapshots.  
  `PARTIAL` — second-pass tag review: Clock skew, rollback, NTP step, leap seconds, suspend, restored snapshots untested — evidence: test_expiry_is_logical
- [ ] **GAP05-MC31-005** — Replicate expiration intent as data when expiry must converge across replicas rather than letting each node infer independently from local time.  
  `BLOCKED` — requires independent human review, approval or an exercise with people
- [ ] **GAP05-MC31-006** — Ensure expired data cannot be resurrected by delayed peers if policy intends permanent expiry/deletion semantics.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Expiry intent is not replicated as data.
- [ ] **GAP05-MC31-007** — Coordinate expiration with tombstones, backups, anti-entropy horizon, audit retention, and dedupe.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Expiry intent is not replicated as data.
- [ ] **GAP05-MC31-008** — Use monotonic clocks for local duration measurement and wall clocks only where absolute civil time is semantically required.  
  `BLOCKED` — no graphical UI exists (read-only CLI only) — evidence: test_expiry_is_logical
- [ ] **GAP05-MC31-009** — Record the authority/source of any time used in a state-changing expiry decision.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Expiry intent is not replicated as data.
- [ ] **GAP05-MC31-010** — Expose upcoming/overdue expiry backlogs and clock-health anomalies without embedding time into causal comparison.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Expiry intent is not replicated as data.
- [ ] **GAP05-MC31-011** — Test large skew, backwards clock movement, long partitions, restore after TTL, and expiry during membership changes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Expiry intent is not replicated as data.
- [ ] **GAP05-MC31-012** — Require acceptance evidence that replicas converge on expiry outcomes under documented clock-error assumptions.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC31-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC31-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc31
- [ ] **GAP05-MC31-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc31
- [ ] **GAP05-MC31-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc31
- [ ] **GAP05-MC31-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc31
- [ ] **GAP05-MC31-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc31
- [ ] **GAP05-MC31-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC31-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC31-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC31-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC31-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC31-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC31-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC31-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC31-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC31-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc31
- [ ] **GAP05-MC31-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC31-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc31

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 32. Split-brain fencing

**Priority:** P1  
**Requirement family:** `GAP05-MC32`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC32-001** — Define a monotonically advancing membership epoch, lease generation, or fencing token authoritative for write admission.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_cas_and_chain
- [ ] **GAP05-MC32-002** — Include the fencing context in provenance and validate it on every state-mutating replicated write.  
  `PARTIAL` — second-pass tag review: check_authorship unit only; not validated on every replicated write — evidence: test_fencing_rules
- [ ] **GAP05-MC32-003** — Reject writes from replicas/controllers whose fencing token is older than the currently active generation.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_fencing_rules
- [ ] **GAP05-MC32-004** — Ensure failover grants a strictly newer fencing generation before replacement writers are allowed to mutate state.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_rollback_keeps_retirements
- [ ] **GAP05-MC32-005** — Persist fencing state durably so restart cannot revert to an obsolete authority generation.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No leases; epoch distribution to all nodes is out of scope.
- [ ] **GAP05-MC32-006** — Bind credentials/authorization to fencing where possible so a network-isolated old primary cannot continue indefinitely with otherwise valid credentials.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No leases; epoch distribution to all nodes is out of scope.
- [ ] **GAP05-MC32-007** — Define lease expiry using a trusted mechanism and avoid relying on unsynchronized wall clocks for safety-critical comparisons.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No leases; epoch distribution to all nodes is out of scope.
- [ ] **GAP05-MC32-008** — Integrate fencing with membership removal, restore/reseed, counter allocation, policy control, and transport session establishment.  
  `PARTIAL` — second-pass tag review: Restore/reseed, counter, policy, session integration not tested — evidence: test_removed_replica_cannot_write_after_fencing
- [ ] **GAP05-MC32-009** — Audit all fencing generation changes and stale-writer rejection events.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No leases; epoch distribution to all nodes is out of scope.
- [ ] **GAP05-MC32-010** — Expose current fencing generation and rejection counts in health/diagnostics.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No leases; epoch distribution to all nodes is out of scope.
- [ ] **GAP05-MC32-011** — Test network split, dual-controller startup, delayed old writes, failover/failback, restored old disk, and paused-process resume.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No leases; epoch distribution to all nodes is out of scope.
- [ ] **GAP05-MC32-012** — Require acceptance evidence that at most the currently fenced-in authority can create newly accepted writes during split-brain scenarios.  
  `PARTIAL` — second-pass tag review: No split-brain scenario, only rule unit test — evidence: test_fencing_rules

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC32-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC32-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC32-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC32-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC32-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC32-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC32-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC32-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC32-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32
- [ ] **GAP05-MC32-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc32

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

## P1 — Test and certification gaps

### 33. Fuzz tests

**Priority:** P1  
**Requirement family:** `GAP05-MC33`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC33-001** — Build fuzz targets for wire decoders, persisted record decoders, vector parsing/comparison, provenance parsing, configuration parsing, and administrative request parsing.  
  `PARTIAL` — second-pass tag review: Only wire decoders; persisted, config, admin parsers not fuzzed — evidence: test_binary_and_frame_fuzz; test_json_decoder_fuzz
- [ ] **GAP05-MC33-002** — Seed corpora with valid minimal, valid maximal, legacy-version, truncated, corrupted, and adversarial fixtures.  
  `PARTIAL` — second-pass tag review: Corpus categories (min, max, legacy, truncated) not asserted — evidence: test_published_corpus
- [ ] **GAP05-MC33-003** — Exercise oversized vectors, duplicate map keys/fields, invalid Unicode, embedded NULs, extreme integers, negative-equivalent encodings, and deep nesting.  
  `PARTIAL` — second-pass tag review: Oversized vectors, extreme ints, negative-equivalent encodings not in cited tests — evidence: test_duplicate_keys_unicode_extremes; test_json_decoder_fuzz
- [ ] **GAP05-MC33-004** — Fuzz schema downgrade/upgrade negotiation and unknown mandatory fields.  
  `PARTIAL` — second-pass tag review: Only schema id strings; negotiation and unknown mandatory fields not fuzzed — evidence: test_downgrade_fuzz
- [ ] **GAP05-MC33-005** — Fuzz compressed payloads with expansion-ratio guards and malformed compression streams.  
  `BLOCKED` — no compression is implemented, so compression-specific checks cannot run
- [ ] **GAP05-MC33-006** — Fuzz restored-state invariant validation including duplicate causal events and causally dominated frontier members.  
  `PARTIAL` — second-pass tag review: Single case, not fuzzed; duplicate events absent — evidence: test_restore_rejects_dominated_frontier
- [ ] **GAP05-MC33-007** — Assert no crash, hang, unbounded memory growth, undefined behavior, or silent invariant relaxation for malformed inputs.  
  `PARTIAL` — second-pass tag review: Only no-crash; hang, memory growth not asserted — evidence: test_json_decoder_fuzz
- [ ] **GAP05-MC33-008** — Treat resource exhaustion and timeout behavior as testable outcomes with explicit bounds.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_json_decoder_fuzz
- [ ] **GAP05-MC33-009** — Persist minimized crashing inputs as permanent regression fixtures.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_published_corpus
- [ ] **GAP05-MC33-010** — Run fuzzers under memory/error instrumentation appropriate to the implementation language.  
  `BLOCKED` — requires native fuzzing/sanitizer tooling absent from this build
- [ ] **GAP05-MC33-011** — Track execution time, corpus growth, unique paths, and regressions in CI or scheduled security testing.  
  `BLOCKED` — requires native fuzzing/sanitizer tooling absent from this build
- [ ] **GAP05-MC33-012** — Require a defined minimum fuzzing budget and zero unresolved high-severity crashes before release.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC33-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC33-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC33-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 6}
- [ ] **GAP05-MC33-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC33-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC33-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC33-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `PARTIAL` — generic design record shared by the test/certification components

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 34. Property-based causal tests

**Priority:** P1  
**Requirement family:** `GAP05-MC34`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC34-001** — Generate arbitrary replica sets, write vectors, deliveries, duplicates, partitions, and conflict resolutions within bounded histories.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_convergence_maximality_replay; test_node_level_random_multi_replica
- [ ] **GAP05-MC34-002** — Assert convergence across all sampled delivery orders for the same logical event set.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_convergence_maximality_replay
- [ ] **GAP05-MC34-003** — Assert the active/unresolved frontier contains only causally maximal relevant events according to the model specification.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_convergence_maximality_replay
- [ ] **GAP05-MC34-004** — Assert causally dominated writes cannot displace a newer frontier member.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_convergence_maximality_replay
- [ ] **GAP05-MC34-005** — Assert exact duplicate replay is idempotent and does not alter convergence state.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_convergence_maximality_replay
- [ ] **GAP05-MC34-006** — Assert equivocation for the same causal identity but different payload/provenance is detected according to policy.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_equivocation_detected_and_audited
- [ ] **GAP05-MC34-007** — Generate conflict overflow beyond `max_siblings` and prove deterministic retained/quarantined partition independent of arrival order.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_convergence_maximality_replay
- [ ] **GAP05-MC34-008** — Assert conflict resolution dominates all targeted active and quarantined events before clearing them.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_end_to_end_resolution_dominates_quarantine; test_resolution_dominates_all
- [ ] **GAP05-MC34-009** — Include membership epochs, removed replicas, vector compaction, tombstones, and CRDT types as those components become available.  
  `PARTIAL` — second-pass tag review: No epochs, removed replicas, compaction, CRDT types in node test — evidence: test_node_level_random_multi_replica
- [ ] **GAP05-MC34-010** — Shrink failing histories to minimal counterexamples and save them as deterministic regression tests.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC34-011** — Run property suites under multiple random seeds and runtime optimization modes.  
  `PARTIAL` — second-pass tag review: No runtime optimization modes — evidence: test_convergence_maximality_replay
- [ ] **GAP05-MC34-012** — Require published invariant coverage showing which formal/model invariants have executable property tests.  
  `BLOCKED` — no graphical UI exists (read-only CLI only) — evidence: test_exhaustive_bounded_invariants

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC34-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC34-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC34-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 6}
- [ ] **GAP05-MC34-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC34-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC34-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC34-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `PARTIAL` — generic design record shared by the test/certification components

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 35. Process-crash fault injection

**Priority:** P1  
**Requirement family:** `GAP05-MC35`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC35-001** — Enumerate every durability boundary in WAL append, fsync, checkpoint publish, dedupe update, audit append, configuration activation, and resolution commit.  
  `PARTIAL` — second-pass tag review: No dedupe update, config activation, resolution commit boundaries — evidence: test_wal_durable_write_is_audited_after_crash; test_crash_matrix_no_acked_loss
- [ ] **GAP05-MC35-002** — Inject abrupt process termination before, during, and after each boundary.  
  `PARTIAL` — second-pass tag review: Not before/during/after every boundary — evidence: test_wal_durable_write_is_audited_after_crash; test_crash_matrix_no_acked_loss
- [ ] **GAP05-MC35-003** — Restart using only durable artifacts; prohibit test harness repair of state that production recovery would not have.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_crash_matrix_no_acked_loss
- [ ] **GAP05-MC35-004** — Compare recovered accepted writes and unresolved frontier against the documented acknowledgement/durability contract.  
  `PARTIAL` — second-pass tag review: Unresolved frontier not compared — evidence: test_crash_matrix_no_acked_loss
- [ ] **GAP05-MC35-005** — Verify partial/torn tail records are detected and handled without discarding prior valid records.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_torn_tail_truncated_prior_kept
- [ ] **GAP05-MC35-006** — Exercise repeated crash loops rather than only one crash/restart cycle.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_crash_matrix_no_acked_loss
- [ ] **GAP05-MC35-007** — Inject disk-full, fsync error, rename failure, permission loss, and checksum corruption in addition to process death.  
  `PARTIAL` — second-pass tag review: Only checksum corruption; disk-full, fsync, rename, permission untested — evidence: test_mid_log_corruption_fails_closed
- [ ] **GAP05-MC35-008** — Verify readiness remains false while recovery cannot prove a safe state.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC35-009** — Correlate crash injection points with durable sequence/checkpoint IDs for deterministic reproduction.  
  `NOT_EVIDENCED` — second-pass tag review: No correlation to sequence/checkpoint IDs — evidence: test_crash_matrix_no_acked_loss
- [ ] **GAP05-MC35-010** — Measure recovery time and scan/replay amplification at realistic state sizes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC35-011** — Run tests on each supported storage/filesystem class when semantics differ materially.  
  `BLOCKED` — only one filesystem/hardware class available
- [ ] **GAP05-MC35-012** — Require zero silent acknowledged-write loss across the certified crash-injection matrix.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_crash_matrix_no_acked_loss

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC35-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC35-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC35-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC35-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC35-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC35-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC35-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `PARTIAL` — generic design record shared by the test/certification components

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 36. Network partition/reconnect integration tests

**Priority:** P1  
**Requirement family:** `GAP05-MC36`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC36-001** — Run multiple independent replica processes rather than simulating all replicas in one in-memory object.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_three_os_processes_partition_duplicate_reorder_restart
- [ ] **GAP05-MC36-002** — Inject full and asymmetric partitions, latency, jitter, duplication, reordering, frame loss, and connection resets.  
  `PARTIAL` — second-pass tag review: No asymmetric partitions, jitter, or connection resets — evidence: test_three_os_processes_partition_duplicate_reorder_restart; test_full_partition_then_heal; test_lossy_reordering_duplicating_link_converges
- [ ] **GAP05-MC36-003** — Continue local writes on permitted sides of the partition according to fencing/membership policy.  
  `PARTIAL` — second-pass tag review: Writes not made during partition on permitted side per fencing — evidence: test_three_os_processes_partition_duplicate_reorder_restart
- [ ] **GAP05-MC36-004** — Verify concurrent writes remain explicitly unresolved/quarantined rather than being delivery-order winners.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_converge_after_divergence; test_three_os_processes_partition_duplicate_reorder_restart; test_node_level_random_multi_replica
- [ ] **GAP05-MC36-005** — Reconnect peers and exercise both normal replication replay and anti-entropy repair.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_converge_after_divergence; test_three_os_processes_partition_duplicate_reorder_restart; test_full_partition_then_heal
- [ ] **GAP05-MC36-006** — Validate dedupe under repeated resend after uncertain acknowledgements.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_three_os_processes_partition_duplicate_reorder_restart; test_lossy_reordering_duplicating_link_converges
- [ ] **GAP05-MC36-007** — Include transport reconnect during schema upgrade and membership change.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC36-008** — Verify removed/fenced replicas remain unable to author accepted writes when connectivity returns.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_removed_replica_cannot_write_after_fencing
- [ ] **GAP05-MC36-009** — Measure time-to-convergence and bytes transferred after partitions of different duration.  
  `PARTIAL` — second-pass tag review: Single partition duration; measurement recorded, not asserted; bytes not — evidence: test_full_partition_then_heal
- [ ] **GAP05-MC36-010** — Capture traces/audit sufficient to reconstruct the partition conflict lifecycle.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC36-011** — Repeat scenarios with crash/restart on one or more sides before healing.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_three_os_processes_partition_duplicate_reorder_restart
- [ ] **GAP05-MC36-012** — Require acceptance evidence that all supported partition scenarios converge or fail safely with an explicit unresolved state.  
  `PARTIAL` — second-pass tag review: Asymmetric and other partition scenarios not covered — evidence: test_three_os_processes_partition_duplicate_reorder_restart; test_full_partition_then_heal

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC36-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC36-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC36-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 6}
- [ ] **GAP05-MC36-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC36-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC36-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC36-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `PARTIAL` — generic design record shared by the test/certification components

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 37. Membership churn tests

**Priority:** P1  
**Requirement family:** `GAP05-MC37`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC37-001** — Generate repeated join, seed, activate, drain, remove, fence, and reseed sequences while writes continue.  
  `PARTIAL` — second-pass tag review: Single join; no repeated drain/remove/fence/reseed sequences — evidence: test_join_during_writes_and_rejoin_via_sync
- [ ] **GAP05-MC37-002** — Combine membership changes with concurrent writes on hot keys and multiple tenants.  
  `PARTIAL` — second-pass tag review: No hot keys or multiple tenants during churn — evidence: test_join_during_writes_and_rejoin_via_sync
- [ ] **GAP05-MC37-003** — Verify joining replicas cannot author writes before completing required seed/catch-up and activation.  
  `BLOCKED` — no graphical UI exists (read-only CLI only) — evidence: test_join_during_writes_and_rejoin_via_sync
- [ ] **GAP05-MC37-004** — Verify removed replicas are rejected immediately according to the authoritative epoch/fencing rules.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_removed_replica_cannot_write_after_fencing
- [ ] **GAP05-MC37-005** — Attempt replica-ID reuse and confirm incarnation/epoch protections prevent history ambiguity.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_reseed_creates_new_incarnation
- [ ] **GAP05-MC37-006** — Exercise vector compaction across retired replicas and later restore of stale data referencing them.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC37-007** — Crash nodes during membership transition and prove restart resumes or rolls back deterministically.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC37-008** — Partition a replica during removal and reconnect it after the fleet has advanced epochs.  
  `BLOCKED` — requires production-scale data or multi-hour runs outside this build's budget
- [ ] **GAP05-MC37-009** — Test rapid successive configuration generations and stale controller updates.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_concurrent_controllers_one_winner
- [ ] **GAP05-MC37-010** — Measure state-transfer and convergence cost under realistic replica counts.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC37-011** — Verify audit/observability exposes every lifecycle transition and rejection reason.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC37-012** — Require zero acceptance of stale-incarnation writes across the certified churn matrix.  
  `PARTIAL` — second-pass tag review: Single scenario, not a churn matrix — evidence: test_removed_replica_cannot_write_after_fencing

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC37-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC37-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC37-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC37-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC37-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC37-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC37-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `PARTIAL` — generic design record shared by the test/certification components

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 38. Security tests

**Priority:** P1  
**Requirement family:** `GAP05-MC38`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC38-001** — Attempt replica identity spoofing at payload, transport, certificate/workload identity, and membership-mapping layers.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_authenticated_session_maps_to_one_replica; test_expired_revoked_untrusted_unknown; test_replay_and_channel_binding
- [ ] **GAP05-MC38-002** — Attempt forged, truncated, algorithm-downgraded, replayed, and field-substituted provenance signatures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_replay_and_channel_binding; test_malformed_and_downgrade; test_single_bit_mutation_detected
- [ ] **GAP05-MC38-003** — Attempt monotonic counter rollback, counter reuse, extreme counter jumps, and cross-replica counter substitution.  
  `PARTIAL` — second-pass tag review: Cross-replica counter substitution and rollback not tested — evidence: test_guard_jump_rollback
- [ ] **GAP05-MC38-004** — Replay valid writes across tenants, environments, membership epochs, and restored nodes.  
  `PARTIAL` — second-pass tag review: Only cross-tenant; environments, epochs, restored nodes absent — evidence: test_cross_tenant_replay
- [ ] **GAP05-MC38-005** — Attempt audit-chain modification, truncation, record insertion, segment replacement, and signing-key rollover confusion.  
  `PARTIAL` — second-pass tag review: No record insertion, segment replacement, or signing-key rollover confusion — evidence: test_tamper_insert_delete_truncate
- [ ] **GAP05-MC38-006** — Test authorization privilege escalation, confused-deputy paths, stale cached grants, and break-glass controls.  
  `PARTIAL` — second-pass tag review: Confused-deputy and privilege escalation paths not in cited tests — evidence: test_revoked_grant_takes_effect_immediately; test_wildcards_only_break_glass
- [ ] **GAP05-MC38-007** — Test malformed wire/persistence inputs for parser abuse, memory exhaustion, decompression bombs, and algorithmic complexity attacks.  
  `PARTIAL` — second-pass tag review: No memory exhaustion, decompression bomb, complexity attack checks — evidence: test_binary_and_frame_fuzz; test_json_decoder_fuzz
- [ ] **GAP05-MC38-008** — Attempt stale/removed replica writes after fencing and during split-brain.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_removed_replica_cannot_write_after_fencing
- [ ] **GAP05-MC38-009** — Verify secret redaction in logs, metrics, traces, crash reports, exports, and operator APIs.  
  `PARTIAL` — second-pass tag review: Only logs; metrics, traces, crash reports, exports, APIs not checked — evidence: test_log_redaction_injection_sampling
- [ ] **GAP05-MC38-010** — Test key rotation failure, revoked key use, unavailable KMS/key service, and old encrypted checkpoint recovery.  
  `PARTIAL` — second-pass tag review: Rotation failure, KMS unavailable, old checkpoint recovery untested — evidence: test_encrypted_wal_recovers_and_fails_closed_without_key; test_wrong_namespace_and_corruption
- [ ] **GAP05-MC38-011** — Map findings to a threat model and severity/remediation SLA with regression tests for every fixed issue.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC38-012** — Require independent security review/penetration evidence before declaring P0 production readiness.  
  `BLOCKED` — requires independent human review, approval or an exercise with people

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC38-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC38-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC38-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 18}
- [ ] **GAP05-MC38-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"note": "fault/dependency-failure tests tagged for this component"}
- [ ] **GAP05-MC38-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC38-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC38-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `PARTIAL` — generic design record shared by the test/certification components

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 39. Soak/burst/fleet benchmarks

**Priority:** P1  
**Requirement family:** `GAP05-MC39`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC39-001** — Define representative workload profiles for normal replication, hot-key conflicts, replay bursts, partition healing, anti-entropy, and restore.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC39-002** — Benchmark p50/p95/p99/max apply latency and end-to-end convergence latency under each profile.  
  `PARTIAL` — second-pass tag review: Only p99 keys; p50/p95/max, convergence latency absent — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC39-003** — Measure sustained and burst throughput by writes/sec, bytes/sec, conflicts/sec, and repair records/sec.  
  `PARTIAL` — second-pass tag review: Only burst writes/s; bytes/s, conflicts/s, repair/s absent — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC39-004** — Track memory, CPU, GC/runtime overhead, lock contention, queue growth, vector growth, WAL growth, and checkpoint cost over long runs.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC39-005** — Include realistic value sizes, vector sizes, replica counts, tenant counts, and conflict distributions.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC39-006** — Run multi-hour/day soak tests sufficient to reveal leaks and unbounded metadata growth.  
  `BLOCKED` — requires production-scale data or multi-hour runs outside this build's budget
- [ ] **GAP05-MC39-007** — Measure quarantine pressure behavior and recovery time after conflict storms.  
  `PARTIAL` — second-pass tag review: Recovery time after storms not measured — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC39-008** — Benchmark crash recovery and restore at several durable-state sizes.  
  `PARTIAL` — second-pass tag review: Single recovery rate; not several state sizes — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC39-009** — Test fleet synchronization after long partition and rolling upgrade.  
  `BLOCKED` — requires production-scale data or multi-hour runs outside this build's budget
- [ ] **GAP05-MC39-010** — Record hardware/runtime/storage environment so results are reproducible.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC39-011** — Set release regression thresholds and compare every release candidate against a pinned baseline.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC39-012** — Require capacity conclusions to include headroom assumptions and the first observed saturation bottleneck.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC39-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC39-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC39-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC39-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC39-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC39-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC39-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `PARTIAL` — generic design record shared by the test/certification components

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 40. Compatibility matrix

**Priority:** P1  
**Requirement family:** `GAP05-MC40`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC40-001** — Maintain a machine-readable matrix of supported runtime/Python versions, OS/platforms, storage formats, wire schemas, policy adapters, transport adapters, and neighboring subsystem versions.  
  `PARTIAL` — second-pass tag review: Only python, wire, crypto; OS, storage, adapters, neighbors not asserted — evidence: test_compat_matrix_runtime_check
- [ ] **GAP05-MC40-002** — Distinguish tested, supported, deprecated, experimental, and explicitly unsupported combinations.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_compat_matrix_runtime_check
- [ ] **GAP05-MC40-003** — Define N/N-1 compatibility guarantees for rolling upgrade and rollback.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC40-004** — Include cryptographic provider/library and storage/backend versions when behavior can affect correctness or security.  
  `PARTIAL` — second-pass tag review: Storage/backend versions not asserted — evidence: test_compat_matrix_runtime_check
- [ ] **GAP05-MC40-005** — Gate CI against every mandatory supported combination or an approved risk-based representative matrix.  
  `BLOCKED` — requires independent human review, approval or an exercise with people
- [ ] **GAP05-MC40-006** — Generate incompatibility errors early during startup/session negotiation rather than failing mid-replication.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_compat_matrix_runtime_check
- [ ] **GAP05-MC40-007** — Version the compatibility matrix with the release and include it in artifact metadata.  
  `PARTIAL` — second-pass tag review: Release version and artifact metadata not asserted in cited test — evidence: test_compat_matrix_runtime_check
- [ ] **GAP05-MC40-008** — Record known limitations and required migration steps for transitions between matrix cells.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC40-009** — Test mixed-version clusters under normal writes, conflicts, partitions, recovery, and membership changes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).
- [ ] **GAP05-MC40-010** — Retire unsupported combinations through an explicit deprecation process with dates and migration guidance.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC40-011** — Verify documentation, packaging metadata, and runtime checks agree with the same matrix source.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_version_consistency
- [ ] **GAP05-MC40-012** — Require release approval to include a completed compatibility test report for all mandatory cells.  
  `BLOCKED` — requires independent human review, approval or an exercise with people

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC40-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC40-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC40-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 2}
- [ ] **GAP05-MC40-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC40-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC40-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `PARTIAL` — generic design record shared by the test/certification components
- [ ] **GAP05-MC40-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `PARTIAL` — generic design record shared by the test/certification components

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

## P2 — Operability and scale maturity

### 41. Hot-key sharding/partitioning strategy

**Priority:** P2  
**Requirement family:** `GAP05-MC41`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC41-001** — Profile contention and identify thresholds at which one key/state lock becomes a throughput or tail-latency bottleneck.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No partition-count migration; single process only.
- [ ] **GAP05-MC41-002** — Define deterministic key-to-partition mapping including tenant/environment namespace and a versioned hash/routing algorithm.  
  `PARTIAL` — second-pass tag review: Only _shard(x) repeatability; tenant namespace and versioned hash not asserted — evidence: test_unrelated_keys_scale_single_key_semantics_unchanged
- [ ] **GAP05-MC41-003** — Ensure all causally related mutations for a key are serialized through the correct authoritative partition.  
  `PARTIAL` — second-pass tag review: No same-key concurrent writers across threads — evidence: test_unrelated_keys_scale_single_key_semantics_unchanged
- [ ] **GAP05-MC41-004** — Support partition-count changes through an explicit migration protocol rather than silent hash remapping.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No partition-count migration; single process only.
- [ ] **GAP05-MC41-005** — Prevent one hot key from monopolizing worker pools, WAL batching, policy calls, or anti-entropy bandwidth.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No partition-count migration; single process only.
- [ ] **GAP05-MC41-006** — Use per-partition queues/locks while preserving global membership and durability invariants.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_reader_threads_see_coherent_views; test_unrelated_keys_scale_single_key_semantics_unchanged
- [ ] **GAP05-MC41-007** — Coordinate sharding with snapshots, WAL segmentation, dedupe indexes, metrics, backup/restore, and administrative APIs.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No partition-count migration; single process only.
- [ ] **GAP05-MC41-008** — Define cross-partition operations as unsupported or specify a transaction/coordinator model; do not imply atomicity accidentally.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No partition-count migration; single process only.
- [ ] **GAP05-MC41-009** — Expose hot-key/partition skew using privacy-safe identifiers or digests.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No partition-count migration; single process only.
- [ ] **GAP05-MC41-010** — Benchmark uniform, Zipfian, and adversarial key distributions.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No partition-count migration; single process only.
- [ ] **GAP05-MC41-011** — Test partition migration during concurrent writes, restart, and membership changes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No partition-count migration; single process only.
- [ ] **GAP05-MC41-012** — Require acceptance evidence that increasing unrelated-key concurrency scales without changing single-key causal semantics.  
  `PARTIAL` — second-pass tag review: No scaling measurement — evidence: test_unrelated_keys_scale_single_key_semantics_unchanged

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC41-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC41-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc41
- [ ] **GAP05-MC41-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc41
- [ ] **GAP05-MC41-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc41
- [ ] **GAP05-MC41-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC41-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC41-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC41-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc41
- [ ] **GAP05-MC41-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC41-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc41
- [ ] **GAP05-MC41-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC41-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC41-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 2}
- [ ] **GAP05-MC41-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC41-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC41-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc41
- [ ] **GAP05-MC41-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC41-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc41

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 42. Batch apply API

**Priority:** P2  
**Requirement family:** `GAP05-MC42`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC42-001** — Define batch request schema with stable batch ID, ordered or unordered semantics, membership/schema context, and per-item write identities.  
  `PARTIAL` — second-pass tag review: No batch ID, ordering semantics, or membership/schema context — evidence: test_batch_per_item_outcomes_and_retry_idempotent
- [ ] **GAP05-MC42-002** — Specify whether the batch is atomic, partition-atomic, or independently applied per item; make partial-failure semantics explicit.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_batch_per_item_outcomes_and_retry_idempotent
- [ ] **GAP05-MC42-003** — Bound batch item count, serialized bytes, decoded bytes, aggregate vector entries, and processing time.  
  `PARTIAL` — second-pass tag review: Only item count; bytes, vector entries, processing time not bounded/tested — evidence: test_batch_per_item_outcomes_and_retry_idempotent
- [ ] **GAP05-MC42-004** — Validate tenant/environment consistency rules and whether mixed-namespace batches are prohibited.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No batch id / batch-level audit record.
- [ ] **GAP05-MC42-005** — Apply dedupe and provenance verification per item even when transport/authentication is shared.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_batch_per_item_outcomes_and_retry_idempotent
- [ ] **GAP05-MC42-006** — Preserve deterministic item outcomes independent of internal parallelism.  
  `BLOCKED` — requires independent human review, approval or an exercise with people — evidence: test_batch_per_item_outcomes_and_retry_idempotent
- [ ] **GAP05-MC42-007** — Define rollback/compensation behavior only where actual atomicity is promised; otherwise return durable per-item outcomes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No batch id / batch-level audit record.
- [ ] **GAP05-MC42-008** — Stream or chunk large batches to avoid double-buffering entire payloads in memory.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No batch id / batch-level audit record.
- [ ] **GAP05-MC42-009** — Propagate backpressure and cancellation without leaving ambiguous acknowledgement state.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No batch id / batch-level audit record.
- [ ] **GAP05-MC42-010** — Audit batch-level identity plus individual state-changing item outcomes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No batch id / batch-level audit record.
- [ ] **GAP05-MC42-011** — Test duplicates within a batch, dependencies between items, oversized item, mid-batch crash, retry, and reordered batch delivery.  
  `PARTIAL` — second-pass tag review: No dependencies, oversized item, mid-batch crash, reordered batch — evidence: test_batch_per_item_outcomes_and_retry_idempotent
- [ ] **GAP05-MC42-012** — Require acceptance evidence that retrying the same batch cannot create additional logical writes.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_batch_per_item_outcomes_and_retry_idempotent

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC42-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC42-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc42
- [ ] **GAP05-MC42-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc42
- [ ] **GAP05-MC42-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc42
- [ ] **GAP05-MC42-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC42-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC42-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC42-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc42
- [ ] **GAP05-MC42-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC42-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC42-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC42-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC42-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC42-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC42-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC42-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC42-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC42-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc42

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 43. Zero-copy/binary encoding path

**Priority:** P2  
**Requirement family:** `GAP05-MC43`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC43-001** — Establish profiling evidence that serialization/copy overhead is material before introducing complexity.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No cross-language codec.
- [ ] **GAP05-MC43-002** — Choose a binary schema/codec with bounded parsing behavior, explicit versioning, and cross-language support.  
  `PARTIAL` — second-pass tag review: No cross-language support; bounded parsing not asserted here — evidence: test_roundtrip_equivalence
- [ ] **GAP05-MC43-003** — Preserve the same semantic validation and security checks as the canonical logical wire schema.  
  `PARTIAL` — second-pass tag review: Validation equivalence on binary path not asserted — evidence: test_roundtrip_equivalence
- [ ] **GAP05-MC43-004** — Use slices/views/reference-counted buffers only where lifetime and ownership are unambiguous.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_lazy_value_view
- [ ] **GAP05-MC43-005** — Prevent untrusted payload lengths from producing unchecked allocations or buffer overreads.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_trailing_and_truncation; test_binary_and_frame_fuzz
- [ ] **GAP05-MC43-006** — Canonicalize or hash the exact security-relevant representation used for provenance so zero-copy paths do not change signature semantics.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_roundtrip_equivalence
- [ ] **GAP05-MC43-007** — Define fallback behavior when buffers are non-contiguous, encrypted/compressed, or require schema translation.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC43-008** — Keep immutable payload buffers separate from mutable runtime state to prevent time-of-check/time-of-use corruption.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_lazy_value_view
- [ ] **GAP05-MC43-009** — Benchmark copy count, allocation count, throughput, latency, and CPU before/after using representative payload sizes.  
  `NOT_EVIDENCED` — second-pass tag review: No copy/allocation/before-after benchmark asserted — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC43-010** — Run parser fuzzing and memory-safety tooling appropriate to any native extension used.  
  `BLOCKED` — requires native fuzzing/sanitizer tooling absent from this build
- [ ] **GAP05-MC43-011** — Test buffer lifetime across async transport, batching, persistence, and cancellation.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No cross-language codec.
- [ ] **GAP05-MC43-012** — Require a regression gate proving the optimization preserves byte/logical equivalence and produces a quantified performance benefit.  
  `PARTIAL` — second-pass tag review: No quantified performance benefit — evidence: test_roundtrip_equivalence

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC43-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC43-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc43
- [ ] **GAP05-MC43-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc43
- [ ] **GAP05-MC43-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc43
- [ ] **GAP05-MC43-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc43
- [ ] **GAP05-MC43-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc43
- [ ] **GAP05-MC43-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC43-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc43
- [ ] **GAP05-MC43-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC43-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC43-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC43-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC43-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 5}
- [ ] **GAP05-MC43-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC43-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC43-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC43-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC43-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc43

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 44. Conflict analytics

**Priority:** P2  
**Requirement family:** `GAP05-MC44`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC44-001** — Define a privacy-safe event model for conflict creation, growth, overflow/quarantine, resolution, recurrence, and age.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Raw keys in report (should be digests for unauthorised viewers).
- [ ] **GAP05-MC44-002** — Attribute conflicts by tenant-safe aggregate, key digest/hot-key cohort, replica/site pair, data type, policy version, and causal pattern where permitted.  
  `PARTIAL` — second-pass tag review: Only hot key/recurrence; site pair, data type, policy version, causal pattern absent — evidence: test_analytics_matches_audit
- [ ] **GAP05-MC44-003** — Track conflict rate per write, unresolved duration, sibling/frontier width, quarantine frequency, and repeat-conflict frequency.  
  `PARTIAL` — second-pass tag review: Unresolved duration, frontier width, quarantine frequency, conflict rate not asserted — evidence: test_analytics_matches_audit
- [ ] **GAP05-MC44-004** — Differentiate genuine concurrent authoring from replay/equivocation/security anomalies.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC44-005** — Correlate conflict spikes with membership changes, partitions, transport health, deployments, and policy changes.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Raw keys in report (should be digests for unauthorised viewers).
- [ ] **GAP05-MC44-006** — Use bounded-cardinality dimensions and offline aggregation for high-dimensional analysis.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Raw keys in report (should be digests for unauthorised viewers).
- [ ] **GAP05-MC44-007** — Define retention and access control for analytics data derived from potentially sensitive operational metadata.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Raw keys in report (should be digests for unauthorised viewers).
- [ ] **GAP05-MC44-008** — Provide top-N and trend views without exposing raw keys to unauthorized operators.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Raw keys in report (should be digests for unauthorised viewers).
- [ ] **GAP05-MC44-009** — Add recurrence detection to identify keys/workflows that repeatedly enter conflict after resolution.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_analytics_matches_audit
- [ ] **GAP05-MC44-010** — Validate analytics counts against sampled audit-ledger ground truth.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_analytics_matches_audit
- [ ] **GAP05-MC44-011** — Test analytics pipeline under conflict storms and telemetry collector outages.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Raw keys in report (should be digests for unauthorised viewers).
- [ ] **GAP05-MC44-012** — Require operational review criteria that turn analytics findings into capacity, product, or policy remediation actions.  
  `BLOCKED` — requires independent human review, approval or an exercise with people

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC44-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC44-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44
- [ ] **GAP05-MC44-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44
- [ ] **GAP05-MC44-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44
- [ ] **GAP05-MC44-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44
- [ ] **GAP05-MC44-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44
- [ ] **GAP05-MC44-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44
- [ ] **GAP05-MC44-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44
- [ ] **GAP05-MC44-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44
- [ ] **GAP05-MC44-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC44-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC44-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC44-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC44-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC44-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC44-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC44-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC44-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc44

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 45. Administrative tooling/UI

**Priority:** P2  
**Requirement family:** `GAP05-MC45`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC45-001** — Design separate workflows for inspection, export, freeze, retry, resolve, reseed, restore, membership change, and emergency fencing.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No UI; no operation receipts.
- [ ] **GAP05-MC45-002** — Require strong operator authentication and least-privilege authorization for each workflow.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC45-003** — Display tenant/environment, membership epoch, provenance status, causal vectors or readable summaries, policy version, and audit linkage for every conflict action.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No UI; no operation receipts.
- [ ] **GAP05-MC45-004** — Use explicit confirmation and reason capture for destructive or irreversible operations.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No UI; no operation receipts.
- [ ] **GAP05-MC45-005** — Use optimistic concurrency so a UI cannot resolve a conflict whose state changed after it was displayed.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_stale_decision_rejected
- [ ] **GAP05-MC45-006** — Default to redacted values and require elevated permission plus audit for sensitive payload viewing.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC45-007** — Provide dry-run/explain previews for resolution, membership, restore, and cleanup actions.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No UI; no operation receipts.
- [ ] **GAP05-MC45-008** — Prevent direct editing of authoritative persisted files or internal collections through the tool.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_cli_read_only_tools
- [ ] **GAP05-MC45-009** — Surface health/readiness, storage pressure, backlog, and policy dependency state before allowing risky operations.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No UI; no operation receipts.
- [ ] **GAP05-MC45-010** — Generate machine-readable operation receipts containing request ID, actor, target generation, result, and audit reference.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No UI; no operation receipts.
- [ ] **GAP05-MC45-011** — Test stale browser/session state, repeated clicks, interrupted requests, CSRF-equivalent threats, cross-tenant navigation, and permission revocation.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC45-012** — Require usability/incident drills showing an operator can diagnose and safely resolve a representative conflict without bypassing system invariants.  
  `BLOCKED` — requires independent human review, approval or an exercise with people

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC45-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC45-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc45
- [ ] **GAP05-MC45-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc45
- [ ] **GAP05-MC45-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc45
- [ ] **GAP05-MC45-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC45-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC45-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC45-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC45-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC45-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC45-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC45-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC45-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 2}
- [ ] **GAP05-MC45-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC45-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC45-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC45-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc45
- [ ] **GAP05-MC45-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc45

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 46. Capacity model and release regression gates

**Priority:** P2  
**Requirement family:** `GAP05-MC46`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC46-001** — Define workload variables including replica count, tenant count, key cardinality, hot-key skew, write rate, payload size, vector size, conflict rate, partition duration, and retention horizons.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No owner-approved thresholds, no baseline history, no variance analysis.
- [ ] **GAP05-MC46-002** — Build analytical or empirical models for CPU, memory, WAL growth, checkpoint footprint, quarantine growth, dedupe growth, and network bandwidth.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC46-003** — Identify saturation points and document required operational headroom rather than sizing to maximum observed throughput.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC46-004** — Set p50/p95/p99/worst-case or timeout thresholds for apply, persist, resolve, reconcile, recover, and restore operations.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC46-005** — Separate steady-state budgets from temporary partition-healing and disaster-recovery budgets.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No owner-approved thresholds, no baseline history, no variance analysis.
- [ ] **GAP05-MC46-006** — Include storage amplification from WAL, multiple checkpoints, audit, quarantine, backups, and encryption/encoding overhead.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No owner-approved thresholds, no baseline history, no variance analysis.
- [ ] **GAP05-MC46-007** — Parameterize models by supported hardware/storage classes and runtime versions.  
  `BLOCKED` — only one filesystem/hardware class available
- [ ] **GAP05-MC46-008** — Automate benchmark execution using pinned datasets/configurations and compare release candidates to a known baseline.  
  `PARTIAL` — second-pass tag review: No baseline comparison of release candidates — evidence: test_bench_and_proposed_gates
- [ ] **GAP05-MC46-009** — Block release on statistically meaningful regressions beyond approved thresholds.  
  `BLOCKED` — requires independent human review, approval or an exercise with people
- [ ] **GAP05-MC46-010** — Record benchmark variance, environment noise, and confidence so small changes are not overinterpreted.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No owner-approved thresholds, no baseline history, no variance analysis.
- [ ] **GAP05-MC46-011** — Feed production telemetry back into assumptions and periodically recalibrate the model.  
  `BLOCKED` — requires production-scale data or multi-hour runs outside this build's budget
- [ ] **GAP05-MC46-012** — Require a signed-off capacity sheet for each production deployment tier with expected load and documented safety margin.  
  `BLOCKED` — requires independent human review, approval or an exercise with people

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC46-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC46-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc46
- [ ] **GAP05-MC46-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc46
- [ ] **GAP05-MC46-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc46
- [ ] **GAP05-MC46-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC46-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC46-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC46-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC46-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC46-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC46-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC46-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC46-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC46-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC46-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC46-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC46-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC46-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc46

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 47. Runbooks and incident automation

**Priority:** P2  
**Requirement family:** `GAP05-MC47`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC47-001** — Create runbooks for replication lag, quarantine surge, WAL/checkpoint corruption, disk pressure, identity/key failure, policy outage, split-brain, bad deployment, and failed restore.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No game-day evidence.
- [ ] **GAP05-MC47-002** — Define severity levels and concrete paging thresholds tied to observability signals.  
  `PARTIAL` — second-pass tag review: One SEV1 mapping; concrete paging thresholds not asserted — evidence: test_triage_and_containment
- [ ] **GAP05-MC47-003** — Document first-response containment actions that preserve evidence and prevent additional unsafe writes.  
  `PARTIAL` — second-pass tag review: Freeze asserted; evidence preservation and documentation not — evidence: test_triage_and_containment
- [ ] **GAP05-MC47-004** — Provide safe automation for fencing a stale replica, pausing admission, increasing diagnostics, exporting evidence, and initiating approved reseed/restore flows.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_triage_and_containment
- [ ] **GAP05-MC47-005** — Require explicit authorization and audit for automated actions that change membership, delete state, or alter conflict resolution.  
  `PARTIAL` — second-pass tag review: Only containment authz; audit and membership/delete/resolution automation not — evidence: test_triage_and_containment
- [ ] **GAP05-MC47-006** — Document when not to automate and when human/security approval is mandatory.  
  `BLOCKED` — requires independent human review, approval or an exercise with people
- [ ] **GAP05-MC47-007** — Include decision trees for choosing repair versus restore versus reseed versus rollback.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No game-day evidence.
- [ ] **GAP05-MC47-008** — Capture commands/API examples using stable supported tooling rather than direct file edits.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No game-day evidence.
- [ ] **GAP05-MC47-009** — Define post-action verification: readiness, invariant checks, anti-entropy convergence, audit verification, and tenant impact.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No game-day evidence.
- [ ] **GAP05-MC47-010** — Run game-day exercises and update runbooks from observed confusion or missing telemetry.  
  `BLOCKED` — requires independent human review, approval or an exercise with people
- [ ] **GAP05-MC47-011** — Version runbooks with the software/compatibility matrix and retire obsolete procedures.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No game-day evidence.
- [ ] **GAP05-MC47-012** — Require each P0/P1 failure mode to map to an owned runbook or an explicit documented rationale.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC47-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC47-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc47
- [ ] **GAP05-MC47-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc47
- [ ] **GAP05-MC47-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc47
- [ ] **GAP05-MC47-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC47-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC47-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC47-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC47-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC47-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC47-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC47-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC47-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC47-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC47-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC47-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC47-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc47
- [ ] **GAP05-MC47-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc47

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 48. Formal invariant specification/model checking

**Priority:** P2  
**Requirement family:** `GAP05-MC48`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC48-001** — Model replicas, causal vectors, active frontier, quarantine overflow, dedupe identity, conflict resolution, membership epochs, and fencing as explicit state variables.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_exhaustive_bounded_invariants
- [ ] **GAP05-MC48-002** — Specify safety invariants including causal maximality, no silent write loss, deterministic overflow selection, replay idempotence, and stale-epoch rejection.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_exhaustive_bounded_invariants
- [ ] **GAP05-MC48-003** — Specify resolution invariants requiring the resolution event to dominate all targeted unresolved events.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_exhaustive_bounded_invariants; test_resolution_dominates_all
- [ ] **GAP05-MC48-004** — Specify membership invariants preventing removed or old-incarnation replicas from authoring accepted new state.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_exhaustive_bounded_invariants
- [ ] **GAP05-MC48-005** — Model crash/recovery abstractions for WAL/checkpoint durability decisions where feasible.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: TLC not run.
- [ ] **GAP05-MC48-006** — Model nondeterministic message delay, duplication, reordering, partition, and reconnect.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_exhaustive_bounded_invariants
- [ ] **GAP05-MC48-007** — Check small state spaces exhaustively and document bounds so proof claims are not overstated.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_exhaustive_bounded_invariants
- [ ] **GAP05-MC48-008** — Convert every discovered counterexample into an executable regression test against the implementation.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_checker_catches_injected_bug
- [ ] **GAP05-MC48-009** — Keep the formal model versioned beside the implementation and map model transitions to concrete APIs/events.  
  `PARTIAL` — second-pass tag review: Transition-to-API mapping not asserted — evidence: test_tla_spec_shipped_not_claimed
- [ ] **GAP05-MC48-010** — Review assumptions such as finite counters, trusted membership authority, authenticated identity, and storage atomicity explicitly.  
  `PARTIAL` — weak_link: passing test shares no content word with item — evidence: test_tla_spec_shipped_not_claimed
- [ ] **GAP05-MC48-011** — Automate model checking in CI for tractable bounds and schedule larger exploration separately.  
  `PARTIAL` — second-pass tag review: CI automation and separate larger schedule not shown — evidence: test_checker_catches_injected_bug
- [ ] **GAP05-MC48-012** — Require architecture changes affecting causal or membership semantics to update the model before release approval.  
  `BLOCKED` — requires independent human review, approval or an exercise with people

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC48-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC48-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc48
- [ ] **GAP05-MC48-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc48
- [ ] **GAP05-MC48-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc48
- [ ] **GAP05-MC48-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC48-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `NOT_EVIDENCED` — registry field 'thr' empty
- [ ] **GAP05-MC48-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC48-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc48
- [ ] **GAP05-MC48-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC48-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC48-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC48-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC48-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 4}
- [ ] **GAP05-MC48-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC48-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `MEASURED_UNDER_PROPOSED_TARGET` — measured by bench.py; thresholds PROPOSED, no owner-approved budget
- [ ] **GAP05-MC48-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC48-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC48-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc48

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 49. Packaging/CI/release metadata

**Priority:** P2  
**Requirement family:** `GAP05-MC49`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC49-001** — Add authoritative package metadata (`pyproject.toml` or platform equivalent) with name, version, runtime constraints, license, authorship/ownership, and build backend.  
  `PARTIAL` — second-pass tag review: Only version checked; license, authorship, constraints, backend not — evidence: test_version_consistency
- [ ] **GAP05-MC49-002** — Pin build/test dependencies through a reproducible lock or constraints process and scan them for known vulnerabilities.  
  `BLOCKED` — requires release infrastructure (signing keys, provenance builder, protected branches, advisory feed)
- [ ] **GAP05-MC49-003** — Build release artifacts in a clean isolated environment and verify reproducibility where practical.  
  `BLOCKED` — requires release infrastructure (signing keys, provenance builder, protected branches, advisory feed)
- [ ] **GAP05-MC49-004** — Generate an SBOM covering direct, transitive, native, and bundled dependencies.  
  `PARTIAL` — second-pass tag review: SBOM lists only cryptography; transitive/native deps absent — evidence: test_sbom_and_checksums
- [ ] **GAP05-MC49-005** — Generate provenance/attestation for source revision, builder identity, build inputs, test results, and artifact hashes.  
  `BLOCKED` — requires release infrastructure (signing keys, provenance builder, protected branches, advisory feed)
- [ ] **GAP05-MC49-006** — Sign release artifacts and publish verifiable checksums/signatures through an authenticated release channel.  
  `BLOCKED` — requires release infrastructure (signing keys, provenance builder, protected branches, advisory feed)
- [ ] **GAP05-MC49-007** — Run unit, property, fuzz smoke, integration, security, compatibility, and packaging validation gates appropriate to release tier.  
  `NOT_EVIDENCED` — second-pass tag review: Test checks evidence refs only, not release gate suite — evidence: test_evidence_reference_check
- [ ] **GAP05-MC49-008** — Verify source distributions/wheels/archives contain required schemas, migrations, notices, tests/fixtures as policy requires, and exclude secrets/temp files.  
  `PARTIAL` — second-pass tag review: Source tree checksummed; built distributions not inspected, secrets not excluded — evidence: test_sbom_and_checksums
- [ ] **GAP05-MC49-009** — Enforce version consistency across package metadata, `VERSION`, changelog, protocol capability declarations, and generated documentation.  
  `PARTIAL` — second-pass tag review: Protocol capability declarations and generated docs not checked — evidence: test_version_consistency
- [ ] **GAP05-MC49-010** — Use branch/release protection so failed required gates cannot be bypassed without an auditable exception.  
  `BLOCKED` — requires release infrastructure (signing keys, provenance builder, protected branches, advisory feed)
- [ ] **GAP05-MC49-011** — Perform install/import/smoke tests from the final packaged artifact rather than only from the source tree.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: No signing, no provenance attestation, no vulnerability scan, no reproducible-build check.
- [ ] **GAP05-MC49-012** — Require a release manifest listing hashes, compatibility matrix version, SBOM, provenance, signatures, and known limitations.  
  `PARTIAL` — second-pass tag review: No release manifest with SBOM, provenance, signatures, limitations — evidence: test_sbom_and_checksums

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC49-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC49-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc49
- [ ] **GAP05-MC49-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc49
- [ ] **GAP05-MC49-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc49
- [ ] **GAP05-MC49-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc49
- [ ] **GAP05-MC49-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc49
- [ ] **GAP05-MC49-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC49-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC49-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC49-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC49-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC49-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC49-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: {"passing_tagged_tests": 3}
- [ ] **GAP05-MC49-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC49-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC49-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC49-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC49-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc49

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

### 50. Missing master-prompt evidence artifact

**Priority:** P2  
**Requirement family:** `GAP05-MC50`  
**Exit condition:** The component is implemented, integrated, failure-tested, observable, documented, and supported by objective release evidence without weakening the GAP-05 causal or security invariants.

#### Component-specific implementation checklist

- [ ] **GAP05-MC50-001** — Determine whether `MASTER.md` is actually an authoritative artifact required by the GAP series governance/audit chain rather than assuming it can be regenerated.  
  `BLOCKED` — no graphical UI exists (read-only CLI only)
- [ ] **GAP05-MC50-002** — Locate the original source-of-truth through repository history, release artifacts, documented upstream package, or authorized project records.  
  `BLOCKED` — authoritative MASTER.md source is not available to this build
- [ ] **GAP05-MC50-003** — Do not reconstruct missing authoritative content from inference and then represent it as original evidence.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_evidence_reference_check
- [ ] **GAP05-MC50-004** — Verify recovered artifact identity using historical hash, signature, release manifest, commit reference, or another trustworthy provenance source.  
  `BLOCKED` — authoritative MASTER.md source is not available to this build
- [ ] **GAP05-MC50-005** — Record where the artifact was recovered from, by whom/what process, and the verification method used.  
  `BLOCKED` — authoritative MASTER.md source is not available to this build
- [ ] **GAP05-MC50-006** — Compare references in README/changelog/manifests against the recovered artifact version and intended scope.  
  `BLOCKED` — authoritative MASTER.md source is not available to this build
- [ ] **GAP05-MC50-007** — If the original cannot be recovered, update documentation to mark the evidence gap explicitly and define the governance impact.  
  `PARTIAL` — second-pass tag review: Gap documentation and governance impact not asserted — evidence: test_evidence_reference_check
- [ ] **GAP05-MC50-008** — Separate any newly authored replacement guidance from recovered historical evidence using a new filename/version/provenance record.  
  `BLOCKED` — no graphical UI exists (read-only CLI only) — evidence: test_evidence_reference_check
- [ ] **GAP05-MC50-009** — Add the artifact to release packaging only after provenance and licensing/ownership are established.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Artifact not recovered; waiver not granted.
- [ ] **GAP05-MC50-010** — Add CI checks that fail when mandatory evidence artifacts referenced by manifests/documentation are absent.  
  `LOCAL_VERIFIED_UNREVIEWED` — evidence: test_evidence_reference_check
- [ ] **GAP05-MC50-011** — Include the artifact hash in `SHA256SUMS.txt` and release provenance when restored.  
  `NOT_EVIDENCED` — no test or artifact in this build evidences this item; component gap: Artifact not recovered; waiver not granted.
- [ ] **GAP05-MC50-012** — Require closure evidence consisting of the verified authoritative artifact or an approved documented waiver explaining why the reference was removed.  
  `BLOCKED` — requires independent human review, approval or an exercise with people

#### Cross-cutting hardening and certification checklist

- [ ] **GAP05-MC50-013 · Architecture** — Assign an accountable component owner and reviewer, document the production use cases/non-goals, and link the design to GAP-05 causal-state invariants.  
  `BLOCKED` — owner and reviewer assignment is a human decision; registry records UNASSIGNED
- [ ] **GAP05-MC50-014 · Architecture** — Write explicit safety, liveness, consistency, durability, and isolation invariants that this component must preserve under normal and failure conditions.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc50
- [ ] **GAP05-MC50-015 · Interfaces** — Define stable public/internal APIs, input/output contracts, error codes, retry semantics, idempotency behavior, and ownership boundaries with adjacent GAP components.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc50
- [ ] **GAP05-MC50-016 · Interfaces** — Version all externally persisted or transmitted semantics and document forward/backward compatibility and deprecation behavior.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc50
- [ ] **GAP05-MC50-017 · Security** — Update the threat model with trust boundaries, attacker capabilities, protected assets, abuse cases, and required controls introduced by this component.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc50
- [ ] **GAP05-MC50-018 · Security** — Apply least privilege, fail-closed handling for security-critical uncertainty, secret redaction, and audit coverage for privileged state changes.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc50
- [ ] **GAP05-MC50-019 · Reliability** — Define behavior for timeout, cancellation, retry, duplicate execution, partial failure, dependency outage, process crash, restart, and stale inputs.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC50-020 · Reliability** — Ensure all memory/disk/network queues and collections are explicitly bounded or have a documented capacity/retention mechanism with observable pressure signals.  
  `NOT_EVIDENCED` — registry field 'bnd' empty
- [ ] **GAP05-MC50-021 · Persistence** — Specify whether component state is ephemeral or durable; if durable, define atomicity, checksum/integrity, recovery order, migration, backup, and corruption behavior.  
  `NOT_EVIDENCED` — registry field 'per' empty
- [ ] **GAP05-MC50-022 · Concurrency** — Document locking/transaction boundaries, ordering constraints, deadlock avoidance, and thread/process safety; add race-focused tests where shared state exists.  
  `NOT_EVIDENCED` — registry field 'con' empty
- [ ] **GAP05-MC50-023 · Observability** — Define structured metrics, logs, traces, health signals, and stable reason codes sufficient to distinguish correctness failures from capacity/dependency failures.  
  `NOT_EVIDENCED` — registry field 'obs' empty
- [ ] **GAP05-MC50-024 · Observability** — Define alert thresholds/SLO impact and include a dashboard or diagnostic query path that an operator can use without reading internal files directly.  
  `PARTIAL` — no alert thresholds/SLO or dashboard agreed
- [ ] **GAP05-MC50-025 · Testing** — Implement positive, negative, boundary, malformed-input, replay/idempotency, concurrency, and regression tests with deterministic fixtures.  
  `PARTIAL` — 1 passing tagged tests
- [ ] **GAP05-MC50-026 · Testing** — Add fault-injection or dependency-failure tests appropriate to the component and prove failures preserve GAP-05 state invariants.  
  `NOT_EVIDENCED` — no fault-injection test for this component
- [ ] **GAP05-MC50-027 · Performance** — Establish latency/throughput/resource budgets and benchmark worst realistic inputs, not only nominal cases; create a regression threshold for release.  
  `NOT_EVIDENCED` — no benchmark for this component
- [ ] **GAP05-MC50-028 · Operations** — Provide configuration schema with safe defaults, validation, immutable/reload semantics, ownership, and rollback instructions; reject unsafe startup configurations.  
  `NOT_EVIDENCED` — registry field 'cfg' empty
- [ ] **GAP05-MC50-029 · Operations** — Write operator/runbook procedures for deployment, upgrade, rollback, diagnosis, recovery, and emergency containment, with required authorization clearly stated.  
  `NOT_EVIDENCED` — registry field 'rb' empty
- [ ] **GAP05-MC50-030 · Evidence** — Define objective completion evidence (tests, logs, metrics, manifests, model-check output, signatures, restore drill, or benchmark report) and store it with the release.  
  `DESIGN_RECORDED_UNREVIEWED` — evidence: md#mc50

**Component completion gate:** all **30** requirements above have reviewable evidence; open exceptions are formally risk-accepted and do not contradict a P0 causal, durability, isolation, identity, provenance, or fencing invariant.

---

## Final certification record

- [ ] **GAP05-CERT-001** — Architecture review approves the complete dependency graph among all 50 components and adjacent GAP subsystems.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-002** — Security review validates identity, provenance, authorization, encryption, audit integrity, tenant isolation, replay resistance, and split-brain fencing.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-003** — Reliability review validates crash consistency, restore/reseed, anti-entropy, partition recovery, bounded overload behavior, and no acknowledged-write loss under the certified fault model.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-004** — Formal/property test evidence covers causal maximality, delivery-order convergence, deterministic overflow/quarantine semantics, replay idempotence, and resolution dominance.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-005** — Compatibility and rolling-upgrade certification passes for every supported matrix cell.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-006** — Capacity/performance certification passes at production limits with documented safety headroom and automated regression gates.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-007** — Operations review validates dashboards, alerts, incident runbooks, backup/restore drills, and administrative workflows.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-008** — Release engineering verifies package metadata, reproducible build controls, SBOM, provenance/attestation, hashes/signatures, license/notice, and artifact completeness.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-009** — The `MASTER.md` evidence gap is either closed with verified authoritative provenance or resolved through an approved documented waiver/reference removal.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED
- [ ] **GAP05-CERT-010** — Final release decision records all accepted residual risks, expiry dates for waivers, owners, and required follow-up milestones.  
  `BLOCKED` — certification/gate decision requires independent review; mechanically NOT MET because component items remain BLOCKED/NOT_EVIDENCED

---

## Traceability summary

- **Components:** 50
- **Per-component component-specific checks:** 12
- **Per-component cross-cutting checks:** 18
- **Per-component total:** 30
- **Global gates:** 6
- **Final certification gates:** 10
- **Total checklist items:** 1516

**Document control:** This checklist expands the `MISSING_COMPONENTS.md` inventory from GAP-05 v4.2.0. It is an implementation/certification work product, not a claim that the listed components already exist.
