# GAP-02 — Remaining / Missing Components after v4.2.0

> **Superseded by v4.3.0.** All 55 items below were executed in 4.3.0. Their live
> status (LOCALLY_VERIFIED / CONTRACT_VERIFIED / PARTIAL / BLOCKED, with blockers)
> is in `COMPONENT_STATUS.json`; evidence per item is in `evidence/GAP02-MC-NN.json`.
> The list is kept verbatim for traceability.

---


This list is intentionally limited to capabilities **not yet fully implemented in this standalone package**. Items that 4.2.0 added (basic discovery, three-state reporting, canonical bytes, typed schemas, scheduling decisions, local tests) are not repeated here.

## P0 — Required before production capability claims

1. **Vendor-grade GPU compute probes** — prove usable compute runtimes/devices (CUDA/NVML, ROCm/HSA, Level Zero/OpenCL/Metal as applicable), driver compatibility, memory, partitions/MIG, and health. Display-adapter presence must not be treated as compute capability.
2. **NPU/AI accelerator probes** — OS/vendor-specific discovery for Intel/AMD/Qualcomm/Apple/other NPUs with runtime/driver usability checks rather than model-name inference.
3. **Cross-platform CPU feature engine** — native CPUID/HWCAP-style discovery for x86/x64/ARM64/RISC-V instruction sets, virtualization extensions, crypto extensions, vector widths, topology, and microarchitecture identifiers.
4. **NUMA and memory-topology discovery** — sockets, NUMA nodes, locality, total/available memory per node, huge-page support, ECC exposure, memory bandwidth class, and hot-plug state.
5. **Storage-device capability discovery** — per-device topology, media class, capacity, discard/TRIM, queue model, health, encryption support, persistence class, and mount/namespace exposure.
6. **NIC capability discovery** — distinguish physical/virtual NICs and prove link state, speed, MTU, offloads, RSS, RDMA/RoCE/iWARP, SR-IOV/VF, PTP, and device locality without collecting unnecessary addresses.
7. **Virtualization/IOMMU discovery across Windows/Linux/macOS** — VT-x/AMD-V/ARM virtualization, SLAT, IOMMU, nested virtualization, hypervisor type, device passthrough, and VM/container visibility semantics.
8. **Confidential-computing probes** — AMD SEV/SEV-ES/SEV-SNP, Intel TDX/SGX, Arm CCA/TrustZone and relevant kernel/firmware enablement, including attestation evidence binding.
9. **Cross-platform secure-device probes** — TPM 2.0/secure element presence, usability, version, EK/AK support, PCR banks, secure boot relationship, and permissions.
10. **Signed report envelope API** — production code that binds the canonical capability digest to a GAP-06-attested identity and signs/verifies it through GAP-07. The current package demonstrates this in the assessment path but does not expose a first-class signed-envelope object/protocol.
11. **Replay protection and report sequencing** — nonce/epoch/sequence semantics so an old but correctly signed capability report cannot be replayed as current after topology changes.
12. **Trusted time policy** — define and implement the source/quality of `now`, clock rollback behavior, skew tolerance, and interaction with attestation/signature freshness.
13. **Probe configuration model** — versioned declarative configuration for allow/deny lists, intervals, timeouts, privilege requirements, expected devices, environment overrides, and secure defaults.
14. **Probe executor/service loop** — long-running agent that executes `ProbeSchedule.due()`, handles hot-plug notifications, bounds concurrency, and atomically publishes a complete sweep.
15. **Atomic sweep semantics** — generation IDs or snapshots so a consumer never sees a half-old/half-new report assembled across a topology change.
16. **Control-plane publisher transport** — authenticated publication, bounded retries/backoff, cancellation, idempotency, backpressure, offline buffering, reconnect, and delivery acknowledgement.
17. **Structured error-code taxonomy** — stable machine-readable codes for unavailable probe, denied privilege, unsupported OS/API, timeout, driver error, malformed response, stale data, signature failure, and dependency failure.
18. **Probe privilege broker / least-privilege isolation** — separate privileged device queries from the unprivileged reporter with narrow capabilities and explicit authorization.
19. **Report authorization policy** — who may request deep probes, read detailed inventory, consume scheduling facts, or force an immediate re-probe.
20. **Package/artifact provenance enforcement** — verify digests, approved versions, SBOM/provenance attestations, and dependency policy before executing probe plugins.

## P1 — Integration, reliability, and observability

21. **GAP-06 integration tests** — bind capability state to real device identity/attestation evidence and failure modes.
22. **GAP-07 integration tests** — key provisioning, rotation, revocation, signature verification, tamper tests, and unavailable-key behavior.
23. **GAP-01 supervisor integration** — readiness publication, restart behavior, quarantine/disable controls, and hot-plug event routing.
24. **SCH-01 placement integration** — prove `unprobed` is never matched as present and quantitative inventory constraints are evaluated correctly.
25. **PLN-04 execution-plane integration** — tier catalog construction and isolation primitive handling.
26. **GAP-11 accelerator-scheduler integration** — device identity, allocation units, partitions, health transitions, and capacity updates.
27. **Compatibility negotiation** — supported schema-version matrix, downgrade/upgrade rules, unknown-field handling, and migration fixtures.
28. **Persistent probe cache** — optional signed cache with boot/session identity and strict invalidation rules; never reuse stale hardware claims across topology/firmware changes.
29. **Hot-plug watcher adapters** — Linux udev/sysfs, Windows device notifications, and supported platform equivalents.
30. **Health/readiness endpoint** — expose version, last complete sweep, oldest probe age, degraded probes, dependency state, and signing readiness.
31. **Metrics exporter** — probe duration/failure counters, state transitions, report age, sweep duration, queue/backlog, resource cost, and publication failures.
32. **Structured logging** — stable event IDs and bounded fields with explicit privacy/redaction rules.
33. **Distributed tracing/OpenTelemetry hooks** — trace probe sweeps and publication without leaking device secrets.
34. **Tamper-evident audit stream** — record security-sensitive probe requests, configuration changes, forced refreshes, signing events, and quarantine actions.
35. **Operator explain view** — show why each capability is present/absent/unprobed, evidence source, probe time, and the policy preventing promotion.
36. **Alert/dashboard definitions** — stale reports, sustained unprobed transitions, mass capability downgrade, signing failure, probe latency regression, and fleet drift.
37. **Load shedding / circuit breaker** — prevent expensive or failing deep probes from cascading across a node/fleet.
38. **Crash/restart/resume semantics** — define what state survives process crashes and how incomplete sweep generations are discarded.
39. **Quarantine/freeze control** — remove a node's capability report from scheduling immediately when discovery integrity is suspect.
40. **Resource ceilings** — enforce probe concurrency, output size, memory, CPU time, file/device handles, subprocess count, and total sweep deadline.

## P2 — Certification, platform depth, and operations

41. **OS/architecture compatibility matrix** — tested Windows/Linux/macOS distributions and x86-64/ARM64/RISC-V targets, including containers and VMs.
42. **Physical hardware fixture lab** — known-positive and known-negative machines for GPU/NPU/TPM/SEV-SNP/TDX/SGX/RDMA/SR-IOV/IOMMU validation.
43. **Contract conformance fixtures** — golden valid/invalid examples for every public schema and compatibility version.
44. **Property/fuzz tests** — capability labels, mutable record corruption, schema payloads, OS parser inputs, timestamps, and plugin responses.
45. **Concurrency/race tests** — hot-add during sweep, simultaneous forced refresh, report publication races, and configuration replacement.
46. **Fault-injection suite** — permission denial, disappearing devices, hung drivers, time rollback, corrupted sysfs/WMI responses, control-plane partitions, and key-service outages.
47. **Performance/soak benchmarks** — p50/p95/p99/worst-case sweep latency, CPU/memory/I/O overhead, first-boot cost, thermal/power impact, and fleet-scale publication load.
48. **Release regression gates** — machine-readable thresholds that block releases on discovery latency/resource/soundness regressions.
49. **Formal ADR and accountable ownership record** — approved architecture decision, owner, escalation path, review cadence, and exception/waiver process.
50. **Support/security lifecycle policy** — patch SLA, vulnerability response, supported versions, end-of-life, dependency review, and emergency disable procedure.
51. **Incident runbooks** — severity, paging, containment, rollback, forensic evidence, recovery, and fleet-wide false-capability incident handling.
52. **Reproducible packaging + SBOM** — deterministic artifact generation, dependency lock/pins, SBOM, checksums, signing, and provenance statement.
53. **Explicit `pk_core` dependency/version contract** — the standalone ZIP knows `pk_core` is external but does not carry an exact compatible version/commit or dependency lock.
54. **Restore the original `MASTER.md` provenance artifact** — the supplied 4.1.0 README said it was included, but it was absent. Restore the actual source artifact if audit traceability requires it; do not synthesize a replacement and label it verbatim.
55. **Full 100-check evidence package** — run and archive `pk_core run/gate/verify` against the complete estate with all required siblings present, producing machine-readable evidence rather than relying on standalone unit tests.

## Recommended build order

Implement P0 items 1–20 before treating GAP-02 as a production scheduler authority. Then complete P1 integration/observability and P2 certification. The single most important rule to preserve through every extension is the existing fail-closed invariant: **observation, inference, or API unavailability must never be promoted to `present` without a successful capability-specific proof.**
