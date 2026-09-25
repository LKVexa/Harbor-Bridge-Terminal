# INV-58 v4.2.0 — Missing / Incomplete Components: Professional Implementation Checklist

**Repository:** Existing service-mesh layer  
**Audit baseline:** v4.2.0  
**Audit date:** 2026-09-22  
**Source of truth:** `INV58_v4.2.0_MISSING_COMPONENTS.json`  
**Coverage at audit:** 11 implemented / 25 partial / 64 missing requirements  
**Work packages:** 41 missing or incomplete components

This checklist is an execution specification for closing every gap identified by the v4.2.0 post-audit. Checkboxes should be closed only with verifiable implementation and evidence; documentation-only completion is insufficient for controls that require executable behavior or tests.

## Global completion rules
- [ ] Preserve the hardened 4.2.0 invariants: one retry owner per route, bounded total attempts, strict/fail-closed SPIFFE mapping, bounded bypass evidence, bounded route registry, and copy-on-write revisioned route migration.
- [ ] Use stable identifiers for new requirements, decisions, threats, error codes, metrics, audit events, tests, waivers, and release evidence so cross-artifact traceability is machine-checkable.
- [ ] For any security-critical ambiguity, reject/fail closed unless the approved requirements explicitly define a bounded fail-safe mode.
- [ ] Every state-changing administrative operation must be authenticated, authorized, bounded, idempotent or conflict-detected, and security-audited.
- [ ] All queues, buffers, registries, caches, fan-out, concurrency, payloads, and diagnostic cardinality must have explicit ceilings and documented saturation behavior.
- [ ] Every new external interface or configuration format must be versioned, schema-validated, semantically validated, and covered by positive, negative, boundary, and compatibility tests.
- [ ] No requirement may be marked implemented solely because a document claims it; closure requires an implementation reference plus verification evidence appropriate to the requirement.
- [ ] Unexpected test skips, missing external framework dependencies, stale evidence, expired waivers, or digest mismatch must block production acceptance rather than silently degrade to pass.
- [ ] Release evidence must identify the exact source tree, dependency/BOM set, configuration/schema versions, test environment, and artifact digests that were verified.
- [ ] Re-run the full missing-component audit after closure and regenerate the RTM and release acceptance record from machine-readable sources.

## Recommended dependency-aware execution order

| Wave | Purpose | Components |
|---|---|---|
| 0 | Source, ownership, normative requirements, traceability | MC-001–MC-004 |
| 1 | Boundary security, interface semantics, dependency/spec pins, configuration/bootstrap | MC-005–MC-010 |
| 2 | Threat, identity/artifact trust, isolation, cryptography, audit, adversarial security | MC-011–MC-016 |
| 3 | Failure detection, overload safety, failover, chaos/fault recovery | MC-017–MC-020 |
| 4 | Performance, capacity, release regression gates | MC-021–MC-023 |
| 5 | Health, telemetry, explainability, dashboards/alerts | MC-024–MC-027 |
| 6 | Certification, concurrency, security regression, soak/disaster | MC-028–MC-031 |
| 7 | Release evidence and production operating package | MC-032–MC-040 |
| 8 | Standalone packaging/CI/release metadata and final closure | MC-041 |

---

## MC-005 — Boundary authentication and authorization/capability policy

**Priority:** Critical  
**Audit gap:** Identity mapping exists, but authentication and authorization requirements are not specified per reconcile/identity/bypass boundary.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C023` | **missing** | Define authentication requirements at each Existing service-mesh layer boundary. |
| `INV-58-C024` | **missing** | Define authorization and explicit capability requirements at each Existing service-mesh layer boundary. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-005, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-005 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define a boundary matrix for `reconcile`, `identity`, `bypass`, configuration mutation, status/diagnostics, and administrative freeze/rollback operations.
- [ ] For each boundary identify caller type, authentication mechanism, required identity claims, trust anchor, token/certificate lifetime, replay protections, and failure mode.
- [ ] Define deny-by-default authorization using explicit roles/capabilities rather than relying on authentication alone.
- [ ] Separate read-only observation capabilities from policy mutation, route migration, configuration activation, audit export, and emergency control capabilities.
- [ ] Define tenant and workload scoping rules so a caller authorized for one tenant/route cannot read or mutate another.
- [ ] Define authorization behavior for missing claims, unknown role/capability, expired credential, stale policy, trust-service outage, and ambiguous identity.
- [ ] Produce stable machine-readable authorization decision codes suitable for audit and metrics without leaking secrets.
- [ ] Add positive, negative, confused-deputy, cross-tenant, privilege-escalation, replay, and stale-credential tests for every privileged operation.
- [ ] Audit every denied and privileged action with authenticated actor, target, requested capability, policy version, decision, reason code, and correlation identifier.
- [ ] Require explicit security review for any wildcard capability, global administrator role, or break-glass bypass.

### B. Mandatory work-product expansion
#### B.1 — Per-interface caller identity requirements.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Per-interface caller identity requirements.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Capability/role policy and deny-by-default authorization.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Capability/role policy and deny-by-default authorization.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Negative authorization tests and audit events.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Negative authorization tests and audit events.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-009 — Declarative configuration, provenance, atomic activation, rollback, and secret-handling subsystem

**Priority:** Critical  
**Audit gap:** Core functions validate inputs and route migration is copy-on-write, but the repository has no complete immutable-artifact/mutable-config separation or production configuration lifecycle.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C032` | **missing** | Separate immutable artifacts from mutable configuration and state for Existing service-mesh layer. |
| `INV-58-C033` | **missing** | Define declarative configuration and secure defaults for Existing service-mesh layer. |
| `INV-58-C034` | **partial** | Validate configuration before activation and fail closed on security-critical errors. |
| `INV-58-C035` | **missing** | Support site- and environment-specific configuration without rebuilding immutable artifacts. |
| `INV-58-C036` | **missing** | Record configuration provenance, version, author, and activation time. |
| `INV-58-C037` | **partial** | Apply atomic or transactional configuration updates where partial application is unsafe. |
| `INV-58-C038` | **missing** | Define automatic and operator-driven rollback for failed Existing service-mesh layer changes. |
| `INV-58-C039` | **missing** | Keep credentials and secret material out of ordinary Existing service-mesh layer configuration and diagnostics. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-009, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-009 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define a versioned configuration schema separated from immutable code artifacts and runtime-generated state.
- [ ] Classify every setting as global/site/environment/tenant/workload/route scoped; prohibit ambiguous precedence between scopes.
- [ ] Provide secure defaults that disable unsafe bypasses, duplicated retries, permissive trust domains, unbounded buffers, and unauthenticated administration.
- [ ] Implement environment/site overlays using explicit merge semantics and reject unknown or conflicting settings rather than silently ignoring them.
- [ ] Validate syntax, schema, semantic constraints, cross-field invariants, authorization, compatibility, and capacity before activation.
- [ ] Implement a prepare/validate/commit activation model or equivalent atomic mechanism for multi-setting changes.
- [ ] Assign a monotonically increasing revision and immutable digest to every activated configuration snapshot.
- [ ] Record author/actor, source, change ticket/commit if available, parent revision, validation result, activation time, and rollout scope.
- [ ] Implement operator rollback to a known-good snapshot and automatic rollback criteria for failed activation or health regression.
- [ ] Represent secrets only by references/handles; never serialize raw keys/tokens/cert private material into ordinary config, logs, status, or evidence.
- [ ] Define redaction and zeroization expectations for secret-derived values and test logs/exceptions for leakage.
- [ ] Add concurrent-update/conflict tests, crash-during-activation tests, stale-revision tests, and rollback idempotency tests.
- [ ] Provide a read-only “effective configuration” view with secrets redacted and provenance visible.

### B. Mandatory work-product expansion
#### B.1 — Versioned declarative configuration schema with secure defaults.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Versioned declarative configuration schema with secure defaults.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Environment/site overlays without rebuild.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Environment/site overlays without rebuild.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Provenance: author, source, version, digest, activation time.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Provenance: author, source, version, digest, activation time.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Atomic multi-setting activation and rollback.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Atomic multi-setting activation and rollback.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.5 — Secret references rather than secret material in config/logs.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Secret references rather than secret material in config/logs.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.6 — Validation-before-activation and fail-closed security policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Validation-before-activation and fail-closed security policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-011 — Complete threat model, least privilege, and ambient-authority reduction

**Priority:** Critical  
**Audit gap:** Only three threats are listed; no data-flow threat model, privilege inventory, or ambient filesystem/network/kernel/secret authority analysis is present.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C041` | **partial** | Threat-model Existing service-mesh layer against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse. |
| `INV-58-C042` | **missing** | Apply least privilege to every identity and capability used by Existing service-mesh layer. |
| `INV-58-C043` | **missing** | Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Existing service-mesh layer permits. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-011, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-011 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create a data-flow diagram showing trust boundaries among application/runtime, incumbent mesh, security plane, authorization, observability, configuration, and operator interfaces.
- [ ] Inventory protected assets: retry policy, route registry, identities, configuration, audit evidence, telemetry, trust anchors, and release metadata.
- [ ] Enumerate attacker/actor classes including compromised workload, malicious tenant, compromised node/proxy, privileged operator, supply-chain attacker, and network adversary.
- [ ] Perform structured threat analysis across spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege, replay, and confused-deputy cases.
- [ ] Map every abuse case to preventive, detective, recovery, and residual-risk controls plus a regression test ID.
- [ ] Inventory process/file/network/kernel/secret/time/administrative privileges required by INV-58 and justify each one.
- [ ] Remove ambient filesystem and network access where a narrow capability, explicit descriptor, or injected dependency is sufficient.
- [ ] Constrain writable paths, outbound destinations, credential access, environment variables, subprocess execution, and dynamic code loading.
- [ ] Define privilege separation for ordinary policy reconciliation versus administrative/configuration/security operations.
- [ ] Document residual risks and explicit risk acceptances with owner and expiry; link them to the waiver register.
- [ ] Require threat-model review when interfaces, trust domains, privilege requirements, persistence, or deployment topology change.

### B. Mandatory work-product expansion
#### B.1 — Threat model with assets, actors, trust boundaries, abuse cases, mitigations, and residual risk.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Threat model with assets, actors, trust boundaries, abuse cases, mitigations, and residual risk.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Capability/privilege inventory with least-privilege justification.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Capability/privilege inventory with least-privilege justification.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Ambient-authority elimination/isolation controls.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Ambient-authority elimination/isolation controls.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-012 — Non-workload actor authentication and artifact integrity verification

**Priority:** Critical  
**Audit gap:** Workload SPIFFE SANs are validated, but node/peer/provider/control-plane identity and executable/policy signature/digest/provenance verification are missing.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C044` | **partial** | Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted. |
| `INV-58-C045` | **missing** | Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Existing service-mesh layer. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-012, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-012 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create an actor-authentication matrix covering workloads, nodes, mesh peers/proxies, providers/adapters, controllers, operators, CI/release actors, and control-plane services.
- [ ] Define identity format, trust root, authentication handshake, freshness/lifetime, revocation, and fail-closed behavior for each actor class.
- [ ] Distinguish workload SPIFFE identity from node/platform identity and prevent one from being accepted where the other is required.
- [ ] Verify executable/package/config/policy artifacts by cryptographic digest and approved provenance before activation.
- [ ] Where signatures are used, pin trusted signing identities/keys and define rotation, revocation, threshold/approval, and expired-signature behavior.
- [ ] Bind policy/configuration signatures to version, scope, and content digest to prevent replay in another environment or tenant.
- [ ] Reject unsigned, unknown-signer, malformed-signature, digest-mismatch, expired, revoked, and downgraded artifacts with stable audit reason codes.
- [ ] Add tests for signature substitution, version rollback/downgrade, stale policy replay, and trust-root rotation.
- [ ] Record verified provenance in status and release evidence without exposing sensitive key material.

### B. Mandatory work-product expansion
#### B.1 — Actor authentication matrix.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Actor authentication matrix.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Artifact/policy signature and digest verification.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Artifact/policy signature and digest verification.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Approved-version/provenance enforcement with fail-closed behavior.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Approved-version/provenance enforcement with fail-closed behavior.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-013 — Tenant/workload isolation enforcement

**Priority:** Critical  
**Audit gap:** Isolation boundaries are documented but not enforced or tested by the component.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C046` | **missing** | Enforce tenant/workload isolation across Existing service-mesh layer execution, memory, state, network, and device boundaries as applicable. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-013, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-013 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define the canonical isolation key(s) used for tenant, environment, site, workload, and route; avoid deriving scope from untrusted display names.
- [ ] Partition route-policy state and bypass evidence by required scope and prevent cross-scope key collisions.
- [ ] Apply authorization filters before lookup/mutation so existence of another tenant’s route or evidence is not leaked.
- [ ] Partition metrics/logs/traces or attach mandatory tenant/workload labels with privacy controls and server-side access enforcement.
- [ ] Define per-tenant quotas and fairness behavior so one tenant cannot exhaust global route, evidence, concurrency, or diagnostic capacity.
- [ ] Ensure configuration overlays cannot accidentally broaden from tenant/workload scope to global scope.
- [ ] Add cross-tenant read/write/delete/migrate/rollback/diagnostic denial tests and side-channel-oriented existence tests.
- [ ] Test adversarial identifiers for prefix/suffix confusion, Unicode/normalization collisions, delimiter injection, and case-sensitivity mistakes.
- [ ] If persistence is added, verify storage namespaces, encryption boundaries, backup/restore filters, and migration tooling preserve isolation.
- [ ] Include isolation invariants in architecture and threat-model reviews.

### B. Mandatory work-product expansion
#### B.1 — Tenant/workload keying and isolation invariants.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Tenant/workload keying and isolation invariants.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Cross-tenant denial tests.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Cross-tenant denial tests.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Isolation of state, telemetry, policy, and administrative operations.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Isolation of state, telemetry, policy, and administrative operations.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-014 — Encryption/key-rotation policy and trust-service outage behavior

**Priority:** Critical  
**Audit gap:** Incumbent mTLS is assumed, but at-rest encryption/key rotation and safe behavior when identity/attestation/policy/key/time services fail are not specified.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C047` | **partial** | Encrypt sensitive Existing service-mesh layer data in transit and at rest with managed key rotation. |
| `INV-58-C048` | **missing** | Define safe behavior when identity, attestation, policy, key, or time services are unavailable. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-014, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-014 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define the approved mTLS/TLS profile: protocol versions, cipher suites, certificate validation, SAN requirements, trust roots, and hostname/SPIFFE expectations.
- [ ] Define ownership and maximum age for workload certificates, trust bundles, signing keys, and any at-rest encryption keys.
- [ ] Define overlapping rotation windows and behavior when old/new trust bundles coexist during rotation.
- [ ] If configuration, audit evidence, or route state becomes durable, define at-rest encryption requirements and key separation by environment/tenant where needed.
- [ ] Create a dependency-outage matrix for identity provider, attestation service, policy service, key service, secure time source, and trust-bundle distribution.
- [ ] For each outage define fail-closed versus bounded fail-safe behavior, cache age limits, grace periods, and prohibited operations.
- [ ] Define clock-skew tolerance and behavior for expired/not-yet-valid credentials; never silently extend validity based solely on local failure.
- [ ] Test key/certificate rotation, revoked trust roots, stale caches, skewed clocks, expired identity, unavailable trust service, and partial bundle propagation.
- [ ] Audit use of degraded trust behavior and make it visible in health/status and alerts.

### B. Mandatory work-product expansion
#### B.1 — TLS/mTLS profile and rotation ownership.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **TLS/mTLS profile and rotation ownership.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — At-rest protection for persisted evidence/config if introduced.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **At-rest protection for persisted evidence/config if introduced.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Fail-closed/fail-safe matrix for trust dependencies.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Fail-closed/fail-safe matrix for trust dependencies.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Expiry/skew/time-source handling.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Expiry/skew/time-source handling.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-015 — Tamper-evident security audit trail

**Priority:** Critical  
**Audit gap:** Bypass evidence is retained in-memory but is neither durable nor tamper-evident and security-sensitive operations are not comprehensively audited.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C049` | **missing** | Emit tamper-evident audit events for security-sensitive Existing service-mesh layer operations. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-015, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-015 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define a versioned security-audit event schema separate from ordinary debug/application logs.
- [ ] Include event time, monotonic ordering/sequence where possible, actor identity, tenant/scope, action, target, policy/config version, decision, reason code, correlation ID, and release version.
- [ ] Audit successful and failed authentication, authorization denials, identity mapping failures, bypass detections, policy/config changes, route migrations, rollbacks, quarantine/freeze, and break-glass actions.
- [ ] Use append-only storage or external sealing; if local chaining is used, hash-chain events and periodically anchor/seal heads externally.
- [ ] Define durability, retention, rotation, export, clock-integrity, and loss/backpressure behavior; security events must not disappear silently on buffer overflow.
- [ ] Redact secrets and sensitive payloads while preserving enough context for forensics.
- [ ] Define who may read/export/delete audit data and audit those administrative actions themselves.
- [ ] Add tamper tests for deletion, reordering, modification, truncation, duplicate insertion, forged chain head, and clock rollback.
- [ ] Expose audit-pipeline degradation as a health/status condition and define whether sensitive operations must fail closed when durable audit is unavailable.
- [ ] Verify audit event digests/retention evidence during release and incident exercises.

### B. Mandatory work-product expansion
#### B.1 — Structured security audit event schema.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Structured security audit event schema.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Append-only/hash-chained or externally sealed retention.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Append-only/hash-chained or externally sealed retention.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Identity, policy-change, bypass, rejection, rollback, and admin events.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Identity, policy-change, bypass, rejection, rollback, and admin events.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-016 — Full adversarial security test program

**Priority:** Critical  
**Audit gap:** Current tests cover malformed identities and some resource bounds only.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C050` | **partial** | Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-016, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-016 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Build an adversarial test inventory directly from the threat model and tag each test with one or more threat IDs.
- [ ] Test malformed, oversized, ambiguous, encoded, Unicode, control-character, and delimiter-confusing route/identity inputs.
- [ ] Test authentication spoofing, foreign trust domains, replay, expired credentials, mismatched actor type, and trust-root substitution.
- [ ] Test authorization bypass, confused deputy, tenant escape, scope widening, stale-policy replay, and break-glass misuse.
- [ ] Test policy/config injection, schema confusion, unknown fields, version downgrade, malicious provenance metadata, and unsafe overlay precedence.
- [ ] Test retry amplification, deliberate dependency flapping, queue exhaustion, route-registry exhaustion, bypass-evidence flooding, and expensive invalid-input paths.
- [ ] Test concurrency attacks including racing route migration, rollback, config activation, quarantine, and status reads.
- [ ] Test audit-log injection/redaction failures and attempts to hide or forge security-relevant events.
- [ ] Create a permanent regression fixture for every security defect found, with CVE/issue/advisory reference where applicable.
- [ ] Run the security regression corpus in normal and optimized Python modes and with fuzz/property testing for parser boundaries.

### B. Mandatory work-product expansion
#### B.1 — Privilege escalation/injection/replay/spoofing/escape tests.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Privilege escalation/injection/replay/spoofing/escape tests.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Resource-exhaustion and side-channel-oriented cases.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Resource-exhaustion and side-channel-oriented cases.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Security regression corpus tied to threat-model entries.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Security regression corpus tied to threat-model entries.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-018 — Retry timing safety and overload protection

**Priority:** Critical  
**Audit gap:** Attempt counts are bounded, but no backoff/jitter/retry-safety executor or admission control/load shedding/circuit breaker exists.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C053` | **partial** | Implement bounded retry with backoff and jitter only where operations are safe to retry. |
| `INV-58-C054` | **missing** | Implement admission control, load shedding, or circuit breaking to prevent Existing service-mesh layer failure cascades. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-018, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-018 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Classify operations as safely retryable, conditionally retryable with idempotency key, or never automatically retryable.
- [ ] Define a total attempt budget that includes the initial attempt and all app/mesh/internal retries so multiplication cannot reappear through hidden layers.
- [ ] Define backoff schedule, cap, jitter algorithm, deadline interaction, and maximum cumulative retry time per operation class.
- [ ] Honor caller deadlines and cancellation; do not start a retry that cannot complete within the remaining deadline budget.
- [ ] Define circuit-breaker state machine, sample window, trip threshold, half-open behavior, reset policy, and per-tenant/route scoping.
- [ ] Implement bounded admission control/concurrency limits and explicit load shedding before queues become unbounded.
- [ ] Differentiate overload responses from dependency failures using stable error codes so callers do not blindly retry shed traffic.
- [ ] Protect health/status/audit/control operations from starvation by ordinary traffic.
- [ ] Test synchronized failure storms to demonstrate jitter disperses retries and total attempts stay within budget.
- [ ] Test overload fairness, circuit-breaker races, recovery from half-open, and interactions with route migration/config changes.

### B. Mandatory work-product expansion
#### B.1 — Retry-safety/idempotency classification.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Retry-safety/idempotency classification.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Bounded exponential backoff + jitter policy where applicable.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Bounded exponential backoff + jitter policy where applicable.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Circuit breaker/admission/load-shed controls with tests.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Circuit breaker/admission/load-shed controls with tests.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-019 — Failover, degraded mode, restart/replay, distributed ownership, and quarantine controls

**Priority:** Critical  
**Audit gap:** Single-layer retry ownership is protected, but the broader resilience state model and operator safety controls are absent.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C055` | **missing** | Define failover behavior without violating isolation, residency, or consistency requirements. |
| `INV-58-C056` | **missing** | Provide degraded operation when noncritical dependencies are unavailable. |
| `INV-58-C057` | **missing** | Define crash-consistency, restart, resume, or replay semantics for mutable Existing service-mesh layer state. |
| `INV-58-C058` | **partial** | Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant. |
| `INV-58-C059` | **missing** | Provide quarantine, freeze, disable, or isolation controls for unsafe Existing service-mesh layer behavior. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-019, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-019 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define safe failover eligibility with hard constraints for residency, tenant isolation, trust domain, compatible policy, and supported version.
- [ ] Define degraded modes such as read-only policy, cached identity mapping, reconciliation without migration, bypass detection only, or fail-closed unavailability; document exactly which operations remain legal.
- [ ] Define crash-consistency model for any mutable state and whether route/config/audit state is durable, reconstructable, or ephemeral.
- [ ] Define replay/resume semantics with monotonic revision/epoch so stale controllers cannot overwrite newer state after restart.
- [ ] Introduce ownership epochs/leases/fencing tokens if more than one controller/instance can mutate shared state.
- [ ] Detect and reject split-brain or stale-controller writes; define operator-visible evidence when fencing occurs.
- [ ] Provide quarantine/freeze/disable controls scoped to tenant/workload/route/component with explicit authorization and audit.
- [ ] Define whether emergency disable preserves observation/audit while blocking mutation or traffic-affecting actions.
- [ ] Test failover during config activation, route migration, key rotation, audit export, and dependency partition.
- [ ] Test restart/replay after process kill at every mutation phase and prove no duplicate/partial policy activation.
- [ ] Document recovery priority and operator decision tree for conflicting safety/availability goals.

### B. Mandatory work-product expansion
#### B.1 — Residency/isolation-safe failover policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Residency/isolation-safe failover policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Defined degraded modes.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Defined degraded modes.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Crash consistency and replay/resume semantics.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Crash consistency and replay/resume semantics.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Stale-controller/split-brain fencing.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Stale-controller/split-brain fencing.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.5 — Quarantine/freeze/disable controls with authorization and audit.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Quarantine/freeze/disable controls with authorization and audit.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-030 — Threat-model-derived security regression suite

**Priority:** Critical  
**Audit gap:** Security tests are not systematically generated/traced from every threat-model abuse case.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C087` | **partial** | Create security tests derived directly from the Existing service-mesh layer threat model. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-030, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-030 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Assign stable threat IDs in the threat model and require every abuse case to reference at least one automated security test or an approved manual verification.
- [ ] Create a machine-readable threat-to-test mapping containing threat, mitigation, test IDs, expected result, owner, and release status.
- [ ] Include positive and negative authentication/authorization tests so security controls are proven usable as well as restrictive.
- [ ] Create regression tests for every security bug, incident lesson, penetration-test finding, and dependency vulnerability that materially affects INV-58.
- [ ] Fail CI when an active/high-risk threat has no verification evidence or when its mapped tests are skipped unexpectedly.
- [ ] Preserve exploit/minimized malicious fixtures safely and document handling restrictions if they contain sensitive details.
- [ ] Run the suite under representative configuration profiles, including strict defaults, supported legacy compatibility, and degraded trust-service scenarios.
- [ ] Link security test evidence into release acceptance and require explicit security approval for waived failures.

### B. Mandatory work-product expansion
#### B.1 — Threat-to-test mapping.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Threat-to-test mapping.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Positive/negative authorization and identity cases.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Positive/negative authorization and identity cases.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Regression fixtures for every remediated security defect.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Regression fixtures for every remediated security defect.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-032 — Machine-readable release acceptance evidence and reproducible production exit gate

**Priority:** Critical  
**Audit gap:** The README references `pk_core gate`, but this archive has no current evidence ledger/gate result and cannot run the framework-level gate without external `pk_core`.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C090` | **missing** | Require machine-readable acceptance evidence before certifying a Existing service-mesh layer release for production. |
| `INV-58-C100` | **partial** | Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-032, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-032 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define a versioned machine-readable release acceptance schema covering all 100 checklist items and all supplemental release gates.
- [ ] For every requirement record status, implementation reference, verification evidence reference/digest, reviewer/owner, timestamp, and waiver ID if not fully satisfied.
- [ ] Include source tree/release digest, BOM/SBOM digest, compatibility matrix digest, configuration schema version, benchmark baseline ID, and RTM digest.
- [ ] Run `pk_core` conformance/gate in an environment where the exact supported `pk_core` version is available; do not treat local skipped framework tests as equivalent.
- [ ] Reject release publication if mandatory evidence is missing, evidence hashes do not resolve, tests were unexpectedly skipped, or an expired waiver is referenced.
- [ ] Sign or externally seal the final acceptance record and retain it immutably with release artifacts.
- [ ] Make the gate reproducible from documented inputs and capture tool versions/command line/environment needed to reproduce the verdict.
- [ ] Prevent manual editing of a passing verdict without invalidating its digest/signature.
- [ ] Generate a concise human-readable release summary from the machine-readable record while preserving the canonical machine source.

### B. Mandatory work-product expansion
#### B.1 — Versioned machine-readable acceptance record.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Versioned machine-readable acceptance record.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Evidence hashes/references for all checklist items.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Evidence hashes/references for all checklist items.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Signed/immutable release gate result.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Signed/immutable release gate result.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — CI rule preventing publication without passing evidence.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **CI rule preventing publication without passing evidence.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-001 — Missing source master prompt/workflow bundle

**Priority:** High  
**Audit gap:** README/source inventory expects `MASTER.md`, but the file is absent. It was not reconstructed because the original is described as verbatim source material.

### Requirement traceability

This work package is a repository-level audit finding rather than a direct `INV-58-Cxxx` checklist row; it still requires release evidence and RTM linkage as a supplemental control.

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-001, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-001 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Locate the authoritative upstream source that originally supplied `MASTER.md`; do not synthesize or paraphrase a source described as verbatim.
- [ ] Record source repository/path, commit or release identifier, acquisition date, and SHA-256 digest in a provenance sidecar such as `MASTER.provenance.json`.
- [ ] Compare headings, phase names, checklist identifiers, interface names, and version references in `MASTER.md` against `README.md`, `CHECKLIST.json`, and the 4.2.0 contract.
- [ ] Detect duplicate, missing, reordered, or renamed checklist IDs and document any intentional divergence rather than silently editing source material.
- [ ] Add an artifact-integrity test that fails when README-declared source artifacts are absent, unreadable, empty, or digest-mismatched.
- [ ] If the upstream source is licensed separately, record the applicable license/notice and redistribution conditions alongside provenance metadata.
- [ ] Keep the authoritative source immutable in release packages; derivative annotations belong in a separate generated file.
- [ ] Add the recovered artifact and its provenance digest to release evidence and the requirements traceability matrix.

### B. Mandatory work-product expansion
#### B.1 — Supply the authoritative `MASTER.md` from the source set.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Supply the authoritative `MASTER.md` from the source set.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Verify hash/provenance and align it to `CHECKLIST.json` item IDs.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Verify hash/provenance and align it to `CHECKLIST.json` item IDs.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Add a test or release check that README-declared audit artifacts exist.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Add a test or release check that README-declared audit artifacts exist.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-002 — Accountable ownership and architecture decision record

**Priority:** High  
**Audit gap:** No accountable owner/escalation path or approved ADR for Istio/mTLS coexistence is present.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C009` | **missing** | Assign an accountable owner and escalation path for Existing service-mesh layer. |
| `INV-58-C010` | **missing** | Approve an architecture decision record for Existing service-mesh layer, its technologies (Istio, mTLS), and its function (Network routing/security). |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-002, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-002 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define one accountable service owner for INV-58 and distinguish accountable owner, code owners, security approver, release approver, and operational/on-call roles.
- [ ] Create a CODEOWNERS/OWNER record covering `contract.py`, `mesh_logic.py`, interface schemas, configuration, audit policy, tests, and release evidence.
- [ ] Define primary/secondary escalation paths, response expectations, handoff rules, and the authority required to freeze retry migration or bypass handling.
- [ ] Create an ADR identifying why coexistence with the incumbent Istio/mTLS layer is required and what responsibilities remain explicitly outside INV-58.
- [ ] Capture retry-ownership alternatives considered, including app-only, mesh-only, adaptive ownership, and duplicated ownership; record rejection rationale and safety tradeoffs.
- [ ] Capture identity-handoff choices, SPIFFE trust-domain assumptions, certificate/SAN parsing constraints, and downstream authorization contract.
- [ ] Document route-by-route migration invariants, rollback semantics, and compatibility constraints between old mesh policy and new runtime policy.
- [ ] Include ADR status, approvers, approval date, supersession rules, and links to tests/evidence validating each safety-sensitive decision.

### B. Mandatory work-product expansion
#### B.1 — OWNER/CODEOWNERS or equivalent accountable-owner record.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **OWNER/CODEOWNERS or equivalent accountable-owner record.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Escalation path/on-call ownership.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Escalation path/on-call ownership.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — ADR covering incumbent mesh, retry ownership, mTLS identity handoff, migration constraints, and alternatives.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **ADR covering incumbent mesh, retry ownership, mTLS identity handoff, migration constraints, and alternatives.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-003 — Formal requirements, deployment-context, lifecycle, precedence, and compatibility semantics

**Priority:** High  
**Audit gap:** The contract states scope and a few SLOs, but does not provide a complete SHALL-level requirements specification across deployment contexts, lifecycle/outcome states, versioning, connectivity loss, quota/fairness, or precedence rules.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C011` | **missing** | Translate the source function of Existing service-mesh layer — Network routing/security — into testable SHALL-level requirements. |
| `INV-58-C012` | **missing** | Define functional requirements for Existing service-mesh layer across cloud, datacenter, near-edge, and far-edge contexts where applicable. |
| `INV-58-C013` | **partial** | Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable. |
| `INV-58-C014` | **missing** | Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Existing service-mesh layer. |
| `INV-58-C015` | **missing** | Define lifecycle states and legal state transitions managed or exposed by Existing service-mesh layer. |
| `INV-58-C016` | **missing** | Define versioning and backward-compatibility requirements for Existing service-mesh layer. |
| `INV-58-C017` | **partial** | Define capacity ceilings, quotas, and fairness semantics relevant to Existing service-mesh layer. |
| `INV-58-C018` | **missing** | Define behavior when network connectivity is intermittent or absent. |
| `INV-58-C019` | **missing** | Define precedence rules when Existing service-mesh layer requirements conflict with security, residency, SLO, or cost constraints. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-003, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-003 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create a normative `REQUIREMENTS.md` or machine-readable equivalent using RFC 2119/8174-style SHALL/SHOULD/MAY language and stable requirement identifiers.
- [ ] For each requirement, define actor, preconditions, inputs, observable behavior, failure behavior, measurable acceptance criterion, and owning subsystem.
- [ ] Create a deployment-context applicability matrix for cloud, datacenter, near-edge, and far-edge; mark N/A only with written justification.
- [ ] Define a canonical outcome vocabulary: success, partial success, degraded success, retryable failure, terminal failure, rejected/policy failure, and unavailable dependency.
- [ ] Define lifecycle states for configuration and route migration such as proposed, validated, staged, active, degraded, rolled-back, quarantined, and retired.
- [ ] Define legal and illegal lifecycle transitions and specify atomicity, authorization, idempotency, and audit requirements for each transition.
- [ ] Define API/schema compatibility policy for major/minor/patch changes and exact behavior for older/newer supported peers.
- [ ] Define hard capacity ceilings and fairness behavior per tenant/workload/route, including admission decisions when global or tenant ceilings are reached.
- [ ] Define offline/intermittent-connectivity behavior for identity, policy, configuration, telemetry, and evidence paths without assuming a global singleton.
- [ ] Create an explicit precedence table for security, residency, correctness, availability/SLO, operational override, and cost constraints; identify which constraints may never be overridden.

### B. Mandatory work-product expansion
#### B.1 — SHALL-level requirements with stable IDs.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **SHALL-level requirements with stable IDs.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Cloud/datacenter/near-edge/far-edge applicability matrix.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Cloud/datacenter/near-edge/far-edge applicability matrix.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Success/partial/degraded/retryable/terminal outcome model.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Success/partial/degraded/retryable/terminal outcome model.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Lifecycle state machine and legal transitions.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Lifecycle state machine and legal transitions.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.5 — Backward-compatibility/versioning policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Backward-compatibility/versioning policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.6 — Capacity/quota/fairness model.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Capacity/quota/fairness model.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.7 — Disconnected/intermittent-connectivity behavior.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Disconnected/intermittent-connectivity behavior.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.8 — Constraint-precedence rules.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Constraint-precedence rules.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-004 — Requirements traceability matrix

**Priority:** High  
**Audit gap:** No matrix maps each requirement to implementation location, test/evidence, owner, and release status.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C020` | **missing** | Maintain a requirements traceability matrix from each Existing service-mesh layer requirement to implementation and verification evidence. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-004, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-004 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create `REQUIREMENTS_TRACEABILITY.json` (or equivalent) with one row for every `INV-58-C001` through `INV-58-C100`.
- [ ] For each row record requirement text, implementation artifact/symbol, test identifier, evidence path/digest, owner, status, release introduced, and last verification timestamp.
- [ ] Permit multiple implementation/test references per requirement and support one implementation artifact satisfying multiple requirements without losing provenance.
- [ ] Validate that every referenced file/symbol/test actually exists and that evidence digests match packaged artifacts.
- [ ] Add a CI validator that fails on duplicate IDs, missing IDs, unknown IDs, empty implementation evidence, stale file references, or status/evidence contradictions.
- [ ] Generate a human-readable RTM view from the machine-readable source rather than maintaining two manually divergent matrices.
- [ ] Include partial requirements with explicit residual gaps; do not encode partial as pass.
- [ ] Bind release acceptance evidence to the exact RTM digest so a release cannot reuse an older matrix accidentally.

### B. Mandatory work-product expansion
#### B.1 — Machine-readable RTM keyed by INV-58-C001..C100.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Machine-readable RTM keyed by INV-58-C001..C100.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Implementation and verification evidence references.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Implementation and verification evidence references.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Release-time completeness check that rejects dangling requirements.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Release-time completeness check that rejects dangling requirements.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-006 — Complete interface operational semantics, structured failures, compatibility, limits, and fixtures

**Priority:** High  
**Audit gap:** Typed schemas exist, but timeout/cancel/backpressure/idempotency semantics, structured error codes, peer-version behavior, complete limits, and reusable conformance fixtures are incomplete.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C025` | **partial** | Define timeout, cancellation, retry, idempotency, and backpressure semantics for Existing service-mesh layer. |
| `INV-58-C026` | **missing** | Define structured failure codes and machine-readable error details for Existing service-mesh layer. |
| `INV-58-C027` | **missing** | Define compatibility behavior when peers use different supported versions. |
| `INV-58-C028` | **partial** | Document payload, concurrency, queue, connection, or resource limits at Existing service-mesh layer interfaces. |
| `INV-58-C029` | **partial** | Provide reference examples and conformance fixtures for Existing service-mesh layer. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-006, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-006 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define timeout budgets for each public interface and distinguish caller timeout, internal processing timeout, dependency timeout, and overall deadline propagation.
- [ ] Define cancellation semantics, including whether cancellation is best-effort or guaranteed and whether a partially applied mutation may remain.
- [ ] Define idempotency keys and duplicate-request behavior for state-changing operations; specify retention window and collision behavior.
- [ ] Define backpressure behavior under queue/concurrency saturation: reject, shed, block, or degrade; never allow unbounded queues.
- [ ] Create a stable error envelope containing code, category, retryable flag, safe message, correlation ID, details schema, and optional remediation hint.
- [ ] Create a versioned error-code registry and reserve ranges/categories for validation, authentication, authorization, conflict, capacity, dependency, and internal faults.
- [ ] Define peer-version negotiation and exact handling of unsupported major versions, unknown optional fields, and required field evolution.
- [ ] Document concrete payload, route-length, identity-length, destination-count, route-count, connection, queue, concurrency, and evidence-buffer ceilings.
- [ ] Create golden valid/invalid request, response, and error fixtures for each schema and include boundary values at every declared limit.
- [ ] Add conformance tests ensuring implementations reject structurally valid but semantically unsafe payloads in the same way as direct Python APIs.

### B. Mandatory work-product expansion
#### B.1 — Timeout/cancellation/backpressure/idempotency rules.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Timeout/cancellation/backpressure/idempotency rules.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Stable machine-readable error envelope and codes.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Stable machine-readable error envelope and codes.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Version negotiation/compatibility behavior.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Version negotiation/compatibility behavior.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Explicit payload/queue/connection/concurrency ceilings.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Explicit payload/queue/connection/concurrency ceilings.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.5 — Golden request/response/error fixtures for every schema.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Golden request/response/error fixtures for every schema.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-007 — Adjacent-layer integration test harness

**Priority:** High  
**Audit gap:** No automated integration suite exercises INV-48, security plane, INV-59, and GAP-09 interactions.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C030` | **missing** | Create automated integration tests proving Existing service-mesh layer interoperates with adjacent architectural layers. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-007, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-007 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define an integration topology that exercises INV-58 with INV-48 service communication APIs, PLN-07 security plane, INV-59 authorization, and GAP-09 observability.
- [ ] Provide deterministic test doubles for fast CI plus an optional deployable topology using real supported adapters/components for certification.
- [ ] Test propagation from upstream retry policy through reconciliation to the effective single-owner policy consumed by a downstream request path.
- [ ] Test SPIFFE identity issuance/mapping through the security-plane boundary and consumption by authorization, including rejection of foreign or malformed identities.
- [ ] Test bypass detection visibility in unified observability and confirm correlation identifiers connect upstream request, mesh, runtime, and audit records.
- [ ] Inject dependency unavailability, incompatible versions, latency, partial response, and malformed payloads at every adjacent boundary.
- [ ] Assert no integration test permits multiplied retries, cross-tenant identity confusion, silent bypass, or unbounded waiting.
- [ ] Run the matrix against every supported adjacent-layer version combination declared in the compatibility matrix.
- [ ] Capture topology version, component versions, test seed, logs, traces, and result digests as release evidence.

### B. Mandatory work-product expansion
#### B.1 — Mocks/test doubles or deployable test topology for each declared dependency.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Mocks/test doubles or deployable test topology for each declared dependency.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Positive and failure-path integration tests.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Positive and failure-path integration tests.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — CI gate for supported adjacent-layer versions.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **CI gate for supported adjacent-layer versions.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-008 — Pinned Istio/mTLS implementation/specification bill of materials

**Priority:** High  
**Audit gap:** The repository names Istio/mTLS conceptually but does not pin approved versions/spec revisions or compatibility ranges.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C031` | **missing** | Select and pin approved implementations, versions, or specifications for Existing service-mesh layer: Istio, mTLS. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-008, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-008 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create an approved implementation BOM identifying Istio control-plane version, proxy/data-plane version, Kubernetes/runtime assumptions if applicable, and supported skew windows.
- [ ] Pin the SPIFFE/SPIRE or SPIFFE-ID specification/profile assumptions used by `map_identity`, including URI normalization rules and trust-domain validation rules.
- [ ] Pin TLS/mTLS protocol versions, cipher/profile policy, certificate key types, SAN expectations, and prohibited legacy modes.
- [ ] Define minimum, maximum, recommended, deprecated, and EOL versions instead of a single floating “latest” version.
- [ ] Define allowed control-plane/data-plane skew and upgrade order; document behavior outside the supported skew window.
- [ ] Generate or ingest an SBOM for runtime/package dependencies and include package name, version, source, license, digest, and vulnerability identifiers where available.
- [ ] Define dependency update policy, approval owner, compatibility test requirement, and emergency security update process.
- [ ] Add CI checks rejecting unpinned production dependencies, unsupported versions, unexpected transitive dependencies, or BOM/compatibility-matrix disagreement.
- [ ] Bind the BOM digest to release acceptance evidence.

### B. Mandatory work-product expansion
#### B.1 — Approved Istio version/range and proxy/data-plane version policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Approved Istio version/range and proxy/data-plane version policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — SPIFFE/mTLS/TLS profile/spec revision pins.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **SPIFFE/mTLS/TLS profile/spec revision pins.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — SBOM/dependency manifest with update policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **SBOM/dependency manifest with update policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-010 — Reproducible empty-environment bootstrap

**Priority:** High  
**Audit gap:** README commands assume the external ecosystem is already available; no lockfile/installer/bootstrap verifies prerequisites from an empty environment.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C040` | **partial** | Provide a deterministic bootstrap path from an empty node/environment to healthy Existing service-mesh layer operation. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-010, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-010 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Declare supported Python versions and architecture/OS constraints explicitly.
- [ ] Add `pyproject.toml` or equivalent package metadata with deterministic dependency declaration and a lock/constraints file for reproducible environments.
- [ ] Declare `pk_core` compatibility explicitly instead of assuming it is importable from an external parent checkout.
- [ ] Provide a preflight command that verifies Python version, filesystem permissions, required packages, optional integration tooling, and compatibility versions.
- [ ] Provide a deterministic bootstrap command from an empty virtual environment and ensure it does not silently install unapproved floating dependencies.
- [ ] Fail with actionable diagnostics when `pk_core` is missing, wrong-version, or shadowed on `sys.path`.
- [ ] Run local unit/schema tests and a package import/version check as a post-bootstrap health verification.
- [ ] Test bootstrap on at least one clean CI image for every supported OS/Python combination and cache only by lockfile digest.
- [ ] Document offline/air-gapped bootstrap inputs and required artifact mirrors if production environments may lack public network access.

### B. Mandatory work-product expansion
#### B.1 — Pinned dependency/bootstrap manifest.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Pinned dependency/bootstrap manifest.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Preflight checks for Python and `pk_core`.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Preflight checks for Python and `pk_core`.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Deterministic setup command and post-bootstrap health check.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Deterministic setup command and post-bootstrap health check.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-017 — Complete failure taxonomy plus health/stall detection

**Priority:** High  
**Audit gap:** A short failure-mode list exists, but no layer-by-layer failure catalog or automated health/stall thresholds are implemented.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C051` | **partial** | Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Existing service-mesh layer. |
| `INV-58-C052` | **missing** | Define automated health and stall detection thresholds for Existing service-mesh layer. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-017, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-017 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create a failure taxonomy covering process crash/hang, Python/runtime failure, proxy failure, node failure, site failure, partition, DNS, control plane, security plane, authorization, observability, storage, provider, and operator/configuration failure.
- [ ] Classify each failure by detectability, blast radius, data/state risk, retryability, expected degraded mode, and recovery owner.
- [ ] Define liveness separately from readiness and from dependency health; avoid declaring ready solely because the process is running.
- [ ] Define stall indicators for lock contention, route migration not progressing, audit/telemetry queue saturation, stale config revision, and repeated dependency timeout.
- [ ] Set detection thresholds and detection-latency objectives with hysteresis/debounce to avoid alert flapping.
- [ ] Define startup grace periods and dependency-specific readiness semantics.
- [ ] Define what health information is safe for unauthenticated exposure versus privileged diagnostics.
- [ ] Test false-positive and false-negative scenarios, dependency slowness, intermittent failures, and partial subsystem degradation.
- [ ] Link every health/stall detector to a remediation/runbook and alert classification.

### B. Mandatory work-product expansion
#### B.1 — Process/VM/node/site/network/provider/dependency/control-plane failure matrix.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Process/VM/node/site/network/provider/dependency/control-plane failure matrix.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Health/readiness/stall indicators and thresholds.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Health/readiness/stall indicators and thresholds.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Detection latency objectives and false-positive handling.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Detection latency objectives and false-positive handling.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-020 — Fault-injection recovery suite

**Priority:** High  
**Audit gap:** No fault-injection tests demonstrate recovery against documented objectives.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C060` | **missing** | Run fault-injection tests proving Existing service-mesh layer recovery against documented objectives. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-020, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-020 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Build deterministic fault-injection hooks at dependency boundaries instead of relying only on random process kills.
- [ ] Inject timeout, connection reset, malformed response, stale response, version mismatch, partial write, unavailable dependency, delayed dependency, and authorization denial.
- [ ] Inject mesh/control-plane/security-plane/observability outages independently and in selected combinations.
- [ ] Inject packet loss, latency, reordering, partition, reconnect, DNS failure, and clock skew where the deployment environment permits.
- [ ] Assert attempt budgets, isolation, audit integrity, state atomicity, and fail-closed security invariants under every fault.
- [ ] Measure detection time, degraded-mode entry time, recovery time, and any lost/replayed work against explicit objectives.
- [ ] Use deterministic seeds and capture injected-fault timeline so failures can be replayed.
- [ ] Keep a fast smoke subset in CI and run broader chaos profiles on schedule/pre-release.
- [ ] Fail the suite on leaked threads/resources, stuck locks, unrecovered circuit breakers, or stale readiness after recovery.

### B. Mandatory work-product expansion
#### B.1 — Dependency/network/control-plane failure injection.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Dependency/network/control-plane failure injection.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Recovery-time/data-integrity assertions.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Recovery-time/data-integrity assertions.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — CI or scheduled chaos profile.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **CI or scheduled chaos profile.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-021 — Performance baselines, percentile thresholds, load profiles, and tenant/workload overhead measurements

**Priority:** High  
**Audit gap:** Only a p99 identity-mapping target is declared; no reproducible benchmark evidence or broad threshold set exists.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C061` | **missing** | Establish reproducible baselines for Existing service-mesh layer latency, throughput, startup, CPU, memory, storage, network, and power overhead. |
| `INV-58-C062` | **partial** | Define p50, p95, p99, and worst-case performance thresholds for Existing service-mesh layer. |
| `INV-58-C063` | **missing** | Measure Existing service-mesh layer under steady load, burst load, overload, scale-out, scale-in, and recovery. |
| `INV-58-C064` | **missing** | Measure per-workload and per-tenant overhead introduced by Existing service-mesh layer. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-021, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-021 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define a reproducible benchmark environment manifest containing hardware/CPU, OS/kernel, Python version, dependency versions, mesh/proxy versions, topology, and configuration digest.
- [ ] Benchmark `reconcile`, `map_identity`, bypass observation, route migration, status/telemetry overhead, and end-to-end integrated request path where applicable.
- [ ] Measure latency distributions p50/p95/p99/p99.9/max, throughput, CPU, memory/RSS, allocations/GC, network bytes, and startup/readiness time.
- [ ] Verify the declared p99 identity-mapping target under realistic identity lengths and concurrent load, not only microbenchmarks.
- [ ] Define steady-state, burst, overload, ramp, saturation, recovery, high-cardinality, and cold-start profiles.
- [ ] Measure per-tenant/workload overhead and fairness under skewed noisy-neighbor load.
- [ ] Record confidence intervals/sample counts and warm-up methodology; avoid reporting a single best run.
- [ ] Separate benchmark noise from regression using repeated runs and machine/environment identity.
- [ ] Store baseline artifacts in machine-readable form with release/version/config digests and raw samples or sufficient aggregates for audit.
- [ ] Define absolute ceilings and relative regression thresholds for every release-gated metric.

### B. Mandatory work-product expansion
#### B.1 — Benchmark harness and environment manifest.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Benchmark harness and environment manifest.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Latency/throughput/startup/CPU/memory/network/power baselines.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Latency/throughput/startup/CPU/memory/network/power baselines.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — p50/p95/p99/worst thresholds.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **p50/p95/p99/worst thresholds.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Steady/burst/overload/scale/recovery and per-tenant/workload measurements.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Steady/burst/overload/scale/recovery and per-tenant/workload measurements.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-023 — Performance-regression release gate

**Priority:** High  
**Audit gap:** No automated release gate compares benchmark results with approved thresholds.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C070` | **missing** | Block releases that regress approved Existing service-mesh layer startup, density, throughput, or tail-latency thresholds. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-023, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-023 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Choose the canonical benchmark scenarios and metrics that are release-gating rather than informational.
- [ ] Version baseline results and associate them with source commit, dependency/BOM digest, configuration digest, hardware class, and benchmark harness version.
- [ ] Define allowed absolute and relative regression thresholds, including treatment of statistically insignificant noise.
- [ ] Require a minimum sample count/repetition count and reject comparison when environments are materially non-comparable.
- [ ] Implement CI/release comparison producing machine-readable pass/fail plus metric deltas.
- [ ] Fail releases on threshold regression unless a time-bounded approved waiver exists in the exception register.
- [ ] Prevent baseline “reset” from concealing a regression by requiring explicit approval and rationale for baseline changes.
- [ ] Archive raw/aggregate benchmark artifacts and comparison result with release evidence.
- [ ] Add trend reporting so gradual regressions across several individually acceptable releases remain visible.

### B. Mandatory work-product expansion
#### B.1 — Baseline artifacts.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Baseline artifacts.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Allowed-regression policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Allowed-regression policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — CI/release job that blocks threshold regressions.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **CI/release job that blocks threshold regressions.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-024 — Health/readiness/status surface

**Priority:** High  
**Audit gap:** No endpoint/command exposes health, readiness, active version/config, dependency status, and capability set.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C071` | **missing** | Expose Existing service-mesh layer health, readiness, version, configuration, dependency status, and active capability set. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-024, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-024 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define a versioned machine-readable status schema with separate liveness, readiness, degradation, dependency, configuration, and capability fields.
- [ ] Expose component version, build/release identifier, active configuration revision/digest, schema/interface versions, and compatibility state.
- [ ] Expose dependency status for security plane, authorization, observability, mesh/control plane, and any persistence/audit sink without leaking credentials/endpoints that should remain private.
- [ ] Expose capacity/saturation indicators needed to explain not-ready or degraded states.
- [ ] Define readiness rules that reflect ability to perform safety-critical operations rather than merely import/start successfully.
- [ ] Define privileged versus public status fields and redact tenant identities, tokens, secrets, certificate material, and sensitive topology.
- [ ] Provide deterministic exit codes for CLI status/health checks if a command surface is used.
- [ ] Test status during startup, healthy operation, each degraded dependency mode, configuration failure, quarantine, overload, and recovery.
- [ ] Ensure health/status handlers are bounded and cannot themselves create dependency cascades or large allocations.

### B. Mandatory work-product expansion
#### B.1 — Machine-readable status model.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Machine-readable status model.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Health/readiness semantics.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Health/readiness semantics.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Version/config/dependency/capability fields with redaction policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Version/config/dependency/capability fields with redaction policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-025 — Metrics, structured logging, trace propagation, and diagnostic privacy controls

**Priority:** High  
**Audit gap:** The contract names three signals but contains no telemetry implementation for rate/errors/latency/saturation/resource use, stable structured logs, trace propagation, or safe high-cardinality diagnostics.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C072` | **missing** | Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use. |
| `INV-58-C073` | **missing** | Emit structured logs with stable node, tenant, workload, component, and operation identifiers. |
| `INV-58-C074` | **missing** | Propagate trace context across all relevant Existing service-mesh layer boundaries. |
| `INV-58-C075` | **missing** | Expose high-cardinality diagnostic detail safely without leaking tenant or secret data. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-025, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-025 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define a metric catalog with stable names, type, unit, description, label set, aggregation, and owner.
- [ ] At minimum instrument request/reconcile/identity/bypass rates, errors by reason, latency distributions, saturation, retry attempts/owner, registry usage, audit pipeline health, and dependency health.
- [ ] Enforce a bounded label-cardinality policy; prohibit raw route/identity/tenant values as labels unless an explicit cardinality/privacy design approves them.
- [ ] Define a structured logging schema with timestamp, severity, event code, correlation/trace ID, component/release/config revision, safe scope identifiers, and stable reason codes.
- [ ] Propagate W3C trace context or the project-approved equivalent across adjacent layer boundaries and preserve a consistent request correlation identifier.
- [ ] Create span/event conventions showing retry ownership and each actual attempt without double counting mesh/runtime attempts.
- [ ] Redact secrets, certificates, raw identity payloads, personal/sensitive values, and unbounded request content from diagnostics.
- [ ] Define sampling behavior that never samples away mandatory security-audit events and does not bias SLO/error measurements.
- [ ] Test malformed trace headers, missing context, context injection, oversized baggage, redaction, and high-cardinality attacks.
- [ ] Provide export adapters or documented integration contract for the unified observability layer.

### B. Mandatory work-product expansion
#### B.1 — Metric schema/export adapter.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Metric schema/export adapter.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Structured logging schema with stable identifiers.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Structured logging schema with stable identifiers.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Trace-context propagation rules/tests.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Trace-context propagation rules/tests.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — High-cardinality privacy/redaction controls.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **High-cardinality privacy/redaction controls.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-028 — Contract/integration/compatibility/fuzz certification expansion

**Priority:** High  
**Audit gap:** Schema tests exist, but full public-interface contract tests, adjacent-tier integration, platform/protocol compatibility, and fuzzing are incomplete.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C082` | **partial** | Create contract tests for every public Existing service-mesh layer interface. |
| `INV-58-C083` | **missing** | Create integration tests with every supported adjacent layer and execution tier. |
| `INV-58-C084` | **missing** | Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Existing service-mesh layer. |
| `INV-58-C085` | **missing** | Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Existing service-mesh layer. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-028, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-028 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Enumerate every public function/interface/schema and create contract tests for both direct Python implementation and real transport/adapter representations.
- [ ] Validate semantic invariants beyond JSON-schema shape, including retry single ownership, attempt budget, trust-domain rules, route limits, and bounded evidence.
- [ ] Build an adjacent-tier integration matrix across supported `pk_core`, security plane, authorization, observability, Istio/proxy, and Python/runtime versions.
- [ ] Define platform coverage for supported CPU architectures, operating systems, containers/VMs where applicable, and protocol/TLS profiles.
- [ ] Add property-based tests for retry arithmetic, registry revisions, capacity boundaries, identity parser invariants, and round-trip schema serialization.
- [ ] Fuzz untrusted route strings, SPIFFE/SAN inputs, schema payloads, error details, and configuration documents with bounded execution time/memory.
- [ ] Persist minimized crash/bug inputs as deterministic regression fixtures.
- [ ] Test old/new supported peer-version combinations and unknown optional fields to prove compatibility behavior.
- [ ] Publish a certification report identifying exactly which matrix cells were executed for a release.

### B. Mandatory work-product expansion
#### B.1 — Contract tests against real component adapters.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Contract tests against real component adapters.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Integration matrix across supported tiers.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Integration matrix across supported tiers.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — CPU/runtime/provider/protocol compatibility suite.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **CPU/runtime/provider/protocol compatibility suite.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Fuzz/property tests for schemas and untrusted identity/route inputs.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Fuzz/property tests for schemas and untrusted identity/route inputs.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-029 — Comprehensive concurrency/race test suite

**Priority:** High  
**Audit gap:** One concurrent bypass-detector test exists; registry/config/state race behavior is not stress-tested.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C086` | **partial** | Create concurrency and race-condition tests for shared/distributed Existing service-mesh layer state. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-029, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-029 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create stress tests for concurrent `RoutePolicyRegistry.get`, `snapshot`, and `migrate_route` operations across the route-capacity boundary.
- [ ] Test simultaneous migrations of the same route and define the accepted conflict semantics (serialize, compare-and-swap, last-writer prohibited, etc.).
- [ ] Test simultaneous config activation/rollback with route reads and migrations once the configuration subsystem is implemented.
- [ ] Test concurrent bypass observations, snapshot/export, capacity rollover, and any clear/acknowledge operation added later.
- [ ] Test race conditions around health/status reads during dependency/configuration state transitions.
- [ ] Run high-iteration randomized schedules with deterministic seeds and record any failure seed.
- [ ] Use race/thread sanitization tooling where available in integrated/native dependencies; supplement Python lock tests with invariant checks.
- [ ] Assert monotonic revisions, no lost updates, immutable snapshots, bounded memory, and no deadlocks/livelocks.
- [ ] If distributed controllers/persistence are added, add stale-leader, fencing-token, duplicate-delivery, and concurrent-recovery tests.

### B. Mandatory work-product expansion
#### B.1 — Concurrent route migration/read tests.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Concurrent route migration/read tests.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Race/stress runs with repeated scheduling.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Race/stress runs with repeated scheduling.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Distributed-state race tests if persistence/controller replication is added.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Distributed-state race tests if persistence/controller replication is added.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-031 — Benchmark/soak/burst/fleet and disaster/partition/reconnect test programs

**Priority:** High  
**Audit gap:** No long-duration, burst/fleet-scale, disaster, partition, reconnect, or degraded-control-plane suites are present.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C088` | **missing** | Create benchmark, soak, burst, and fleet-scale tests appropriate to Existing service-mesh layer. |
| `INV-58-C089` | **missing** | Create disaster, partition, reconnect, and degraded-control-plane tests. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-031, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-031 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define long-duration soak profiles exercising normal traffic, policy churn, identity churn, telemetry export, and periodic dependency disruptions.
- [ ] Define burst profiles with rapid route/tenant growth and synchronized request spikes approaching and exceeding capacity.
- [ ] Create synthetic fleet-scale topologies representing supported site/tenant/workload/route cardinalities without requiring production data.
- [ ] Monitor memory growth, file/socket/thread leaks, registry growth, GC behavior, latency drift, audit backlog, and metric-cardinality growth during soak.
- [ ] Test site/network partitions, asymmetric partitions, control-plane isolation, security-plane outage, observability outage, and partial reconnect.
- [ ] Test reconnect/reconciliation for duplicate/stale events, configuration revisions, route ownership, and identity/trust bundle updates.
- [ ] Test disaster restart from empty local state using documented reconstruction/restore procedures.
- [ ] Measure recovery point/recovery time objectives where durable state exists and verify no isolation/security invariant is relaxed to recover faster.
- [ ] Archive scenario, topology, duration, load generator seed, faults, telemetry, and result summary as release or scheduled-certification evidence.

### B. Mandatory work-product expansion
#### B.1 — Benchmark + soak profiles.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Benchmark + soak profiles.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Fleet-scale synthetic topology.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Fleet-scale synthetic topology.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Partition/reconnect/degraded-control-plane scenarios with recovery assertions.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Partition/reconnect/degraded-control-plane scenarios with recovery assertions.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-033 — Complete production SLO/error-budget/support commitment package

**Priority:** High  
**Audit gap:** Three SLOs are listed, but support hours/ownership/escalation and operational commitments are incomplete.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C091` | **partial** | Define production SLOs, error budgets, and support commitments for Existing service-mesh layer. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-033, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-033 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define exact SLI computation for bounded attempts, bypass detection latency, and identity-mapping latency, including numerator/denominator and exclusions.
- [ ] Define measurement source and aggregation window so SLO evaluation is reproducible from telemetry.
- [ ] Define error-budget amount, burn policy, freeze criteria, and who can approve continued rollout while budget is exhausted.
- [ ] Clarify zero-budget SLO operational behavior: what constitutes any violation, how quickly it pages, and what release/rollback action follows.
- [ ] Define service/support hours, primary/secondary on-call roles, response targets by incident severity, and escalation timeout.
- [ ] Define ownership boundaries with incumbent mesh, security plane, authorization, and observability teams so incidents are not bounced between layers.
- [ ] Create monthly/quarterly SLO review outputs and require action items for recurring burn or measurement gaps.
- [ ] Test SLO queries/calculations against synthetic known-good and known-bad telemetry fixtures.

### B. Mandatory work-product expansion
#### B.1 — SLO measurement definitions.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **SLO measurement definitions.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Error-budget policy and burn handling.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Error-budget policy and burn handling.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Support/on-call commitments and ownership.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Support/on-call commitments and ownership.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-034 — Canary/staged rollout, tested rollback/emergency-disable, and full day-0/day-1/day-2 runbooks

**Priority:** High  
**Audit gap:** README has short lifecycle bullets but not executable rollout/runbook procedures.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C092` | **partial** | Define canary, staged rollout, rollback, and emergency-disable procedures for Existing service-mesh layer. |
| `INV-58-C096` | **partial** | Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-034, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-034 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define staged rollout units such as test, canary tenant/site, limited percentage, regional/site wave, and general availability.
- [ ] Define entry/exit criteria for each stage using health, SLO, security, compatibility, and performance signals.
- [ ] Define automatic halt/rollback thresholds and manual approval points; specify which conditions require immediate emergency disable.
- [ ] Provide exact rollback procedure for configuration revision, route migration, package/release, and dependency-version changes.
- [ ] Provide emergency freeze/disable procedure that is scoped, authenticated, audited, reversible, and preserves diagnostic evidence.
- [ ] Document Day-0 prerequisites/bootstrap, trust/config setup, compatibility verification, baseline evidence, and preflight.
- [ ] Document Day-1 rollout, canary verification, progressive promotion, monitoring, approval, and rollback steps.
- [ ] Document Day-2 operations: routine health review, capacity, SLO/error budget, certificate/trust rotation, dependency patching, incident response, backup/reconstruction, and deprecation.
- [ ] Include decision trees for retry storm, bypass spike, identity mapping failure, incompatible peer, audit outage, and configuration activation failure.
- [ ] Exercise the runbooks in a non-production environment and capture command output/screenshots/log evidence proving the procedures are executable.

### B. Mandatory work-product expansion
#### B.1 — Canary/stage promotion criteria.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Canary/stage promotion criteria.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Rollback and emergency-disable commands with verification.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Rollback and emergency-disable commands with verification.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Detailed day-0/day-1/day-2 procedures and decision trees.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Detailed day-0/day-1/day-2 procedures and decision trees.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-035 — Supported-version compatibility matrix

**Priority:** High  
**Audit gap:** No current matrix covers component, `pk_core`, Istio/proxy, SPIFFE/TLS profile, Python, and adjacent component versions.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C093` | **missing** | Maintain a supported-version compatibility matrix for Existing service-mesh layer and adjacent dependencies. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-035, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-035 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create a machine-readable matrix covering INV-58 version, `pk_core`, Python, Istio control plane, data-plane proxy, SPIFFE/TLS profile, and each adjacent component.
- [ ] Represent minimum/maximum/exact supported ranges, known incompatible combinations, deprecation date, EOL date, and notes.
- [ ] Define allowed skew during rolling upgrades separately from steady-state supported combinations.
- [ ] Add matrix cells for platform/CPU/OS where behavior or packaging differs.
- [ ] Generate CI jobs from the matrix where practical so documentation and tested combinations cannot silently diverge.
- [ ] Fail packaging/release if declared supported combinations lack required certification evidence.
- [ ] Publish upgrade-order guidance derived from compatibility constraints.
- [ ] Version the matrix and bind its digest to release acceptance records.

### B. Mandatory work-product expansion
#### B.1 — Machine-readable compatibility matrix.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Machine-readable compatibility matrix.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Supported/deprecated/EOL states.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Supported/deprecated/EOL states.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Automated matrix validation in CI.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Automated matrix validation in CI.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-036 — Patching, vulnerability-response, and EOL SLAs

**Priority:** High  
**Audit gap:** No vulnerability intake/severity/remediation or EOL timing policy is included.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C094` | **missing** | Define patching, vulnerability response, and end-of-life SLAs for Existing service-mesh layer. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-036, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-036 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define vulnerability intake sources for Python packages, `pk_core`, Istio/proxy, TLS libraries, base images/OS, and other runtime dependencies.
- [ ] Define severity/risk triage incorporating exploitability, exposure, compensating controls, tenant impact, and supply-chain provenance.
- [ ] Define maximum acknowledgement, mitigation, patch, rebuild, and release timelines by severity.
- [ ] Define emergency release process for actively exploited or trust-critical vulnerabilities, including compatibility and rollback minimum checks.
- [ ] Automate dependency/SBOM scanning and flag unsupported/EOL dependencies even when no current CVE is known.
- [ ] Define responsible owner for vulnerability decisions and security communication/advisory process.
- [ ] Define version support window and EOL notification cadence for INV-58 and tightly coupled dependencies.
- [ ] Require documented exception with owner/expiry for any vulnerability or EOL dependency carried beyond SLA.
- [ ] Capture scan results and remediation status in release evidence.

### B. Mandatory work-product expansion
#### B.1 — Security response SLA by severity.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Security response SLA by severity.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Patch/rebuild/release process.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Patch/rebuild/release process.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Dependency CVE monitoring and EOL policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Dependency CVE monitoring and EOL policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-037 — Backup/restore/migration/reconstruction procedures

**Priority:** High  
**Audit gap:** The in-memory registry/evidence state has no stated durability class or reconstruction/restore procedure.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C095` | **missing** | Provide backup, restore, migration, or reconstruction procedures for Existing service-mesh layer state where applicable. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-037, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-037 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Classify each state object: route registry, active configuration, configuration history, bypass evidence, audit records, telemetry buffers, compatibility/BOM data, and release evidence as ephemeral, reconstructable, or durable.
- [ ] For reconstructable state, document authoritative source and deterministic reconstruction order and verify reconstruction from an empty local state.
- [ ] For durable state, define backup scope, frequency, encryption, integrity check, retention, location/residency, and access control.
- [ ] Define restore procedure with version compatibility checks and validation before the restored state becomes active.
- [ ] Define migration procedure for schema/version changes, including forward migration, rollback/downgrade limits, and interrupted migration recovery.
- [ ] Ensure restore/migration does not bypass tenant isolation, signature/provenance checks, or monotonic revision/fencing rules.
- [ ] Test corrupted/missing backup, partial restore, stale backup, wrong-environment backup, and incompatible-version backup handling.
- [ ] Periodically perform restore/reconstruction drills and record measured RPO/RTO or equivalent objectives.
- [ ] Bind backup/reconstruction responsibility and runbook to operational ownership.

### B. Mandatory work-product expansion
#### B.1 — Classify state as ephemeral/reconstructable/durable.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Classify state as ephemeral/reconstructable/durable.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Backup/restore or deterministic reconstruction steps.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Backup/restore or deterministic reconstruction steps.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Migration/version-change procedure and validation.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Migration/version-change procedure and validation.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-038 — Incident severity, paging, escalation, containment, and recovery procedure

**Priority:** High  
**Audit gap:** No incident-response runbook exists for retry storms, identity mapping failures, mesh bypass, or policy conflicts.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C097` | **missing** | Define incident severity, paging, escalation, containment, and recovery procedures. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-038, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-038 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define incident severity levels using impact, tenant scope, security exposure, SLO violation, bypass/retry amplification, and recovery complexity.
- [ ] Define paging triggers for retry storm, bounded-attempt violation, mesh-bypass spike, identity mapping failure, trust-service failure, unauthorized policy/config changes, and split-brain/stale controller conditions.
- [ ] Define primary/secondary escalation ownership and time-based escalation chain.
- [ ] Create first-response containment steps that prioritize stopping amplification or unauthorized change while preserving forensic evidence.
- [ ] Define safe use of quarantine, route freeze, rollback, config rollback, dependency isolation, and emergency disable for each incident class.
- [ ] Define recovery verification: effective attempt budget, identity path, bypass status, audit continuity, configuration/release version, and SLO recovery.
- [ ] Define communications and cross-team handoff with mesh/security/authorization/observability owners without exposing sensitive incident details unnecessarily.
- [ ] Capture timeline, relevant correlation IDs, config/release digests, audit-chain head, fault symptoms, decisions, and evidence for post-incident review.
- [ ] Run tabletop and technical exercises for the four named primary scenarios plus at least one combined dependency/security failure.
- [ ] Feed post-incident action items back into threat model, regression tests, runbooks, and waiver/technical-debt registers.

### B. Mandatory work-product expansion
#### B.1 — Severity definitions and triggers.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Severity definitions and triggers.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Paging/escalation ownership.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Paging/escalation ownership.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Containment/recovery steps and post-incident evidence capture.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Containment/recovery steps and post-incident evidence capture.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-041 — Standalone packaging/dependency/CI/release metadata

**Priority:** High  
**Audit gap:** The archive has no `pyproject.toml`/locked dependency manifest, no pin for `pk_core`, no CI definition, and no standalone license/notice. These may be inherited from a parent repository, but inheritance is not documented here.

### Requirement traceability

This work package is a repository-level audit finding rather than a direct `INV-58-Cxxx` checklist row; it still requires release evidence and RTM linkage as a supplemental control.

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-041, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-041 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Add or explicitly inherit `pyproject.toml` package metadata with package name/version, Python requirement, package-data inclusion for schemas/checklists, and deterministic build backend.
- [ ] Declare `pk_core` dependency/compatibility in package metadata or document parent-repository injection contract precisely.
- [ ] Add locked/constraints dependency inputs for development, test, integration, and release tooling; separate optional integration dependencies from the dependency-free core.
- [ ] Ensure built wheel/sdist/archive contains VERSION, schemas, checklist/audit artifacts required at runtime/release, and excludes caches/secrets/local state.
- [ ] Add CI stages for formatting/lint if adopted, compile/import, unit tests, optimized-mode tests, schema validation, artifact-consistency, RTM validation, security tests, integration tests, and release gate.
- [ ] Run supported Python/platform matrix and record skipped tests as explicit failures unless the skip is expected and justified.
- [ ] Add reproducible build/release metadata: source commit, dirty-tree detection, build timestamp policy, dependency/BOM digest, artifact SHA-256, and provenance attestation where supported.
- [ ] Add the applicable LICENSE and NOTICE files or an explicit documented inheritance mechanism; verify third-party notices from the SBOM.
- [ ] Document release tagging/versioning, changelog procedure, artifact signing/checksum generation, and publication/rollback process.
- [ ] Add CI checks ensuring `__version__`, `VERSION`, package metadata, changelog, schemas, and release record stay synchronized.

### B. Mandatory work-product expansion
#### B.1 — Document parent-repository inheritance or add packaging metadata.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Document parent-repository inheritance or add packaging metadata.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Pin/declare `pk_core` compatibility.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Pin/declare `pk_core` compatibility.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Add CI for tests/schema/compile/gate checks.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Add CI for tests/schema/compile/gate checks.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Document applicable license/notice and release provenance.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Document applicable license/notice and release provenance.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-022 — Optimization analysis, complete resource bounds, power/thermal characterization, and capacity model

**Priority:** Medium  
**Audit gap:** Some in-memory counts are bounded, but there is no systematic copy/hop/serialization analysis, optimization record, power/thermal data, or saturation/capacity model.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C065` | **missing** | Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Existing service-mesh layer. |
| `INV-58-C066` | **missing** | Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit. |
| `INV-58-C067` | **partial** | Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out. |
| `INV-58-C068` | **missing** | Measure power and thermal impact on constrained edge nodes where relevant. |
| `INV-58-C069` | **missing** | Define capacity models and saturation signals that predict when Existing service-mesh layer needs more resources. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-022, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-022 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Profile hot paths for copies, allocations, regex/URI parsing, locks, serialization/deserialization, telemetry emission, and route registry snapshots.
- [ ] Map every network/process hop and serialization boundary in the integrated request path and identify avoidable duplicate work.
- [ ] Document optimization decisions with before/after measurements; reject complexity-increasing changes that lack measurable benefit.
- [ ] Enumerate and bound all queues, buffers, registries, fan-out, thread/task counts, open connections, metric label sets, and audit buffers.
- [ ] Define behavior at each resource ceiling: reject, evict, compact, spill, sample, or shed; avoid silent truncation for security evidence.
- [ ] Create a capacity model linking tenant/workload/route cardinality and request rate to CPU, memory, telemetry, and control-plane load.
- [ ] Define saturation signals and headroom targets used by autoscaling or operator planning.
- [ ] For edge deployments, measure power/energy and thermal behavior under idle, normal, burst, and sustained saturation on representative hardware.
- [ ] Include CPU-frequency/throttling conditions when evaluating latency on thermally constrained devices.
- [ ] Validate capacity predictions against load tests and update the model when architecture or dependency versions change.

### B. Mandatory work-product expansion
#### B.1 — Profiling/optimization analysis.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Profiling/optimization analysis.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Explicit queue/buffer/concurrency/fan-out bounds.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Explicit queue/buffer/concurrency/fan-out bounds.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Edge power/thermal characterization when applicable.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Edge power/thermal characterization when applicable.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.4 — Capacity model and saturation signals.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Capacity model and saturation signals.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-026 — Complete decision explainability and release/infrastructure correlation

**Priority:** Medium  
**Audit gap:** Retry decisions now carry a reason string, but there is no comprehensive decision journal/operator explain view or correlation to release lineage/live topology.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C076` | **partial** | Record the reason for every automated decision made by Existing service-mesh layer. |
| `INV-58-C077` | **missing** | Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints. |
| `INV-58-C078` | **missing** | Correlate Existing service-mesh layer events with application release lineage and the live infrastructure graph. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-026, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-026 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define a decision-record schema for retry-owner selection, budget clamping, identity rejection, bypass flagging, migration activation, rollback, quarantine, and degraded-mode entry.
- [ ] Capture input summary, relevant policy/config revision, evaluated rules, selected outcome, stable reason code, timestamp, actor/source, and correlation ID.
- [ ] Ensure decision records explain the actual effective policy rather than exposing only the raw app/mesh configuration.
- [ ] Provide an operator-facing explain command/API that can answer “why did this route get this owner/budget/state?” without requiring log archaeology.
- [ ] Include current and previous revision where a change or rollback caused the outcome.
- [ ] Correlate decisions to release/build digest and deployed infrastructure/topology identity so historical behavior can be reconstructed.
- [ ] Protect explain output with the same tenant/scope authorization rules as the underlying policy/evidence.
- [ ] Keep reason codes stable and machine-readable while allowing human-readable text to evolve.
- [ ] Test deterministic explanations for identical inputs and explicit explanation changes when policy/config version changes.

### B. Mandatory work-product expansion
#### B.1 — Decision record schema for every automated action.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Decision record schema for every automated action.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Operator-readable explain command/view.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Operator-readable explain command/view.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Release artifact and infrastructure-graph correlation identifiers.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Release artifact and infrastructure-graph correlation identifiers.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-027 — Telemetry retention/export policy plus dashboards and alerts

**Priority:** Medium  
**Audit gap:** Retention, sampling, privacy, export, dashboards, and alert classification are absent.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C079` | **missing** | Define telemetry retention, sampling, privacy, and export policy. |
| `INV-58-C080` | **missing** | Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-027, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-027 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define retention periods separately for metrics, ordinary logs, traces, security audit, benchmark evidence, and release evidence.
- [ ] Define sampling policies and identify classes that must never be probabilistically dropped.
- [ ] Define export destinations, encryption/authentication, tenant segregation, regional/residency constraints, and behavior when exporters are unavailable.
- [ ] Define privacy classification and redaction/aggregation requirements before telemetry leaves the component/environment.
- [ ] Build dashboards for bounded attempts, bypass detection, identity handoff latency/failure, retry ownership distribution, saturation, dependency health, config/release revision, and audit pipeline health.
- [ ] Define alert conditions and runbook links for load/saturation, degraded dependency, security/policy rejection, mesh bypass, retry amplification, software defect, and suspected attack.
- [ ] Use burn-rate/multi-window alerting for SLOs where appropriate rather than noisy single-threshold alerts.
- [ ] Test alert routing and deduplication; ensure expected overload does not masquerade as an attack and authorization rejection does not masquerade as software failure.
- [ ] Version dashboards/alerts as code and validate metric/log field references in CI.

### B. Mandatory work-product expansion
#### B.1 — Retention/sampling/export/privacy policy.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Retention/sampling/export/privacy policy.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Dashboards for SLO and saturation.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Dashboards for SLO and saturation.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Alerts differentiating load, degradation, policy rejection, dependency failure, attack, and software defect.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Alerts differentiating load, degradation, policy rejection, dependency failure, attack, and software defect.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-039 — Recurring security/configuration/dependency/architecture review process

**Priority:** Medium  
**Audit gap:** No recurring review cadence, scope, owner, or evidence artifact is defined.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C098` | **missing** | Perform recurring access, policy, dependency, configuration, and architecture reviews. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-039, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-039 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Define recurring review cadences for security/threat model, configuration/defaults, dependencies/BOM/EOL, architecture/ADR, compatibility, SLO/capacity, and operational runbooks.
- [ ] Assign an accountable role and required reviewers for each review type.
- [ ] Define review inputs such as incidents, vulnerabilities, telemetry trends, waivers, architecture changes, dependency updates, and audit findings.
- [ ] Create versioned checklists and machine-readable review records with date, participants, findings, decisions, action owner, due date, and evidence links.
- [ ] Automatically flag overdue reviews and unresolved high-risk findings in release acceptance where applicable.
- [ ] Trigger out-of-cycle review when trust boundaries, interfaces, privilege requirements, persistence, mesh versions, or security dependencies materially change.
- [ ] Link review outcomes to ADRs, threat model, compatibility matrix, dependency policy, and waiver register rather than leaving findings in meeting notes.
- [ ] Retain review records according to governance/audit requirements.

### B. Mandatory work-product expansion
#### B.1 — Review cadence and responsible roles.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Review cadence and responsible roles.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Review checklist and output record.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Review checklist and output record.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Automatic reminders/release linkage if appropriate.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Automatic reminders/release linkage if appropriate.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## MC-040 — Exceptions, waivers, technical-debt, and deprecation register

**Priority:** Medium  
**Audit gap:** No governed register tracks temporary exceptions with owner, rationale, risk, and expiry.

### Requirement traceability

| Requirement | Audit status | Normative requirement |
|---|---|---|
| `INV-58-C099` | **missing** | Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates. |

### A. Specification and design controls
- [ ] Assign an accountable owner for MC-040, a primary implementer, required reviewers, and an escalation path; record them in the ownership/RTM artifacts.
- [ ] Write a normative design note for MC-040 defining scope, non-goals, trust boundaries, dependencies, state owned, inputs/outputs, failure semantics, and compatibility assumptions.
- [ ] Identify all security, isolation, residency, latency/SLO, capacity, and availability constraints that can override convenience or cost; record precedence explicitly.
- [ ] Define stable machine-readable identifiers for the new artifacts, states, reason/error codes, and verification evidence introduced by this work package.
- [ ] Define rollback/deactivation behavior before implementation; no irreversible production mutation may be introduced without an approved recovery path.
- [ ] Create a machine-readable exception/waiver/technical-debt/deprecation register with stable IDs.
- [ ] Require type, affected requirement/control, scope, risk description, rationale, compensating controls, owner, approver, creation date, expiry/review date, and remediation plan.
- [ ] Forbid permanent waivers without a separately governed policy; every operational waiver must have an owner and expiry or scheduled review.
- [ ] Attach evidence showing why the normal control cannot currently be met and how residual risk is bounded.
- [ ] Link each partial/missing release requirement to a waiver when release is nevertheless permitted.
- [ ] Add CI/release checks that reject expired, ownerless, unapproved, malformed, or unknown waiver IDs.
- [ ] Define automatic warnings ahead of expiry and escalation for overdue remediation.
- [ ] Keep deprecated interface/version entries until explicit removal criteria and migration completion evidence are satisfied.
- [ ] Include open high-risk waivers in recurring security/architecture reviews and release summaries.

### B. Mandatory work-product expansion
#### B.1 — Machine-readable exception/waiver register.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Machine-readable exception/waiver register.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.2 — Owner + expiry required fields.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Owner + expiry required fields.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.
#### B.3 — Release gate rejecting expired/ownerless waivers.
- [ ] Convert this work product into one or more normative SHALL-level requirements with measurable acceptance criteria: **Release gate rejecting expired/ownerless waivers.**
- [ ] Define the concrete repository artifacts, API/schema/configuration objects, runtime state, owners, and dependencies needed to satisfy it; avoid leaving the requirement as prose only.
- [ ] Implement the behavior with explicit validation, bounded resource use, deterministic failure handling, and backward-compatibility treatment appropriate to the interface/state involved.
- [ ] Add positive-path, negative-path, boundary/limit, malformed-input, dependency-failure, and concurrency tests where applicable; include at least one test that proves the control fails safely.
- [ ] Add a machine-readable RTM entry linking the requirement/work product to implementation symbols/files, test IDs, evidence path/digest, owner, and release status.
- [ ] Capture release evidence proving the implemented artifact/version was the one tested and that the acceptance criterion was satisfied.

### C. Security, resilience, and isolation review
- [ ] Perform abuse-case review for spoofing, tampering, replay, privilege escalation, cross-tenant access, resource exhaustion, information leakage, and unsafe downgrade relevant to this component.
- [ ] Verify authentication and authorization boundaries for any newly introduced read or mutation operation; administrative controls must be deny-by-default.
- [ ] Verify secrets/credentials/private keys are referenced through approved secret mechanisms and cannot appear in ordinary configuration, logs, exceptions, status, fixtures, or release evidence.
- [ ] Verify tenant/site/environment/workload scoping is explicit and cross-scope reads/writes are rejected before state access.
- [ ] Define bounded behavior when dependencies are slow, unavailable, incompatible, or return malformed data; do not add hidden unbounded retry loops.
- [ ] Add audit events for security-sensitive state transitions, denials, overrides, rollback, quarantine, break-glass, and evidence-integrity failures introduced by this work package.
- [ ] Review new persisted state for encryption, integrity, replay, backup/restore, retention, and secure deletion requirements.
- [ ] Record residual risks and link any accepted exception to a time-bounded waiver with owner and expiry.

### D. Verification and certification checklist
- [ ] Unit tests cover all branch/outcome classes added by this work package and assert semantic invariants rather than only successful execution.
- [ ] Boundary tests cover minimum, maximum, just-below, just-above, empty, malformed, duplicated, stale, and conflicting inputs where meaningful.
- [ ] Failure-injection tests verify safe behavior for dependency timeout/unavailability, cancellation, partial progress, and restart during mutation where applicable.
- [ ] Concurrency tests cover simultaneous read/write/update/rollback paths and prove monotonic revision/no-lost-update/no-deadlock invariants where state is shared.
- [ ] Compatibility tests cover every supported old/new peer, schema, configuration, dependency, or artifact version relationship introduced by this component.
- [ ] Security tests cover both authorized success and unauthorized denial; no security control is considered verified solely by positive tests.
- [ ] Tests run under normal Python and optimized `python -O` modes where repository behavior is expected to be optimization-independent.
- [ ] If `pk_core` or another external dependency is required for conformance, execute the test in an environment where that dependency is present and pinned; do not accept a skip as pass.
- [ ] CI treats unexpected skips, warnings elevated by policy, schema drift, missing evidence, and stale generated artifacts as failures.
- [ ] A reviewer independent of the primary implementation confirms acceptance evidence matches the actual packaged source/version.

### E. Operationalization and evidence
- [ ] Update README/architecture/runbook content to describe the implemented behavior, operator-visible states, configuration, failure modes, and rollback procedure.
- [ ] Update `CHANGELOG.md` with externally observable behavior, security changes, compatibility impact, migration instructions, and known residual limitations.
- [ ] Update the compatibility matrix/BOM when this work package adds or constrains dependency versions, protocols, platforms, or peer interfaces.
- [ ] Update metrics/logging/tracing/status surfaces so operators can detect both successful operation and the primary failure/degraded states introduced here.
- [ ] Add or update alerts/runbook links when the component can create a production-impacting condition requiring operator action.
- [ ] Update `MISSING_COMPONENTS.json`/post-audit status only after implementation and verification evidence exist; retain historical closure reference rather than deleting the finding without trace.
- [ ] Add release evidence with source digest, test result digest, relevant config/BOM/RTM digests, reviewer, and timestamp.
- [ ] Re-run repository unit/schema/audit tests and the production gate after integration; archive the exact command/results used for closure.

### Definition of done
- [ ] All mapped missing/partial requirements for this work package have an implemented or explicitly waived status backed by machine-readable evidence.
- [ ] No critical or high-risk negative/failure test for this work package is skipped, xfailed without approved reason, or dependent on an unavailable unpinned framework.
- [ ] RTM, audit artifacts, documentation, tests, package metadata, and release evidence agree on the same version/status and pass automated consistency checks.
- [ ] Rollback/recovery procedure has been executed successfully in a representative non-production environment when the component changes runtime state or production policy.
- [ ] Security/architecture reviewer signs off residual risk; any remaining exception has owner, compensating controls, and expiry.
- [ ] Post-implementation audit no longer reports this component as missing; any intentionally partial remainder is split into a new explicitly scoped work item rather than hidden.

---

## Final repository closure checklist
- [ ] Re-run all dependency-free unit/schema/audit tests from a clean checkout and a clean virtual environment.
- [ ] Run the full `pk_core` conformance and gate with the pinned supported `pk_core` version available; verify all 100 requirement findings are present and evidence-linked.
- [ ] Run adjacent-layer integration, security regression, concurrency, performance, fault-injection, soak/disaster, and compatibility suites required by the completed controls.
- [ ] Confirm zero unexpected test skips and zero missing evidence references; any approved exception must resolve to a non-expired waiver.
- [ ] Validate `CHECKLIST.json`, RTM, `MISSING_COMPONENTS.json`, schemas, README, changelog, VERSION/package metadata, BOM/SBOM, compatibility matrix, and release evidence for cross-artifact consistency.
- [ ] Generate immutable/signed release acceptance evidence and bind it to the exact source, artifacts, configuration/BOM/compatibility/RTM digests, and test results.
- [ ] Perform a fresh missing-components audit; require every prior MC-001..MC-041 item to be closed or explicitly superseded by a traceable approved work item.
- [ ] Package the release from a clean source tree, verify archive integrity/checksum, and retain the release evidence/checksum/provenance record together.

## Audit provenance

- Checklist generated from `INV58_v4.2.0_MISSING_COMPONENTS.json`.
- Source audit element/version: `INV-58` / `4.2.0`.
- Source audit date: `2026-09-22`.
- Source audit basis: Static repository inspection plus local dependency-free tests; external pk_core unavailable in this archive.
- This document is a remediation checklist, not evidence that any listed work has been completed.
