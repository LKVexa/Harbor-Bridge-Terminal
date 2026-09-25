# INV-04 Current Orchestration — Missing Components Inventory

> **v4.3.0 status note.** This list is the v4.2.0 gap inventory and is kept unchanged as the baseline. Per checklist rule ACC-nn.21, no gap is closed on design prose. The current state of every item is in `COMPONENT_STATUS.json`, verified by `tools/evidence_gate.py`, and rendered in `docs/TRACEABILITY.md`. In v4.3.0: 52 components are `reference_implemented`, 7 are `port_with_reference`, 13 are `tooling`, 6 are `documented` and 2 are `open`. Exit gates: 41 `OPEN_REVIEW`, 32 `OPEN_EXTERNAL`, 7 `OPEN_GOVERNANCE`, 0 `PASS`.

This inventory lists capabilities that are absent from v4.2.0 and would be required to turn the hardened reference model into a production-grade incumbent-orchestrator compatibility layer. Items are grouped by implementation priority rather than implying that every item belongs inside the same deployable binary.

## P0 — Control-plane correctness and loss prevention

1. **Kubernetes API client adapter** — authenticated, version-pinned client for Pods, controllers, Nodes, Evictions, PodDisruptionBudgets, Services, PVCs, and relevant discovery APIs.
2. **Informer/watch cache subsystem** — list/watch lifecycle, relist, bookmark handling, watch expiration recovery, object tombstones, and cache synchronization barriers.
3. **Controller work queue** — keyed reconciliation queue with deduplication, dirty/processing sets, bounded workers, retry accounting, and shutdown semantics.
4. **ResourceVersion / optimistic-concurrency layer** — compare-and-swap behavior, conflict detection, retry policy, and stale-cache rejection.
5. **Leader election / active-controller fencing** — lease acquisition, renewal, loss handling, fencing tokens, and split-brain prevention.
6. **Durable desired-state adapter** — authoritative controller/object source rather than an in-memory `dict`, including generation and observed-generation tracking.
7. **Crash/restart recovery** — reconstruction of in-flight reconcile/drain operations after process or node restart.
8. **Drain transaction coordinator** — explicit phases for cordon, eviction planning, eviction execution, verification, uncordon/rollback, and terminal state.
9. **Native Kubernetes Eviction API integration** — policy-aware eviction requests instead of direct in-memory pod removal.
10. **Full PodDisruptionBudget evaluator** — `minAvailable`, `maxUnavailable`, integer/percentage forms, selectors, expected pods, disruptions allowed, unhealthy-pod eviction policy, and controller scale semantics.
11. **Unmanaged/static/mirror pod policy** — explicit behavior for pods with no reconstructable desired-state owner.
12. **Node health/unreachable semantics** — distinguish administratively drained, NotReady, unreachable, deleted, and partitioned nodes.
13. **Pod termination lifecycle model** — grace periods, `preStop`, finalizers, deletion timestamps, force deletion, and stuck-terminating detection.
14. **Stateful workload semantics** — StatefulSet identity, ordered rollout/termination, stable storage, ordinal safety, and quorum-aware drain constraints.
15. **DaemonSet semantics** — do-not-reschedule-as-ordinary-replica behavior and drain filtering.
16. **Job/CronJob semantics** — completed/failed pods, restart policy, active deadlines, parallelism/completions, and non-replica-controller behavior.
17. **Persistent-volume drain constraints** — local PVs, attachment/detachment, topology, RWO/RWOP constraints, CSI health, and data-loss prevention.
18. **Preflight capacity engine** — CPU, memory, ephemeral storage, extended resources, hugepages, GPUs/accelerators, pod slots, and allocatable-vs-requested checks.
19. **Scheduling constraint evaluator** — taints/tolerations, node selectors, affinity/anti-affinity, topology spread, zones, architecture/OS, and required node labels.
20. **Priority/preemption semantics** — priority classes, nominated nodes, preemption safety, and interaction with disruption budgets.
21. **Atomic multi-object operation journal** — durable intent/commit/abort records so a process crash cannot strand a half-applied drain.
22. **Idempotency keys / operation identity** — safe replay of reconcile and drain requests across retries and failover.

## P1 — Interface, security, multitenancy, and hand-off integrity

23. **Runtime schema validation** — validate `PK_ORCH_* /1` payloads against the shipped schemas at trust boundaries.
24. **Transport/API implementation** — concrete HTTP/gRPC/WIT/event/control-plane bindings for reconcile, drain, inventory, and errors.
25. **Protocol compatibility negotiation** — supported-version advertisement, downgrade rules, deprecation windows, and incompatible-peer refusal.
26. **Stable transport error mapping** — map model error codes to Kubernetes Status, HTTP status/problem details, or gRPC status/details.
27. **Authentication layer** — service/workload identity, certificate/token verification, expiry handling, and issuer/audience checks.
28. **Authorization/RBAC layer** — least-privilege verbs/resources/namespaces and explicit authorization of drain/reconcile/inventory operations.
29. **mTLS/service identity** — authenticated encryption and peer identity for remote control-plane boundaries.
30. **Admission/policy integration** — policy checks before mutating workload or node state, including tenant and maintenance restrictions.
31. **Tenant/environment/site isolation enforcement** — actual namespace/account/site scoping behind the boundaries declared in `contract.py`.
32. **Quota and fairness controller** — per-tenant/workload limits, queue fairness, starvation prevention, and overload admission rules.
33. **Timeout/deadline/cancellation semantics** — bounded operations and propagated cancellation through API/watch/eviction layers.
34. **Retry/backoff/jitter policy** — retryable-vs-terminal classification, exponential backoff, jitter, and retry budgets.
35. **Backpressure/rate limiting** — bounded queues, API QPS/burst limits, per-tenant limits, and overload shedding.
36. **Inventory snapshot identity** — snapshot IDs, timestamps, source resource versions, object UIDs, generations, owner references, and consistency markers.
37. **Handoff checkpoint/acknowledgement protocol** — successor scheduler acknowledgement, retry, resume, and exactly-once/at-least-once semantics.
38. **Handoff diff/change stream** — incremental updates after the initial inventory snapshot and gap detection/recovery.
39. **Cross-controller ownership resolution** — identify authoritative controller per workload and prevent duplicate reconciliation during migration.
40. **Configuration schema and loader** — typed runtime configuration, defaults, environment/site overlays, and startup validation.
41. **Configuration provenance/activation record** — version, author/issuer, digest, activation time, and active/previous configuration pointers.
42. **Transactional configuration rollback** — validate, stage, activate, health-check, and automatically or manually revert failed changes.
43. **Secret-management integration** — external secret references, rotation, redaction, and prohibition of secret material in ordinary diagnostics.

## P2 — Observability, resilience, performance, and certification

44. **Metrics implementation** — replica drift, queue depth, reconcile latency, drain latency/outcome, budget blocks, retries, API errors, and capacity failures.
45. **Structured logging** — operation IDs, workload/node identity, phase, outcome, reason code, and redaction policy.
46. **Distributed tracing** — spans across API request, queue, cache lookup, eviction, scheduler interaction, and handoff.
47. **Health/readiness/startup endpoints** — dependency readiness, informer sync state, leader status, queue health, and degraded-mode reporting.
48. **SLO measurement engine** — real measurement for 30-second convergence and zero-budget drain/inventory objectives.
49. **Alerting and error-budget policy** — burn-rate alerts, paging thresholds, maintenance suppression, and escalation routing.
50. **Durable audit trail** — authenticated operator/action ledger for drain, configuration, policy, and handoff changes.
51. **Reconcile-stall detector** — detect no-progress loops, stuck work items, repeated conflicts, and dependency deadlock.
52. **Network-partition behavior** — cache staleness limits, read/write policy during control-plane loss, reconciliation pause/resume, and split-brain safeguards.
53. **Dependency circuit breakers** — bounded failure propagation for API server, storage, policy, identity, and successor-scheduler dependencies.
54. **Chaos/fault-injection suite** — API timeouts, watch loss, process crash, leader loss, network partition, storage delay, node disappearance, and eviction rejection.
55. **Property-based/state-machine testing** — invariant checking across arbitrary reconcile/drain sequences and failure injection.
56. **Fuzz testing** — schemas, configuration, pod/node state, malformed events, and error serialization.
57. **Concurrency/race tests** — simultaneous desired changes, drains, watch updates, leader transitions, and duplicate events.
58. **Real-cluster integration tests** — kind/k3s/Kubernetes matrix with controllers, PDBs, PVCs, taints, affinity, Jobs, StatefulSets, and failure cases.
59. **Migration parity test harness** — execute incumbent and successor behavior against identical scenarios and compare observable outcomes.
60. **Scale/performance benchmarks** — nodes, pods, workloads, event rate, reconcile throughput, queue latency, memory, CPU, and watch pressure.
61. **Soak/endurance tests** — long-duration drift, leak, queue growth, watch reconnect, and error-budget validation.
62. **Recovery/RTO/RPO tests** — process/node/control-plane recovery with explicit maximum recovery objectives.

## P3 — Supply chain, release engineering, governance, and evidence quality

63. **Packaging metadata (`pyproject.toml`)** — explicit Python compatibility, build backend, package data, optional `pk_core` integration dependency, and installation metadata.
64. **Pinned dependency manifest/lock strategy** — exact or policy-bounded versions and repeatable resolution for integrated deployments.
65. **SBOM generation** — SPDX/CycloneDX inventory covering Python and external runtime/controller dependencies.
66. **Artifact signing and provenance** — signed build outputs, source revision, builder identity, reproducible-build metadata, and verification policy.
67. **Vulnerability/license scanning gates** — dependency, container, source, secret, and license-policy checks.
68. **CI matrix** — supported Python versions, normal/optimized mode, operating systems as relevant, schema tests, lint/static analysis, and Kubernetes integration versions.
69. **Static type checking** — enforced type analysis for model and adapters, including API object conversion boundaries.
70. **Lint/security static analysis** — formatter/linter plus unsafe-pattern scanning and policy gates.
71. **Release rollback package** — tested previous-version rollback, compatibility checks, state migration rules, and rollback evidence.
72. **Architecture Decision Record** — approved rationale for the compatibility model, Kubernetes assumptions, migration boundary, and chosen semantics.
73. **Threat model** — assets, trust boundaries, attacker capabilities, abuse cases, mitigations, and residual risks.
74. **Operator runbook** — drain failures, no-capacity incidents, watch desynchronization, leader loss, stuck reconciliation, rollback, and emergency disable.
75. **Ownership/RACI and escalation path** — accountable owner, on-call route, dependency owners, security contact, and change approvers.
76. **Evidence traceability matrix** — map each of the 100 checklist requirements to concrete implementation, test, runtime evidence, or an explicit unresolved status.
77. **Evidence-quality gate** — prevent a requirement from being marked satisfied solely because descriptive contract text exists; require executable or externally verifiable evidence where the requirement is implementation-level.
78. **`pk_core` integration pin/test fixture** — a reproducible way to run the 100-item conformance suite in CI instead of silently skipping all integrated tests.
79. **Conformance fixtures for all v1 schemas** — positive/negative request/response examples and compatibility vectors.
80. **Master prompt/workflow corpus restoration (conditional)** — restore the previously documented `MASTER.md` / per-item master artifacts if this distribution is contractually expected to carry them; otherwise formally remove that packaging requirement.

## Explicit non-goals that should remain external

Cluster provisioning, network/CNI implementation, image building, registry operation, and successor-platform scheduling are intentionally outside INV-04. Their integration contracts and failure behavior still need tests, but those systems should not be duplicated inside this component.
