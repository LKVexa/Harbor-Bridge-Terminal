# GAP-03 Topology-Aware Scheduler — Missing Components Engineering Checklist

**Derived from:** `gap03_topology_aware_scheduler_v4.2.0_MISSING_COMPONENTS.md`  
**Target baseline:** GAP-03 v4.2.0  
**Checklist scope:** MC-001 through MC-046  
**Checklist density:** 30 implementation/certification checks per component (1,380 component checks total), plus program-level gates  

## Purpose and use

This checklist converts the v4.2.0 missing-component inventory into an implementation-grade engineering and certification plan. A checkbox is complete only when the implementation exists **and** objective evidence is attached. Design-only, prose-only, or “planned” work does not satisfy an implementation control unless that control explicitly calls for documentation.

### Evidence convention

For each completed checkbox, retain one or more of: source path/commit, schema/IDL, ADR, automated test ID/report, benchmark result, threat-model entry, security scan, signed manifest/attestation, operational runbook, dashboard/alert definition, deployment record, or approval record. Evidence should be addressable by immutable version/digest where practical.

### Global completion rules

- [ ] **PG-001 — No silent fail-open:** Any unavailable security/identity/authoritative-state dependency has an explicitly documented fail-open/fail-closed rule and automated test.
- [ ] **PG-002 — Determinism:** Identical immutable inputs and software/config versions produce identical ranking/explain outputs unless a documented non-deterministic signal is intentionally present.
- [ ] **PG-003 — Bounded resources:** Every external input, queue, cache, retry loop, parser, and telemetry buffer has enforced size/time/cardinality/concurrency bounds.
- [ ] **PG-004 — Stable identity and versioning:** Public schemas, APIs, errors, configuration, state migrations, and evidence artifacts have explicit version identifiers and compatibility rules.
- [ ] **PG-005 — Distributed safety:** Process-local locks are never treated as distributed ownership; all cross-replica mutation paths use durable atomicity and/or fencing appropriate to the selected architecture.
- [ ] **PG-006 — Auditable privileged change:** Topology, entitlement, trust, freeze/quarantine, configuration, release, and waiver mutations record actor, reason, before/after identity, and resulting generation.
- [ ] **PG-007 — Test independence:** Critical tests can run in CI without undeclared local files/services; external integrations use versioned fixtures or explicit integration environments.
- [ ] **PG-008 — Negative-path coverage:** Malformed, stale, duplicate, replayed, unauthorized, over-capacity, partitioned, timeout, crash, and recovery behaviors are covered for all critical mutation workflows.
- [ ] **PG-009 — Operator recoverability:** Every production-affecting stateful subsystem has documented rollback/reconciliation/restore procedures that have been exercised.
- [ ] **PG-010 — Exit evidence:** Production promotion consumes the formal evidence bundle and fails closed when mandatory P0/P1 evidence is absent, stale, mismatched, or associated with a different artifact digest.

---

# P0 — Required before a production control-plane deployment

All P0 controls inherit the global completion rules above.

---

## MC-001 — Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`

**Priority:** P0  
**Need:** The contract names interfaces but supplies no typed external schema, parser, compatibility rules, or generated bindings.  
**Related controls:** C021-C022, C026-C029, C082  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-001-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`**; explicitly state what remains owned by adjacent services.
- [ ] **MC-001-CHK-002** — Assign an accountable owner and reviewer set for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-001-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-001-CHK-004** — Define the canonical data/state model for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-001-CHK-005** — Document safety/correctness invariants for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-001-CHK-006** — Define normative external schemas for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1` using an explicitly selected IDL/serialization format; assign stable schema IDs, package namespaces, semantic versions, and media/content types.
- [ ] **MC-001-CHK-007** — Specify every field with canonical type, units, numeric bounds, nullability, required/optional status, default semantics, enum evolution rules, and maximum encoded length; prohibit ambiguous implicit unit conversion.
- [ ] **MC-001-CHK-008** — Define compatibility policy for additive/removal/type-changing edits, unknown fields, unknown enum values, reserved field numbers/names, deprecated fields, and minimum/maximum supported peer versions.
- [ ] **MC-001-CHK-009** — Implement resource-bounded parsers that reject malformed, duplicate, non-canonical, over-depth, over-size, NaN/Inf, integer-overflow, and schema-confused payloads before they reach scheduling logic.
- [ ] **MC-001-CHK-010** — Generate or maintain typed bindings for every supported runtime and ensure generated artifacts are pinned to the exact schema compiler/runtime version used by CI.
- [ ] **MC-001-CHK-011** — Add a schema registry or immutable release location with content digests; require runtime schema fingerprint/version negotiation before accepting peer payloads.
- [ ] **MC-001-CHK-012** — Create canonical positive, boundary, backward-compatibility, forward-compatibility, malformed, and adversarial fixtures for all three interfaces.
- [ ] **MC-001-CHK-013** — Define deterministic canonical serialization where signatures/hashes/idempotency keys depend on payload identity; document field ordering and normalization requirements.
- [ ] **MC-001-CHK-014** — Provide explicit schema migration/conversion functions between supported major/minor versions and test round-trip semantic preservation.
- [ ] **MC-001-CHK-015** — Publish machine-readable API reference, compatibility matrix, deprecation schedule, and release notes; make schema compatibility validation a blocking CI gate.
### Security & trust

- [ ] **MC-001-CHK-016** — Complete a threat-model pass for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-001-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`**; default to least privilege and explicitly test denied access.
- [ ] **MC-001-CHK-018** — Apply strict untrusted-input validation and resource limits to **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-001-CHK-019** — Determine cryptographic/secret-management requirements for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-001-CHK-020** — Ensure sensitive data handled by **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-001-CHK-021** — Create a failure-mode and recovery table for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-001-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-001-CHK-023** — Expose structured metrics/logs/traces/health for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-001-CHK-024** — Provide an operator runbook for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-001-CHK-025** — Implement unit tests for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-001-CHK-026** — Implement integration/contract tests for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-001-CHK-027** — Add fault/adversarial tests for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-001-CHK-028** — Benchmark or capacity-test **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-001-CHK-029** — Link **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-001-CHK-030** — Package production evidence for **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-001 definition of done

- [ ] All **30 MC-001 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Versioned wire/schema definitions for `PK_TOPOLOGY/1`, `PK_LOCALITY_COST/1`, and `PK_FAIR_SHARE/1`** satisfies its stated need: The contract names interfaces but supplies no typed external schema, parser, compatibility rules, or generated bindings.
- [ ] Required controls **C021-C022, C026-C029, C082** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-001.

---

## MC-002 — Authenticated topology mutation boundary

**Priority:** P0  
**Need:** `Topology.place()` is local logic; there is no identity verification for the actor allowed to add or re-parent nodes.  
**Related controls:** C023-C024, C041-C044  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-002-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Authenticated topology mutation boundary**; explicitly state what remains owned by adjacent services.
- [ ] **MC-002-CHK-002** — Assign an accountable owner and reviewer set for **Authenticated topology mutation boundary** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-002-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Authenticated topology mutation boundary**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-002-CHK-004** — Define the canonical data/state model for **Authenticated topology mutation boundary**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-002-CHK-005** — Document safety/correctness invariants for **Authenticated topology mutation boundary** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-002-CHK-006** — Place all topology mutations behind an authenticated service boundary using mutually authenticated transport or an equivalent workload identity mechanism; reject anonymous mutation calls.
- [ ] **MC-002-CHK-007** — Define RBAC/ABAC permissions for create, relabel, re-parent, quarantine, delete, bulk import, and emergency override operations; treat re-parenting and mass mutation as elevated privileges.
- [ ] **MC-002-CHK-008** — Bind each request to actor identity, trust domain, request ID, nonce/idempotency key, source service, topology generation precondition, and authorization decision.
- [ ] **MC-002-CHK-009** — Use optimistic concurrency control against topology generation/revision so mutations based on stale topology are rejected rather than silently overwriting newer state.
- [ ] **MC-002-CHK-010** — Validate the complete proposed mutation atomically before commit, including parent existence, cycle prevention, hierarchy type constraints, label canonicalization, uniqueness, and policy restrictions.
- [ ] **MC-002-CHK-011** — Require explicit `replace/reparent` intent for parent changes and optionally two-person approval or policy authorization for high-blast-radius topology rewrites.
- [ ] **MC-002-CHK-012** — Persist before/after state, actor, reason, policy decision, correlation ID, and resulting generation in the tamper-evident audit trail.
- [ ] **MC-002-CHK-013** — Apply per-principal and global rate limits, request-size limits, bulk-operation limits, and circuit breakers to prevent mutation storms from destabilizing the scheduler.
- [ ] **MC-002-CHK-014** — Support signed mutation envelopes or equivalent request integrity protection where mutations may traverse untrusted intermediaries; verify freshness to prevent replay.
- [ ] **MC-002-CHK-015** — Implement transaction rollback/compensation and deterministic error codes so partial topology mutations cannot leak into the active scheduling snapshot.
### Security & trust

- [ ] **MC-002-CHK-016** — Complete a threat-model pass for **Authenticated topology mutation boundary** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-002-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Authenticated topology mutation boundary**; default to least privilege and explicitly test denied access.
- [ ] **MC-002-CHK-018** — Apply strict untrusted-input validation and resource limits to **Authenticated topology mutation boundary** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-002-CHK-019** — Determine cryptographic/secret-management requirements for **Authenticated topology mutation boundary**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-002-CHK-020** — Ensure sensitive data handled by **Authenticated topology mutation boundary** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-002-CHK-021** — Create a failure-mode and recovery table for **Authenticated topology mutation boundary** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-002-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Authenticated topology mutation boundary** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-002-CHK-023** — Expose structured metrics/logs/traces/health for **Authenticated topology mutation boundary** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-002-CHK-024** — Provide an operator runbook for **Authenticated topology mutation boundary** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-002-CHK-025** — Implement unit tests for **Authenticated topology mutation boundary** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-002-CHK-026** — Implement integration/contract tests for **Authenticated topology mutation boundary** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-002-CHK-027** — Add fault/adversarial tests for **Authenticated topology mutation boundary** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-002-CHK-028** — Benchmark or capacity-test **Authenticated topology mutation boundary** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-002-CHK-029** — Link **Authenticated topology mutation boundary** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-002-CHK-030** — Package production evidence for **Authenticated topology mutation boundary** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-002 definition of done

- [ ] All **30 MC-002 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Authenticated topology mutation boundary** satisfies its stated need: `Topology.place()` is local logic; there is no identity verification for the actor allowed to add or re-parent nodes.
- [ ] Required controls **C023-C024, C041-C044** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-002.

---

## MC-003 — Tenant entitlement / reservation authority

**Priority:** P0  
**Need:** The runtime validates numbers but cannot prove that a tenant is entitled to declare a given reserved share.  
**Related controls:** C017, C024, C041-C046  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-003-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Tenant entitlement / reservation authority**; explicitly state what remains owned by adjacent services.
- [ ] **MC-003-CHK-002** — Assign an accountable owner and reviewer set for **Tenant entitlement / reservation authority** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-003-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Tenant entitlement / reservation authority**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-003-CHK-004** — Define the canonical data/state model for **Tenant entitlement / reservation authority**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-003-CHK-005** — Document safety/correctness invariants for **Tenant entitlement / reservation authority** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-003-CHK-006** — Define the authoritative entitlement source for tenant reservations and quotas, including ownership, update API, trust root, and failure behavior when that authority is unreachable.
- [ ] **MC-003-CHK-007** — Define a reservation/entitlement record containing tenant identity, resource dimension, capacity unit, reserved quantity/share, hard/soft limit, effective time, expiry, issuer, version, and signature/provenance.
- [ ] **MC-003-CHK-008** — Normalize all capacity and reservation quantities into canonical units before comparison; reject cross-dimension or negative/overflow values.
- [ ] **MC-003-CHK-009** — Validate that aggregate reservations cannot exceed policy-defined physical or oversubscription limits unless an explicitly approved oversubscription policy is active.
- [ ] **MC-003-CHK-010** — Use signed/versioned entitlement snapshots and bind scheduler decisions to the exact entitlement generation used during scoring and commit.
- [ ] **MC-003-CHK-011** — Implement revocation and expiry handling with bounded propagation delay; ensure revoked entitlement cannot continue authorizing new claims after its validity window.
- [ ] **MC-003-CHK-012** — Define conflict resolution for concurrent entitlement updates, including monotonic revisions, compare-and-swap semantics, and deterministic handling of stale issuers.
- [ ] **MC-003-CHK-013** — Enforce tenant isolation so one tenant cannot enumerate, mutate, or consume another tenant’s reservation state beyond aggregate metadata intentionally exposed by policy.
- [ ] **MC-003-CHK-014** — Build periodic reconciliation between authoritative entitlement state and the local fair-share ledger, producing explicit drift events and safe correction procedures.
- [ ] **MC-003-CHK-015** — Provide admission tests for zero reservation, full reservation, oversubscription, expired entitlement, revoked entitlement, stale snapshot, malformed issuer data, and authority outage.
### Security & trust

- [ ] **MC-003-CHK-016** — Complete a threat-model pass for **Tenant entitlement / reservation authority** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-003-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Tenant entitlement / reservation authority**; default to least privilege and explicitly test denied access.
- [ ] **MC-003-CHK-018** — Apply strict untrusted-input validation and resource limits to **Tenant entitlement / reservation authority** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-003-CHK-019** — Determine cryptographic/secret-management requirements for **Tenant entitlement / reservation authority**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-003-CHK-020** — Ensure sensitive data handled by **Tenant entitlement / reservation authority** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-003-CHK-021** — Create a failure-mode and recovery table for **Tenant entitlement / reservation authority** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-003-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Tenant entitlement / reservation authority** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-003-CHK-023** — Expose structured metrics/logs/traces/health for **Tenant entitlement / reservation authority** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-003-CHK-024** — Provide an operator runbook for **Tenant entitlement / reservation authority** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-003-CHK-025** — Implement unit tests for **Tenant entitlement / reservation authority** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-003-CHK-026** — Implement integration/contract tests for **Tenant entitlement / reservation authority** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-003-CHK-027** — Add fault/adversarial tests for **Tenant entitlement / reservation authority** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-003-CHK-028** — Benchmark or capacity-test **Tenant entitlement / reservation authority** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-003-CHK-029** — Link **Tenant entitlement / reservation authority** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-003-CHK-030** — Package production evidence for **Tenant entitlement / reservation authority** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-003 definition of done

- [ ] All **30 MC-003 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Tenant entitlement / reservation authority** satisfies its stated need: The runtime validates numbers but cannot prove that a tenant is entitled to declare a given reserved share.
- [ ] Required controls **C017, C024, C041-C046** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-003.

---

## MC-004 — Durable topology state store

**Priority:** P0  
**Need:** Topology is in-memory only; restart/recovery, migration, backup, and reconstruction are not implemented.  
**Related controls:** C032, C037-C038, C057, C095  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-004-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Durable topology state store**; explicitly state what remains owned by adjacent services.
- [ ] **MC-004-CHK-002** — Assign an accountable owner and reviewer set for **Durable topology state store** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-004-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Durable topology state store**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-004-CHK-004** — Define the canonical data/state model for **Durable topology state store**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-004-CHK-005** — Document safety/correctness invariants for **Durable topology state store** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-004-CHK-006** — Design a durable topology schema representing node identity, parent edge, node type, labels/attributes, lifecycle state, generation/revision, timestamps, provenance, and tombstones.
- [ ] **MC-004-CHK-007** — Choose a storage engine and consistency model that provides atomic edge/attribute updates and prevents cycles or orphaned child records across transaction boundaries.
- [ ] **MC-004-CHK-008** — Implement write-ahead/transactional commit so acknowledged topology mutations survive process and host crashes without exposing half-applied hierarchy changes.
- [ ] **MC-004-CHK-009** — Persist a monotonic topology generation and support compare-and-swap reads/writes used by scheduler snapshots and stale-decision rejection.
- [ ] **MC-004-CHK-010** — Implement crash recovery that reconstructs an immutable in-memory scheduling snapshot from durable state and verifies hierarchy invariants before marking readiness true.
- [ ] **MC-004-CHK-011** — Provide versioned schema migrations with forward/rollback plans, migration locking, preflight validation, dry-run reporting, and recovery from interrupted migrations.
- [ ] **MC-004-CHK-012** — Implement snapshot/compaction/archive strategy appropriate to topology size and mutation rate while preserving required forensic history.
- [ ] **MC-004-CHK-013** — If the store is replicated, define quorum/consistency behavior, leader or multi-writer semantics, replication lag limits, and failover fencing.
- [ ] **MC-004-CHK-014** — Add storage-level uniqueness, referential, type, length, and generation constraints so invalid topology cannot be persisted even if application validation regresses.
- [ ] **MC-004-CHK-015** — Provide bootstrap/import/export/reconstruction tooling with integrity hashes and a tested procedure to rebuild topology from authoritative inventory sources.
### Security & trust

- [ ] **MC-004-CHK-016** — Complete a threat-model pass for **Durable topology state store** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-004-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Durable topology state store**; default to least privilege and explicitly test denied access.
- [ ] **MC-004-CHK-018** — Apply strict untrusted-input validation and resource limits to **Durable topology state store** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-004-CHK-019** — Determine cryptographic/secret-management requirements for **Durable topology state store**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-004-CHK-020** — Ensure sensitive data handled by **Durable topology state store** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-004-CHK-021** — Create a failure-mode and recovery table for **Durable topology state store** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-004-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Durable topology state store** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-004-CHK-023** — Expose structured metrics/logs/traces/health for **Durable topology state store** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-004-CHK-024** — Provide an operator runbook for **Durable topology state store** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-004-CHK-025** — Implement unit tests for **Durable topology state store** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-004-CHK-026** — Implement integration/contract tests for **Durable topology state store** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-004-CHK-027** — Add fault/adversarial tests for **Durable topology state store** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-004-CHK-028** — Benchmark or capacity-test **Durable topology state store** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-004-CHK-029** — Link **Durable topology state store** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-004-CHK-030** — Package production evidence for **Durable topology state store** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-004 definition of done

- [ ] All **30 MC-004 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Durable topology state store** satisfies its stated need: Topology is in-memory only; restart/recovery, migration, backup, and reconstruction are not implemented.
- [ ] Required controls **C032, C037-C038, C057, C095** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-004.

---

## MC-005 — Durable fair-share ledger

**Priority:** P0  
**Need:** `FairShare` is in-memory only; used/reserved state is lost on process restart.  
**Related controls:** C032, C057, C095  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-005-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Durable fair-share ledger**; explicitly state what remains owned by adjacent services.
- [ ] **MC-005-CHK-002** — Assign an accountable owner and reviewer set for **Durable fair-share ledger** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-005-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Durable fair-share ledger**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-005-CHK-004** — Define the canonical data/state model for **Durable fair-share ledger**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-005-CHK-005** — Document safety/correctness invariants for **Durable fair-share ledger** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-005-CHK-006** — Model durable fair-share state for tenant reservations, current usage, pending claims, committed claims, released capacity, ledger revision, and reconciliation metadata.
- [ ] **MC-005-CHK-007** — Implement atomic conditional updates that enforce physical capacity and tenant fairness invariants at the durable-store boundary, not only in process memory.
- [ ] **MC-005-CHK-008** — Assign idempotency/claim IDs to every claim and release operation; repeated delivery must return the original outcome without double-consuming or double-releasing capacity.
- [ ] **MC-005-CHK-009** — Persist a monotonic ledger revision/state token and require commit callers to present the token or equivalent precondition from the scoring snapshot.
- [ ] **MC-005-CHK-010** — Define crash-safe write ordering/WAL behavior for reservation updates and claim/release operations so acknowledged state is recoverable after abrupt termination.
- [ ] **MC-005-CHK-011** — Use leases or explicit ownership metadata for pending claims; reclaim abandoned claims only after deterministic expiry and fencing checks.
- [ ] **MC-005-CHK-012** — Implement periodic reconciliation against actual placed workload/resource state and authoritative entitlements, with bounded automatic repair and operator review for large drift.
- [ ] **MC-005-CHK-013** — Provide point-in-time snapshots and replay/audit support sufficient to explain historical fairness decisions without mutating the current ledger.
- [ ] **MC-005-CHK-014** — Enforce tenant isolation, numeric bounds, overflow protection, and denial of impossible states such as negative usage or used capacity above physical capacity.
- [ ] **MC-005-CHK-015** — Load-test atomic claim/release under high concurrency and verify linearizable or explicitly documented consistency semantics across multiple scheduler replicas.
### Security & trust

- [ ] **MC-005-CHK-016** — Complete a threat-model pass for **Durable fair-share ledger** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-005-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Durable fair-share ledger**; default to least privilege and explicitly test denied access.
- [ ] **MC-005-CHK-018** — Apply strict untrusted-input validation and resource limits to **Durable fair-share ledger** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-005-CHK-019** — Determine cryptographic/secret-management requirements for **Durable fair-share ledger**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-005-CHK-020** — Ensure sensitive data handled by **Durable fair-share ledger** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-005-CHK-021** — Create a failure-mode and recovery table for **Durable fair-share ledger** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-005-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Durable fair-share ledger** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-005-CHK-023** — Expose structured metrics/logs/traces/health for **Durable fair-share ledger** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-005-CHK-024** — Provide an operator runbook for **Durable fair-share ledger** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-005-CHK-025** — Implement unit tests for **Durable fair-share ledger** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-005-CHK-026** — Implement integration/contract tests for **Durable fair-share ledger** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-005-CHK-027** — Add fault/adversarial tests for **Durable fair-share ledger** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-005-CHK-028** — Benchmark or capacity-test **Durable fair-share ledger** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-005-CHK-029** — Link **Durable fair-share ledger** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-005-CHK-030** — Package production evidence for **Durable fair-share ledger** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-005 definition of done

- [ ] All **30 MC-005 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Durable fair-share ledger** satisfies its stated need: `FairShare` is in-memory only; used/reserved state is lost on process restart.
- [ ] Required controls **C032, C057, C095** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-005.

---

## MC-006 — Distributed coordination / leader fencing

**Priority:** P0  
**Need:** `RLock` protects threads in one process only; multiple scheduler replicas can still overclaim or act on stale ownership.  
**Related controls:** C058, C086, C089  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-006-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Distributed coordination / leader fencing**; explicitly state what remains owned by adjacent services.
- [ ] **MC-006-CHK-002** — Assign an accountable owner and reviewer set for **Distributed coordination / leader fencing** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-006-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Distributed coordination / leader fencing**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-006-CHK-004** — Define the canonical data/state model for **Distributed coordination / leader fencing**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-006-CHK-005** — Document safety/correctness invariants for **Distributed coordination / leader fencing** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-006-CHK-006** — Choose and document a coordination model (single elected leader, sharded ownership, or consensus-backed multi-writer) and state which operations require exclusive ownership.
- [ ] **MC-006-CHK-007** — Implement lease/election with quorum-backed ownership and monotonically increasing fencing tokens; never rely on a process-local lock for cross-replica exclusivity.
- [ ] **MC-006-CHK-008** — Propagate fencing tokens to every mutable downstream resource and reject writes carrying a token older than the last accepted token.
- [ ] **MC-006-CHK-009** — Define lease TTL, renewal cadence, clock-skew assumptions, network timeout behavior, and safety margin; prefer server/quorum time semantics where feasible.
- [ ] **MC-006-CHK-010** — Make loss of leadership/lease immediately revoke mutation privileges and transition the instance to read-only/not-ready before any further placement commit.
- [ ] **MC-006-CHK-011** — Test asymmetric partitions and stale leaders to prove that two replicas cannot both successfully mutate protected state even if each believes the peer failed.
- [ ] **MC-006-CHK-012** — Define replica membership changes, graceful drain, rolling upgrade, replacement, and disaster-recovery procedures without reusing stale fencing identities.
- [ ] **MC-006-CHK-013** — Expose current role, leader/owner identity, fencing token, lease expiry, election term, and coordination health through metrics and readiness diagnostics.
- [ ] **MC-006-CHK-014** — Implement bounded retry/backoff for coordination operations and prevent retry storms from amplifying a degraded quorum.
- [ ] **MC-006-CHK-015** — Run deterministic failover tests that kill the active owner during score, prepare, commit, and release phases and verify invariant preservation after a new owner takes over.
### Security & trust

- [ ] **MC-006-CHK-016** — Complete a threat-model pass for **Distributed coordination / leader fencing** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-006-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Distributed coordination / leader fencing**; default to least privilege and explicitly test denied access.
- [ ] **MC-006-CHK-018** — Apply strict untrusted-input validation and resource limits to **Distributed coordination / leader fencing** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-006-CHK-019** — Determine cryptographic/secret-management requirements for **Distributed coordination / leader fencing**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-006-CHK-020** — Ensure sensitive data handled by **Distributed coordination / leader fencing** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-006-CHK-021** — Create a failure-mode and recovery table for **Distributed coordination / leader fencing** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-006-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Distributed coordination / leader fencing** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-006-CHK-023** — Expose structured metrics/logs/traces/health for **Distributed coordination / leader fencing** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-006-CHK-024** — Provide an operator runbook for **Distributed coordination / leader fencing** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-006-CHK-025** — Implement unit tests for **Distributed coordination / leader fencing** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-006-CHK-026** — Implement integration/contract tests for **Distributed coordination / leader fencing** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-006-CHK-027** — Add fault/adversarial tests for **Distributed coordination / leader fencing** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-006-CHK-028** — Benchmark or capacity-test **Distributed coordination / leader fencing** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-006-CHK-029** — Link **Distributed coordination / leader fencing** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-006-CHK-030** — Package production evidence for **Distributed coordination / leader fencing** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-006 definition of done

- [ ] All **30 MC-006 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Distributed coordination / leader fencing** satisfies its stated need: `RLock` protects threads in one process only; multiple scheduler replicas can still overclaim or act on stale ownership.
- [ ] Required controls **C058, C086, C089** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-006.

---

## MC-007 — Distributed atomic placement commit protocol

**Priority:** P0  
**Need:** Local fair-share state tokens now reject stale in-process commits, but there is no distributed transaction/idempotency token tying scoring, final selection, claim, durable state, and rollback together across replicas.  
**Related controls:** C025-C026, C037, C057-C058  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-007-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Distributed atomic placement commit protocol**; explicitly state what remains owned by adjacent services.
- [ ] **MC-007-CHK-002** — Assign an accountable owner and reviewer set for **Distributed atomic placement commit protocol** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-007-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Distributed atomic placement commit protocol**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-007-CHK-004** — Define the canonical data/state model for **Distributed atomic placement commit protocol**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-007-CHK-005** — Document safety/correctness invariants for **Distributed atomic placement commit protocol** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-007-CHK-006** — Define a globally unique placement transaction ID and require it across scoring, candidate selection, capacity reservation, final commit, release/rollback, and audit events.
- [ ] **MC-007-CHK-007** — Bind the transaction to immutable decision inputs: workload identity/version, candidate set digest, topology generation, fairness-ledger revision, policy/config generation, and entitlement revision.
- [ ] **MC-007-CHK-008** — Implement an explicit prepare/reserve phase that acquires provisional capacity using atomic compare-and-swap/fencing without making an externally visible placement twice.
- [ ] **MC-007-CHK-009** — Commit scheduler state and downstream placement ownership with documented transaction semantics (single transactional store, saga, or idempotent two-phase protocol) and a defined source of truth.
- [ ] **MC-007-CHK-010** — Make every prepare/commit/abort/release endpoint idempotent and return the prior terminal state when the same transaction ID is retried.
- [ ] **MC-007-CHK-011** — Use monotonic fencing/ownership tokens so commits from stale leaders or superseded scheduler epochs are rejected by all participants.
- [ ] **MC-007-CHK-012** — Define timeout, lease expiry, cancellation, and orphaned-transaction recovery rules; ensure provisional reservations cannot leak capacity indefinitely.
- [ ] **MC-007-CHK-013** — Implement compensating rollback for downstream failures and define when a transaction is `ABORTED`, `COMMITTED`, `UNKNOWN`, or requires reconciliation.
- [ ] **MC-007-CHK-014** — Persist a transaction journal sufficient to recover after crash and deterministically continue or repair in-doubt transactions.
- [ ] **MC-007-CHK-015** — Exercise duplicate delivery, lost response, partial commit, store failover, leader failover, delayed messages, and replay attacks in integration tests.
### Security & trust

- [ ] **MC-007-CHK-016** — Complete a threat-model pass for **Distributed atomic placement commit protocol** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-007-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Distributed atomic placement commit protocol**; default to least privilege and explicitly test denied access.
- [ ] **MC-007-CHK-018** — Apply strict untrusted-input validation and resource limits to **Distributed atomic placement commit protocol** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-007-CHK-019** — Determine cryptographic/secret-management requirements for **Distributed atomic placement commit protocol**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-007-CHK-020** — Ensure sensitive data handled by **Distributed atomic placement commit protocol** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-007-CHK-021** — Create a failure-mode and recovery table for **Distributed atomic placement commit protocol** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-007-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Distributed atomic placement commit protocol** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-007-CHK-023** — Expose structured metrics/logs/traces/health for **Distributed atomic placement commit protocol** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-007-CHK-024** — Provide an operator runbook for **Distributed atomic placement commit protocol** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-007-CHK-025** — Implement unit tests for **Distributed atomic placement commit protocol** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-007-CHK-026** — Implement integration/contract tests for **Distributed atomic placement commit protocol** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-007-CHK-027** — Add fault/adversarial tests for **Distributed atomic placement commit protocol** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-007-CHK-028** — Benchmark or capacity-test **Distributed atomic placement commit protocol** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-007-CHK-029** — Link **Distributed atomic placement commit protocol** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-007-CHK-030** — Package production evidence for **Distributed atomic placement commit protocol** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-007 definition of done

- [ ] All **30 MC-007 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Distributed atomic placement commit protocol** satisfies its stated need: Local fair-share state tokens now reject stale in-process commits, but there is no distributed transaction/idempotency token tying scoring, final selection, claim, durable state, and rollback together across replicas.
- [ ] Required controls **C025-C026, C037, C057-C058** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-007.

---

## MC-008 — Adjacent `SCH-01` integration

**Priority:** P0  
**Need:** The downstream placement owner named by the contract is not bundled or integration-tested here.  
**Related controls:** C003, C019, C030, C083  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-008-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Adjacent `SCH-01` integration**; explicitly state what remains owned by adjacent services.
- [ ] **MC-008-CHK-002** — Assign an accountable owner and reviewer set for **Adjacent `SCH-01` integration** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-008-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Adjacent `SCH-01` integration**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-008-CHK-004** — Define the canonical data/state model for **Adjacent `SCH-01` integration**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-008-CHK-005** — Document safety/correctness invariants for **Adjacent `SCH-01` integration** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-008-CHK-006** — Capture the normative `SCH-01` placement API, ownership boundary, lifecycle states, and exact responsibility split between scoring and final placement execution.
- [ ] **MC-008-CHK-007** — Build a versioned adapter mapping GAP-03 candidate/score/fairness records into SCH-01 request fields without lossy or implicit conversions.
- [ ] **MC-008-CHK-008** — Ensure SCH-01 returns a stable placement transaction/operation ID that GAP-03 can correlate with claims, releases, errors, traces, and audit records.
- [ ] **MC-008-CHK-009** — Define how SCH-01 selects among ranked candidates and prohibit it from bypassing hard GAP-03 constraints without an explicit override policy and audit event.
- [ ] **MC-008-CHK-010** — Integrate backpressure and admission signals so SCH-01 cannot enqueue unbounded placement work when GAP-03 or durable state dependencies are saturated.
- [ ] **MC-008-CHK-011** — Propagate idempotency keys and retry classification across the boundary to prevent duplicate placements when responses are lost.
- [ ] **MC-008-CHK-012** — Map all SCH-01 terminal and transient failures into GAP-03’s stable external error taxonomy and define compensating capacity release behavior.
- [ ] **MC-008-CHK-013** — Implement protocol/version negotiation and reject unsupported major versions before any placement side effects occur.
- [ ] **MC-008-CHK-014** — Create end-to-end fixtures covering successful placement, no feasible candidate, fairness denial, stale generation, duplicate request, timeout, and partial downstream failure.
- [ ] **MC-008-CHK-015** — Add CI contract tests against the real SCH-01 implementation or a schema-faithful conformance harness maintained with it.
### Security & trust

- [ ] **MC-008-CHK-016** — Complete a threat-model pass for **Adjacent `SCH-01` integration** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-008-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Adjacent `SCH-01` integration**; default to least privilege and explicitly test denied access.
- [ ] **MC-008-CHK-018** — Apply strict untrusted-input validation and resource limits to **Adjacent `SCH-01` integration** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-008-CHK-019** — Determine cryptographic/secret-management requirements for **Adjacent `SCH-01` integration**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-008-CHK-020** — Ensure sensitive data handled by **Adjacent `SCH-01` integration** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-008-CHK-021** — Create a failure-mode and recovery table for **Adjacent `SCH-01` integration** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-008-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Adjacent `SCH-01` integration** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-008-CHK-023** — Expose structured metrics/logs/traces/health for **Adjacent `SCH-01` integration** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-008-CHK-024** — Provide an operator runbook for **Adjacent `SCH-01` integration** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-008-CHK-025** — Implement unit tests for **Adjacent `SCH-01` integration** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-008-CHK-026** — Implement integration/contract tests for **Adjacent `SCH-01` integration** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-008-CHK-027** — Add fault/adversarial tests for **Adjacent `SCH-01` integration** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-008-CHK-028** — Benchmark or capacity-test **Adjacent `SCH-01` integration** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-008-CHK-029** — Link **Adjacent `SCH-01` integration** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-008-CHK-030** — Package production evidence for **Adjacent `SCH-01` integration** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-008 definition of done

- [ ] All **30 MC-008 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Adjacent `SCH-01` integration** satisfies its stated need: The downstream placement owner named by the contract is not bundled or integration-tested here.
- [ ] Required controls **C003, C019, C030, C083** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-008.

---

## MC-009 — `GAP-02` hardware-capability feed integration

**Priority:** P0  
**Need:** No concrete adapter validates that topology nodes correspond to authoritative discovered hardware facts.  
**Related controls:** C003-C004, C030, C083  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-009-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **`GAP-02` hardware-capability feed integration**; explicitly state what remains owned by adjacent services.
- [ ] **MC-009-CHK-002** — Assign an accountable owner and reviewer set for **`GAP-02` hardware-capability feed integration** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-009-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **`GAP-02` hardware-capability feed integration**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-009-CHK-004** — Define the canonical data/state model for **`GAP-02` hardware-capability feed integration**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-009-CHK-005** — Document safety/correctness invariants for **`GAP-02` hardware-capability feed integration** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-009-CHK-006** — Define the GAP-02 hardware inventory/capability contract consumed by the scheduler, including node identity, CPU/ISA, memory, accelerators, storage, network, power/thermal attributes, and lifecycle state.
- [ ] **MC-009-CHK-007** — Normalize hardware capabilities into scheduler-owned canonical types/units and reject ambiguous vendor strings or unbounded free-form capability claims.
- [ ] **MC-009-CHK-008** — Bind topology node IDs to authoritative inventory identities and reject topology nodes that cannot be resolved to a valid discovered device/resource record when policy requires hardware verification.
- [ ] **MC-009-CHK-009** — Carry inventory generation, observation timestamp, source identity, and attestation/provenance metadata into the scheduler snapshot used for a decision.
- [ ] **MC-009-CHK-010** — Define freshness TTLs and degraded behavior for stale/missing discovery data; do not silently treat unknown capability as sufficient capability.
- [ ] **MC-009-CHK-011** — Validate cryptographic/device attestation where available before honoring security-sensitive capability claims such as trusted execution or accelerator identity.
- [ ] **MC-009-CHK-012** — Handle hot-add/hot-remove, node reboot, device replacement, partial discovery, and conflicting discovery sources without retaining phantom capacity.
- [ ] **MC-009-CHK-013** — Implement hard capability predicates and distinguish them from soft preferences so unsupported hardware can never win by score.
- [ ] **MC-009-CHK-014** — Periodically reconcile topology, GAP-02 inventory, and actual placement state; emit drift events for orphan nodes, duplicate identities, and capability regressions.
- [ ] **MC-009-CHK-015** — Build fixtures for heterogeneous nodes, stale inventory, spoofed identity, removed accelerators, unit conversion, unsupported ISA, and conflicting capability reports.
### Security & trust

- [ ] **MC-009-CHK-016** — Complete a threat-model pass for **`GAP-02` hardware-capability feed integration** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-009-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **`GAP-02` hardware-capability feed integration**; default to least privilege and explicitly test denied access.
- [ ] **MC-009-CHK-018** — Apply strict untrusted-input validation and resource limits to **`GAP-02` hardware-capability feed integration** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-009-CHK-019** — Determine cryptographic/secret-management requirements for **`GAP-02` hardware-capability feed integration**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-009-CHK-020** — Ensure sensitive data handled by **`GAP-02` hardware-capability feed integration** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-009-CHK-021** — Create a failure-mode and recovery table for **`GAP-02` hardware-capability feed integration** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-009-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **`GAP-02` hardware-capability feed integration** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-009-CHK-023** — Expose structured metrics/logs/traces/health for **`GAP-02` hardware-capability feed integration** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-009-CHK-024** — Provide an operator runbook for **`GAP-02` hardware-capability feed integration** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-009-CHK-025** — Implement unit tests for **`GAP-02` hardware-capability feed integration** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-009-CHK-026** — Implement integration/contract tests for **`GAP-02` hardware-capability feed integration** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-009-CHK-027** — Add fault/adversarial tests for **`GAP-02` hardware-capability feed integration** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-009-CHK-028** — Benchmark or capacity-test **`GAP-02` hardware-capability feed integration** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-009-CHK-029** — Link **`GAP-02` hardware-capability feed integration** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-009-CHK-030** — Package production evidence for **`GAP-02` hardware-capability feed integration** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-009 definition of done

- [ ] All **30 MC-009 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **`GAP-02` hardware-capability feed integration** satisfies its stated need: No concrete adapter validates that topology nodes correspond to authoritative discovered hardware facts.
- [ ] Required controls **C003-C004, C030, C083** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-009.

---

## MC-010 — `GAP-14` data-gravity integration

**Priority:** P0  
**Need:** No concrete source/API provides data location anchors or validates their freshness/provenance.  
**Related controls:** C003-C004, C030, C083  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-010-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **`GAP-14` data-gravity integration**; explicitly state what remains owned by adjacent services.
- [ ] **MC-010-CHK-002** — Assign an accountable owner and reviewer set for **`GAP-14` data-gravity integration** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-010-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **`GAP-14` data-gravity integration**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-010-CHK-004** — Define the canonical data/state model for **`GAP-14` data-gravity integration**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-010-CHK-005** — Document safety/correctness invariants for **`GAP-14` data-gravity integration** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-010-CHK-006** — Define the GAP-14 data-gravity input model: dataset/object identity, replica/anchor locations, size, access pattern, freshness, jurisdiction/security constraints, and provenance.
- [ ] **MC-010-CHK-007** — Normalize location anchors to scheduler topology identities and explicitly define behavior when a data anchor refers to an unknown, decommissioned, or quarantined topology node.
- [ ] **MC-010-CHK-008** — Verify source authenticity, data-location revision, observation time, and freshness before allowing an anchor to influence placement scoring.
- [ ] **MC-010-CHK-009** — Calculate data-gravity contribution from explicit size/traffic/transfer-cost semantics rather than opaque labels; document units and normalization.
- [ ] **MC-010-CHK-010** — Handle multiple replicas/erasure sets by computing feasible locality options without assuming one canonical copy or double-counting replicated bytes.
- [ ] **MC-010-CHK-011** — Define staleness TTL and fallback behavior when the data-gravity service is unavailable; record when scoring used stale or absent gravity information.
- [ ] **MC-010-CHK-012** — Protect sensitive dataset names/locations through scoped identifiers and authorization so scheduling telemetry cannot leak tenant data placement unnecessarily.
- [ ] **MC-010-CHK-013** — Ensure data gravity remains a soft objective unless policy explicitly marks residency/security constraints as hard requirements.
- [ ] **MC-010-CHK-014** — Expose per-candidate data-gravity score components and source revision in explain output for operator review and deterministic replay.
- [ ] **MC-010-CHK-015** — Create integration cases for local replica, remote-only data, multiple replicas, stale anchors, conflicting provenance, very large datasets, and anchor disappearance during commit.
### Security & trust

- [ ] **MC-010-CHK-016** — Complete a threat-model pass for **`GAP-14` data-gravity integration** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-010-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **`GAP-14` data-gravity integration**; default to least privilege and explicitly test denied access.
- [ ] **MC-010-CHK-018** — Apply strict untrusted-input validation and resource limits to **`GAP-14` data-gravity integration** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-010-CHK-019** — Determine cryptographic/secret-management requirements for **`GAP-14` data-gravity integration**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-010-CHK-020** — Ensure sensitive data handled by **`GAP-14` data-gravity integration** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-010-CHK-021** — Create a failure-mode and recovery table for **`GAP-14` data-gravity integration** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-010-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **`GAP-14` data-gravity integration** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-010-CHK-023** — Expose structured metrics/logs/traces/health for **`GAP-14` data-gravity integration** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-010-CHK-024** — Provide an operator runbook for **`GAP-14` data-gravity integration** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-010-CHK-025** — Implement unit tests for **`GAP-14` data-gravity integration** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-010-CHK-026** — Implement integration/contract tests for **`GAP-14` data-gravity integration** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-010-CHK-027** — Add fault/adversarial tests for **`GAP-14` data-gravity integration** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-010-CHK-028** — Benchmark or capacity-test **`GAP-14` data-gravity integration** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-010-CHK-029** — Link **`GAP-14` data-gravity integration** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-010-CHK-030** — Package production evidence for **`GAP-14` data-gravity integration** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-010 definition of done

- [ ] All **30 MC-010 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **`GAP-14` data-gravity integration** satisfies its stated need: No concrete source/API provides data location anchors or validates their freshness/provenance.
- [ ] Required controls **C003-C004, C030, C083** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-010.

---

## MC-011 — `PLN-05` elasticity/demand integration

**Priority:** P0  
**Need:** The optional capacity-demand peer named by the contract has no adapter or fallback policy.  
**Related controls:** C003, C056, C083  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-011-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **`PLN-05` elasticity/demand integration**; explicitly state what remains owned by adjacent services.
- [ ] **MC-011-CHK-002** — Assign an accountable owner and reviewer set for **`PLN-05` elasticity/demand integration** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-011-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **`PLN-05` elasticity/demand integration**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-011-CHK-004** — Define the canonical data/state model for **`PLN-05` elasticity/demand integration**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-011-CHK-005** — Document safety/correctness invariants for **`PLN-05` elasticity/demand integration** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-011-CHK-006** — Define the PLN-05 demand/elasticity contract, including requested capacity, resource dimensions, forecast horizon, confidence, priority, deadlines, and signal revision.
- [ ] **MC-011-CHK-007** — Build a versioned adapter that converts PLN-05 units and resource classes into the scheduler’s canonical capacity model with strict bounds checking.
- [ ] **MC-011-CHK-008** — Define whether demand signals are advisory or admission-affecting and ensure a forecast cannot override physical-capacity, security, or fairness hard constraints.
- [ ] **MC-011-CHK-009** — Validate signal freshness and confidence; discard or de-weight stale forecasts instead of treating them as current demand.
- [ ] **MC-011-CHK-010** — Provide bounded fallback behavior when PLN-05 is unavailable, including last-known-good TTL and a deterministic baseline policy.
- [ ] **MC-011-CHK-011** — Rate-limit and debounce demand updates to avoid scheduler thrash from noisy forecast oscillation; support hysteresis where appropriate.
- [ ] **MC-011-CHK-012** — Correlate scale-out/scale-in recommendations with actual placement outcomes so planner feedback does not double-count capacity already in transition.
- [ ] **MC-011-CHK-013** — Propagate planner request IDs and revisions into traces/explain records for causality analysis.
- [ ] **MC-011-CHK-014** — Implement failure/error mapping and retry semantics that cannot turn a transient PLN-05 outage into unbounded placement retries.
- [ ] **MC-011-CHK-015** — Test demand spikes, demand collapse, stale forecasts, low-confidence forecasts, planner restart, duplicate updates, and conflicting current/forecast capacity.
### Security & trust

- [ ] **MC-011-CHK-016** — Complete a threat-model pass for **`PLN-05` elasticity/demand integration** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-011-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **`PLN-05` elasticity/demand integration**; default to least privilege and explicitly test denied access.
- [ ] **MC-011-CHK-018** — Apply strict untrusted-input validation and resource limits to **`PLN-05` elasticity/demand integration** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-011-CHK-019** — Determine cryptographic/secret-management requirements for **`PLN-05` elasticity/demand integration**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-011-CHK-020** — Ensure sensitive data handled by **`PLN-05` elasticity/demand integration** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-011-CHK-021** — Create a failure-mode and recovery table for **`PLN-05` elasticity/demand integration** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-011-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **`PLN-05` elasticity/demand integration** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-011-CHK-023** — Expose structured metrics/logs/traces/health for **`PLN-05` elasticity/demand integration** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-011-CHK-024** — Provide an operator runbook for **`PLN-05` elasticity/demand integration** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-011-CHK-025** — Implement unit tests for **`PLN-05` elasticity/demand integration** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-011-CHK-026** — Implement integration/contract tests for **`PLN-05` elasticity/demand integration** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-011-CHK-027** — Add fault/adversarial tests for **`PLN-05` elasticity/demand integration** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-011-CHK-028** — Benchmark or capacity-test **`PLN-05` elasticity/demand integration** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-011-CHK-029** — Link **`PLN-05` elasticity/demand integration** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-011-CHK-030** — Package production evidence for **`PLN-05` elasticity/demand integration** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-011 definition of done

- [ ] All **30 MC-011 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **`PLN-05` elasticity/demand integration** satisfies its stated need: The optional capacity-demand peer named by the contract has no adapter or fallback policy.
- [ ] Required controls **C003, C056, C083** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-011.

---

## MC-012 — Identity, attestation, and topology-provenance verification

**Priority:** P0  
**Need:** No signatures/attestation chain protects topology, peer identity, or policy artifacts from forgery.  
**Related controls:** C041, C044-C045, C048-C050  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-012-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Identity, attestation, and topology-provenance verification**; explicitly state what remains owned by adjacent services.
- [ ] **MC-012-CHK-002** — Assign an accountable owner and reviewer set for **Identity, attestation, and topology-provenance verification** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-012-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Identity, attestation, and topology-provenance verification**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-012-CHK-004** — Define the canonical data/state model for **Identity, attestation, and topology-provenance verification**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-012-CHK-005** — Document safety/correctness invariants for **Identity, attestation, and topology-provenance verification** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-012-CHK-006** — Define workload/service/node identity types and trust domains; document which identities may assert topology, entitlements, policies, and placement actions.
- [ ] **MC-012-CHK-007** — Use verifiable credentials such as mTLS workload certificates, signed tokens, or hardware-backed attestation with explicit issuer trust roots and audience binding.
- [ ] **MC-012-CHK-008** — Validate certificate/token chains, signature algorithms, issuer, subject, audience, validity window, nonce/challenge where applicable, and revocation status.
- [ ] **MC-012-CHK-009** — Attach signed provenance metadata to topology snapshots, entitlement/policy artifacts, and peer capability statements; preserve the verified signer identity and digest.
- [ ] **MC-012-CHK-010** — Implement key/certificate rotation with overlapping validity, emergency revocation, trust-root rollover, and no requirement for unsafe global downtime.
- [ ] **MC-012-CHK-011** — Protect private keys/secrets using OS/service secret facilities or HSM/KMS where risk warrants; never store long-lived credentials in repository config.
- [ ] **MC-012-CHK-012** — Prevent replay by binding signed requests/artifacts to version, nonce/transaction ID, audience, and bounded validity windows.
- [ ] **MC-012-CHK-013** — Define attestation claim requirements for security-sensitive node classes and fail closed when mandatory claims are absent, unverifiable, or outside policy.
- [ ] **MC-012-CHK-014** — Emit audit events for failed verification, revoked credentials, trust-root changes, downgrade attempts, and emergency trust overrides.
- [ ] **MC-012-CHK-015** — Test expired/not-yet-valid certs, revoked credentials, wrong audience, unknown issuer, algorithm downgrade, key rotation overlap, replay, forged provenance, and attestation mismatch.
### Security & trust

- [ ] **MC-012-CHK-016** — Complete a threat-model pass for **Identity, attestation, and topology-provenance verification** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-012-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Identity, attestation, and topology-provenance verification**; default to least privilege and explicitly test denied access.
- [ ] **MC-012-CHK-018** — Apply strict untrusted-input validation and resource limits to **Identity, attestation, and topology-provenance verification** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-012-CHK-019** — Determine cryptographic/secret-management requirements for **Identity, attestation, and topology-provenance verification**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-012-CHK-020** — Ensure sensitive data handled by **Identity, attestation, and topology-provenance verification** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-012-CHK-021** — Create a failure-mode and recovery table for **Identity, attestation, and topology-provenance verification** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-012-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Identity, attestation, and topology-provenance verification** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-012-CHK-023** — Expose structured metrics/logs/traces/health for **Identity, attestation, and topology-provenance verification** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-012-CHK-024** — Provide an operator runbook for **Identity, attestation, and topology-provenance verification** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-012-CHK-025** — Implement unit tests for **Identity, attestation, and topology-provenance verification** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-012-CHK-026** — Implement integration/contract tests for **Identity, attestation, and topology-provenance verification** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-012-CHK-027** — Add fault/adversarial tests for **Identity, attestation, and topology-provenance verification** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-012-CHK-028** — Benchmark or capacity-test **Identity, attestation, and topology-provenance verification** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-012-CHK-029** — Link **Identity, attestation, and topology-provenance verification** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-012-CHK-030** — Package production evidence for **Identity, attestation, and topology-provenance verification** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-012 definition of done

- [ ] All **30 MC-012 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Identity, attestation, and topology-provenance verification** satisfies its stated need: No signatures/attestation chain protects topology, peer identity, or policy artifacts from forgery.
- [ ] Required controls **C041, C044-C045, C048-C050** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-012.

---

## MC-013 — Tamper-evident security audit log

**Priority:** P0  
**Need:** Security-sensitive topology and reservation changes are not persisted to an append-only/tamper-evident ledger.  
**Related controls:** C049, C073, C078  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-013-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Tamper-evident security audit log**; explicitly state what remains owned by adjacent services.
- [ ] **MC-013-CHK-002** — Assign an accountable owner and reviewer set for **Tamper-evident security audit log** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-013-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Tamper-evident security audit log**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-013-CHK-004** — Define the canonical data/state model for **Tamper-evident security audit log**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-013-CHK-005** — Document safety/correctness invariants for **Tamper-evident security audit log** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-013-CHK-006** — Define a stable security-audit event schema containing event ID, actor, target, action, authorization result, request/transaction ID, before/after digest, reason, source, timestamp, and software/config generation.
- [ ] **MC-013-CHK-007** — Write audit events to append-only storage separated from ordinary application logs; prevent scheduler service principals from deleting or rewriting historical records.
- [ ] **MC-013-CHK-008** — Implement tamper evidence using signed batches, hash chaining, WORM/object lock, transparency log, or an equivalently reviewable mechanism.
- [ ] **MC-013-CHK-009** — Use trusted/monotonic time metadata where feasible and record clock source/uncertainty so event ordering can be reconstructed across replicas.
- [ ] **MC-013-CHK-010** — Capture topology re-parenting, entitlement changes, freeze/quarantine actions, trust-root changes, overrides, denied privileged calls, and release/promote actions as mandatory events.
- [ ] **MC-013-CHK-011** — Redact secrets and minimize sensitive tenant payload while preserving stable identifiers/digests needed for forensic correlation.
- [ ] **MC-013-CHK-012** — Define retention, archival, legal/operational hold, tenant partitioning, and deletion policy that does not undermine required security evidence.
- [ ] **MC-013-CHK-013** — Provide query/export with least-privilege access, pagination, integrity verification, and correlation by transaction/actor/topology generation.
- [ ] **MC-013-CHK-014** — Continuously verify chain/signature integrity and alert on gaps, duplicate sequence numbers, storage write failure, or retention policy violation.
- [ ] **MC-013-CHK-015** — Test log tampering, storage outage, full disk/quota, out-of-order events, replayed events, clock skew, and recovery while proving privileged mutations fail or degrade safely when mandatory audit persistence is unavailable.
### Security & trust

- [ ] **MC-013-CHK-016** — Complete a threat-model pass for **Tamper-evident security audit log** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-013-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Tamper-evident security audit log**; default to least privilege and explicitly test denied access.
- [ ] **MC-013-CHK-018** — Apply strict untrusted-input validation and resource limits to **Tamper-evident security audit log** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-013-CHK-019** — Determine cryptographic/secret-management requirements for **Tamper-evident security audit log**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-013-CHK-020** — Ensure sensitive data handled by **Tamper-evident security audit log** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-013-CHK-021** — Create a failure-mode and recovery table for **Tamper-evident security audit log** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-013-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Tamper-evident security audit log** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-013-CHK-023** — Expose structured metrics/logs/traces/health for **Tamper-evident security audit log** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-013-CHK-024** — Provide an operator runbook for **Tamper-evident security audit log** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-013-CHK-025** — Implement unit tests for **Tamper-evident security audit log** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-013-CHK-026** — Implement integration/contract tests for **Tamper-evident security audit log** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-013-CHK-027** — Add fault/adversarial tests for **Tamper-evident security audit log** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-013-CHK-028** — Benchmark or capacity-test **Tamper-evident security audit log** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-013-CHK-029** — Link **Tamper-evident security audit log** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-013-CHK-030** — Package production evidence for **Tamper-evident security audit log** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-013 definition of done

- [ ] All **30 MC-013 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Tamper-evident security audit log** satisfies its stated need: Security-sensitive topology and reservation changes are not persisted to an append-only/tamper-evident ledger.
- [ ] Required controls **C049, C073, C078** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-013.

---

## MC-014 — Service-level failure codes and RPC error model

**Priority:** P0  
**Need:** Python exceptions exist locally, but there is no stable machine-readable external error taxonomy.  
**Related controls:** C014, C025-C026  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-014-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Service-level failure codes and RPC error model**; explicitly state what remains owned by adjacent services.
- [ ] **MC-014-CHK-002** — Assign an accountable owner and reviewer set for **Service-level failure codes and RPC error model** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-014-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Service-level failure codes and RPC error model**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-014-CHK-004** — Define the canonical data/state model for **Service-level failure codes and RPC error model**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-014-CHK-005** — Document safety/correctness invariants for **Service-level failure codes and RPC error model** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-014-CHK-006** — Define a versioned error-code namespace covering validation, authorization, policy/fairness denial, no-capacity, stale state, conflict, dependency unavailable, timeout, overload, internal defect, and unsupported version.
- [ ] **MC-014-CHK-007** — For every code define stability, human message template, machine reason, retryable flag, retry-after semantics, severity, and owning subsystem.
- [ ] **MC-014-CHK-008** — Map internal exceptions to external codes at one boundary so stack traces/class names do not become an accidental wire contract.
- [ ] **MC-014-CHK-009** — Define transport mapping for HTTP/gRPC/message protocols, including status code, structured error detail, correlation ID, and safe diagnostic metadata.
- [ ] **MC-014-CHK-010** — Distinguish deterministic denials from transient failures so clients do not retry impossible placements or permanently abandon transient ones.
- [ ] **MC-014-CHK-011** — Protect error payloads from leaking tenant data, topology secrets, credentials, filesystem paths, or internal implementation details.
- [ ] **MC-014-CHK-012** — Preserve a causal chain internally using structured cause codes while limiting external depth/size to prevent amplification attacks.
- [ ] **MC-014-CHK-013** — Version and document deprecation/alias rules so clients can safely handle new granular reasons under an existing stable top-level code.
- [ ] **MC-014-CHK-014** — Instrument error-code counters and latency by class while controlling high-cardinality dimensions.
- [ ] **MC-014-CHK-015** — Create golden tests asserting exact code/status/retryability for every public failure path, including nested dependency failures and unknown internal exceptions.
### Security & trust

- [ ] **MC-014-CHK-016** — Complete a threat-model pass for **Service-level failure codes and RPC error model** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-014-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Service-level failure codes and RPC error model**; default to least privilege and explicitly test denied access.
- [ ] **MC-014-CHK-018** — Apply strict untrusted-input validation and resource limits to **Service-level failure codes and RPC error model** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-014-CHK-019** — Determine cryptographic/secret-management requirements for **Service-level failure codes and RPC error model**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-014-CHK-020** — Ensure sensitive data handled by **Service-level failure codes and RPC error model** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-014-CHK-021** — Create a failure-mode and recovery table for **Service-level failure codes and RPC error model** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-014-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Service-level failure codes and RPC error model** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-014-CHK-023** — Expose structured metrics/logs/traces/health for **Service-level failure codes and RPC error model** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-014-CHK-024** — Provide an operator runbook for **Service-level failure codes and RPC error model** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-014-CHK-025** — Implement unit tests for **Service-level failure codes and RPC error model** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-014-CHK-026** — Implement integration/contract tests for **Service-level failure codes and RPC error model** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-014-CHK-027** — Add fault/adversarial tests for **Service-level failure codes and RPC error model** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-014-CHK-028** — Benchmark or capacity-test **Service-level failure codes and RPC error model** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-014-CHK-029** — Link **Service-level failure codes and RPC error model** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-014-CHK-030** — Package production evidence for **Service-level failure codes and RPC error model** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-014 definition of done

- [ ] All **30 MC-014 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Service-level failure codes and RPC error model** satisfies its stated need: Python exceptions exist locally, but there is no stable machine-readable external error taxonomy.
- [ ] Required controls **C014, C025-C026** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-014.

---

## MC-015 — Production configuration subsystem

**Priority:** P0  
**Need:** No declarative config schema, provenance, activation timestamp, transactional activation, environment overlays, or rollback mechanism exists.  
**Related controls:** C033-C038, C040  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-015-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Production configuration subsystem**; explicitly state what remains owned by adjacent services.
- [ ] **MC-015-CHK-002** — Assign an accountable owner and reviewer set for **Production configuration subsystem** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-015-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Production configuration subsystem**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-015-CHK-004** — Define the canonical data/state model for **Production configuration subsystem**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-015-CHK-005** — Document safety/correctness invariants for **Production configuration subsystem** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-015-CHK-006** — Define a typed configuration schema with version, defaults, ranges, units, mutually exclusive fields, feature gates, and explicit distinction between dynamic and restart-required settings.
- [ ] **MC-015-CHK-007** — Implement deterministic source precedence across built-in defaults, signed config file/service, environment overlays, and command-line overrides; prohibit hidden undeclared sources.
- [ ] **MC-015-CHK-008** — Validate the complete candidate configuration before activation and reject unknown or deprecated fields according to a documented compatibility policy.
- [ ] **MC-015-CHK-009** — Activate configuration transactionally as an immutable snapshot with a monotonic generation, digest, activation timestamp, actor/source, and previous-generation pointer.
- [ ] **MC-015-CHK-010** — Bind each scheduling decision to the configuration generation used so explain/replay can reproduce behavior.
- [ ] **MC-015-CHK-011** — Provide staged/dry-run validation for risky changes and enforce policy limits on weight, TTL, capacity, fail-open, and security settings.
- [ ] **MC-015-CHK-012** — Implement rollback to a known-good generation without reconstructing settings manually; preserve rollback provenance and audit events.
- [ ] **MC-015-CHK-013** — Keep secrets as references to a secret manager rather than plaintext configuration values and ensure config dumps redact secret material.
- [ ] **MC-015-CHK-014** — If dynamic watching is supported, debounce updates and ensure every worker observes a coherent whole-snapshot transition rather than per-field tearing.
- [ ] **MC-015-CHK-015** — Add schema migration, configuration diff, startup validation, invalid-update, rollback, concurrent-update, and partial-source-failure tests.
### Security & trust

- [ ] **MC-015-CHK-016** — Complete a threat-model pass for **Production configuration subsystem** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-015-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Production configuration subsystem**; default to least privilege and explicitly test denied access.
- [ ] **MC-015-CHK-018** — Apply strict untrusted-input validation and resource limits to **Production configuration subsystem** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-015-CHK-019** — Determine cryptographic/secret-management requirements for **Production configuration subsystem**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-015-CHK-020** — Ensure sensitive data handled by **Production configuration subsystem** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-015-CHK-021** — Create a failure-mode and recovery table for **Production configuration subsystem** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-015-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Production configuration subsystem** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-015-CHK-023** — Expose structured metrics/logs/traces/health for **Production configuration subsystem** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-015-CHK-024** — Provide an operator runbook for **Production configuration subsystem** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-015-CHK-025** — Implement unit tests for **Production configuration subsystem** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-015-CHK-026** — Implement integration/contract tests for **Production configuration subsystem** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-015-CHK-027** — Add fault/adversarial tests for **Production configuration subsystem** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-015-CHK-028** — Benchmark or capacity-test **Production configuration subsystem** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-015-CHK-029** — Link **Production configuration subsystem** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-015-CHK-030** — Package production evidence for **Production configuration subsystem** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-015 definition of done

- [ ] All **30 MC-015 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Production configuration subsystem** satisfies its stated need: No declarative config schema, provenance, activation timestamp, transactional activation, environment overlays, or rollback mechanism exists.
- [ ] Required controls **C033-C038, C040** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-015.

---

## MC-016 — Safe degraded-mode/failover policy

**Priority:** P0  
**Need:** The package has no implemented behavior for dependency loss, partition, unavailable identity/policy/time services, or site failover.  
**Related controls:** C018-C019, C048, C051-C056  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-016-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Safe degraded-mode/failover policy**; explicitly state what remains owned by adjacent services.
- [ ] **MC-016-CHK-002** — Assign an accountable owner and reviewer set for **Safe degraded-mode/failover policy** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-016-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Safe degraded-mode/failover policy**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-016-CHK-004** — Define the canonical data/state model for **Safe degraded-mode/failover policy**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-016-CHK-005** — Document safety/correctness invariants for **Safe degraded-mode/failover policy** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-016-CHK-006** — Create a dependency/failure-mode matrix covering identity, topology store, fair-share ledger, entitlement authority, GAP-02, GAP-14, PLN-05, SCH-01, telemetry, time, DNS/network, and coordination services.
- [ ] **MC-016-CHK-007** — For every dependency define fail-open/fail-closed behavior by operation, maximum stale-data TTL, allowed degraded capabilities, and operator-visible status.
- [ ] **MC-016-CHK-008** — Implement circuit breakers and bounded retry budgets so dependency outages cannot create cascading thread/connection exhaustion.
- [ ] **MC-016-CHK-009** — Define site/region failover criteria, candidate filtering, and state-transfer prerequisites without violating topology, residency, fairness, or fencing constraints.
- [ ] **MC-016-CHK-010** — Block mutating commits when ownership, authoritative state, identity, or integrity requirements cannot be proven; distinguish safe read/explain operation from unsafe mutation.
- [ ] **MC-016-CHK-011** — Implement stale-snapshot detection using explicit generation/timestamp provenance rather than wall-clock heuristics alone.
- [ ] **MC-016-CHK-012** — Provide operator-controlled degraded-mode overrides with scoped duration, strong authorization, explicit risk acknowledgment, audit trail, and automatic expiry.
- [ ] **MC-016-CHK-013** — Define recovery ordering after dependency restoration and reconcile topology, ledger, transactions, and downstream placement before clearing degraded status.
- [ ] **MC-016-CHK-014** — Expose degraded reason codes, affected capabilities, stale age, breaker state, and recovery progress through health/metrics/alerts.
- [ ] **MC-016-CHK-015** — Run dependency blackhole, high-latency, partial partition, stale cache, clock skew, dual-site failure, and recovery tests while asserting no invariant-breaking placement succeeds.
### Security & trust

- [ ] **MC-016-CHK-016** — Complete a threat-model pass for **Safe degraded-mode/failover policy** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-016-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Safe degraded-mode/failover policy**; default to least privilege and explicitly test denied access.
- [ ] **MC-016-CHK-018** — Apply strict untrusted-input validation and resource limits to **Safe degraded-mode/failover policy** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-016-CHK-019** — Determine cryptographic/secret-management requirements for **Safe degraded-mode/failover policy**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-016-CHK-020** — Ensure sensitive data handled by **Safe degraded-mode/failover policy** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-016-CHK-021** — Create a failure-mode and recovery table for **Safe degraded-mode/failover policy** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-016-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Safe degraded-mode/failover policy** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-016-CHK-023** — Expose structured metrics/logs/traces/health for **Safe degraded-mode/failover policy** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-016-CHK-024** — Provide an operator runbook for **Safe degraded-mode/failover policy** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-016-CHK-025** — Implement unit tests for **Safe degraded-mode/failover policy** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-016-CHK-026** — Implement integration/contract tests for **Safe degraded-mode/failover policy** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-016-CHK-027** — Add fault/adversarial tests for **Safe degraded-mode/failover policy** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-016-CHK-028** — Benchmark or capacity-test **Safe degraded-mode/failover policy** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-016-CHK-029** — Link **Safe degraded-mode/failover policy** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-016-CHK-030** — Package production evidence for **Safe degraded-mode/failover policy** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-016 definition of done

- [ ] All **30 MC-016 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Safe degraded-mode/failover policy** satisfies its stated need: The package has no implemented behavior for dependency loss, partition, unavailable identity/policy/time services, or site failover.
- [ ] Required controls **C018-C019, C048, C051-C056** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-016.

---

## MC-017 — Emergency freeze/quarantine/disable control

**Priority:** P0  
**Need:** README describes suite-level removal, but no runtime kill switch or quarantine API exists.  
**Related controls:** C059, C092  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-017-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Emergency freeze/quarantine/disable control**; explicitly state what remains owned by adjacent services.
- [ ] **MC-017-CHK-002** — Assign an accountable owner and reviewer set for **Emergency freeze/quarantine/disable control** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-017-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Emergency freeze/quarantine/disable control**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-017-CHK-004** — Define the canonical data/state model for **Emergency freeze/quarantine/disable control**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-017-CHK-005** — Document safety/correctness invariants for **Emergency freeze/quarantine/disable control** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-017-CHK-006** — Define freeze/quarantine scopes for global service, tenant, site/region, topology subtree, node, workload class, and individual placement transaction.
- [ ] **MC-017-CHK-007** — Define control modes such as `freeze-new`, `drain`, `quarantine`, `disable-commit`, and emergency `hard-stop`, including which read/explain operations remain available.
- [ ] **MC-017-CHK-008** — Require privileged authorization and optional dual approval/break-glass workflow for high-blast-radius controls.
- [ ] **MC-017-CHK-009** — Persist control state durably with reason, actor, creation time, expiry/TTL, incident/change ticket, and monotonic generation so restart cannot unintentionally clear a freeze.
- [ ] **MC-017-CHK-010** — Propagate freeze state into scoring and commit paths atomically; a transaction prepared before a new freeze must be revalidated before commit.
- [ ] **MC-017-CHK-011** — Implement graceful drain semantics that stop new work and allow or time-bound in-flight work according to documented policy.
- [ ] **MC-017-CHK-012** — Allow narrowly scoped, time-limited emergency exceptions only through an audited explicit override path; never through undocumented flags.
- [ ] **MC-017-CHK-013** — Expose active controls in health, metrics, operator explain output, and audit logs without leaking unauthorized tenant details.
- [ ] **MC-017-CHK-014** — Provide safe CLI/API commands for create/list/extend/clear controls with idempotency and optimistic concurrency.
- [ ] **MC-017-CHK-015** — Test race conditions between freeze and commit, restart persistence, expired controls, nested scopes, conflicting controls, authorization denial, and recovery/drain completion.
### Security & trust

- [ ] **MC-017-CHK-016** — Complete a threat-model pass for **Emergency freeze/quarantine/disable control** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-017-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Emergency freeze/quarantine/disable control**; default to least privilege and explicitly test denied access.
- [ ] **MC-017-CHK-018** — Apply strict untrusted-input validation and resource limits to **Emergency freeze/quarantine/disable control** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-017-CHK-019** — Determine cryptographic/secret-management requirements for **Emergency freeze/quarantine/disable control**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-017-CHK-020** — Ensure sensitive data handled by **Emergency freeze/quarantine/disable control** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-017-CHK-021** — Create a failure-mode and recovery table for **Emergency freeze/quarantine/disable control** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-017-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Emergency freeze/quarantine/disable control** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-017-CHK-023** — Expose structured metrics/logs/traces/health for **Emergency freeze/quarantine/disable control** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-017-CHK-024** — Provide an operator runbook for **Emergency freeze/quarantine/disable control** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-017-CHK-025** — Implement unit tests for **Emergency freeze/quarantine/disable control** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-017-CHK-026** — Implement integration/contract tests for **Emergency freeze/quarantine/disable control** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-017-CHK-027** — Add fault/adversarial tests for **Emergency freeze/quarantine/disable control** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-017-CHK-028** — Benchmark or capacity-test **Emergency freeze/quarantine/disable control** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-017-CHK-029** — Link **Emergency freeze/quarantine/disable control** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-017-CHK-030** — Package production evidence for **Emergency freeze/quarantine/disable control** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-017 definition of done

- [ ] All **30 MC-017 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Emergency freeze/quarantine/disable control** satisfies its stated need: README describes suite-level removal, but no runtime kill switch or quarantine API exists.
- [ ] Required controls **C059, C092** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-017.

---

## MC-018 — Production health/readiness endpoint

**Priority:** P0  
**Need:** No endpoint exposes version, configuration generation, dependency status, or active capabilities.  
**Related controls:** C052, C071  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-018-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Production health/readiness endpoint**; explicitly state what remains owned by adjacent services.
- [ ] **MC-018-CHK-002** — Assign an accountable owner and reviewer set for **Production health/readiness endpoint** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-018-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Production health/readiness endpoint**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-018-CHK-004** — Define the canonical data/state model for **Production health/readiness endpoint**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-018-CHK-005** — Document safety/correctness invariants for **Production health/readiness endpoint** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-018-CHK-006** — Expose distinct liveness, startup, readiness, and deep-diagnostics endpoints so orchestration does not conflate process existence with safe ability to schedule.
- [ ] **MC-018-CHK-007** — Include build/version, API/schema versions, configuration generation/digest, topology generation, ledger revision, coordination role/term, and enabled capability set in protected diagnostics.
- [ ] **MC-018-CHK-008** — Readiness must fail when mandatory state/identity/coordination dependencies cannot support a safe placement commit, not merely when the process is running.
- [ ] **MC-018-CHK-009** — Report dependency state with bounded timeouts and reason codes; never let a health request block indefinitely behind a failed dependency.
- [ ] **MC-018-CHK-010** — Expose degraded-mode status, stale-data age, active freeze/quarantine state, pending migrations, and reconciliation backlog.
- [ ] **MC-018-CHK-011** — Protect deep health details with authorization and redact sensitive tenant/topology data; keep basic orchestrator probes minimal and cheap.
- [ ] **MC-018-CHK-012** — Implement probe response deadlines and resource isolation so health checking remains available under scheduler load without becoming an amplification vector.
- [ ] **MC-018-CHK-013** — Define readiness hysteresis/debounce to avoid rapid pod/service flapping during brief dependency jitter while preserving fail-safe behavior.
- [ ] **MC-018-CHK-014** — Publish health endpoint SLOs and wire them into deployment gates, load balancer registration, and alerting.
- [ ] **MC-018-CHK-015** — Test cold start, migration, leader election, dependency loss/restoration, stale state, overload, freeze, and graceful shutdown transitions against expected probe states.
### Security & trust

- [ ] **MC-018-CHK-016** — Complete a threat-model pass for **Production health/readiness endpoint** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-018-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Production health/readiness endpoint**; default to least privilege and explicitly test denied access.
- [ ] **MC-018-CHK-018** — Apply strict untrusted-input validation and resource limits to **Production health/readiness endpoint** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-018-CHK-019** — Determine cryptographic/secret-management requirements for **Production health/readiness endpoint**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-018-CHK-020** — Ensure sensitive data handled by **Production health/readiness endpoint** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-018-CHK-021** — Create a failure-mode and recovery table for **Production health/readiness endpoint** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-018-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Production health/readiness endpoint** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-018-CHK-023** — Expose structured metrics/logs/traces/health for **Production health/readiness endpoint** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-018-CHK-024** — Provide an operator runbook for **Production health/readiness endpoint** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-018-CHK-025** — Implement unit tests for **Production health/readiness endpoint** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-018-CHK-026** — Implement integration/contract tests for **Production health/readiness endpoint** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-018-CHK-027** — Add fault/adversarial tests for **Production health/readiness endpoint** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-018-CHK-028** — Benchmark or capacity-test **Production health/readiness endpoint** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-018-CHK-029** — Link **Production health/readiness endpoint** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-018-CHK-030** — Package production evidence for **Production health/readiness endpoint** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-018 definition of done

- [ ] All **30 MC-018 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Production health/readiness endpoint** satisfies its stated need: No endpoint exposes version, configuration generation, dependency status, or active capabilities.
- [ ] Required controls **C052, C071** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-018.

---

# P1 — Required for operational hardening and certification

All P1 controls inherit the global completion rules above.

---

## MC-019 — Metrics exporter

**Priority:** P1  
**Need:** Contract signals are prose only; no counters/histograms/gauges are emitted.  
**Related controls:** C061-C064, C069, C072  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-019-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Metrics exporter**; explicitly state what remains owned by adjacent services.
- [ ] **MC-019-CHK-002** — Assign an accountable owner and reviewer set for **Metrics exporter** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-019-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Metrics exporter**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-019-CHK-004** — Define the canonical data/state model for **Metrics exporter**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-019-CHK-005** — Document safety/correctness invariants for **Metrics exporter** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-019-CHK-006** — Define a versioned metric catalog with names, type, unit, labels, cardinality budget, description, owner, and deprecation policy.
- [ ] **MC-019-CHK-007** — Export request/scoring/commit latency histograms with stable buckets or native histograms and record count/error outcome separately from high-cardinality identifiers.
- [ ] **MC-019-CHK-008** — Emit candidate-set size, feasible-candidate count, locality-cost distribution, fairness verdict/denial reason, reservation utilization, and physical-capacity headroom metrics.
- [ ] **MC-019-CHK-009** — Emit stale-score rejection, topology-generation conflict, transaction retry, idempotent replay, release/reconciliation, and orphaned-reservation counters.
- [ ] **MC-019-CHK-010** — Export dependency latency/error/breaker state, coordination leader/term, cache hit/miss/eviction, store latency, and queue/concurrency saturation gauges.
- [ ] **MC-019-CHK-011** — Keep tenant/workload/node IDs out of general metric labels unless explicitly bounded and privacy-approved; use logs/traces for high-cardinality drill-down.
- [ ] **MC-019-CHK-012** — Provide OpenTelemetry/Prometheus-compatible export or an explicitly selected standard, with scrape/export authentication and backpressure handling.
- [ ] **MC-019-CHK-013** — Ensure telemetry failures cannot block placement critical paths; use bounded asynchronous queues and observable drop counters.
- [ ] **MC-019-CHK-014** — Define SLO-derived recording rules and alertable aggregates for availability, correctness proxies, latency, overload, and state drift.
- [ ] **MC-019-CHK-015** — Test metric presence/type/unit, label cardinality limits, exporter outage, high load, reset/restart semantics, and backward compatibility of dashboards/alerts.
### Security & trust

- [ ] **MC-019-CHK-016** — Complete a threat-model pass for **Metrics exporter** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-019-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Metrics exporter**; default to least privilege and explicitly test denied access.
- [ ] **MC-019-CHK-018** — Apply strict untrusted-input validation and resource limits to **Metrics exporter** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-019-CHK-019** — Determine cryptographic/secret-management requirements for **Metrics exporter**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-019-CHK-020** — Ensure sensitive data handled by **Metrics exporter** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-019-CHK-021** — Create a failure-mode and recovery table for **Metrics exporter** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-019-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Metrics exporter** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-019-CHK-023** — Expose structured metrics/logs/traces/health for **Metrics exporter** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-019-CHK-024** — Provide an operator runbook for **Metrics exporter** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-019-CHK-025** — Implement unit tests for **Metrics exporter** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-019-CHK-026** — Implement integration/contract tests for **Metrics exporter** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-019-CHK-027** — Add fault/adversarial tests for **Metrics exporter** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-019-CHK-028** — Benchmark or capacity-test **Metrics exporter** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-019-CHK-029** — Link **Metrics exporter** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-019-CHK-030** — Package production evidence for **Metrics exporter** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-019 definition of done

- [ ] All **30 MC-019 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Metrics exporter** satisfies its stated need: Contract signals are prose only; no counters/histograms/gauges are emitted.
- [ ] Required controls **C061-C064, C069, C072** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-019.

---

## MC-020 — Structured logging pipeline

**Priority:** P1  
**Need:** No stable structured event schema for tenant/node/workload/operation IDs.  
**Related controls:** C073, C075-C076  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-020-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Structured logging pipeline**; explicitly state what remains owned by adjacent services.
- [ ] **MC-020-CHK-002** — Assign an accountable owner and reviewer set for **Structured logging pipeline** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-020-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Structured logging pipeline**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-020-CHK-004** — Define the canonical data/state model for **Structured logging pipeline**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-020-CHK-005** — Document safety/correctness invariants for **Structured logging pipeline** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-020-CHK-006** — Define a stable structured log schema with timestamp, severity, event name/code, service/version, instance, request/transaction/trace IDs, tenant-safe identifier, topology/config generation, and outcome.
- [ ] **MC-020-CHK-007** — Use machine-readable JSON or equivalent structured encoding; prohibit parsing operational meaning from free-form message strings.
- [ ] **MC-020-CHK-008** — Generate correlation IDs at the ingress boundary when absent and propagate them through scoring, state access, downstream placement, retries, and audit events.
- [ ] **MC-020-CHK-009** — Define severity semantics and event taxonomy so `ERROR`, `WARN`, policy denial, expected conflict, and security event are not conflated.
- [ ] **MC-020-CHK-010** — Prevent log injection by canonical escaping/encoding of untrusted labels, node names, tenant metadata, and error text.
- [ ] **MC-020-CHK-011** — Redact credentials, tokens, secrets, raw attestation material, and sensitive tenant data; test redaction on nested exception/context payloads.
- [ ] **MC-020-CHK-012** — Use bounded asynchronous buffering with drop/backpressure policy and explicit dropped-event counters so logging outages do not halt scheduling.
- [ ] **MC-020-CHK-013** — Implement sampling/rate limiting for high-volume success/debug events while never sampling mandatory security/audit records below policy.
- [ ] **MC-020-CHK-014** — Define retention, rotation, compression, transport encryption, access control, and centralized export requirements.
- [ ] **MC-020-CHK-015** — Create golden event tests for critical workflows and schema validation tests that fail CI when required fields disappear or incompatible types change.
### Security & trust

- [ ] **MC-020-CHK-016** — Complete a threat-model pass for **Structured logging pipeline** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-020-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Structured logging pipeline**; default to least privilege and explicitly test denied access.
- [ ] **MC-020-CHK-018** — Apply strict untrusted-input validation and resource limits to **Structured logging pipeline** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-020-CHK-019** — Determine cryptographic/secret-management requirements for **Structured logging pipeline**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-020-CHK-020** — Ensure sensitive data handled by **Structured logging pipeline** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-020-CHK-021** — Create a failure-mode and recovery table for **Structured logging pipeline** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-020-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Structured logging pipeline** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-020-CHK-023** — Expose structured metrics/logs/traces/health for **Structured logging pipeline** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-020-CHK-024** — Provide an operator runbook for **Structured logging pipeline** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-020-CHK-025** — Implement unit tests for **Structured logging pipeline** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-020-CHK-026** — Implement integration/contract tests for **Structured logging pipeline** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-020-CHK-027** — Add fault/adversarial tests for **Structured logging pipeline** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-020-CHK-028** — Benchmark or capacity-test **Structured logging pipeline** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-020-CHK-029** — Link **Structured logging pipeline** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-020-CHK-030** — Package production evidence for **Structured logging pipeline** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-020 definition of done

- [ ] All **30 MC-020 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Structured logging pipeline** satisfies its stated need: No stable structured event schema for tenant/node/workload/operation IDs.
- [ ] Required controls **C073, C075-C076** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-020.

---

## MC-021 — Distributed tracing propagation

**Priority:** P1  
**Need:** No trace-context input/output exists at scheduler boundaries.  
**Related controls:** C074, C078  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-021-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Distributed tracing propagation**; explicitly state what remains owned by adjacent services.
- [ ] **MC-021-CHK-002** — Assign an accountable owner and reviewer set for **Distributed tracing propagation** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-021-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Distributed tracing propagation**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-021-CHK-004** — Define the canonical data/state model for **Distributed tracing propagation**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-021-CHK-005** — Document safety/correctness invariants for **Distributed tracing propagation** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-021-CHK-006** — Adopt a standard distributed trace context (for example W3C Trace Context through OpenTelemetry) and define ingress/egress propagation rules for every RPC/message boundary.
- [ ] **MC-021-CHK-007** — Create spans for admission, snapshot acquisition, candidate filtering, locality scoring, fairness evaluation, cache access, durable claim, downstream commit, and rollback/reconciliation.
- [ ] **MC-021-CHK-008** — Attach low-cardinality semantic attributes such as result class, candidate count, generations, dependency name, and retry count while excluding sensitive tenant payload.
- [ ] **MC-021-CHK-009** — Propagate context through asynchronous tasks/threads and ensure retries remain linked to the original transaction rather than creating unrelated traces.
- [ ] **MC-021-CHK-010** — Validate incoming trace headers and enforce size/count limits on baggage to prevent memory/cardinality abuse.
- [ ] **MC-021-CHK-011** — Define sampling that preserves errors, slow requests, stale-state conflicts, and security-relevant operations while keeping normal traffic cost bounded.
- [ ] **MC-021-CHK-012** — Record exception/status details using stable error codes and avoid duplicating secrets or large payload bodies in spans.
- [ ] **MC-021-CHK-013** — Correlate trace IDs with structured logs, audit events, and operator explain records.
- [ ] **MC-021-CHK-014** — Measure tracing overhead under load and provide a safe disable/degraded path for exporter failure without removing local correlation IDs.
- [ ] **MC-021-CHK-015** — Test propagation across SCH-01 and state services, async boundaries, retry chains, exporter outage, invalid headers, and sampling policy.
### Security & trust

- [ ] **MC-021-CHK-016** — Complete a threat-model pass for **Distributed tracing propagation** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-021-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Distributed tracing propagation**; default to least privilege and explicitly test denied access.
- [ ] **MC-021-CHK-018** — Apply strict untrusted-input validation and resource limits to **Distributed tracing propagation** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-021-CHK-019** — Determine cryptographic/secret-management requirements for **Distributed tracing propagation**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-021-CHK-020** — Ensure sensitive data handled by **Distributed tracing propagation** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-021-CHK-021** — Create a failure-mode and recovery table for **Distributed tracing propagation** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-021-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Distributed tracing propagation** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-021-CHK-023** — Expose structured metrics/logs/traces/health for **Distributed tracing propagation** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-021-CHK-024** — Provide an operator runbook for **Distributed tracing propagation** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-021-CHK-025** — Implement unit tests for **Distributed tracing propagation** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-021-CHK-026** — Implement integration/contract tests for **Distributed tracing propagation** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-021-CHK-027** — Add fault/adversarial tests for **Distributed tracing propagation** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-021-CHK-028** — Benchmark or capacity-test **Distributed tracing propagation** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-021-CHK-029** — Link **Distributed tracing propagation** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-021-CHK-030** — Package production evidence for **Distributed tracing propagation** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-021 definition of done

- [ ] All **30 MC-021 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Distributed tracing propagation** satisfies its stated need: No trace-context input/output exists at scheduler boundaries.
- [ ] Required controls **C074, C078** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-021.

---

## MC-022 — Operator explain API/view

**Priority:** P1  
**Need:** Score and fairness records are explainable in Python, but no operator-facing query/history view exists.  
**Related controls:** C076-C077  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-022-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Operator explain API/view**; explicitly state what remains owned by adjacent services.
- [ ] **MC-022-CHK-002** — Assign an accountable owner and reviewer set for **Operator explain API/view** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-022-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Operator explain API/view**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-022-CHK-004** — Define the canonical data/state model for **Operator explain API/view**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-022-CHK-005** — Document safety/correctness invariants for **Operator explain API/view** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-022-CHK-006** — Define an immutable decision/explanation record containing request/transaction ID, workload reference, candidate digest, topology/config/entitlement/ledger revisions, hard-filter outcomes, score components, fairness verdict, final selection, and error/commit state.
- [ ] **MC-022-CHK-007** — Persist only the minimum input snapshot or content-addressed references needed for reproducibility; avoid storing secret or bulky raw payloads when a verified digest/reference is sufficient.
- [ ] **MC-022-CHK-008** — Expose an authenticated, authorization-scoped query API with lookup by transaction/request/workload, bounded time range, pagination, and tenant isolation.
- [ ] **MC-022-CHK-009** — Return per-candidate hard-constraint failures separately from soft score components so operators can distinguish infeasibility from preference.
- [ ] **MC-022-CHK-010** — Include deterministic tie-break evidence and the exact scoring/config version so identical historical inputs can be replayed.
- [ ] **MC-022-CHK-011** — Capture fairness rationale including reservation, usage, physical capacity, entitlement revision, and denial/starvation/surplus state without exposing other tenants’ confidential details.
- [ ] **MC-022-CHK-012** — Provide retention and archival policy aligned with incident/debugging needs and privacy requirements.
- [ ] **MC-022-CHK-013** — Add a replay tool that can re-run a historical decision in non-mutating mode and flag divergence caused by code/config/schema version changes.
- [ ] **MC-022-CHK-014** — Instrument explain-query access itself with audit events and rate limits because explanations may reveal sensitive infrastructure metadata.
- [ ] **MC-022-CHK-015** — Test complete/partial records, denied access, historical migrations, pagination, replay determinism, redaction, and records spanning failed/rolled-back transactions.
### Security & trust

- [ ] **MC-022-CHK-016** — Complete a threat-model pass for **Operator explain API/view** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-022-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Operator explain API/view**; default to least privilege and explicitly test denied access.
- [ ] **MC-022-CHK-018** — Apply strict untrusted-input validation and resource limits to **Operator explain API/view** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-022-CHK-019** — Determine cryptographic/secret-management requirements for **Operator explain API/view**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-022-CHK-020** — Ensure sensitive data handled by **Operator explain API/view** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-022-CHK-021** — Create a failure-mode and recovery table for **Operator explain API/view** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-022-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Operator explain API/view** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-022-CHK-023** — Expose structured metrics/logs/traces/health for **Operator explain API/view** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-022-CHK-024** — Provide an operator runbook for **Operator explain API/view** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-022-CHK-025** — Implement unit tests for **Operator explain API/view** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-022-CHK-026** — Implement integration/contract tests for **Operator explain API/view** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-022-CHK-027** — Add fault/adversarial tests for **Operator explain API/view** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-022-CHK-028** — Benchmark or capacity-test **Operator explain API/view** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-022-CHK-029** — Link **Operator explain API/view** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-022-CHK-030** — Package production evidence for **Operator explain API/view** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-022 definition of done

- [ ] All **30 MC-022 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Operator explain API/view** satisfies its stated need: Score and fairness records are explainable in Python, but no operator-facing query/history view exists.
- [ ] Required controls **C076-C077** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-022.

---

## MC-023 — Dashboard and alert definitions

**Priority:** P1  
**Need:** No alert thresholds distinguish overload, policy denial, dependency failure, attack, or software defect.  
**Related controls:** C052, C080  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-023-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Dashboard and alert definitions**; explicitly state what remains owned by adjacent services.
- [ ] **MC-023-CHK-002** — Assign an accountable owner and reviewer set for **Dashboard and alert definitions** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-023-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Dashboard and alert definitions**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-023-CHK-004** — Define the canonical data/state model for **Dashboard and alert definitions**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-023-CHK-005** — Document safety/correctness invariants for **Dashboard and alert definitions** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-023-CHK-006** — Define operator dashboards around golden signals: traffic, errors, latency, saturation, plus correctness/state-drift and security indicators specific to scheduling.
- [ ] **MC-023-CHK-007** — Create panels for scoring latency/candidate count, commit latency, fairness denials, capacity headroom, topology/ledger generation lag, dependency health, and coordination ownership.
- [ ] **MC-023-CHK-008** — Distinguish overload, policy/fairness denial, dependency outage, stale-state conflict, security rejection, and internal software defect using separate metric/error dimensions.
- [ ] **MC-023-CHK-009** — Define SLO/error-budget burn alerts with multi-window thresholds rather than single static percentage alarms where service volume permits.
- [ ] **MC-023-CHK-010** — Add alerts for split-brain/fencing rejection, audit-log write failure, reconciliation drift, excessive orphan transactions, stale topology, and prolonged degraded mode.
- [ ] **MC-023-CHK-011** — Attach runbook links, owning team, severity, escalation target, and actionable first diagnostics to every alert definition.
- [ ] **MC-023-CHK-012** — Use environment-aware thresholds and suppress expected deployment/migration behavior through controlled maintenance signals rather than disabling alerting globally.
- [ ] **MC-023-CHK-013** — Validate dashboards/alerts against recorded/synthetic incidents and confirm alerts fire and clear at intended boundaries.
- [ ] **MC-023-CHK-014** — Version dashboard and alert definitions as code, review them with scheduler releases, and test query syntax in CI.
- [ ] **MC-023-CHK-015** — Track alert precision/noise and periodically retire or retune non-actionable alerts with documented rationale.
### Security & trust

- [ ] **MC-023-CHK-016** — Complete a threat-model pass for **Dashboard and alert definitions** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-023-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Dashboard and alert definitions**; default to least privilege and explicitly test denied access.
- [ ] **MC-023-CHK-018** — Apply strict untrusted-input validation and resource limits to **Dashboard and alert definitions** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-023-CHK-019** — Determine cryptographic/secret-management requirements for **Dashboard and alert definitions**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-023-CHK-020** — Ensure sensitive data handled by **Dashboard and alert definitions** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-023-CHK-021** — Create a failure-mode and recovery table for **Dashboard and alert definitions** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-023-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Dashboard and alert definitions** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-023-CHK-023** — Expose structured metrics/logs/traces/health for **Dashboard and alert definitions** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-023-CHK-024** — Provide an operator runbook for **Dashboard and alert definitions** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-023-CHK-025** — Implement unit tests for **Dashboard and alert definitions** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-023-CHK-026** — Implement integration/contract tests for **Dashboard and alert definitions** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-023-CHK-027** — Add fault/adversarial tests for **Dashboard and alert definitions** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-023-CHK-028** — Benchmark or capacity-test **Dashboard and alert definitions** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-023-CHK-029** — Link **Dashboard and alert definitions** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-023-CHK-030** — Package production evidence for **Dashboard and alert definitions** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-023 definition of done

- [ ] All **30 MC-023 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Dashboard and alert definitions** satisfies its stated need: No alert thresholds distinguish overload, policy denial, dependency failure, attack, or software defect.
- [ ] Required controls **C052, C080** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-023.

---

## MC-024 — Telemetry privacy/retention/export policy

**Priority:** P1  
**Need:** No sampling, retention, redaction, tenant-privacy, or export configuration exists.  
**Related controls:** C075, C079  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-024-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Telemetry privacy/retention/export policy**; explicitly state what remains owned by adjacent services.
- [ ] **MC-024-CHK-002** — Assign an accountable owner and reviewer set for **Telemetry privacy/retention/export policy** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-024-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Telemetry privacy/retention/export policy**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-024-CHK-004** — Define the canonical data/state model for **Telemetry privacy/retention/export policy**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-024-CHK-005** — Document safety/correctness invariants for **Telemetry privacy/retention/export policy** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-024-CHK-006** — Classify every telemetry field as public/internal/confidential/sensitive and identify tenant, infrastructure, security, and potentially identifying data before export.
- [ ] **MC-024-CHK-007** — Define allowed identifiers per telemetry signal; prefer pseudonymous/content-hash IDs and prohibit raw sensitive payloads in metrics.
- [ ] **MC-024-CHK-008** — Create redaction/tokenization rules for logs, traces, explain records, and audit exports, including nested exception and metadata structures.
- [ ] **MC-024-CHK-009** — Define retention periods by data class and telemetry type, with secure deletion/expiry mechanisms and documented exceptions for security evidence.
- [ ] **MC-024-CHK-010** — Apply least-privilege access controls and tenant boundaries to dashboards, logs, traces, explain APIs, and exported archives.
- [ ] **MC-024-CHK-011** — Encrypt telemetry in transit and at rest according to organizational policy and protect exporter credentials through managed secret mechanisms.
- [ ] **MC-024-CHK-012** — Define sampling policies that preserve required audit/security events while controlling cost and unnecessary data collection.
- [ ] **MC-024-CHK-013** — Control external/export destinations with explicit allowlists, data-processing agreements/policy where applicable, and observable export failures.
- [ ] **MC-024-CHK-014** — Implement deletion/tenant-offboarding workflows where legally/policy required without corrupting immutable security records that have separate retention authority.
- [ ] **MC-024-CHK-015** — Test redaction bypass, structured-field injection, unauthorized query, export misconfiguration, retention expiry, backup copies, and cross-tenant data leakage.
### Security & trust

- [ ] **MC-024-CHK-016** — Complete a threat-model pass for **Telemetry privacy/retention/export policy** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-024-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Telemetry privacy/retention/export policy**; default to least privilege and explicitly test denied access.
- [ ] **MC-024-CHK-018** — Apply strict untrusted-input validation and resource limits to **Telemetry privacy/retention/export policy** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-024-CHK-019** — Determine cryptographic/secret-management requirements for **Telemetry privacy/retention/export policy**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-024-CHK-020** — Ensure sensitive data handled by **Telemetry privacy/retention/export policy** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-024-CHK-021** — Create a failure-mode and recovery table for **Telemetry privacy/retention/export policy** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-024-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Telemetry privacy/retention/export policy** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-024-CHK-023** — Expose structured metrics/logs/traces/health for **Telemetry privacy/retention/export policy** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-024-CHK-024** — Provide an operator runbook for **Telemetry privacy/retention/export policy** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-024-CHK-025** — Implement unit tests for **Telemetry privacy/retention/export policy** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-024-CHK-026** — Implement integration/contract tests for **Telemetry privacy/retention/export policy** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-024-CHK-027** — Add fault/adversarial tests for **Telemetry privacy/retention/export policy** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-024-CHK-028** — Benchmark or capacity-test **Telemetry privacy/retention/export policy** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-024-CHK-029** — Link **Telemetry privacy/retention/export policy** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-024-CHK-030** — Package production evidence for **Telemetry privacy/retention/export policy** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-024 definition of done

- [ ] All **30 MC-024 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Telemetry privacy/retention/export policy** satisfies its stated need: No sampling, retention, redaction, tenant-privacy, or export configuration exists.
- [ ] Required controls **C075, C079** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-024.

---

## MC-025 — Admission control / load shedding / circuit breaker

**Priority:** P1  
**Need:** The local functions bound neither request rate nor queue/fan-out under overload.  
**Related controls:** C053-C054, C067  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-025-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Admission control / load shedding / circuit breaker**; explicitly state what remains owned by adjacent services.
- [ ] **MC-025-CHK-002** — Assign an accountable owner and reviewer set for **Admission control / load shedding / circuit breaker** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-025-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Admission control / load shedding / circuit breaker**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-025-CHK-004** — Define the canonical data/state model for **Admission control / load shedding / circuit breaker**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-025-CHK-005** — Document safety/correctness invariants for **Admission control / load shedding / circuit breaker** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-025-CHK-006** — Define independent limits for ingress requests, candidate fan-out, concurrent scoring, concurrent commits, queue depth, and dependency concurrency.
- [ ] **MC-025-CHK-007** — Implement global and tenant/workload-class admission policy so one noisy tenant cannot exhaust scheduler worker, store, or coordination capacity.
- [ ] **MC-025-CHK-008** — Use bounded queues/semaphores/token buckets and reject or shed before memory/thread/connection exhaustion occurs.
- [ ] **MC-025-CHK-009** — Define workload priority classes and deterministic shedding order; never drop already-committed state transitions without reconciliation.
- [ ] **MC-025-CHK-010** — Add circuit breakers around slow/failing dependencies with open/half-open/closed state, bounded probes, and explicit recovery criteria.
- [ ] **MC-025-CHK-011** — Propagate backpressure to SCH-01/clients using stable overload codes and retry-after guidance instead of accepting unbounded queued work.
- [ ] **MC-025-CHK-012** — Account retries against a retry budget so overload does not self-amplify through repeated calls.
- [ ] **MC-025-CHK-013** — Reserve control-plane capacity for health, freeze/quarantine, release/rollback, and reconciliation operations even when new-placement admission is closed.
- [ ] **MC-025-CHK-014** — Emit saturation, queue wait, rejected requests, shed class, breaker state, and concurrency utilization metrics.
- [ ] **MC-025-CHK-015** — Load-test burst, sustained overload, slow dependency, tenant hotspot, and recovery; verify bounded memory/latency and rapid restoration after load subsides.
### Security & trust

- [ ] **MC-025-CHK-016** — Complete a threat-model pass for **Admission control / load shedding / circuit breaker** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-025-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Admission control / load shedding / circuit breaker**; default to least privilege and explicitly test denied access.
- [ ] **MC-025-CHK-018** — Apply strict untrusted-input validation and resource limits to **Admission control / load shedding / circuit breaker** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-025-CHK-019** — Determine cryptographic/secret-management requirements for **Admission control / load shedding / circuit breaker**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-025-CHK-020** — Ensure sensitive data handled by **Admission control / load shedding / circuit breaker** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-025-CHK-021** — Create a failure-mode and recovery table for **Admission control / load shedding / circuit breaker** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-025-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Admission control / load shedding / circuit breaker** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-025-CHK-023** — Expose structured metrics/logs/traces/health for **Admission control / load shedding / circuit breaker** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-025-CHK-024** — Provide an operator runbook for **Admission control / load shedding / circuit breaker** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-025-CHK-025** — Implement unit tests for **Admission control / load shedding / circuit breaker** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-025-CHK-026** — Implement integration/contract tests for **Admission control / load shedding / circuit breaker** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-025-CHK-027** — Add fault/adversarial tests for **Admission control / load shedding / circuit breaker** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-025-CHK-028** — Benchmark or capacity-test **Admission control / load shedding / circuit breaker** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-025-CHK-029** — Link **Admission control / load shedding / circuit breaker** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-025-CHK-030** — Package production evidence for **Admission control / load shedding / circuit breaker** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-025 definition of done

- [ ] All **30 MC-025 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Admission control / load shedding / circuit breaker** satisfies its stated need: The local functions bound neither request rate nor queue/fan-out under overload.
- [ ] Required controls **C053-C054, C067** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-025.

---

## MC-026 — Retry/backoff/idempotency layer

**Priority:** P1  
**Need:** No retry policy exists for external dependencies or state commits.  
**Related controls:** C025, C053  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-026-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Retry/backoff/idempotency layer**; explicitly state what remains owned by adjacent services.
- [ ] **MC-026-CHK-002** — Assign an accountable owner and reviewer set for **Retry/backoff/idempotency layer** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-026-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Retry/backoff/idempotency layer**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-026-CHK-004** — Define the canonical data/state model for **Retry/backoff/idempotency layer**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-026-CHK-005** — Document safety/correctness invariants for **Retry/backoff/idempotency layer** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-026-CHK-006** — Classify every external operation as read-only, idempotent mutation, non-idempotent mutation, or transaction phase and define whether automatic retry is permitted.
- [ ] **MC-026-CHK-007** — Assign end-to-end deadlines and derive per-attempt timeout budgets so nested retries cannot exceed the caller’s overall placement deadline.
- [ ] **MC-026-CHK-008** — Use exponential backoff with jitter and a maximum retry count/duration; prohibit synchronized fixed-interval retry storms.
- [ ] **MC-026-CHK-009** — Generate/propagate idempotency keys for mutation calls and persist deduplication outcomes for at least the maximum retry/replay window.
- [ ] **MC-026-CHK-010** — Retry only explicitly transient codes and respect server retry-after/backpressure signals; never retry validation, authorization, stale-fencing, or deterministic capacity denials as though transient.
- [ ] **MC-026-CHK-011** — Define behavior for lost responses where server outcome is unknown; query transaction state before issuing a semantically duplicate mutation.
- [ ] **MC-026-CHK-012** — Use retry budgets per dependency/tenant and disable speculative hedging for operations where duplicate side effects cannot be safely deduplicated.
- [ ] **MC-026-CHK-013** — Quarantine/alert on poison messages or permanently failing transactions rather than retrying indefinitely.
- [ ] **MC-026-CHK-014** — Expose attempts, backoff time, terminal reason, dedup hits, and retry-budget exhaustion through traces/metrics.
- [ ] **MC-026-CHK-015** — Test timeout-before-send, timeout-after-commit, duplicate response, partial network failure, server restart, overload retry-after, and idempotency-window expiry.
### Security & trust

- [ ] **MC-026-CHK-016** — Complete a threat-model pass for **Retry/backoff/idempotency layer** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-026-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Retry/backoff/idempotency layer**; default to least privilege and explicitly test denied access.
- [ ] **MC-026-CHK-018** — Apply strict untrusted-input validation and resource limits to **Retry/backoff/idempotency layer** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-026-CHK-019** — Determine cryptographic/secret-management requirements for **Retry/backoff/idempotency layer**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-026-CHK-020** — Ensure sensitive data handled by **Retry/backoff/idempotency layer** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-026-CHK-021** — Create a failure-mode and recovery table for **Retry/backoff/idempotency layer** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-026-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Retry/backoff/idempotency layer** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-026-CHK-023** — Expose structured metrics/logs/traces/health for **Retry/backoff/idempotency layer** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-026-CHK-024** — Provide an operator runbook for **Retry/backoff/idempotency layer** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-026-CHK-025** — Implement unit tests for **Retry/backoff/idempotency layer** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-026-CHK-026** — Implement integration/contract tests for **Retry/backoff/idempotency layer** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-026-CHK-027** — Add fault/adversarial tests for **Retry/backoff/idempotency layer** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-026-CHK-028** — Benchmark or capacity-test **Retry/backoff/idempotency layer** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-026-CHK-029** — Link **Retry/backoff/idempotency layer** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-026-CHK-030** — Package production evidence for **Retry/backoff/idempotency layer** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-026 definition of done

- [ ] All **30 MC-026 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Retry/backoff/idempotency layer** satisfies its stated need: No retry policy exists for external dependencies or state commits.
- [ ] Required controls **C025, C053** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-026.

---

## MC-027 — Latency-refinement engine

**Priority:** P1  
**Need:** Contract lists measured-latency refinement as optional, but there is no trusted measurement ingest, smoothing, staleness handling, or injection defense.  
**Related controls:** C004, C041, C050, C066  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-027-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Latency-refinement engine**; explicitly state what remains owned by adjacent services.
- [ ] **MC-027-CHK-002** — Assign an accountable owner and reviewer set for **Latency-refinement engine** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-027-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Latency-refinement engine**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-027-CHK-004** — Define the canonical data/state model for **Latency-refinement engine**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-027-CHK-005** — Document safety/correctness invariants for **Latency-refinement engine** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-027-CHK-006** — Define trusted latency measurement sources, probe identity, measurement path, direction, protocol, sample timestamp, topology endpoints, and provenance.
- [ ] **MC-027-CHK-007** — Authenticate measurement producers and validate endpoint ownership so an untrusted node cannot arbitrarily bias scheduler scores by injecting fabricated latency.
- [ ] **MC-027-CHK-008** — Normalize samples into canonical units with strict bounds and reject negative, impossible, non-finite, duplicate, or grossly future-dated values.
- [ ] **MC-027-CHK-009** — Implement smoothing/aggregation such as EWMA or robust quantiles with documented window size and sensitivity to spikes; preserve raw sample confidence/count metadata.
- [ ] **MC-027-CHK-010** — Apply freshness TTL and confidence thresholds; decay, ignore, or fall back to static topology cost when measurement evidence is stale or insufficient.
- [ ] **MC-027-CHK-011** — Use robust outlier detection and rate-of-change limits to reduce susceptibility to transient anomalies and manipulation while retaining genuine failure signals.
- [ ] **MC-027-CHK-012** — Model asymmetric paths where relevant instead of assuming A→B equals B→A; document how missing direction data is handled.
- [ ] **MC-027-CHK-013** — Expose measured-latency contribution, sample age, confidence, and fallback status in the candidate explain record.
- [ ] **MC-027-CHK-014** — Bound measurement-state memory/cardinality and define cache invalidation when nodes/topology generations change.
- [ ] **MC-027-CHK-015** — Test poisoned samples, burst jitter, route change, stale data, sparse data, asymmetric links, clock skew, source compromise simulation, and fallback determinism.
### Security & trust

- [ ] **MC-027-CHK-016** — Complete a threat-model pass for **Latency-refinement engine** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-027-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Latency-refinement engine**; default to least privilege and explicitly test denied access.
- [ ] **MC-027-CHK-018** — Apply strict untrusted-input validation and resource limits to **Latency-refinement engine** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-027-CHK-019** — Determine cryptographic/secret-management requirements for **Latency-refinement engine**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-027-CHK-020** — Ensure sensitive data handled by **Latency-refinement engine** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-027-CHK-021** — Create a failure-mode and recovery table for **Latency-refinement engine** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-027-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Latency-refinement engine** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-027-CHK-023** — Expose structured metrics/logs/traces/health for **Latency-refinement engine** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-027-CHK-024** — Provide an operator runbook for **Latency-refinement engine** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-027-CHK-025** — Implement unit tests for **Latency-refinement engine** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-027-CHK-026** — Implement integration/contract tests for **Latency-refinement engine** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-027-CHK-027** — Add fault/adversarial tests for **Latency-refinement engine** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-027-CHK-028** — Benchmark or capacity-test **Latency-refinement engine** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-027-CHK-029** — Link **Latency-refinement engine** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-027-CHK-030** — Package production evidence for **Latency-refinement engine** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-027 definition of done

- [ ] All **30 MC-027 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Latency-refinement engine** satisfies its stated need: Contract lists measured-latency refinement as optional, but there is no trusted measurement ingest, smoothing, staleness handling, or injection defense.
- [ ] Required controls **C004, C041, C050, C066** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-027.

---

## MC-028 — Topology/cost cache with invalidation

**Priority:** P1  
**Need:** No generation-keyed cache exists for repeated large-fleet scoring.  
**Related controls:** C061-C066  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-028-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Topology/cost cache with invalidation**; explicitly state what remains owned by adjacent services.
- [ ] **MC-028-CHK-002** — Assign an accountable owner and reviewer set for **Topology/cost cache with invalidation** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-028-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Topology/cost cache with invalidation**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-028-CHK-004** — Define the canonical data/state model for **Topology/cost cache with invalidation**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-028-CHK-005** — Document safety/correctness invariants for **Topology/cost cache with invalidation** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-028-CHK-006** — Define cacheable computations and prove their keys include every state dimension that can change the result, including topology/config/entitlement/ledger generations where applicable.
- [ ] **MC-028-CHK-007** — Use immutable/cache-safe value objects so callers cannot mutate cached topology or score artifacts in place.
- [ ] **MC-028-CHK-008** — Define bounded memory capacity, eviction policy, TTL, and per-entry size limits; prevent tenant-controlled keys from causing unbounded cardinality.
- [ ] **MC-028-CHK-009** — Invalidate or namespace cache entries on topology/config/schema generation changes rather than relying only on time-based expiry.
- [ ] **MC-028-CHK-010** — Use single-flight/request coalescing or jittered refresh to prevent cache stampedes after invalidation or cold start.
- [ ] **MC-028-CHK-011** — Ensure thread/process safety and define whether caches are local, distributed, or read-through; do not rely on cache coherence for correctness-critical state.
- [ ] **MC-028-CHK-012** — Never cache a mutable capacity claim/authorization result beyond its revision precondition; revalidate correctness-critical state at commit.
- [ ] **MC-028-CHK-013** — Expose hit/miss/eviction/stale-reject/build-time/size metrics without high-cardinality cache-key labels.
- [ ] **MC-028-CHK-014** — Provide cache warm-up/precompute only where measured beneficial and ensure warm-up cannot delay readiness indefinitely.
- [ ] **MC-028-CHK-015** — Test generation change, concurrent fill, eviction pressure, key collision, stale entry, corrupt entry, cache disable, and correctness equivalence between cached and uncached paths.
### Security & trust

- [ ] **MC-028-CHK-016** — Complete a threat-model pass for **Topology/cost cache with invalidation** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-028-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Topology/cost cache with invalidation**; default to least privilege and explicitly test denied access.
- [ ] **MC-028-CHK-018** — Apply strict untrusted-input validation and resource limits to **Topology/cost cache with invalidation** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-028-CHK-019** — Determine cryptographic/secret-management requirements for **Topology/cost cache with invalidation**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-028-CHK-020** — Ensure sensitive data handled by **Topology/cost cache with invalidation** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-028-CHK-021** — Create a failure-mode and recovery table for **Topology/cost cache with invalidation** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-028-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Topology/cost cache with invalidation** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-028-CHK-023** — Expose structured metrics/logs/traces/health for **Topology/cost cache with invalidation** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-028-CHK-024** — Provide an operator runbook for **Topology/cost cache with invalidation** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-028-CHK-025** — Implement unit tests for **Topology/cost cache with invalidation** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-028-CHK-026** — Implement integration/contract tests for **Topology/cost cache with invalidation** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-028-CHK-027** — Add fault/adversarial tests for **Topology/cost cache with invalidation** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-028-CHK-028** — Benchmark or capacity-test **Topology/cost cache with invalidation** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-028-CHK-029** — Link **Topology/cost cache with invalidation** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-028-CHK-030** — Package production evidence for **Topology/cost cache with invalidation** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-028 definition of done

- [ ] All **30 MC-028 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Topology/cost cache with invalidation** satisfies its stated need: No generation-keyed cache exists for repeated large-fleet scoring.
- [ ] Required controls **C061-C066** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-028.

---

## MC-029 — Multi-objective score composition

**Priority:** P1  
**Need:** No configurable weights for locality, data gravity, connectivity, cost, or other soft objectives.  
**Related controls:** C007, C019, C066  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-029-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Multi-objective score composition**; explicitly state what remains owned by adjacent services.
- [ ] **MC-029-CHK-002** — Assign an accountable owner and reviewer set for **Multi-objective score composition** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-029-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Multi-objective score composition**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-029-CHK-004** — Define the canonical data/state model for **Multi-objective score composition**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-029-CHK-005** — Document safety/correctness invariants for **Multi-objective score composition** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-029-CHK-006** — Define the complete objective vector (for example topology locality, measured latency, data gravity, network cost, energy, monetary cost, disruption risk) and classify each as hard constraint or soft objective.
- [ ] **MC-029-CHK-007** — Normalize each soft objective to a documented dimensionless range or comparable scale so raw units cannot accidentally dominate combined score.
- [ ] **MC-029-CHK-008** — Define configurable weights with safe numeric bounds, defaults, versioned configuration, and validation that rejects NaN/Inf/negative values where not meaningful.
- [ ] **MC-029-CHK-009** — Keep fairness/entitlement/physical-capacity/security hard gates outside the weighted sum unless the policy explicitly models them as admissibility constraints.
- [ ] **MC-029-CHK-010** — Define missing-signal behavior per objective (neutral, disabled, penalty, or hard deny) and include source freshness/confidence in that decision.
- [ ] **MC-029-CHK-011** — Preserve deterministic tie-breaking after score composition using stable candidate identity/order rules independent of hash randomization.
- [ ] **MC-029-CHK-012** — Expose every normalized component, weight, subtotal, hard-filter outcome, and final score in explain output.
- [ ] **MC-029-CHK-013** — Add monotonicity/invariance tests showing that improving one isolated objective cannot worsen its own contribution and unit scaling does not change ranking unexpectedly.
- [ ] **MC-029-CHK-014** — Run sensitivity/perturbation analysis across representative workloads to detect weight regimes where tiny input noise causes unstable placement oscillation.
- [ ] **MC-029-CHK-015** — Version scoring formulas and provide replay/compatibility tests so a release can explain why ranking changed relative to a previous scoring version.
### Security & trust

- [ ] **MC-029-CHK-016** — Complete a threat-model pass for **Multi-objective score composition** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-029-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Multi-objective score composition**; default to least privilege and explicitly test denied access.
- [ ] **MC-029-CHK-018** — Apply strict untrusted-input validation and resource limits to **Multi-objective score composition** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-029-CHK-019** — Determine cryptographic/secret-management requirements for **Multi-objective score composition**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-029-CHK-020** — Ensure sensitive data handled by **Multi-objective score composition** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-029-CHK-021** — Create a failure-mode and recovery table for **Multi-objective score composition** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-029-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Multi-objective score composition** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-029-CHK-023** — Expose structured metrics/logs/traces/health for **Multi-objective score composition** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-029-CHK-024** — Provide an operator runbook for **Multi-objective score composition** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-029-CHK-025** — Implement unit tests for **Multi-objective score composition** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-029-CHK-026** — Implement integration/contract tests for **Multi-objective score composition** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-029-CHK-027** — Add fault/adversarial tests for **Multi-objective score composition** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-029-CHK-028** — Benchmark or capacity-test **Multi-objective score composition** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-029-CHK-029** — Link **Multi-objective score composition** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-029-CHK-030** — Package production evidence for **Multi-objective score composition** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-029 definition of done

- [ ] All **30 MC-029 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Multi-objective score composition** satisfies its stated need: No configurable weights for locality, data gravity, connectivity, cost, or other soft objectives.
- [ ] Required controls **C007, C019, C066** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-029.

---

## MC-030 — Capacity/saturation model

**Priority:** P1  
**Need:** No model predicts scheduler saturation or required control-plane resources.  
**Related controls:** C061-C069  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-030-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Capacity/saturation model**; explicitly state what remains owned by adjacent services.
- [ ] **MC-030-CHK-002** — Assign an accountable owner and reviewer set for **Capacity/saturation model** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-030-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Capacity/saturation model**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-030-CHK-004** — Define the canonical data/state model for **Capacity/saturation model**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-030-CHK-005** — Document safety/correctness invariants for **Capacity/saturation model** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-030-CHK-006** — Define the scheduler workload model using request arrival rate, candidate count distribution, topology size, objective count, commit rate, state-store latency, and concurrency.
- [ ] **MC-030-CHK-007** — Measure per-stage CPU time, allocations/memory, I/O, lock contention, queue time, and downstream call count under representative workloads.
- [ ] **MC-030-CHK-008** — Build a capacity model relating replicas/CPU/memory/store throughput to sustainable requests per second and target p50/p95/p99 latency.
- [ ] **MC-030-CHK-009** — Include burst capacity and headroom targets rather than sizing at mean utilization; define maximum safe concurrency before latency/error runaway.
- [ ] **MC-030-CHK-010** — Model candidate fan-out and topology depth effects explicitly, including worst-case pathological but valid inputs.
- [ ] **MC-030-CHK-011** — Include state-store/coordination saturation and dependency latency in bottleneck analysis rather than measuring only pure scoring CPU.
- [ ] **MC-030-CHK-012** — Define autoscaling or replica-sizing signals and minimum/maximum fleet size with anti-thrash stabilization windows.
- [ ] **MC-030-CHK-013** — Identify single-threaded/global-lock/leader bottlenecks and define scale-up/scale-out ceilings for each architecture mode.
- [ ] **MC-030-CHK-014** — Continuously compare predicted vs measured throughput/latency and recalibrate the model when implementation or hardware changes.
- [ ] **MC-030-CHK-015** — Produce an operator capacity guide with safe request/candidate/topology envelopes and alerts before the service enters unstable saturation.
### Security & trust

- [ ] **MC-030-CHK-016** — Complete a threat-model pass for **Capacity/saturation model** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-030-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Capacity/saturation model**; default to least privilege and explicitly test denied access.
- [ ] **MC-030-CHK-018** — Apply strict untrusted-input validation and resource limits to **Capacity/saturation model** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-030-CHK-019** — Determine cryptographic/secret-management requirements for **Capacity/saturation model**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-030-CHK-020** — Ensure sensitive data handled by **Capacity/saturation model** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-030-CHK-021** — Create a failure-mode and recovery table for **Capacity/saturation model** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-030-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Capacity/saturation model** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-030-CHK-023** — Expose structured metrics/logs/traces/health for **Capacity/saturation model** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-030-CHK-024** — Provide an operator runbook for **Capacity/saturation model** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-030-CHK-025** — Implement unit tests for **Capacity/saturation model** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-030-CHK-026** — Implement integration/contract tests for **Capacity/saturation model** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-030-CHK-027** — Add fault/adversarial tests for **Capacity/saturation model** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-030-CHK-028** — Benchmark or capacity-test **Capacity/saturation model** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-030-CHK-029** — Link **Capacity/saturation model** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-030-CHK-030** — Package production evidence for **Capacity/saturation model** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-030 definition of done

- [ ] All **30 MC-030 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Capacity/saturation model** satisfies its stated need: No model predicts scheduler saturation or required control-plane resources.
- [ ] Required controls **C061-C069** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-030.

---

## MC-031 — Production benchmark baseline and regression gate

**Priority:** P1  
**Need:** A non-gating local 1,000-candidate benchmark now exists, but there is no controlled per-platform baseline, load matrix, accepted threshold file, or CI release gate.  
**Related controls:** C061-C063, C070, C088  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-031-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Production benchmark baseline and regression gate**; explicitly state what remains owned by adjacent services.
- [ ] **MC-031-CHK-002** — Assign an accountable owner and reviewer set for **Production benchmark baseline and regression gate** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-031-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Production benchmark baseline and regression gate**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-031-CHK-004** — Define the canonical data/state model for **Production benchmark baseline and regression gate**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-031-CHK-005** — Document safety/correctness invariants for **Production benchmark baseline and regression gate** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-031-CHK-006** — Create a dedicated benchmark harness separated from functional unit tests, with fixed seeds, immutable workload fixtures, and machine-readable results.
- [ ] **MC-031-CHK-007** — Define a workload matrix spanning candidate counts, topology depths/sizes, tenant counts, objective combinations, cache states, concurrency, and commit/no-commit paths.
- [ ] **MC-031-CHK-008** — Record hardware/VM/container/OS/Python/runtime/compiler/power-mode metadata with every baseline so results are comparable.
- [ ] **MC-031-CHK-009** — Use controlled warm-up and repeated samples; report p50/p90/p95/p99/max, throughput, CPU, memory, allocations, and variance/confidence where practical.
- [ ] **MC-031-CHK-010** — Establish accepted per-platform threshold files with explicit regression budgets for latency, throughput, and memory rather than one ad hoc local number.
- [ ] **MC-031-CHK-011** — Benchmark dependency-mocked and integrated state-store paths separately so pure algorithm regressions can be distinguished from environment latency.
- [ ] **MC-031-CHK-012** — Run selected benchmarks as blocking CI/release gates on stable runners and keep larger stress/soak suites scheduled but reproducible.
- [ ] **MC-031-CHK-013** — Fail or require reviewed waiver when a threshold regresses beyond budget; store the before/after evidence with the release artifact.
- [ ] **MC-031-CHK-014** — Maintain longitudinal trend data keyed by commit/version and annotate hardware or methodology changes that invalidate direct comparison.
- [ ] **MC-031-CHK-015** — Validate the benchmark itself for timer resolution, dead-code avoidance, GC effects, warm-cache bias, and unrealistic fixture simplifications before using it for certification.
### Security & trust

- [ ] **MC-031-CHK-016** — Complete a threat-model pass for **Production benchmark baseline and regression gate** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-031-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Production benchmark baseline and regression gate**; default to least privilege and explicitly test denied access.
- [ ] **MC-031-CHK-018** — Apply strict untrusted-input validation and resource limits to **Production benchmark baseline and regression gate** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-031-CHK-019** — Determine cryptographic/secret-management requirements for **Production benchmark baseline and regression gate**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-031-CHK-020** — Ensure sensitive data handled by **Production benchmark baseline and regression gate** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-031-CHK-021** — Create a failure-mode and recovery table for **Production benchmark baseline and regression gate** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-031-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Production benchmark baseline and regression gate** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-031-CHK-023** — Expose structured metrics/logs/traces/health for **Production benchmark baseline and regression gate** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-031-CHK-024** — Provide an operator runbook for **Production benchmark baseline and regression gate** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-031-CHK-025** — Implement unit tests for **Production benchmark baseline and regression gate** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-031-CHK-026** — Implement integration/contract tests for **Production benchmark baseline and regression gate** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-031-CHK-027** — Add fault/adversarial tests for **Production benchmark baseline and regression gate** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-031-CHK-028** — Benchmark or capacity-test **Production benchmark baseline and regression gate** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-031-CHK-029** — Link **Production benchmark baseline and regression gate** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-031-CHK-030** — Package production evidence for **Production benchmark baseline and regression gate** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-031 definition of done

- [ ] All **30 MC-031 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Production benchmark baseline and regression gate** satisfies its stated need: A non-gating local 1,000-candidate benchmark now exists, but there is no controlled per-platform baseline, load matrix, accepted threshold file, or CI release gate.
- [ ] Required controls **C061-C063, C070, C088** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-031.

---

## MC-032 — Fault-injection / partition test suite

**Priority:** P1  
**Need:** No crash, disconnect, split-brain, reconnect, stale-controller, or degraded-control-plane tests are present.  
**Related controls:** C051-C060, C089  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-032-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Fault-injection / partition test suite**; explicitly state what remains owned by adjacent services.
- [ ] **MC-032-CHK-002** — Assign an accountable owner and reviewer set for **Fault-injection / partition test suite** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-032-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Fault-injection / partition test suite**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-032-CHK-004** — Define the canonical data/state model for **Fault-injection / partition test suite**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-032-CHK-005** — Document safety/correctness invariants for **Fault-injection / partition test suite** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-032-CHK-006** — Build a fault-injection harness capable of killing scheduler replicas at deterministic points in score, reserve, commit, release, reconciliation, and migration workflows.
- [ ] **MC-032-CHK-007** — Inject full and asymmetric network partitions between scheduler replicas, coordination service, state stores, entitlement authority, SCH-01, and peer feeds.
- [ ] **MC-032-CHK-008** — Inject latency, packet loss, connection resets, DNS failure, TLS failure, and intermittent dependency errors with reproducible seeds/scenarios.
- [ ] **MC-032-CHK-009** — Simulate leader loss and stale-controller behavior, including delayed messages from the former leader after a new fencing epoch is active.
- [ ] **MC-032-CHK-010** — Inject durable-store crash/restart, read-only mode, disk-full/quota, high latency, transaction conflict, and partial replica outage.
- [ ] **MC-032-CHK-011** — Simulate clock skew/time jumps where time-based leases/TTLs exist and assert fencing/expiry semantics remain safe.
- [ ] **MC-032-CHK-012** — Inject duplicate, reordered, delayed, and replayed placement transaction messages to verify idempotency and stale-state rejection.
- [ ] **MC-032-CHK-013** — Assert safety invariants after every scenario: no capacity overcommit, no unauthorized topology mutation, no duplicate committed placement, no negative ledger state, and bounded orphan claims.
- [ ] **MC-032-CHK-014** — Verify recovery convergence and define maximum acceptable reconciliation time/backlog after the fault is removed.
- [ ] **MC-032-CHK-015** — Run the critical fault matrix in CI/nightly automation and preserve logs, traces, state snapshots, and invariant results as certification evidence.
### Security & trust

- [ ] **MC-032-CHK-016** — Complete a threat-model pass for **Fault-injection / partition test suite** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-032-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Fault-injection / partition test suite**; default to least privilege and explicitly test denied access.
- [ ] **MC-032-CHK-018** — Apply strict untrusted-input validation and resource limits to **Fault-injection / partition test suite** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-032-CHK-019** — Determine cryptographic/secret-management requirements for **Fault-injection / partition test suite**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-032-CHK-020** — Ensure sensitive data handled by **Fault-injection / partition test suite** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-032-CHK-021** — Create a failure-mode and recovery table for **Fault-injection / partition test suite** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-032-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Fault-injection / partition test suite** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-032-CHK-023** — Expose structured metrics/logs/traces/health for **Fault-injection / partition test suite** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-032-CHK-024** — Provide an operator runbook for **Fault-injection / partition test suite** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-032-CHK-025** — Implement unit tests for **Fault-injection / partition test suite** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-032-CHK-026** — Implement integration/contract tests for **Fault-injection / partition test suite** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-032-CHK-027** — Add fault/adversarial tests for **Fault-injection / partition test suite** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-032-CHK-028** — Benchmark or capacity-test **Fault-injection / partition test suite** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-032-CHK-029** — Link **Fault-injection / partition test suite** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-032-CHK-030** — Package production evidence for **Fault-injection / partition test suite** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-032 definition of done

- [ ] All **30 MC-032 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Fault-injection / partition test suite** satisfies its stated need: No crash, disconnect, split-brain, reconnect, stale-controller, or degraded-control-plane tests are present.
- [ ] Required controls **C051-C060, C089** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-032.

---

## MC-033 — Fuzz/property/adversarial tests

**Priority:** P1  
**Need:** Runtime unit tests exist, but there is no fuzzing of schemas/untrusted inputs or threat-derived adversarial suite.  
**Related controls:** C041, C050, C085, C087  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-033-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Fuzz/property/adversarial tests**; explicitly state what remains owned by adjacent services.
- [ ] **MC-033-CHK-002** — Assign an accountable owner and reviewer set for **Fuzz/property/adversarial tests** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-033-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Fuzz/property/adversarial tests**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-033-CHK-004** — Define the canonical data/state model for **Fuzz/property/adversarial tests**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-033-CHK-005** — Document safety/correctness invariants for **Fuzz/property/adversarial tests** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-033-CHK-006** — Fuzz all external schema parsers with malformed lengths/types/nesting, unknown fields, duplicate keys, Unicode edge cases, extreme numbers, and truncated payloads.
- [ ] **MC-033-CHK-007** — Define property tests for topology invariants: acyclic hierarchy, valid parents, deterministic cost/ranking, unknown-node refusal, and generation monotonicity.
- [ ] **MC-033-CHK-008** — Define property tests for fair-share invariants: non-negative usage, physical capacity never exceeded, release never creates negative usage, and equivalent operation orders preserve valid totals where semantics permit.
- [ ] **MC-033-CHK-009** — Generate adversarial candidate sets with duplicates, huge cardinality, pathological names/labels, hash-collision-like patterns, and boundary score values.
- [ ] **MC-033-CHK-010** — Fuzz transaction/idempotency state machines with randomized duplicate/reordered prepare/commit/abort/release sequences and crash/restart points.
- [ ] **MC-033-CHK-011** — Use differential tests comparing optimized/cached implementations against a simple reference model for small randomly generated topologies and ledgers.
- [ ] **MC-033-CHK-012** — Add concurrency/race stress that randomizes thread/process interleavings around claim/release, cache fill, config swap, and freeze transitions.
- [ ] **MC-033-CHK-013** — Maintain a minimized regression corpus for every discovered crash/invariant violation and run it on every release.
- [ ] **MC-033-CHK-014** — Capture reproducible seeds and environment metadata for failures; automatically minimize failing inputs where the framework supports it.
- [ ] **MC-033-CHK-015** — Enforce runtime/time/memory limits on fuzz targets and treat hangs, unbounded allocation, uncaught exceptions, invariant failures, and security-relevant parser discrepancies as defects.
### Security & trust

- [ ] **MC-033-CHK-016** — Complete a threat-model pass for **Fuzz/property/adversarial tests** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-033-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Fuzz/property/adversarial tests**; default to least privilege and explicitly test denied access.
- [ ] **MC-033-CHK-018** — Apply strict untrusted-input validation and resource limits to **Fuzz/property/adversarial tests** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-033-CHK-019** — Determine cryptographic/secret-management requirements for **Fuzz/property/adversarial tests**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-033-CHK-020** — Ensure sensitive data handled by **Fuzz/property/adversarial tests** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-033-CHK-021** — Create a failure-mode and recovery table for **Fuzz/property/adversarial tests** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-033-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Fuzz/property/adversarial tests** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-033-CHK-023** — Expose structured metrics/logs/traces/health for **Fuzz/property/adversarial tests** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-033-CHK-024** — Provide an operator runbook for **Fuzz/property/adversarial tests** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-033-CHK-025** — Implement unit tests for **Fuzz/property/adversarial tests** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-033-CHK-026** — Implement integration/contract tests for **Fuzz/property/adversarial tests** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-033-CHK-027** — Add fault/adversarial tests for **Fuzz/property/adversarial tests** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-033-CHK-028** — Benchmark or capacity-test **Fuzz/property/adversarial tests** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-033-CHK-029** — Link **Fuzz/property/adversarial tests** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-033-CHK-030** — Package production evidence for **Fuzz/property/adversarial tests** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-033 definition of done

- [ ] All **30 MC-033 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Fuzz/property/adversarial tests** satisfies its stated need: Runtime unit tests exist, but there is no fuzzing of schemas/untrusted inputs or threat-derived adversarial suite.
- [ ] Required controls **C041, C050, C085, C087** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-033.

---

## MC-034 — Adjacent-layer integration/contract test fixtures

**Priority:** P1  
**Need:** No real fixtures prove interoperability with GAP-02, GAP-14, PLN-05, and SCH-01.  
**Related controls:** C029-C030, C082-C083  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-034-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Adjacent-layer integration/contract test fixtures**; explicitly state what remains owned by adjacent services.
- [ ] **MC-034-CHK-002** — Assign an accountable owner and reviewer set for **Adjacent-layer integration/contract test fixtures** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-034-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Adjacent-layer integration/contract test fixtures**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-034-CHK-004** — Define the canonical data/state model for **Adjacent-layer integration/contract test fixtures**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-034-CHK-005** — Document safety/correctness invariants for **Adjacent-layer integration/contract test fixtures** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-034-CHK-006** — Define a versioned contract fixture set for GAP-02, GAP-14, PLN-05, and SCH-01 using exact external schemas rather than hand-written approximate dictionaries.
- [ ] **MC-034-CHK-007** — Include positive, boundary, malformed, unsupported-version, stale-revision, authorization-failure, and dependency-error fixtures for each adjacent service.
- [ ] **MC-034-CHK-008** — Provide schema-faithful mocks/fakes with deterministic latency/error injection for fast CI while retaining separate tests against real implementations or shared conformance services.
- [ ] **MC-034-CHK-009** — Capture canonical request/response pairs and expected normalized scheduler-domain objects; validate no field is silently dropped or reinterpreted.
- [ ] **MC-034-CHK-010** — Exercise version negotiation across minimum/current/next-compatible peer versions and verify incompatible majors fail before side effects.
- [ ] **MC-034-CHK-011** — Include end-to-end transaction IDs/trace context/idempotency keys in fixtures so cross-service correlation is validated.
- [ ] **MC-034-CHK-012** — Add network and retry scenarios to prove adapters preserve idempotency and error classification under timeouts/lost responses.
- [ ] **MC-034-CHK-013** — Validate provenance/freshness fields and negative cases where adjacent data is unsigned, stale, conflicting, or refers to unknown topology identities.
- [ ] **MC-034-CHK-014** — Run the fixture suite whenever this package or an adjacent contract changes and require explicit fixture/version updates for intentional breaks.
- [ ] **MC-034-CHK-015** — Publish a compatibility report artifact that records exact adjacent versions tested and links each contract fixture to its owning schema/repository.
### Security & trust

- [ ] **MC-034-CHK-016** — Complete a threat-model pass for **Adjacent-layer integration/contract test fixtures** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-034-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Adjacent-layer integration/contract test fixtures**; default to least privilege and explicitly test denied access.
- [ ] **MC-034-CHK-018** — Apply strict untrusted-input validation and resource limits to **Adjacent-layer integration/contract test fixtures** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-034-CHK-019** — Determine cryptographic/secret-management requirements for **Adjacent-layer integration/contract test fixtures**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-034-CHK-020** — Ensure sensitive data handled by **Adjacent-layer integration/contract test fixtures** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-034-CHK-021** — Create a failure-mode and recovery table for **Adjacent-layer integration/contract test fixtures** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-034-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Adjacent-layer integration/contract test fixtures** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-034-CHK-023** — Expose structured metrics/logs/traces/health for **Adjacent-layer integration/contract test fixtures** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-034-CHK-024** — Provide an operator runbook for **Adjacent-layer integration/contract test fixtures** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-034-CHK-025** — Implement unit tests for **Adjacent-layer integration/contract test fixtures** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-034-CHK-026** — Implement integration/contract tests for **Adjacent-layer integration/contract test fixtures** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-034-CHK-027** — Add fault/adversarial tests for **Adjacent-layer integration/contract test fixtures** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-034-CHK-028** — Benchmark or capacity-test **Adjacent-layer integration/contract test fixtures** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-034-CHK-029** — Link **Adjacent-layer integration/contract test fixtures** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-034-CHK-030** — Package production evidence for **Adjacent-layer integration/contract test fixtures** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-034 definition of done

- [ ] All **30 MC-034 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Adjacent-layer integration/contract test fixtures** satisfies its stated need: No real fixtures prove interoperability with GAP-02, GAP-14, PLN-05, and SCH-01.
- [ ] Required controls **C029-C030, C082-C083** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-034.

---

## MC-035 — Compatibility matrix and multi-platform CI

**Priority:** P1  
**Need:** No matrix validates supported Python/runtime/CPU/provider/protocol combinations.  
**Related controls:** C016, C027, C084, C093  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-035-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Compatibility matrix and multi-platform CI**; explicitly state what remains owned by adjacent services.
- [ ] **MC-035-CHK-002** — Assign an accountable owner and reviewer set for **Compatibility matrix and multi-platform CI** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-035-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Compatibility matrix and multi-platform CI**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-035-CHK-004** — Define the canonical data/state model for **Compatibility matrix and multi-platform CI**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-035-CHK-005** — Document safety/correctness invariants for **Compatibility matrix and multi-platform CI** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-035-CHK-006** — Define the supported runtime matrix: Python versions/implementations, OS families, CPU architectures, container/base images, and any provider-specific deployment targets.
- [ ] **MC-035-CHK-007** — Define the supported protocol/schema and adjacent-service version matrix, including minimum/maximum compatible versions and deprecation dates.
- [ ] **MC-035-CHK-008** — Run unit and contract suites across all required Python/runtime/OS combinations with optimized mode where relevant.
- [ ] **MC-035-CHK-009** — Run architecture-sensitive tests on every supported CPU architecture, including integer/endianness/atomicity assumptions and optional accelerator/native dependencies.
- [ ] **MC-035-CHK-010** — Pin or bound dependency versions and test both minimum-supported and current dependency sets to detect hidden reliance on newest behavior.
- [ ] **MC-035-CHK-011** — Exercise network/TLS stacks and storage/coordination client versions actually used in deployment environments.
- [ ] **MC-035-CHK-012** — Define explicit `unsupported` combinations and fail startup or packaging with a clear error instead of silently running unverified configurations.
- [ ] **MC-035-CHK-013** — Produce immutable CI artifacts: test reports, coverage, benchmark summary, environment manifest, dependency lock/SBOM, and package checksum for each release candidate.
- [ ] **MC-035-CHK-014** — Require all mandatory matrix cells to pass or carry an approved, time-bounded waiver before release promotion.
- [ ] **MC-035-CHK-015** — Review the matrix on a scheduled cadence and whenever an OS/runtime/provider reaches end of support; remove obsolete combinations through a documented migration/EOL process.
### Security & trust

- [ ] **MC-035-CHK-016** — Complete a threat-model pass for **Compatibility matrix and multi-platform CI** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-035-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Compatibility matrix and multi-platform CI**; default to least privilege and explicitly test denied access.
- [ ] **MC-035-CHK-018** — Apply strict untrusted-input validation and resource limits to **Compatibility matrix and multi-platform CI** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-035-CHK-019** — Determine cryptographic/secret-management requirements for **Compatibility matrix and multi-platform CI**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-035-CHK-020** — Ensure sensitive data handled by **Compatibility matrix and multi-platform CI** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-035-CHK-021** — Create a failure-mode and recovery table for **Compatibility matrix and multi-platform CI** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-035-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Compatibility matrix and multi-platform CI** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-035-CHK-023** — Expose structured metrics/logs/traces/health for **Compatibility matrix and multi-platform CI** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-035-CHK-024** — Provide an operator runbook for **Compatibility matrix and multi-platform CI** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-035-CHK-025** — Implement unit tests for **Compatibility matrix and multi-platform CI** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-035-CHK-026** — Implement integration/contract tests for **Compatibility matrix and multi-platform CI** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-035-CHK-027** — Add fault/adversarial tests for **Compatibility matrix and multi-platform CI** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-035-CHK-028** — Benchmark or capacity-test **Compatibility matrix and multi-platform CI** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-035-CHK-029** — Link **Compatibility matrix and multi-platform CI** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-035-CHK-030** — Package production evidence for **Compatibility matrix and multi-platform CI** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-035 definition of done

- [ ] All **30 MC-035 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Compatibility matrix and multi-platform CI** satisfies its stated need: No matrix validates supported Python/runtime/CPU/provider/protocol combinations.
- [ ] Required controls **C016, C027, C084, C093** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-035.

---

# P2 — Governance, release, and lifecycle components

All P2 controls inherit the global completion rules above.

---

## MC-036 — Accountable owner and escalation metadata

**Priority:** P2  
**Need:** The contract defines responsibility but no named accountable service owner/on-call escalation path.  
**Related controls:** C009, C097  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-036-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Accountable owner and escalation metadata**; explicitly state what remains owned by adjacent services.
- [ ] **MC-036-CHK-002** — Assign an accountable owner and reviewer set for **Accountable owner and escalation metadata** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-036-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Accountable owner and escalation metadata**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-036-CHK-004** — Define the canonical data/state model for **Accountable owner and escalation metadata**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-036-CHK-005** — Document safety/correctness invariants for **Accountable owner and escalation metadata** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-036-CHK-006** — Assign a single accountable service owner for GAP-03 and publish the owning organization/team in repository metadata and service catalog.
- [ ] **MC-036-CHK-007** — Define primary/secondary on-call rotations with 24x7 coverage expectations appropriate to the production SLO and dependency criticality.
- [ ] **MC-036-CHK-008** — Publish severity-based escalation paths with contact methods, maximum acknowledgement times, and management/security escalation where required.
- [ ] **MC-036-CHK-009** — Create a RACI for architecture, code ownership, security, operations, schema contracts, state stores, adjacent integrations, and release approval.
- [ ] **MC-036-CHK-010** — Configure repository `CODEOWNERS` or equivalent review enforcement for critical runtime, schema, security, deployment, and policy files.
- [ ] **MC-036-CHK-011** — Define ownership transfer/offboarding procedure so departures/reorganizations cannot orphan the service or its signing/secrets responsibilities.
- [ ] **MC-036-CHK-012** — Maintain a service catalog entry with production endpoints/environments, dependencies, dashboards, runbooks, repositories, and data classifications.
- [ ] **MC-036-CHK-013** — Require owners to review high-risk changes, waivers, incident action items, and EOL decisions through auditable change records.
- [ ] **MC-036-CHK-014** — Test escalation paths periodically using game days/paging drills and correct stale contacts or unowned dependencies.
- [ ] **MC-036-CHK-015** — Add an automated ownership metadata check to release/CI so missing owner/on-call/runbook references block production certification.
### Security & trust

- [ ] **MC-036-CHK-016** — Complete a threat-model pass for **Accountable owner and escalation metadata** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-036-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Accountable owner and escalation metadata**; default to least privilege and explicitly test denied access.
- [ ] **MC-036-CHK-018** — Apply strict untrusted-input validation and resource limits to **Accountable owner and escalation metadata** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-036-CHK-019** — Determine cryptographic/secret-management requirements for **Accountable owner and escalation metadata**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-036-CHK-020** — Ensure sensitive data handled by **Accountable owner and escalation metadata** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-036-CHK-021** — Create a failure-mode and recovery table for **Accountable owner and escalation metadata** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-036-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Accountable owner and escalation metadata** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-036-CHK-023** — Expose structured metrics/logs/traces/health for **Accountable owner and escalation metadata** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-036-CHK-024** — Provide an operator runbook for **Accountable owner and escalation metadata** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-036-CHK-025** — Implement unit tests for **Accountable owner and escalation metadata** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-036-CHK-026** — Implement integration/contract tests for **Accountable owner and escalation metadata** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-036-CHK-027** — Add fault/adversarial tests for **Accountable owner and escalation metadata** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-036-CHK-028** — Benchmark or capacity-test **Accountable owner and escalation metadata** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-036-CHK-029** — Link **Accountable owner and escalation metadata** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-036-CHK-030** — Package production evidence for **Accountable owner and escalation metadata** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-036 definition of done

- [ ] All **30 MC-036 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Accountable owner and escalation metadata** satisfies its stated need: The contract defines responsibility but no named accountable service owner/on-call escalation path.
- [ ] Required controls **C009, C097** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-036.

---

## MC-037 — Approved architecture decision record

**Priority:** P2  
**Need:** No ADR records why this implementation/algorithm was selected and approved.  
**Related controls:** C010, C098  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-037-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Approved architecture decision record**; explicitly state what remains owned by adjacent services.
- [ ] **MC-037-CHK-002** — Assign an accountable owner and reviewer set for **Approved architecture decision record** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-037-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Approved architecture decision record**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-037-CHK-004** — Define the canonical data/state model for **Approved architecture decision record**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-037-CHK-005** — Document safety/correctness invariants for **Approved architecture decision record** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-037-CHK-006** — Create a numbered, immutable ADR describing the topology-aware scheduler’s problem statement, scope, non-goals, and operational context.
- [ ] **MC-037-CHK-007** — Document the selected locality/fairness algorithms, topology model, distributed coordination/commit model, state-store choices, and security trust boundaries.
- [ ] **MC-037-CHK-008** — Record alternatives considered and why they were rejected, including simpler centralized, stateless, or alternative consistency models.
- [ ] **MC-037-CHK-009** — List architecture invariants and assumptions such as deterministic ordering, authoritative state sources, fencing requirements, clock assumptions, and maximum topology/candidate scale.
- [ ] **MC-037-CHK-010** — Document key tradeoffs in consistency, availability, latency, fairness, operability, and failure blast radius.
- [ ] **MC-037-CHK-011** — Include architecture/data-flow diagrams showing request, state, identity, topology, adjacent services, telemetry, and commit paths.
- [ ] **MC-037-CHK-012** — Link the ADR to relevant requirements, threat model, benchmarks, fault tests, schemas, and control checklist items.
- [ ] **MC-037-CHK-013** — Require approval from accountable engineering, operations/SRE, and security architecture roles for production-impacting decisions.
- [ ] **MC-037-CHK-014** — Define supersession rules: architecture changes create a new ADR referencing the old one rather than silently rewriting historical rationale.
- [ ] **MC-037-CHK-015** — Review ADR assumptions before major releases or after incidents and open tracked work when real-world evidence invalidates an assumption.
### Security & trust

- [ ] **MC-037-CHK-016** — Complete a threat-model pass for **Approved architecture decision record** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-037-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Approved architecture decision record**; default to least privilege and explicitly test denied access.
- [ ] **MC-037-CHK-018** — Apply strict untrusted-input validation and resource limits to **Approved architecture decision record** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-037-CHK-019** — Determine cryptographic/secret-management requirements for **Approved architecture decision record**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-037-CHK-020** — Ensure sensitive data handled by **Approved architecture decision record** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-037-CHK-021** — Create a failure-mode and recovery table for **Approved architecture decision record** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-037-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Approved architecture decision record** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-037-CHK-023** — Expose structured metrics/logs/traces/health for **Approved architecture decision record** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-037-CHK-024** — Provide an operator runbook for **Approved architecture decision record** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-037-CHK-025** — Implement unit tests for **Approved architecture decision record** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-037-CHK-026** — Implement integration/contract tests for **Approved architecture decision record** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-037-CHK-027** — Add fault/adversarial tests for **Approved architecture decision record** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-037-CHK-028** — Benchmark or capacity-test **Approved architecture decision record** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-037-CHK-029** — Link **Approved architecture decision record** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-037-CHK-030** — Package production evidence for **Approved architecture decision record** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-037 definition of done

- [ ] All **30 MC-037 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Approved architecture decision record** satisfies its stated need: No ADR records why this implementation/algorithm was selected and approved.
- [ ] Required controls **C010, C098** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-037.

---

## MC-038 — Full requirements traceability matrix

**Priority:** P2  
**Need:** `CHECKLIST.json` lists controls, but there is no requirement-to-code-to-test-to-evidence matrix.  
**Related controls:** C020, C090, C100  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-038-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Full requirements traceability matrix**; explicitly state what remains owned by adjacent services.
- [ ] **MC-038-CHK-002** — Assign an accountable owner and reviewer set for **Full requirements traceability matrix** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-038-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Full requirements traceability matrix**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-038-CHK-004** — Define the canonical data/state model for **Full requirements traceability matrix**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-038-CHK-005** — Document safety/correctness invariants for **Full requirements traceability matrix** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-038-CHK-006** — Assign stable requirement IDs to every functional, security, resilience, performance, operational, compatibility, and governance requirement applicable to GAP-03.
- [ ] **MC-038-CHK-007** — For each requirement record source, rationale, priority, owner, acceptance criteria, and applicable versions/environments.
- [ ] **MC-038-CHK-008** — Map every requirement to implementing code/module/function or external dependency and record explicit `not applicable` rationale where no code is expected.
- [ ] **MC-038-CHK-009** — Map every requirement to one or more automated/manual tests with exact test IDs and expected evidence artifacts.
- [ ] **MC-038-CHK-010** — Map every requirement to release evidence such as report, benchmark, scan, ADR, runbook, audit record, or approval.
- [ ] **MC-038-CHK-011** — Maintain bidirectional traceability so code/tests can identify the requirements they satisfy and orphan code/tests/requirements are detectable.
- [ ] **MC-038-CHK-012** — Generate coverage summaries that distinguish implemented, tested, evidenced, waived, blocked, and not-applicable states.
- [ ] **MC-038-CHK-013** — Validate RTM references automatically in CI so deleted/renamed tests, files, or controls create a blocking traceability failure.
- [ ] **MC-038-CHK-014** — Version the RTM with the release and preserve historical snapshots for incident/regression analysis.
- [ ] **MC-038-CHK-015** — Require zero unexplained P0/P1 requirement gaps at production exit gate and link any accepted gap to the formal waiver registry with owner/expiry.
### Security & trust

- [ ] **MC-038-CHK-016** — Complete a threat-model pass for **Full requirements traceability matrix** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-038-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Full requirements traceability matrix**; default to least privilege and explicitly test denied access.
- [ ] **MC-038-CHK-018** — Apply strict untrusted-input validation and resource limits to **Full requirements traceability matrix** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-038-CHK-019** — Determine cryptographic/secret-management requirements for **Full requirements traceability matrix**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-038-CHK-020** — Ensure sensitive data handled by **Full requirements traceability matrix** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-038-CHK-021** — Create a failure-mode and recovery table for **Full requirements traceability matrix** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-038-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Full requirements traceability matrix** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-038-CHK-023** — Expose structured metrics/logs/traces/health for **Full requirements traceability matrix** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-038-CHK-024** — Provide an operator runbook for **Full requirements traceability matrix** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-038-CHK-025** — Implement unit tests for **Full requirements traceability matrix** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-038-CHK-026** — Implement integration/contract tests for **Full requirements traceability matrix** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-038-CHK-027** — Add fault/adversarial tests for **Full requirements traceability matrix** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-038-CHK-028** — Benchmark or capacity-test **Full requirements traceability matrix** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-038-CHK-029** — Link **Full requirements traceability matrix** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-038-CHK-030** — Package production evidence for **Full requirements traceability matrix** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-038 definition of done

- [ ] All **30 MC-038 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Full requirements traceability matrix** satisfies its stated need: `CHECKLIST.json` lists controls, but there is no requirement-to-code-to-test-to-evidence matrix.
- [ ] Required controls **C020, C090, C100** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-038.

---

## MC-039 — Original `MASTER.md` source bundle

**Priority:** P2  
**Need:** README lineage referenced 100 master prompt/workflow documents, but the file is absent from the archive.  
**Related controls:** Provenance/evidence gap; supports C020/C090  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-039-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Original `MASTER.md` source bundle**; explicitly state what remains owned by adjacent services.
- [ ] **MC-039-CHK-002** — Assign an accountable owner and reviewer set for **Original `MASTER.md` source bundle** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-039-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Original `MASTER.md` source bundle**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-039-CHK-004** — Define the canonical data/state model for **Original `MASTER.md` source bundle**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-039-CHK-005** — Document safety/correctness invariants for **Original `MASTER.md` source bundle** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-039-CHK-006** — Locate the authoritative original `MASTER.md` and establish legal/organizational authority to redistribute or bundle it with this package.
- [ ] **MC-039-CHK-007** — Capture immutable provenance: source repository/path, commit or source version, acquisition timestamp, author/owner metadata, and cryptographic digest.
- [ ] **MC-039-CHK-008** — Verify the source document against any historical references/manifests to ensure the recovered file is the intended 100-workflow master source rather than a similarly named derivative.
- [ ] **MC-039-CHK-009** — Determine licensing/confidentiality classification and add the appropriate license/notice or distribution restriction metadata.
- [ ] **MC-039-CHK-010** — Place the canonical source at a stable package path and update README/manifest references so lineage claims are accurate and machine-verifiable.
- [ ] **MC-039-CHK-011** — Add a checksum/signature entry for the bundled source and fail release verification if it changes without an intentional provenance/version update.
- [ ] **MC-039-CHK-012** — Parse the document in CI to validate expected section/workflow count, identifiers, and internal references; report missing/duplicate IDs.
- [ ] **MC-039-CHK-013** — Link relevant source requirements/workflows into the requirements traceability matrix rather than treating the file as unstructured archival material.
- [ ] **MC-039-CHK-014** — Preserve historical versions in an immutable archive and document how a new source revision is reviewed and incorporated.
- [ ] **MC-039-CHK-015** — Add a reproducibility check showing that generated downstream checklist/evidence artifacts can identify the exact `MASTER.md` revision from which they derive.
### Security & trust

- [ ] **MC-039-CHK-016** — Complete a threat-model pass for **Original `MASTER.md` source bundle** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-039-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Original `MASTER.md` source bundle**; default to least privilege and explicitly test denied access.
- [ ] **MC-039-CHK-018** — Apply strict untrusted-input validation and resource limits to **Original `MASTER.md` source bundle** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-039-CHK-019** — Determine cryptographic/secret-management requirements for **Original `MASTER.md` source bundle**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-039-CHK-020** — Ensure sensitive data handled by **Original `MASTER.md` source bundle** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-039-CHK-021** — Create a failure-mode and recovery table for **Original `MASTER.md` source bundle** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-039-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Original `MASTER.md` source bundle** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-039-CHK-023** — Expose structured metrics/logs/traces/health for **Original `MASTER.md` source bundle** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-039-CHK-024** — Provide an operator runbook for **Original `MASTER.md` source bundle** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-039-CHK-025** — Implement unit tests for **Original `MASTER.md` source bundle** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-039-CHK-026** — Implement integration/contract tests for **Original `MASTER.md` source bundle** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-039-CHK-027** — Add fault/adversarial tests for **Original `MASTER.md` source bundle** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-039-CHK-028** — Benchmark or capacity-test **Original `MASTER.md` source bundle** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-039-CHK-029** — Link **Original `MASTER.md` source bundle** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-039-CHK-030** — Package production evidence for **Original `MASTER.md` source bundle** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-039 definition of done

- [ ] All **30 MC-039 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Original `MASTER.md` source bundle** satisfies its stated need: README lineage referenced 100 master prompt/workflow documents, but the file is absent from the archive.
- [ ] Required controls **Provenance/evidence gap; supports C020/C090** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-039.

---

## MC-040 — Supply-chain manifest/signing/SBOM pipeline

**Priority:** P2  
**Need:** A local checksum manifest can detect accidental changes, but there is no signed release, SBOM, provenance attestation, or dependency-vulnerability workflow.  
**Related controls:** C045, C094  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-040-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Supply-chain manifest/signing/SBOM pipeline**; explicitly state what remains owned by adjacent services.
- [ ] **MC-040-CHK-002** — Assign an accountable owner and reviewer set for **Supply-chain manifest/signing/SBOM pipeline** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-040-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Supply-chain manifest/signing/SBOM pipeline**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-040-CHK-004** — Define the canonical data/state model for **Supply-chain manifest/signing/SBOM pipeline**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-040-CHK-005** — Document safety/correctness invariants for **Supply-chain manifest/signing/SBOM pipeline** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-040-CHK-006** — Generate an SBOM for every release in SPDX or CycloneDX (or equivalent approved format) covering first-party files, Python packages, native/runtime components, container/base image, and build tooling as applicable.
- [ ] **MC-040-CHK-007** — Produce a signed release manifest with cryptographic digests for package files and bind the manifest to version, source commit, build job, and build environment identity.
- [ ] **MC-040-CHK-008** — Generate provenance attestation at a defined SLSA/equivalent level describing source, builder, build steps, dependencies, and artifact digests.
- [ ] **MC-040-CHK-009** — Sign release artifacts using an organization-controlled signing service/key or keyless transparency-backed mechanism; define verification steps for deployers.
- [ ] **MC-040-CHK-010** — Pin dependencies with hashes/lockfiles where applicable and prohibit unreviewed floating versions in production builds.
- [ ] **MC-040-CHK-011** — Run vulnerability scanning against dependencies, base images, and bundled binaries with severity policy, suppression/waiver workflow, and fresh advisory data.
- [ ] **MC-040-CHK-012** — Run license/compliance checks and block disallowed or unknown licenses from release unless formally approved.
- [ ] **MC-040-CHK-013** — Harden CI/build permissions, protect release branches/tags, isolate signing credentials, and prevent untrusted pull-request code from accessing release secrets.
- [ ] **MC-040-CHK-014** — Test reproducible or at minimum repeatable builds and investigate unexpected digest differences in deterministic artifacts.
- [ ] **MC-040-CHK-015** — Publish SBOM, provenance, signatures, verification instructions, vulnerability summary, and retained build logs as part of the production evidence bundle.
### Security & trust

- [ ] **MC-040-CHK-016** — Complete a threat-model pass for **Supply-chain manifest/signing/SBOM pipeline** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-040-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Supply-chain manifest/signing/SBOM pipeline**; default to least privilege and explicitly test denied access.
- [ ] **MC-040-CHK-018** — Apply strict untrusted-input validation and resource limits to **Supply-chain manifest/signing/SBOM pipeline** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-040-CHK-019** — Determine cryptographic/secret-management requirements for **Supply-chain manifest/signing/SBOM pipeline**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-040-CHK-020** — Ensure sensitive data handled by **Supply-chain manifest/signing/SBOM pipeline** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-040-CHK-021** — Create a failure-mode and recovery table for **Supply-chain manifest/signing/SBOM pipeline** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-040-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Supply-chain manifest/signing/SBOM pipeline** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-040-CHK-023** — Expose structured metrics/logs/traces/health for **Supply-chain manifest/signing/SBOM pipeline** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-040-CHK-024** — Provide an operator runbook for **Supply-chain manifest/signing/SBOM pipeline** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-040-CHK-025** — Implement unit tests for **Supply-chain manifest/signing/SBOM pipeline** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-040-CHK-026** — Implement integration/contract tests for **Supply-chain manifest/signing/SBOM pipeline** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-040-CHK-027** — Add fault/adversarial tests for **Supply-chain manifest/signing/SBOM pipeline** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-040-CHK-028** — Benchmark or capacity-test **Supply-chain manifest/signing/SBOM pipeline** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-040-CHK-029** — Link **Supply-chain manifest/signing/SBOM pipeline** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-040-CHK-030** — Package production evidence for **Supply-chain manifest/signing/SBOM pipeline** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-040 definition of done

- [ ] All **30 MC-040 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Supply-chain manifest/signing/SBOM pipeline** satisfies its stated need: A local checksum manifest can detect accidental changes, but there is no signed release, SBOM, provenance attestation, or dependency-vulnerability workflow.
- [ ] Required controls **C045, C094** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-040.

---

## MC-041 — Canary/staged deployment controller

**Priority:** P2  
**Need:** No rollout orchestration, automated rollback controller, or promotion criteria exist in this package.  
**Related controls:** C038, C092  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-041-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Canary/staged deployment controller**; explicitly state what remains owned by adjacent services.
- [ ] **MC-041-CHK-002** — Assign an accountable owner and reviewer set for **Canary/staged deployment controller** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-041-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Canary/staged deployment controller**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-041-CHK-004** — Define the canonical data/state model for **Canary/staged deployment controller**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-041-CHK-005** — Document safety/correctness invariants for **Canary/staged deployment controller** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-041-CHK-006** — Define rollout stages such as dev → integration → shadow → canary → partial production → full production, with explicit population/traffic percentages or environment criteria.
- [ ] **MC-041-CHK-007** — Define pre-promotion gates for functional tests, security scans, state migration readiness, benchmark thresholds, error budget, and open P0/P1 defects.
- [ ] **MC-041-CHK-008** — Choose canary cohorts that represent topology/tenant/workload diversity while bounding blast radius; exclude only with documented rationale.
- [ ] **MC-041-CHK-009** — Continuously compare canary vs control on errors, latency, fairness denials, capacity utilization, stale conflicts, reconciliation drift, and resource consumption.
- [ ] **MC-041-CHK-010** — Automate rollback when defined health/SLO/invariant thresholds breach for a sustained decision window; do not depend solely on manual observation.
- [ ] **MC-041-CHK-011** — Coordinate code, schema, config, and state migrations so rollback remains possible and old/new versions can coexist for the planned overlap window.
- [ ] **MC-041-CHK-012** — Drain or fence instances cleanly during promotion/rollback so in-flight placement transactions are not duplicated or orphaned.
- [ ] **MC-041-CHK-013** — Record rollout generation, artifact digest, config generation, approver, cohort, start/end time, metrics snapshot, and rollback/promote decisions in audit evidence.
- [ ] **MC-041-CHK-014** — Provide operator pause/resume/abort controls with authorization and documented recovery if automation itself fails.
- [ ] **MC-041-CHK-015** — Exercise rollback and forward-fix in staging/game days, including after partial state migration and during leader failover, before production approval.
### Security & trust

- [ ] **MC-041-CHK-016** — Complete a threat-model pass for **Canary/staged deployment controller** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-041-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Canary/staged deployment controller**; default to least privilege and explicitly test denied access.
- [ ] **MC-041-CHK-018** — Apply strict untrusted-input validation and resource limits to **Canary/staged deployment controller** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-041-CHK-019** — Determine cryptographic/secret-management requirements for **Canary/staged deployment controller**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-041-CHK-020** — Ensure sensitive data handled by **Canary/staged deployment controller** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-041-CHK-021** — Create a failure-mode and recovery table for **Canary/staged deployment controller** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-041-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Canary/staged deployment controller** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-041-CHK-023** — Expose structured metrics/logs/traces/health for **Canary/staged deployment controller** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-041-CHK-024** — Provide an operator runbook for **Canary/staged deployment controller** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-041-CHK-025** — Implement unit tests for **Canary/staged deployment controller** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-041-CHK-026** — Implement integration/contract tests for **Canary/staged deployment controller** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-041-CHK-027** — Add fault/adversarial tests for **Canary/staged deployment controller** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-041-CHK-028** — Benchmark or capacity-test **Canary/staged deployment controller** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-041-CHK-029** — Link **Canary/staged deployment controller** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-041-CHK-030** — Package production evidence for **Canary/staged deployment controller** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-041 definition of done

- [ ] All **30 MC-041 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Canary/staged deployment controller** satisfies its stated need: No rollout orchestration, automated rollback controller, or promotion criteria exist in this package.
- [ ] Required controls **C038, C092** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-041.

---

## MC-042 — Backup/restore/migration tooling

**Priority:** P2  
**Need:** No commands or tested procedure reconstruct durable scheduler state because durable state itself is absent.  
**Related controls:** C057, C095  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-042-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Backup/restore/migration tooling**; explicitly state what remains owned by adjacent services.
- [ ] **MC-042-CHK-002** — Assign an accountable owner and reviewer set for **Backup/restore/migration tooling** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-042-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Backup/restore/migration tooling**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-042-CHK-004** — Define the canonical data/state model for **Backup/restore/migration tooling**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-042-CHK-005** — Document safety/correctness invariants for **Backup/restore/migration tooling** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-042-CHK-006** — Define recovery point objective (RPO) and recovery time objective (RTO) separately for topology, fair-share ledger, placement transaction journal, configuration, audit references, and other durable state.
- [ ] **MC-042-CHK-007** — Inventory exactly which state is authoritative, reconstructable, ephemeral, or externally sourced so backup scope is neither incomplete nor unnecessarily broad.
- [ ] **MC-042-CHK-008** — Implement encrypted backups/snapshots with authenticated integrity metadata, version/schema identifiers, creation time, source cluster, and retention class.
- [ ] **MC-042-CHK-009** — Support appropriate full/incremental/snapshot/PITR mechanisms and verify they are consistent across interdependent stores or can be reconciled deterministically after restore.
- [ ] **MC-042-CHK-010** — Protect backup credentials and storage with least privilege, immutability/object-lock where warranted, geographic/domain separation, and monitored access.
- [ ] **MC-042-CHK-011** — Provide versioned restore tooling that validates checksum/signature/schema before activation and supports dry-run inspection.
- [ ] **MC-042-CHK-012** — Define migration/restore ordering for coordination, topology, entitlements cache, ledger, transactions, and downstream reconciliation to avoid resurrecting stale ownership.
- [ ] **MC-042-CHK-013** — Automate periodic restore rehearsals into an isolated environment and verify topology/fairness/transaction invariants plus application readiness.
- [ ] **MC-042-CHK-014** — Measure achieved RPO/RTO and alert when backup age, failed jobs, restore failures, or integrity checks violate targets.
- [ ] **MC-042-CHK-015** — Publish a disaster-recovery runbook with decision authority, rollback point selection, data-loss assessment, post-restore reconciliation, and evidence collection.
### Security & trust

- [ ] **MC-042-CHK-016** — Complete a threat-model pass for **Backup/restore/migration tooling** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-042-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Backup/restore/migration tooling**; default to least privilege and explicitly test denied access.
- [ ] **MC-042-CHK-018** — Apply strict untrusted-input validation and resource limits to **Backup/restore/migration tooling** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-042-CHK-019** — Determine cryptographic/secret-management requirements for **Backup/restore/migration tooling**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-042-CHK-020** — Ensure sensitive data handled by **Backup/restore/migration tooling** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-042-CHK-021** — Create a failure-mode and recovery table for **Backup/restore/migration tooling** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-042-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Backup/restore/migration tooling** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-042-CHK-023** — Expose structured metrics/logs/traces/health for **Backup/restore/migration tooling** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-042-CHK-024** — Provide an operator runbook for **Backup/restore/migration tooling** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-042-CHK-025** — Implement unit tests for **Backup/restore/migration tooling** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-042-CHK-026** — Implement integration/contract tests for **Backup/restore/migration tooling** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-042-CHK-027** — Add fault/adversarial tests for **Backup/restore/migration tooling** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-042-CHK-028** — Benchmark or capacity-test **Backup/restore/migration tooling** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-042-CHK-029** — Link **Backup/restore/migration tooling** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-042-CHK-030** — Package production evidence for **Backup/restore/migration tooling** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-042 definition of done

- [ ] All **30 MC-042 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Backup/restore/migration tooling** satisfies its stated need: No commands or tested procedure reconstruct durable scheduler state because durable state itself is absent.
- [ ] Required controls **C057, C095** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-042.

---

## MC-043 — Incident response runbook

**Priority:** P2  
**Need:** No severity, paging, containment, forensic, or recovery runbook is bundled.  
**Related controls:** C096-C097  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-043-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Incident response runbook**; explicitly state what remains owned by adjacent services.
- [ ] **MC-043-CHK-002** — Assign an accountable owner and reviewer set for **Incident response runbook** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-043-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Incident response runbook**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-043-CHK-004** — Define the canonical data/state model for **Incident response runbook**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-043-CHK-005** — Document safety/correctness invariants for **Incident response runbook** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-043-CHK-006** — Define incident severity levels with scheduler-specific examples, user/business impact criteria, security escalation triggers, and required response times.
- [ ] **MC-043-CHK-007** — Document detection sources and first-response triage for overload, state corruption/drift, split-brain/fencing, topology errors, fairness anomalies, dependency outage, and suspected compromise.
- [ ] **MC-043-CHK-008** — Assign incident commander, operations lead, communications role, security role, and scribe responsibilities with escalation contacts.
- [ ] **MC-043-CHK-009** — Provide immediate containment actions including freeze/quarantine, admission reduction, replica fencing, dependency isolation, rollback, and credential revocation as appropriate.
- [ ] **MC-043-CHK-010** — List authoritative dashboards, queries, explain endpoints, transaction journals, audit logs, and state snapshots required for diagnosis.
- [ ] **MC-043-CHK-011** — Define forensic evidence preservation so responders do not destroy logs/state needed to reconstruct privileged mutations or duplicate placements.
- [ ] **MC-043-CHK-012** — Provide recovery validation steps that check topology, ledger, pending/orphan transactions, coordination ownership, dependency freshness, and downstream placement reconciliation before normal admission resumes.
- [ ] **MC-043-CHK-013** — Include stakeholder/customer/internal communication templates and update cadence proportional to severity without leaking sensitive infrastructure detail.
- [ ] **MC-043-CHK-014** — Require a post-incident review with timeline, contributing factors, violated assumptions/invariants, corrective actions, owners, due dates, and linkage to ADR/RTM/waivers.
- [ ] **MC-043-CHK-015** — Exercise the runbook through scheduled tabletop/game-day scenarios and update it based on observed ambiguity, stale commands, missing permissions, or excessive recovery time.
### Security & trust

- [ ] **MC-043-CHK-016** — Complete a threat-model pass for **Incident response runbook** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-043-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Incident response runbook**; default to least privilege and explicitly test denied access.
- [ ] **MC-043-CHK-018** — Apply strict untrusted-input validation and resource limits to **Incident response runbook** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-043-CHK-019** — Determine cryptographic/secret-management requirements for **Incident response runbook**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-043-CHK-020** — Ensure sensitive data handled by **Incident response runbook** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-043-CHK-021** — Create a failure-mode and recovery table for **Incident response runbook** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-043-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Incident response runbook** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-043-CHK-023** — Expose structured metrics/logs/traces/health for **Incident response runbook** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-043-CHK-024** — Provide an operator runbook for **Incident response runbook** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-043-CHK-025** — Implement unit tests for **Incident response runbook** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-043-CHK-026** — Implement integration/contract tests for **Incident response runbook** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-043-CHK-027** — Add fault/adversarial tests for **Incident response runbook** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-043-CHK-028** — Benchmark or capacity-test **Incident response runbook** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-043-CHK-029** — Link **Incident response runbook** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-043-CHK-030** — Package production evidence for **Incident response runbook** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-043 definition of done

- [ ] All **30 MC-043 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Incident response runbook** satisfies its stated need: No severity, paging, containment, forensic, or recovery runbook is bundled.
- [ ] Required controls **C096-C097** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-043.

---

## MC-044 — Patch/vulnerability/EOL policy

**Priority:** P2  
**Need:** No support window, vulnerability response SLA, or end-of-life policy is present.  
**Related controls:** C094  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-044-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Patch/vulnerability/EOL policy**; explicitly state what remains owned by adjacent services.
- [ ] **MC-044-CHK-002** — Assign an accountable owner and reviewer set for **Patch/vulnerability/EOL policy** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-044-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Patch/vulnerability/EOL policy**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-044-CHK-004** — Define the canonical data/state model for **Patch/vulnerability/EOL policy**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-044-CHK-005** — Document safety/correctness invariants for **Patch/vulnerability/EOL policy** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-044-CHK-006** — Define supported release branches/versions, maintenance window, end-of-support date, and compatibility expectations for each supported major/minor release.
- [ ] **MC-044-CHK-007** — Establish vulnerability severity classification and patch SLAs, including emergency handling for actively exploited or critical scheduler/state/identity vulnerabilities.
- [ ] **MC-044-CHK-008** — Ingest advisories from dependency/runtime/OS/provider sources and continuously map affected versions against the SBOM.
- [ ] **MC-044-CHK-009** — Define patch qualification requirements: targeted regression tests, security verification, compatibility matrix, benchmark smoke tests, and rollback artifact.
- [ ] **MC-044-CHK-010** — Maintain a protected emergency-release path that is faster than normal rollout but still produces signed artifacts, audit trail, and minimum required evidence.
- [ ] **MC-044-CHK-011** — Define dependency/runtime upgrade cadence so the service does not remain indefinitely on unsupported Python/OS/client libraries.
- [ ] **MC-044-CHK-012** — Publish advance EOL notices and tested upgrade/migration paths for schema, config, clients, and durable state.
- [ ] **MC-044-CHK-013** — Prevent new deployments of EOL/known-vulnerable versions unless a formally approved, time-bounded exception exists.
- [ ] **MC-044-CHK-014** — Track patch adoption across environments and alert on instances running outside the support/vulnerability policy.
- [ ] **MC-044-CHK-015** — Review patch/EOL policy after significant incidents or ecosystem changes and preserve historical policy/version evidence for audits.
### Security & trust

- [ ] **MC-044-CHK-016** — Complete a threat-model pass for **Patch/vulnerability/EOL policy** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-044-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Patch/vulnerability/EOL policy**; default to least privilege and explicitly test denied access.
- [ ] **MC-044-CHK-018** — Apply strict untrusted-input validation and resource limits to **Patch/vulnerability/EOL policy** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-044-CHK-019** — Determine cryptographic/secret-management requirements for **Patch/vulnerability/EOL policy**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-044-CHK-020** — Ensure sensitive data handled by **Patch/vulnerability/EOL policy** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-044-CHK-021** — Create a failure-mode and recovery table for **Patch/vulnerability/EOL policy** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-044-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Patch/vulnerability/EOL policy** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-044-CHK-023** — Expose structured metrics/logs/traces/health for **Patch/vulnerability/EOL policy** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-044-CHK-024** — Provide an operator runbook for **Patch/vulnerability/EOL policy** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-044-CHK-025** — Implement unit tests for **Patch/vulnerability/EOL policy** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-044-CHK-026** — Implement integration/contract tests for **Patch/vulnerability/EOL policy** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-044-CHK-027** — Add fault/adversarial tests for **Patch/vulnerability/EOL policy** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-044-CHK-028** — Benchmark or capacity-test **Patch/vulnerability/EOL policy** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-044-CHK-029** — Link **Patch/vulnerability/EOL policy** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-044-CHK-030** — Package production evidence for **Patch/vulnerability/EOL policy** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-044 definition of done

- [ ] All **30 MC-044 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Patch/vulnerability/EOL policy** satisfies its stated need: No support window, vulnerability response SLA, or end-of-life policy is present.
- [ ] Required controls **C094** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-044.

---

## MC-045 — Exception/waiver/debt registry

**Priority:** P2  
**Need:** No owner/expiry-tracked register exists for accepted gaps or deprecated behaviors.  
**Related controls:** C099  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-045-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Exception/waiver/debt registry**; explicitly state what remains owned by adjacent services.
- [ ] **MC-045-CHK-002** — Assign an accountable owner and reviewer set for **Exception/waiver/debt registry** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-045-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Exception/waiver/debt registry**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-045-CHK-004** — Define the canonical data/state model for **Exception/waiver/debt registry**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-045-CHK-005** — Document safety/correctness invariants for **Exception/waiver/debt registry** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-045-CHK-006** — Create a uniquely identified waiver/debt record schema containing affected requirement/control, scope, environment, owner, approver, rationale, risk statement, and discovery date.
- [ ] **MC-045-CHK-007** — Require explicit compensating controls and residual-risk assessment rather than accepting a gap solely because implementation is deferred.
- [ ] **MC-045-CHK-008** — Assign an expiry/review date to every waiver; prohibit indefinite exceptions without recurring executive/security re-approval as policy requires.
- [ ] **MC-045-CHK-009** — Classify waivers by severity and prohibit waiver of non-waivable safety/security/legal controls through this mechanism.
- [ ] **MC-045-CHK-010** — Link each waiver to defects/work items, affected versions, RTM entries, evidence, incident history, and planned remediation milestone.
- [ ] **MC-045-CHK-011** — Integrate active waiver checks into CI/release gates so expired, unapproved, or out-of-scope waivers block promotion automatically.
- [ ] **MC-045-CHK-012** — Notify owners/approvers before expiry and escalate overdue remediation according to severity.
- [ ] **MC-045-CHK-013** — Require reassessment when scope/version/architecture changes because the original risk decision may no longer apply.
- [ ] **MC-045-CHK-014** — Produce a release summary of active waivers and aggregate technical debt by severity/owner/age without hiding waived controls as “passed.”
- [ ] **MC-045-CHK-015** — Audit waiver creation/edit/approval/closure and preserve closed records for historical decision traceability.
### Security & trust

- [ ] **MC-045-CHK-016** — Complete a threat-model pass for **Exception/waiver/debt registry** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-045-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Exception/waiver/debt registry**; default to least privilege and explicitly test denied access.
- [ ] **MC-045-CHK-018** — Apply strict untrusted-input validation and resource limits to **Exception/waiver/debt registry** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-045-CHK-019** — Determine cryptographic/secret-management requirements for **Exception/waiver/debt registry**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-045-CHK-020** — Ensure sensitive data handled by **Exception/waiver/debt registry** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-045-CHK-021** — Create a failure-mode and recovery table for **Exception/waiver/debt registry** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-045-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Exception/waiver/debt registry** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-045-CHK-023** — Expose structured metrics/logs/traces/health for **Exception/waiver/debt registry** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-045-CHK-024** — Provide an operator runbook for **Exception/waiver/debt registry** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-045-CHK-025** — Implement unit tests for **Exception/waiver/debt registry** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-045-CHK-026** — Implement integration/contract tests for **Exception/waiver/debt registry** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-045-CHK-027** — Add fault/adversarial tests for **Exception/waiver/debt registry** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-045-CHK-028** — Benchmark or capacity-test **Exception/waiver/debt registry** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-045-CHK-029** — Link **Exception/waiver/debt registry** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-045-CHK-030** — Package production evidence for **Exception/waiver/debt registry** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-045 definition of done

- [ ] All **30 MC-045 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Exception/waiver/debt registry** satisfies its stated need: No owner/expiry-tracked register exists for accepted gaps or deprecated behaviors.
- [ ] Required controls **C099** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-045.

---

## MC-046 — Formal production exit-gate evidence bundle

**Priority:** P2  
**Need:** `pk_core` can participate in a wider gate, but this isolated archive lacks the external evidence needed to certify all architecture/security/resilience/performance/operations controls.  
**Related controls:** C090, C100  

**Component completion gate:** No checkbox below may be marked complete without linked evidence. The component is production-complete only when all mandatory checks are satisfied or an approved, unexpired waiver is linked.

### Requirements & architecture

- [ ] **MC-046-CHK-001** — Define the normative scope, non-goals, trust/consistency boundaries, and production responsibility of **Formal production exit-gate evidence bundle**; explicitly state what remains owned by adjacent services.
- [ ] **MC-046-CHK-002** — Assign an accountable owner and reviewer set for **Formal production exit-gate evidence bundle** and link its service/repository/ADR/runbook locations to the requirements traceability matrix.
- [ ] **MC-046-CHK-003** — Enumerate all upstream/downstream interfaces and state dependencies required by **Formal production exit-gate evidence bundle**; record protocol/schema versions, ownership, authentication, timeout, retry, and failure semantics.
- [ ] **MC-046-CHK-004** — Define the canonical data/state model for **Formal production exit-gate evidence bundle**, including identity, version/revision, timestamp/freshness, lifecycle state, units, bounds, nullability, and provenance fields applicable to the component.
- [ ] **MC-046-CHK-005** — Document safety/correctness invariants for **Formal production exit-gate evidence bundle** and convert each invariant into at least one automated positive or negative test.
### Implementation & integration

- [ ] **MC-046-CHK-006** — Define a versioned production exit-gate manifest enumerating every required evidence class: architecture, requirements, tests, security, resilience, performance, operations, compatibility, provenance, and approvals.
- [ ] **MC-046-CHK-007** — Bind the evidence bundle to an immutable release candidate digest/version/source commit/config/schema set so evidence cannot be reused for a different artifact.
- [ ] **MC-046-CHK-008** — Include complete automated test reports, optimized-mode results, integration/contract results, coverage/invariant summaries, and any required manual validation records.
- [ ] **MC-046-CHK-009** — Include threat model/security review, vulnerability/SBOM/provenance/signature outputs, identity/authorization test evidence, and audit-log integrity results.
- [ ] **MC-046-CHK-010** — Include fault-injection, failover, backup/restore, degraded-mode, canary/rollback rehearsal, and incident-response exercise evidence required by policy.
- [ ] **MC-046-CHK-011** — Include controlled benchmark/load-test results against approved thresholds and the exact hardware/runtime environment metadata used.
- [ ] **MC-046-CHK-012** — Include compatibility matrix results for supported runtimes/platforms/protocols/adjacent systems and explicit unsupported combinations.
- [ ] **MC-046-CHK-013** — Include ownership/on-call/runbook/dashboard/alert readiness evidence plus state migration/rollback procedures.
- [ ] **MC-046-CHK-014** — List all unresolved defects and active waivers with severity, scope, owner, expiry, compensating controls, and approval; never represent waived controls as unqualified passes.
- [ ] **MC-046-CHK-015** — Require named technical, security, operations/SRE, and release authority sign-off; emit a final signed machine-readable gate result that can be verified by deployment automation before production promotion.
### Security & trust

- [ ] **MC-046-CHK-016** — Complete a threat-model pass for **Formal production exit-gate evidence bundle** covering spoofing, tampering, repudiation/audit gaps, information disclosure, denial of service/resource exhaustion, privilege escalation, replay, stale-state use, and cross-tenant abuse as applicable.
- [ ] **MC-046-CHK-017** — Define and enforce authentication/authorization boundaries for every privileged operation exposed by **Formal production exit-gate evidence bundle**; default to least privilege and explicitly test denied access.
- [ ] **MC-046-CHK-018** — Apply strict untrusted-input validation and resource limits to **Formal production exit-gate evidence bundle** at the earliest boundary; include canonicalization, length/depth/cardinality/numeric bounds, duplicate handling, and malformed/unknown-version rejection where relevant.
- [ ] **MC-046-CHK-019** — Determine cryptographic/secret-management requirements for **Formal production exit-gate evidence bundle**. If applicable, specify approved algorithms, key ownership/rotation/revocation/storage, replay resistance, and verification failure behavior; if not applicable, record a reviewed N/A rationale.
- [ ] **MC-046-CHK-020** — Ensure sensitive data handled by **Formal production exit-gate evidence bundle** is minimized, redacted in telemetry, encrypted in transit/at rest where required, access-controlled, and covered by retention/deletion policy.
### Resilience & operations

- [ ] **MC-046-CHK-021** — Create a failure-mode and recovery table for **Formal production exit-gate evidence bundle** covering dependency loss, timeout, duplicate/reordered delivery, crash/restart, stale state, partial commit, overload, and operator error as applicable; state fail-open/fail-closed behavior.
- [ ] **MC-046-CHK-022** — Define concurrency, idempotency, timeout, retry/backoff, cancellation, and stale-operation semantics for **Formal production exit-gate evidence bundle** so repeated or concurrent execution cannot violate scheduler invariants.
- [ ] **MC-046-CHK-023** — Expose structured metrics/logs/traces/health for **Formal production exit-gate evidence bundle** with stable event/error codes, bounded cardinality, correlation IDs, and enough generation/revision metadata to diagnose stale or conflicting state.
- [ ] **MC-046-CHK-024** — Provide an operator runbook for **Formal production exit-gate evidence bundle** covering rollout, validation, rollback/disable, degraded operation, recovery/reconciliation, and escalation; exercise critical procedures before production certification.
### Verification & certification

- [ ] **MC-046-CHK-025** — Implement unit tests for **Formal production exit-gate evidence bundle** covering nominal, boundary, invalid, duplicate, stale, and deterministic behavior with no undeclared environmental dependency.
- [ ] **MC-046-CHK-026** — Implement integration/contract tests for **Formal production exit-gate evidence bundle** against its real schemas/adapters/state interfaces, including supported-version negotiation and exact error/idempotency behavior.
- [ ] **MC-046-CHK-027** — Add fault/adversarial tests for **Formal production exit-gate evidence bundle** that inject malformed inputs, authorization failure, dependency faults, high latency, crash/restart, and concurrency races appropriate to its risk profile.
- [ ] **MC-046-CHK-028** — Benchmark or capacity-test **Formal production exit-gate evidence bundle** under representative and worst-supported scale; define blocking thresholds for latency, throughput, memory/state growth, queueing, or recovery time as applicable.
- [ ] **MC-046-CHK-029** — Link **Formal production exit-gate evidence bundle** requirements → implementation → tests → evidence in the RTM; unresolved gaps must reference the waiver/debt registry rather than being silently marked complete.
### Exit gate

- [ ] **MC-046-CHK-030** — Package production evidence for **Formal production exit-gate evidence bundle** with exact software/schema/config versions and cryptographic artifact digest; verify evidence is current and reproducible from a clean environment.

### MC-046 definition of done

- [ ] All **30 MC-046 checklist controls** are completed or explicitly covered by an approved, unexpired waiver.
- [ ] Evidence demonstrates that **Formal production exit-gate evidence bundle** satisfies its stated need: `pk_core` can participate in a wider gate, but this isolated archive lacks the external evidence needed to certify all architecture/security/resilience/performance/operations controls.
- [ ] Required controls **C090, C100** are traceable to implementation and test evidence.
- [ ] No open P0-equivalent correctness/security/resilience defect remains attributable to MC-046.

---

# Final program exit checklist

- [ ] All MC-001…MC-018 P0 components are implemented and independently verified before production control-plane deployment.
- [ ] All MC-019…MC-035 P1 components required by the organization’s operational/certification baseline are implemented or covered by formally approved, time-bounded exceptions.
- [ ] MC-036…MC-046 governance/release controls are active and tied to the exact release artifact.
- [ ] The RTM reports zero unexplained mandatory-control gaps and all waivers are in-scope, approved, and unexpired.
- [ ] Clean-environment CI can reproduce the runtime tests, contract tests, fault tests, benchmark gates, SBOM/provenance/signatures, and final evidence manifest.
- [ ] A staged/canary rollout has demonstrated stable health and rollback readiness before full promotion.

**Recommended implementation sequence:** MC-001 → MC-002 → MC-003 → MC-004/MC-005 → MC-006 → MC-007, then adjacent integrations MC-008…MC-012, operational safety MC-013…MC-018, certification/observability MC-019…MC-035, and governance/release closure MC-036…MC-046.