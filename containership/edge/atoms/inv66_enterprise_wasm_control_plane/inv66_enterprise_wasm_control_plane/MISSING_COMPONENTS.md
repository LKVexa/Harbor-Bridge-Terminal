# INV-66 v4.2.0 — Missing Components Audit

This is the post-hardening gap inventory for the **updated** repository.  “Missing” means no production-grade implementation or auditable artifact is present in this archive; a sentence in `contract.py` or a generic checklist finding is not counted as implementation evidence.

## Architecture and governance

1. **MC-001 — Bundled master prompt/workflow source (`MASTER.md`)** — **Medium** — README previously claimed it was present, but it is not in the archive. Restore the authoritative 100-item master prompt/workflow source or remove it from the release bill of materials. *(C020, C090, C100)*
2. **MC-002 — Approved architecture decision record (ADR)** — **High** — No ADR records the Cosmonic Control/wasmCloud technology choice, alternatives, constraints, or approval. *(C010)*
3. **MC-003 — Accountable owner and escalation matrix** — **High** — No named service owner, security owner, on-call owner, or escalation route is packaged. *(C009, C097)*
4. **MC-004 — Deployment/topology architecture specification** — **High** — No production topology defines control-plane instances, trust zones, stores, sites, dependency endpoints, or failure domains. *(C003, C005, C006, C051)*
5. **MC-005 — Production source-of-truth design** — **Critical** — The contract says the audit log is authoritative, but only process-local memory exists; no durable authoritative store or consistency model is implemented. *(C004, C032, C057, C095)*

## Requirements and semantics

6. **MC-006 — Normative SHALL requirements specification** — **High** — The checklist asks for testable requirements, but the archive has no separate normative requirements document with IDs, acceptance criteria, and owners. *(C011-C019)*
7. **MC-007 — Requirements traceability matrix (RTM)** — **High** — No machine-readable mapping connects all 100 requirements to code, tests, evidence, exceptions, and release status. *(C020, C090, C100)*
8. **MC-008 — Lifecycle/state-transition model** — **High** — No explicit state machine defines proposed/admitted/rejected/deployed/rolled-back/quarantined states and legal transitions. *(C014-C015)*
9. **MC-009 — Capacity, quota, and fairness model** — **High** — `max_components` and manifest bytes are local parser limits only; tenant/lattice quotas, concurrency budgets, and fairness are absent. *(C017, C028, C067, C069)*
10. **MC-010 — Offline/partition semantics** — **High** — No documented or implemented behavior exists for identity, policy, registry, signer, deployment-manager, or audit-store unavailability. *(C018, C048, C055-C057, C089)*
11. **MC-011 — Constraint precedence policy** — **Medium** — No deterministic precedence rules resolve security, residency, SLO, availability, and cost conflicts. *(C019)*

## Interfaces and integration

12. **MC-012 — Versioned typed admission schema** — **Critical** — `PK_ECP_ADMIT/1` is named but no JSON Schema, protobuf, WIT, OpenAPI, or equivalent typed contract is included. *(C021-C022, C082)*
13. **MC-013 — Versioned RBAC administration schema/API** — **Critical** — `PK_ECP_RBAC/1` has no typed request/response contract or administration surface. *(C021-C024)*
14. **MC-014 — Versioned audit event schema/API** — **Critical** — `PK_ECP_AUDIT/1` has no formal external event schema, query/export API, or compatibility rules. *(C021-C022, C027)*
15. **MC-015 — Authentication boundary** — **Critical** — `admit()` accepts a caller-supplied user string; there is no authenticated principal, token validation, mTLS, workload identity, or peer attestation. *(C023, C044)*
16. **MC-016 — Structured machine-readable error model** — **High** — Denials are free-form strings rather than stable error codes with typed details and remediation metadata. *(C026)*
17. **MC-017 — Idempotency, timeout, cancellation, retry, and backpressure contract** — **High** — No request IDs/idempotency keys, deadlines, retry classifications, queue semantics, or overload protocol are defined. *(C025, C028, C053-C054)*
18. **MC-018 — Protocol/version compatibility matrix and negotiation** — **High** — No supported-version matrix or cross-version test fixtures are bundled. *(C016, C027, C093)*
19. **MC-019 — Real deployment-manager adapter** — **Critical** — Admitted manifests are appended to an in-memory `forwarded` list; no INV-63 client, transport, acknowledgement, failure handling, or delivery semantics exist. *(C003, C021, C030, C051)*
20. **MC-020 — Adjacent-layer integration adapters/tests** — **Critical** — No executable integrations exist for INV-64 application model, GAP-13 policy engine, GAP-07 provenance/signing, identity, registry, or audit storage. *(C003, C030, C083)*
21. **MC-021 — GitOps ingestion/change-controller integration** — **High** — The source function names enterprise management/GitOps, but no Git repository watcher, desired-state ingestion interface, webhook, change-set model, or handoff to reconciliation is present. *(C011-C012, C021, C030)*

## Configuration and state management

22. **MC-022 — Declarative production configuration schema/loader** — **Critical** — RBAC, registries, signers, limits, endpoints, and environment/site overrides are constructor arguments only. *(C033-C035)*
23. **MC-023 — Configuration provenance and version history** — **High** — No author, source revision, approval, activation timestamp, or configuration digest is retained. *(C036)*
24. **MC-024 — Atomic configuration activation and rollback** — **Critical** — No transaction/staging mechanism protects partial policy updates or enables safe rollback. *(C037-C038)*
25. **MC-025 — Persistent RBAC/policy store** — **Critical** — Roles are process-local immutable mappings with no enterprise persistence, synchronization, review, or delegated administration. *(C032-C038, C098)*
26. **MC-026 — Approved registry/signer policy administration store** — **Critical** — Registry and signer allowlists have no persistent control plane, approval workflow, versioning, or distribution mechanism. *(C032-C038, C045)*
27. **MC-027 — Secret-management integration** — **Critical** — No KMS/Vault/secret provider integration or secret-reference model exists. *(C039, C047-C048)*
28. **MC-028 — Deterministic bootstrap/install packaging** — **High** — No `pyproject.toml`, dependency lock/constraints, install command, container image, service unit, or reproducible bootstrap artifact is bundled. *(C031, C040)*

## Security, trust, and isolation

29. **MC-029 — Cryptographic artifact signature verification** — **Critical** — Admission trusts the manifest’s signer string; it does not verify an actual signature, certificate/key identity, transparency record, or signing policy. *(C045)*
30. **MC-030 — Artifact digest/provenance verification** — **Critical** — The engine hashes the admission manifest but does not resolve/verify immutable artifact digests, SBOM/provenance attestations, approved versions, or registry metadata. *(C045)*
31. **MC-031 — Enterprise identity federation** — **Critical** — No OIDC/SAML/workload identity integration, token audience/issuer validation, session policy, or identity lifecycle exists. *(C023, C044)*
32. **MC-032 — Organisation/tenant RBAC hierarchy and capability model** — **Critical** — The current `(user, lattice) -> role` map does not implement organisation scope, tenant delegation, groups, service principals, capability scoping, or deny policy. *(C006, C024, C042, C046)*
33. **MC-033 — External policy-engine enforcement** — **Critical** — GAP-13 is declared as a dependency but is not queried, cached, version-pinned, or failure-handled. *(C019, C030, C048)*
34. **MC-034 — Transport/storage encryption and key rotation** — **Critical** — There is no network transport or durable storage layer and therefore no implemented TLS/mTLS, at-rest encryption, managed keys, or rotation workflow. *(C047)*
35. **MC-035 — Durable tamper-evident audit anchoring** — **Critical** — The local SHA-256 chain detects accidental mutation but an actor able to rewrite all in-memory records can recompute it; no signed/WORM/remote anchor exists. *(C049)*
36. **MC-036 — Formal threat model** — **High** — No STRIDE/attack-tree/abuse-case artifact covers malicious tenants, compromised control-plane actors, replay, confused deputy, dependency compromise, or supply-chain attacks. *(C041)*
37. **MC-037 — Security adversarial and fuzz suite** — **High** — No fuzzing or dedicated tests cover replay, spoofing, injection, privilege escalation, side channels, parser bombs, or resource exhaustion. *(C050, C085, C087)*

## Resilience and distributed-systems behavior

38. **MC-038 — Durable state store with crash recovery/replay** — **Critical** — Audit and forwarded state disappear on process restart; no journal, transaction log, snapshot, or replay protocol exists. *(C057, C095)*
39. **MC-039 — HA replication/consensus/leader election** — **Critical** — No multi-instance coordination, fencing, epoch/lease model, duplicate-owner protection, or split-brain handling exists. *(C055, C058)*
40. **MC-040 — Dependency health and degraded-mode controller** — **High** — No health model tracks identity, policy, registry, signing, deployment, or storage dependencies or decides safe degraded behavior. *(C052, C056)*
41. **MC-041 — Bounded retry/circuit breaker/load shedding** — **High** — No remote calls exist yet, and no reusable retry/backoff/jitter, breaker, queue, or shedding policy is implemented for future adapters. *(C053-C054)*
42. **MC-042 — Quarantine/freeze/emergency-disable control** — **High** — README mentions package removal, but no runtime administrative freeze, tenant/lattice quarantine, kill switch, or audited emergency action exists. *(C059, C092)*
43. **MC-043 — Fault-injection/recovery test suite** — **High** — No dependency failure, crash, disk-full, timeout, partition, reconnect, or stale-controller tests exist. *(C060, C089)*

## Performance and resource efficiency

44. **MC-044 — Reproducible benchmark/load/soak suite** — **High** — No latency, throughput, startup, CPU, memory, storage, network, burst, overload, recovery, or fleet-scale measurements are packaged. *(C061-C064, C088)*
45. **MC-045 — Performance thresholds and regression gate** — **High** — The contract declares p99 <50 ms, but no benchmark enforces p50/p95/p99/worst-case or blocks regressions. *(C062, C070)*
46. **MC-046 — Bounded audit/forwarded retention** — **Critical** — Both in-memory collections grow without retention, compaction, persistence, or backpressure, creating unbounded memory growth. *(C067)*
47. **MC-047 — Capacity/saturation model** — **High** — No capacity formula or signal identifies safe admission QPS, queue depth, audit growth, tenant count, or scaling thresholds. *(C069)*
48. **MC-048 — Edge power/thermal characterization** — **Low/conditional** — No constrained-edge power or thermal measurements establish whether this central control-plane component is suitable where C068 applies. *(C068)*

## Observability and explainability

49. **MC-049 — Health/readiness/version/config/dependency endpoint** — **High** — No operator endpoint exposes health, readiness, active version, config digest, dependency state, or capability set. *(C071)*
50. **MC-050 — Metrics instrumentation/export** — **High** — Contract signal names are declarations only; no counters/histograms/gauges or Prometheus/OTel exporter exist. *(C072)*
51. **MC-051 — Structured operational logging** — **High** — No stable tenant/lattice/workload/request identifiers, structured log schema, redaction policy, or sink integration exists. *(C073, C075)*
52. **MC-052 — Distributed tracing/context propagation** — **High** — No trace/span propagation is present across admission, policy, provenance, audit, or deployment boundaries. *(C074)*
53. **MC-053 — Decision explainability/policy linkage view** — **High** — Reasons exist, but there is no operator explain view linking a decision to authenticated principal, exact policy/config version, provenance result, topology, and constraints. *(C076-C078)*
54. **MC-054 — Telemetry retention/privacy/export policy and dashboards/alerts** — **High** — No retention/sampling/privacy configuration, dashboards, alerts, or incident-oriented signal separation exists. *(C079-C080)*

## Testing, certification, release, and operations

55. **MC-055 — Public-interface contract test suite** — **High** — Local unit tests now cover the engine, but no schema-driven contract tests exist for admit/RBAC/audit APIs. *(C082)*
56. **MC-056 — End-to-end integration suite** — **Critical** — No tests exercise a real identity provider, policy engine, provenance verifier, registry, audit store, deployment manager, or wasmCloud lattice. *(C030, C083)*
57. **MC-057 — Compatibility/platform test matrix** — **High** — No CI matrix validates supported Python/runtime versions, OS/CPU architectures, wasmCloud/Cosmonic versions, or protocol combinations. *(C084, C093)*
58. **MC-058 — Distributed concurrency/race suite** — **High** — v4.2.0 adds an in-process concurrency test, but no multi-process/multi-node race, failover, duplicate-delivery, or stale-leader suite exists. *(C086)*
59. **MC-059 — Disaster/partition/reconnect certification suite** — **High** — No restore, region/site loss, network partition, reconnect, or degraded-control-plane acceptance tests exist. *(C089)*
60. **MC-060 — Full machine-readable production acceptance evidence bundle** — **High** — v4.2.0 now includes `VERIFICATION.json` for local checks, but no generated 100-item production acceptance evidence exists; the bundled full conformance tests require external `pk_core` and skip when it is absent. *(C090)*
61. **MC-061 — CI/CD release pipeline and staged rollout artifacts** — **Critical** — No pipeline configuration, signed build, canary/staged rollout, deployment manifest, or automated rollback integration is included. *(C092)*
62. **MC-062 — Vulnerability/SBOM/patch/EOL program artifacts** — **High** — No SBOM, dependency vulnerability policy, patch SLA, supported-version policy, or EOL schedule is packaged. *(C094)*
63. **MC-063 — Backup/restore/migration/reconstruction runbook** — **Critical** — No procedure or tooling exists because durable state itself is absent. *(C095)*
64. **MC-064 — Complete day-0/day-1/day-2 operational runbooks** — **High** — README provides only brief commands; production bootstrap, deployment, rotation, failure handling, capacity, restore, and maintenance procedures are missing. *(C096)*
65. **MC-065 — Incident response/on-call runbook** — **High** — No severity model, paging rules, containment steps, evidence preservation, recovery criteria, or communications workflow exists. *(C097)*
66. **MC-066 — Recurring review automation/evidence** — **Medium** — No scheduled access, policy, dependency, configuration, and architecture review mechanism or retained results are present. *(C098)*
67. **MC-067 — Exception/waiver/technical-debt register** — **Medium** — No machine-readable waiver owner, rationale, expiry, compensating control, or deprecation register exists. *(C099)*
68. **MC-068 — Formal production exit gate artifact** — **Critical** — No signed/generated gate proves architecture, security, resilience, performance, observability, testing, rollback, and ownership readiness; current generic checklist satisfaction is insufficient production evidence. *(C100)*
69. **MC-069 — Cross-lattice inventory service** — **High** — `contract.py` says INV-66 owns cross-lattice inventory, but the implementation only retains admitted manifest copies and offers no queryable, durable inventory model. *(C002, C011, C021)*
70. **MC-070 — Audit query/retention/export service** — **High** — The local audit snapshot has no retention class, index/query API, immutable export, SIEM integration, legal hold, or archival lifecycle. *(C049, C079, C095)*
71. **MC-071 — Repository license/notice metadata** — **Medium** — No `LICENSE` or `NOTICE` is bundled, so redistribution and third-party compliance terms are not established by this archive. *(repository governance artifact; not represented by a dedicated checklist item)*

## Post-hardening status

The v4.2.0 local decision engine is materially safer than v4.1.0: malformed manifests fail closed; policy inputs are defensively copied; output/audit snapshots do not expose live mutable state; manifests receive canonical SHA-256 identities; audit records are sequence-bound and domain-separated; resource limits exist for component count and manifest bytes; admission/audit ordering is serialized; and 11 self-contained tests run without `pk_core`.

Those fixes do **not** convert this archive into a production enterprise Wasm control-plane service. The 71 items above are the complete set of missing components identified in this repository-level audit.

## 4.3.0 disposition (generated by tools/mc_status.py — do not edit)

1420 checklist items executed: DONE 852, NA_PROPOSED 7, OPEN_EXTERNAL 21, OPEN_HUMAN 114, PARTIAL 426. No MC is closed: each needs an independent review (D05). Disposition is judged on the task (T) items; every MC also carries the shared D-item blockers D02 (hash-locked deps), D03 (owners) and D05 (review).

| MC | Severity | Disposition | DONE | PARTIAL | HUMAN | EXTERNAL | Title |
|---|---|---|---|---|---|---|---|
| MC-001 | Medium | PARTIAL | 15 | 3 | 2 | 0 | Bundled master prompt/workflow source (`MASTER.md`) |
| MC-002 | High | IMPLEMENTED_PENDING_HUMAN_DECISIONS | 14 | 3 | 3 | 0 | Approved architecture decision record (ADR) |
| MC-003 | High | PARTIAL | 11 | 4 | 5 | 0 | Accountable owner and escalation matrix |
| MC-004 | High | PARTIAL | 14 | 4 | 2 | 0 | Deployment/topology architecture specification |
| MC-005 | Critical | IMPLEMENTED_PENDING_HUMAN_DECISIONS | 16 | 2 | 2 | 0 | Production source-of-truth design |
| MC-006 | High | IMPLEMENTED_PENDING_HUMAN_DECISIONS | 16 | 2 | 2 | 0 | Normative SHALL requirements specification |
| MC-007 | High | IMPLEMENTED_PENDING_HUMAN_DECISIONS | 16 | 2 | 2 | 0 | Requirements traceability matrix (RTM) |
| MC-008 | High | PARTIAL | 15 | 3 | 2 | 0 | Lifecycle/state-transition model |
| MC-009 | High | PARTIAL | 13 | 5 | 2 | 0 | Capacity, quota, and fairness model |
| MC-010 | High | PARTIAL | 13 | 5 | 2 | 0 | Offline/partition semantics |
| MC-011 | Medium | PARTIAL | 14 | 4 | 2 | 0 | Constraint precedence policy |
| MC-012 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 15 | 3 | 1 | 1 | Versioned typed admission schema |
| MC-013 | Critical | PARTIAL | 13 | 6 | 1 | 0 | Versioned RBAC administration schema/API |
| MC-014 | Critical | PARTIAL | 14 | 5 | 1 | 0 | Versioned audit event schema/API |
| MC-015 | Critical | PARTIAL | 13 | 6 | 1 | 0 | Authentication boundary |
| MC-016 | High | PARTIAL | 16 | 3 | 1 | 0 | Structured machine-readable error model |
| MC-017 | High | PARTIAL | 15 | 4 | 1 | 0 | Idempotency, timeout, cancellation, retry, and backpressure contract |
| MC-018 | High | PARTIAL | 12 | 7 | 1 | 0 | Protocol/version compatibility matrix and negotiation |
| MC-019 | Critical | PARTIAL | 13 | 6 | 1 | 0 | Real deployment-manager adapter |
| MC-020 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 12 | 6 | 1 | 1 | Adjacent-layer integration adapters/tests |
| MC-021 | High | PARTIAL_EXTERNAL_DEPENDENCY | 9 | 8 | 1 | 2 | GitOps ingestion/change-controller integration |
| MC-022 | Critical | PARTIAL | 16 | 3 | 1 | 0 | Declarative production configuration schema/loader |
| MC-023 | High | PARTIAL | 13 | 5 | 2 | 0 | Configuration provenance and version history |
| MC-024 | Critical | PARTIAL | 13 | 6 | 1 | 0 | Atomic configuration activation and rollback |
| MC-025 | Critical | PARTIAL | 13 | 6 | 1 | 0 | Persistent RBAC/policy store |
| MC-026 | Critical | PARTIAL | 12 | 7 | 1 | 0 | Approved registry/signer policy administration store |
| MC-027 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 9 | 9 | 1 | 1 | Secret-management integration |
| MC-028 | High | PARTIAL | 12 | 7 | 1 | 0 | Deterministic bootstrap/install packaging |
| MC-029 | Critical | PARTIAL | 14 | 5 | 1 | 0 | Cryptographic artifact signature verification |
| MC-030 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 10 | 7 | 1 | 2 | Artifact digest/provenance verification |
| MC-031 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 10 | 7 | 2 | 1 | Enterprise identity federation |
| MC-032 | Critical | PARTIAL | 13 | 6 | 1 | 0 | Organisation/tenant RBAC hierarchy and capability model |
| MC-033 | Critical | PARTIAL | 12 | 7 | 1 | 0 | External policy-engine enforcement |
| MC-034 | Critical | PARTIAL | 10 | 8 | 2 | 0 | Transport/storage encryption and key rotation |
| MC-035 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 12 | 6 | 1 | 1 | Durable tamper-evident audit anchoring |
| MC-036 | High | PARTIAL | 14 | 3 | 3 | 0 | Formal threat model |
| MC-037 | High | PARTIAL | 11 | 7 | 2 | 0 | Security adversarial and fuzz suite |
| MC-038 | Critical | PARTIAL | 13 | 6 | 1 | 0 | Durable state store with crash recovery/replay |
| MC-039 | Critical | PARTIAL | 10 | 9 | 1 | 0 | HA replication/consensus/leader election |
| MC-040 | High | PARTIAL | 9 | 10 | 1 | 0 | Dependency health and degraded-mode controller |
| MC-041 | High | PARTIAL | 11 | 8 | 1 | 0 | Bounded retry/circuit breaker/load shedding |
| MC-042 | High | PARTIAL | 11 | 8 | 1 | 0 | Quarantine/freeze/emergency-disable control |
| MC-043 | High | PARTIAL_EXTERNAL_DEPENDENCY | 8 | 10 | 1 | 1 | Fault-injection/recovery test suite |
| MC-044 | High | PARTIAL_EXTERNAL_DEPENDENCY | 6 | 12 | 1 | 1 | Reproducible benchmark/load/soak suite |
| MC-045 | High | PARTIAL | 10 | 9 | 1 | 0 | Performance thresholds and regression gate |
| MC-046 | Critical | PARTIAL | 12 | 7 | 1 | 0 | Bounded audit/forwarded retention |
| MC-047 | High | PARTIAL | 8 | 9 | 3 | 0 | Capacity/saturation model |
| MC-048 | Low/conditional | NA_PROPOSED | 4 | 7 | 2 | 0 | Edge power/thermal characterization |
| MC-049 | High | PARTIAL | 15 | 4 | 1 | 0 | Health/readiness/version/config/dependency endpoint |
| MC-050 | High | PARTIAL | 11 | 8 | 1 | 0 | Metrics instrumentation/export |
| MC-051 | High | PARTIAL | 14 | 5 | 1 | 0 | Structured operational logging |
| MC-052 | High | PARTIAL | 13 | 6 | 1 | 0 | Distributed tracing/context propagation |
| MC-053 | High | PARTIAL | 13 | 6 | 1 | 0 | Decision explainability/policy linkage view |
| MC-054 | High | PARTIAL | 15 | 3 | 2 | 0 | Telemetry retention/privacy/export policy and dashboards/alerts |
| MC-055 | High | PARTIAL | 12 | 7 | 1 | 0 | Public-interface contract test suite |
| MC-056 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 12 | 6 | 1 | 1 | End-to-end integration suite |
| MC-057 | High | PARTIAL_EXTERNAL_DEPENDENCY | 10 | 7 | 1 | 2 | Compatibility/platform test matrix |
| MC-058 | High | PARTIAL | 13 | 6 | 1 | 0 | Distributed concurrency/race suite |
| MC-059 | High | PARTIAL | 12 | 5 | 3 | 0 | Disaster/partition/reconnect certification suite |
| MC-060 | High | PARTIAL_EXTERNAL_DEPENDENCY | 12 | 6 | 1 | 1 | Full machine-readable production acceptance evidence bundle |
| MC-061 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 8 | 8 | 2 | 2 | CI/CD release pipeline and staged rollout artifacts |
| MC-062 | High | PARTIAL_EXTERNAL_DEPENDENCY | 8 | 7 | 3 | 2 | Vulnerability/SBOM/patch/EOL program artifacts |
| MC-063 | Critical | PARTIAL | 12 | 5 | 3 | 0 | Backup/restore/migration/reconstruction runbook |
| MC-064 | High | PARTIAL | 13 | 5 | 2 | 0 | Complete day-0/day-1/day-2 operational runbooks |
| MC-065 | High | PARTIAL | 11 | 5 | 4 | 0 | Incident response/on-call runbook |
| MC-066 | Medium | PARTIAL | 9 | 8 | 3 | 0 | Recurring review automation/evidence |
| MC-067 | Medium | PARTIAL | 13 | 6 | 1 | 0 | Exception/waiver/technical-debt register |
| MC-068 | Critical | PARTIAL_EXTERNAL_DEPENDENCY | 11 | 6 | 2 | 1 | Formal production exit gate artifact |
| MC-069 | High | PARTIAL_EXTERNAL_DEPENDENCY | 11 | 7 | 1 | 1 | Cross-lattice inventory service |
| MC-070 | High | PARTIAL | 10 | 9 | 1 | 0 | Audit query/retention/export service |
| MC-071 | Medium | PARTIAL | 9 | 6 | 5 | 0 | Repository license/notice metadata |
