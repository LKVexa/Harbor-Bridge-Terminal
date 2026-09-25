> **Historical baseline.** This is the v4.2.0 audit. The v4.3.0 remediation outcome is in `REMEDIATION_REPORT.md` and `STATUS_REGISTER.json`.

# INV-57 Durable Execution — v4.2.0 Post-Hardening Audit

**Audit date:** 2026-09-22  
**Input:** supplied `inv57_durable_execution.zip` at v4.1.0  
**Output version:** 4.2.0  
**Audit scope:** repository content physically present in the supplied archive plus behavior reproducible in the local Python environment. External `pk_core` evidence was not available.

## Executive result

- Checklist items fully evidenced in the updated standalone repository: **11/100**.
- Checklist items partially evidenced: **27/100**.
- Checklist items with no concrete satisfying artifact/implementation/test: **62/100**.
- Core Python compile: **PASS**.
- Self-contained test suite: **PASS**.
- External `pk_core` conformance tests: **SKIPPED** because `pk_core` is not bundled/importable in this standalone archive.
- Production readiness: **not demonstrated by this repository alone**. The reference replay core is materially safer, but the production integration, security, observability, performance, operations, and distributed-coordination surfaces remain incomplete.

`TRACEABILITY.json` is the machine-readable 100-item status/evidence map used for the counts above.

## Baseline defects found and fixed

1. **Duplicate-effect crash window:** v4.1 recorded only completed `(activity_name, result)` tuples. A process loss after an external effect but before history append could cause blind re-execution. v4.2 records `started` before invoking the activity and treats a missing outcome as `ActivityInDoubt`, requiring reconciliation rather than automatic retry.
2. **No independently runnable core tests:** every v4.1 test lived under a class-level `pk_core` skip. v4.2 adds a stdlib-only core suite; package-version validation also runs without `pk_core`.
3. **Package import coupled to `pk_core`:** importing `inv57_durable_execution` failed when the framework was absent. v4.2 lazy-loads framework-bound objects and keeps the replay engine importable.
4. **Untyped/unvalidated mutable history:** v4.2 adds typed history events, deterministic result encoding, strict JSON loading, sequence checks, and a SHA-256 hash chain.
5. **No bounded reference history:** v4.2 adds `max_events` and checks capacity before user activity code runs.
6. **Same-worker concurrent execution not refused:** v4.2 rejects concurrent `run()` calls on one `Worker` instance.
7. **Replay identity too weak:** v4.2 supports stable `activity_id` and optional `fingerprint` so code/input-version changes can invalidate replay deterministically.
8. **Exception text could become durable diagnostic data in future failure handling:** v4.2 records failure state without persisting the exception message.
9. **Framework evidence mapped to the wrong resilience item:** the crash-resume demonstration previously overwrote the first resilience finding (C051); v4.2 maps it to C057/C058.
10. **README claimed a non-existent `MASTER.md`:** the file was absent from the supplied archive. v4.2 removes the false inclusion claim and explicitly records the omission rather than fabricating source material.
11. **History backend was not actually replaceable:** v4.2 adds a `HistoryStore` protocol so a production persistent adapter can be supplied without changing `Worker` replay logic.

## Validation performed

- `python -m compileall` over the repository.
- `python -m unittest discover -s inv57_durable_execution/tests -v`.
- optimized-mode replay check via a subprocess using `python -O`.
- JSON parse/structural validation of `CHECKLIST.json` and `TRACEABILITY.json`.
- archive/path scan for traversal entries before extraction.
- source scan for stale v4.1 version references, bare runtime assertions in the replay engine, and the absent `MASTER.md` claim.

## Remaining missing or partial production components

The table below groups every checklist item that is not fully evidenced. `PARTIAL` means some repository evidence exists but production coverage is incomplete; `MISSING` means no satisfying implementation/artifact/test was found.

| Gap | Status | Checklist | Component still required |
|---:|---|---|---|
| MC-01 | MISSING | C009 | **Accountable ownership and escalation path.** No named accountable owner, on-call/escalation chain, or ownership metadata is included. |
| MC-02 | MISSING | C010 | **Approved architecture decision record.** No ADR approves the Dapr Durable Workflow Engine choice, alternatives, tradeoffs, or checkpointed/resumable workflow architecture. |
| MC-03 | PARTIAL/MISSING | C011, C012 | **SHALL-level requirements and deployment-context matrix.** Mandatory behaviors exist, but there is no complete SHALL/SHALL-NOT specification with testable acceptance criteria across cloud, datacenter, near-edge, and far-edge contexts. |
| MC-04 | PARTIAL | C013 | **Complete non-functional requirements and measured acceptance criteria.** Three SLO targets are declared, but the complete latency/availability/durability/consistency/isolation/determinism requirement set and measured evidence are absent. |
| MC-05 | MISSING | C014, C015 | **Outcome semantics and workflow lifecycle state machine.** Success/partial/degraded/retryable/terminal semantics and legal lifecycle states/transitions are not specified as a formal model. |
| MC-06 | MISSING | C016 | **Backward-compatibility and versioning policy.** No supported history/schema/workflow-code compatibility policy, deprecation policy, or version-skew rules exist. |
| MC-07 | PARTIAL | C017 | **Capacity, quotas, and fairness model.** The in-memory event count is bounded, but tenant/workload quotas, scheduling fairness, and capacity ceilings are not defined. |
| MC-08 | MISSING | C018 | **Disconnected/intermittent network semantics.** No explicit offline, partitioned, reconnect, or store-unavailable workflow semantics are defined. |
| MC-09 | MISSING | C019 | **Constraint-precedence policy.** No deterministic precedence rules resolve conflicts among security, residency, SLO, and cost constraints. |
| MC-10 | PARTIAL/MISSING | C021, C022 | **Complete boundary inventory and versioned typed schemas.** The contract names history/activity/replay interfaces, but no concrete versioned schema files define all external API/RPC/event/control-plane boundaries. |
| MC-11 | MISSING | C023 | **Boundary authentication model.** No per-interface authentication requirements, identity types, trust roots, or credential lifecycle are defined. |
| MC-12 | MISSING | C024 | **Authorization/capability model.** No explicit capabilities, RBAC/ABAC policy, least-authority tokens, or permission matrix is implemented. |
| MC-13 | PARTIAL | C025 | **Timeout, cancellation, retry, idempotency, and backpressure contract.** Replay identity and conservative in-doubt behavior are implemented, but the rest of the operational interaction semantics are not. |
| MC-14 | MISSING | C026 | **Machine-readable error model.** Exceptions exist, but there is no stable error-code taxonomy or typed error-detail schema for external consumers. |
| MC-15 | MISSING | C027 | **Cross-version peer compatibility behavior.** No version-negotiation, upgrade/downgrade, or mixed-version interoperability rules are defined. |
| MC-16 | PARTIAL | C028 | **Complete interface resource limits.** History length and same-worker concurrency are bounded; payload, queue, connection, execution, and fan-out limits are incomplete. |
| MC-17 | PARTIAL | C029 | **Versioned reference examples and conformance fixtures.** README examples and unit fixtures exist, but there is no formal fixture corpus for every external interface/version. |
| MC-18 | MISSING | C030, C083 | **Adjacent-layer integration harness and tests.** No executable tests integrate with INV-50 state, INV-53 message reliability, Dapr, or other declared adjacent layers/execution tiers. |
| MC-19 | MISSING | C031 | **Pinned production implementation/specification.** Dapr Durable Workflow Engine is named but no approved version, lock, compatibility constraint, digest, or release artifact is pinned. |
| MC-20 | PARTIAL | C032 | **Production artifact/configuration/state separation model.** The reference engine separates code from in-memory history, but the production packaging and mutable configuration/state boundaries are not defined. |
| MC-21 | MISSING | C033, C034 | **Declarative configuration schema, secure defaults, and validation.** No configuration schema, default profile, validation layer, or fail-closed activation path exists. |
| MC-22 | MISSING | C035 | **Site/environment configuration overlays.** No site-, environment-, or tenant-specific configuration mechanism exists without rebuilding artifacts. |
| MC-23 | MISSING | C036 | **Configuration provenance ledger.** No record of configuration author, version, source, approval, or activation time exists. |
| MC-24 | MISSING | C037 | **Atomic configuration activation.** No transactional/atomic configuration update mechanism protects against partial activation. |
| MC-25 | PARTIAL | C038 | **Executable configuration/deployment rollback.** Rollback intent is documented only at a high level; no tested automatic or operator rollback mechanism is packaged. |
| MC-26 | PARTIAL | C039 | **Secret-provider integration and secret separation.** Failure records avoid exception text, but credentials/secrets are not modeled, externalized, rotated, or redacted through a secret provider. |
| MC-27 | PARTIAL | C040 | **Deterministic bootstrap/deployment path.** Test commands exist, but there is no one-command or declarative path from an empty node/environment to a healthy production deployment. |
| MC-28 | PARTIAL | C041 | **Complete durable-execution threat model.** Only a short threat list exists; malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse are not fully modeled. |
| MC-29 | MISSING | C042, C043 | **Least privilege and ambient-authority elimination.** No runtime capability sandbox, filesystem/network/device restrictions, or least-privilege identity design is implemented. |
| MC-30 | MISSING | C044 | **Trust bootstrap for nodes/peers/artifacts/providers/control plane.** No authentication/attestation chain establishes trust before durable-execution actors are accepted. |
| MC-31 | MISSING | C045 | **Artifact signature, digest, provenance, and approved-version verification.** No supply-chain verification gate, SBOM/provenance validation, or signature policy is implemented. |
| MC-32 | MISSING | C046 | **Tenant/workload isolation enforcement.** The contract states boundaries, but there is no concrete execution/memory/state/network isolation mechanism. |
| MC-33 | MISSING | C047 | **Encryption and managed key rotation.** No transport/storage encryption configuration or managed key lifecycle is included. |
| MC-34 | MISSING | C048 | **Safe behavior when trust/key/time dependencies fail.** No fail-closed/degraded policy covers identity, attestation, policy, key, or time-service outages. |
| MC-35 | PARTIAL | C049 | **Security-sensitive audit event pipeline.** Workflow history is hash chained, but administrative/security-sensitive operations do not emit a dedicated tamper-evident audit stream. |
| MC-36 | PARTIAL/MISSING | C050, C087 | **Threat-derived adversarial/security test suite.** Tamper/leakage tests exist, but privilege escalation, injection, replay, spoofing, escape, side-channel, and exhaustion testing is absent. |
| MC-37 | PARTIAL/MISSING | C051, C052 | **Full failure taxonomy plus health/stall detection.** The contract lists several failures, but there is no complete infrastructure failure matrix or automated liveness/stall thresholding. |
| MC-38 | MISSING | C053, C054 | **Bounded retry, backoff/jitter, admission control, load shedding, circuit breaking.** These cascade-prevention and retry-control mechanisms are not implemented. |
| MC-39 | MISSING | C055, C056 | **Failover and degraded-operation model.** No cross-node/site/provider failover rules or noncritical-dependency degraded mode is implemented. |
| MC-40 | PARTIAL | C058 | **Distributed ownership/fencing and split-brain protection.** Single-worker duplicate replay is hardened, but no lease, fencing token, epoch, CAS ownership, or stale-worker rejection exists across processes/nodes. |
| MC-41 | MISSING | C059, C060 | **Quarantine/freeze/disable controls and fault-injection recovery suite.** No operational isolation controls or systematic failure-injection harness proves recovery objectives. |
| MC-42 | PARTIAL/MISSING | C061, C062, C063, C064 | **Performance baselines, percentile thresholds, load matrix, and tenant overhead.** No reproducible benchmark evidence covers latency/throughput/startup/resources across steady, burst, overload, scaling, recovery, and per-tenant/workload cases. |
| MC-43 | PARTIAL/MISSING | C065, C066, C067 | **Performance profiling, optimization, and comprehensive resource bounds.** No serialization/copy/context-switch/network-hop audit or optimization work exists; only history-count and same-worker bounds are present. |
| MC-44 | MISSING | C068 | **Edge power and thermal measurement.** No constrained-node power/thermal benchmark or acceptance threshold exists. |
| MC-45 | MISSING | C069 | **Capacity model and saturation signals.** No predictive capacity model relates history/workflow/activity load to CPU, memory, storage, queue depth, or saturation. |
| MC-46 | MISSING | C070 | **Performance regression release gate.** No automated release blocker compares benchmark results to approved startup/density/throughput/tail-latency thresholds. |
| MC-47 | MISSING | C071 | **Health/readiness/version/config/dependency/capability status surface.** No operator/API endpoint or machine-readable status view exposes runtime health and active capabilities. |
| MC-48 | PARTIAL/MISSING | C072, C073, C074 | **Metrics, structured logs, and distributed tracing implementation.** Signal names are declared, but no telemetry emitter, stable contextual logging, or trace-context propagation exists. |
| MC-49 | PARTIAL/MISSING | C075, C076, C077, C078 | **Privacy-safe diagnostics, decision reasons, explain view, and lineage/topology correlation.** No operator explainability subsystem links decisions to inputs, policy, topology, release lineage, and infrastructure graph. |
| MC-50 | MISSING | C079, C080 | **Telemetry governance plus dashboards/alerts.** No retention/sampling/privacy/export policy or dashboards/alerts distinguish load, degradation, rejection, dependency failure, attack, and defect. |
| MC-51 | PARTIAL | C082 | **Complete public-interface contract tests.** Core replay behavior is tested, but versioned external interface schemas and exhaustive contract tests are absent. |
| MC-52 | MISSING | C084, C093 | **Platform/protocol compatibility matrix and tests.** No supported CPU/runtime/hypervisor/provider/protocol matrix or automated compatibility certification exists. |
| MC-53 | MISSING | C085 | **Fuzz/property testing.** No fuzzing exists for serialized history, schemas, protocol handlers, RPC/WIT boundaries, or other untrusted input surfaces. |
| MC-54 | PARTIAL | C086 | **Shared/distributed-state concurrency and race tests.** Same-worker concurrency refusal is tested, but concurrent workers sharing a persistent history store are not exercised. |
| MC-55 | MISSING | C088 | **Benchmark, soak, burst, and fleet-scale test suites.** No long-duration, burst, scale, or fleet workload harness/evidence exists. |
| MC-56 | PARTIAL | C089 | **Disaster, partition, reconnect, and degraded-control-plane tests.** Crash/replay tests exist, but network/site/provider/control-plane disaster cases are not exercised. |
| MC-57 | MISSING | C090, C100 | **Machine-readable production acceptance evidence and formal exit gate.** No self-contained release evidence bundle or executable production exit gate can certify the repository; external pk_core is unavailable here. |
| MC-58 | PARTIAL | C091 | **Measured production SLOs plus support commitments.** Targets/error budgets are declared, but measured evidence, support hours, response objectives, and ownership commitments are absent. |
| MC-59 | PARTIAL | C092 | **Canary/staged rollout, rollback, and emergency-disable procedures.** High-level intent exists, but there are no deployment manifests/scripts, canary criteria, rollout stages, rollback rehearsal, or kill-switch implementation. |
| MC-60 | MISSING | C094 | **Patching, vulnerability-response, and EOL policy.** No vulnerability SLA, patch cadence, supported-version window, or end-of-life policy is documented. |
| MC-61 | PARTIAL | C095 | **Persistent backup/restore/migration/reconstruction procedures.** Legacy in-memory migration and in-doubt reconciliation exist, but no production history backup/restore/migration/reconstruction tooling is included. |
| MC-62 | PARTIAL | C096 | **Complete day-0/day-1/day-2 operator runbooks.** README intent is too thin for production operations; prerequisites, commands, decision trees, failure handling, and rollback steps are missing. |
| MC-63 | MISSING | C097 | **Incident severity, paging, escalation, containment, and recovery procedures.** No incident response plan or operational contact/escalation model exists. |
| MC-64 | MISSING | C098 | **Recurring security/configuration/dependency/architecture review process.** No review cadence, evidence template, owner, or automation exists. |
| MC-65 | MISSING | C099 | **Exception/waiver/technical-debt/deprecation ledger.** No governed ledger tracks deviations, owners, rationale, expiry dates, or deprecated behavior. |

## Durable-execution-specific structural gaps not solved by the reference engine

- **Persistent production history adapter:** only `InMemoryHistoryStore` is provided. A production `HistoryStore` implementation still needs atomic/conditional append, durable persistence, consistency semantics, failover behavior, retention/compaction, and recovery.
- **Workflow instance identity and namespace:** the reference `Worker` has no durable workflow/run ID, tenant/site namespace, generation/epoch, or ownership record.
- **Distributed fencing/leases:** two workers against the same future store could race; no CAS ownership, lease renewal, fencing token, or stale-owner rejection is implemented.
- **External effect protocol:** `ActivityInDoubt` prevents blind retries but does not prove exactly-once external effects. Production requires idempotency keys, transactional outbox/inbox, receipt reconciliation, or equivalent effect-specific protocol.
- **INV-50 state adapter:** no integration binds the history protocol to the declared state abstraction dependency.
- **INV-53 message adapter:** no integration binds activity dispatch/acknowledgment to the declared reliable messaging dependency.
- **History lifecycle tooling:** no compaction/snapshot/archival/retention policy or large-history continuation mechanism exists.
- **Workflow lifecycle controls:** cancellation, termination, suspension/resume, timeout, retry policy, and operator intervention states are not modeled as a complete state machine.
- **Cross-process crash semantics:** the reference engine simulates abrupt loss but does not validate fsync/commit boundaries or database transaction behavior on a real backend.

## Repository engineering gaps outside the 100-item checklist

1. **`pk_core` is not bundled or pinned.** The external production conformance gate cannot be reproduced from this ZIP alone.
2. **No build/package manifest.** There is no `pyproject.toml`, wheel/sdist configuration, or declared dependency metadata for a standalone release.
3. **No CI workflow.** There is no checked-in automation for tests, optimized-mode checks, security scanning, traceability validation, or release gates.
4. **No license/notice file.** Distribution terms are not present in the supplied repository.
5. **No deployment artifacts.** There are no Dapr component definitions, Kubernetes manifests, Helm/Kustomize assets, service units, or equivalent deployment descriptors.
6. **No SBOM/provenance/signing artifacts.** Supply-chain metadata and verification evidence are absent.
7. **No benchmark evidence bundle.** Performance targets are declarations only.
8. **Original `MASTER.md` source artifact remains unavailable.** The README was corrected; the missing source prompt/workflow content was not reconstructed from guesswork.

## Release recommendation for this repository state

Use v4.2.0 as a **hardened reference/conformance component**, not as a production durable workflow runtime. The replay core now fails safer around ambiguous in-flight activities and has independently runnable tests, but production certification should remain blocked until the missing security, persistence, distributed-coordination, observability, integration, performance, and operations components above are implemented and evidenced.
