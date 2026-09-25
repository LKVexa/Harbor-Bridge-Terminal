# GAP-14 Data-Gravity Manager v4.2.0
## Missing Components — Professional Engineering Checklist

**Document purpose:** Convert the v4.2.0 residual-component register into an implementation, assurance, and production-certification checklist.

**Scope:** 40 residual components (P0/P1/P2). This checklist is intentionally stricter than a feature backlog: a component is not considered complete merely because code exists; it must also have contracts, security controls, failure semantics, telemetry, tests, rollout evidence, and acceptance criteria.

### Priority model

- **P0 — Production certification blockers:** required before the GAP-14 service can be represented as estate-integrated and production-certifiable.
- **P1 — Reliability/security/operability maturity:** required for a hardened operational service and sustained production SLOs.
- **P2 — Capability expansion/optimization:** advanced decision quality, modeling depth, calibration, and operational lifecycle capabilities.

### Global Definition of Done

- [ ] Every component has an accountable technical owner and reviewing owner.
- [ ] Public/internal interfaces are versioned, schema-validated, documented, and compatibility-tested.
- [ ] Security/threat-model review is complete for trust boundaries, identity, data classification, and failure behavior.
- [ ] All external I/O has explicit timeout, cancellation, freshness, retry, and backpressure semantics where applicable.
- [ ] Stable machine-readable error/reason codes exist for all expected refusal and failure paths.
- [ ] Observability uses bounded-cardinality metrics, structured logs, trace propagation, and no secret leakage.
- [ ] Unit, contract, integration, property/fuzz, negative-path, and fault tests are present as applicable.
- [ ] Release evidence records source revision, component versions, configuration, test results, and artifact digests.
- [ ] Operational rollback/recovery behavior is documented and exercised for production-affecting components.
- [ ] A checklist item may be marked complete only with linked evidence (code, test, schema, trace, benchmark, runbook, or signed release artifact).

### Traceability table

| ID | Priority | Component | Primary completion evidence |
|---|---|---|---|
| `G14-P0-01` | P0 | pk_core conformance runtime and pinned compatibility version | schemas + tests + release evidence |
| `G14-P0-02` | P0 | Policy-engine adapter (GAP-13) | schemas + tests + release evidence |
| `G14-P0-03` | P0 | Topology/cost-feed adapter (GAP-03) | schemas + tests + release evidence |
| `G14-P0-04` | P0 | Replication-state adapter (GAP-05) | schemas + tests + release evidence |
| `G14-P0-05` | P0 | Workload/placement adapter (SCH-01) | schemas + tests + release evidence |
| `G14-P0-06` | P0 | Data-plane handoff adapter (PLN-06) | schemas + tests + release evidence |
| `G14-P0-07` | P0 | Authentication and authorization layer | schemas + tests + release evidence |
| `G14-P0-08` | P0 | Tenant/workload identity in the runtime decision model | schemas + tests + release evidence |
| `G14-P0-09` | P0 | Decision provenance envelope | schemas + tests + release evidence |
| `G14-P0-10` | P0 | Cryptographic evidence/audit sink | cryptographic/supply-chain evidence |
| `G14-P0-11` | P0 | Production configuration loader/validator | schemas + tests + release evidence |
| `G14-P0-12` | P0 | Estate-level integration tests | schemas + tests + release evidence |
| `G14-P1-13` | P1 | Timeout, cancellation, and backpressure semantics | schemas + tests + release evidence |
| `G14-P1-14` | P1 | Retry and circuit-breaker policy | schemas + tests + release evidence |
| `G14-P1-15` | P1 | Freshness and TTL rules | schemas + tests + release evidence |
| `G14-P1-16` | P1 | Stale-data fail-safe policy | schemas + tests + release evidence |
| `G14-P1-17` | P1 | Health/readiness endpoint or probe contract | schemas + tests + release evidence |
| `G14-P1-18` | P1 | Metrics exporter | telemetry/benchmark/fault evidence |
| `G14-P1-19` | P1 | Structured logging and trace-context propagation | telemetry/benchmark/fault evidence |
| `G14-P1-20` | P1 | Operator explain endpoint/view | schemas + tests + release evidence |
| `G14-P1-21` | P1 | Admission control and resource bounds | schemas + tests + release evidence |
| `G14-P1-22` | P1 | Fuzz and property testing | schemas + tests + release evidence |
| `G14-P1-23` | P1 | Performance, soak, and burst benchmarks | telemetry/benchmark/fault evidence |
| `G14-P1-24` | P1 | Fault-injection suite | telemetry/benchmark/fault evidence |
| `G14-P1-25` | P1 | Compatibility matrix | schemas + tests + release evidence |
| `G14-P1-26` | P1 | Dependency and supply-chain policy | cryptographic/supply-chain evidence |
| `G14-P1-27` | P1 | Packaging metadata | schemas + tests + release evidence |
| `G14-P2-28` | P2 | Partial dataset movement and sharding model | schemas + tests + release evidence |
| `G14-P2-29` | P2 | Repeated-job amortization model | schemas + tests + release evidence |
| `G14-P2-30` | P2 | Replication as a third decision option | schemas + tests + release evidence |
| `G14-P2-31` | P2 | Multi-dataset and DAG-aware gravity optimization | schemas + tests + release evidence |
| `G14-P2-32` | P2 | Carbon, power, and thermal cost dimension | schemas + tests + release evidence |
| `G14-P2-33` | P2 | Network congestion and transfer-time estimation | schemas + tests + release evidence |
| `G14-P2-34` | P2 | Storage read/write/IOPS cost model | schemas + tests + release evidence |
| `G14-P2-35` | P2 | Compute architecture/runtime compatibility model | schemas + tests + release evidence |
| `G14-P2-36` | P2 | Quota and capacity reservation awareness | schemas + tests + release evidence |
| `G14-P2-37` | P2 | Historical calibration and model-drift detection | telemetry/benchmark/fault evidence |
| `G14-P2-38` | P2 | Canary and shadow decision mode | schemas + tests + release evidence |
| `G14-P2-39` | P2 | Policy simulation and what-if API | schemas + tests + release evidence |
| `G14-P2-40` | P2 | Formal release and incident runbooks | runbooks + exercise records |

---

# G14-P0-01 — pk_core conformance runtime and pinned compatibility version

**Priority:** P0  
**Objective:** Make the estate conformance gate executable, reproducible, and version-bounded without silently downgrading coverage when the runtime is absent.  
**Dependencies:** GAP-14 release pipeline, estate package registry, CI runners, pk_core maintainers.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-01-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-01-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-01-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-01-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-01-A05` Define the exact supported `pk_core` semantic-version range and pin a certified build by immutable digest/hash, not only by a floating package version.
- [ ] `G14-P0-01-A06` Add a startup compatibility handshake that records `pk_core` version, ABI/API capability set, conformance schema version, and feature flags before any full-gate test runs.
- [ ] `G14-P0-01-A07` Separate `pk_core` availability failures from conformance failures with stable machine-readable exit/reason codes; missing runtime must never be represented as a passing gate.
- [ ] `G14-P0-01-A08` Package a deterministic bootstrap or dependency lock that can reconstruct the certified conformance environment on Windows and CI without user-global state.
- [ ] `G14-P0-01-A09` Add an adapter boundary so GAP-14 consumes only the documented `pk_core` surface and never relies on private/internal symbols.
- [ ] `G14-P0-01-A10` Define downgrade/upgrade behavior when the installed `pk_core` version is outside the certified range, including hard refusal for incompatible major/schema changes.

## B. Failure semantics and safety
- [ ] `G14-P0-01-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-01-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-01-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-01-B04` Implement and test explicit handling for: **runtime missing or importable only from unintended user-global paths**.
- [ ] `G14-P0-01-B05` Implement and test explicit handling for: **API/schema drift between certified and installed `pk_core`**.
- [ ] `G14-P0-01-B06` Implement and test explicit handling for: **partial gate execution reported as a complete pass**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-01-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-01-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-01-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-01-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-01-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-01-D01` Instrument **runtime version/digest and capability-set at test start**.
- [ ] `G14-P0-01-D02` Instrument **count of executed/skipped/failed conformance checks with skip reasons**.
- [ ] `G14-P0-01-D03` Instrument **compatibility-handshake duration and failure code**.
- [ ] `G14-P0-01-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-01-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-01-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-01-E01` run the full 100-check gate against the minimum, maximum, and pinned `pk_core` versions.
- [ ] `G14-P0-01-E02` remove `pk_core` and verify a hard non-success gate result.
- [ ] `G14-P0-01-E03` inject an incompatible API/schema version and verify deterministic rejection.
- [ ] `G14-P0-01-E04` execute from a clean Windows/CI environment with no preinstalled user packages.
- [ ] `G14-P0-01-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-01-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-01-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-01-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-01-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-01-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-01-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-01-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-01-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-01-G01` **Acceptance:** 100/100 checks are attempted when the certified runtime is present and every skip is explicitly policy-approved.
- [ ] `G14-P0-01-G02` **Acceptance:** the exact runtime version and immutable digest appear in release evidence.
- [ ] `G14-P0-01-G03` **Acceptance:** a missing or incompatible runtime cannot produce a production-certification PASS.
- [ ] `G14-P0-01-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-01-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-02 — Policy-engine adapter (GAP-13)

**Priority:** P0  
**Objective:** Consume cryptographically verifiable, fresh, versioned data-residency/legal-placement verdicts and fail closed when policy authority is unavailable or ambiguous.  
**Dependencies:** GAP-13 policy engine, identity service, trust/key distribution, audit sink.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-02-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-02-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-02-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-02-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-02-A05` Define a versioned request contract containing tenant, workload, dataset, source site, candidate destination, operation type, jurisdiction tags, and evaluation timestamp.
- [ ] `G14-P0-02-A06` Define a signed verdict contract containing allow/deny, policy version, rule identifiers, obligations, expiry/TTL, decision ID, issuer identity, and signature metadata.
- [ ] `G14-P0-02-A07` Validate policy responses against a strict schema and reject unknown mandatory fields, malformed signatures, expired verdicts, or mismatched request binding.
- [ ] `G14-P0-02-A08` Bind every verdict cryptographically or by canonical request hash to the exact tenant/workload/dataset/candidate tuple evaluated by GAP-14.
- [ ] `G14-P0-02-A09` Implement fail-closed behavior for timeout, signature failure, stale verdict, policy version rollback, issuer mismatch, or non-authoritative response.
- [ ] `G14-P0-02-A10` Support obligation propagation so restrictions such as encryption domain, approved region set, deletion deadline, or audit requirements remain attached to the decision.

## B. Failure semantics and safety
- [ ] `G14-P0-02-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-02-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-02-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-02-B04` Implement and test explicit handling for: **policy service timeout/partition**.
- [ ] `G14-P0-02-B05` Implement and test explicit handling for: **stale or replayed signed verdict**.
- [ ] `G14-P0-02-B06` Implement and test explicit handling for: **validly signed verdict bound to a different request or policy revision**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-02-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-02-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-02-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-02-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-02-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-02-D01` Instrument **policy request latency and timeout count**.
- [ ] `G14-P0-02-D02` Instrument **allow/deny/fail-closed outcomes by stable rule code without high-cardinality tenant labels**.
- [ ] `G14-P0-02-D03` Instrument **policy version/issuer and freshness age in trace attributes**.
- [ ] `G14-P0-02-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-02-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-02-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-02-E01` contract-test signed allow and deny fixtures across schema versions.
- [ ] `G14-P0-02-E02` tamper with payload/signature/request binding and verify rejection.
- [ ] `G14-P0-02-E03` advance clock beyond TTL and verify stale verdict refusal.
- [ ] `G14-P0-02-E04` simulate GAP-13 outage and verify no illegal fallback decision is emitted.
- [ ] `G14-P0-02-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-02-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-02-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-02-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-02-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-02-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-02-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-02-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-02-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-02-G01` **Acceptance:** no data-movement recommendation is legal without a fresh authoritative verdict.
- [ ] `G14-P0-02-G02` **Acceptance:** every accepted verdict is attributable to a policy version, rule set, issuer, and decision ID.
- [ ] `G14-P0-02-G03` **Acceptance:** timeouts and ambiguous responses produce stable fail-closed reason codes.
- [ ] `G14-P0-02-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-02-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-03 — Topology/cost-feed adapter (GAP-03)

**Priority:** P0  
**Objective:** Supply authoritative route availability and locality/cost inputs with explicit snapshot identity, freshness, provenance, and asymmetric route semantics.  
**Dependencies:** GAP-03 topology service, network inventory, cost/pricing feeds, time source.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-03-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-03-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-03-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-03-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-03-A05` Define a topology snapshot schema with site IDs, directed routes, route state, locality multiplier, egress rate, capacity metadata, observed-at timestamp, and source provenance.
- [ ] `G14-P0-03-A06` Treat route keys as directed (`A→B` distinct from `B→A`) and reject accidental symmetric fallback unless explicitly configured.
- [ ] `G14-P0-03-A07` Validate every numeric value as finite and domain-valid; reject NaN, infinity, negative rates, zero/negative invalid multipliers, and malformed site identifiers.
- [ ] `G14-P0-03-A08` Require a snapshot version/revision and canonical snapshot hash so the exact cost inputs can be reproduced during audit.
- [ ] `G14-P0-03-A09` Implement atomic snapshot replacement; a recommendation must never mix fields from two topology revisions.
- [ ] `G14-P0-03-A10` Define behavior for missing route, administratively disabled route, unknown cost, and stale cost independently using stable elimination/error codes.

## B. Failure semantics and safety
- [ ] `G14-P0-03-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-03-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-03-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-03-B04` Implement and test explicit handling for: **missing directed route represented as an implicit default**.
- [ ] `G14-P0-03-B05` Implement and test explicit handling for: **mixed-revision topology/cost data during update**.
- [ ] `G14-P0-03-B06` Implement and test explicit handling for: **corrupted or stale pricing/locality feed**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-03-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-03-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-03-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-03-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-03-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-03-D01` Instrument **snapshot age/version and update success/failure**.
- [ ] `G14-P0-03-D02` Instrument **route-missing/disabled/stale eliminations**.
- [ ] `G14-P0-03-D03` Instrument **distribution of locality multipliers and effective route costs with bounded cardinality**.
- [ ] `G14-P0-03-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-03-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-03-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-03-E01` exercise asymmetric egress rates and verify directional cost differences.
- [ ] `G14-P0-03-E02` delete a required route and verify fail-closed elimination rather than defaulting.
- [ ] `G14-P0-03-E03` inject NaN/infinity/negative values and verify schema/domain rejection.
- [ ] `G14-P0-03-E04` race snapshot refresh against concurrent decisions and verify each decision uses one immutable revision.
- [ ] `G14-P0-03-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-03-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-03-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-03-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-03-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-03-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-03-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-03-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-03-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-03-G01` **Acceptance:** every cross-site comparison cites one immutable fresh topology/cost snapshot.
- [ ] `G14-P0-03-G02` **Acceptance:** missing or invalid route economics never silently become `1.0` or zero cost.
- [ ] `G14-P0-03-G03` **Acceptance:** all route inputs are reproducible from recorded snapshot/version evidence.
- [ ] `G14-P0-03-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-03-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-04 — Replication-state adapter (GAP-05)

**Priority:** P0  
**Objective:** Replace caller-supplied convergence booleans with authenticated evidence of replica membership, epoch, freshness, and consistency state.  
**Dependencies:** GAP-05 replication service, replica metadata store, identity/trust service, time source.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-04-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-04-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-04-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-04-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-04-A05` Define a convergence-proof contract containing dataset ID, replica-set ID, epoch/term, member set, consistency mode, convergence status, proof timestamp, expiry, issuer, and integrity signature.
- [ ] `G14-P0-04-A06` Require proof binding to the exact dataset version/content generation used by the gravity decision, not merely the dataset name.
- [ ] `G14-P0-04-A07` Reject convergence evidence from old epochs, unknown issuers, mismatched replica sets, expired TTLs, or unsigned/unverifiable sources.
- [ ] `G14-P0-04-A08` Represent nuanced states such as converged, catching-up, degraded, split/partitioned, unknown, and rebuilding instead of collapsing all states into a Boolean.
- [ ] `G14-P0-04-A09` Protect against TOCTOU by recording the proof ID/epoch in the decision and requiring downstream execution to revalidate preconditions before moving data.
- [ ] `G14-P0-04-A10` Define consistency-mode-specific eligibility rules for eventual, quorum, strong, or application-defined replication contracts.

## B. Failure semantics and safety
- [ ] `G14-P0-04-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-04-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-04-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-04-B04` Implement and test explicit handling for: **stale convergence proof after a topology or replica-set change**.
- [ ] `G14-P0-04-B05` Implement and test explicit handling for: **false-positive convergence from untrusted caller input**.
- [ ] `G14-P0-04-B06` Implement and test explicit handling for: **epoch rollback or split-brain evidence**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-04-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-04-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-04-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-04-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-04-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-04-D01` Instrument **proof age/epoch and state distribution**.
- [ ] `G14-P0-04-D02` Instrument **convergence-check latency/failure reasons**.
- [ ] `G14-P0-04-D03` Instrument **decisions refused due to unknown/degraded replication**.
- [ ] `G14-P0-04-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-04-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-04-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-04-E01` supply valid converged proof and verify eligibility.
- [ ] `G14-P0-04-E02` use stale, wrong-dataset, wrong-epoch, and invalid-signature proofs and verify rejection.
- [ ] `G14-P0-04-E03` simulate split-brain/degraded states and verify conservative behavior.
- [ ] `G14-P0-04-E04` change dataset generation between proof and decision and verify mismatch detection.
- [ ] `G14-P0-04-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-04-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-04-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-04-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-04-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-04-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-04-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-04-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-04-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-04-G01` **Acceptance:** GAP-14 no longer trusts an unverified caller Boolean for production convergence.
- [ ] `G14-P0-04-G02` **Acceptance:** every convergence-dependent decision carries proof identity/epoch/freshness.
- [ ] `G14-P0-04-G03` **Acceptance:** unknown or unverifiable convergence cannot authorize a data move.
- [ ] `G14-P0-04-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-04-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-05 — Workload/placement adapter (SCH-01)

**Priority:** P0  
**Objective:** Replace bare `compute_sites` with authoritative workload compatibility, capacity, and placement constraints from the scheduler domain.  
**Dependencies:** SCH-01 scheduler, capacity inventory, runtime/accelerator catalogs, quota service.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-05-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-05-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-05-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-05-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-05-A05` Define a workload requirement vector covering CPU architecture, cores, memory, GPU/accelerator type/count, local storage, runtime/ABI, device features, network class, and affinity/anti-affinity constraints.
- [ ] `G14-P0-05-A06` Define a candidate-site capability vector with allocatable capacity, reservations, maintenance state, runtime compatibility, accelerators, and placement labels.
- [ ] `G14-P0-05-A07` Require scheduler snapshot version/freshness and bind candidate eligibility to the exact workload revision or immutable workload spec hash.
- [ ] `G14-P0-05-A08` Separate 'technically compatible' from 'currently allocatable' and expose elimination reasons for each failed capability or capacity predicate.
- [ ] `G14-P0-05-A09` Model required versus preferred constraints explicitly so optimization never treats a hard scheduling requirement as a soft cost.
- [ ] `G14-P0-05-A10` Provide deterministic handling for zero eligible sites, one eligible site, and rapidly changing capacity.

## B. Failure semantics and safety
- [ ] `G14-P0-05-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-05-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-05-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-05-B04` Implement and test explicit handling for: **site listed as eligible despite missing architecture/runtime capability**.
- [ ] `G14-P0-05-B05` Implement and test explicit handling for: **capacity race between recommendation and placement**.
- [ ] `G14-P0-05-B06` Implement and test explicit handling for: **hard constraint downgraded to a cost preference**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-05-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-05-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-05-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-05-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-05-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-05-D01` Instrument **candidate count and elimination reasons**.
- [ ] `G14-P0-05-D02` Instrument **scheduler snapshot age/version**.
- [ ] `G14-P0-05-D03` Instrument **resource-fit margin for selected candidate using bounded labels**.
- [ ] `G14-P0-05-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-05-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-05-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-05-E01` exercise CPU/GPU/ISA/runtime incompatibilities and verify precise eliminations.
- [ ] `G14-P0-05-E02` simulate capacity exhaustion after discovery and verify execution precondition failure.
- [ ] `G14-P0-05-E03` verify preferred constraints may influence cost/order but cannot override required constraints.
- [ ] `G14-P0-05-E04` run contract tests against SCH-01 versioned fixtures.
- [ ] `G14-P0-05-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-05-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-05-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-05-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-05-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-05-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-05-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-05-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-05-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-05-G01` **Acceptance:** every selected compute destination is proven compatible with the workload specification.
- [ ] `G14-P0-05-G02` **Acceptance:** hard scheduler constraints are non-bypassable by cost optimization.
- [ ] `G14-P0-05-G03` **Acceptance:** placement evidence records scheduler revision and workload-spec identity.
- [ ] `G14-P0-05-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-05-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-06 — Data-plane handoff adapter (PLN-06)

**Priority:** P0  
**Objective:** Turn an approved move-data recommendation into a signed, idempotent, preconditioned execution request without embedding transfer execution inside GAP-14.  
**Dependencies:** PLN-06 data-plane planner/executor, identity/trust service, object/storage services, GAP-05 replication state.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-06-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-06-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-06-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-06-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-06-A05` Define an idempotent handoff request with decision ID, operation ID, dataset generation, source/destination, byte estimate, policy obligations, integrity hash/manifest, expiry, and preconditions.
- [ ] `G14-P0-06-A06` Require downstream acknowledgement to include accepted operation ID, executor identity, plan revision, and a cryptographic binding to the originating GAP-14 decision.
- [ ] `G14-P0-06-A07` Implement idempotency-key persistence semantics so retries cannot create duplicate moves or duplicated billing side effects.
- [ ] `G14-P0-06-A08` Express preconditions for policy freshness, source generation, destination authorization, free capacity, encryption domain, and convergence state.
- [ ] `G14-P0-06-A09` Define execution states (`accepted`, `staged`, `transferring`, `verifying`, `committed`, `failed`, `cancelled`, `rolled_back`) and legal transitions.
- [ ] `G14-P0-06-A10` Require completion attestation with bytes transferred, content/integrity verification, final placement, timestamps, and terminal outcome.

## B. Failure semantics and safety
- [ ] `G14-P0-06-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-06-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-06-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-06-B04` Implement and test explicit handling for: **duplicate transfer created by client retry**.
- [ ] `G14-P0-06-B05` Implement and test explicit handling for: **execution begins after decision/policy preconditions expired**.
- [ ] `G14-P0-06-B06` Implement and test explicit handling for: **partial transfer committed without integrity verification**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-06-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-06-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-06-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-06-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-06-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-06-D01` Instrument **handoff acceptance latency and rejection reasons**.
- [ ] `G14-P0-06-D02` Instrument **operation-state durations and retry counts**.
- [ ] `G14-P0-06-D03` Instrument **bytes planned versus transferred and integrity-verification failures**.
- [ ] `G14-P0-06-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-06-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-06-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-06-E01` replay the same idempotency key and verify one logical operation.
- [ ] `G14-P0-06-E02` expire policy/preconditions before execution and verify refusal.
- [ ] `G14-P0-06-E03` inject transfer interruption and verify safe resume/rollback semantics.
- [ ] `G14-P0-06-E04` tamper completion attestation or dataset generation and verify rejection.
- [ ] `G14-P0-06-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-06-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-06-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-06-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-06-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-06-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-06-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-06-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-06-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-06-G01` **Acceptance:** an approved decision cannot directly mutate storage without the signed handoff contract.
- [ ] `G14-P0-06-G02` **Acceptance:** retries are demonstrably idempotent.
- [ ] `G14-P0-06-G03` **Acceptance:** terminal success includes integrity and destination-state evidence bound to the decision.
- [ ] `G14-P0-06-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-06-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-07 — Authentication and authorization layer

**Priority:** P0  
**Objective:** Establish trusted caller identity, tenant scoping, least privilege, and authorization binding at every production API/adapter boundary.  
**Dependencies:** enterprise identity provider, certificate/key infrastructure, GAP-13 policy engine, secret management.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-07-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-07-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-07-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-07-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-07-A05` Select supported workload identity mechanisms (for example mTLS/SPIFFE, OIDC/JWT, or estate-issued capability tokens) and document trust roots and rotation.
- [ ] `G14-P0-07-A06` Authenticate the caller before deserializing or executing privileged decision requests beyond minimal protocol parsing.
- [ ] `G14-P0-07-A07` Authorize explicit actions such as `recommend`, `explain`, `simulate`, `reload_config`, and `handoff` using least-privilege RBAC/ABAC policies.
- [ ] `G14-P0-07-A08` Bind tenant identity and authorized resource scope to the request so callers cannot substitute arbitrary tenant/dataset/workload identifiers.
- [ ] `G14-P0-07-A09` Enforce token audience, issuer, expiry, not-before, nonce/replay controls, algorithm allowlists, and key-ID validation.
- [ ] `G14-P0-07-A10` Define service-to-service authorization separately from human/operator authorization and prevent privilege inheritance between them.

## B. Failure semantics and safety
- [ ] `G14-P0-07-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-07-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-07-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-07-B04` Implement and test explicit handling for: **anonymous or weakly authenticated decision request**.
- [ ] `G14-P0-07-B05` Implement and test explicit handling for: **cross-tenant identifier substitution**.
- [ ] `G14-P0-07-B06` Implement and test explicit handling for: **replayed or wrong-audience credential accepted**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-07-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-07-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-07-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-07-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-07-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-07-D01` Instrument **authentication failures by stable reason**.
- [ ] `G14-P0-07-D02` Instrument **authorization denies by action/resource class without sensitive identifiers**.
- [ ] `G14-P0-07-D03` Instrument **credential issuer/key version and rotation health**.
- [ ] `G14-P0-07-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-07-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-07-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-07-E01` attempt anonymous, expired, wrong-audience, replayed, and cross-tenant requests.
- [ ] `G14-P0-07-E02` rotate trust keys/certificates without unsafe acceptance gaps.
- [ ] `G14-P0-07-E03` verify every privileged endpoint has an authorization test.
- [ ] `G14-P0-07-E04` fuzz token/header parsing within strict size limits.
- [ ] `G14-P0-07-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-07-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-07-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-07-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-07-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-07-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-07-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-07-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-07-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-07-G01` **Acceptance:** all production entry points require authenticated identity.
- [ ] `G14-P0-07-G02` **Acceptance:** cross-tenant access is denied by construction and verified in tests.
- [ ] `G14-P0-07-G03` **Acceptance:** authorization evidence is recorded in the decision/audit trail without leaking secrets.
- [ ] `G14-P0-07-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-07-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-08 — Tenant/workload identity in the runtime decision model

**Priority:** P0  
**Objective:** Make tenant and workload identity first-class immutable fields throughout evaluation, provenance, policy checks, logging, and handoff.  
**Dependencies:** API schemas, identity layer, GAP-13 adapter, SCH-01 adapter.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-08-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-08-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-08-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-08-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-08-A05` Add canonical `tenant_id` and `workload_id` fields to the decision input model with explicit format, length, normalization, and immutability rules.
- [ ] `G14-P0-08-A06` Add `dataset_id`/generation and workload revision identifiers where needed to prevent name-based ambiguity.
- [ ] `G14-P0-08-A07` Reject missing identities in production mode; if development compatibility mode exists, mark it non-certifiable and impossible to enable accidentally in production.
- [ ] `G14-P0-08-A08` Propagate identity fields to policy, scheduler, provenance, audit, metrics-safe dimensions, and data-plane handoff contracts.
- [ ] `G14-P0-08-A09` Define migration/versioning rules for existing callers so identity additions do not create silent field dropping.
- [ ] `G14-P0-08-A10` Prohibit implicit tenant inference from site, path, dataset name, process user, or ambient environment variables.

## B. Failure semantics and safety
- [ ] `G14-P0-08-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-08-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-08-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-08-B04` Implement and test explicit handling for: **same dataset name across tenants resolves ambiguously**.
- [ ] `G14-P0-08-B05` Implement and test explicit handling for: **legacy caller silently omits workload identity**.
- [ ] `G14-P0-08-B06` Implement and test explicit handling for: **identity normalized differently across adapters**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-08-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-08-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-08-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-08-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-08-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-08-D01` Instrument **schema-version usage by caller**.
- [ ] `G14-P0-08-D02` Instrument **missing/invalid identity rejection counts**.
- [ ] `G14-P0-08-D03` Instrument **correlation via opaque hashed identifiers where operationally required**.
- [ ] `G14-P0-08-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-08-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-08-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-08-E01` collision tests for same names across different tenant IDs.
- [ ] `G14-P0-08-E02` Unicode/case/whitespace normalization tests.
- [ ] `G14-P0-08-E03` legacy schema downgrade/upgrade contract tests.
- [ ] `G14-P0-08-E04` verify identities remain unchanged through policy/topology/scheduler/handoff propagation.
- [ ] `G14-P0-08-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-08-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-08-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-08-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-08-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-08-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-08-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-08-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-08-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-08-G01` **Acceptance:** every production decision is uniquely scoped to tenant, workload, and dataset identity.
- [ ] `G14-P0-08-G02` **Acceptance:** no adapter derives identity from ambient context.
- [ ] `G14-P0-08-G03` **Acceptance:** schema evolution cannot silently discard identity fields.
- [ ] `G14-P0-08-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-08-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-09 — Decision provenance envelope

**Priority:** P0  
**Objective:** Make every recommendation reproducible and attributable to exact input snapshots, model/config revisions, actor identity, and time.  
**Dependencies:** all external adapters, configuration subsystem, identity layer, audit sink.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-09-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-09-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-09-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-09-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-09-A05` Create a versioned provenance schema containing decision ID, canonical input hash, actor/service identity, tenant/workload/dataset IDs, wall-clock timestamp, and monotonic timing metadata.
- [ ] `G14-P0-09-A06` Record policy version/decision ID, topology/cost snapshot version, replication proof ID/epoch, scheduler snapshot version, configuration revision, engine version, and schema versions.
- [ ] `G14-P0-09-A07` Canonicalize provenance serialization before hashing/signing so logically identical inputs produce stable evidence across platforms.
- [ ] `G14-P0-09-A08` Distinguish source timestamps from observation timestamps and decision timestamp to expose stale-data and clock-skew conditions.
- [ ] `G14-P0-09-A09` Include eliminated alternatives and stable reason codes without embedding sensitive raw credentials or secrets.
- [ ] `G14-P0-09-A10` Make provenance immutable after decision finalization; subsequent execution outcomes must reference rather than overwrite the original envelope.

## B. Failure semantics and safety
- [ ] `G14-P0-09-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-09-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-09-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-09-B04` Implement and test explicit handling for: **decision cannot be reconstructed because one input revision is missing**.
- [ ] `G14-P0-09-B05` Implement and test explicit handling for: **provenance mutates after execution**.
- [ ] `G14-P0-09-B06` Implement and test explicit handling for: **noncanonical serialization breaks evidence verification**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-09-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-09-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-09-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-09-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-09-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-09-D01` Instrument **provenance construction/signing failures**.
- [ ] `G14-P0-09-D02` Instrument **percentage of decisions with complete source-version coverage**.
- [ ] `G14-P0-09-D03` Instrument **clock-skew observations beyond configured tolerance**.
- [ ] `G14-P0-09-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-09-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-09-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-09-E01` replay a recorded provenance bundle and reproduce the same decision.
- [ ] `G14-P0-09-E02` mutate one input revision and verify hash/evidence changes.
- [ ] `G14-P0-09-E03` verify cross-platform canonical serialization.
- [ ] `G14-P0-09-E04` attempt post-finalization mutation and verify immutability.
- [ ] `G14-P0-09-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-09-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-09-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-09-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-09-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-09-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-09-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-09-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-09-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-09-G01` **Acceptance:** 100% of certifiable decisions contain all required provenance fields.
- [ ] `G14-P0-09-G02` **Acceptance:** the original decision can be reconstructed from retained snapshots/evidence.
- [ ] `G14-P0-09-G03` **Acceptance:** provenance is immutable and cryptographically bindable to audit records.
- [ ] `G14-P0-09-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-09-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-10 — Cryptographic evidence/audit sink

**Priority:** P0  
**Objective:** Emit tamper-evident, append-only records for recommendations, refusals, configuration changes, and execution handoffs with retention and verification controls.  
**Dependencies:** key management, WORM/append-only storage, provenance envelope, operations/SIEM.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-10-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-10-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-10-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-10-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-10-A05` Define canonical event schemas for decision, refusal, adapter failure, config activation/rollback, and handoff lifecycle events.
- [ ] `G14-P0-10-A06` Use hash chaining, Merkle batching, digital signatures, or an estate-approved equivalent so deletion/reordering/modification can be detected.
- [ ] `G14-P0-10-A07` Store signer key ID, signing algorithm, event sequence/chain metadata, event time, and provenance decision ID in every signed record.
- [ ] `G14-P0-10-A08` Define retention, legal hold, partitioning, compaction, and export rules without weakening integrity verification.
- [ ] `G14-P0-10-A09` Design bounded buffering/backpressure behavior when the audit sink is slow or unavailable; define which operations must fail closed rather than run unaudited.
- [ ] `G14-P0-10-A10` Implement independent verification tooling that can validate signatures/chains without needing the live GAP-14 service.

## B. Failure semantics and safety
- [ ] `G14-P0-10-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-10-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-10-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-10-B04` Implement and test explicit handling for: **audit sink unavailable during privileged decision**.
- [ ] `G14-P0-10-B05` Implement and test explicit handling for: **records altered/reordered after emission**.
- [ ] `G14-P0-10-B06` Implement and test explicit handling for: **signing key unavailable or revoked**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-10-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-10-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-10-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-10-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-10-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-10-D01` Instrument **audit enqueue/commit latency and queue depth**.
- [ ] `G14-P0-10-D02` Instrument **signature/chain verification failures**.
- [ ] `G14-P0-10-D03` Instrument **dropped/blocked event counts, which must be zero for mandatory classes**.
- [ ] `G14-P0-10-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-10-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-10-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-10-E01` tamper, delete, duplicate, and reorder stored events and verify detection.
- [ ] `G14-P0-10-E02` take the sink offline and verify configured fail-closed/buffer semantics.
- [ ] `G14-P0-10-E03` rotate signing keys and verify historical validation remains possible.
- [ ] `G14-P0-10-E04` recover from process crash with pending audit events and verify no silent loss.
- [ ] `G14-P0-10-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-10-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-10-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-10-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-10-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-10-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-10-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-10-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-10-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-10-G01` **Acceptance:** mandatory production actions never complete without required audit evidence.
- [ ] `G14-P0-10-G02` **Acceptance:** independent verifier detects any tested record tampering.
- [ ] `G14-P0-10-G03` **Acceptance:** retention and key-rotation procedures preserve verifiability for the required audit horizon.
- [ ] `G14-P0-10-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-10-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-11 — Production configuration loader/validator

**Priority:** P0  
**Objective:** Load signed, schema-validated, versioned configuration transactionally with deterministic rollback and no mutable global-state ambiguity.  
**Dependencies:** configuration repository, key management, schema registry, audit sink.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-11-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-11-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-11-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-11-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-11-A05` Define one authoritative declarative configuration format and schema with explicit version, defaults, required fields, numeric domains, and unknown-field policy.
- [ ] `G14-P0-11-A06` Require source provenance and optional/required signature verification according to deployment tier; reject unsigned production configuration when signing is mandated.
- [ ] `G14-P0-11-A07` Parse into an immutable candidate snapshot, perform semantic validation, then atomically activate only after the entire candidate passes.
- [ ] `G14-P0-11-A08` Generate monotonic configuration revision IDs and canonical hashes and expose them in provenance, health, and logs.
- [ ] `G14-P0-11-A09` Persist the last-known-good revision and provide an explicit audited rollback transaction rather than editing live objects in place.
- [ ] `G14-P0-11-A10` Separate secrets from ordinary configuration and resolve secret references through an approved secret store; never write resolved secrets to logs or provenance.

## B. Failure semantics and safety
- [ ] `G14-P0-11-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-11-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-11-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-11-B04` Implement and test explicit handling for: **partially applied configuration after validation failure**.
- [ ] `G14-P0-11-B05` Implement and test explicit handling for: **rollback to an incompatible schema revision**.
- [ ] `G14-P0-11-B06` Implement and test explicit handling for: **secret value accidentally embedded in config evidence**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-11-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-11-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-11-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-11-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-11-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-11-D01` Instrument **active revision/hash and activation timestamp**.
- [ ] `G14-P0-11-D02` Instrument **reload success/failure and validation reason**.
- [ ] `G14-P0-11-D03` Instrument **rollback count and configuration age**.
- [ ] `G14-P0-11-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-11-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-11-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-11-E01` load valid/invalid boundary-value configurations.
- [ ] `G14-P0-11-E02` interrupt activation and verify previous snapshot remains intact.
- [ ] `G14-P0-11-E03` tamper signature/hash and verify rejection.
- [ ] `G14-P0-11-E04` activate then roll back under concurrent decision load and verify per-decision snapshot consistency.
- [ ] `G14-P0-11-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-11-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-11-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-11-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-11-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-11-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-11-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-11-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-11-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-11-G01` **Acceptance:** configuration changes are atomic, validated, attributable, and reversible.
- [ ] `G14-P0-11-G02` **Acceptance:** every decision records the exact active configuration revision.
- [ ] `G14-P0-11-G03` **Acceptance:** no production path consumes mutable unvalidated configuration.
- [ ] `G14-P0-11-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-11-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P0-12 — Estate-level integration tests

**Priority:** P0  
**Objective:** Prove cross-service correctness for GAP-13, GAP-03, GAP-05, SCH-01, PLN-06, identity, audit, and GAP-14 under realistic success and failure scenarios.  
**Dependencies:** all P0 adapters, integration environment, test identities/keys, fixture orchestration.

## A. Architecture, ownership, and requirements
- [ ] `G14-P0-12-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P0-12-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P0-12-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P0-12-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P0-12-A05` Build a hermetic integration topology with version-pinned service fixtures or approved live test deployments for each adjacent estate component.
- [ ] `G14-P0-12-A06` Create deterministic scenario manifests covering legal/illegal placement, asymmetric costs, convergence states, capability constraints, and execution handoff.
- [ ] `G14-P0-12-A07` Seed test identities, keys, topology snapshots, policies, datasets, and workloads from versioned fixtures with reproducible cleanup.
- [ ] `G14-P0-12-A08` Verify provenance across service boundaries by correlating one decision ID through policy, topology, replication, scheduler, audit, and handoff records.
- [ ] `G14-P0-12-A09` Add negative-path scenarios for dependency timeout, stale data, signature failure, partial partition, capacity race, and handoff rejection.
- [ ] `G14-P0-12-A10` Publish machine-readable evidence showing component versions, executed scenarios, results, and artifacts for every release candidate.

## B. Failure semantics and safety
- [ ] `G14-P0-12-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P0-12-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P0-12-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P0-12-B04` Implement and test explicit handling for: **individual unit tests pass while combined semantics violate policy**.
- [ ] `G14-P0-12-B05` Implement and test explicit handling for: **test fixture drift makes results non-reproducible**.
- [ ] `G14-P0-12-B06` Implement and test explicit handling for: **integration suite silently skips unavailable services**.

## C. Security, integrity, and data protection
- [ ] `G14-P0-12-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P0-12-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P0-12-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P0-12-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P0-12-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P0-12-D01` Instrument **scenario execution counts/pass/fail/skip with reasons**.
- [ ] `G14-P0-12-D02` Instrument **cross-service trace completeness**.
- [ ] `G14-P0-12-D03` Instrument **environment/component version manifest**.
- [ ] `G14-P0-12-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P0-12-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P0-12-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P0-12-E01` end-to-end move-compute decision with all authoritative adapters.
- [ ] `G14-P0-12-E02` end-to-end move-data decision through accepted/completed PLN-06 handoff.
- [ ] `G14-P0-12-E03` policy deny and stale-replication scenarios.
- [ ] `G14-P0-12-E04` concurrent topology/config update during integration workload.
- [ ] `G14-P0-12-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P0-12-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P0-12-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P0-12-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P0-12-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P0-12-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P0-12-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P0-12-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P0-12-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P0-12-G01` **Acceptance:** all required P0 integration scenarios execute with zero unapproved skips.
- [ ] `G14-P0-12-G02` **Acceptance:** each scenario has reproducible versioned fixtures and evidence.
- [ ] `G14-P0-12-G03` **Acceptance:** release certification consumes integration results rather than unit tests alone.
- [ ] `G14-P0-12-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P0-12-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-13 — Timeout, cancellation, and backpressure semantics

**Priority:** P1  
**Objective:** Bound dependency latency and work accumulation so slow or cancelled requests do not exhaust threads, memory, queues, or caller deadlines.  
**Dependencies:** all external adapters, API/runtime execution model, metrics/tracing.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-13-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-13-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-13-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-13-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-13-A05` Define per-adapter connection, request, and total deadline budgets derived from the overall decision SLO.
- [ ] `G14-P1-13-A06` Propagate caller cancellation/deadline through every downstream operation and stop unnecessary work promptly.
- [ ] `G14-P1-13-A07` Use bounded queues/semaphores for decision concurrency and adapter fan-out; prohibit unbounded task creation.
- [ ] `G14-P1-13-A08` Define saturation behavior (`reject`, `shed`, or bounded wait) with explicit status/reason codes and Retry-After guidance where applicable.
- [ ] `G14-P1-13-A09` Ensure cancellation cannot leave partially mutated shared state, leaked sockets, orphaned subprocesses, or uncommitted audit/config transactions.
- [ ] `G14-P1-13-A10` Reserve capacity or priority classes for control-plane/health operations so overload cannot blind operators.

## B. Failure semantics and safety
- [ ] `G14-P1-13-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-13-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-13-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-13-B04` Implement and test explicit handling for: **hung dependency consumes request workers indefinitely**.
- [ ] `G14-P1-13-B05` Implement and test explicit handling for: **client cancellation leaves background work running**.
- [ ] `G14-P1-13-B06` Implement and test explicit handling for: **unbounded queue causes memory exhaustion**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-13-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-13-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-13-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-13-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-13-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-13-D01` Instrument **active/queued request gauges and saturation rejects**.
- [ ] `G14-P1-13-D02` Instrument **deadline exceeded/cancelled operations by dependency**.
- [ ] `G14-P1-13-D03` Instrument **queue wait and downstream time budget consumption**.
- [ ] `G14-P1-13-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-13-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-13-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-13-E01` hold each dependency beyond its budget and verify deterministic timeout.
- [ ] `G14-P1-13-E02` cancel requests at each lifecycle phase and check cleanup.
- [ ] `G14-P1-13-E03` burst beyond concurrency limits and verify bounded memory/latency.
- [ ] `G14-P1-13-E04` stress health/control endpoints during data-plane overload.
- [ ] `G14-P1-13-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-13-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-13-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-13-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-13-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-13-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-13-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-13-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-13-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-13-G01` **Acceptance:** all external calls have enforced finite deadlines.
- [ ] `G14-P1-13-G02` **Acceptance:** queue and concurrency bounds are documented and test-proven.
- [ ] `G14-P1-13-G03` **Acceptance:** cancellation and overload do not leak resources or produce unsafe partial decisions.
- [ ] `G14-P1-13-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-13-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-14 — Retry and circuit-breaker policy

**Priority:** P1  
**Objective:** Recover from transient idempotent read failures without amplifying outages, duplicating side effects, or hiding persistent dependency faults.  
**Dependencies:** external adapters, timeout policy, metrics/tracing.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-14-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-14-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-14-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-14-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-14-A05` Classify every adapter operation as idempotent read, conditionally idempotent, or side-effecting and allow automatic retries only where safe.
- [ ] `G14-P1-14-A06` Define bounded exponential backoff with jitter, maximum attempts, cumulative retry budget, and caller-deadline awareness.
- [ ] `G14-P1-14-A07` Implement per-dependency circuit states with documented trip thresholds, open duration, half-open probes, and reset behavior.
- [ ] `G14-P1-14-A08` Do not retry deterministic validation, authentication, authorization, policy-deny, schema, or signature failures.
- [ ] `G14-P1-14-A09` Honor server throttling/Retry-After signals within the caller budget and prevent synchronized retry storms.
- [ ] `G14-P1-14-A10` Record the original error separately from the final retry/circuit outcome for accurate diagnosis.

## B. Failure semantics and safety
- [ ] `G14-P1-14-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-14-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-14-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-14-B04` Implement and test explicit handling for: **retry storm worsens dependency outage**.
- [ ] `G14-P1-14-B05` Implement and test explicit handling for: **side-effecting handoff duplicated by retry**.
- [ ] `G14-P1-14-B06` Implement and test explicit handling for: **circuit remains open/closed incorrectly after recovery**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-14-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-14-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-14-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-14-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-14-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-14-D01` Instrument **retry attempts/exhaustions by dependency and error class**.
- [ ] `G14-P1-14-D02` Instrument **circuit state transitions and open duration**.
- [ ] `G14-P1-14-D03` Instrument **success-after-retry ratio and added latency**.
- [ ] `G14-P1-14-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-14-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-14-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-14-E01` inject transient failures and verify bounded successful recovery.
- [ ] `G14-P1-14-E02` inject deterministic failures and verify zero retries.
- [ ] `G14-P1-14-E03` simulate dependency outage across many clients and verify jitter/circuit containment.
- [ ] `G14-P1-14-E04` verify side-effecting operations rely on idempotency semantics rather than blind retries.
- [ ] `G14-P1-14-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-14-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-14-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-14-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-14-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-14-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-14-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-14-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-14-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-14-G01` **Acceptance:** retryable operation set is explicit and reviewable.
- [ ] `G14-P1-14-G02` **Acceptance:** retry/circuit behavior respects the end-to-end deadline.
- [ ] `G14-P1-14-G03` **Acceptance:** failure injection shows no duplicate side effects or retry amplification.
- [ ] `G14-P1-14-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-14-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-15 — Freshness and TTL rules

**Priority:** P1  
**Objective:** Define authoritative maximum ages for policy, topology, convergence, price, capacity, and other time-sensitive decision inputs.  
**Dependencies:** GAP-13, GAP-03, GAP-05, SCH-01, time synchronization.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-15-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-15-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-15-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-15-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-15-A05` Define independent TTL/max-age policy for each input class based on risk and update cadence rather than one global cache duration.
- [ ] `G14-P1-15-A06` Require source `observed_at`/`issued_at` timestamps plus local receipt time and record both in provenance.
- [ ] `G14-P1-15-A07` Define clock-skew tolerance and use monotonic elapsed time for in-process expiry where possible.
- [ ] `G14-P1-15-A08` Reject timestamps unreasonably far in the future or before an accepted epoch/revision boundary.
- [ ] `G14-P1-15-A09` Evaluate freshness at decision finalization, not merely when an asynchronous refresh started.
- [ ] `G14-P1-15-A10` Expose remaining TTL/age to downstream execution when execution preconditions depend on evidence still being valid.

## B. Failure semantics and safety
- [ ] `G14-P1-15-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-15-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-15-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-15-B04` Implement and test explicit handling for: **stale legal verdict accepted from cache**.
- [ ] `G14-P1-15-B05` Implement and test explicit handling for: **clock skew makes expired data look fresh**.
- [ ] `G14-P1-15-B06` Implement and test explicit handling for: **long-running decision crosses TTL before finalization**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-15-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-15-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-15-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-15-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-15-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-15-D01` Instrument **input age distributions per source type**.
- [ ] `G14-P1-15-D02` Instrument **stale/future-timestamp rejection counts**.
- [ ] `G14-P1-15-D03` Instrument **clock-skew estimates and TTL headroom**.
- [ ] `G14-P1-15-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-15-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-15-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-15-E01` boundary tests at TTL-ε, TTL, and TTL+ε.
- [ ] `G14-P1-15-E02` simulate positive/negative clock skew.
- [ ] `G14-P1-15-E03` hold a request until evidence expires before finalization.
- [ ] `G14-P1-15-E04` verify different source classes honor different max-age rules.
- [ ] `G14-P1-15-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-15-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-15-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-15-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-15-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-15-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-15-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-15-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-15-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-15-G01` **Acceptance:** each time-sensitive source has documented and machine-enforced freshness rules.
- [ ] `G14-P1-15-G02` **Acceptance:** expired/future-invalid evidence yields stable fail-safe outcomes.
- [ ] `G14-P1-15-G03` **Acceptance:** decision provenance records enough timing information to audit freshness.
- [ ] `G14-P1-15-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-15-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-16 — Stale-data fail-safe policy

**Priority:** P1  
**Objective:** Define when cached or stale inputs may be used, when they must block decisions, and how degraded-mode behavior is made explicit and auditable.  
**Dependencies:** freshness rules, all authoritative adapters, operator policy.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-16-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-16-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-16-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-16-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-16-A05` Classify each input by safety criticality and define stale-use policy separately for legal policy, topology, prices, convergence, and capacity.
- [ ] `G14-P1-16-A06` Default legal/residency authorization and unverifiable convergence to fail closed; any exception must be explicitly approved and bounded.
- [ ] `G14-P1-16-A07` Define maximum degraded-mode age, allowed operation classes, and required operator/audit signaling for cache use.
- [ ] `G14-P1-16-A08` Never substitute stale data silently; mark decision quality/degraded status and the exact stale source in provenance.
- [ ] `G14-P1-16-A09` Prevent a stale cached allow from overriding a newer reachable deny/error revision.
- [ ] `G14-P1-16-A10` Define recovery behavior when fresh data resumes, including cache invalidation and circuit/state reset.

## B. Failure semantics and safety
- [ ] `G14-P1-16-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-16-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-16-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-16-B04` Implement and test explicit handling for: **stale allow permits newly illegal placement**.
- [ ] `G14-P1-16-B05` Implement and test explicit handling for: **cached cost silently drives materially wrong optimization**.
- [ ] `G14-P1-16-B06` Implement and test explicit handling for: **mixed fresh/stale sources create inconsistent decision semantics**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-16-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-16-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-16-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-16-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-16-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-16-D01` Instrument **degraded-mode decision count and stale source class**.
- [ ] `G14-P1-16-D02` Instrument **stale age at decision time**.
- [ ] `G14-P1-16-D03` Instrument **recovery/cache invalidation events**.
- [ ] `G14-P1-16-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-16-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-16-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-16-E01` make each dependency stale independently and verify configured behavior.
- [ ] `G14-P1-16-E02` publish newer deny after cached allow and verify stale cache cannot win.
- [ ] `G14-P1-16-E03` mix stale topology with fresh policy and verify provenance/decision flags.
- [ ] `G14-P1-16-E04` recover source and ensure degraded mode exits deterministically.
- [ ] `G14-P1-16-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-16-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-16-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-16-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-16-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-16-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-16-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-16-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-16-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-16-G01` **Acceptance:** no stale-data fallback is implicit.
- [ ] `G14-P1-16-G02` **Acceptance:** safety-critical stale data cannot authorize prohibited operations.
- [ ] `G14-P1-16-G03` **Acceptance:** all degraded decisions are identifiable, bounded, and auditable.
- [ ] `G14-P1-16-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-16-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-17 — Health/readiness endpoint or probe contract

**Priority:** P1  
**Objective:** Expose process liveness and decision-service readiness without leaking sensitive state or causing probe storms against dependencies.  
**Dependencies:** runtime host, adapter health state, configuration subsystem, metrics.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-17-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-17-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-17-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-17-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-17-A05` Separate liveness from readiness: liveness proves the process/event loop is functioning; readiness proves required configuration/capabilities/dependencies satisfy serving policy.
- [ ] `G14-P1-17-A06` Include active engine/config version, schema capability level, and dependency-state summary without exposing tokens, tenant data, raw URLs with credentials, or secret values.
- [ ] `G14-P1-17-A07` Use cached dependency health with bounded age so probes do not fan out synchronously on every orchestrator poll.
- [ ] `G14-P1-17-A08` Define critical versus optional dependency readiness impact and document degraded-serving rules.
- [ ] `G14-P1-17-A09` Return machine-readable stable status codes and component reason codes suitable for orchestration.
- [ ] `G14-P1-17-A10` Add startup and shutdown transitions so instances do not receive traffic before initialization or during drain.

## B. Failure semantics and safety
- [ ] `G14-P1-17-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-17-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-17-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-17-B04` Implement and test explicit handling for: **liveness tied to remote dependency causes restart loop**.
- [ ] `G14-P1-17-B05` Implement and test explicit handling for: **readiness says healthy despite missing mandatory adapter/config**.
- [ ] `G14-P1-17-B06` Implement and test explicit handling for: **probe leaks sensitive endpoint or identity data**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-17-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-17-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-17-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-17-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-17-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-17-D01` Instrument **readiness transitions by reason**.
- [ ] `G14-P1-17-D02` Instrument **startup initialization duration**.
- [ ] `G14-P1-17-D03` Instrument **probe request rate and internal dependency-health age**.
- [ ] `G14-P1-17-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-17-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-17-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-17-E01` kill/freeze mandatory adapters and verify readiness not liveness changes.
- [ ] `G14-P1-17-E02` start with invalid configuration and verify never-ready state.
- [ ] `G14-P1-17-E03` verify secrets/tenant IDs absent from probe payload.
- [ ] `G14-P1-17-E04` test graceful drain/readiness removal before shutdown.
- [ ] `G14-P1-17-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-17-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-17-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-17-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-17-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-17-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-17-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-17-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-17-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-17-G01` **Acceptance:** orchestrators can reliably distinguish dead, starting, ready, degraded, and draining states.
- [ ] `G14-P1-17-G02` **Acceptance:** probes are bounded and do not amplify dependency load.
- [ ] `G14-P1-17-G03` **Acceptance:** no sensitive operational data is exposed unauthenticated.
- [ ] `G14-P1-17-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-17-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-18 — Metrics exporter

**Priority:** P1  
**Objective:** Provide bounded-cardinality, production-grade operational metrics for decision volume, latency, errors, costs, eliminations, and dependency health.  
**Dependencies:** telemetry backend, runtime, all adapters.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-18-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-18-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-18-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-18-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-18-A05` Define counters for decisions, refusals, adapter errors, stale-input failures, eliminations, handoffs, config changes, and audit failures.
- [ ] `G14-P1-18-A06` Define latency histograms for total decision time and each dependency with buckets aligned to the p99 SLO and timeout budgets.
- [ ] `G14-P1-18-A07` Expose cost/size distributions using histograms/summaries that avoid tenant/dataset identifiers as labels.
- [ ] `G14-P1-18-A08` Document metric names, units, label allowlist, cardinality budget, and backward-compatibility policy.
- [ ] `G14-P1-18-A09` Export build/engine/config/schema version information through low-cardinality info metrics.
- [ ] `G14-P1-18-A10` Implement exporter failure isolation so telemetry outages cannot corrupt decision logic or block safety-critical evidence paths unless explicitly required.

## B. Failure semantics and safety
- [ ] `G14-P1-18-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-18-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-18-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-18-B04` Implement and test explicit handling for: **tenant/dataset label explosion exhausts metrics backend**.
- [ ] `G14-P1-18-B05` Implement and test explicit handling for: **wrong units/buckets make SLO unreadable**.
- [ ] `G14-P1-18-B06` Implement and test explicit handling for: **metrics failure affects decision correctness**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-18-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-18-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-18-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-18-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-18-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-18-D01` Instrument **self-metrics for scrape/export success and dropped observations**.
- [ ] `G14-P1-18-D02` Instrument **series cardinality estimates**.
- [ ] `G14-P1-18-D03` Instrument **instrumentation overhead**.
- [ ] `G14-P1-18-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-18-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-18-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-18-E01` load high-identity-cardinality traffic and verify bounded series count.
- [ ] `G14-P1-18-E02` validate metric names/types/units against a contract.
- [ ] `G14-P1-18-E03` measure instrumentation overhead under benchmark load.
- [ ] `G14-P1-18-E04` disconnect metrics backend and verify decision path remains correct.
- [ ] `G14-P1-18-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-18-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-18-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-18-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-18-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-18-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-18-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-18-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-18-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-18-G01` **Acceptance:** required SLO/error/security dashboards can be built from documented metrics.
- [ ] `G14-P1-18-G02` **Acceptance:** metric cardinality remains within budget under worst-case tenant volume.
- [ ] `G14-P1-18-G03` **Acceptance:** instrumentation does not materially violate the decision latency target.
- [ ] `G14-P1-18-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-18-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-19 — Structured logging and trace-context propagation

**Priority:** P1  
**Objective:** Produce machine-parseable, correlated diagnostics across services while enforcing redaction and bounded data exposure.  
**Dependencies:** logging backend, OpenTelemetry or estate tracing standard, identity/redaction policy.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-19-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-19-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-19-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-19-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-19-A05` Emit structured records with timestamp, severity, event code, decision ID, trace/span IDs, engine/config versions, and stable reason codes.
- [ ] `G14-P1-19-A06` Accept and validate standard trace context at ingress and propagate it through GAP-13/GAP-03/GAP-05/SCH-01/PLN-06 calls.
- [ ] `G14-P1-19-A07` Define a strict redaction/classification policy for tenant, dataset, workload, paths, topology details, tokens, signatures, and raw payloads.
- [ ] `G14-P1-19-A08` Use opaque/hardened correlation identifiers instead of raw sensitive identifiers when operational correlation is needed.
- [ ] `G14-P1-19-A09` Implement log-size limits and truncation rules that preserve the event code and correlation metadata.
- [ ] `G14-P1-19-A10` Define sampling rules so errors/security events are retained while high-volume success traces can be sampled predictably.

## B. Failure semantics and safety
- [ ] `G14-P1-19-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-19-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-19-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-19-B04` Implement and test explicit handling for: **credential or sensitive identifier written to logs**.
- [ ] `G14-P1-19-B05` Implement and test explicit handling for: **broken trace propagation prevents cross-service diagnosis**.
- [ ] `G14-P1-19-B06` Implement and test explicit handling for: **unbounded payload logging causes storage/latency pressure**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-19-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-19-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-19-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-19-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-19-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-19-D01` Instrument **log/trace export failures and queue depth**.
- [ ] `G14-P1-19-D02` Instrument **trace propagation completeness rate**.
- [ ] `G14-P1-19-D03` Instrument **redaction-rule violations detected by tests/scanners**.
- [ ] `G14-P1-19-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-19-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-19-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-19-E01` seed canary secrets/PII-like identifiers and assert they never appear in logs.
- [ ] `G14-P1-19-E02` verify one decision yields a continuous cross-service trace.
- [ ] `G14-P1-19-E03` send oversized/malformed payloads and verify safe truncation.
- [ ] `G14-P1-19-E04` exercise sampling and ensure error/security events remain retained.
- [ ] `G14-P1-19-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-19-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-19-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-19-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-19-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-19-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-19-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-19-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-19-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-19-G01` **Acceptance:** operators can correlate a decision across dependencies without raw sensitive data.
- [ ] `G14-P1-19-G02` **Acceptance:** redaction tests are mandatory in CI.
- [ ] `G14-P1-19-G03` **Acceptance:** logging/tracing failure cannot silently alter decision semantics.
- [ ] `G14-P1-19-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-19-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-20 — Operator explain endpoint/view

**Priority:** P1  
**Objective:** Give authorized operators a deterministic explanation of selected and eliminated options tied to exact input evidence, without exposing protected internals or secrets.  
**Dependencies:** provenance store, authorization layer, audit sink, decision schema.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-20-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-20-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-20-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-20-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-20-A05` Define a read-only explanation schema containing selected direction, cost breakdown, candidate alternatives, eliminated options, reason codes, and source snapshot references.
- [ ] `G14-P1-20-A06` Require operator authentication/authorization and tenant-scope checks before revealing decision details.
- [ ] `G14-P1-20-A07` Use provenance references to retrieve the exact historical snapshots used rather than recomputing against current state.
- [ ] `G14-P1-20-A08` Clearly distinguish factual input values, policy constraints, and optimization calculations to prevent ambiguous interpretation.
- [ ] `G14-P1-20-A09` Redact secrets, credentials, raw signatures, and protected tenant/dataset fields according to role.
- [ ] `G14-P1-20-A10` Audit every explanation access with operator identity, decision ID, purpose/action, and result.

## B. Failure semantics and safety
- [ ] `G14-P1-20-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-20-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-20-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-20-B04` Implement and test explicit handling for: **explanation recomputed with current data differs from historical decision**.
- [ ] `G14-P1-20-B05` Implement and test explicit handling for: **operator views cross-tenant details**.
- [ ] `G14-P1-20-B06` Implement and test explicit handling for: **UI/API exposes credentials or internal secret material**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-20-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-20-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-20-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-20-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-20-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-20-D01` Instrument **explain request count/latency/denies**.
- [ ] `G14-P1-20-D02` Instrument **historical evidence retrieval failures**.
- [ ] `G14-P1-20-D03` Instrument **redaction events**.
- [ ] `G14-P1-20-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-20-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-20-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-20-E01` retrieve explanations after topology/config changes and verify historical fidelity.
- [ ] `G14-P1-20-E02` attempt unauthorized/cross-tenant access.
- [ ] `G14-P1-20-E03` verify cost arithmetic against engine output.
- [ ] `G14-P1-20-E04` run snapshot/redaction golden tests.
- [ ] `G14-P1-20-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-20-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-20-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-20-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-20-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-20-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-20-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-20-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-20-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-20-G01` **Acceptance:** an authorized operator can account for every selected/eliminated option from immutable evidence.
- [ ] `G14-P1-20-G02` **Acceptance:** explain is side-effect free and cannot trigger execution.
- [ ] `G14-P1-20-G03` **Acceptance:** access control and redaction are test-proven.
- [ ] `G14-P1-20-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-20-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-21 — Admission control and resource bounds

**Priority:** P1  
**Objective:** Protect the service from overload and malicious/unbounded payloads by constraining request size, batch volume, concurrency, memory, and expensive graph/map structures.  
**Dependencies:** API host, timeout/backpressure policy, metrics.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-21-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-21-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-21-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-21-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-21-A05` Set explicit byte-size and nesting/depth limits for serialized requests before full materialization.
- [ ] `G14-P1-21-A06` Set maximum dataset count, candidate sites, route-map entries, batch items, and string lengths per request/schema.
- [ ] `G14-P1-21-A07` Enforce global and per-tenant/service-principal concurrency/rate limits with documented fairness strategy.
- [ ] `G14-P1-21-A08` Use bounded worker pools/queues and reject early when admission budgets are exhausted.
- [ ] `G14-P1-21-A09` Estimate or cap computational complexity for DAG/route optimization features before accepting work.
- [ ] `G14-P1-21-A10` Define memory/CPU watchdog thresholds and safe process/orchestrator behavior under sustained pressure.

## B. Failure semantics and safety
- [ ] `G14-P1-21-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-21-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-21-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-21-B04` Implement and test explicit handling for: **oversized map/list exhausts memory**.
- [ ] `G14-P1-21-B05` Implement and test explicit handling for: **one tenant monopolizes workers**.
- [ ] `G14-P1-21-B06` Implement and test explicit handling for: **pathological graph causes superlinear CPU spike**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-21-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-21-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-21-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-21-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-21-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-21-D01` Instrument **admission rejects by limit**.
- [ ] `G14-P1-21-D02` Instrument **request-size/batch-size histograms**.
- [ ] `G14-P1-21-D03` Instrument **CPU/memory/queue saturation indicators**.
- [ ] `G14-P1-21-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-21-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-21-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-21-E01` fuzz maximum/deep payload structures.
- [ ] `G14-P1-21-E02` burst one tenant versus multiple tenants and verify fairness.
- [ ] `G14-P1-21-E03` send worst-case candidate/route cardinality at limits.
- [ ] `G14-P1-21-E04` run memory/CPU profiling under rejection pressure.
- [ ] `G14-P1-21-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-21-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-21-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-21-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-21-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-21-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-21-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-21-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-21-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-21-G01` **Acceptance:** all externally controllable resource dimensions have documented hard limits.
- [ ] `G14-P1-21-G02` **Acceptance:** over-limit work is rejected before expensive processing.
- [ ] `G14-P1-21-G03` **Acceptance:** stress tests demonstrate bounded memory and queue growth.
- [ ] `G14-P1-21-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-21-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-22 — Fuzz and property testing

**Priority:** P1  
**Objective:** Systematically explore malformed schemas, identifiers, numeric edge cases, configuration maps, and algebraic invariants beyond hand-written examples.  
**Dependencies:** test framework, schema models, engine/adapters.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-22-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-22-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-22-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-22-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-22-A05` Adopt a property-based test framework suitable for the supported Python range and pin it in test dependencies.
- [ ] `G14-P1-22-A06` Generate schema-valid and schema-invalid inputs for datasets, sites, route maps, pricing, policy verdicts, config, and provenance.
- [ ] `G14-P1-22-A07` Include Unicode normalization, control characters, extreme lengths, duplicate/colliding identifiers, and reserved delimiter cases.
- [ ] `G14-P1-22-A08` Generate numeric boundaries including zero, subnormal, max finite, negative, NaN, ±infinity, and precision-sensitive ties.
- [ ] `G14-P1-22-A09` Define engine properties such as determinism, immutability of inputs, no negative costs, no illegal option selection, and tie-policy stability.
- [ ] `G14-P1-22-A10` Persist minimal failing examples as regression fixtures and seed/reproduce randomized CI runs.

## B. Failure semantics and safety
- [ ] `G14-P1-22-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-22-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-22-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-22-B04` Implement and test explicit handling for: **parser crash on malformed input**.
- [ ] `G14-P1-22-B05` Implement and test explicit handling for: **non-deterministic decision for identical snapshots**.
- [ ] `G14-P1-22-B06` Implement and test explicit handling for: **numeric edge case bypasses validation**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-22-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-22-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-22-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-22-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-22-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-22-D01` Instrument **fuzz/property case counts and shrink failures in CI artifacts**.
- [ ] `G14-P1-22-D02` Instrument **coverage deltas for fuzz targets**.
- [ ] `G14-P1-22-D03` Instrument **unique crash/invariant signatures**.
- [ ] `G14-P1-22-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-22-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-22-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-22-E01` run targeted property suites for each public schema.
- [ ] `G14-P1-22-E02` mutation-test validation guards to prove tests fail when checks are removed.
- [ ] `G14-P1-22-E03` longer nightly randomized campaigns.
- [ ] `G14-P1-22-E04` replay all previously minimized failures on every release.
- [ ] `G14-P1-22-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-22-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-22-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-22-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-22-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-22-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-22-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-22-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-22-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-22-G01` **Acceptance:** all public input models have property-based coverage.
- [ ] `G14-P1-22-G02` **Acceptance:** no unhandled exception occurs for arbitrary bounded untrusted input.
- [ ] `G14-P1-22-G03` **Acceptance:** critical invariants are encoded as executable properties.
- [ ] `G14-P1-22-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-22-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-23 — Performance, soak, and burst benchmarks

**Priority:** P1  
**Objective:** Demonstrate the stated p99 decision-latency objective and resource stability under representative steady-state, long-duration, and burst workloads.  
**Dependencies:** benchmark harness, representative hardware, metrics, adapter fixtures.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-23-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-23-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-23-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-23-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-23-A05` Define representative traffic mixes by dataset size, candidate-site count, route-map size, cache state, and adapter latency.
- [ ] `G14-P1-23-A06` Separate pure engine latency from end-to-end service latency and report both.
- [ ] `G14-P1-23-A07` Measure p50/p95/p99/max latency, throughput, CPU, memory, allocation/GC behavior, queue wait, and downstream budget usage.
- [ ] `G14-P1-23-A08` Run warm-up before measurement and pin host/runtime configuration to make results comparable across releases.
- [ ] `G14-P1-23-A09` Create sustained soak profiles long enough to expose leaks, queue creep, descriptor leaks, and periodic refresh interactions.
- [ ] `G14-P1-23-A10` Create controlled burst tests above nominal traffic to verify admission control and recovery without an extended latency tail.

## B. Failure semantics and safety
- [ ] `G14-P1-23-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-23-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-23-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-23-B04` Implement and test explicit handling for: **microbenchmark meets target while end-to-end path does not**.
- [ ] `G14-P1-23-B05` Implement and test explicit handling for: **memory/descriptor leak appears only during long soak**.
- [ ] `G14-P1-23-B06` Implement and test explicit handling for: **burst causes queue backlog that persists after load subsides**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-23-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-23-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-23-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-23-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-23-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-23-D01` Instrument **benchmark time series and percentile distributions**.
- [ ] `G14-P1-23-D02` Instrument **resource utilization and GC/allocation rates**.
- [ ] `G14-P1-23-D03` Instrument **baseline-versus-candidate regression percentages**.
- [ ] `G14-P1-23-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-23-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-23-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-23-E01` benchmark engine-only deterministic fixtures.
- [ ] `G14-P1-23-E02` benchmark full adapters with representative dependency latency.
- [ ] `G14-P1-23-E03` multi-hour soak with periodic config/topology refresh.
- [ ] `G14-P1-23-E04` burst to defined multiples of target QPS and observe recovery.
- [ ] `G14-P1-23-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-23-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-23-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-23-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-23-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-23-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-23-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-23-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-23-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-23-G01` **Acceptance:** p99 < 50 ms is demonstrated for the explicitly defined target profile or the SLO is revised transparently.
- [ ] `G14-P1-23-G02` **Acceptance:** no sustained resource leak is observed in soak criteria.
- [ ] `G14-P1-23-G03` **Acceptance:** release CI blocks on agreed statistically meaningful regressions.
- [ ] `G14-P1-23-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-23-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-24 — Fault-injection suite

**Priority:** P1  
**Objective:** Verify safe, deterministic behavior under dependency loss, stale/corrupt inputs, partitions, time faults, and partial internal failures.  
**Dependencies:** integration harness, adapter test doubles/proxies, observability.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-24-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-24-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-24-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-24-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-24-A05` Create injectable failure controls for timeout, connection reset, DNS/service discovery failure, malformed response, wrong signature, stale timestamp, and slow response.
- [ ] `G14-P1-24-A06` Support partial partitions where one dependency or one route/site is unreachable while others remain healthy.
- [ ] `G14-P1-24-A07` Inject cost-feed corruption including extreme finite values, missing fields, schema mismatch, and inconsistent snapshot revision.
- [ ] `G14-P1-24-A08` Inject clock skew/jumps within the test environment to validate TTL and provenance behavior.
- [ ] `G14-P1-24-A09` Inject audit/telemetry sink failure independently to distinguish mandatory evidence from best-effort observability.
- [ ] `G14-P1-24-A10` Ensure every injected fault maps to an expected stable error/elimination/degraded-mode code and documented recovery behavior.

## B. Failure semantics and safety
- [ ] `G14-P1-24-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-24-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-24-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-24-B04` Implement and test explicit handling for: **fault leads to unsafe default rather than refusal**.
- [ ] `G14-P1-24-B05` Implement and test explicit handling for: **recovery requires process restart unnecessarily**.
- [ ] `G14-P1-24-B06` Implement and test explicit handling for: **multiple simultaneous faults create undocumented state**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-24-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-24-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-24-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-24-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-24-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-24-D01` Instrument **injected fault ID correlated in traces**.
- [ ] `G14-P1-24-D02` Instrument **recovery duration/circuit behavior**.
- [ ] `G14-P1-24-D03` Instrument **unexpected error-code or readiness-state deviations**.
- [ ] `G14-P1-24-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-24-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-24-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-24-E01` single-fault matrix for every adapter.
- [ ] `G14-P1-24-E02` pairwise/multi-fault scenarios for high-risk combinations.
- [ ] `G14-P1-24-E03` fault during configuration/topology refresh.
- [ ] `G14-P1-24-E04` fault at PLN-06 handoff lifecycle boundaries.
- [ ] `G14-P1-24-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-24-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-24-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-24-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-24-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-24-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-24-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-24-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-24-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-24-G01` **Acceptance:** all defined high-risk faults have deterministic expected outcomes.
- [ ] `G14-P1-24-G02` **Acceptance:** no tested dependency corruption authorizes an illegal move.
- [ ] `G14-P1-24-G03` **Acceptance:** service recovers automatically where policy says recovery is supported.
- [ ] `G14-P1-24-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-24-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-25 — Compatibility matrix

**Priority:** P1  
**Objective:** Make supported combinations of Python, schemas, pk_core, GAP/SCH/PLN services, and packaging explicit and continuously tested.  
**Dependencies:** CI matrix, release management, adjacent service version policies.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-25-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-25-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-25-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-25-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-25-A05` Define minimum/maximum supported Python versions and architectures/operating systems where applicable.
- [ ] `G14-P1-25-A06` Define compatible engine/API/schema versions for GAP-13, GAP-03, GAP-05, SCH-01, PLN-06, and `pk_core`.
- [ ] `G14-P1-25-A07` Distinguish backward-compatible, forward-compatible, deprecated, and explicitly unsupported combinations.
- [ ] `G14-P1-25-A08` Automate matrix generation from source-controlled compatibility metadata rather than a manually drifting wiki.
- [ ] `G14-P1-25-A09` Run contract/integration tests for all mandatory combinations and a selected set of adjacent-version upgrade paths.
- [ ] `G14-P1-25-A10` Define deprecation notice periods and removal gates for old schema/runtime versions.

## B. Failure semantics and safety
- [ ] `G14-P1-25-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-25-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-25-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-25-B04` Implement and test explicit handling for: **unverified version combination reaches production**.
- [ ] `G14-P1-25-B05` Implement and test explicit handling for: **schema consumer silently ignores new mandatory field**.
- [ ] `G14-P1-25-B06` Implement and test explicit handling for: **deprecation removes support before dependent systems migrate**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-25-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-25-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-25-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-25-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-25-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-25-D01` Instrument **runtime-observed version combinations**.
- [ ] `G14-P1-25-D02` Instrument **unsupported/deprecated client usage**.
- [ ] `G14-P1-25-D03` Instrument **CI coverage of matrix cells**.
- [ ] `G14-P1-25-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-25-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-25-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-25-E01` minimum and maximum supported Python runs.
- [ ] `G14-P1-25-E02` old/new adjacent service contract fixtures.
- [ ] `G14-P1-25-E03` rolling-upgrade mixed-version scenario.
- [ ] `G14-P1-25-E04` explicit rejection of unsupported major/schema versions.
- [ ] `G14-P1-25-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-25-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-25-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-25-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-25-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-25-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-25-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-25-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-25-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-25-G01` **Acceptance:** every supported production combination appears in a source-controlled matrix.
- [ ] `G14-P1-25-G02` **Acceptance:** mandatory cells have automated evidence.
- [ ] `G14-P1-25-G03` **Acceptance:** unsupported combinations fail early with actionable diagnostics.
- [ ] `G14-P1-25-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-25-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-26 — Dependency and supply-chain policy

**Priority:** P1  
**Objective:** Control third-party and internal dependencies through locking, SBOMs, integrity verification, provenance, vulnerability response, and signed releases.  
**Dependencies:** package registry, CI/CD, signing/KMS, vulnerability scanners.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-26-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-26-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-26-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-26-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-26-A05` Lock all runtime/build/test dependencies to reviewed versions with hashes where the packaging ecosystem supports it.
- [ ] `G14-P1-26-A06` Generate an SBOM for every release containing direct/transitive dependencies, versions, licenses, and package identifiers.
- [ ] `G14-P1-26-A07` Verify package/release signatures or trusted hashes before installation and define approved registries/mirrors.
- [ ] `G14-P1-26-A08` Produce build provenance/attestation identifying source revision, builder, dependency lock, build parameters, and artifact digests.
- [ ] `G14-P1-26-A09` Scan dependencies and artifacts for known vulnerabilities and define severity-based block/exception/expiry policy.
- [ ] `G14-P1-26-A10` Prevent dependency confusion/typosquatting through namespace controls, source priority, and internal package naming policy.

## B. Failure semantics and safety
- [ ] `G14-P1-26-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-26-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-26-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-26-B04` Implement and test explicit handling for: **unlocked transitive dependency changes release behavior**.
- [ ] `G14-P1-26-B05` Implement and test explicit handling for: **artifact replaced after build**.
- [ ] `G14-P1-26-B06` Implement and test explicit handling for: **critical vulnerability ships without explicit exception**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-26-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-26-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-26-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-26-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-26-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-26-D01` Instrument **dependency/SBOM scan findings by severity**.
- [ ] `G14-P1-26-D02` Instrument **signature/provenance verification status**.
- [ ] `G14-P1-26-D03` Instrument **exception age and expiry**.
- [ ] `G14-P1-26-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-26-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-26-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-26-E01` rebuild from lock in a clean environment and compare dependency set.
- [ ] `G14-P1-26-E02` tamper package/artifact and verify integrity failure.
- [ ] `G14-P1-26-E03` simulate unavailable public registry and ensure no unsafe fallback source.
- [ ] `G14-P1-26-E04` validate SBOM completeness against installed environment.
- [ ] `G14-P1-26-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-26-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-26-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-26-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-26-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-26-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-26-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-26-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-26-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-26-G01` **Acceptance:** every release has a verifiable SBOM and artifact digest/signature/provenance record.
- [ ] `G14-P1-26-G02` **Acceptance:** unapproved dependency changes fail CI.
- [ ] `G14-P1-26-G03` **Acceptance:** critical supply-chain exceptions are explicit, owned, and time-bounded.
- [ ] `G14-P1-26-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-26-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P1-27 — Packaging metadata

**Priority:** P1  
**Objective:** Provide standards-compliant package metadata, reproducible wheel/sdist artifacts, versioning, supported-Python declaration, and dependency separation.  
**Dependencies:** Python build backend, release pipeline, package registry.

## A. Architecture, ownership, and requirements
- [ ] `G14-P1-27-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P1-27-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P1-27-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P1-27-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P1-27-A05` Add `pyproject.toml` (or estate-approved equivalent) with project name, semantic version, description, license, authors/maintainers, Python range, and classifiers.
- [ ] `G14-P1-27-A06` Declare runtime, optional integration, development, test, benchmark, and documentation dependencies in separated groups/extras.
- [ ] `G14-P1-27-A07` Use one authoritative version source and verify package metadata, `__version__`, release docs, and artifact names remain synchronized.
- [ ] `G14-P1-27-A08` Define import package layout, public API exports, type information policy, and console entry points if applicable.
- [ ] `G14-P1-27-A09` Build wheel and source distribution in an isolated environment and exclude caches, secrets, local paths, and unintended large files.
- [ ] `G14-P1-27-A10` Publish hashes/signatures and validate install/uninstall behavior in a clean virtual environment.

## B. Failure semantics and safety
- [ ] `G14-P1-27-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P1-27-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P1-27-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P1-27-B04` Implement and test explicit handling for: **metadata version differs from runtime version**.
- [ ] `G14-P1-27-B05` Implement and test explicit handling for: **undeclared dependency works only on developer machine**.
- [ ] `G14-P1-27-B06` Implement and test explicit handling for: **sdist/wheel contains local secret or path artifact**.

## C. Security, integrity, and data protection
- [ ] `G14-P1-27-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P1-27-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P1-27-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P1-27-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P1-27-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P1-27-D01` Instrument **build/install validation results in release evidence**.
- [ ] `G14-P1-27-D02` Instrument **artifact size/file inventory changes**.
- [ ] `G14-P1-27-D03` Instrument **supported Python environment matrix**.
- [ ] `G14-P1-27-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P1-27-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P1-27-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P1-27-E01` build and install wheel/sdist on all supported Python versions.
- [ ] `G14-P1-27-E02` import/test from installed artifact rather than source tree.
- [ ] `G14-P1-27-E03` inspect package contents against allowlist/denylist.
- [ ] `G14-P1-27-E04` verify deterministic metadata and version synchronization.
- [ ] `G14-P1-27-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P1-27-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P1-27-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P1-27-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P1-27-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P1-27-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P1-27-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P1-27-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P1-27-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P1-27-G01` **Acceptance:** clean installation requires no ambient developer dependencies.
- [ ] `G14-P1-27-G02` **Acceptance:** artifact metadata accurately declares support and dependencies.
- [ ] `G14-P1-27-G03` **Acceptance:** release artifacts pass content/integrity inspection.
- [ ] `G14-P1-27-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P1-27-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-28 — Partial dataset movement and sharding model

**Priority:** P2  
**Objective:** Optimize movement at shard/partition granularity while preserving legal placement, identity, lineage, consistency, and reconstruction semantics.  
**Dependencies:** dataset metadata service, GAP-05, PLN-06, policy engine.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-28-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-28-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-28-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-28-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-28-A05` Define immutable shard/partition identity, dataset generation, range/key-space membership, parent dataset ID, and content/integrity hash.
- [ ] `G14-P2-28-A06` Represent per-shard size, current replica locations, residency constraints, convergence state, and movement eligibility.
- [ ] `G14-P2-28-A07` Define legality rules for splitting datasets whose policy obligations apply at dataset, record, tenant, or jurisdictional granularity.
- [ ] `G14-P2-28-A08` Compute movement/compute costs per shard and aggregate without double-counting shared fixed costs or transfer reuse.
- [ ] `G14-P2-28-A09` Define reconstruction/completeness semantics so partial moves cannot be interpreted as a complete dataset placement.
- [ ] `G14-P2-28-A10` Integrate shard handoff with idempotent PLN-06 operations and per-shard completion evidence.

## B. Failure semantics and safety
- [ ] `G14-P2-28-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-28-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-28-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-28-B04` Implement and test explicit handling for: **shard split crosses a legal/data-classification boundary**.
- [ ] `G14-P2-28-B05` Implement and test explicit handling for: **cost model double-counts or omits fixed transfer charges**.
- [ ] `G14-P2-28-B06` Implement and test explicit handling for: **partial completion exposed as complete dataset availability**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-28-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-28-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-28-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-28-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-28-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-28-D01` Instrument **shard counts/bytes moved and partial completion**.
- [ ] `G14-P2-28-D02` Instrument **per-shard elimination reasons**.
- [ ] `G14-P2-28-D03` Instrument **reconstruction/convergence failures**.
- [ ] `G14-P2-28-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-28-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-28-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-28-E01` partition boundary/coverage/no-overlap properties.
- [ ] `G14-P2-28-E02` mixed-legal-shard scenario.
- [ ] `G14-P2-28-E03` partial transfer interruption and resume.
- [ ] `G14-P2-28-E04` cost equivalence tests for whole-dataset versus shard aggregation under defined assumptions.
- [ ] `G14-P2-28-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-28-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-28-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-28-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-28-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-28-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-28-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-28-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-28-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-28-G01` **Acceptance:** every shard has traceable lineage and policy scope.
- [ ] `G14-P2-28-G02` **Acceptance:** partial state is explicit and cannot masquerade as whole-dataset state.
- [ ] `G14-P2-28-G03` **Acceptance:** cost and convergence semantics are documented and property-tested.
- [ ] `G14-P2-28-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-28-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-29 — Repeated-job amortization model

**Priority:** P2  
**Objective:** Account for repeated workloads where transfer, cache, compilation, and warm-up costs can be amortized across a bounded execution horizon.  
**Dependencies:** workload history, scheduler, cache/runtime telemetry, cost model.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-29-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-29-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-29-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-29-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-29-A05` Define a recurrence model with workload identity, expected run count/frequency, horizon, confidence, and invalidation conditions.
- [ ] `G14-P2-29-A06` Separate one-time costs (data transfer, image pull, compilation, cache fill) from per-run costs and persistent storage/caching costs.
- [ ] `G14-P2-29-A07` Model cache/warm-state lifetime and eviction probability rather than assuming indefinite reuse.
- [ ] `G14-P2-29-A08` Prevent speculative future runs from justifying illegal or capacity-infeasible placement in the present.
- [ ] `G14-P2-29-A09` Record the assumed recurrence horizon and amortization inputs in decision provenance.
- [ ] `G14-P2-29-A10` Provide conservative fallback to single-run economics when recurrence confidence is below a configured threshold.

## B. Failure semantics and safety
- [ ] `G14-P2-29-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-29-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-29-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-29-B04` Implement and test explicit handling for: **optimistic recurrence causes large transfer with no reuse**.
- [ ] `G14-P2-29-B05` Implement and test explicit handling for: **stale cache assumption understates future cost**.
- [ ] `G14-P2-29-B06` Implement and test explicit handling for: **different workload revision incorrectly reuses prior warm-state benefits**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-29-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-29-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-29-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-29-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-29-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-29-D01` Instrument **predicted versus realized repeated-run count**.
- [ ] `G14-P2-29-D02` Instrument **cache/warm hit rate and retained duration**.
- [ ] `G14-P2-29-D03` Instrument **amortized versus single-run decision divergence**.
- [ ] `G14-P2-29-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-29-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-29-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-29-E01` one-run, N-run, and uncertain recurrence scenarios.
- [ ] `G14-P2-29-E02` cache expiry/eviction between runs.
- [ ] `G14-P2-29-E03` workload revision invalidating warm state.
- [ ] `G14-P2-29-E04` compare predicted amortized cost with observed execution sequence.
- [ ] `G14-P2-29-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-29-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-29-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-29-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-29-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-29-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-29-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-29-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-29-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-29-G01` **Acceptance:** amortization assumptions are explicit, bounded, and auditable.
- [ ] `G14-P2-29-G02` **Acceptance:** single-run fallback is deterministic when evidence is weak.
- [ ] `G14-P2-29-G03` **Acceptance:** historical calibration can measure whether amortization predictions were realized.
- [ ] `G14-P2-29-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-29-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-30 — Replication as a third decision option

**Priority:** P2  
**Objective:** Evaluate creating/maintaining a replica as an explicit alternative to moving compute or relocating the sole working data copy.  
**Dependencies:** GAP-05, PLN-06, storage cost model, policy engine.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-30-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-30-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-30-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-30-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-30-A05` Add a versioned `replicate_data` candidate with explicit semantics distinct from destructive move/relocation.
- [ ] `G14-P2-30-A06` Model initial transfer, ongoing synchronization, storage, request/IO, consistency, retention, and deletion/lifecycle costs.
- [ ] `G14-P2-30-A07` Require policy authorization for both destination replica creation and ongoing retention of an additional copy.
- [ ] `G14-P2-30-A08` Define consistency mode and acceptable lag; incorporate synchronization/network costs and workload read/write pattern.
- [ ] `G14-P2-30-A09` Define replica lifecycle ownership, expiry, garbage collection, and deletion attestation.
- [ ] `G14-P2-30-A10` Prevent replica option from bypassing capacity quota, encryption domain, or dataset-classification requirements.

## B. Failure semantics and safety
- [ ] `G14-P2-30-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-30-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-30-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-30-B04` Implement and test explicit handling for: **cheap initial replica hides expensive ongoing sync/storage**.
- [ ] `G14-P2-30-B05` Implement and test explicit handling for: **replica persists beyond authorized retention**.
- [ ] `G14-P2-30-B06` Implement and test explicit handling for: **replication lag violates workload consistency needs**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-30-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-30-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-30-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-30-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-30-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-30-D01` Instrument **replicate option selected/eliminated and reason**.
- [ ] `G14-P2-30-D02` Instrument **replica lifetime/storage/sync cost**.
- [ ] `G14-P2-30-D03` Instrument **lag/convergence and lifecycle deletion status**.
- [ ] `G14-P2-30-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-30-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-30-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-30-E01` read-heavy versus write-heavy economics.
- [ ] `G14-P2-30-E02` policy allows move but forbids replica and vice versa.
- [ ] `G14-P2-30-E03` replica TTL/deletion lifecycle.
- [ ] `G14-P2-30-E04` network partition and convergence-lag behavior.
- [ ] `G14-P2-30-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-30-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-30-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-30-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-30-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-30-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-30-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-30-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-30-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-30-G01` **Acceptance:** replication cost includes full lifecycle, not only copy cost.
- [ ] `G14-P2-30-G02` **Acceptance:** extra-copy legality/retention is explicitly authorized.
- [ ] `G14-P2-30-G03` **Acceptance:** created replicas have observable lifecycle and verified deletion/expiry behavior.
- [ ] `G14-P2-30-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-30-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-31 — Multi-dataset and DAG-aware gravity optimization

**Priority:** P2  
**Objective:** Optimize placement across workload DAGs and multiple datasets while respecting dependencies, legality, resource constraints, and combinatorial complexity.  
**Dependencies:** workflow/DAG model, scheduler, policy engine, topology/cost model.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-31-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-31-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-31-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-31-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-31-A05` Define a DAG schema with task IDs, edges, dataset inputs/outputs, sizes, compute requirements, ordering, fan-in/fan-out, and locality constraints.
- [ ] `G14-P2-31-A06` Validate graph acyclicity (or explicitly support bounded iterative graphs) and reject malformed/missing references.
- [ ] `G14-P2-31-A07` Model intermediate data creation and movement rather than treating only original source datasets.
- [ ] `G14-P2-31-A08` Optimize total workflow objective including transfer, compute, storage, critical-path latency, and hard placement/policy constraints.
- [ ] `G14-P2-31-A09` Use algorithmic complexity guards, pruning, heuristics, or solver time limits so large DAGs cannot monopolize resources.
- [ ] `G14-P2-31-A10` Return an explainable plan with per-node placement, data movement edges, costs, eliminations, and objective decomposition.

## B. Failure semantics and safety
- [ ] `G14-P2-31-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-31-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-31-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-31-B04` Implement and test explicit handling for: **locally optimal pairwise decisions create globally expensive DAG plan**.
- [ ] `G14-P2-31-B05` Implement and test explicit handling for: **intermediate dataset residency is omitted**.
- [ ] `G14-P2-31-B06` Implement and test explicit handling for: **large graph causes unbounded search time**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-31-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-31-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-31-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-31-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-31-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-31-D01` Instrument **DAG size/edge count/solver time**.
- [ ] `G14-P2-31-D02` Instrument **objective decomposition and heuristic/optimality status**.
- [ ] `G14-P2-31-D03` Instrument **pruned/eliminated placements**.
- [ ] `G14-P2-31-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-31-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-31-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-31-E01` known small DAGs with analytically known optimum.
- [ ] `G14-P2-31-E02` fan-in/fan-out and intermediate-data scenarios.
- [ ] `G14-P2-31-E03` policy restriction on one DAG edge/node.
- [ ] `G14-P2-31-E04` large bounded graph to validate timeout/complexity controls.
- [ ] `G14-P2-31-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-31-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-31-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-31-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-31-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-31-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-31-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-31-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-31-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-31-G01` **Acceptance:** workflow decisions respect all per-node/per-dataset hard constraints.
- [ ] `G14-P2-31-G02` **Acceptance:** solver/heuristic status is explicit and bounded.
- [ ] `G14-P2-31-G03` **Acceptance:** plan cost can be decomposed and independently recomputed.
- [ ] `G14-P2-31-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-31-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-32 — Carbon, power, and thermal cost dimension

**Priority:** P2  
**Objective:** Incorporate energy/carbon intensity and constrained-site power/thermal headroom as explicit optimization dimensions without overriding hard policy constraints.  
**Dependencies:** site telemetry, carbon-intensity feed, power/thermal scheduler data, policy/config.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-32-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-32-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-32-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-32-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-32-A05` Define units and sources for grid carbon intensity, renewable attribution, power price, energy per compute unit, thermal headroom, and site power caps.
- [ ] `G14-P2-32-A06` Timestamp and version environmental inputs with freshness/quality metadata and reject unknown units or stale critical telemetry.
- [ ] `G14-P2-32-A07` Normalize carbon/power/thermal signals into transparent objective terms or constraints; do not mix units without explicit weighting.
- [ ] `G14-P2-32-A08` Separate hard site power/thermal safety constraints from soft sustainability preferences.
- [ ] `G14-P2-32-A09` Account for transfer energy where sufficiently modeled, or explicitly document exclusions to avoid false precision.
- [ ] `G14-P2-32-A10` Record weighting/policy configuration and environmental snapshot in provenance.

## B. Failure semantics and safety
- [ ] `G14-P2-32-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-32-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-32-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-32-B04` Implement and test explicit handling for: **unit conversion error changes placement**.
- [ ] `G14-P2-32-B05` Implement and test explicit handling for: **stale carbon feed treated as current**.
- [ ] `G14-P2-32-B06` Implement and test explicit handling for: **soft carbon objective overrides thermal safety or residency law**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-32-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-32-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-32-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-32-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-32-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-32-D01` Instrument **selected-site carbon/power/thermal estimates**.
- [ ] `G14-P2-32-D02` Instrument **constraint eliminations due to headroom**.
- [ ] `G14-P2-32-D03` Instrument **feed freshness/quality and objective contribution**.
- [ ] `G14-P2-32-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-32-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-32-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-32-E01` unit conversion and boundary tests.
- [ ] `G14-P2-32-E02` thermal cap hard-failure scenario.
- [ ] `G14-P2-32-E03` vary carbon weights and verify transparent objective response.
- [ ] `G14-P2-32-E04` stale/missing feed fallback according to policy.
- [ ] `G14-P2-32-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-32-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-32-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-32-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-32-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-32-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-32-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-32-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-32-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-32-G01` **Acceptance:** all sustainability inputs have documented units/provenance/freshness.
- [ ] `G14-P2-32-G02` **Acceptance:** hard safety/legal constraints always dominate soft objectives.
- [ ] `G14-P2-32-G03` **Acceptance:** decision explanation shows environmental contribution separately from monetary cost.
- [ ] `G14-P2-32-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-32-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-33 — Network congestion and transfer-time estimation

**Priority:** P2  
**Objective:** Estimate completion time and reliability from bandwidth, RTT, loss, congestion, protocol overhead, and route conditions in addition to monetary cost.  
**Dependencies:** network telemetry, GAP-03 topology, historical transfer measurements.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-33-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-33-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-33-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-33-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-33-A05` Define route telemetry inputs including effective throughput, RTT, packet loss, congestion state, MTU/protocol constraints, and observation time.
- [ ] `G14-P2-33-A06` Use conservative effective-throughput estimates rather than raw link speed for large transfer duration.
- [ ] `G14-P2-33-A07` Model fixed setup/handshake latency separately from byte-proportional transfer time where material.
- [ ] `G14-P2-33-A08` Represent uncertainty/confidence and optionally use percentile estimates (for example p50/p95) for risk-aware decisions.
- [ ] `G14-P2-33-A09` Handle multi-hop or overlay routes without double-counting shared bottlenecks where topology data supports it.
- [ ] `G14-P2-33-A10` Bind transfer-time estimates to the same directed route/snapshot identity as monetary route cost.

## B. Failure semantics and safety
- [ ] `G14-P2-33-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-33-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-33-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-33-B04` Implement and test explicit handling for: **nominal bandwidth severely underestimates congested transfer time**.
- [ ] `G14-P2-33-B05` Implement and test explicit handling for: **asymmetric route conditions ignored**.
- [ ] `G14-P2-33-B06` Implement and test explicit handling for: **stale telemetry masks route degradation**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-33-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-33-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-33-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-33-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-33-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-33-D01` Instrument **predicted transfer duration versus actual**.
- [ ] `G14-P2-33-D02` Instrument **throughput/RTT/loss snapshot age**.
- [ ] `G14-P2-33-D03` Instrument **prediction error by route class**.
- [ ] `G14-P2-33-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-33-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-33-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-33-E01` bandwidth/RTT/loss sensitivity tests.
- [ ] `G14-P2-33-E02` asymmetric A→B/B→A conditions.
- [ ] `G14-P2-33-E03` large-object transfer using measured fixture data.
- [ ] `G14-P2-33-E04` stale/missing telemetry fallback behavior.
- [ ] `G14-P2-33-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-33-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-33-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-33-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-33-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-33-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-33-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-33-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-33-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-33-G01` **Acceptance:** transfer-time estimate is reproducible from versioned route telemetry.
- [ ] `G14-P2-33-G02` **Acceptance:** prediction uncertainty is explicit where data quality is low.
- [ ] `G14-P2-33-G03` **Acceptance:** calibration process can compare estimated and observed durations.
- [ ] `G14-P2-33-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-33-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-34 — Storage read/write/IOPS cost model

**Priority:** P2  
**Objective:** Model provider/site-specific storage capacity, request, throughput, retrieval, minimum-duration, and rounding charges rather than treating storage as free.  
**Dependencies:** storage pricing feeds, dataset access profile, provider metadata, cost model.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-34-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-34-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-34-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-34-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-34-A05` Define cost dimensions for GB-month, read/write requests, IOPS, throughput, retrieval, early-delete/minimum duration, transaction, and tier transition fees.
- [ ] `G14-P2-34-A06` Represent provider/site/tier pricing with effective dates, currency, units, minimum billing quanta, and rounding semantics.
- [ ] `G14-P2-34-A07` Model dataset access profile separately for reads, writes, request counts, sequential/random IO, and retention horizon.
- [ ] `G14-P2-34-A08` Account for temporary staging/duplicate storage during movement or replication.
- [ ] `G14-P2-34-A09` Validate currency/unit consistency and convert only through explicitly versioned FX/config inputs if multiple currencies are permitted.
- [ ] `G14-P2-34-A10` Expose each storage-cost component independently in the decision breakdown.

## B. Failure semantics and safety
- [ ] `G14-P2-34-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-34-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-34-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-34-B04` Implement and test explicit handling for: **request/IO costs omitted for small-object workloads**.
- [ ] `G14-P2-34-B05` Implement and test explicit handling for: **minimum retention/rounding causes underestimation**.
- [ ] `G14-P2-34-B06` Implement and test explicit handling for: **staging double-storage omitted**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-34-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-34-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-34-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-34-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-34-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-34-D01` Instrument **predicted storage cost decomposition**.
- [ ] `G14-P2-34-D02` Instrument **pricing snapshot age/version**.
- [ ] `G14-P2-34-D03` Instrument **predicted-versus-billed calibration error**.
- [ ] `G14-P2-34-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-34-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-34-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-34-E01` provider minimum charge and rounding golden cases.
- [ ] `G14-P2-34-E02` high-IOPS small-object versus bulk sequential dataset.
- [ ] `G14-P2-34-E03` replication/staging overlap costs.
- [ ] `G14-P2-34-E04` pricing revision/effective-date boundary.
- [ ] `G14-P2-34-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-34-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-34-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-34-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-34-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-34-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-34-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-34-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-34-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-34-G01` **Acceptance:** storage costs are unit-consistent and independently auditable.
- [ ] `G14-P2-34-G02` **Acceptance:** provider minimum/rounding/lifecycle rules are encoded as test fixtures.
- [ ] `G14-P2-34-G03` **Acceptance:** cost breakdown prevents hidden aggregation of materially different storage charges.
- [ ] `G14-P2-34-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-34-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-35 — Compute architecture/runtime compatibility model

**Priority:** P2  
**Objective:** Ensure candidate sites can actually execute a workload across CPU/GPU/accelerator ISA, runtime, drivers, ABI, container, and kernel requirements.  
**Dependencies:** SCH-01, artifact/runtime metadata, site inventory.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-35-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-35-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-35-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-35-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-35-A05` Define workload compatibility requirements for CPU ISA/features, GPU/accelerator model, driver/API level, OS/kernel, container runtime, ABI, and required device capabilities.
- [ ] `G14-P2-35-A06` Represent site capability versions and supported compatibility ranges rather than coarse booleans.
- [ ] `G14-P2-35-A07` Define exact/compatible version comparison rules for drivers, CUDA/ROCm-like stacks, runtimes, and architecture features.
- [ ] `G14-P2-35-A08` Bind workload artifact/image digest to its declared runtime requirements and prevent mutable tag ambiguity.
- [ ] `G14-P2-35-A09` Separate compatibility from capacity: a compatible site with zero allocatable resources remains ineligible.
- [ ] `G14-P2-35-A10` Return machine-readable elimination reasons for each unmet requirement.

## B. Failure semantics and safety
- [ ] `G14-P2-35-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-35-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-35-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-35-B04` Implement and test explicit handling for: **scheduler selects x86-only artifact for incompatible ISA**.
- [ ] `G14-P2-35-B05` Implement and test explicit handling for: **driver/runtime mismatch discovered only after placement**.
- [ ] `G14-P2-35-B06` Implement and test explicit handling for: **mutable container tag changes requirements after decision**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-35-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-35-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-35-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-35-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-35-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-35-D01` Instrument **compatibility elimination counts by requirement class**.
- [ ] `G14-P2-35-D02` Instrument **capability inventory age/version**.
- [ ] `G14-P2-35-D03` Instrument **post-placement compatibility failures, targeted at zero**.
- [ ] `G14-P2-35-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-35-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-35-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-35-E01` CPU ISA/feature mismatch.
- [ ] `G14-P2-35-E02` accelerator driver/API version matrix.
- [ ] `G14-P2-35-E03` immutable image digest versus mutable tag.
- [ ] `G14-P2-35-E04` compatible-but-no-capacity and capacity-but-incompatible cases.
- [ ] `G14-P2-35-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-35-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-35-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-35-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-35-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-35-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-35-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-35-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-35-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-35-G01` **Acceptance:** every eligible site satisfies all declared hard runtime requirements.
- [ ] `G14-P2-35-G02` **Acceptance:** artifact/runtime identity is immutable in provenance.
- [ ] `G14-P2-35-G03` **Acceptance:** compatibility errors are detected before execution handoff.
- [ ] `G14-P2-35-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-35-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-36 — Quota and capacity reservation awareness

**Priority:** P2  
**Objective:** Include real allocatable quota, reservations, leases, and race-safe capacity preconditions in gravity decisions.  
**Dependencies:** quota service, SCH-01, PLN-06, capacity inventory.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-36-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-36-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-36-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-36-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-36-A05` Define per-tenant/project/site quota dimensions for compute, accelerator, storage, transfer, and relevant rate limits.
- [ ] `G14-P2-36-A06` Represent existing reservations, committed capacity, soft quotas, burst allowances, and expiration times.
- [ ] `G14-P2-36-A07` Use short-lived reservation/lease tokens for decisions that require capacity guarantees across handoff boundaries.
- [ ] `G14-P2-36-A08` Bind reservation token to tenant, workload, resource vector, site, expiry, and decision ID.
- [ ] `G14-P2-36-A09` Define fallback/reoptimization behavior when reservation acquisition fails or expires.
- [ ] `G14-P2-36-A10` Prevent double-counting the same reserved capacity across concurrent decision requests.

## B. Failure semantics and safety
- [ ] `G14-P2-36-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-36-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-36-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-36-B04` Implement and test explicit handling for: **decision selects site with nominal capacity but no tenant quota**.
- [ ] `G14-P2-36-B05` Implement and test explicit handling for: **capacity disappears before execution**.
- [ ] `G14-P2-36-B06` Implement and test explicit handling for: **same capacity reserved by competing decisions**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-36-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-36-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-36-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-36-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-36-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-36-D01` Instrument **quota/capacity eliminations**.
- [ ] `G14-P2-36-D02` Instrument **reservation acquisition latency/success/expiry**.
- [ ] `G14-P2-36-D03` Instrument **reoptimization due to reservation loss**.
- [ ] `G14-P2-36-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-36-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-36-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-36-E01` quota exhausted despite physical capacity.
- [ ] `G14-P2-36-E02` concurrent reservation contention.
- [ ] `G14-P2-36-E03` lease expiry before PLN-06 execution.
- [ ] `G14-P2-36-E04` release/cancel reservation on failed decision.
- [ ] `G14-P2-36-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-36-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-36-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-36-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-36-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-36-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-36-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-36-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-36-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-36-G01` **Acceptance:** selected destinations are feasible under both physical capacity and tenant quota.
- [ ] `G14-P2-36-G02` **Acceptance:** capacity guarantees use race-safe reservation semantics where required.
- [ ] `G14-P2-36-G03` **Acceptance:** expired/failed reservations cannot authorize execution.
- [ ] `G14-P2-36-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-36-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-37 — Historical calibration and model-drift detection

**Priority:** P2  
**Objective:** Compare predicted costs/times with observed execution outcomes and detect systematic drift before optimization quality degrades materially.  
**Dependencies:** execution outcome telemetry, provenance store, analytics/metrics backend.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-37-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-37-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-37-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-37-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-37-A05` Persist predicted cost/time components and join them to actual transfer, compute, storage, and execution outcomes by decision/operation ID.
- [ ] `G14-P2-37-A06` Define error metrics such as absolute/relative error, bias, MAPE where appropriate, quantile loss, and calibration by route/site/workload class.
- [ ] `G14-P2-37-A07` Establish minimum sample sizes and confidence rules before declaring drift.
- [ ] `G14-P2-37-A08` Detect persistent bias or distribution shift using bounded statistical tests/control limits suitable for operational monitoring.
- [ ] `G14-P2-37-A09` Version cost-model parameters and record model revision so calibration can distinguish model change from environment change.
- [ ] `G14-P2-37-A10` Define remediation workflow: investigate feed quality, tune coefficients, shadow-test candidate model, approve, and roll back if needed.

## B. Failure semantics and safety
- [ ] `G14-P2-37-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-37-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-37-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-37-B04` Implement and test explicit handling for: **model underestimates one route/site for weeks without alert**.
- [ ] `G14-P2-37-B05` Implement and test explicit handling for: **actual outcomes cannot be joined to predictions**.
- [ ] `G14-P2-37-B06` Implement and test explicit handling for: **automatic tuning destabilizes decisions without review**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-37-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-37-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-37-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-37-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-37-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-37-D01` Instrument **prediction-error distributions and bias**.
- [ ] `G14-P2-37-D02` Instrument **drift alert state by bounded dimension**.
- [ ] `G14-P2-37-D03` Instrument **sample count/coverage and unmatched outcomes**.
- [ ] `G14-P2-37-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-37-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-37-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-37-E01` synthetic known-bias data triggers drift threshold.
- [ ] `G14-P2-37-E02` insufficient-sample case does not over-alert.
- [ ] `G14-P2-37-E03` model revision boundary separated in analytics.
- [ ] `G14-P2-37-E04` missing/corrupt outcome data handled explicitly.
- [ ] `G14-P2-37-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-37-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-37-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-37-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-37-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-37-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-37-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-37-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-37-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-37-G01` **Acceptance:** predictions and actuals are traceably joinable for a defined coverage target.
- [ ] `G14-P2-37-G02` **Acceptance:** drift thresholds and ownership are documented.
- [ ] `G14-P2-37-G03` **Acceptance:** model changes follow controlled shadow/canary validation rather than opaque automatic mutation.
- [ ] `G14-P2-37-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-37-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-38 — Canary and shadow decision mode

**Priority:** P2  
**Objective:** Evaluate new engines, cost models, or policies in parallel without allowing experimental output to drive execution until promoted.  
**Dependencies:** decision engine versioning, telemetry/provenance, routing/config.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-38-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-38-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-38-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-38-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-38-A05` Implement shadow evaluation that receives the same immutable input snapshot as the active engine but is technically incapable of calling execution/handoff paths.
- [ ] `G14-P2-38-A06` Assign experiment/model version and sampling cohort deterministically to support reproducible comparison.
- [ ] `G14-P2-38-A07` Record active-versus-shadow decision, cost, eliminated options, latency, and error differences using bounded telemetry dimensions.
- [ ] `G14-P2-38-A08` Define canary mode separately if a small approved traffic slice may use the candidate for real decisions, with explicit rollback guardrails.
- [ ] `G14-P2-38-A09` Prevent experimental failures from increasing active-path latency beyond a configured budget; use asynchronous/bounded comparison where safe.
- [ ] `G14-P2-38-A10` Define promotion criteria, rollback criteria, minimum sample size, and required review evidence.

## B. Failure semantics and safety
- [ ] `G14-P2-38-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-38-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-38-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-38-B04` Implement and test explicit handling for: **shadow path accidentally triggers side effects**.
- [ ] `G14-P2-38-B05` Implement and test explicit handling for: **experimental latency degrades production path**.
- [ ] `G14-P2-38-B06` Implement and test explicit handling for: **comparison uses different input revisions and creates false differences**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-38-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-38-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-38-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-38-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-38-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-38-D01` Instrument **decision divergence rate and cost delta**.
- [ ] `G14-P2-38-D02` Instrument **shadow/canary error and latency**.
- [ ] `G14-P2-38-D03` Instrument **sample counts and rollback-trigger status**.
- [ ] `G14-P2-38-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-38-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-38-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-38-E01` prove shadow implementation has no PLN-06/output side-effect capability.
- [ ] `G14-P2-38-E02` force candidate crash/timeout and verify active result unaffected.
- [ ] `G14-P2-38-E03` verify identical provenance snapshot fed to both engines.
- [ ] `G14-P2-38-E04` exercise automatic/manual canary rollback conditions.
- [ ] `G14-P2-38-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-38-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-38-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-38-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-38-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-38-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-38-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-38-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-38-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-38-G01` **Acceptance:** shadow output cannot execute by construction.
- [ ] `G14-P2-38-G02` **Acceptance:** comparisons are apples-to-apples on identical immutable inputs.
- [ ] `G14-P2-38-G03` **Acceptance:** promotion requires explicit evidence and rollback remains immediate.
- [ ] `G14-P2-38-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-38-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-39 — Policy simulation and what-if API

**Priority:** P2  
**Objective:** Allow authorized operators to compare alternate policy/cost/topology scenarios safely, immutably, and without generating executable production actions.  
**Dependencies:** operator authorization, decision engine, snapshot/provenance store.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-39-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-39-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-39-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-39-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-39-A05` Create a simulation endpoint/type that is explicitly non-executable and returns artifacts distinguishable from production decisions.
- [ ] `G14-P2-39-A06` Require caller to specify base historical/current snapshot references and explicit overrides rather than mutating shared live configuration.
- [ ] `G14-P2-39-A07` Validate hypothetical policy/topology/cost overrides with the same schemas/domain rules as production inputs while marking them synthetic.
- [ ] `G14-P2-39-A08` Support multiple named scenarios and deterministic diff output across selected direction, costs, constraints, and eliminations.
- [ ] `G14-P2-39-A09` Apply strict authorization and rate/resource limits because simulation can expose sensitive topology/cost information and invoke expensive optimization.
- [ ] `G14-P2-39-A10` Audit simulation access and inputs while keeping outputs segregated from production execution/audit decision streams.

## B. Failure semantics and safety
- [ ] `G14-P2-39-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-39-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-39-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-39-B04` Implement and test explicit handling for: **simulation result mistaken for executable approval**.
- [ ] `G14-P2-39-B05` Implement and test explicit handling for: **what-if override mutates live configuration**.
- [ ] `G14-P2-39-B06` Implement and test explicit handling for: **operator can simulate unauthorized tenant data**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-39-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-39-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-39-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-39-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-39-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-39-D01` Instrument **simulation request count/latency/denies**.
- [ ] `G14-P2-39-D02` Instrument **scenario size/complexity**.
- [ ] `G14-P2-39-D03` Instrument **production-versus-simulated artifact classification violations**.
- [ ] `G14-P2-39-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-39-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-39-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-39-E01` attempt PLN-06 handoff using simulation artifact and verify cryptographic/type rejection.
- [ ] `G14-P2-39-E02` run concurrent simulations with conflicting overrides and verify isolation.
- [ ] `G14-P2-39-E03` cross-tenant authorization tests.
- [ ] `G14-P2-39-E04` historical snapshot replay with controlled overrides.
- [ ] `G14-P2-39-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-39-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-39-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-39-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-39-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-39-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-39-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-39-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-39-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-39-G01` **Acceptance:** simulation artifacts are non-executable by design.
- [ ] `G14-P2-39-G02` **Acceptance:** live state cannot be mutated through the what-if API.
- [ ] `G14-P2-39-G03` **Acceptance:** authorized users can reproduce and diff scenarios from explicit snapshot inputs.
- [ ] `G14-P2-39-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-39-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# G14-P2-40 — Formal release and incident runbooks

**Priority:** P2  
**Objective:** Operationalize incident severity, paging, containment, restore, rollback, deprecation, disaster recovery, and end-of-life procedures with tested ownership.  
**Dependencies:** operations/on-call, release management, monitoring/alerting, configuration/artifact rollback.

## A. Architecture, ownership, and requirements
- [ ] `G14-P2-40-A01` Assign a primary engineering owner, security reviewer, operations owner, and release approver; record RACI/escalation ownership in repository metadata.
- [ ] `G14-P2-40-A02` Write a normative design note that defines scope, non-goals, trust boundaries, authoritative data sources, invariants, and interaction with the GAP-14 decision lifecycle.
- [ ] `G14-P2-40-A03` Define versioning and backward/forward-compatibility expectations for every interface introduced by this component.
- [ ] `G14-P2-40-A04` Identify production modes, development/test modes, and any degraded modes; prohibit test conveniences from being enabled implicitly in production.
- [ ] `G14-P2-40-A05` Define severity levels with concrete GAP-14 examples such as illegal-placement risk, audit evidence loss, widespread decision outage, cost-model corruption, and degraded observability.
- [ ] `G14-P2-40-A06` Map each severity to paging target, acknowledgement objective, escalation path, communications owner, and evidence-preservation requirements.
- [ ] `G14-P2-40-A07` Document containment actions including disabling data-move recommendations, forcing compute-only safe mode where approved, freezing configuration, or isolating a bad dependency/model revision.
- [ ] `G14-P2-40-A08` Document artifact/config/model rollback using immutable known-good versions and post-rollback validation.
- [ ] `G14-P2-40-A09` Define backup/restore and disaster-recovery objectives for configuration, provenance/audit evidence, and any persistent operational state.
- [ ] `G14-P2-40-A10` Define schema/API/model deprecation and EOL timelines, migration evidence, customer/internal dependency notification, and removal gates.

## B. Failure semantics and safety
- [ ] `G14-P2-40-B01` Define stable error, refusal, elimination, or degraded-mode reason codes for expected failures; separate caller errors, dependency failures, security failures, stale-data failures, and internal faults.
- [ ] `G14-P2-40-B02` Specify which failures are fail-closed, retryable, degradable, or operator-actionable; document the rationale and maximum tolerated uncertainty.
- [ ] `G14-P2-40-B03` Verify failure handling is deterministic and does not fall through to implicit defaults, ambient configuration, untrusted caller values, or stale global state.
- [ ] `G14-P2-40-B04` Implement and test explicit handling for: **operators improvise unsafe containment during legal-placement incident**.
- [ ] `G14-P2-40-B05` Implement and test explicit handling for: **rollback artifact/config cannot be located or verified**.
- [ ] `G14-P2-40-B06` Implement and test explicit handling for: **deprecated schema removed before estate migration completes**.

## C. Security, integrity, and data protection
- [ ] `G14-P2-40-C01` Threat-model spoofing, tampering, replay, privilege escalation, cross-tenant access, information disclosure, denial of service, and unsafe fallback at every new trust boundary.
- [ ] `G14-P2-40-C02` Authenticate authoritative producers/consumers and validate authorization scope before accepting or exposing protected state.
- [ ] `G14-P2-40-C03` Validate all untrusted fields with strict type, length, character/normalization, numeric-domain, enum, and unknown-field rules before use.
- [ ] `G14-P2-40-C04` Define integrity/provenance requirements (hash, signature, immutable revision, issuer, timestamp, or equivalent) for decision-affecting data.
- [ ] `G14-P2-40-C05` Classify sensitive fields and define redaction, retention, encryption-in-transit/at-rest, and least-privilege access requirements; prohibit secrets in logs, metrics, or provenance.

## D. Observability and evidence
- [ ] `G14-P2-40-D01` Instrument **incident detection-to-acknowledge/contain/restore times**.
- [ ] `G14-P2-40-D02` Instrument **rollback success and validation status**.
- [ ] `G14-P2-40-D03` Instrument **deprecated-version usage approaching EOL**.
- [ ] `G14-P2-40-D04` Add trace correlation using the GAP-14 decision ID plus standard trace/span context across all applicable dependency calls.
- [ ] `G14-P2-40-D05` Keep metrics/log labels within an explicit cardinality budget; do not use raw tenant, workload, dataset, request, or operation IDs as unbounded metric labels.
- [ ] `G14-P2-40-D06` Define release/incident evidence that proves the component version, configuration, and observed runtime state for a specific decision.

## E. Verification and test matrix
- [ ] `G14-P2-40-E01` tabletop illegal-placement/audit-loss incident.
- [ ] `G14-P2-40-E02` game-day rollback to previous engine/config version.
- [ ] `G14-P2-40-E03` restore evidence from backup and independently verify integrity.
- [ ] `G14-P2-40-E04` exercise deprecation warning through final rejection in a staged environment.
- [ ] `G14-P2-40-E05` Add schema/contract tests for minimum supported, current, and intentionally incompatible versions where versioned interfaces exist.
- [ ] `G14-P2-40-E06` Add malformed-input and boundary-value tests, including oversized inputs, missing required fields, unknown fields, invalid enums, and numeric extremes where applicable.
- [ ] `G14-P2-40-E07` Add concurrency/race tests for mutable external state, refreshes, retries, cancellation, or handoff boundaries applicable to this component.
- [ ] `G14-P2-40-E08` Add at least one negative test proving that the most dangerous unsafe fallback is impossible.

## F. Documentation, rollout, and lifecycle
- [ ] `G14-P2-40-F01` Document configuration knobs, defaults, safe ranges, ownership, and whether each setting is reloadable or restart-bound.
- [ ] `G14-P2-40-F02` Document deployment/upgrade order with dependent services and define mixed-version behavior during rolling upgrades.
- [ ] `G14-P2-40-F03` Add operator troubleshooting guidance mapping symptoms/alerts/reason codes to evidence sources and safe corrective actions.
- [ ] `G14-P2-40-F04` Define rollback/disable strategy and prove that rollback does not invalidate retained provenance/audit evidence.
- [ ] `G14-P2-40-F05` Record component status in the GAP-14 production-certification manifest with links to schemas, tests, dashboards, runbooks, and artifact digests.

## G. Acceptance gates
- [ ] `G14-P2-40-G01` **Acceptance:** runbooks identify named roles, commands/procedures, evidence, and success checks.
- [ ] `G14-P2-40-G02` **Acceptance:** critical rollback/restore procedures are exercised on a defined cadence.
- [ ] `G14-P2-40-G03` **Acceptance:** EOL/removal cannot occur until measured dependent usage satisfies the migration gate.
- [ ] `G14-P2-40-G04` **Evidence gate:** independent reviewer can reproduce the critical success/failure behavior from source-controlled fixtures and release artifacts.
- [ ] `G14-P2-40-G05` **Production gate:** no unresolved Critical/High security defect or unowned fail-open path remains for this component.

---

# Program-level closure checklist

## P0 certification closure
- [ ] All P0 component acceptance gates are complete with linked evidence.
- [ ] The full `pk_core` 100-check conformance gate executes with zero unapproved skips.
- [ ] Estate-level integration suite passes against certified GAP-13/GAP-03/GAP-05/SCH-01/PLN-06 versions.
- [ ] Identity, provenance, and tamper-evident audit are active for 100% of production-certifiable decisions.
- [ ] No production data move can execute without current policy authorization, validated convergence/placement preconditions, and an idempotent signed handoff.

## P1 hardening closure
- [ ] End-to-end deadlines, cancellation, retries, backpressure, and stale-data behavior are defined and fault-tested.
- [ ] Health, metrics, logs, traces, explainability, and admission control are deployed with tested redaction/cardinality limits.
- [ ] Performance evidence demonstrates the declared target load/SLO profile and long-run resource stability.
- [ ] Compatibility, packaging, and supply-chain controls are enforced by CI/CD rather than documentation alone.

## P2 capability closure
- [ ] Advanced optimization features have explicit objective functions, hard-constraint precedence, provenance, and explainability.
- [ ] Prediction models are calibrated against observed outcomes and new model revisions can be shadowed/canary-tested safely.
- [ ] Simulation is non-executable by construction and production execution rejects simulation artifacts.
- [ ] Incident, rollback, restore, deprecation, and EOL runbooks are exercised and tied to release governance.

## Final certification evidence bundle
- [ ] Source revision/commit and clean-tree evidence.
- [ ] Engine/package version and compatibility matrix.
- [ ] Dependency lock, SBOM, vulnerability report, artifact hashes/signatures/provenance.
- [ ] Active configuration schema/revision and signed configuration evidence.
- [ ] Unit/contract/property/fuzz/integration/fault/performance test reports.
- [ ] Metrics/dashboard and alert definitions with cardinality/redaction review.
- [ ] Runbook/tabletop/game-day evidence.
- [ ] Signed certification decision identifying remaining accepted risks and expiration/review date.
