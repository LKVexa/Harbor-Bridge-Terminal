> **v4.3.0 status:** all 35 components below are now implemented to the extent this environment allows. Per-control state: `evidence/CHECKLIST_STATUS.md`. Remaining blockers are external inputs (see CHANGELOG 4.3.0 → Release verdict).

# INV-14 Remaining Missing Components — after v4.2.0 hardening

This inventory lists components that are still absent from the submitted archive after the implementation repair. Items are ordered by production risk, not by the numerical checklist order.

## P0 — release-blocking dependencies and interface artifacts

1. **Pinned `pk_core` runtime/dependency package** — the archive imports `pk_core` but contains no dependency manifest, lock, vendored runtime, compatibility hash, or install bootstrap. Without the exact compatible core, the 100-item assessment/gate cannot run reproducibly. *(C016, C031, C040, C084, C090, C093, C100)*
2. **Actual WASI 0.2 / `wasi:io` integration adapter** — the repository is a Python reference model only; no WIT world/interface, component binding, runtime adapter, or execution fixture proves interoperability with real WASI pollables. *(C021-C030, C031, C082-C084)*
3. **Versioned WIT/schema definitions for `PK_POLL/1`, `PK_POLLABLE/1`, `PK_POLL_ERROR/1`, and `PK_POLL_METRICS/1`** — schemas are named in code/docs but no canonical machine-readable contract artifact is present. *(C021, C022, C026, C029)*
4. **INV-15 migration bridge/shim** — the migration target is named, but there is no converter/adaptor, dual-stack compatibility layer, migration state machine, or proof that a live INV-14 consumer can transition to INV-15 safely. *(C016, C027, C038, C095, C099)*
## P1 — security, concurrency, lifecycle, and operability

5. **Cancellation contract** — `poll()` supports readiness/timeout but no caller-driven cancellation token, cancellation error code, or cancellation race tests. *(C025)*
6. **Backpressure/admission policy beyond a set-size ceiling** — there is no tenant quota, concurrent-poll ceiling, queueing policy, fairness scheduler, or overload/load-shedding mechanism. *(C017, C025, C054, C067)*
7. **Cross-tenant identity/capability integration** — ownership is a string equality check; no authenticated component identity, capability token, tenant namespace, or runtime attestation binds `owner` to a trusted principal. *(C023, C024, C042, C044, C046)*
8. **Tamper-evident audit event sink** — structured exceptions/counters exist, but security-sensitive refusals and deprecation use are not written to a chained/signed audit ledger. *(C049, C073, C079)*
9. **Telemetry exporter** — `metrics_snapshot()` is local only; no OpenTelemetry/Prometheus adapter, stable metric labels, sampling policy, or remote export integration exists. *(C071-C080)*
10. **Structured logging implementation** — no stable tenant/workload/component/operation IDs, redaction policy, or log schema is implemented. *(C073, C075, C079)*
11. **Trace-context propagation** — no trace/span context is accepted, returned, or bridged across the poll boundary. *(C074)*
12. **Emergency disable / policy enforcement hook** — documentation says the component may be removed from a registry, but there is no runtime policy switch that rejects new legacy polls while preserving safe drain/rollback behavior. *(C019, C048, C059, C092)*
13. **Per-component migration status registry** — a counter measures local use, but no inventory identifies which deployed components still depend on INV-14, their owner, age, exception, deadline, or migration stage. *(C091, C094, C099)*
14. **Lifecycle/state model artifact** — no explicit state machine covers enabled, deprecated, draining, disabled, migrating, failed, or quarantined states and legal transitions. *(C014, C015, C057, C059)*
15. **Restart/replay semantics** — readiness and counters are in-memory only; no definition or test exists for process restart, checkpointing, reconstructed pollables, or replay after crash. *(C057, C095)*
16. **Clock/tick authority specification** — v4.2.0 defines a Python default of 1 ms/tick, but no external configuration/schema establishes how `timeout_ticks` maps to runtime/WASI time across platforms. *(C011-C013, C022, C031)*
17. **Owner/escalation metadata** — no accountable team, on-call route, escalation target, or support boundary is stored in the repository. *(C009, C091, C097)*
18. **Architecture Decision Record (ADR)** — rationale for retaining the legacy model, limits, migration target, and retirement criteria is not captured in an approved ADR artifact. *(C010, C098, C099)*
19. **Compatibility matrix** — no tested matrix covers Python/core versions, WASI runtimes, CPU architectures, `wasi:io` versions, or INV-13/INV-15/GAP-15 combinations. *(C027, C084, C093)*

## P2 — verification, performance, supply chain, and governance

20. **Real adjacent-layer integration tests** — no executable tests against INV-13 system interface, INV-15 async ABI, or GAP-15 runtime certification are included. *(C030, C083, C089)*
21. **WIT/protocol contract tests** — no golden fixtures or negative conformance suite validates serialized interface/error/metrics schemas. *(C029, C082)*
22. **Fuzz harness** — no fuzzing of poll-set shape, identities, timeout boundaries, schema decoding, or foreign-owner inputs. *(C050, C085)*
23. **Dedicated concurrency model checking/race tooling** — thread tests exist, but there is no stress/TSAN-equivalent/model-checking regime for interleavings, clear-vs-signal races, cancellation, or multiple poll sets. *(C086)*
24. **Benchmark suite and approved thresholds** — no p50/p95/p99/worst-case latency, throughput, CPU, memory, wake fan-out, startup, power, or thermal baselines. *(C061-C070, C088)*
25. **Soak/burst/fleet-scale test harness** — no long-duration, overload, recovery, or high-cardinality deployment test exists. *(C063, C088)*
26. **Fault-injection harness** — no systematic process kill, runtime stall, clock anomaly, dependency loss, partition, reconnect, or control-plane degradation tests. *(C060, C089)*
27. **CI release pipeline** — no workflow enforces compile, standalone tests, optimized tests, framework conformance, integration tests, artifact hashes, or release gates on every change. *(C070, C090, C100)*
28. **Dependency/SBOM/provenance artifacts** — no SBOM, dependency lock, signed provenance/attestation, build manifest, or vulnerability scan policy is present. *(C045, C094)*
29. **Artifact signing and verification hook** — no release signature, trusted-key policy, or signature verification command accompanies the package. *(C045)*
30. **Configuration schema/provenance** — safety limits are constructor parameters only; no declarative config schema, environment/site overlays, author/version/activation metadata, or atomic config update mechanism exists. *(C033-C038)*
31. **Secret-handling/redaction policy** — the component currently needs no secrets, but no explicit policy/test prevents future diagnostic fields from leaking credentials or tenant-sensitive data. *(C039, C047, C075)*
32. **Dashboard and alert definitions** — no operator dashboard or alert rules distinguish timeout load, cross-owner attacks, invalid requests, migration regressions, software defects, or saturation. *(C080)*
33. **Incident/runbook package** — README contains a short day-0/day-1/day-2 outline but no executable incident, containment, recovery, rollback, paging, or escalation runbook. *(C092, C096, C097)*
34. **Exception/waiver registry** — no machine-readable list tracks accepted legacy users, waiver owners, expiry dates, and retirement commitments. *(C099)*
35. **Formal end-of-life policy** — deprecation is signaled, but there is no version/date-based EOL SLA, removal milestone, support window, or forced migration criterion. *(C094, C099)*

## Component boundary note

Several checklist topics (encryption at rest, backup, network partition, provider failover) are largely *not applicable to this in-memory primitive itself*. They become applicable at the runtime, telemetry, evidence-ledger, or integration layers. The production package should explicitly mark those items N/A with objective boundary evidence rather than silently claiming implementation inside INV-14.
