# INV-54 Missing Components - Second-Pass Audit

> **v4.3.0 note:** this is the v4.2.0 audit, kept as the historical baseline. Current per-component status is in `CHECKLIST_STATUS.md` and `evidence/component_status.json`.

## Scope and interpretation

This is a static repository audit of the supplied/updated INV-54 archive. A component is listed when the repository contains no implementation/artifact for it, or only a declaration that is insufficient to demonstrate the checklist requirement. The list intentionally does not fabricate Kafka/RabbitMQ/SQS infrastructure, credentials, external control planes, or `pk_core` gate evidence.

Priority meanings: **P0** = production blocker/security/data-integrity blocker; **P1** = required production-readiness capability; **P2** = governance, packaging, or maintainability gap that should still be closed before formal release.

## A. Architecture, requirements, and governance

1. **P1 - Accountable owner and escalation artifact** (`INV-54-C009`). No CODEOWNERS/OWNER/operational ownership file identifies accountable owner, backup owner, paging target, or escalation chain.
2. **P1 - Approved architecture decision record for broker technologies** (`C010`, `C031`). No ADR records why/where Kafka, RabbitMQ, and AWS SQS are supported, excluded, or preferred, nor pins approved versions/specifications.
3. **P1 - Deployment-context requirements specification** (`C011`, `C012`). The contract has concise mandatory statements, but no SHALL-level requirements document covers cloud, datacenter, near-edge, and far-edge behaviour.
4. **P1 - Complete non-functional requirements specification** (`C013`). A few SLOs exist, but availability, durability, consistency, isolation, startup, throughput, storage, recovery, and edge constraints are not fully specified.
5. **P1 - Failure-semantics taxonomy** (`C014`). No machine-readable or normative definition distinguishes success, partial success, degraded operation, retryable failure, and terminal failure.
6. **P1 - Lifecycle/state-transition model** (`C015`). No broker/adapter lifecycle state machine or legal-transition table is shipped.
7. **P1 - Backward-compatibility/versioning policy** (`C016`, `C027`). A component version exists, but there is no supported protocol/API compatibility policy, deprecation window, or mixed-version behaviour specification.
8. **P0 - Capacity, quota, and fairness model** (`C017`, `C028`, `C067`, `C069`). No per-tenant/per-workload quotas, queue/log bounds, fairness rules, saturation model, or admission thresholds are implemented.
9. **P1 - Intermittent/offline network semantics** (`C018`). No normative reconnect, buffering, delivery, duplication, or consistency behaviour is defined for intermittent/absent connectivity.
10. **P1 - Constraint-precedence policy** (`C019`). No documented ordering resolves conflicts among security, residency, consistency, SLO, and cost constraints.
11. **P1 - Requirements traceability matrix** (`C020`). There is no artifact mapping each checklist/SHALL requirement to source, implementation symbol, test, runtime evidence, and release gate result.
12. **P2 - Master prompt/workflow source corpus** (repository integrity). README history referred to `MASTER.md`, but the archive does not ship it. The false claim is fixed; the source corpus remains absent.

## B. Provider and physical broker implementations

13. **P0 - Kafka production adapter** (`C010`, `C030`, `C031`, `C083`). No Kafka client adapter, configuration, topic/partition mapping, offset/consumer-group integration, error translation, security setup, or conformance fixture exists.
14. **P0 - RabbitMQ production adapter** (`C010`, `C030`, `C031`, `C083`). No exchange/queue/binding adapter, acknowledgement/redelivery semantics, publisher confirms, consumer recovery, or conformance fixture exists.
15. **P0 - AWS SQS production adapter** (`C010`, `C030`, `C031`, `C083`). No standard/FIFO queue adapter, visibility-timeout handling, deduplication mapping, IAM integration, or conformance fixture exists.
16. **P1 - Provider capability/feature matrix** (`C027`, `C031`, `C093`). No documented matrix shows which contract features map cleanly, degrade, or are unsupported across the three provider families.
17. **P1 - Provider version pin/lock data** (`C031`, `C045`, `C093`). No client-library lockfile or approved provider/API-version manifest is shipped.

## C. Public interfaces and integration contracts

18. **P0 - Versioned typed external schemas** (`C022`). Interface identifiers are strings in `contract.py`, but no schema/WIT/IDL/OpenAPI/AsyncAPI/JSON-Schema/protobuf artifacts define request/message/error structures.
19. **P0 - Authentication boundary implementation** (`C023`, `C044`). No broker/provider authentication integration is implemented.
20. **P0 - Authorization/capability model** (`C024`, `C042`). No publish/subscribe/admin capability checks or least-privilege policy binding exists.
21. **P0 - Timeout/cancellation/retry/idempotency/backpressure contract** (`C025`, `C053`, `C054`). The reference API has no normative timeout/cancel semantics, idempotency keys, bounded retry policy, backpressure protocol, or circuit-breaker/admission-control implementation.
22. **P1 - Structured machine-readable error model** (`C026`). The reference classes raise built-in exceptions; there is no stable error-code namespace or serializable failure detail contract.
23. **P1 - Mixed-version negotiation/compatibility layer** (`C027`). No wire/API version negotiation or downgrade/upgrade behaviour is implemented.
24. **P1 - Reference examples and conformance fixtures** (`C029`). README usage is minimal; no provider-neutral fixture corpus or golden input/output cases are shipped.
25. **P0 - Adjacent-layer integration harness** (`C030`, `C083`). No executable tests prove interoperability with INV-52 Messaging abstraction, INV-53 Message reliability, INV-49 Pluggable infrastructure adapters, or INV-37 Bulk data plane.

## D. Configuration and bootstrap

26. **P1 - Declarative configuration schema** (`C033`). No typed configuration file/schema covers provider selection, endpoints, TLS, credentials references, partitions/queues, limits, retry, retention, telemetry, or feature flags.
27. **P0 - Configuration validation/fail-closed activation** (`C034`). No pre-activation validator or fail-closed security-critical configuration gate exists.
28. **P1 - Site/environment overlays** (`C035`). No supported mechanism cleanly applies site/environment-specific values without rebuilding artifacts.
29. **P1 - Configuration provenance record** (`C036`). No author/source/version/digest/activation-time record is produced.
30. **P1 - Atomic/transactional configuration update mechanism** (`C037`). No staged validate/apply/commit behaviour exists.
31. **P1 - Configuration rollback mechanism** (`C038`). README describes high-level release rollback, not configuration rollback to a known-good broker/provider state.
32. **P0 - Secret-reference and credential integration** (`C039`). No secret-provider interface, external secret reference format, redaction guarantees, or credential rotation path exists.
33. **P1 - Deterministic bootstrap/install path** (`C040`). README assumes Python plus external `pk_core`; no pinned environment/bootstrap script reproduces a healthy integrated install from an empty node.
34. **P2 - Python package/build metadata** (repository hygiene). No `pyproject.toml`/build manifest defines supported Python versions, package metadata, dependencies, entry points, or build backend.
35. **P2 - Dependency lock/SBOM input manifest** (`C045`). No reproducible dependency lock or package manifest exists from which an SBOM can be generated.

## E. Security, trust, isolation, and supply chain

36. **P0 - Formal threat model** (`C041`). `contract.py` lists three threats, but there is no systematic model covering malicious tenants, compromised workloads, hostile payloads, supply-chain compromise, identity abuse, control-plane abuse, and resource exhaustion.
37. **P0 - Least-privilege/ambient-authority architecture** (`C042`, `C043`). No runtime identity/capability design demonstrates removal of ambient filesystem/network/secret authority for provider adapters.
38. **P0 - Artifact signature/digest/provenance verification** (`C045`). No verification of executable/provider/policy artifacts, allowlist, signature policy, or provenance attestation exists.
39. **P0 - Enforced tenant/workload isolation** (`C046`). Tenant isolation is stated in the contract, but the reference broker APIs have no tenant dimension and no storage/network/identity enforcement boundary.
40. **P0 - Transport encryption/TLS policy and implementation** (`C047`). No mTLS/TLS configuration, certificate policy, cipher policy, or provider-specific secure transport implementation exists.
41. **P0 - At-rest encryption and managed key rotation** (`C047`, `C048`). No durable store exists and no KMS/key rotation integration or failure behaviour is defined.
42. **P0 - Security-service outage behaviour** (`C048`). No fail-closed/degraded behaviour is specified for unavailable identity, attestation, policy, key, or trusted-time services.
43. **P0 - Tamper-evident security audit events** (`C049`). No signed/chained/append-only audit-event stream is emitted for subscribe/publish/admin/config/security operations.
44. **P0 - Adversarial security test suite** (`C050`, `C087`). No tests cover spoofing, replay, injection, privilege escalation, escape, side channels, malformed inputs, or resource exhaustion.
45. **P2 - Security policy/vulnerability disclosure document** (`C094`). No repository security policy identifies reporting, triage, patch, or disclosure procedures.
46. **P2 - License/legal metadata** (repository hygiene). The component archive has no LICENSE/NOTICE artifact establishing redistribution/use terms.

## F. Durability, resilience, and distributed failure handling

47. **P0 - Durable log/storage backend** (`C057`, `C095`). `PartitionedLog` is memory-only; process exit loses messages and committed offsets.
48. **P0 - Retention/compaction/expiry subsystem** (`C028`, `C057`, `C067`). The log grows without bound and has no retention, segmenting, compaction, TTL, or disk-pressure policy.
49. **P0 - Replication/high-availability subsystem** (`C051`, `C055`). No replicas, quorum semantics, provider failover, or availability-zone/site failover exist.
50. **P0 - Split-brain/duplicate-owner fencing** (`C058`). No epochs, leases, fencing tokens, leader terms, or duplicate-consumer ownership protection exists.
51. **P1 - Comprehensive failure catalogue** (`C051`). Four failure modes are named, but process/VM/node/site/network/provider/dependency/control-plane failure modes and recovery objectives are not fully enumerated.
52. **P0 - Automated health/stall detection** (`C052`, `C071`). No liveness/readiness probes, consumer-stall detector, append-stall detector, or health thresholds exist.
53. **P0 - Retry/backoff/jitter framework** (`C053`). No bounded provider-operation retry engine with retryability classification exists.
54. **P0 - Admission control/load shedding/circuit breaking** (`C054`, `C067`). No bounded queues, overload rejection, producer throttling, breaker state, or priority admission exists.
55. **P0 - Failover consistency/residency policy implementation** (`C055`). No failover mechanism proves that recovery preserves ordering, isolation, residency, and consistency constraints.
56. **P1 - Degraded-operation modes** (`C056`). No defined read-only/local-buffer/provider-degraded mode is implemented.
57. **P0 - Crash/restart/resume recovery** (`C057`). Replay works only while the process lives; there is no WAL/checkpoint/recovery path for broker state or offsets.
58. **P1 - Quarantine/freeze/isolation control** (`C059`). README mentions registry removal as emergency disable, but there is no explicit runtime quarantine/freeze/drain control.
59. **P0 - Fault-injection resilience suite** (`C060`). No kill/restart/latency/loss/corruption/provider-outage fault tests exist.
60. **P0 - Disaster/partition/reconnect test suite** (`C089`). No site/network partition, reconnect, degraded-control-plane, or disaster-recovery tests exist.
61. **P1 - Backup/restore/migration/reconstruction tooling** (`C095`). No durable state exists and no state migration, backup, restore, or reconstruction workflow is shipped.

## G. Performance, efficiency, and capacity engineering

62. **P1 - Reproducible benchmark harness** (`C061`, `C088`). No benchmark records latency, throughput, startup, CPU, memory, storage, network, or power from a pinned environment.
63. **P1 - Complete latency/throughput thresholds** (`C062`). Only an append p99 target exists; p50, p95, worst-case, throughput, startup, and recovery thresholds are absent.
64. **P1 - Load-profile test suite** (`C063`, `C088`). No steady, burst, overload, scale-out, scale-in, soak, or fleet-scale scenarios exist.
65. **P1 - Per-tenant/per-workload resource accounting** (`C064`). No attribution of CPU, memory, queue/log growth, bytes, requests, or provider cost by tenant/workload exists.
66. **P1 - Serialization/copy/hop efficiency analysis** (`C065`). Fan-out deliberately deep-copies for isolation, but no production serialization/copy/hop budget or measurement exists.
67. **P1 - Production optimization layer** (`C066`). No batching, caching, locality, zero-copy, direct composition, or provider-specific efficiency path is implemented or benchmarked.
68. **P0 - Bounded memory/queue/log/concurrency controls** (`C067`). Both reference inboxes and log partitions are unbounded; no resource ceiling prevents memory exhaustion.
69. **P1 - Edge power/thermal characterization** (`C068`). No power or thermal measurements exist for constrained nodes.
70. **P1 - Capacity model and saturation signals** (`C069`). No formula/model converts rates, backlog, lag, latency, storage, and resource usage into scale decisions.
71. **P1 - Performance regression release gate** (`C070`). No CI/release gate blocks startup, density, throughput, or tail-latency regressions.

## H. Observability and explainability

72. **P0 - Health/readiness/version/config/dependency status surface** (`C071`). No operator/API endpoint exposes current health, readiness, provider dependency state, configuration version, or active capabilities.
73. **P0 - Runtime metrics instrumentation** (`C072`). `contract.py` names signals, but the implementation emits no counters/histograms/gauges for rate, errors, latency, saturation, backlog, or resources.
74. **P0 - Structured operational logging** (`C073`). No logger emits stable node/tenant/workload/component/operation identifiers.
75. **P1 - Distributed trace propagation** (`C074`). No trace-context fields or propagation across broker/provider calls exist.
76. **P1 - Safe high-cardinality diagnostics** (`C075`). No controlled diagnostic surface provides per-tenant/message/provider detail with redaction/privacy controls.
77. **P1 - Decision-reason records** (`C076`). No reason/event model records why automated retry, rejection, routing, failover, or load-shedding decisions occurred.
78. **P1 - Operator explain view** (`C077`). No human-readable diagnostic command/UI links current decisions to input state, policies, topology, and constraints.
79. **P1 - Release/infrastructure lineage correlation** (`C078`). Telemetry is not correlated with application releases, broker versions, configuration digests, or infrastructure graph identities.
80. **P1 - Telemetry retention/sampling/privacy/export policy** (`C079`). No policy or configuration exists.
81. **P1 - Dashboards and alert rules** (`C080`). No dashboards or alert definitions distinguish load, degradation, policy rejection, dependency failure, attack, and software defect.

## I. Testing, certification, and acceptance evidence

82. **P1 - Full public-interface contract test suite** (`C082`). The new unit tests exercise reference broker methods, but no schema/provider contract suite covers every externally supported boundary.
83. **P0 - Cross-layer/provider integration tests** (`C030`, `C083`). No actual adjacent-system/provider test environment is shipped.
84. **P1 - Cross-runtime/architecture/provider/protocol compatibility tests** (`C084`). No matrix exercises supported Python/runtime/CPU/provider/protocol combinations.
85. **P1 - Fuzz/property-based input suite** (`C085`). No fuzzers exercise keys, messages, schemas, error decoders, provider responses, or boundary inputs.
86. **P1 - Distributed concurrency/race suite** (`C086`). A local concurrent-append integrity test now exists, but there is no race/linearizability test for concurrent consumers, provider callbacks, failover, or distributed ownership.
87. **P0 - Security test suite derived from threat model** (`C087`). No threat-model-derived executable security suite exists.
88. **P1 - Benchmark/soak/burst/fleet-scale certification suite** (`C088`). No certification workload harness or threshold evaluation exists.
89. **P0 - Machine-readable release acceptance evidence** (`C090`). No current evidence ledger, gate-result JSON, signed result, or artifact digest is included in the archive.
90. **P0 - Re-runnable integrated `pk_core` certification environment** (`C090`, `C100`). Tests support external `pk_core`, but it is not present in the supplied archive/audit environment; two conformance tests therefore remain unverified here.

## J. Operations, release, and lifecycle governance

91. **P1 - Complete support/SLO commitment document** (`C091`). Three SLOs exist, but support hours, escalation commitments, availability/durability targets, measurement windows, and breach handling are absent.
92. **P1 - Executable canary/staged rollout plan** (`C092`). README has generic gate/rollback guidance, but no canary cohort rules, promotion thresholds, staged rollout automation, drain procedure, or tested rollback workflow exists.
93. **P1 - Supported-version compatibility matrix** (`C093`). No matrix covers component, `pk_core`, provider clients, provider services/APIs, schemas, and adjacent INV components.
94. **P1 - Patching/vulnerability/EOL SLAs** (`C094`). No severity-to-fix deadlines, supported-version window, dependency patch cadence, or end-of-life policy is defined.
95. **P1 - Detailed day-0/day-1/day-2 runbooks** (`C096`). README contains a brief outline, not operational procedures with prerequisites, expected outputs, failure branches, rollback, verification, and ownership.
96. **P1 - Incident response runbook** (`C097`). No severity taxonomy, paging criteria, escalation, containment, evidence preservation, recovery, or post-incident workflow exists.
97. **P1 - Recurring architecture/access/policy/dependency/config review process** (`C098`). No schedule, checklist, owner, or retained evidence exists.
98. **P1 - Exception/waiver/technical-debt/deprecation register** (`C099`). No machine-readable register tracks owner, rationale, compensating controls, expiry, and closure evidence.
99. **P0 - Formal production exit-gate evidence** (`C100`). No current gate artifact proves closure across architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership.
100. **P2 - CI/release automation** (supports `C070`, `C090`, `C092`, `C100`). No workflow automates tests, static validation, packaging, evidence generation, performance/security gates, version checks, or release artifact production.

## Coverage note

The 100 entries above are **missing or materially incomplete repository components/artifacts identified after the 4.2.0 hardening pass**. Several checklist requirements are already represented adequately at reference-contract level (for example responsibility, owned/non-owned scope, dependency direction, source-of-truth statement, assumptions, boundaries, mandatory/optional split, and non-goals), so they do not appear as separate gaps unless the implementation/evidence remains incomplete.

The highest-risk blockers are the P0 items: real provider adapters; durable bounded storage; authn/authz/isolation/encryption; configuration fail-closed behaviour; HA/failover/fencing; overload controls; health/telemetry; integration/security/disaster testing; and machine-readable production gate evidence.
