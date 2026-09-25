# GAP-08 OTA Lifecycle/Rollback — Professional Missing-Components Implementation Checklist

**Baseline:** GAP-08 v4.2.0  
**Document version:** 1.0  
**Purpose:** Convert the 40-item GAP-08 missing-components register into an implementation-, verification-, operations-, and release-grade engineering checklist.  
**Scope:** GAP-08 control plane and its required integration boundaries. This checklist does not reassign ownership of sibling GAP subsystems; it defines the evidence GAP-08 must require and consume from them.

## How to use this checklist

- Treat every unchecked item as an engineering or assurance gap until objective evidence exists.
- Link each completed item to code, schema, ADR, test, benchmark, runbook, dashboard, signed configuration, or release evidence.
- P0 items are production blockers; P1 items are production-hardening requirements; P2 items cover certification, scale, and governance maturity.
- For safety-critical behavior, prefer executable invariants and machine-verifiable evidence over prose-only claims.
- Do not close an item merely because an interface is stubbed; integration behavior must be exercised under success, failure, timeout, restart, replay, and concurrency conditions.

## Global completion gates

- [ ] All 15 P0 component sections are complete, evidenced, peer-reviewed, and exercised in an environment representative of production.
- [ ] No P0 requirement relies on caller-supplied booleans, mutable local-only trust anchors, or best-effort persistence for a safety decision.
- [ ] Controller ownership/fencing, durable state, command idempotency, authenticated node identity, and external audit anchoring are tested together under partition/failover.
- [ ] Every node mutation can be causally traced from authorized rollout intent -> verified artifact -> policy/topology admission -> fenced command -> authenticated node acknowledgement -> observed state -> audit record.
- [ ] Every production dependency has an explicit fail-closed/degraded-mode policy and tested timeout/retry/circuit behavior.
- [ ] Rollback and quarantine remain available under overload and are not starved by normal rollout traffic.
- [ ] All externally visible schemas and error codes are versioned and compatibility-tested.
- [ ] Release evidence is tied to the exact shipped artifact digest and cannot be silently reused after code/configuration changes.

# P0 — Production blockers

## 1. Durable transactional rollout-state store

**Objective:** Persist PK_ROLLOUT_STATE/1 as the authoritative durable state for every rollout while preventing lost updates, split-brain writes, torn snapshots, and stale-controller mutation.

**Primary integration surface:** Rollout controller <-> GAP-05/selected state backend; snapshot()/from_snapshot(); transaction/CAS API; audit anchor writer; backup/restore tooling.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Persist PK_ROLLOUT_STATE/1 as the authoritative durable state for every rollout while preventing lost updates, split-brain writes, torn snapshots, and stale-controller mutation.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Rollout controller <-> GAP-05/selected state backend; snapshot()/from_snapshot(); transaction/CAS API; audit anchor writer; backup/restore tooling.
- [ ] Define the canonical persisted/message data model, including at minimum: rollout_id, schema, state_revision, controller_fence, bundle, pinned_target, wave_index, waves, versions, deferred, rolled_back, rollback_failed, quarantined, audit_head, state_digest, created_at, updated_at.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Exactly one committed revision succeeds for a given expected revision; pinned_target is immutable after first commit; state_digest and audit chain validate before mutation; rollback/deferred/quarantine state survives restart without regression.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Mutual TLS or workload identity to the store; least-privilege namespace access; encryption at rest; signed configuration for consistency/quorum settings; redact bundle secrets and credentials from snapshots.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: state write latency, CAS conflicts, stale-write rejects, commit failures, recovery duration, snapshot size, revision growth, backend quorum/health.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: CAS collision, leader failover between read/write, torn transaction, stale snapshot replay, backend timeout after commit, quorum loss, disk-full, restore from backup, schema-version mismatch.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: A restore/restart test proves byte-for-byte state continuity and a two-controller race proves only the holder of the current revision/fence can advance the rollout.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 2. Controller lease and fencing service

**Objective:** Guarantee a single effective rollout owner across controller failover, network partitions, process pauses, and stale restarts.

**Primary integration surface:** Controller <-> lease service/consensus store; acquire/renew/release API; monotonic fencing token propagated to state store and node-command transport.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Guarantee a single effective rollout owner across controller failover, network partitions, process pauses, and stale restarts.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Controller <-> lease service/consensus store; acquire/renew/release API; monotonic fencing token propagated to state store and node-command transport.
- [ ] Define the canonical persisted/message data model, including at minimum: rollout_id, lease_owner_id, lease_epoch/fencing_token, acquired_at, renew_deadline, expiry, last_heartbeat, holder_metadata.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Only the highest valid fencing token may mutate rollout state or issue node commands; expired owners can never regain authority without acquiring a newer token; release is idempotent.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Authenticated controller identity; authorization scoped per rollout/environment; signed or integrity-protected lease records; clock-skew-safe expiry semantics using server/consensus time.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: lease acquisition/renew latency, renewal failures, forced fencing events, stale-token rejects, ownership churn, failover recovery time.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: controller pause beyond TTL, asymmetric partition, duplicate acquisition, lease service failover, delayed renew response, stale node command from old epoch, token wrap/overflow.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: A partition test demonstrates the old controller is fenced at both persistence and command layers before the new controller advances any wave.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 3. Cross-rollout conflict detector

**Objective:** Prevent concurrent rollouts from touching overlapping environments, sites, nodes, runtime slots, or immutable artifact lineages in incompatible ways.

**Primary integration surface:** Rollout admission API; topology inventory; active-rollout index; artifact lineage/provenance metadata; policy engine for conflict classes.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Prevent concurrent rollouts from touching overlapping environments, sites, nodes, runtime slots, or immutable artifact lineages in incompatible ways.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Rollout admission API; topology inventory; active-rollout index; artifact lineage/provenance metadata; policy engine for conflict classes.
- [ ] Define the canonical persisted/message data model, including at minimum: rollout_id, environment_id, site_ids, node_ids, artifact_id/digest, lineage_id, compatibility domain, lock scope, lock owner, lock expiry/fence.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Conflicting scopes are rejected or serialized before first mutation; locks are atomic with rollout admission; no orphan lock survives past bounded lease expiry; non-conflicting rollouts can proceed concurrently.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Authenticated inventory and rollout identities; tamper-resistant lock records; prevent privilege-based bypass except via separately audited emergency override.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: conflict checks, rejected admissions by reason, active lock cardinality, lock wait time, orphan cleanup, false-positive/false-negative conflict incidents.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: simultaneous admission, partial inventory, late topology change, orphaned lock, controller crash, conflicting rollback while another rollout starts, same artifact different lineage metadata.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Concurrency tests start overlapping rollouts at the same instant and prove one is deterministically blocked before node-side execution begins.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 4. Authenticated health-gate adapter

**Objective:** Replace caller-supplied booleans with authenticated, fresh, scoped health evidence from GAP-09 and derive deterministic gate verdicts.

**Primary integration surface:** GAP-08 gate evaluator <-> GAP-09 query/subscription API; signed evidence envelope; policy evaluator; evidence cache with TTL and replay defense.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Replace caller-supplied booleans with authenticated, fresh, scoped health evidence from GAP-09 and derive deterministic gate verdicts.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: GAP-08 gate evaluator <-> GAP-09 query/subscription API; signed evidence envelope; policy evaluator; evidence cache with TTL and replay defense.
- [ ] Define the canonical persisted/message data model, including at minimum: gate_id, rollout_id, wave_id, node/cohort scope, source_identity, measurement_window, generated_at, expires_at, metric samples, aggregation, verdict, evidence_digest.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Evidence must match rollout/wave scope, be within freshness bounds, originate from an allowed source, cover the configured observation window, and be consumed once where replay would be unsafe.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: mTLS/workload identity, signed evidence or channel binding, nonce/event ID replay protection, source allowlist, policy-change provenance, no trust in caller-provided healthy=true.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: gate evaluation latency, evidence age, source coverage, stale/replay rejects, fail-open attempts rejected, inconclusive gates, health-source availability.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: stale evidence, future-dated evidence, partial metric set, source impersonation, replay, delayed telemetry, observability outage, contradictory sources, clock skew.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Integration tests feed stale, replayed, mis-scoped, unsigned, and contradictory evidence and verify every unsafe case fails closed.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 5. Externally sealed audit sink

**Objective:** Anchor rollout transitions outside the controller so a privileged local rewriter cannot erase or recompute the complete history.

**Primary integration surface:** PK_ROLLOUT_AUDIT/1 emitter <-> WORM object store/transparency log/SIEM; batching/ack API; seal receipt verification; reconciliation job.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Anchor rollout transitions outside the controller so a privileged local rewriter cannot erase or recompute the complete history.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: PK_ROLLOUT_AUDIT/1 emitter <-> WORM object store/transparency log/SIEM; batching/ack API; seal receipt verification; reconciliation job.
- [ ] Define the canonical persisted/message data model, including at minimum: event_id, rollout_id, sequence, previous_hash, event_hash, controller_fence, event_type, canonical payload digest, wall/monotonic time, signer/source identity, external receipt.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Audit sequence is append-only; gaps and forks are detectable; external receipt is durably associated with the local event; rollout transitions cannot be considered fully committed when required audit sealing fails under configured policy.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Dedicated signing identity/HSM where applicable; immutable retention; RBAC-separated writers/readers/admins; legal hold support; integrity verification on retrieval.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: seal latency, pending-unsealed events, reconciliation gaps, duplicate rejects, chain verification failures, retention coverage, sink availability.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: sink unavailable, duplicate delivery, out-of-order batch, forked chain, receipt loss, retention misconfiguration, compromised local disk, replayed event IDs.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Tamper drills alter local history after sealing and prove independent external verification detects the modification and reconstructs the authoritative event chain.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 6. Artifact digest/content verifier integration

**Objective:** Cryptographically bind rollout admission to the exact bytes delivered to and installed by nodes, not merely a logical bundle identifier.

**Primary integration surface:** GAP-07 verification result; downloader/content store; node installer; digest calculator; optional transparency/SBOM/provenance lookup.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Cryptographically bind rollout admission to the exact bytes delivered to and installed by nodes, not merely a logical bundle identifier.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: GAP-07 verification result; downloader/content store; node installer; digest calculator; optional transparency/SBOM/provenance lookup.
- [ ] Define the canonical persisted/message data model, including at minimum: artifact_id, logical bundle ID, algorithm, canonical digest, size, chunk digests/manifest, signature/provenance reference, download instance ID, verified_at.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: The digest accepted at rollout admission equals the digest of downloaded bytes and the digest acknowledged by the installer; partial/resumed transfer cannot bypass final whole-object verification.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Approved cryptographic algorithms only; signature/provenance chain validation; TOCTOU-resistant content-addressed storage; quarantine unverified bytes; secure deletion of rejected artifacts.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: verification latency, digest mismatches, cache hit/miss, corrupted chunks, provenance failures, bytes verified, algorithm distribution.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: bit flip, truncated download, resumed-range corruption, cache poisoning, digest mismatch between controller and node, algorithm downgrade, valid signature over different content.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: End-to-end tests mutate one byte after upstream verification and verify node installation is blocked before any activation step.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 7. Node-side transactional installer

**Objective:** Provide atomic installation/activation semantics with an explicitly recoverable old version across crashes, power loss, and partial writes.

**Primary integration surface:** GAP-01 supervisor <-> installer; content store; A/B slots or transactional package/image manager; bootloader/service manager; local journal.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Provide atomic installation/activation semantics with an explicitly recoverable old version across crashes, power loss, and partial writes.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: GAP-01 supervisor <-> installer; content store; A/B slots or transactional package/image manager; bootloader/service manager; local journal.
- [ ] Define the canonical persisted/message data model, including at minimum: install_txn_id, node_id, target_digest/version, active_slot, inactive_slot, previous_slot/version, phase, fsync checkpoints, activation_attempts, health marker, rollback marker.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Never overwrite the only known-good boot/runtime image; activation occurs only after complete verified staging; commit marker is written atomically; interrupted installs resume or revert deterministically.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Privilege separation for installer; signed artifact enforcement; protected boot/config partitions; secure boot/verified boot integration where available; path traversal/archive bomb defenses.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: install duration, bytes written, stage/activate failures, rollback count, boot-attempt count, slot health, disk wear/space, transaction recovery outcome.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: power loss per phase, ENOSPC, read-only filesystem, checksum failure, boot failure, service restart failure, corrupted journal, repeated activation loop, hardware watchdog reset.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Hardware-in-the-loop tests cut power at every durable checkpoint and prove the node always returns to either the previous known-good version or the fully verified new version.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 8. Real rollback executor feedback loop

**Objective:** Replace synthetic failure injection with authenticated node/supervisor execution acknowledgements, bounded waits, retries, and terminal failure classification.

**Primary integration surface:** GAP-08 rollback orchestrator <-> GAP-01 command channel; command status stream; timeout/retry scheduler; quarantine workflow.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Replace synthetic failure injection with authenticated node/supervisor execution acknowledgements, bounded waits, retries, and terminal failure classification.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: GAP-08 rollback orchestrator <-> GAP-01 command channel; command status stream; timeout/retry scheduler; quarantine workflow.
- [ ] Define the canonical persisted/message data model, including at minimum: rollback_command_id, rollout_id, node_id, target_version/digest, fence, issued_at, acked_at, phase, attempt, terminal_status, reason_code, observed_version.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Rollback completion is declared only after authoritative observed-version confirmation; duplicate commands are idempotent; a timeout never implies success; terminal failures enter quarantine.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Authenticated node identity and signed/channel-bound acknowledgements; command authorization bound to rollout/fence; replay protection; redact diagnostic secrets.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: rollback success/failure rate, acknowledgment latency, retries, timeout count, terminal reasons, quarantine rate, time-to-known-good.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: lost ack after successful rollback, duplicate ack, node reboot mid-rollback, unreachable node, stale command, supervisor restart, wrong observed version, rollback loop.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Fault tests drop, duplicate, and reorder acknowledgements and verify the controller converges to the correct observed node state without double-counting success.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 9. Site/topology blast-radius policy engine

**Objective:** Enforce fault-domain-aware rollout limits so a wave cannot simultaneously remove all healthy capacity in a rack, site, AZ, device class, quorum set, or service shard.

**Primary integration surface:** GAP-03 topology plan; hardware discovery; capacity/SLO inventory; rollout wave admission; policy configuration.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Enforce fault-domain-aware rollout limits so a wave cannot simultaneously remove all healthy capacity in a rack, site, AZ, device class, quorum set, or service shard.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: GAP-03 topology plan; hardware discovery; capacity/SLO inventory; rollout wave admission; policy configuration.
- [ ] Define the canonical persisted/message data model, including at minimum: node_id, site, rack, zone/AZ, power domain, network domain, device_class, service shard, redundancy group, minimum healthy count, max concurrent disruption.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Every admitted wave satisfies configured max-disruption and minimum-survivor constraints using current topology; stale/unknown topology fails closed for protected domains.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Signed topology/config provenance; authorization for policy exceptions; immutable audit of overrides; separate emergency policy path.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: wave risk score, per-domain disruption count, rejected plans, topology age, override usage, survivor margin, protected-domain saturation.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: stale topology, node moved domains, hidden dependency, single-node quorum, maintenance overlap, concurrent external outage, topology service unavailable.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Simulation and production-shadow tests prove canary/waves never violate N+1/quorum constraints under concurrent node and site failures.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 10. Emergency freeze/disable control

**Objective:** Provide an authenticated out-of-band control to stop new waves, freeze an in-flight rollout, and disable a known-bad artifact independently of ordinary health gates.

**Primary integration surface:** Operator/API emergency endpoint; policy/authorization service; state store; command scheduler; artifact denylist; audit sink.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Provide an authenticated out-of-band control to stop new waves, freeze an in-flight rollout, and disable a known-bad artifact independently of ordinary health gates.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Operator/API emergency endpoint; policy/authorization service; state store; command scheduler; artifact denylist; audit sink.
- [ ] Define the canonical persisted/message data model, including at minimum: freeze_id, scope, reason, actor, approver if required, created_at, expires_at, affected rollouts/artifacts/sites, resume authorization, revision.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Freeze takes precedence over ordinary progression; already-issued irreversible node operations are tracked to completion; artifact disable blocks all new admissions and deferred retries.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Strong MFA/workload identity; break-glass role with least privilege; optional dual control; immutable audit; rate limiting; protected recovery credentials.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: freeze propagation latency, blocked command count, active freezes, artifact denylist hits, break-glass use, resume failures.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: controller partition during freeze, stale cached policy, duplicate freeze request, malicious/accidental global freeze, expiry during incident, resume race.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: A live drill issues a global and scoped freeze during a rollout and proves no subsequent wave/deferred command is emitted after the bounded propagation interval.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 11. Authorization policy layer

**Objective:** Define and enforce least-privilege capabilities for rollout lifecycle actions, separating ordinary operators, approvers, security responders, automation, and administrators.

**Primary integration surface:** API gateway/controller <-> policy engine; identity provider; role/attribute mapping; decision log; emergency override path.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Define and enforce least-privilege capabilities for rollout lifecycle actions, separating ordinary operators, approvers, security responders, automation, and administrators.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: API gateway/controller <-> policy engine; identity provider; role/attribute mapping; decision log; emergency override path.
- [ ] Define the canonical persisted/message data model, including at minimum: principal, tenant/estate/environment/site scope, action, rollout_id, resource attributes, decision, policy_version, obligations, reason, request_id.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Every privileged state transition requires an explicit allow decision; deny is default; policy version is captured in audit; privilege changes do not retroactively authorize stale requests.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: MFA for human privileged actions; short-lived tokens; workload identities; separation of duties for override/final approval where required; periodic entitlement review.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: allow/deny counts by action, authorization latency, policy errors, break-glass events, privilege review findings, cross-scope reject count.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: stale token, revoked user, role escalation, confused deputy, cross-environment access, policy service outage, conflicting policies, emergency role misuse.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Negative authorization tests cover every lifecycle action and prove principals cannot act outside their assigned environment/site/operation scope.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 12. Device identity and attestation integration

**Objective:** Authenticate each target node and bind installation/rollback acknowledgements to a trusted device identity and acceptable platform state.

**Primary integration surface:** GAP-06 attestation verifier; node certificate/TPM identity; command channel; supervisor acknowledgment; inventory binding.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Authenticate each target node and bind installation/rollback acknowledgements to a trusted device identity and acceptable platform state.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: GAP-06 attestation verifier; node certificate/TPM identity; command channel; supervisor acknowledgment; inventory binding.
- [ ] Define the canonical persisted/message data model, including at minimum: node_id, hardware identity, certificate/key ID, attestation nonce, quote/evidence, PCR/measurement policy, firmware/boot state, verification time, expiry.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Controller node identity matches inventory and command target; attestation is fresh and nonce-bound; acknowledgements are accepted only from the authenticated intended device.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Hardware-backed keys where available; certificate rotation/revocation; anti-cloning policy; measured/secure boot policy; privacy-preserving attestation where necessary.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: attestation success/failure, evidence age, cert expiry, revoked-device attempts, identity mismatch, verifier latency/availability.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: cloned credential, revoked cert, stale quote, nonce replay, failed secure boot, replaced motherboard, TPM unavailable, attestation verifier outage.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Security tests replay valid acknowledgements from another node and prove they are rejected despite matching rollout and artifact identifiers.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 13. Persistent deferred-node scheduler

**Objective:** Persist and safely retry nodes that missed their wave because of offline/unavailable state without losing ordering, policy, or retry history.

**Primary integration surface:** Rollout state store; reconnect/event stream; retry queue; health gate; topology/admission policy; operator API.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Persist and safely retry nodes that missed their wave because of offline/unavailable state without losing ordering, policy, or retry history.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Rollout state store; reconnect/event stream; retry queue; health gate; topology/admission policy; operator API.
- [ ] Define the canonical persisted/message data model, including at minimum: deferred_item_id, rollout_id, node_id, original_wave, reason, first_deferred_at, next_attempt_at, attempt_count, retry_budget, expiry, current_version, policy_snapshot.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Deferred items survive controller restart; only one active retry per node/rollout exists; retry obeys current freeze/topology/authorization/compatibility gates; expiry is explicit and observable.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Queue mutations authorized by controller fence; authenticated reconnect events; prevent spoofed online status; no sensitive device credentials in queue payloads.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: deferred count/age histogram, retry success rate, retry attempts, expired items, reconnect-to-retry latency, queue lag, starvation indicators.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: reconnect storm, repeated flapping, node removed from inventory, rollout canceled, artifact disabled, retry budget exhausted, queue corruption, clock jump.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Restart and reconnect-storm tests prove every deferred node is processed at most once concurrently and never bypasses the explicit deferred health gate.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 14. Idempotent command transport

**Objective:** Provide at-least-once delivery while ensuring repeated rollout/install/rollback commands cannot cause duplicate side effects or stale actions.

**Primary integration surface:** Controller command publisher <-> broker/RPC <-> GAP-01 supervisor; deduplication store; acknowledgment stream; fencing token validation.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Provide at-least-once delivery while ensuring repeated rollout/install/rollback commands cannot cause duplicate side effects or stale actions.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Controller command publisher <-> broker/RPC <-> GAP-01 supervisor; deduplication store; acknowledgment stream; fencing token validation.
- [ ] Define the canonical persisted/message data model, including at minimum: command_id, operation_id/idempotency_key, rollout_id, node_id, action, artifact/target, fence, sequence, issued_at, expiry, payload_digest, status.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: A command ID maps to one semantic operation; duplicates return the prior result; lower fence/sequence commands are rejected; expired commands cannot activate after long partition.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: mTLS/message authentication; nonces or unique IDs; signed payload digest if transport is not end-to-end trusted; broker ACLs; no unauthenticated redelivery.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: delivery attempts, dedupe hits, stale-fence rejects, ack latency, dead-letter volume, expired commands, handler retries, poison-message count.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: duplicate/redelivered message, broker failover, ack loss, reorder, delayed old command, consumer restart, partial handler crash, poisoned message.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Transport tests inject duplicates/reordering/ack loss and verify each node performs exactly one semantic state transition per operation ID.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 15. Dependency-unavailable fail-closed policy

**Objective:** Define deterministic safe behavior when identity, signing, policy, time, persistence, supervisor, compatibility, or health dependencies are degraded or unavailable.

**Primary integration surface:** Dependency health registry; rollout state machine; policy configuration; circuit breakers; operator explain surface; emergency controls.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Define deterministic safe behavior when identity, signing, policy, time, persistence, supervisor, compatibility, or health dependencies are degraded or unavailable.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Dependency health registry; rollout state machine; policy configuration; circuit breakers; operator explain surface; emergency controls.
- [ ] Define the canonical persisted/message data model, including at minimum: dependency_name, required_for_actions, status, last_success, staleness, failure_mode, safe_action, grace_period if any, override policy.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: No action proceeds without every dependency required for that action being within configured health/freshness bounds; degraded modes are explicit and never silently become fail-open.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Authenticated health signals; override privilege separated from ordinary operator; immutable audit of overrides; signed configuration of dependency criticality.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: dependency availability, blocked rollout actions, fail-closed events, override count, stale-health age, circuit state, recovery time.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: DNS failure, time source skew, policy timeout, state-store read-only, health service stale, verifier outage, supervisor partition, partial recovery/flapping.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: A dependency matrix test systematically removes each service at each lifecycle phase and proves the resulting action matches the documented safe-state policy.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

# P1 — Production hardening and operations

## 16. Retry/backoff/jitter engine

**Objective:** Standardize bounded retry behavior only for idempotent or safely deduplicated operations and prevent retry storms during fleet-wide faults.

**Primary integration surface:** Command transport, state store client, health adapter, audit sink, content distribution, deferred scheduler; shared retry policy library.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Standardize bounded retry behavior only for idempotent or safely deduplicated operations and prevent retry storms during fleet-wide faults.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Command transport, state store client, health adapter, audit sink, content distribution, deferred scheduler; shared retry policy library.
- [ ] Define the canonical persisted/message data model, including at minimum: operation_class, attempt, max_attempts, base_delay, max_delay, jitter_mode, deadline, retryable_codes, circuit_key, next_attempt_at.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Non-idempotent operations are never blindly retried; retry budget is bounded by operation deadline; exponential backoff uses randomized jitter; circuit state is shared at appropriate node/site/dependency scope.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Policy configuration signed/versioned; no attacker-controlled error can force unbounded retries; retry logs redact tokens and payload secrets.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: attempt histogram, retries by cause, exhausted budgets, circuit opens, suppressed calls, recovery success, total retry-induced traffic.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: thundering herd, transient 5xx, permanent 4xx, timeout after success, site outage, clock change, retry queue overflow.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Load/fault tests prove fleet-wide failures do not exceed configured request/command amplification factors and recover without synchronized bursts.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 17. Backpressure and admission control

**Objective:** Bound rollout/controller work so overload cannot exhaust memory, network, state-store throughput, site bandwidth, or node supervisors.

**Primary integration surface:** API ingress; rollout scheduler; per-site/wave queues; command transport; deferred queue; content distribution; resource budget service.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Bound rollout/controller work so overload cannot exhaust memory, network, state-store throughput, site bandwidth, or node supervisors.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: API ingress; rollout scheduler; per-site/wave queues; command transport; deferred queue; content distribution; resource budget service.
- [ ] Define the canonical persisted/message data model, including at minimum: global/per-environment/per-site concurrency, queue limits, token buckets, outstanding commands, byte budgets, priority class, rejection reason.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Admission happens before expensive work; fairness prevents one rollout/site from starving others; queue limits are finite; overload returns machine-readable retry guidance.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Authenticated quota identity; prevent quota-key spoofing; administrative limit changes audited; protect emergency rollback traffic from starvation.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: queue depth, admission reject rate, wait time, concurrent rollouts, outstanding commands, bandwidth tokens, CPU/memory saturation.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: burst traffic, reconnect storm, oversized wave, slow downstream, queue saturation, priority inversion, malicious request flood.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Capacity tests exceed each configured limit and prove the controller remains responsive, preserves rollback capacity, and sheds load predictably.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 18. Rollout-window and maintenance-policy engine

**Objective:** Enforce approved deployment windows, blackouts, regional calendars, change freezes, and business constraints without ambiguous timezone behavior.

**Primary integration surface:** Policy service/config store; calendar source; rollout scheduler; emergency override; operator explain API.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Enforce approved deployment windows, blackouts, regional calendars, change freezes, and business constraints without ambiguous timezone behavior.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Policy service/config store; calendar source; rollout scheduler; emergency override; operator explain API.
- [ ] Define the canonical persisted/message data model, including at minimum: policy_id/version, scope, timezone, allowed windows, blackout intervals, holidays, freeze flags, override rule, effective_from/to.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Window evaluation uses explicit IANA timezone and DST semantics; a rollout cannot start a new wave outside policy; long-running wave behavior at window close is defined.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Policy revisions signed and audited; overrides require specific capability and reason; external calendar inputs authenticated and cached with freshness bounds.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: window blocks, override events, policy evaluation latency, stale calendar age, waves delayed, time-to-next-window.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: DST transition, leap day, stale calendar, policy update mid-rollout, overlapping windows, regional outage, emergency rollback outside window.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Deterministic time-travel tests cover DST gaps/folds, overlapping policies, freeze activation, and emergency rollback exemptions.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 19. Bandwidth-aware content distribution

**Objective:** Deliver large artifacts efficiently across constrained edge links with resumable, integrity-checked transfers and site-aware caching.

**Primary integration surface:** Origin/CDN/cache/peer distribution; downloader; chunk manifest; bandwidth scheduler; node/site topology; artifact verifier.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Deliver large artifacts efficiently across constrained edge links with resumable, integrity-checked transfers and site-aware caching.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Origin/CDN/cache/peer distribution; downloader; chunk manifest; bandwidth scheduler; node/site topology; artifact verifier.
- [ ] Define the canonical persisted/message data model, including at minimum: artifact/chunk digest, byte ranges, resume token, cache key, site budget, transfer priority, bytes_received, verified ranges, source peer.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Every resumed/chunked transfer reconstructs the exact admitted digest; per-site bandwidth caps are respected; cache/peer failures fall back safely without content ambiguity.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Authenticated sources/peers; content-addressed cache; TLS; poisoned cache eviction; source authorization; limit peer exposure across trust boundaries.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: throughput, cache hit ratio, resumed bytes, verification failures, per-site bandwidth, transfer completion time, origin egress, stalled downloads.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: interrupted transfer, cache corruption, range mismatch, slow link, origin outage, peer churn, partial disk write, simultaneous fleet fetch.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Network emulation tests verify correctness and bounded bandwidth at high loss/latency and after repeated interruption/resume cycles.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 20. Typed external API schemas

**Objective:** Define stable machine-readable interfaces for rollout, gate, rollback, state, audit, errors, and lifecycle operations with explicit compatibility rules.

**Primary integration surface:** JSON Schema/OpenAPI and/or Protobuf/WIT/RPC IDL; generated clients; compatibility checker; schema registry; conformance fixtures.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Define stable machine-readable interfaces for rollout, gate, rollback, state, audit, errors, and lifecycle operations with explicit compatibility rules.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: JSON Schema/OpenAPI and/or Protobuf/WIT/RPC IDL; generated clients; compatibility checker; schema registry; conformance fixtures.
- [ ] Define the canonical persisted/message data model, including at minimum: Schema identifiers/versions, required/optional fields, enums, bounds, oneofs/unions, timestamps, digests, error envelope, extension rules.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Wire compatibility is mechanically checked; unknown optional fields are safely ignored where specified; breaking changes require a major schema/version boundary and migration plan.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Input size/depth limits; reject duplicate/conflicting fields; canonicalization rules for signed content; no secret-bearing fields in public responses.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: schema validation failures, client/server version mix, deprecated field use, compatibility-test status, payload size.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: old/new client combinations, unknown enum, missing required field, oversized payload, duplicate keys, malformed timestamp/digest, downgrade attempt.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: CI generates clients and runs backward/forward compatibility fixtures against every supported schema version before release.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 21. Machine-readable error taxonomy

**Objective:** Provide stable, actionable error semantics across API, scheduler, transport, node execution, health gating, rollback, and persistence.

**Primary integration surface:** Shared error model; API responses; logs/traces; supervisor acknowledgements; retry engine; operator UI/runbooks.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Provide stable, actionable error semantics across API, scheduler, transport, node execution, health gating, rollback, and persistence.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Shared error model; API responses; logs/traces; supervisor acknowledgements; retry engine; operator UI/runbooks.
- [ ] Define the canonical persisted/message data model, including at minimum: error_code, category, severity, retryable, resource_type/id, operation_id, cause chain, dependency, remediation_hint, correlation_id, safe_message.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Each failure path maps to one documented stable code; retryability is explicit; wrapped causes preserve root classification; user-facing messages never expose secrets.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Redaction policy; avoid embedding raw credentials/attestation blobs; access-control sensitive details; integrity of node-originated reason codes.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: errors by code, unknown/unclassified rate, retryable vs terminal, remediation success, top failure causes, error-budget impact.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: unknown error, nested cause, multiple node failures, partial success, timeout ambiguity, dependency translation, legacy code mapping.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Contract tests assert exact error codes/fields for all major failure branches and prevent accidental semantic changes during refactors.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 22. Observability exporter

**Objective:** Emit metrics, structured logs, traces, lineage, queue and safety-state telemetry sufficient to operate and investigate GAP-08 at fleet scale.

**Primary integration surface:** OpenTelemetry/metrics backend/log sink; GAP-09; trace propagation through controller, state store, command transport, supervisor, and health gates.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Emit metrics, structured logs, traces, lineage, queue and safety-state telemetry sufficient to operate and investigate GAP-08 at fleet scale.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: OpenTelemetry/metrics backend/log sink; GAP-09; trace propagation through controller, state store, command transport, supervisor, and health gates.
- [ ] Define the canonical persisted/message data model, including at minimum: rollout_id, wave_id, node_id where cardinality permits, artifact digest, controller fence, operation_id, state transition, durations, queue age, failure code.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Telemetry never drives safety decisions unless explicitly authenticated as gate evidence; metric label cardinality is bounded; every state transition has correlated log/trace context.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Secret/PII redaction; secure exporter credentials; transport encryption; sampling rules preserve security/audit events; access controls for detailed node data.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: rollout/wave latency, rollback rate, quarantine count, deferred age, queue depth, command latency, gate evidence age, saturation, exporter drops.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: exporter outage, backend throttling, high-cardinality input, trace loss, clock skew, log disk full, telemetry storm during incident.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Operational validation shows a responder can reconstruct one failed rollout end-to-end using only supported dashboards, logs, traces, and audit references.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 23. Operator explain view

**Objective:** Expose deterministic reasoning for gate, admission, defer, quarantine, conflict, and policy outcomes without requiring source-code inspection.

**Primary integration surface:** Controller decision records; policy engine; health evidence metadata; topology engine; authorization/audit data; UI/API.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Expose deterministic reasoning for gate, admission, defer, quarantine, conflict, and policy outcomes without requiring source-code inspection.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Controller decision records; policy engine; health evidence metadata; topology engine; authorization/audit data; UI/API.
- [ ] Define the canonical persisted/message data model, including at minimum: decision_id, action, result, policy_version, evidence_refs, topology constraints, dependency health, authorization reason, failure codes, timestamps.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Displayed explanation corresponds to the exact decision revision that drove state; no post-hoc recomputation with newer policy/evidence; sensitive details are redacted by role.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: RBAC on detail levels; redact secrets/device attestation internals; protect against injection from untrusted reason strings; audit operator access where required.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: explain API latency, missing-reference rate, operator drill resolution time, top decision reasons, redaction failures.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: missing evidence, updated policy after decision, large multi-node failure, contradictory rules, localization/encoding edge cases.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Usability/incident drills require an operator to identify why a rollout stopped and the exact evidence/policy involved without privileged database access.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 24. Backup/restore and disaster-recovery procedure

**Objective:** Recover durable rollout state, policy/configuration, audit references, and control-plane service after corruption or regional loss within defined RPO/RTO.

**Primary integration surface:** State backend backups/snapshots; key/config backup; audit sink; controller deployment; restore automation; reconciliation loop.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Recover durable rollout state, policy/configuration, audit references, and control-plane service after corruption or regional loss within defined RPO/RTO.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: State backend backups/snapshots; key/config backup; audit sink; controller deployment; restore automation; reconciliation loop.
- [ ] Define the canonical persisted/message data model, including at minimum: backup_id, state revision range, consistency point, encryption key reference, created_at, retention, restore test status, audit checkpoint.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Backups are transactionally consistent; restore never reactivates stale controller ownership; reconciler compares restored desired state with actual fleet before new mutations.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Encrypted backups, separate credentials, immutable/offline copy, restore authorization, key recovery controls, periodic access review.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: backup success/age, restore duration, RPO/RTO attainment, reconciliation drift, failed restores, backup integrity checks.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: regional loss, corrupted latest backup, partial restore, missing audit receipts, stale DNS, lost key, restored state behind actual nodes.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Scheduled DR exercises restore into an isolated environment and prove controller ownership, state integrity, audit continuity, and fleet reconciliation before declaring service recovered.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 25. Compatibility matrix

**Objective:** Maintain an explicit supported-combination matrix across GAP-08, pk_core, protocol/schema versions, node runtimes, architectures, supervisors, and sibling GAP components.

**Primary integration surface:** Release metadata; CI matrix; GAP-15 certification output; package manifests; node inventory; upgrade planner.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Maintain an explicit supported-combination matrix across GAP-08, pk_core, protocol/schema versions, node runtimes, architectures, supervisors, and sibling GAP components.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Release metadata; CI matrix; GAP-15 certification output; package manifests; node inventory; upgrade planner.
- [ ] Define the canonical persisted/message data model, including at minimum: component/version, protocol/schema range, OS/runtime, architecture, supervisor version, feature flags, certification status, first/last supported release.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Rollout admission checks the matrix/certification for the actual target cohort; unsupported/unknown combinations fail before download or install.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Matrix updates are signed/reviewed; no unsigned local override; exceptions are time-bounded and audited.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: unsupported admission count, certification coverage, version distribution, deprecated combinations, exception usage.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: mixed fleet, rolling control-plane upgrade, unsupported old node, schema skew, architecture mismatch, feature-flag dependency.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: CI and staging test every supported compatibility cell and negative-test selected unsupported combinations to prove enforcement.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 26. Configuration provenance system

**Objective:** Treat rollout, retry, health-gate, topology, maintenance, and security configuration as versioned signed inputs with reproducible activation history.

**Primary integration surface:** Config repository/service; signer/approver workflow; controller config loader; environment/site overlays; rollback tooling; audit sink.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Treat rollout, retry, health-gate, topology, maintenance, and security configuration as versioned signed inputs with reproducible activation history.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Config repository/service; signer/approver workflow; controller config loader; environment/site overlays; rollback tooling; audit sink.
- [ ] Define the canonical persisted/message data model, including at minimum: config_revision/digest, parent revision, author, approver, signature, scope, effective time, overlay order, schema version, rollback target.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Every decision records the exact config revision; overlay precedence is deterministic; invalid or unsigned configuration never activates; rollback is atomic.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Signing keys protected; separation of author/approver where required; secret references rather than secret values; provenance retained with releases.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: active revision by scope, config load failures, signature rejects, drift, rollback count, propagation latency.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: bad overlay, missing field, signature failure, partial config rollout, config rollback, concurrent edit, stale controller cache.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Reproducibility test replays a historical decision using archived config/evidence and obtains the same policy result.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 27. Secrets/key handling boundary

**Objective:** Centralize credential/key lifecycle for API identities, transport, signing verification, storage access, and observability without secret leakage into state or diagnostics.

**Primary integration surface:** Secret manager/KMS/HSM; workload identity; certificate issuer; controller; state store; audit/telemetry exporters.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Centralize credential/key lifecycle for API identities, transport, signing verification, storage access, and observability without secret leakage into state or diagnostics.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Secret manager/KMS/HSM; workload identity; certificate issuer; controller; state store; audit/telemetry exporters.
- [ ] Define the canonical persisted/message data model, including at minimum: secret reference, key/cert ID, purpose, owner, rotation interval, expiry, version, revocation state; never raw secret bytes in rollout snapshots.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Secrets are fetched just-in-time or mounted through protected mechanisms; rotation does not require unsafe restart; revoked credentials stop authorizing new operations.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Least privilege, HSM/KMS for private keys where appropriate, mTLS, file ACLs, memory/log redaction, no credentials in CLI args/environment when avoidable.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: credential age/expiry, rotation success, auth failures, secret-manager latency, redaction scan findings, revoked credential use attempts.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: expired certificate, rotation during rollout, revoked token, secret manager outage, accidental log serialization, crash dump exposure.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Automated secret-scanning and rotation drills prove no snapshot/log/audit record contains raw credentials and service continuity survives credential rollover.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 28. Rollout cancellation semantics

**Objective:** Define unambiguous lifecycle semantics for pause, resume, cancel-before-touch, cancel-after-partial-apply, rollback, abandonment, and artifact disable.

**Primary integration surface:** Controller state machine; API schemas; scheduler; command transport; node acknowledgements; operator UI; audit sink.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Define unambiguous lifecycle semantics for pause, resume, cancel-before-touch, cancel-after-partial-apply, rollback, abandonment, and artifact disable.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Controller state machine; API schemas; scheduler; command transport; node acknowledgements; operator UI; audit sink.
- [ ] Define the canonical persisted/message data model, including at minimum: lifecycle_state, cancellation_type, requested_by, reason, cutoff sequence/fence, touched_nodes, in_flight_commands, resulting desired version, terminal disposition.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Each cancellation action has a documented transition table; in-flight irreversible operations are reconciled; pause never implies rollback; abandonment preserves drift visibility.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Authorization differs by operation risk; cancellation intent and actor sealed in audit; stale cancel/resume requests rejected by revision/fence.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: cancellation count/type, convergence time, in-flight drain time, orphaned commands, post-cancel drift, operator errors.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: cancel during download/install/activate/rollback, simultaneous pause/resume, cancel after gate failure, offline nodes, delayed commands.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: State-model tests cover every phase/action combination and assert the final desired/observed node states and legal next transitions.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 29. Quarantine recovery workflow

**Objective:** Provide a controlled remediation path for nodes quarantined after rollback/install failures and require explicit evidence before returning them to service.

**Primary integration surface:** Quarantine inventory; GAP-01 supervisor; reimage/recovery tooling; GAP-06 identity; health/compatibility checks; operator approval.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Provide a controlled remediation path for nodes quarantined after rollback/install failures and require explicit evidence before returning them to service.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Quarantine inventory; GAP-01 supervisor; reimage/recovery tooling; GAP-06 identity; health/compatibility checks; operator approval.
- [ ] Define the canonical persisted/message data model, including at minimum: quarantine_case_id, node_id, rollout_id, cause, bad/desired version, evidence, remediation plan, attempts, approver, release criteria, released_at.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Quarantined nodes are excluded from normal rollout progression and service capacity assumptions where appropriate; release requires completed remediation and fresh validation.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Restricted recovery role; secure reimage; re-attestation after hardware/software remediation; immutable case audit; prevent self-release by compromised node.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: quarantine population/age, recovery success, repeat quarantine, time-to-remediate, causes, manual override use.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: failed reimage, persistent hardware fault, identity change, repeated bad boot, operator abort, missing evidence, site capacity pressure.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Recovery drills take a deliberately broken node from rollback failure through reimage/attestation/health verification to explicit, audited release.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 30. Fleet reconciliation loop

**Objective:** Continuously compare desired rollout state with authoritative observed node versions/health so drift and missed acknowledgements are repaired or escalated after restart.

**Primary integration surface:** Desired state store; GAP-01 observed-state inventory; command transport; deferred/quarantine scheduler; policy engine.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Continuously compare desired rollout state with authoritative observed node versions/health so drift and missed acknowledgements are repaired or escalated after restart.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Desired state store; GAP-01 observed-state inventory; command transport; deferred/quarantine scheduler; policy engine.
- [ ] Define the canonical persisted/message data model, including at minimum: node_id, desired_version/digest, observed_version/digest, last_observed_at, rollout association, divergence reason, remediation action, attempt history.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Reconciliation is idempotent; stale observations are not treated as truth; quarantined/canceled nodes follow their own policies; unexpected newer/foreign versions are never overwritten without policy.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Authenticated observed state; anti-spoofing via device identity; authorization for corrective commands; protect against compromised inventory source.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: drift count/age, reconciliation latency, corrective actions, stale observations, unknown versions, repeated divergence.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: missed ack, controller restart, manual node change, partial rollback, stale inventory, node replacement, split-brain observed sources.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Restart tests delete transient controller memory and prove reconciliation reconstructs the true fleet state without duplicate or unsafe commands.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

# P2 — Certification, scale, and governance

## 31. Property/fuzz testing

**Objective:** Systematically discover state-machine, parser, serialization, identifier, and invariant failures using generated and adversarial inputs.

**Primary integration surface:** rollout.py public API; snapshot/from_snapshot; API schemas; verification/gate payload parsers; error taxonomy; corpus minimizer.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Systematically discover state-machine, parser, serialization, identifier, and invariant failures using generated and adversarial inputs.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: rollout.py public API; snapshot/from_snapshot; API schemas; verification/gate payload parsers; error taxonomy; corpus minimizer.
- [ ] Define the canonical persisted/message data model, including at minimum: Generated waves/nodes/state snapshots, Unicode/long identifiers, numeric boundaries, malformed JSON, duplicate keys where parser permits, huge nested structures, corrupt digests.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: All safety invariants hold for every generated sequence; invalid input terminates with documented bounded errors; no crash permits an unsafe state transition.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Include hostile payloads for injection, path traversal in identifiers, resource exhaustion, malformed signatures/digests, and replay metadata.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: cases/sec, unique failures, minimized counterexamples, coverage/state-transition coverage, timeout/OOM incidence.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: serialization round-trip, mutation between operations, snapshot tamper, huge wave sets, empty/duplicate topology, invalid state transitions.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: CI runs deterministic seeded suites plus scheduled extended fuzzing; every discovered defect becomes a permanent regression corpus entry.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 32. Concurrency/race testing

**Objective:** Verify correctness under simultaneous state mutations, retries, rollback, reconciliation, controller failover, and operator actions.

**Primary integration surface:** Persistent store, lease/fencing, command scheduler, API handlers, deferred scheduler, emergency controls, audit sink.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Verify correctness under simultaneous state mutations, retries, rollback, reconciliation, controller failover, and operator actions.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Persistent store, lease/fencing, command scheduler, API handlers, deferred scheduler, emergency controls, audit sink.
- [ ] Define the canonical persisted/message data model, including at minimum: operation interleavings, expected revision/fence, transaction result, emitted command IDs, resulting lifecycle state, audit sequence.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Linearizable/defined consistency points are documented; stale writers are rejected; terminal safety state cannot be undone by lower-revision concurrent action.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Race tests include privilege/policy changes and stale auth tokens; audit order cannot be forged through concurrent writers.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: conflict rate, stale-write rejects, invariant violations, duplicate commands, deadlocks/livelocks, tail latency under contention.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: rollback vs next wave, pause vs resume, cancel vs retry-deferred, failover vs snapshot, duplicate admission, freeze vs command issue.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: A deterministic scheduler/model checker or high-volume race harness executes targeted interleavings and demonstrates zero invariant violations across the supported concurrency model.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 33. Network-partition/fault-injection harness

**Objective:** Exercise realistic partial failures across controller, state store, health, audit, content, command transport, and node supervisors.

**Primary integration surface:** Traffic proxy/fault injector; dependency emulators; clock controls; controller cluster; test fleet; observability assertions.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Exercise realistic partial failures across controller, state store, health, audit, content, command transport, and node supervisors.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Traffic proxy/fault injector; dependency emulators; clock controls; controller cluster; test fleet; observability assertions.
- [ ] Define the canonical persisted/message data model, including at minimum: fault plan, target link/service, latency/loss/reorder/partition parameters, start/stop time, expected safe state, recovery criterion.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Every injected fault maps to a documented safety response; recovery never requires assuming a lost command succeeded; stale controllers remain fenced.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Include TLS/auth failures, replayed messages, corrupted responses, and compromised-looking evidence in addition to availability faults.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: fault detection time, safe-state transition time, recovery convergence, data loss, duplicate operations, blocked rollouts.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: split brain, lost acks, delayed gate evidence, state-store quorum loss, stale lease, partial site outage, reconnect storm, audit sink partition.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Automated chaos scenarios assert both positive behavior and forbidden behavior—for example, no new wave while health evidence is stale or ownership is uncertain.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 34. Fleet-scale benchmark suite

**Objective:** Characterize controller and dependency performance at representative and worst-case fleet sizes to set defensible capacity limits and SLOs.

**Primary integration surface:** Load generator; state backend; command broker; health adapter; audit sink; metrics profiler; representative topology/artifact metadata.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Characterize controller and dependency performance at representative and worst-case fleet sizes to set defensible capacity limits and SLOs.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Load generator; state backend; command broker; health adapter; audit sink; metrics profiler; representative topology/artifact metadata.
- [ ] Define the canonical persisted/message data model, including at minimum: fleet size, rollouts, nodes/wave, deferred ratio, command rate, state size, artifact metadata size, dependency latency distribution, hardware profile.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Benchmarks use production-equivalent settings; results include p50/p95/p99/max and saturation point; safety checks remain enabled during tests.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Synthetic credentials/test identities only; benchmark cannot bypass authn/authz/signature validation in a way that hides production costs.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: latency/throughput, CPU, RSS, GC, disk IOPS, network, queue depth, state growth, audit throughput, error rate.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: steady rollout, mass rollback, reconnect storm, many small rollouts, huge rollout, slow health backend, store contention.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Release criteria define supported fleet/concurrency envelopes with headroom, and CI/performance lab flags statistically significant regression.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 35. Long-duration soak tests

**Objective:** Detect memory/resource leaks, unbounded state/audit growth, timer drift, retry accumulation, and reconciliation instability over days or weeks.

**Primary integration surface:** Production-like controller cluster; durable store; broker; synthetic fleet; rotating dependencies; metrics/heap/file-descriptor monitoring.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Detect memory/resource leaks, unbounded state/audit growth, timer drift, retry accumulation, and reconciliation instability over days or weeks.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Production-like controller cluster; durable store; broker; synthetic fleet; rotating dependencies; metrics/heap/file-descriptor monitoring.
- [ ] Define the canonical persisted/message data model, including at minimum: test epoch, cumulative rollouts, state revisions, audit events, deferred churn, restart count, memory/FD/thread counts, storage growth.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Resource usage reaches bounded steady behavior or documented linear retention growth; no timer/retry queue silently drifts; repeated restart retains invariants.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Credentials rotate during the soak; audit/telemetry redaction continues to hold; stale credentials are rejected.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: memory/FD/thread trend, store size/event, queue age, timer skew, error drift, reconciliation backlog, restart recovery.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: continuous deferred flapping, frequent rollouts, periodic rollback, controller restart, dependency outages, config rotations, clock correction.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Soak exit criteria include no unexplained resource slope, no invariant breach, and successful integrity verification of final persisted/audit state.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 36. Power-loss/device-reboot certification

**Objective:** Certify update/rollback behavior when edge hardware loses power or reboots at any installation or activation phase.

**Primary integration surface:** Physical/HIL test rig; programmable power control; node installer; bootloader; supervisor; controller; serial/remote recovery capture.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Certify update/rollback behavior when edge hardware loses power or reboots at any installation or activation phase.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Physical/HIL test rig; programmable power control; node installer; bootloader; supervisor; controller; serial/remote recovery capture.
- [ ] Define the canonical persisted/message data model, including at minimum: device model/revision, storage type, installer phase, power-cut offset, boot result, active slot/version, journal state, recovery action, data integrity.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: After every power interruption the device boots a known-good verified image or enters a bounded recoverable quarantine/recovery mode; no endless boot loop is accepted.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Secure/verified boot remains enforced after interruption; recovery paths cannot downgrade verification or expose maintenance credentials.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: successful recovery %, boot time, rollback time, corrupted storage count, manual recovery count, wear indicators.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: cut during download/write/fsync/metadata swap/boot mark-good/rollback; repeated brownout; battery depletion; watchdog reset.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Certification matrix covers every supported hardware/storage/bootloader combination and archives reproducible test evidence per release.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 37. Release acceptance evidence bundle

**Objective:** Produce machine-readable, signed evidence linking every release requirement to test, schema, provenance, SBOM, benchmark, and approval artifacts.

**Primary integration surface:** CI/CD; test reports; checklist IDs; release manifest; SBOM; provenance/signatures; benchmark results; audit seal; artifact repository.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Produce machine-readable, signed evidence linking every release requirement to test, schema, provenance, SBOM, benchmark, and approval artifacts.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: CI/CD; test reports; checklist IDs; release manifest; SBOM; provenance/signatures; benchmark results; audit seal; artifact repository.
- [ ] Define the canonical persisted/message data model, including at minimum: release_id/version, commit, artifact digests, checklist requirement IDs, evidence URI/digest, test result, environment, tool version, signer, timestamp.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Every mandatory requirement has current evidence for the exact released bytes; stale or mismatched evidence fails release; evidence bundle is immutable and reproducible.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Signing/attestation of evidence; protected CI identity; provenance/SLSA-style metadata where applicable; retention and access controls.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: coverage percentage, missing/stale evidence, signature verification, release gate duration, waived requirements and expiry.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: rerun after code change, missing evidence, test from wrong commit, mutable URI, failed signature, benchmark regression, unsupported dependency version.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Independent verification from a clean environment can validate the release artifact digest and trace every required checklist item to authentic evidence without trusting the build workspace.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 38. SBOM and vulnerability response process

**Objective:** Inventory shipped software and dependencies and provide a repeatable process to assess, patch, release, and retire vulnerable components.

**Primary integration surface:** SBOM generator; dependency lockfiles; vulnerability scanners/advisories; ticketing; release pipeline; artifact provenance.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Inventory shipped software and dependencies and provide a repeatable process to assess, patch, release, and retire vulnerable components.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: SBOM generator; dependency lockfiles; vulnerability scanners/advisories; ticketing; release pipeline; artifact provenance.
- [ ] Define the canonical persisted/message data model, including at minimum: package/component, version, supplier, license, hashes, dependency relationship, vulnerability IDs, severity, exploitability, disposition, fix/EOL date.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: SBOM corresponds to released bytes; vulnerabilities are triaged against runtime reachability; patch SLA varies by severity/exploitability; EOL dependencies block release per policy.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Verify package signatures where available; defend dependency confusion/typosquatting; restrict registries; protect CI credentials; attest build provenance.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: open vulns by severity/age, SLA breaches, SBOM completeness, dependency freshness, emergency release lead time.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: new critical CVE, compromised dependency, unavailable patch, false positive, transitive vulnerability, emergency rollback, EOL package.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Tabletop and practical exercises take a newly disclosed critical dependency flaw through impact analysis, patched build, regression verification, signed release, and fleet rollout.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 39. Architecture Decision Record (ADR)

**Objective:** Record the approved architecture and tradeoffs for storage consistency, ownership/fencing, transport semantics, audit sealing, threat model, and subsystem boundaries.

**Primary integration surface:** ADR repository; architecture review; threat model; diagrams; benchmark/test evidence; related GAP contracts.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Record the approved architecture and tradeoffs for storage consistency, ownership/fencing, transport semantics, audit sealing, threat model, and subsystem boundaries.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: ADR repository; architecture review; threat model; diagrams; benchmark/test evidence; related GAP contracts.
- [ ] Define the canonical persisted/message data model, including at minimum: ADR ID/status, context, decision, alternatives, consequences, assumptions, security implications, migration/reversal plan, approvers, superseded-by links.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Implemented behavior matches accepted ADRs; material architectural changes require a new/superseding decision; unresolved assumptions are tracked as risks.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Threat model includes privileged local attacker, compromised node, stale controller, malicious artifact/evidence, dependency outage, and credential theft.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: open ADR actions, superseded decisions, architecture drift findings, review age, unresolved risks.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: consistency-model change, transport switch, topology-policy change, audit backend change, single-to-multi-controller migration.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Architecture review can trace each major safety mechanism in GAP-08 to an approved decision, evidence, owner, and rollback/migration strategy.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

## 40. Named owner/escalation artifact

**Objective:** Define accountable service ownership, incident/on-call paths, security escalation, exception/waiver owners, and expiry for operational governance.

**Primary integration surface:** Service catalog; on-call system; incident management; security response; release/checklist evidence; exception registry.

### Engineering and assurance checklist

- [ ] Document the component boundary and normative objective: Define accountable service ownership, incident/on-call paths, security escalation, exception/waiver owners, and expiry for operational governance.
- [ ] Produce a sequence/data-flow diagram covering these integration surfaces: Service catalog; on-call system; incident management; security response; release/checklist evidence; exception registry.
- [ ] Define the canonical persisted/message data model, including at minimum: service owner/team, technical owner, on-call rotation, escalation levels, incident severity mapping, security contact, waiver owner, expiry/review date.
- [ ] Assign stable schema identifiers and semantic versions to every externally persisted or transmitted structure; document backward/forward compatibility and migration rules.
- [ ] Define globally unique identifiers, correlation IDs, idempotency keys, and causal linkage between rollout, wave, node operation, gate, rollback, audit, and recovery records where applicable.
- [ ] Encode the safety invariants as executable validation/guards rather than documentation-only checks: Every production alert and waiver resolves to an active owner; expired ownership/waivers are automatically surfaced; no critical control can be permanently exempted without review.
- [ ] Specify the lifecycle/state-transition table, including legal states, legal transitions, terminal states, restart behavior, and behavior for repeated/out-of-order requests.
- [ ] Specify transaction/consistency boundaries and exactly where an operation is considered accepted, committed, externally visible, acknowledged, and recoverable after process loss.
- [ ] Define timeout/deadline semantics for every external call and prohibit unbounded waits; state whether timeout means unknown outcome, retryable failure, or terminal failure.
- [ ] Define retry semantics only for operations that are idempotent or protected by deduplication; cap attempts and total deadline and include randomized backoff/jitter where retry is permitted.
- [ ] Implement and document the security boundary, including authentication, authorization, integrity, confidentiality, credential handling, and least privilege: Restrict editing of owner/escalation data; audit changes; protect personal contact data; break-glass escalation path tested.
- [ ] Threat-model replay, downgrade, stale-data acceptance, confused-deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, and malicious-but-well-formed input.
- [ ] Apply fail-closed behavior to missing, stale, unverifiable, or unauthorized safety-critical inputs unless a separately documented and audited emergency policy explicitly permits otherwise.
- [ ] Define machine-readable error codes for validation failure, dependency unavailability, conflict, timeout, stale revision/fence, authorization denial, integrity failure, and terminal execution failure.
- [ ] Instrument operational telemetry with bounded-cardinality metrics, structured logs, trace correlation, and alertable safety signals; include at minimum: unowned alerts, escalation latency, stale owner records, waiver age/expiry, incident acknowledgment, after-hours reachability.
- [ ] Ensure logs, traces, state snapshots, audit records, and operator views redact credentials, private keys, bearer tokens, raw attestation secrets, and any other prohibited sensitive values.
- [ ] Define resource/capacity limits for payload size, queue depth, concurrency, memory/disk growth, request rate, retry amplification, and per-rollout/per-site work; fail predictably when limits are reached.
- [ ] Create deterministic fault-injection scenarios for: owner leaves team, on-call gap, expired waiver, simultaneous incidents, security incident after hours, stale service catalog.
- [ ] Create positive and negative unit tests for every state transition and safety guard, including repeated calls, malformed inputs, boundary values, and optimizer/runtime modes used in production.
- [ ] Create contract/integration tests against realistic sibling-service doubles or staging services, verifying schema compatibility, authentication, timeout, retry, and failure-translation behavior.
- [ ] Create restart/recovery tests that terminate the controller/process at unsafe timing points, restore from durable state, validate integrity, and prove no already-completed side effect is duplicated.
- [ ] Create concurrency tests for simultaneous operator/API/controller actions and prove stale revisions, stale fencing tokens, duplicate commands, and conflicting transitions cannot violate invariants.
- [ ] Create scale/performance tests with production-equivalent safety checks enabled; establish p50/p95/p99 and saturation limits and convert them into explicit supported-capacity envelopes/SLOs.
- [ ] Publish operator runbooks covering normal deployment, degraded dependency behavior, rollback, emergency stop/freeze, recovery, reconciliation, escalation, and interpretation of error/telemetry signals relevant to this component.
- [ ] Require configuration-as-code or an equivalent versioned configuration source with provenance, review/approval, environment/site scoping, safe defaults, validation, and atomic rollback of configuration changes.
- [ ] Add CI release gates that fail on schema incompatibility, failed tests, missing evidence, security scanning failure, unresolved critical defect, or mismatch between evidence and the exact release artifact.
- [ ] Define objective Definition-of-Done evidence and archive it with the release: Quarterly governance drill confirms an independent responder can identify the correct operational and security owners and that escalation channels function end-to-end.
- [ ] Assign a named owner, operational escalation path, security escalation path, review cadence, and time-bounded waiver process for any requirement not yet met.

### Component release gate

- [ ] Demonstrate the component in a representative end-to-end rollout scenario with success, controlled failure, restart, and recovery paths.
- [ ] Attach evidence identifiers/digests for implementation, tests, security review, observability, runbook, and acceptance result to the GAP-08 release evidence bundle.
- [ ] Record residual risks, temporary waivers, owners, expiry dates, and compensating controls; no unowned or indefinite P0 waiver is permitted.

# Required sibling/upstream integration readiness

The following systems remain outside GAP-08's implementation boundary, but GAP-08 cannot be production-ready unless these contracts are implemented and verified end-to-end.

## GAP-07 Artifact provenance/signing
- [ ] Define the exact `PK_VERIFICATION/1` or successor schema fields GAP-08 consumes, including artifact digest, subject identity, provenance/signature result, verifier identity, verification time, and expiry/freshness policy.
- [ ] Require the verification subject to be the exact artifact digest/content later distributed and installed, not only a mutable logical name.
- [ ] Test rejection of wrong-subject, stale, malformed, unsigned/untrusted, revoked, and algorithm-downgraded verification evidence.
- [ ] Persist the verification evidence digest/reference in rollout state and external audit records.
- [ ] Define behavior when provenance/signing service is unavailable after rollout admission but before later deferred retries.

## GAP-09 Unified observability
- [ ] Define authenticated health-evidence schema, source identity, freshness limit, observation window, aggregation policy, and minimum sample coverage for every gate class.
- [ ] Prohibit a raw caller-provided boolean from satisfying a production health gate.
- [ ] Bind evidence to rollout/wave/cohort identifiers and reject cross-rollout reuse.
- [ ] Test stale, replayed, partial, contradictory, and unavailable telemetry cases.
- [ ] Ensure GAP-08 operational telemetry and GAP-09 gate evidence can be correlated by rollout/wave/node identifiers without uncontrolled metric cardinality.

## GAP-01 Edge Node Supervisor
- [ ] Define fenced, idempotent commands for drain, stage, install, activate/restart, rollback, quarantine, and observed-state reporting.
- [ ] Require authenticated acknowledgements bound to command ID, node identity, rollout ID, fencing token, and resulting observed version/digest.
- [ ] Specify timeout, retry, duplicate, stale-command, reboot, and partial-execution behavior for every command.
- [ ] Verify transactional installer and rollback behavior under power loss/reboot on supported hardware.
- [ ] Feed terminal failures into GAP-08 quarantine and reconciliation rather than translating unknown outcomes into success.

## GAP-15 Runtime compatibility certification
- [ ] Define certification evidence bound to artifact digest, node/runtime profile, architecture, supervisor version, and relevant feature flags.
- [ ] Enforce certification before first mutation and again for deferred nodes when compatibility evidence may have expired or node state changed.
- [ ] Test mixed-version/mixed-architecture fleets and unsupported combinations.
- [ ] Version and publish the compatibility matrix consumed by GAP-08.
- [ ] Fail closed on missing/unknown/expired compatibility evidence unless an explicitly governed emergency policy applies.

## GAP-06 Device identity and attestation
- [ ] Bind controller commands and node acknowledgements to authenticated device identity.
- [ ] Verify attestation freshness/nonces and required boot/runtime measurements before trusting sensitive acknowledgements.
- [ ] Handle certificate/key rotation, revocation, device replacement, and identity mismatch.
- [ ] Prevent a valid acknowledgement from one node being replayed for another node.
- [ ] Record identity/attestation evidence references without persisting raw secrets.

## Topology/hardware discovery services
- [ ] Supply authoritative fault-domain and device-class attributes with version/freshness metadata.
- [ ] Define the policy behavior for unknown/stale topology; protected-domain scheduling must fail closed.
- [ ] Revalidate topology constraints before each wave when the inventory may have changed since rollout creation.
- [ ] Exercise concurrent site/rack/device failures and prove the blast-radius engine preserves configured survivor/quorum margins.
- [ ] Audit topology-policy overrides and require explicit bounded authorization.

# Final GAP-08 production-readiness sign-off

- [ ] All P0 sections have complete implementation and acceptance evidence for the exact release candidate.
- [ ] P1 gaps are either complete or governed by explicit, time-bounded production risk acceptance with compensating controls.
- [ ] P2 certification/scale/governance items required by the deployment's risk tier are complete and evidenced.
- [ ] End-to-end chaos test covers stale controller, state-store failover, lost acknowledgements, health-service outage, audit-sink outage, node rollback failure, and reconnect storm in a single controlled campaign.
- [ ] Disaster-recovery exercise restores control-plane state and reconciles against actual fleet state before allowing new mutations.
- [ ] Security review verifies identity, authorization, fencing, anti-replay, artifact binding, audit sealing, secret handling, and emergency-control separation of duties.
- [ ] Operations review verifies alerts, dashboards, explainability, runbooks, on-call ownership, escalation, maintenance windows, and emergency freeze/rollback procedures.
- [ ] Release manager verifies all evidence digests, SBOM/provenance, compatibility matrix, ADRs, benchmarks, and signed release metadata are archived and reproducible.
