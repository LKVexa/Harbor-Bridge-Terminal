# INV-06 Traditional IaC — Missing Components

Version-audit baseline: **4.2.0**; statuses updated by the **4.3.0** execution pass (`governance/READINESS.json` is authoritative). These are production components or evidence artifacts not present in the supplied archive after the hardening pass. Package-local reference behavior is not a substitute for these estate-level capabilities.

## Source, architecture, and governance

1. **MC-001** `[blocked]` **— Authoritative `MASTER.md` source package** — Restore the referenced per-item master prompts/workflows or remove the dependency from the parent series manifest. (`INV-06-C020`, package provenance)
2. **MC-002** `[owner-required]` **— Accountable owner and escalation registry** — Named service owner, backup owner, escalation chain, on-call destination, and ownership-transfer procedure. (`C009`, `C097`)
3. **MC-003** `[draft]` **— Approved Architecture Decision Record** — Record Terraform/HCL/state/resource-graph/plan-apply technology decisions, alternatives, tradeoffs, and approval history. (`C010`)
4. **MC-004** `[draft]` **— SHALL-level requirements specification** — A normative requirements document separate from the checklist prose. (`C011`–`C019`)
5. **MC-005** `[implemented]` **— Requirements traceability matrix** — Requirement → design → code → test → evidence → release-gate mapping. (`C020`)
6. **MC-006** `[draft]` **— Deployment/support matrix** — Supported cloud, datacenter, near-edge, far-edge, OS/CPU/runtime/provider combinations and exclusions. (`C012`, `C084`, `C093`)
7. **MC-007** `[draft]` **— Compatibility/version policy** — Backward/forward compatibility, deprecation, schema negotiation, migration windows, and peer-version behavior. (`C016`, `C027`, `C093`)
8. **MC-008** `[draft]` **— Capacity/quota/fairness specification** — State size, resource count, plan size, concurrent operations, tenant quotas, queue limits, and fairness policy. (`C017`, `C028`, `C067`)
9. **MC-009** `[implemented]` **— Constraint-precedence policy** — Explicit ordering for security, residency, consistency, SLO, cost, availability, and operator overrides. (`C019`)

## Durable state, execution, and integration

10. **MC-010** `[implemented]` **— Durable remote-state backend** — Transactional persistent state with durability guarantees, integrity metadata, revision history, and recovery semantics. (`C032`, `C037`, `C057`, `C095`)
11. **MC-011** `[implemented]` **— Distributed lock/lease/fencing backend** — Cross-process/node/site mutual exclusion, lease expiry, fencing tokens, stale-writer prevention, and split-brain protection. (`C058`)
12. **MC-012** `[implemented]` **— Crash-safe transaction journal** — Write-ahead/intent log or equivalent mechanism for restart, resume, replay, and interrupted-apply recovery. (`C037`, `C057`)
13. **MC-013** `[implemented]` **— State rollback engine** — Operator and automated rollback with preconditions, reversible/irreversible operation classification, and rollback evidence. (`C038`, `C092`)
14. **MC-014** `[implemented]` **— Backup/restore/migration tooling** — Scheduled backup, restore validation, format migration, reconstruction, and disaster-recovery procedures. (`C095`)
15. **MC-015** `[implemented]` **— Terraform execution adapter** — Approved/pinned Terraform or compatible engine runner with deterministic invocation and output capture. (`C031`)
16. **MC-016** `[implemented]` **— HCL/configuration parser and compiler** — Pinned parser, syntax/semantic validation, secure defaults, and configuration activation boundary. (`C031`, `C033`, `C034`)
17. **MC-017** `[implemented]` **— Resource-graph engine** — Dependency graph construction, cycle handling, ordering, replacement semantics, and graph-level validation. (`C031`)
18. **MC-018** `[implemented]` **— Provider plugin lifecycle manager** — Provider allowlist, version pinning, acquisition, checksum/signature verification, isolation, and upgrade policy. (`C031`, `C045`)
19. **MC-019** `[external]` **— Cloud-provider adapters** — Concrete authenticated adapters and conformance fixtures for supported public/private clouds. (`C012`, `C030`, `C083`)
20. **MC-020** `[external]` **— Datacenter/bare-metal adapters** — Concrete integrations for supported virtualization, network, storage, and bare-metal control planes. (`C012`, `C030`, `C083`)
21. **MC-021** `[implemented]` **— Edge/disconnected execution adapter** — Offline plan policy, local cache, reconnect reconciliation, conflict handling, and bounded stale-operation semantics. (`C018`, `C056`, `C089`)
22. **MC-022** `[implemented]` **— GAP-13 policy-engine integration** — Pre-apply policy evaluation contract, denial reason propagation, policy-version binding, and fail-closed behavior. (`C003`, `C019`, `C030`)
23. **MC-023** `[implemented]` **— INV-01/INV-07/INV-08 integration adapters** — Inventory ingestion, GitOps transition, and dynamic-infrastructure handoff contracts with automated tests. (`C003`, `C030`, `C083`)
24. **MC-024** `[implemented]` **— Site/environment configuration overlay system** — Immutable artifact + mutable overlay model with schema validation, precedence, and site/environment specialization. (`C032`–`C035`)
25. **MC-025** `[implemented]` **— Configuration provenance ledger** — Version, author/actor, source revision, approval, activation time, environment, and rollback link. (`C036`)
26. **MC-026** `[implemented]` **— Timeout/cancellation/retry/idempotency layer** — Operation deadlines, cooperative cancellation, idempotency keys, bounded retry, exponential backoff/jitter, and backpressure. (`C025`, `C053`)
27. **MC-027** `[implemented]` **— Admission/load-shedding/circuit-breaker controls** — Protect state/provider/control-plane dependencies from overload and cascading failure. (`C054`)
28. **MC-028** `[implemented]` **— Degraded-dependency mode** — Explicit behavior when noncritical peers/providers/telemetry are unavailable. (`C056`)
29. **MC-029** `[implemented]` **— Failover and residency-aware continuity controller** — Failover rules that preserve consistency, isolation, data residency, and ownership. (`C055`)
30. **MC-030** `[implemented]` **— Quarantine/freeze/emergency-disable controller** — Stop unsafe applies while retaining inspectability and recovery paths. (`C059`, `C092`)
31. **MC-031** `[implemented]` **— Health/stall watchdog** — Liveness/readiness/stall thresholds, stuck-operation detection, dependency status, and operator actions. (`C052`, `C071`)

## Security, trust, and isolation

32. **MC-032** `[draft]` **— Formal threat model** — Tenant, workload, provider, parser, plan, state, supply-chain, replay, spoofing, exhaustion, escape, and control-plane abuse analysis. (`C041`, `C050`, `C087`)
33. **MC-033** `[implemented]` **— Authentication integration** — Workload/node/operator/provider/service identity verification at every boundary. (`C023`, `C044`)
34. **MC-034** `[implemented]` **— Authorization/capability engine** — Least-privilege roles/capabilities for plan, apply, protect/unprotect, state read, import/export, and emergency operations. (`C024`, `C042`)
35. **MC-035** `[implemented]` **— Ambient-authority sandbox** — Filesystem, network, device, process, kernel, environment, and secret capability minimization for IaC execution. (`C043`)
36. **MC-036** `[implemented]` **— Artifact signature/provenance verifier** — Signatures, digests, SBOM/provenance attestations, approved-version policy, and revocation handling for providers/policies/binaries. (`C045`)
37. **MC-037** `[implemented]` **— Tenant/workload isolation layer** — Namespace/state separation, execution isolation, network boundaries, quotas, and cross-tenant data-flow enforcement. (`C046`)
38. **MC-038** `[external]` **— Encryption and KMS integration** — TLS/mTLS in transit, encryption at rest, managed keys, envelope encryption, rotation, recovery, and key-access audit. (`C047`)
39. **MC-039** `[implemented]` **— Security-service outage policy** — Fail-closed/degraded behavior for identity, attestation, policy, key, certificate, and time-service outages. (`C048`)
40. **MC-040** `[implemented]` **— Durable signed audit service** — Append-only external audit sink with retention, access control, trusted timestamps, signatures, export, and verification. The current chain is memory-only. (`C049`)
41. **MC-041** `[implemented]` **— Secret/redaction guard** — Prevent credentials and sensitive values from plans, state diagnostics, logs, traces, fixtures, and high-cardinality debugging. (`C039`, `C075`)
42. **MC-042** `[implemented]` **— Adversarial security test suite** — Privilege escalation, injection, replay, spoofing, provider compromise, parser abuse, escape, side-channel, and resource-exhaustion tests. (`C050`, `C087`)

## Observability, explainability, and performance

43. **MC-043** `[implemented]` **— Health/readiness/status interface** — Version, config revision, dependency health, capability set, state backend status, lock status, and readiness reason. (`C071`)
44. **MC-044** `[implemented]` **— Metrics exporter** — Prometheus/OpenTelemetry or equivalent export for rate, errors, latency, saturation, backlog, lock contention, provider latency, resource use, and plan/apply outcomes. (`C072`)
45. **MC-045** `[implemented]` **— Structured logging pipeline** — Stable node/tenant/workload/component/operation identifiers, redaction, severity, schema version, and centralized export. (`C073`, `C075`)
46. **MC-046** `[implemented]` **— Distributed tracing integration** — Trace-context propagation through policy, state, provider, inventory, GitOps, and dynamic-infrastructure boundaries. (`C074`)
47. **MC-047** `[implemented]` **— Decision/explainability view** — Human-readable reason chain linking plan decisions to state, desired config, policy, topology, constraints, and provider results. (`C076`, `C077`)
48. **MC-048** `[implemented]` **— Release-lineage/live-graph correlation** — Correlate IaC events with application release IDs, artifact versions, state revisions, and current infrastructure graph. (`C078`)
49. **MC-049** `[draft]` **— Telemetry governance policy** — Retention, sampling, privacy, tenancy, export, access, deletion, and incident-preservation rules. (`C079`)
50. **MC-050** `[draft]` **— Dashboards and alert rules** — Differentiate normal load, saturation, dependency failure, policy rejection, attack, drift, stale plans, and software defects. (`C080`)
51. **MC-051** `[implemented]` **— Performance baseline/benchmark harness** — Reproducible latency, throughput, startup, CPU, memory, storage, network, plan-size, and provider-call baselines. (`C061`–`C063`, `C088`)
52. **MC-052** `[implemented]` **— Tail-latency/SLO thresholds** — p50/p95/p99/worst-case targets and release-blocking thresholds. (`C062`, `C070`)
53. **MC-053** `[implemented]` **— Tenant/workload overhead and capacity model** — Per-tenant cost, saturation indicators, scale triggers, queue/fan-out bounds, and state growth forecasts. (`C064`, `C067`, `C069`)
54. **MC-054** `[implemented]` **— Serialization/copy/network efficiency audit** — Quantify and eliminate avoidable copies, serial bottlenecks, extra network hops, duplicate images/state, and unsafe optimization candidates. (`C065`, `C066`)
55. **MC-055** `[external]` **— Edge power/thermal benchmark** — Power draw, thermal behavior, throttling impact, and energy-per-operation for constrained deployments. (`C068`)

## Testing, certification, release, and operations

56. **MC-056** `[implemented]` **— Public-interface contract test suite** — Tests for every plan/state/drift/provider/policy/identity boundary and schema-version behavior. (`C082`)
57. **MC-057** `[external]` **— Adjacent-layer integration suite** — Automated integration tests covering every supported neighboring component and execution tier. (`C030`, `C083`)
58. **MC-058** `[external]` **— Compatibility matrix test farm** — CPU/OS/runtime/hypervisor/provider/protocol/version combinations with retained results. (`C084`, `C093`)
59. **MC-059** `[implemented]` **— Fuzz/property-based test suite** — State/plan schemas, parsers, provider responses, corrupt snapshots, boundary values, and hostile untrusted inputs. (`C085`)
60. **MC-060** `[implemented]` **— Fault-injection and partition test suite** — Process/node/site/provider/control-plane failures, partitions, reconnects, lock loss, stale leases, and replay/recovery. (`C060`, `C089`)
61. **MC-061** `[implemented]` **— Soak/burst/fleet-scale test suite** — Long-duration stability, burst overload, large graphs, large state, high concurrency, and recovery at fleet scale. (`C063`, `C088`)
62. **MC-062** `[implemented]` **— Machine-readable acceptance evidence artifact** — Signed release evidence proving required tests/gates passed with exact artifact/dependency identities. (`C090`, `C100`)
63. **MC-063** `[implemented]` **— Canary/staged rollout automation** — Progressive exposure, health gates, halt criteria, rollback triggers, and emergency disable. (`C092`)
64. **MC-064** `[implemented]` **— Supported-version matrix and dependency pins** — Exact `pk_core`, Python, Terraform/provider, schema, and adjacent-component compatibility; the archive currently has no `pyproject.toml`/lock manifest. (`C031`, `C093`)
65. **MC-065** `[draft]` **— Vulnerability/patch/EOL policy** — Patch SLAs, CVE triage, emergency fixes, dependency refresh, supported-life windows, and EOL process. (`C094`)
66. **MC-066** `[draft]` **— Incident response runbook** — Severity model, paging, escalation, containment, evidence preservation, recovery, communication, and post-incident review. (`C097`)
67. **MC-067** `[draft]` **— Recurring review program** — Scheduled access, policy, dependency, configuration, threat-model, and architecture reviews with recorded outcomes. (`C098`)
68. **MC-068** `[draft]` **— Exception/waiver/technical-debt ledger** — Owner, rationale, compensating control, risk, approval, expiry, and closure evidence. (`C099`)
69. **MC-069** `[implemented]` **— Formal production exit gate** — A deterministic gate that aggregates architecture, security, resilience, performance, testing, rollback, ownership, and evidence readiness. (`C100`)
70. **MC-070** `[draft]` **— Production support/SLO commitment document** — Availability/latency/durability objectives, error budgets, support hours, response targets, and escalation commitments. (`C091`)
71. **MC-071** `[implemented]` **— Packaging metadata and reproducible build definition** — `pyproject.toml` or equivalent, exact dependency declarations, build backend, artifact metadata, hashes, and reproducible build instructions. (`C031`, `C040`, `C093`)
72. **MC-072** `[owner-required]` **— License/NOTICE provenance package** — Explicit source/binary licensing and third-party notice inventory for redistribution and supply-chain review. (release governance)
