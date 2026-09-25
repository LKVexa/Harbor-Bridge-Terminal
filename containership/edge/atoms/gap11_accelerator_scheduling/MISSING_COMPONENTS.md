# GAP-11 — Missing Components After v4.2.0 Audit

This list records components that are **absent from the supplied package or not implemented by its in-memory reference allocator**. Some belong in adjacent GAP subsystems but still require a concrete integration contract before GAP-11 can be considered production-complete.

## P0 — Required before production ownership

1. **Durable lease-state store** — transactional persistence for allocations, releases, scrub state, quarantine state, and tenant security epochs across process/node restarts. Maps to C032, C037, C057, C095.
2. **Distributed compare-and-swap / fencing layer** — monotonic ownership epochs or fencing tokens preventing two controllers from allocating the same physical accelerator after failover or partition. C055, C058.
3. **HA controller ownership / leader election** — explicit active-controller authority and failover behavior, integrated with fencing rather than best-effort locks. C051, C055, C058.
4. **Lease TTL, heartbeat, and orphan reconciliation** — reclaim or quarantine resources after workload/controller death without prematurely releasing live workloads. C015, C025, C052, C057.
5. **Idempotency and replay-protection store** — request IDs and durable deduplication for allocate/release/scrub calls. C025, C049, C058.
6. **Real hardware inventory adapter** — integration with GAP-02 and vendor APIs (for example NVIDIA, AMD, Intel, NPU, FPGA providers) for device identity, memory, features, health, and hot-plug changes. C021, C030, C083.
7. **Partition topology/lifecycle adapter** — representation of mutually compatible partition profiles and, where GAP-11 owns it, creation/destruction/drain operations for MIG/SR-IOV/vendor slices. The current `PartitionSpec` assumes declared simultaneous slices and does not model alternative profile layouts. C011, C015, C021.
8. **Vendor-specific scrub/reset executor** — actual VRAM/HBM/state zeroization or reset with timeout, retry policy, health verification, and evidence. The current `scrub()` is only a state-machine reference. C046, C048, C053, C059.
9. **Device attestation binding** — cryptographic binding between discovered accelerator identity/capabilities, node identity, driver/firmware state, and GAP-06 attestation evidence. C044, C045.
10. **Authenticated service boundary** — mTLS/workload identity or equivalent authentication for inventory, allocate, release, and scrub APIs. C023, C044, C047.
11. **Authorization/capability policy** — tenant/workload permissions for device classes, partitions, administrative scrub, quarantine overrides, and sensitive inventory. C024, C042, C043.
12. **Versioned wire schemas** — concrete JSON/Protobuf/WIT/RPC schema files for `PK_ACCELERATOR_INVENTORY/1`, `PK_ACCELERATOR_ALLOCATION/1`, `PK_ACCELERATOR_RELEASE/1`, and `PK_SCRUB/1`, including compatibility rules. C022, C026, C027, C082.
13. **API transport/server** — bounded request queues, deadlines, cancellation, backpressure, connection limits, and structured failure mapping. C025, C028, C054, C067.
14. **Admission quotas and fairness** — per-tenant/project caps, reservation classes, starvation prevention, queue discipline, and capacity ceilings. C017, C054, C069.
15. **Workload lifecycle integration** — authoritative hooks for workload start, exit, crash, eviction, and restart so leases cannot leak or be released too early. C030, C057.
16. **Split-brain and stale-controller tests** — multi-controller fault tests proving fencing under delayed messages, network partitions, failover, and replay. C058, C060, C086, C089.

## P1 — Required for operational maturity

17. **Multi-device topology scheduler** — NUMA/PCIe/NVLink/fabric locality, gang allocation, atomic multi-device reservation, and rollback. C017, C065, C066.
18. **Fragmentation-aware partition placement** — profile compatibility and placement minimizing unusable residual accelerator capacity.
19. **Power/thermal admission adapter** — live constraint integration with GAP-10 so thermally unavailable devices cannot be leased. C019, C030, C068.
20. **Health/RAS integration** — ECC, Xid/device faults, link degradation, reset storms, predictive failure, and automatic quarantine/drain. C051, C052, C059.
21. **Hot-plug and inventory reconciliation loop** — safely handle device disappearance, replacement, renumbering, and changed capabilities while leases exist. C051, C057.
22. **Preemption/reservation policy** — optional but needed if priority classes or reserved accelerators are part of the deployment model. C017, C019.
23. **Constraint policy engine** — precedence for security, residency, workload class, generation, feature, cost, power, and SLO constraints, with deterministic decision reasons. C019, C076, C077.
24. **Tamper-evident audit ledger** — signed/chained events for allocation, release, scrub, quarantine, policy decisions, overrides, and controller leadership changes. C049, C090.
25. **Metrics exporter** — allocation latency, refusal reason, active leases, saturation, scrub latency/failure, queue depth, fragmentation, and reconciliation state. C061-C070, C072.
26. **Structured logs and trace propagation** — stable operation/request/lease/device IDs, trace context, privacy controls, and correlation to release lineage. C073-C079.
27. **Health/readiness/debug endpoints** — version, configuration digest, dependency health, controller role, reconciliation lag, and safe explain output. C071, C077.
28. **Dashboards and alerts** — separate capacity exhaustion, policy rejection, scrub failure, device health failure, attack indicators, and software defects. C080.
29. **Declarative configuration schema** — validation, secure defaults, site/environment overlays, provenance, atomic activation, and rollback. C033-C038.
30. **Secrets/KMS integration** — certificate/key retrieval, rotation, redaction, and fail-closed behavior when key or identity services are unavailable. C039, C047, C048.
31. **Usage accounting/export** — durable device/partition occupancy records suitable for capacity analytics, chargeback/showback, and audit without trusting ephemeral process memory.
32. **Operator quarantine/drain controls** — explicit freeze, drain, unquarantine, force-reconcile, and maintenance workflows with authorization and audit. C059, C092, C097.

## P2 — Certification, release, and governance gaps

33. **Public schema fixtures and contract tests** — golden requests/responses/error cases for every wire interface. C029, C082.
34. **Adjacent-layer integration tests** — GAP-02, GAP-06, GAP-09, GAP-10, workload placement, runtime, and workload lifecycle. C030, C083.
35. **Fuzzing/property tests** — request parsing, schema handling, state-machine sequences, lease replay, and malformed inventory. C085.
36. **Broader concurrency tests** — release-vs-scrub, allocate-vs-inventory-change, controller failover, multi-device transactions, and long-running race/soak tests. C086, C088.
37. **Security adversarial suite** — spoofed identity, capability escalation, stale lease replay, denial of service, side-channel assumptions, audit tampering, and malicious device metadata. C041, C050, C087.
38. **Fault-injection/disaster tests** — store loss, partial write, process kill, node loss, network partition, time skew, dependency outage, and reconnect. C060, C089.
39. **Performance/scale benchmarks** — p50/p95/p99/worst-case latency, burst/overload, fleet size, queue depth, memory/CPU overhead, and regression gates. C061-C070, C088.
40. **Compatibility matrix** — supported Python/pk_core versions, API schema versions, architectures, drivers, firmware, hypervisors, accelerator families, and providers. C084, C093.
41. **Packaging metadata and dependency pinning** — `pyproject.toml`/build metadata, explicit `pk_core` compatibility range, reproducible wheel/sdist or repository packaging, and installation tests. C031, C040.
42. **CI release gate** — compile, unit, contract, integration, security, fuzz, benchmark, provenance, and artifact verification before release. C070, C090, C100.
43. **SBOM, signing, and provenance** — signed release artifacts, dependency inventory, source/build attestations, and verification policy. C045, C094.
44. **Threat model document** — attacker classes, trust boundaries, residual-data threat analysis, stale-controller threats, side-channel assumptions, and mitigations. C041, C050.
45. **Architecture Decision Record (ADR)** — approved technology/state-store/API/fencing choices and explicit tradeoffs. C010.
46. **Named accountable owner and escalation path** — owner, on-call/escalation route, incident severity policy, and support commitment are absent from the supplied archive. C009, C091, C097.
47. **Runbooks** — bootstrap, rollout, rollback, emergency disable, store recovery, orphan reconciliation, failed scrub, device replacement, and incident containment. C092, C095-C097.
48. **Exception/waiver/deprecation register** — owners, expiry dates, rationale, migration plan, and review cadence. C098, C099.
49. **Source-series `MASTER.md` artifact** — the prior README said this file was bundled, but it is absent from the supplied archive. Restore the authoritative master prompt/workflow source or remove all downstream assumptions that require it.
50. **Formal production-exit evidence bundle** — machine-readable acceptance results covering architecture, security, resilience, performance, observability, rollback, ownership, and all unresolved exceptions. C090, C100.

## Scope note

Items 6, 9, 19, 25, and related integrations may be implemented primarily by neighboring GAP subsystems. GAP-11 still needs explicit adapters, version compatibility, failure semantics, and test evidence for those dependencies. The current package is a hardened local state-machine reference, not a replacement for those system components.


---

## Status after v4.3.0 (generated from evidence/CHECKLIST_STATUS.json)

Columns: evidenced / partial / blocked / open, out of 20 checks per component. No component gate is MET because check .20 (design approval + independent security review) is blocked on a human for all 50.

| Component | Title | Disposition | x / ~ / ! / blank |
|---|---|---|---|
| GAP11-P0-01 | Durable lease-state store | IMPLEMENTED | 16 / 3 / 1 / 0 |
| GAP11-P0-02 | Distributed compare-and-swap / fencing layer | IMPLEMENTED | 15 / 3 / 1 / 1 |
| GAP11-P0-03 | HA controller ownership / leader election | IMPLEMENTED | 16 / 3 / 1 / 0 |
| GAP11-P0-04 | Lease TTL, heartbeat, and orphan reconciliation | IMPLEMENTED | 16 / 3 / 1 / 0 |
| GAP11-P0-05 | Idempotency and replay-protection store | IMPLEMENTED | 16 / 3 / 1 / 0 |
| GAP11-P0-06 | Real hardware inventory adapter | SIMULATED | 14 / 3 / 3 / 0 |
| GAP11-P0-07 | Partition topology/lifecycle adapter | SIMULATED | 12 / 3 / 3 / 2 |
| GAP11-P0-08 | Vendor-specific scrub/reset executor | SIMULATED | 14 / 3 / 3 / 0 |
| GAP11-P0-09 | Device attestation binding | SIMULATED | 14 / 3 / 1 / 2 |
| GAP11-P0-10 | Authenticated service boundary | SIMULATED | 16 / 3 / 1 / 0 |
| GAP11-P0-11 | Authorization/capability policy | IMPLEMENTED | 15 / 3 / 1 / 1 |
| GAP11-P0-12 | Versioned wire schemas | IMPLEMENTED | 16 / 3 / 1 / 0 |
| GAP11-P0-13 | API transport/server | IMPLEMENTED | 16 / 3 / 1 / 0 |
| GAP11-P0-14 | Admission quotas and fairness | IMPLEMENTED | 17 / 2 / 1 / 0 |
| GAP11-P0-15 | Workload lifecycle integration | IMPLEMENTED | 16 / 3 / 1 / 0 |
| GAP11-P0-16 | Split-brain and stale-controller tests | IMPLEMENTED | 15 / 4 / 1 / 0 |
| GAP11-P1-17 | Multi-device topology scheduler | IMPLEMENTED | 14 / 2 / 1 / 3 |
| GAP11-P1-18 | Fragmentation-aware partition placement | IMPLEMENTED | 15 / 3 / 1 / 1 |
| GAP11-P1-19 | Power/thermal admission adapter | SIMULATED | 13 / 3 / 3 / 1 |
| GAP11-P1-20 | Health/RAS integration | SIMULATED | 13 / 3 / 3 / 1 |
| GAP11-P1-21 | Hot-plug and inventory reconciliation loop | IMPLEMENTED | 15 / 4 / 1 / 0 |
| GAP11-P1-22 | Preemption/reservation policy | IMPLEMENTED | 15 / 3 / 1 / 1 |
| GAP11-P1-23 | Constraint policy engine | IMPLEMENTED | 15 / 2 / 1 / 2 |
| GAP11-P1-24 | Tamper-evident audit ledger | IMPLEMENTED | 14 / 5 / 1 / 0 |
| GAP11-P1-25 | Metrics exporter | IMPLEMENTED | 10 / 6 / 1 / 3 |
| GAP11-P1-26 | Structured logs and trace propagation | IMPLEMENTED | 13 / 6 / 1 / 0 |
| GAP11-P1-27 | Health/readiness/debug endpoints | IMPLEMENTED | 12 / 6 / 1 / 1 |
| GAP11-P1-28 | Dashboards and alerts | DOCUMENTED | 12 / 6 / 1 / 1 |
| GAP11-P1-29 | Declarative configuration schema | IMPLEMENTED | 17 / 2 / 1 / 0 |
| GAP11-P1-30 | Secrets/KMS integration | SIMULATED | 10 / 4 / 1 / 5 |
| GAP11-P1-31 | Usage accounting/export | IMPLEMENTED | 12 / 6 / 1 / 1 |
| GAP11-P1-32 | Operator quarantine/drain controls | IMPLEMENTED | 8 / 3 / 1 / 8 |
| GAP11-P2-33 | Public schema fixtures and contract tests | IMPLEMENTED | 8 / 6 / 1 / 5 |
| GAP11-P2-34 | Adjacent-layer integration tests | BLOCKED | 2 / 3 / 15 / 0 |
| GAP11-P2-35 | Fuzzing/property tests | IMPLEMENTED | 10 / 6 / 1 / 3 |
| GAP11-P2-36 | Broader concurrency tests | IMPLEMENTED | 12 / 6 / 1 / 1 |
| GAP11-P2-37 | Security adversarial suite | IMPLEMENTED | 9 / 6 / 1 / 4 |
| GAP11-P2-38 | Fault-injection/disaster tests | IMPLEMENTED | 13 / 6 / 1 / 0 |
| GAP11-P2-39 | Performance/scale benchmarks | IMPLEMENTED | 7 / 6 / 1 / 6 |
| GAP11-P2-40 | Compatibility matrix | DOCUMENTED | 6 / 7 / 4 / 3 |
| GAP11-P2-41 | Packaging metadata and dependency pinning | IMPLEMENTED | 6 / 7 / 4 / 3 |
| GAP11-P2-42 | CI release gate | IMPLEMENTED | 6 / 7 / 4 / 3 |
| GAP11-P2-43 | SBOM, signing, and provenance | DOCUMENTED | 6 / 7 / 4 / 3 |
| GAP11-P2-44 | Threat model document | DOCUMENTED | 7 / 8 / 3 / 2 |
| GAP11-P2-45 | Architecture Decision Record (ADR) | DOCUMENTED | 7 / 7 / 3 / 3 |
| GAP11-P2-46 | Named accountable owner and escalation path | BLOCKED | 3 / 5 / 9 / 3 |
| GAP11-P2-47 | Runbooks | DOCUMENTED | 5 / 8 / 3 / 4 |
| GAP11-P2-48 | Exception/waiver/deprecation register | DOCUMENTED | 6 / 8 / 3 / 3 |
| GAP11-P2-49 | Source-series MASTER.md artifact | BLOCKED | 6 / 4 / 9 / 1 |
| GAP11-P2-50 | Formal production-exit evidence bundle | IMPLEMENTED | 10 / 5 / 3 / 2 |
