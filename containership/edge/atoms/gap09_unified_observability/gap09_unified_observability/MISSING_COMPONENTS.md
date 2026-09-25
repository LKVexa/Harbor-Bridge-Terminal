# GAP-09 Missing Components - after v5.0.0 hardening

This is the gap list remaining after the code-level audit. The current package is a hardened reference latest-value signal store plus `pk_core` integration glue; it is not yet the full subsystem described by the checklist function: *unify logs, metrics, traces, profiling and causal context across Wasm, microVM, host and network boundaries*.

## P0 - required before production trust / release certification

1. **Real GAP-06 attestation adapter** — validate hardware/software attestation evidence, freshness, revocation and device identity instead of the test fixture.
2. **Real GAP-07 signature/provenance adapter** — asymmetric signature verification, approved key policy, signer provenance and algorithm agility.
3. **Durable replay protection** — persist accepted submission IDs/nonces across restart and define replay-window/eviction semantics.
4. **Key/certificate lifecycle** — rotation, revocation, expiry, compromise response and key-ID compatibility policy.
5. **mTLS/authenticated transport** — secure the network hop carrying submission/query traffic; transport is not implemented here.
6. **Secret/KMS and at-rest encryption integration** — managed secret retrieval, key separation, rotation and encryption for any persisted buffers/audit/configuration state without leaking credentials into diagnostics.
7. **Central authorization-policy integration** — derive tenant/environment/site/workload capability scopes from an authoritative policy service, not static test mappings.
8. **Authenticated query-principal binding** — `SignalStore.read()` is an in-process reference API whose `caller_tenant` argument must come from an already authenticated/authorized query gateway. Add a production query-auth adapter that cryptographically binds the caller principal to permitted tenant/environment/site/workload scopes; never accept a network client’s self-declared tenant as identity.
9. **Time authority / clock-skew policy** — trusted time source, maximum skew, reconnect handling and behavior when time confidence is lost.
10. **Canonical cross-language signing profile** — standardize canonical serialization/number formatting and signature coverage so non-Python reporters produce byte-identical signed envelopes.
11. **Durable local write-ahead buffer** — partition-safe ingestion, crash consistency, resume/replay and bounded disk usage for disconnected sites.
12. **Admission control and backpressure** — per-tenant/per-reporter rates, queue limits, load shedding, fairness and explicit retry-after semantics.
13. **Per-tenant cardinality quotas** — current global bounds prevent process exhaustion but do not prevent one tenant from consuming the entire allowance.
14. **Tamper-evident security audit ledger** — record trust failures, policy denials, configuration changes and operator actions with chain/integrity verification.
15. **Production configuration subsystem** — typed config, provenance/author/activation time, validation, atomic activation, rollback and site/environment overlays.
16. **`pk_core` dependency/package** — absent from the upload; without it the 100-item production gate cannot run.
17. **Actual production gate evidence** — machine-readable `PK_GATE_RESULTS`, evidence ledger and verification output generated in an environment containing all required sibling components.
18. **Evidence-gate hardening** — ensure `pk_core` cannot treat a declarative/default finding as implemented evidence for requirements that still lack concrete artifacts/tests; every production PASS should resolve to traceable evidence.

## P1 - required to satisfy the stated “unified observability” function

19. **Network service / RPC handlers** — the archive exposes in-process Python methods and JSON Schemas, but no authenticated submission/query/catalogue server, WIT/RPC implementation, cancellation or connection lifecycle.
20. **Multi-signal event model** — current `Sample` is numeric latest-value telemetry only; add first-class metric, log, trace/span, profile and event records.
21. **Trace-context propagation** — W3C/estate trace context across Wasm, microVM, host, network and control-plane hops.
22. **Causal-context graph** — correlate telemetry to workload instance, deployment/release lineage, node, network path and infrastructure graph.
23. **Signal catalogue service/registry** — schema now exists, but registration, ownership, units, semantic conventions and lifecycle are not implemented.
24. **Wasm instrumentation/collector adapter** — ingest/export telemetry from Wasm runtimes and component boundaries.
25. **microVM/hypervisor adapter** — guest/host correlation and microVM lifecycle context.
26. **Host/node collectors** — CPU, memory, storage, process/runtime and kernel-level telemetry sources.
27. **Network telemetry adapters** — flow, DNS, transport and policy-path observations with tenant-safe attribution.
28. **Log ingestion pipeline** — structured logs, multiline/encoding handling, severity, redaction and bounded high-cardinality fields.
29. **Metrics pipeline** — counters/gauges/histograms, temporality, aggregation/downsampling and reset semantics.
30. **Trace pipeline** — spans, links, baggage policy, sampling and late/out-of-order span assembly.
31. **Continuous profiling pipeline** — profile types, symbolization, privacy controls and resource budgets.
32. **Export/sink adapters** — one or more supported external observability backends/protocols plus retry/circuit-break semantics.
33. **Query service beyond latest value** — time ranges, pagination, filtering, aggregation, exemplars and explicit consistency semantics.
34. **Retention/sampling/privacy policy engine** — tenant-specific retention, redaction, residency, sampling and export controls.
35. **High-cardinality safety controls** — label/field budgets, overflow policy, secret/PII filtering and safe diagnostic access.
36. **Health/readiness/dependency endpoint** — expose version, config version, dependency health, capability set, saturation and degraded mode.
37. **Decision/explain records** — machine/operator-readable reasons for automated sampling, dropping, quarantine or policy decisions.

## P1 - resilience / distributed operation

38. **Persistent state backend or reconstruction contract** — the reference store is memory-only; restart loses latest values and replay state.
39. **Replication/failover model** — ownership, consistency, split-brain prevention and site failover for mutable observability state.
40. **Partition/reconnect protocol** — ordering, duplicate suppression and reconciliation after long disconnected periods.
41. **Quarantine/freeze controls** — isolate a reporter/site/tenant without stopping unrelated ingestion.
42. **Dependency circuit breakers** — prevent trust/policy/export failures from cascading through the control plane.
43. **Backup/restore/migration procedures** — for any persisted runtime/configuration/audit state introduced by production integration.

## P2 - verification, performance and operational maturity

44. **Adjacent-layer integration tests** — GAP-01, GAP-06, GAP-07, GAP-08 and PLN-05 end-to-end fixtures.
45. **Contract-schema conformance tests** — validate wire payloads against the JSON Schemas and generated/runtime codecs.
46. **Fuzz/property tests** — malformed payloads, hostile cardinality, Unicode identifiers, schema evolution and parser boundaries.
47. **Concurrency/race stress tests** — many readers/writers, replay races, conflict races and capacity-bound races.
48. **Fault-injection tests** — trust dependency loss, disk full, partition, process crash, time regression and reconnect.
49. **Soak/burst/fleet-scale tests** — sustained load, burst load, overload, scale-out/in and recovery.
50. **Performance baselines** — p50/p95/p99/worst-case ingest/query latency, throughput, startup, CPU, memory, storage and network cost.
51. **Edge power/thermal measurements** — resource/power impact on constrained nodes.
52. **Release regression gates** — block startup, density, throughput or tail-latency regressions.
53. **Compatibility matrix** — supported protocol versions, Python/runtime versions, CPU architectures, platforms and adjacent component versions.
54. **Packaging/dependency lock/SBOM** — reproducible build metadata, dependency pinning, software bill of materials and provenance output.
55. **Vulnerability/EOL policy** — patch SLAs, CVE response, supported-version lifetime and deprecation process.
56. **Owner/escalation and incident runbooks** — accountable owner, severity/paging/escalation, containment and recovery procedures.
57. **Architecture decision record** — approved technology/ownership/boundary rationale for the completed subsystem.
58. **Exception/waiver/debt registry** — owner, expiry and review cadence for deviations.
59. **Dashboards and operational views** — distinguish ordinary load, degradation, policy rejection, dependency failure, attack and software defect without making alert policy part of this component's ownership.

## Missing source artifact from the uploaded package

60. **`MASTER.md`** — the original README claimed the 100 per-item master prompt/workflow documents were included in this file, but it was absent from the archive. Restore it from the source series if it is intended to be part of the deliverable.
