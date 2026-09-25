# INV-05 Current Control-State System
# Professional Missing-Components Implementation Checklist

**Baseline:** INV-05 v4.2.0 hardened reference/conformance package  
**Prepared:** 2026-09-22  
**Coverage:** 52 missing or externally required production components  
**Purpose:** Engineering execution, production-readiness review, release gating, security review, and evidence generation.

## Priority model

- **P0 — Certification blocker:** must be satisfied before the system can credibly claim trustworthy production readiness.
- **P1 — Required production capability:** required for production operation, resilience, interoperability, or supportability.
- **P2 — Hardening / scale / operability:** required for mature operation and sustained scale.
- **P3 — Governance / completeness:** documentation, accountability, and lifecycle completeness.

## Checklist usage rules

1. A checkbox is not complete merely because code exists; required tests and evidence must also exist.
2. “External dependency” means INV-05 must still define, version, test, monitor, and evidence the integration boundary.
3. Mandatory tests must fail closed when dependencies are absent; skipped tests do not count as evidence unless the skip is explicitly approved and scoped.
4. Every completed item should link to source revision, artifact digest, test result, owner, and reviewer where practical.
5. Security-sensitive implementation must use least privilege, deny-by-default authorization, secret redaction, and tamper-evident auditability.
6. Production certification should block on unresolved P0 items and on any P1 item required by the intended deployment topology.
7. Evidence should be machine-readable where feasible and retained with the release candidate without rebuilding the artifact.

---

## Component index

- **MC-001 [P0]** — pk_core framework/runtime dependency
- **MC-002 [P0]** — MASTER.md master prompt/workflow corpus
- **MC-003 [P0]** — Requirements-to-evidence traceability matrix
- **MC-004 [P0]** — Approved production backend/version pin
- **MC-005 [P0]** — Production backend adapter/client
- **MC-006 [P0]** — Persistent durable storage path
- **MC-007 [P0]** — Consensus/member-management integration
- **MC-008 [P1]** — Revision-aware read/list/range API
- **MC-009 [P1]** — Delete/tombstone semantics
- **MC-010 [P1]** — Full transaction success/failure branches
- **MC-011 [P1]** — Rich compare predicates
- **MC-012 [P0]** — Versioned typed wire schemas
- **MC-013 [P1]** — Structured machine-readable error model
- **MC-014 [P1]** — Streaming watch transport
- **MC-015 [P1]** — Watch session lifecycle and slow-consumer controls
- **MC-016 [P1]** — Typed event schema
- **MC-017 [P1]** — Consistent snapshot + relist protocol
- **MC-018 [P1]** — Lease/TTL/session ownership subsystem
- **MC-019 [P1]** — Compaction/retention controller
- **MC-020 [P1]** — Interface/resource limits
- **MC-021 [P0]** — Tenant/environment/site/workload isolation implementation
- **MC-022 [P0]** — Authentication / node and peer identity
- **MC-023 [P0]** — Authorization / capability policy
- **MC-024 [P0]** — Secrets/KMS/key-rotation integration
- **MC-025 [P0]** — Encryption in transit and at rest
- **MC-026 [P1]** — Timeout/cancellation/retry/idempotency contract
- **MC-027 [P1]** — Protocol/version negotiation and compatibility matrix
- **MC-028 [P1]** — Declarative configuration subsystem
- **MC-029 [P1]** — Deterministic production bootstrap
- **MC-030 [P1]** — Health/readiness/version/capability endpoints
- **MC-031 [P1]** — Graceful drain, freeze, quarantine, and emergency-disable controls
- **MC-032 [P1]** — Production metrics instrumentation
- **MC-033 [P1]** — Structured logging
- **MC-034 [P1]** — Distributed tracing
- **MC-035 [P2]** — Decision/explainability view
- **MC-036 [P2]** — Telemetry privacy/retention/export policy
- **MC-037 [P1]** — Dashboards and alert rules
- **MC-038 [P0]** — Tamper-evident security audit log
- **MC-039 [P0]** — Backup/restore integration and restore verification
- **MC-040 [P1]** — Disaster recovery / site failover plan
- **MC-041 [P1]** — GAP-05 replication/consistency integration
- **MC-042 [P1]** — Reproducible benchmark and capacity suite
- **MC-043 [P0]** — Linearizability/concurrency history checker
- **MC-044 [P1]** — Fault-injection/chaos suite
- **MC-045 [P1]** — Fuzzing and adversarial security tests
- **MC-046 [P1]** — Adjacent-layer integration and compatibility tests
- **MC-047 [P1]** — Public contract tests and conformance fixtures
- **MC-048 [P0]** — CI/release acceptance pipeline and machine-readable evidence
- **MC-049 [P0]** — Dependency lock, SBOM, vulnerability policy, artifact provenance/signing
- **MC-050 [P1]** — Deployment/upgrade/migration/rollback package
- **MC-051 [P1]** — Day-0/day-1/day-2 and incident runbooks
- **MC-052 [P2]** — Governance package: owner, ADR, exceptions, reviews, license

---

## MC-001 — pk_core framework/runtime dependency

**Priority:** P0  
**Objective:** Pin, resolve, verify, and operationalize the pk_core runtime so the complete assessment, evidence ledger, gate, and verifier execute reproducibly.

### Engineering checklist

- [ ] **MC-001-01** — Select an approved pk_core release and pin by immutable version plus artifact digest.
- [ ] **MC-001-02** — Document Python/runtime compatibility and minimum/maximum supported interpreter versions.
- [ ] **MC-001-03** — Provide an offline/reproducible installation path with dependency hashes.
- [ ] **MC-001-04** — Verify the full 100-item assessment executes with zero skipped checks caused by missing pk_core.
- [ ] **MC-001-05** — Add startup self-test that reports pk_core version and rejects unsupported versions.
- [ ] **MC-001-06** — Add CI matrix coverage for every supported pk_core/runtime combination.
- [ ] **MC-001-07** — Capture pk_core license and transitive dependency obligations in the SBOM.
- [ ] **MC-001-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-001-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-001-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-001-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-001-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-001-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-001-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-001-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-001-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-001-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-001-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-001-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-001-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-001-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-001-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-001-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-001-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-001-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-001-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-001-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-001-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-001-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-001-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-001-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-001-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-001-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-001-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-001-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-001-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-001-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-001-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-001-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-001-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-001-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-001-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-001-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-001-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-001-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-002 — MASTER.md master prompt/workflow corpus

**Priority:** P0  
**Objective:** Restore and govern the authoritative MASTER.md artifact, or formally remove it from the product contract and all traceability references.

### Engineering checklist

- [ ] **MC-002-01** — Recover the authoritative MASTER.md from the approved source of truth or issue a formal deprecation decision.
- [ ] **MC-002-02** — Add a content hash and provenance record for MASTER.md.
- [ ] **MC-002-03** — Validate every README/link/reference to MASTER.md during CI.
- [ ] **MC-002-04** — Define schema/section requirements for MASTER.md so incomplete documents fail validation.
- [ ] **MC-002-05** — Map MASTER.md sections to checklist requirements and implementation artifacts.
- [ ] **MC-002-06** — Require review/approval for changes that alter normative workflows or production gates.
- [ ] **MC-002-07** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-002-08** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-002-09** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-002-10** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-002-11** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-002-12** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-002-13** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-002-14** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-002-15** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-002-16** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-002-17** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-002-18** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-002-19** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-002-20** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-002-21** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-002-22** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-002-23** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-002-24** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-002-25** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-002-26** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-002-27** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-002-28** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-002-29** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-002-30** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-002-31** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-002-32** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-002-33** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-002-34** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-002-35** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-002-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-002-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-002-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-002-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-002-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-002-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-002-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-002-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-002-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-003 — Requirements-to-evidence traceability matrix

**Priority:** P0  
**Objective:** Create a machine-verifiable mapping from every checklist requirement to implementation, tests, evidence, ownership, status, and release gates.

### Engineering checklist

- [ ] **MC-003-01** — Create one row per C001-C100 requirement with unique immutable requirement ID.
- [ ] **MC-003-02** — Record implementation file/module/symbol references for every satisfied requirement.
- [ ] **MC-003-03** — Record test IDs and exact evidence artifact paths for every requirement.
- [ ] **MC-003-04** — Track owner, reviewer, status, exception ID, last-verified build, and evidence freshness.
- [ ] **MC-003-05** — Represent the matrix in a machine-readable format such as JSON/YAML/CSV and render Markdown from it.
- [ ] **MC-003-06** — Fail CI when a mandatory requirement has no evidence, stale evidence, contradictory status, or unresolved broken link.
- [ ] **MC-003-07** — Support bidirectional traceability from requirement→evidence and evidence→requirement.
- [ ] **MC-003-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-003-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-003-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-003-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-003-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-003-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-003-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-003-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-003-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-003-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-003-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-003-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-003-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-003-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-003-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-003-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-003-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-003-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-003-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-003-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-003-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-003-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-003-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-003-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-003-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-003-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-003-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-003-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-003-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-003-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-003-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-003-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-003-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-003-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-003-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-003-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-003-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-003-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-004 — Approved production backend/version pin

**Priority:** P0  
**Objective:** Define the supported production backend and exact version policy, including compatibility, integrity, lifecycle, and support constraints.

### Engineering checklist

- [ ] **MC-004-01** — Select the production backend and pin exact supported release(s), build flavor, and digest.
- [ ] **MC-004-02** — Document required backend features and minimum API/semantic guarantees.
- [ ] **MC-004-03** — Define an N/N-1 or explicit compatibility/support matrix.
- [ ] **MC-004-04** — Record backend configuration baseline, feature flags, and prohibited options.
- [ ] **MC-004-05** — Verify artifact checksums/signatures before deployment.
- [ ] **MC-004-06** — Define backend CVE response, upgrade cadence, EOL policy, and emergency patch procedure.
- [ ] **MC-004-07** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-004-08** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-004-09** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-004-10** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-004-11** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-004-12** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-004-13** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-004-14** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-004-15** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-004-16** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-004-17** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-004-18** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-004-19** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-004-20** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-004-21** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-004-22** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-004-23** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-004-24** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-004-25** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-004-26** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-004-27** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-004-28** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-004-29** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-004-30** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-004-31** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-004-32** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-004-33** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-004-34** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-004-35** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-004-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-004-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-004-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-004-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-004-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-004-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-004-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-004-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-004-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-005 — Production backend adapter/client

**Priority:** P0  
**Objective:** Implement the real control-state backend adapter with discovery, sessions, request translation, error handling, resilience, and observability.

### Engineering checklist

- [ ] **MC-005-01** — Define an adapter interface independent of the backend SDK.
- [ ] **MC-005-02** — Implement endpoint discovery, connection establishment, keepalive, pooling, and reconnect behavior.
- [ ] **MC-005-03** — Translate backend revisions, transactions, watches, compaction, leases, and errors into canonical control-state semantics.
- [ ] **MC-005-04** — Classify backend errors as retryable, terminal, authorization, validation, overload, or consistency failures.
- [ ] **MC-005-05** — Instrument every backend call with latency, outcome, retry count, target, and trace correlation.
- [ ] **MC-005-06** — Add integration tests against a real multi-node backend deployment.
- [ ] **MC-005-07** — Verify no backend-specific behavior leaks through the public contract unless explicitly documented.
- [ ] **MC-005-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-005-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-005-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-005-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-005-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-005-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-005-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-005-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-005-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-005-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-005-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-005-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-005-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-005-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-005-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-005-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-005-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-005-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-005-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-005-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-005-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-005-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-005-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-005-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-005-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-005-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-005-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-005-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-005-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-005-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-005-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-005-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-005-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-005-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-005-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-005-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-005-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-005-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-006 — Persistent durable storage path

**Priority:** P0  
**Objective:** Provide WAL/durable persistence, crash recovery, snapshotting, fsync policy, corruption handling, and durability verification.

### Engineering checklist

- [ ] **MC-006-01** — Define durability class for each acknowledged write and the exact point at which success may be returned.
- [ ] **MC-006-02** — Implement or configure write-ahead logging with checksummed records.
- [ ] **MC-006-03** — Define fsync/group-commit policy and quantify data-loss envelope under power failure.
- [ ] **MC-006-04** — Implement atomic snapshots with integrity metadata and generation/version identifiers.
- [ ] **MC-006-05** — Verify crash recovery after interruption at every critical persistence boundary.
- [ ] **MC-006-06** — Detect and surface truncated/corrupt WAL or snapshot data; never silently continue with ambiguous state.
- [ ] **MC-006-07** — Define disk-full and read-only-filesystem behavior.
- [ ] **MC-006-08** — Run persistence fault tests with abrupt process kill and host restart.
- [ ] **MC-006-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-006-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-006-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-006-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-006-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-006-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-006-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-006-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-006-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-006-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-006-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-006-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-006-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-006-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-006-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-006-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-006-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-006-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-006-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-006-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-006-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-006-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-006-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-006-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-006-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-006-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-006-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-006-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-006-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-006-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-006-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-006-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-006-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-006-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-006-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-006-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-006-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-006-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-007 — Consensus/member-management integration

**Priority:** P0  
**Objective:** Define and verify the external consensus/member-management contract covering quorum, leader/member lifecycle, membership changes, and partition safety.

### Engineering checklist

- [ ] **MC-007-01** — Document quorum assumptions and which operations require leader/quorum confirmation.
- [ ] **MC-007-02** — Define member add/remove/replace workflow including joint-consensus or equivalent safe transition.
- [ ] **MC-007-03** — Define behavior during minority partition, leader loss, quorum loss, and asymmetric connectivity.
- [ ] **MC-007-04** — Verify stale leaders/isolated members cannot commit conflicting control state.
- [ ] **MC-007-05** — Define member identity persistence and rejoin/replacement semantics.
- [ ] **MC-007-06** — Add integration tests for membership churn while reads/writes/watches are active.
- [ ] **MC-007-07** — Document ownership boundary: what INV-05 guarantees versus what the consensus layer guarantees.
- [ ] **MC-007-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-007-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-007-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-007-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-007-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-007-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-007-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-007-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-007-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-007-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-007-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-007-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-007-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-007-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-007-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-007-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-007-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-007-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-007-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-007-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-007-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-007-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-007-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-007-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-007-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-007-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-007-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-007-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-007-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-007-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-007-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-007-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-007-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-007-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-007-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-007-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-007-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-007-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-008 — Revision-aware read/list/range API

**Priority:** P1  
**Objective:** Implement version-aware point, prefix, range, paginated, and consistent snapshot reads with explicit revision semantics.

### Engineering checklist

- [ ] **MC-008-01** — Define point-read semantics for current and historical revisions.
- [ ] **MC-008-02** — Define prefix/range ordering, inclusive/exclusive boundaries, and pagination tokens.
- [ ] **MC-008-03** — Guarantee pagination from a stable snapshot or explicitly expose weaker semantics.
- [ ] **MC-008-04** — Return the revision associated with every response.
- [ ] **MC-008-05** — Define behavior for compacted, future, invalid, and unavailable revisions.
- [ ] **MC-008-06** — Add maximum page size and response-size enforcement.
- [ ] **MC-008-07** — Test concurrent writes during multi-page list operations.
- [ ] **MC-008-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-008-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-008-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-008-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-008-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-008-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-008-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-008-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-008-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-008-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-008-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-008-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-008-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-008-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-008-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-008-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-008-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-008-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-008-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-008-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-008-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-008-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-008-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-008-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-008-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-008-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-008-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-008-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-008-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-008-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-008-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-008-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-008-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-008-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-008-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-008-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-008-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-008-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-009 — Delete/tombstone semantics

**Priority:** P1  
**Objective:** Define and implement delete operations, tombstones, delete events, retention behavior, watch visibility, and compaction interaction.

### Engineering checklist

- [ ] **MC-009-01** — Define delete as an explicit operation distinct from writing an empty/null value.
- [ ] **MC-009-02** — Define tombstone schema, revision behavior, retention, and visibility.
- [ ] **MC-009-03** — Emit typed delete events through watch streams.
- [ ] **MC-009-04** — Define compare-and-delete transactional semantics.
- [ ] **MC-009-05** — Define delete behavior for absent keys and idempotent retries.
- [ ] **MC-009-06** — Test delete→recreate sequences and revision monotonicity.
- [ ] **MC-009-07** — Verify compaction removes obsolete tombstones only when safe for watch/relist semantics.
- [ ] **MC-009-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-009-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-009-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-009-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-009-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-009-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-009-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-009-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-009-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-009-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-009-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-009-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-009-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-009-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-009-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-009-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-009-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-009-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-009-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-009-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-009-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-009-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-009-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-009-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-009-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-009-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-009-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-009-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-009-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-009-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-009-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-009-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-009-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-009-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-009-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-009-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-009-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-009-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-010 — Full transaction success/failure branches

**Priority:** P1  
**Objective:** Implement complete compare/then/else transactional semantics with deterministic success and failure operation branches.

### Engineering checklist

- [ ] **MC-010-01** — Represent transaction compares, success ops, and failure ops in the canonical request schema.
- [ ] **MC-010-02** — Guarantee atomic evaluation and execution against one consistent revision.
- [ ] **MC-010-03** — Return branch selected, resulting revision, and per-operation results.
- [ ] **MC-010-04** — Define nesting/batching limits and prohibit ambiguous partial success.
- [ ] **MC-010-05** — Test false-compare execution of failure operations.
- [ ] **MC-010-06** — Test simultaneous contenders to prove only valid compare winners commit.
- [ ] **MC-010-07** — Define retry semantics so duplicate transaction submission cannot create unintended effects.
- [ ] **MC-010-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-010-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-010-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-010-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-010-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-010-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-010-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-010-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-010-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-010-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-010-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-010-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-010-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-010-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-010-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-010-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-010-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-010-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-010-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-010-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-010-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-010-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-010-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-010-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-010-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-010-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-010-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-010-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-010-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-010-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-010-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-010-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-010-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-010-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-010-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-010-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-010-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-010-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-011 — Rich compare predicates

**Priority:** P1  
**Objective:** Support typed compare predicates such as existence, value, version, lease/session ownership, create revision, and modification revision.

### Engineering checklist

- [ ] **MC-011-01** — Define typed predicates for key existence/non-existence.
- [ ] **MC-011-02** — Define comparisons on create revision, modification revision, logical version, and value.
- [ ] **MC-011-03** — Define lease/session/fencing-token comparisons where ownership matters.
- [ ] **MC-011-04** — Specify byte/string canonicalization for value comparisons.
- [ ] **MC-011-05** — Reject unsupported predicate/operator combinations before execution.
- [ ] **MC-011-06** — Test mixed predicate sets and short-circuit/atomic evaluation semantics.
- [ ] **MC-011-07** — Document which predicates are safe across backend implementations.
- [ ] **MC-011-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-011-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-011-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-011-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-011-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-011-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-011-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-011-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-011-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-011-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-011-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-011-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-011-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-011-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-011-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-011-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-011-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-011-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-011-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-011-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-011-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-011-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-011-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-011-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-011-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-011-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-011-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-011-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-011-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-011-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-011-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-011-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-011-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-011-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-011-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-011-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-011-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-011-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-012 — Versioned typed wire schemas

**Priority:** P0  
**Objective:** Define canonical versioned schemas/IDLs for TXN, WATCH, COMPACT, events, errors, and compatibility fixtures.

### Engineering checklist

- [ ] **MC-012-01** — Choose and document the canonical IDL/schema technology and code-generation toolchain.
- [ ] **MC-012-02** — Assign explicit schema versions and stable field numbers/identifiers.
- [ ] **MC-012-03** — Define unknown-field handling and forward/backward compatibility rules.
- [ ] **MC-012-04** — Define canonical TXN, WATCH, COMPACT, event, error, health, and capability messages.
- [ ] **MC-012-05** — Add golden binary/JSON vectors for every message type.
- [ ] **MC-012-06** — Run schema-breaking-change detection in CI.
- [ ] **MC-012-07** — Generate language bindings reproducibly and verify generated artifacts are clean.
- [ ] **MC-012-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-012-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-012-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-012-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-012-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-012-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-012-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-012-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-012-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-012-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-012-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-012-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-012-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-012-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-012-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-012-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-012-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-012-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-012-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-012-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-012-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-012-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-012-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-012-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-012-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-012-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-012-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-012-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-012-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-012-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-012-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-012-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-012-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-012-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-012-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-012-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-012-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-012-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-013 — Structured machine-readable error model

**Priority:** P1  
**Objective:** Provide stable error codes, details, retryability classifications, causal metadata, and transport-independent error semantics.

### Engineering checklist

- [ ] **MC-013-01** — Create a stable error namespace with immutable machine codes.
- [ ] **MC-013-02** — Separate user/input, conflict, compaction, unavailable, timeout, cancellation, quota, overload, authn, authz, and internal errors.
- [ ] **MC-013-03** — Include safe structured details such as revision, retry-after, limit name, or dependency class where appropriate.
- [ ] **MC-013-04** — Define transport mapping without changing semantic error identity.
- [ ] **MC-013-05** — Mark each error as retryable/non-retryable and idempotency-sensitive.
- [ ] **MC-013-06** — Prevent stack traces, secrets, backend internals, or tenant data from leaking to callers.
- [ ] **MC-013-07** — Add conformance tests for every error code and mapping.
- [ ] **MC-013-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-013-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-013-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-013-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-013-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-013-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-013-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-013-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-013-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-013-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-013-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-013-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-013-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-013-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-013-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-013-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-013-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-013-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-013-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-013-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-013-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-013-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-013-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-013-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-013-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-013-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-013-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-013-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-013-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-013-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-013-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-013-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-013-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-013-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-013-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-013-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-013-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-013-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-014 — Streaming watch transport

**Priority:** P1  
**Objective:** Implement long-lived ordered watch streaming with heartbeats, cancellation, reconnect semantics, and transport-level correctness.

### Engineering checklist

- [ ] **MC-014-01** — Define the watch stream open request including key/range filter, start revision, event filters, and progress options.
- [ ] **MC-014-02** — Guarantee event ordering within the documented scope.
- [ ] **MC-014-03** — Send periodic progress/heartbeat frames without fabricating state changes.
- [ ] **MC-014-04** — Support explicit client cancellation and server shutdown/drain signaling.
- [ ] **MC-014-05** — Define transport keepalive and idle timeout policy.
- [ ] **MC-014-06** — Test reconnect after transient transport interruption.
- [ ] **MC-014-07** — Verify stream resumes without gaps or duplicate ambiguity using revision semantics.
- [ ] **MC-014-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-014-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-014-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-014-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-014-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-014-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-014-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-014-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-014-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-014-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-014-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-014-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-014-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-014-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-014-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-014-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-014-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-014-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-014-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-014-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-014-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-014-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-014-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-014-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-014-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-014-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-014-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-014-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-014-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-014-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-014-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-014-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-014-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-014-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-014-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-014-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-014-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-014-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-015 — Watch session lifecycle and slow-consumer controls

**Priority:** P1  
**Objective:** Add resume, cancellation, bounded buffering, backpressure, progress signals, quotas, and slow-consumer policies.

### Engineering checklist

- [ ] **MC-015-01** — Define opaque resume token or revision-based resumption semantics.
- [ ] **MC-015-02** — Bound server-side per-watch queues and total watch memory.
- [ ] **MC-015-03** — Implement backpressure or disconnect policy for slow consumers.
- [ ] **MC-015-04** — Expose slow-consumer and dropped/disconnected-watch metrics.
- [ ] **MC-015-05** — Enforce per-tenant/per-client watch and connection quotas.
- [ ] **MC-015-06** — Define progress notifications so clients can detect liveness without state changes.
- [ ] **MC-015-07** — Test consumers slower than producer rate and verify bounded resource use.
- [ ] **MC-015-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-015-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-015-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-015-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-015-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-015-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-015-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-015-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-015-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-015-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-015-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-015-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-015-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-015-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-015-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-015-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-015-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-015-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-015-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-015-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-015-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-015-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-015-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-015-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-015-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-015-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-015-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-015-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-015-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-015-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-015-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-015-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-015-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-015-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-015-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-015-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-015-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-015-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-016 — Typed event schema

**Priority:** P1  
**Objective:** Define a versioned event model for create/update/delete/lease/system events including identity, revision, transaction, and correlation metadata.

### Engineering checklist

- [ ] **MC-016-01** — Define event kinds including CREATE, UPDATE, DELETE, EXPIRE, and required system events.
- [ ] **MC-016-02** — Include key, new value, optional previous value, create revision, mod revision, and global/event revision.
- [ ] **MC-016-03** — Include transaction/request correlation ID and actor/tenant/workload identity where policy permits.
- [ ] **MC-016-04** — Include schema version and source/backend identity.
- [ ] **MC-016-05** — Define redaction rules for event values and metadata.
- [ ] **MC-016-06** — Specify ordering/deduplication semantics.
- [ ] **MC-016-07** — Create golden event fixtures and cross-language decoding tests.
- [ ] **MC-016-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-016-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-016-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-016-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-016-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-016-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-016-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-016-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-016-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-016-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-016-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-016-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-016-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-016-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-016-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-016-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-016-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-016-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-016-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-016-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-016-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-016-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-016-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-016-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-016-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-016-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-016-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-016-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-016-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-016-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-016-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-016-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-016-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-016-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-016-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-016-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-016-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-016-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-017 — Consistent snapshot + relist protocol

**Priority:** P1  
**Objective:** Implement a race-free snapshot/revision/relist/resume protocol that survives compaction and reconnects.

### Engineering checklist

- [ ] **MC-017-01** — Provide an atomic snapshot + snapshot-revision acquisition operation.
- [ ] **MC-017-02** — Define relist from snapshot and start-watch-at-next-revision sequence.
- [ ] **MC-017-03** — Handle compaction responses by restarting from a fresh snapshot without losing state.
- [ ] **MC-017-04** — Prevent races between final list page and watch start.
- [ ] **MC-017-05** — Define client algorithm in normative pseudocode.
- [ ] **MC-017-06** — Test continuous writers during snapshot/list/watch transitions.
- [ ] **MC-017-07** — Test repeated compactions and reconnects during relist.
- [ ] **MC-017-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-017-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-017-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-017-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-017-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-017-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-017-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-017-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-017-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-017-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-017-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-017-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-017-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-017-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-017-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-017-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-017-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-017-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-017-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-017-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-017-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-017-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-017-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-017-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-017-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-017-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-017-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-017-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-017-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-017-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-017-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-017-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-017-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-017-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-017-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-017-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-017-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-017-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-018 — Lease/TTL/session ownership subsystem

**Priority:** P1  
**Objective:** Implement lease objects, TTL/renewal/expiry, fencing, ownership transfer, session loss handling, and stale-owner prevention.

### Engineering checklist

- [ ] **MC-018-01** — Define lease/session object identity, owner, TTL, creation revision, renewal state, and fencing token.
- [ ] **MC-018-02** — Use monotonic/fenced ownership semantics so expired owners cannot continue mutating protected resources.
- [ ] **MC-018-03** — Define keepalive frequency, jitter, grace period, and expiry detection.
- [ ] **MC-018-04** — Define attached-key cleanup semantics on expiry.
- [ ] **MC-018-05** — Define behavior during network partition and session uncertainty.
- [ ] **MC-018-06** — Expose lease health and remaining TTL without relying on local wall-clock precision alone.
- [ ] **MC-018-07** — Test expiry, renewal loss, duplicate renewals, owner crash, and rapid reacquisition.
- [ ] **MC-018-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-018-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-018-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-018-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-018-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-018-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-018-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-018-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-018-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-018-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-018-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-018-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-018-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-018-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-018-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-018-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-018-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-018-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-018-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-018-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-018-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-018-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-018-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-018-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-018-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-018-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-018-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-018-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-018-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-018-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-018-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-018-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-018-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-018-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-018-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-018-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-018-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-018-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-019 — Compaction/retention controller

**Priority:** P1  
**Objective:** Provide policy-driven compaction scheduling, safety margins, retention controls, observability, and operator override.

### Engineering checklist

- [ ] **MC-019-01** — Define retention target by revision count, age, storage pressure, or supported combination.
- [ ] **MC-019-02** — Maintain a safety margin based on watch/recovery requirements.
- [ ] **MC-019-03** — Schedule compaction with rate limits and maintenance windows where required.
- [ ] **MC-019-04** — Prevent compaction past protected snapshots/checkpoints.
- [ ] **MC-019-05** — Expose current compacted revision and compaction lag.
- [ ] **MC-019-06** — Provide authenticated operator override with audit trail.
- [ ] **MC-019-07** — Test clients lagging across the compaction boundary.
- [ ] **MC-019-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-019-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-019-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-019-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-019-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-019-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-019-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-019-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-019-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-019-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-019-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-019-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-019-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-019-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-019-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-019-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-019-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-019-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-019-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-019-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-019-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-019-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-019-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-019-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-019-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-019-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-019-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-019-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-019-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-019-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-019-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-019-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-019-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-019-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-019-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-019-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-019-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-019-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-020 — Interface/resource limits

**Priority:** P1  
**Objective:** Define and enforce bounded request, key/value, transaction, connection, watch, queue, history, memory, and rate limits.

### Engineering checklist

- [ ] **MC-020-01** — Specify maximum key length and allowed encoding/character policy.
- [ ] **MC-020-02** — Specify maximum value/request/response/transaction size.
- [ ] **MC-020-03** — Specify maximum operations per transaction and predicates per transaction.
- [ ] **MC-020-04** — Specify watch/connection limits per identity and globally.
- [ ] **MC-020-05** — Specify history retention/memory/backlog limits.
- [ ] **MC-020-06** — Implement request-rate and concurrency controls with explicit overload errors.
- [ ] **MC-020-07** — Load-test every limit and verify graceful rejection rather than process instability.
- [ ] **MC-020-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-020-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-020-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-020-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-020-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-020-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-020-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-020-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-020-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-020-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-020-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-020-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-020-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-020-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-020-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-020-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-020-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-020-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-020-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-020-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-020-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-020-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-020-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-020-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-020-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-020-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-020-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-020-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-020-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-020-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-020-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-020-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-020-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-020-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-020-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-020-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-020-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-020-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-021 — Tenant/environment/site/workload isolation implementation

**Priority:** P0  
**Objective:** Enforce isolation boundaries across keyspaces, identity, authorization, network policy, quotas, telemetry, storage, and tests.

### Engineering checklist

- [ ] **MC-021-01** — Define canonical tenant/environment/site/workload namespace mapping.
- [ ] **MC-021-02** — Enforce namespace boundaries server-side; never rely on client-prefixed keys alone.
- [ ] **MC-021-03** — Bind authenticated identities to allowed namespaces.
- [ ] **MC-021-04** — Apply independent quotas and rate limits where isolation requires them.
- [ ] **MC-021-05** — Prevent cross-tenant leakage through watches, errors, metrics labels, logs, snapshots, and backups.
- [ ] **MC-021-06** — Apply network segmentation/service identity controls between trust zones.
- [ ] **MC-021-07** — Run adversarial cross-tenant read/write/watch tests.
- [ ] **MC-021-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-021-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-021-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-021-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-021-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-021-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-021-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-021-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-021-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-021-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-021-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-021-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-021-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-021-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-021-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-021-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-021-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-021-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-021-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-021-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-021-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-021-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-021-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-021-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-021-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-021-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-021-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-021-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-021-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-021-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-021-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-021-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-021-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-021-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-021-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-021-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-021-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-021-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-022 — Authentication / node and peer identity

**Priority:** P0  
**Objective:** Implement workload/node/peer identity, mTLS, certificate validation, issuance, rotation, revocation, and trust bootstrap.

### Engineering checklist

- [ ] **MC-022-01** — Select identity mechanism for nodes, services, workloads, and peers.
- [ ] **MC-022-02** — Require mutually authenticated transport for privileged control-plane communication.
- [ ] **MC-022-03** — Validate certificate/SPIFFE/identity chain, SAN/audience, validity, revocation, and purpose.
- [ ] **MC-022-04** — Automate issuance and rotation before expiry.
- [ ] **MC-022-05** — Define bootstrap trust anchors and recovery from trust-anchor rotation.
- [ ] **MC-022-06** — Reject expired, revoked, wrong-purpose, or wrong-tenant credentials.
- [ ] **MC-022-07** — Test clock skew and certificate rollover without service interruption.
- [ ] **MC-022-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-022-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-022-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-022-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-022-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-022-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-022-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-022-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-022-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-022-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-022-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-022-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-022-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-022-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-022-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-022-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-022-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-022-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-022-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-022-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-022-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-022-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-022-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-022-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-022-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-022-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-022-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-022-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-022-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-022-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-022-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-022-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-022-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-022-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-022-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-022-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-022-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-022-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-023 — Authorization / capability policy

**Priority:** P0  
**Objective:** Integrate deny-by-default authorization with RBAC/ABAC/capability checks, policy evaluation, auditability, and negative tests.

### Engineering checklist

- [ ] **MC-023-01** — Define authorization subjects, resources, actions, conditions, and decision schema.
- [ ] **MC-023-02** — Apply deny-by-default policy to every public and administrative operation.
- [ ] **MC-023-03** — Perform authorization after authentication and before state mutation or sensitive read.
- [ ] **MC-023-04** — Bind policies to tenant/site/workload boundaries.
- [ ] **MC-023-05** — Return non-sensitive denial details and emit auditable decision records.
- [ ] **MC-023-06** — Support policy versioning and atomic policy rollout/rollback.
- [ ] **MC-023-07** — Add negative tests for privilege escalation, confused deputy, wildcard scope, and stale policy.
- [ ] **MC-023-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-023-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-023-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-023-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-023-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-023-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-023-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-023-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-023-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-023-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-023-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-023-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-023-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-023-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-023-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-023-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-023-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-023-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-023-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-023-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-023-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-023-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-023-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-023-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-023-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-023-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-023-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-023-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-023-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-023-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-023-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-023-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-023-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-023-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-023-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-023-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-023-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-023-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-024 — Secrets/KMS/key-rotation integration

**Priority:** P0  
**Objective:** Integrate secrets and KMS services with key hierarchy, rotation, caching, outage behavior, access control, and redaction.

### Engineering checklist

- [ ] **MC-024-01** — Identify all secrets/keys and classify purpose, owner, rotation frequency, and exposure impact.
- [ ] **MC-024-02** — Use KMS/HSM-backed keys where required; avoid plaintext master keys in application configuration.
- [ ] **MC-024-03** — Define envelope-encryption/key hierarchy and key identifiers.
- [ ] **MC-024-04** — Automate key rotation and verify reads across key generations.
- [ ] **MC-024-05** — Define cached-key lifetime and fail-safe behavior during KMS outage.
- [ ] **MC-024-06** — Prevent secrets from entering logs, metrics, traces, crash dumps, or support bundles.
- [ ] **MC-024-07** — Audit every privileged key-management operation.
- [ ] **MC-024-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-024-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-024-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-024-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-024-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-024-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-024-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-024-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-024-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-024-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-024-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-024-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-024-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-024-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-024-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-024-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-024-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-024-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-024-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-024-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-024-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-024-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-024-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-024-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-024-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-024-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-024-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-024-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-024-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-024-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-024-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-024-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-024-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-024-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-024-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-024-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-024-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-024-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-025 — Encryption in transit and at rest

**Priority:** P0  
**Objective:** Define and verify approved cryptography for transport and persistence, including certificates, keys, rotation, and compliance evidence.

### Engineering checklist

- [ ] **MC-025-01** — Define minimum TLS version and approved cipher/key-exchange policy.
- [ ] **MC-025-02** — Require certificate hostname/service identity verification; prohibit insecure bypass flags.
- [ ] **MC-025-03** — Define at-rest encryption boundaries for WAL, snapshots, backups, and temporary files.
- [ ] **MC-025-04** — Document cryptographic key ownership, storage, rotation, and revocation.
- [ ] **MC-025-05** — Verify encryption configuration through automated runtime checks.
- [ ] **MC-025-06** — Test certificate/key rotation without data loss or prolonged outage.
- [ ] **MC-025-07** — Record compliance evidence for approved algorithms and configurations.
- [ ] **MC-025-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-025-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-025-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-025-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-025-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-025-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-025-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-025-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-025-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-025-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-025-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-025-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-025-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-025-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-025-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-025-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-025-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-025-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-025-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-025-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-025-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-025-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-025-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-025-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-025-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-025-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-025-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-025-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-025-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-025-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-025-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-025-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-025-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-025-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-025-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-025-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-025-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-025-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-026 — Timeout/cancellation/retry/idempotency contract

**Priority:** P1  
**Objective:** Specify deadlines, cancellation propagation, retry/backoff/jitter, idempotency, duplicate suppression, and operation safety classes.

### Engineering checklist

- [ ] **MC-026-01** — Assign default and maximum deadlines per operation class.
- [ ] **MC-026-02** — Propagate caller cancellation to backend and streaming operations.
- [ ] **MC-026-03** — Define exponential backoff with jitter and bounded attempt/time budgets.
- [ ] **MC-026-04** — Classify operations as naturally idempotent, token-idempotent, conditionally retryable, or non-retryable.
- [ ] **MC-026-05** — Provide idempotency/request identifiers for operations that may be safely replayed.
- [ ] **MC-026-06** — Respect server retry-after/overload signals.
- [ ] **MC-026-07** — Test retry storms, cancellation races, duplicate delivery, and deadline expiry at each layer.
- [ ] **MC-026-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-026-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-026-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-026-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-026-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-026-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-026-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-026-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-026-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-026-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-026-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-026-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-026-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-026-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-026-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-026-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-026-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-026-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-026-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-026-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-026-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-026-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-026-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-026-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-026-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-026-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-026-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-026-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-026-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-026-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-026-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-026-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-026-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-026-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-026-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-026-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-026-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-026-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-027 — Protocol/version negotiation and compatibility matrix

**Priority:** P1  
**Objective:** Implement negotiation and validate N/N-1 compatibility, downgrade behavior, migration paths, and mixed-version operation.

### Engineering checklist

- [ ] **MC-027-01** — Define protocol negotiation handshake and advertised capability set.
- [ ] **MC-027-02** — Document supported major/minor version compatibility policy.
- [ ] **MC-027-03** — Reject incompatible major versions with a stable error.
- [ ] **MC-027-04** — Define behavior when optional capabilities differ.
- [ ] **MC-027-05** — Test rolling upgrade with mixed N/N-1 versions.
- [ ] **MC-027-06** — Test downgrade/rollback after partial upgrade.
- [ ] **MC-027-07** — Maintain an executable compatibility matrix in CI.
- [ ] **MC-027-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-027-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-027-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-027-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-027-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-027-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-027-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-027-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-027-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-027-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-027-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-027-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-027-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-027-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-027-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-027-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-027-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-027-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-027-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-027-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-027-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-027-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-027-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-027-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-027-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-027-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-027-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-027-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-027-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-027-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-027-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-027-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-027-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-027-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-027-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-027-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-027-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-027-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-028 — Declarative configuration subsystem

**Priority:** P1  
**Objective:** Provide typed configuration, secure defaults, overlays, validation, provenance, atomic activation, rollback, and secret separation.

### Engineering checklist

- [ ] **MC-028-01** — Define a typed configuration schema with descriptions, defaults, constraints, and sensitivity markers.
- [ ] **MC-028-02** — Separate secrets from ordinary configuration.
- [ ] **MC-028-03** — Support environment/site overlays with deterministic precedence rules.
- [ ] **MC-028-04** — Validate the entire effective configuration before activation.
- [ ] **MC-028-05** — Record configuration provenance and immutable revision/hash.
- [ ] **MC-028-06** — Apply changes atomically or clearly classify restart-required settings.
- [ ] **MC-028-07** — Provide rollback to the previous known-good configuration.
- [ ] **MC-028-08** — Test malformed, conflicting, missing, and unsafe configuration.
- [ ] **MC-028-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-028-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-028-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-028-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-028-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-028-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-028-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-028-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-028-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-028-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-028-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-028-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-028-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-028-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-028-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-028-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-028-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-028-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-028-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-028-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-028-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-028-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-028-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-028-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-028-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-028-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-028-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-028-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-028-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-028-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-028-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-028-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-028-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-028-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-028-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-028-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-028-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-028-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-029 — Deterministic production bootstrap

**Priority:** P1  
**Objective:** Define a reproducible empty-node bootstrap process covering trust, backend, membership, policy, initialization, and verification.

### Engineering checklist

- [ ] **MC-029-01** — Define bootstrap prerequisites and immutable inputs.
- [ ] **MC-029-02** — Bootstrap trust before accepting privileged remote operations.
- [ ] **MC-029-03** — Initialize backend/storage and validate backend identity/version.
- [ ] **MC-029-04** — Create initial membership/namespace/policy state deterministically.
- [ ] **MC-029-05** — Use idempotent bootstrap steps so reruns are safe.
- [ ] **MC-029-06** — Emit a bootstrap completion artifact containing versions, digests, identities, and checks.
- [ ] **MC-029-07** — Test bootstrap on a pristine node with no hidden local state.
- [ ] **MC-029-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-029-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-029-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-029-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-029-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-029-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-029-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-029-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-029-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-029-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-029-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-029-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-029-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-029-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-029-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-029-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-029-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-029-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-029-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-029-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-029-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-029-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-029-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-029-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-029-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-029-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-029-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-029-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-029-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-029-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-029-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-029-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-029-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-029-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-029-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-029-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-029-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-029-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-030 — Health/readiness/version/capability endpoints

**Priority:** P1  
**Objective:** Expose liveness, readiness, dependency health, version/build identity, capability discovery, and stall/degradation state.

### Engineering checklist

- [ ] **MC-030-01** — Expose a shallow liveness check that does not mask deadlock/stall.
- [ ] **MC-030-02** — Expose readiness based on required dependencies, identity, backend access, and initialization.
- [ ] **MC-030-03** — Expose degraded state separately from fully ready/failed states.
- [ ] **MC-030-04** — Publish build version, commit, schema version, backend version, and capability set.
- [ ] **MC-030-05** — Protect detailed diagnostic endpoints from unauthorized disclosure.
- [ ] **MC-030-06** — Test health behavior during dependency loss, quorum loss, overload, and shutdown.
- [ ] **MC-030-07** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-030-08** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-030-09** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-030-10** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-030-11** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-030-12** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-030-13** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-030-14** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-030-15** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-030-16** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-030-17** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-030-18** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-030-19** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-030-20** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-030-21** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-030-22** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-030-23** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-030-24** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-030-25** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-030-26** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-030-27** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-030-28** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-030-29** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-030-30** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-030-31** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-030-32** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-030-33** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-030-34** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-030-35** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-030-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-030-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-030-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-030-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-030-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-030-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-030-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-030-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-030-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-031 — Graceful drain, freeze, quarantine, and emergency-disable controls

**Priority:** P1  
**Objective:** Implement admission freeze, write freeze, stream drain, quarantine, maintenance mode, safe shutdown, and break-glass control.

### Engineering checklist

- [ ] **MC-031-01** — Define admission freeze semantics separately for reads, writes, admin operations, and new watches.
- [ ] **MC-031-02** — Drain active watch streams with bounded grace period and terminal status.
- [ ] **MC-031-03** — Implement write freeze with clear operator-visible reason.
- [ ] **MC-031-04** — Implement quarantine that removes an unsafe node from serving without destroying forensic evidence.
- [ ] **MC-031-05** — Define maintenance mode and explicit exit criteria.
- [ ] **MC-031-06** — Provide authenticated, audited break-glass emergency disable.
- [ ] **MC-031-07** — Test shutdown while transactions and watch events are in flight.
- [ ] **MC-031-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-031-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-031-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-031-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-031-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-031-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-031-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-031-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-031-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-031-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-031-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-031-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-031-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-031-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-031-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-031-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-031-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-031-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-031-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-031-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-031-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-031-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-031-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-031-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-031-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-031-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-031-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-031-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-031-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-031-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-031-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-031-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-031-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-031-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-031-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-031-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-031-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-031-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-032 — Production metrics instrumentation

**Priority:** P1  
**Objective:** Instrument control-state behavior with stable counters, gauges, histograms, resource metrics, cardinality controls, and SLO metrics.

### Engineering checklist

- [ ] **MC-032-01** — Define metric names, units, types, labels, and ownership.
- [ ] **MC-032-02** — Instrument request rate, success/error classes, conflicts, and retries.
- [ ] **MC-032-03** — Instrument latency histograms by operation class with controlled cardinality.
- [ ] **MC-032-04** — Instrument watch count/backlog/lag/slow-consumer disconnects.
- [ ] **MC-032-05** — Instrument storage size, compaction revision/lag, backend latency, and resource saturation.
- [ ] **MC-032-06** — Expose process/runtime CPU, memory, FD, thread/task, and network indicators.
- [ ] **MC-032-07** — Define SLO-derived recording rules and test metric emission in integration tests.
- [ ] **MC-032-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-032-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-032-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-032-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-032-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-032-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-032-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-032-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-032-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-032-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-032-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-032-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-032-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-032-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-032-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-032-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-032-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-032-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-032-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-032-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-032-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-032-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-032-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-032-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-032-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-032-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-032-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-032-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-032-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-032-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-032-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-032-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-032-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-032-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-032-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-032-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-032-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-032-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-033 — Structured logging

**Priority:** P1  
**Objective:** Define stable structured logs with correlation, identity, revision, outcome, redaction, severity, and retention semantics.

### Engineering checklist

- [ ] **MC-033-01** — Define a versioned structured log schema.
- [ ] **MC-033-02** — Include timestamp, severity, component, operation, outcome, request/correlation ID, revision, and safe identity metadata.
- [ ] **MC-033-03** — Use stable event IDs for important lifecycle/security events.
- [ ] **MC-033-04** — Centralize redaction and sensitive-field classification.
- [ ] **MC-033-05** — Prevent high-volume hot loops from generating unbounded log storms.
- [ ] **MC-033-06** — Define log levels and dynamic level-change controls with auditability.
- [ ] **MC-033-07** — Add schema validation tests for emitted logs.
- [ ] **MC-033-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-033-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-033-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-033-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-033-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-033-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-033-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-033-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-033-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-033-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-033-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-033-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-033-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-033-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-033-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-033-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-033-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-033-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-033-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-033-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-033-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-033-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-033-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-033-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-033-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-033-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-033-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-033-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-033-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-033-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-033-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-033-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-033-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-033-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-033-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-033-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-033-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-033-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-034 — Distributed tracing

**Priority:** P1  
**Objective:** Implement trace-context propagation and spans across API, transaction, storage, watch, authorization, and backend boundaries.

### Engineering checklist

- [ ] **MC-034-01** — Accept and propagate standardized trace context across ingress/egress boundaries.
- [ ] **MC-034-02** — Create spans for API handling, authorization, transaction evaluation, backend calls, watch delivery, compaction, and recovery.
- [ ] **MC-034-03** — Attach safe attributes such as operation, result class, revision, and backend target.
- [ ] **MC-034-04** — Exclude secrets and unbounded/high-cardinality values.
- [ ] **MC-034-05** — Define head/tail sampling policy and error-biased retention where appropriate.
- [ ] **MC-034-06** — Propagate cancellation/deadline context through spans.
- [ ] **MC-034-07** — Verify end-to-end trace continuity in integration tests.
- [ ] **MC-034-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-034-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-034-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-034-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-034-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-034-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-034-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-034-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-034-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-034-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-034-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-034-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-034-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-034-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-034-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-034-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-034-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-034-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-034-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-034-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-034-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-034-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-034-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-034-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-034-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-034-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-034-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-034-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-034-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-034-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-034-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-034-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-034-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-034-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-034-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-034-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-034-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-034-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-035 — Decision/explainability view

**Priority:** P2  
**Objective:** Provide operator-readable explanations that connect requests and outcomes to state, policies, constraints, topology, and release lineage.

### Engineering checklist

- [ ] **MC-035-01** — Define an explanation record schema independent of human prose.
- [ ] **MC-035-02** — Capture request identity, relevant state revision, evaluated predicates/policies, constraints, and outcome.
- [ ] **MC-035-03** — Reference exact configuration/policy/release lineage used for the decision.
- [ ] **MC-035-04** — Redact sensitive state while preserving diagnostic usefulness.
- [ ] **MC-035-05** — Expose explanation retrieval to authorized operators only.
- [ ] **MC-035-06** — Support deterministic reconstruction where source evidence remains available.
- [ ] **MC-035-07** — Test that refusal/conflict/compaction explanations remain consistent with machine results.
- [ ] **MC-035-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-035-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-035-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-035-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-035-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-035-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-035-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-035-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-035-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-035-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-035-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-035-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-035-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-035-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-035-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-035-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-035-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-035-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-035-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-035-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-035-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-035-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-035-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-035-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-035-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-035-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-035-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-035-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-035-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-035-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-035-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-035-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-035-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-035-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-035-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-035-D02** — All mandatory P2 controls above pass in the intended production topology.
- [ ] **MC-035-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-035-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-036 — Telemetry privacy/retention/export policy

**Priority:** P2  
**Objective:** Define privacy classification, retention, sampling, cardinality limits, export controls, tenant safeguards, and deletion requirements.

### Engineering checklist

- [ ] **MC-036-01** — Classify every telemetry field as public, internal, confidential, tenant-sensitive, or secret-prohibited.
- [ ] **MC-036-02** — Define retention period per telemetry class.
- [ ] **MC-036-03** — Define aggregation/sampling rules and maximum label cardinality.
- [ ] **MC-036-04** — Specify approved exporters/destinations and residency restrictions.
- [ ] **MC-036-05** — Prevent tenant data from being exported across unauthorized boundaries.
- [ ] **MC-036-06** — Define deletion/expiration behavior for telemetry containing regulated data.
- [ ] **MC-036-07** — Audit configuration changes that alter telemetry export scope.
- [ ] **MC-036-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-036-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-036-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-036-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-036-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-036-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-036-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-036-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-036-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-036-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-036-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-036-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-036-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-036-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-036-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-036-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-036-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-036-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-036-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-036-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-036-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-036-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-036-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-036-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-036-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-036-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-036-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-036-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-036-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-036-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-036-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-036-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-036-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-036-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-036-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-036-D02** — All mandatory P2 controls above pass in the intended production topology.
- [ ] **MC-036-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-036-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-037 — Dashboards and alert rules

**Priority:** P1  
**Objective:** Create operational dashboards and alerts for load, latency, errors, conflicts, compaction, storage, dependency loss, overload, and security rejection.

### Engineering checklist

- [ ] **MC-037-01** — Create overview dashboard for availability, traffic, latency, errors, saturation, and backend health.
- [ ] **MC-037-02** — Create transaction/conflict dashboard with compare-failure and retry trends.
- [ ] **MC-037-03** — Create watch dashboard with active streams, lag, backlog, reconnects, and slow consumers.
- [ ] **MC-037-04** — Create storage/compaction dashboard with size, revision, retention, compaction duration, and pressure.
- [ ] **MC-037-05** — Create security dashboard for authn/authz denials and suspicious administrative operations.
- [ ] **MC-037-06** — Define alerts from SLO/error-budget impact rather than arbitrary thresholds where possible.
- [ ] **MC-037-07** — Link every actionable alert to a tested runbook.
- [ ] **MC-037-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-037-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-037-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-037-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-037-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-037-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-037-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-037-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-037-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-037-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-037-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-037-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-037-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-037-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-037-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-037-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-037-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-037-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-037-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-037-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-037-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-037-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-037-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-037-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-037-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-037-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-037-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-037-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-037-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-037-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-037-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-037-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-037-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-037-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-037-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-037-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-037-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-037-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-038 — Tamper-evident security audit log

**Priority:** P0  
**Objective:** Implement an append-only, integrity-protected audit trail for security-sensitive and administrative actions with verification and retention.

### Engineering checklist

- [ ] **MC-038-01** — Define mandatory auditable event classes: authn, authz, state mutation, compaction, config, membership, key management, and admin actions.
- [ ] **MC-038-02** — Use append-only storage with cryptographic integrity chaining/signing or equivalent tamper evidence.
- [ ] **MC-038-03** — Include trusted timestamp, actor, action, target, outcome, request ID, revision, and source identity.
- [ ] **MC-038-04** — Restrict audit-log write/read/delete privileges separately.
- [ ] **MC-038-05** — Define retention and immutable archival policy.
- [ ] **MC-038-06** — Provide an integrity-verification tool and scheduled verification job.
- [ ] **MC-038-07** — Test tamper detection, truncation detection, replay, and clock anomalies.
- [ ] **MC-038-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-038-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-038-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-038-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-038-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-038-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-038-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-038-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-038-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-038-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-038-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-038-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-038-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-038-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-038-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-038-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-038-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-038-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-038-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-038-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-038-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-038-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-038-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-038-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-038-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-038-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-038-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-038-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-038-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-038-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-038-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-038-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-038-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-038-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-038-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-038-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-038-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-038-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-039 — Backup/restore integration and restore verification

**Priority:** P0  
**Objective:** Define and test backup/restore contracts, schedules, encryption, retention, integrity checks, recovery objectives, and restore drills.

### Engineering checklist

- [ ] **MC-039-01** — Define backup scope for persistent state, metadata, configuration, identity material references, and required manifests.
- [ ] **MC-039-02** — Set explicit RPO/RTO targets and backup frequency.
- [ ] **MC-039-03** — Encrypt backups with independently governed keys.
- [ ] **MC-039-04** — Verify checksums/signatures and completeness before marking a backup successful.
- [ ] **MC-039-05** — Perform automated restore tests into an isolated environment.
- [ ] **MC-039-06** — Verify restored state consistency and watch/revision implications.
- [ ] **MC-039-07** — Document retention, legal hold, expiry, and secure deletion.
- [ ] **MC-039-08** — Run scheduled recovery exercises and record measured RPO/RTO.
- [ ] **MC-039-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-039-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-039-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-039-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-039-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-039-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-039-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-039-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-039-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-039-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-039-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-039-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-039-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-039-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-039-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-039-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-039-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-039-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-039-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-039-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-039-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-039-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-039-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-039-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-039-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-039-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-039-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-039-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-039-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-039-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-039-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-039-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-039-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-039-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-039-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-039-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-039-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-039-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-040 — Disaster recovery / site failover plan

**Priority:** P1  
**Objective:** Create and validate procedures for site loss, partition, provider loss, degraded operation, failover, failback, and residency constraints.

### Engineering checklist

- [ ] **MC-040-01** — Define disaster scenarios and declared service objectives for each.
- [ ] **MC-040-02** — Document decision authority and triggers for failover.
- [ ] **MC-040-03** — Define how quorum/consistency safety is preserved during site partition or loss.
- [ ] **MC-040-04** — Define DNS/service-discovery/routing changes required for failover.
- [ ] **MC-040-05** — Respect data residency/sovereignty constraints during replication and recovery.
- [ ] **MC-040-06** — Define failback and reconciliation after the primary site returns.
- [ ] **MC-040-07** — Run game-day exercises and capture measured recovery timelines and unresolved gaps.
- [ ] **MC-040-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-040-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-040-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-040-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-040-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-040-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-040-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-040-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-040-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-040-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-040-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-040-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-040-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-040-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-040-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-040-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-040-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-040-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-040-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-040-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-040-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-040-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-040-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-040-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-040-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-040-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-040-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-040-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-040-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-040-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-040-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-040-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-040-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-040-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-040-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-040-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-040-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-040-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-041 — GAP-05 replication/consistency integration

**Priority:** P1  
**Objective:** Implement and test the GAP-05 adapter/contract for replication, lag, fencing, conflict handling, and cross-site consistency.

### Engineering checklist

- [ ] **MC-041-01** — Define versioned handshake between INV-05 and GAP-05.
- [ ] **MC-041-02** — Define replicated object/event schema and ordering guarantees.
- [ ] **MC-041-03** — Expose replication lag and safe-read/write boundaries.
- [ ] **MC-041-04** — Implement fencing so stale sites cannot mutate authoritative state after failover.
- [ ] **MC-041-05** — Define conflict detection and resolution ownership.
- [ ] **MC-041-06** — Define reconnect/resync behavior after prolonged disconnection or compaction.
- [ ] **MC-041-07** — Run cross-site partition/heal tests with concurrent updates.
- [ ] **MC-041-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-041-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-041-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-041-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-041-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-041-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-041-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-041-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-041-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-041-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-041-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-041-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-041-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-041-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-041-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-041-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-041-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-041-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-041-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-041-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-041-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-041-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-041-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-041-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-041-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-041-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-041-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-041-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-041-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-041-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-041-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-041-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-041-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-041-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-041-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-041-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-041-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-041-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-042 — Reproducible benchmark and capacity suite

**Priority:** P1  
**Objective:** Build repeatable performance/capacity tests with latency percentiles, throughput, resource profiles, saturation points, and regression gates.

### Engineering checklist

- [ ] **MC-042-01** — Create fixed benchmark datasets/workloads and seed them deterministically.
- [ ] **MC-042-02** — Measure p50/p95/p99/max latency for reads, writes, transactions, watches, and compaction.
- [ ] **MC-042-03** — Measure sustained and burst throughput to saturation.
- [ ] **MC-042-04** — Record CPU, memory, storage IOPS/latency, network, FD, and queue utilization.
- [ ] **MC-042-05** — Test realistic key/value size distributions and watch fan-out.
- [ ] **MC-042-06** — Define capacity model and recommended operating headroom.
- [ ] **MC-042-07** — Store benchmark environment metadata and exact build/backend versions.
- [ ] **MC-042-08** — Fail release on statistically meaningful regression beyond approved thresholds.
- [ ] **MC-042-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-042-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-042-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-042-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-042-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-042-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-042-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-042-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-042-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-042-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-042-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-042-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-042-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-042-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-042-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-042-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-042-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-042-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-042-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-042-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-042-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-042-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-042-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-042-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-042-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-042-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-042-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-042-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-042-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-042-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-042-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-042-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-042-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-042-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-042-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-042-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-042-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-042-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-043 — Linearizability/concurrency history checker

**Priority:** P0  
**Objective:** Add history-based correctness verification under concurrency and faults using a Jepsen/Porcupine-style or equivalent checker.

### Engineering checklist

- [ ] **MC-043-01** — Capture operation histories with invoke/complete times, inputs, outputs, identities, and revisions.
- [ ] **MC-043-02** — Define the formal sequential specification for supported operations.
- [ ] **MC-043-03** — Run a proven linearizability checker against histories.
- [ ] **MC-043-04** — Generate high-concurrency mixed workloads with reads, writes, compare-and-swap, deletes, leases, and watches as applicable.
- [ ] **MC-043-05** — Inject process, node, and network failures during history generation.
- [ ] **MC-043-06** — Retain minimal counterexample histories when verification fails.
- [ ] **MC-043-07** — Run the checker in CI/nightly and before production certification.
- [ ] **MC-043-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-043-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-043-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-043-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-043-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-043-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-043-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-043-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-043-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-043-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-043-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-043-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-043-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-043-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-043-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-043-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-043-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-043-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-043-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-043-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-043-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-043-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-043-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-043-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-043-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-043-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-043-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-043-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-043-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-043-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-043-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-043-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-043-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-043-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-043-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-043-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-043-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-043-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-044 — Fault-injection/chaos suite

**Priority:** P1  
**Objective:** Exercise crash, stall, disk, network, dependency, and recovery faults with measurable safety/liveness/recovery assertions.

### Engineering checklist

- [ ] **MC-044-01** — Define a fault catalog covering process crash, pause/stall, disk full, I/O error, network delay/loss/partition, dependency outage, and resource exhaustion.
- [ ] **MC-044-02** — Attach a safety invariant and recovery expectation to every fault scenario.
- [ ] **MC-044-03** — Inject faults at deterministic points and randomized schedules.
- [ ] **MC-044-04** — Measure detection time, failover/recovery time, and data/availability impact.
- [ ] **MC-044-05** — Verify the system fails closed when correctness cannot be guaranteed.
- [ ] **MC-044-06** — Ensure chaos tooling cannot escape the intended test environment.
- [ ] **MC-044-07** — Persist experiment configuration, timeline, observations, and verdict as evidence.
- [ ] **MC-044-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-044-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-044-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-044-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-044-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-044-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-044-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-044-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-044-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-044-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-044-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-044-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-044-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-044-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-044-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-044-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-044-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-044-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-044-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-044-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-044-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-044-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-044-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-044-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-044-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-044-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-044-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-044-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-044-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-044-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-044-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-044-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-044-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-044-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-044-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-044-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-044-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-044-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-045 — Fuzzing and adversarial security tests

**Priority:** P1  
**Objective:** Fuzz schemas, keys, revisions, protocol frames, replay/spoof/injection paths, quotas, and privilege boundaries.

### Engineering checklist

- [ ] **MC-045-01** — Fuzz key encodings, lengths, Unicode, separators, and namespace edge cases.
- [ ] **MC-045-02** — Fuzz revision/version values including negative, overflow, stale, future, and malformed forms.
- [ ] **MC-045-03** — Fuzz schema/IDL frames and unknown/duplicate fields.
- [ ] **MC-045-04** — Test replay, spoofing, injection, deserialization abuse, and oversized payloads.
- [ ] **MC-045-05** — Fuzz authorization resource/action combinations for privilege-boundary mistakes.
- [ ] **MC-045-06** — Run resource-exhaustion fuzz cases under strict process limits.
- [ ] **MC-045-07** — Persist minimized crashing inputs and add them to regression corpora.
- [ ] **MC-045-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-045-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-045-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-045-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-045-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-045-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-045-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-045-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-045-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-045-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-045-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-045-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-045-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-045-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-045-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-045-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-045-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-045-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-045-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-045-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-045-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-045-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-045-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-045-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-045-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-045-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-045-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-045-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-045-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-045-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-045-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-045-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-045-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-045-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-045-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-045-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-045-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-045-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-046 — Adjacent-layer integration and compatibility tests

**Priority:** P1  
**Objective:** Validate executable integration with INV-04, GAP-05, INV-07, PLN-03, supported backends, runtimes, architectures, and site tiers.

### Engineering checklist

- [ ] **MC-046-01** — Define exact supported versions of INV-04, GAP-05, INV-07, PLN-03, backend, OS/runtime, and architecture.
- [ ] **MC-046-02** — Create executable integration environments for each required combination.
- [ ] **MC-046-03** — Validate startup/handshake/version negotiation between adjacent layers.
- [ ] **MC-046-04** — Validate error propagation and degraded behavior when each neighbor is unavailable or incompatible.
- [ ] **MC-046-05** — Run mixed-version rolling-upgrade scenarios.
- [ ] **MC-046-06** — Test site-tier/environment-specific configuration profiles.
- [ ] **MC-046-07** — Publish matrix results and block unsupported combinations from release promotion.
- [ ] **MC-046-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-046-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-046-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-046-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-046-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-046-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-046-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-046-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-046-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-046-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-046-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-046-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-046-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-046-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-046-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-046-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-046-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-046-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-046-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-046-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-046-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-046-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-046-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-046-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-046-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-046-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-046-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-046-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-046-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-046-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-046-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-046-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-046-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-046-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-046-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-046-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-046-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-046-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-047 — Public contract tests and conformance fixtures

**Priority:** P1  
**Objective:** Publish golden vectors and wire-level contract tests that independent implementations can execute for interoperability certification.

### Engineering checklist

- [ ] **MC-047-01** — Publish canonical valid request/response vectors for every public operation.
- [ ] **MC-047-02** — Publish invalid/boundary vectors and expected machine error codes.
- [ ] **MC-047-03** — Provide golden wire payloads for each supported schema version.
- [ ] **MC-047-04** — Provide deterministic conformance runner with machine-readable output.
- [ ] **MC-047-05** — Validate independent/client implementations against the same vectors.
- [ ] **MC-047-06** — Version fixtures without rewriting historical expected behavior.
- [ ] **MC-047-07** — Sign/release the conformance pack alongside the product artifact.
- [ ] **MC-047-08** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-047-09** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-047-10** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-047-11** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-047-12** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-047-13** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-047-14** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-047-15** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-047-16** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-047-17** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-047-18** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-047-19** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-047-20** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-047-21** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-047-22** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-047-23** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-047-24** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-047-25** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-047-26** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-047-27** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-047-28** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-047-29** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-047-30** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-047-31** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-047-32** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-047-33** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-047-34** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-047-35** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-047-36** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-047-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-047-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-047-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-047-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-047-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-047-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-047-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-047-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-047-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-048 — CI/release acceptance pipeline and machine-readable evidence

**Priority:** P0  
**Objective:** Automate build, unit, integration, security, performance, compatibility, provenance, and release gates with signed evidence output.

### Engineering checklist

- [ ] **MC-048-01** — Define mandatory CI stages: lint/static analysis, unit, optimized-runtime, integration, security, compatibility, performance, packaging, and provenance.
- [ ] **MC-048-02** — Fail closed on skipped mandatory tests.
- [ ] **MC-048-03** — Run tests in hermetic/reproducible environments from pinned dependencies.
- [ ] **MC-048-04** — Generate machine-readable test/evidence manifests tied to commit and artifact digest.
- [ ] **MC-048-05** — Require all P0/P1 acceptance gates before release promotion.
- [ ] **MC-048-06** — Sign acceptance evidence and store it immutably.
- [ ] **MC-048-07** — Support release candidate promotion without rebuilding the artifact.
- [ ] **MC-048-08** — Verify rollback artifacts with the same provenance and acceptance controls.
- [ ] **MC-048-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-048-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-048-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-048-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-048-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-048-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-048-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-048-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-048-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-048-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-048-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-048-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-048-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-048-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-048-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-048-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-048-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-048-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-048-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-048-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-048-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-048-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-048-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-048-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-048-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-048-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-048-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-048-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-048-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-048-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-048-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-048-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-048-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-048-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-048-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-048-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-048-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-048-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-049 — Dependency lock, SBOM, vulnerability policy, artifact provenance/signing

**Priority:** P0  
**Objective:** Establish deterministic dependencies, SBOM generation, vulnerability policy, signed provenance, artifact signing, and verification.

### Engineering checklist

- [ ] **MC-049-01** — Create lockfiles with exact versions and hashes for direct and transitive dependencies.
- [ ] **MC-049-02** — Generate CycloneDX/SPDX or equivalent SBOM for source and built artifacts.
- [ ] **MC-049-03** — Define vulnerability severity policy, SLA, exceptions, and compensating-control process.
- [ ] **MC-049-04** — Run malware/package-integrity and license-policy checks.
- [ ] **MC-049-05** — Generate SLSA-style provenance or equivalent build attestation.
- [ ] **MC-049-06** — Sign release artifacts and publish approved digests.
- [ ] **MC-049-07** — Verify signatures/provenance before installation and at deployment admission.
- [ ] **MC-049-08** — Test dependency-update workflow and reproducibility from a clean environment.
- [ ] **MC-049-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-049-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-049-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-049-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-049-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-049-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-049-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-049-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-049-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-049-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-049-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-049-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-049-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-049-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-049-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-049-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-049-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-049-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-049-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-049-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-049-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-049-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-049-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-049-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-049-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-049-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-049-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-049-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-049-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-049-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-049-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-049-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-049-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-049-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-049-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-049-D02** — All mandatory P0 controls above pass in the intended production topology.
- [ ] **MC-049-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-049-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-050 — Deployment/upgrade/migration/rollback package

**Priority:** P1  
**Objective:** Provide deployable service definitions, staged upgrades, migrations, canaries, rollback, and emergency disable procedures.

### Engineering checklist

- [ ] **MC-050-01** — Provide production service/container/package definitions with explicit resource and security settings.
- [ ] **MC-050-02** — Define preflight checks for configuration, identity, backend compatibility, and capacity.
- [ ] **MC-050-03** — Define staged rollout/canary policy and health gates.
- [ ] **MC-050-04** — Define schema/data migration ordering and backward compatibility.
- [ ] **MC-050-05** — Support rolling upgrades without violating watch/transaction semantics.
- [ ] **MC-050-06** — Define automated and manual rollback triggers.
- [ ] **MC-050-07** — Provide emergency-disable/feature-freeze controls.
- [ ] **MC-050-08** — Test upgrade→rollback across every supported adjacent version.
- [ ] **MC-050-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-050-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-050-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-050-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-050-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-050-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-050-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-050-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-050-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-050-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-050-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-050-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-050-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-050-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-050-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-050-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-050-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-050-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-050-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-050-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-050-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-050-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-050-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-050-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-050-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-050-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-050-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-050-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-050-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-050-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-050-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-050-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-050-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-050-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-050-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-050-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-050-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-050-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-051 — Day-0/day-1/day-2 and incident runbooks

**Priority:** P1  
**Objective:** Create operational runbooks covering installation, commissioning, normal operations, diagnosis, containment, recovery, escalation, and validation.

### Engineering checklist

- [ ] **MC-051-01** — Write Day-0 installation/bootstrap checklist with exact prerequisites and verification commands.
- [ ] **MC-051-02** — Write Day-1 commissioning checklist for health, security, backup, observability, and capacity validation.
- [ ] **MC-051-03** — Write Day-2 routine-operation procedures for rotation, compaction, scaling, upgrades, and audits.
- [ ] **MC-051-04** — Create incident diagnosis trees keyed by symptoms/alerts.
- [ ] **MC-051-05** — Define severity levels, paging/escalation, owner contacts/roles, and communications requirements.
- [ ] **MC-051-06** — Define containment actions that preserve evidence and correctness.
- [ ] **MC-051-07** — Define recovery validation steps before returning to service.
- [ ] **MC-051-08** — Exercise runbooks in drills and record time-to-diagnose/time-to-recover.
- [ ] **MC-051-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-051-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-051-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-051-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-051-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-051-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-051-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-051-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-051-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-051-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-051-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-051-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-051-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-051-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-051-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-051-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-051-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-051-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-051-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-051-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-051-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-051-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-051-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-051-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-051-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-051-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-051-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-051-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-051-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-051-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-051-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-051-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-051-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-051-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-051-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-051-D02** — All mandatory P1 controls above pass in the intended production topology.
- [ ] **MC-051-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-051-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

## MC-052 — Governance package: owner, ADR, exceptions, reviews, license

**Priority:** P2  
**Objective:** Establish accountability, architectural decisions, exception/debt records, recurring reviews, licensing, notices, and governance evidence.

### Engineering checklist

- [ ] **MC-052-01** — Name accountable engineering owner, security owner, operations owner, and escalation roles.
- [ ] **MC-052-02** — Create ADR(s) for core architectural choices and external ownership boundaries.
- [ ] **MC-052-03** — Maintain an exception/waiver/debt register with rationale, compensating controls, owner, and expiry.
- [ ] **MC-052-04** — Schedule architecture/security/operational readiness reviews.
- [ ] **MC-052-05** — Add LICENSE and NOTICE files appropriate to the project and bundled dependencies.
- [ ] **MC-052-06** — Track third-party attribution obligations.
- [ ] **MC-052-07** — Define document review cadence and stale-governance detection.
- [ ] **MC-052-08** — Require governance approval before declaring production certification complete.
- [ ] **MC-052-09** — Define an explicit scope statement covering what this component owns, what it delegates, and its trust boundaries.
- [ ] **MC-052-10** — Document functional requirements, non-functional requirements, invariants, safety properties, and liveness properties.
- [ ] **MC-052-11** — Identify upstream/downstream dependencies and define failure behavior for each dependency.
- [ ] **MC-052-12** — Define stable interfaces, data contracts, versioning rules, and compatibility expectations.
- [ ] **MC-052-13** — Implement fail-closed validation for malformed, unsupported, stale, ambiguous, or unauthorized inputs.
- [ ] **MC-052-14** — Bound memory, CPU, storage, queue depth, concurrency, retries, and network use; avoid unbounded collections or waits.
- [ ] **MC-052-15** — Propagate deadlines and cancellation across internal calls and dependency boundaries.
- [ ] **MC-052-16** — Use deterministic state transitions and explicit error handling; prohibit silent fallback that changes correctness semantics.
- [ ] **MC-052-17** — Threat-model the component using assets, actors, entry points, trust boundaries, abuse cases, and mitigations.
- [ ] **MC-052-18** — Apply least privilege to credentials, filesystem/network access, backend roles, and administrative actions.
- [ ] **MC-052-19** — Ensure secrets and sensitive values are never emitted in logs, traces, metrics labels, error details, crash dumps, or test fixtures.
- [ ] **MC-052-20** — Define authentication and authorization requirements for every externally reachable operation or administrative control.
- [ ] **MC-052-21** — Add positive-path unit tests for every public behavior and state transition.
- [ ] **MC-052-22** — Add negative tests for invalid inputs, boundary values, stale revisions/versions, denied access, and dependency failures.
- [ ] **MC-052-23** — Add concurrency/race tests where shared state, retries, watches, sessions, or lifecycle transitions are involved.
- [ ] **MC-052-24** — Add restart/recovery tests proving persistent or externally reconstructed state returns to a valid state.
- [ ] **MC-052-25** — Add compatibility tests across every supported adjacent version and deployment mode.
- [ ] **MC-052-26** — Add property/invariant tests for safety-critical semantics and deterministic replay where applicable.
- [ ] **MC-052-27** — Define health, readiness, degraded, and failed states with machine-readable status and operator meaning.
- [ ] **MC-052-28** — Emit component-specific metrics, structured logs, and trace spans with bounded cardinality.
- [ ] **MC-052-29** — Create dashboards for normal operation, saturation, error modes, dependency health, and recovery progress.
- [ ] **MC-052-30** — Define alert thresholds tied to user/system impact, with severity, routing, suppression, and runbook links.
- [ ] **MC-052-31** — Document safe startup, shutdown, drain, maintenance, rollback, and emergency-disable procedures.
- [ ] **MC-052-32** — Produce a requirements-to-evidence row for this component with owner, implementation reference, tests, artifacts, and release status.
- [ ] **MC-052-33** — Store machine-readable test results and relevant logs/artifacts as CI evidence tied to the source revision and build digest.
- [ ] **MC-052-34** — Record security review/threat-model approval and unresolved risks with explicit owners and expiry/review dates.
- [ ] **MC-052-35** — Record performance/capacity evidence where this component can affect latency, throughput, storage, or resource saturation.
- [ ] **MC-052-36** — Define a release acceptance gate that blocks promotion when required evidence is missing, stale, unsigned, or failing.
- [ ] **MC-052-37** — Assign an accountable owner and operational escalation path.

### Required acceptance evidence

- [ ] **MC-052-E01** — Design/ADR is approved and references the exact implementation scope.
- [ ] **MC-052-E02** — Automated tests execute in CI with machine-readable pass/fail output and no unexplained skips.
- [ ] **MC-052-E03** — Security/threat-model findings are closed or have approved, time-bounded exceptions.
- [ ] **MC-052-E04** — Operational telemetry and runbook coverage exist for expected failures and degraded states.
- [ ] **MC-052-E05** — Requirements-to-evidence matrix links this component to code, tests, artifacts, owner, and release build.

### Definition of done

- [ ] **MC-052-D01** — The component is implemented or formally integrated through a versioned external contract.
- [ ] **MC-052-D02** — All mandatory P2 controls above pass in the intended production topology.
- [ ] **MC-052-D03** — No open defect or exception can violate the documented safety, isolation, durability, or compatibility properties.
- [ ] **MC-052-D04** — Release evidence is immutable, attributable to the shipped artifact digest, and independently reviewable.

# Program-level completion gate

The INV-05 production-readiness program is complete only when all applicable component definitions of done are satisfied and the following global gates pass:

- [ ] All **P0** components are complete with current evidence and no unapproved exceptions.
- [ ] All deployment-applicable **P1** components are complete with current evidence.
- [ ] Every C001-C100 requirement has bidirectional traceability to implementation and evidence.
- [ ] Release candidate artifact digest matches the digest referenced by CI, provenance, SBOM, conformance, security, performance, and operational evidence.
- [ ] Mandatory test suites contain no unexplained skips, xfails, quarantined tests, or environment-dependent omissions.
- [ ] Linearizability, concurrency, fault-injection, restore, upgrade/rollback, and security-boundary tests pass for the intended production topology.
- [ ] Production backend, runtime, protocol, and adjacent-layer versions are within the approved compatibility matrix.
- [ ] Authentication, authorization, encryption, KMS, tenant isolation, and tamper-evident audit controls are enabled and verified.
- [ ] Capacity evidence demonstrates required headroom at target load and failure conditions.
- [ ] Dashboards, alerts, runbooks, backup/restore, DR, and emergency controls have been exercised in a representative environment.
- [ ] All open exceptions have owners, compensating controls, approval, review date, and expiry.
- [ ] Final production-readiness review is approved by engineering, security, operations/SRE, and the accountable system owner.

