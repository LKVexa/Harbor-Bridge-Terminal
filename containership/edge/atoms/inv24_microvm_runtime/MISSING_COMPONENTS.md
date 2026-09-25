# INV-24 v4.2.0 — Missing Components After Second Audit

> **4.3.0 update:** every item below now has an implementation or disposition, traceability and evidence; see `../docs/CLOSURE_REPORT.md` and `../release/COMPONENT_STATUS.json`. This list is kept as the historical 4.2.0 baseline.

Scope: components not present or not independently verifiable in the supplied repository after the 4.2.0 hardening pass. “Missing” means no concrete artifact/implementation/test/evidence was found in this archive; a prose claim in the external `pk_core` framework cannot substitute for local evidence.

## Critical external/runtime integration gaps

1. **Actual Firecracker/VMM adapter and pinned runtime binary** (`C031`, `C040`) — no Firecracker executable, SDK/adapter, version pin, checksum, launch wrapper, or process supervision code. `MicroVM` remains a domain/state model, not a VMM launcher.
2. **Hardware virtualization integration** (`C003`, `C030`, `C083`) — no executable adapter/test for INV-23/KVM, `/dev/kvm`, CPU feature detection, or virtualization availability/failure handling.
3. **Device backend integration** (`C003`, `C021`, `C030`, `C083`) — no concrete INV-25 virtio-net/block/vsock/serial/RTC backend bindings or end-to-end device tests.
4. **Snapshot integration** (`C003`, `C030`, `C057`, `C083`, `C095`) — no INV-26 snapshot/restore API, snapshot format validation, crash consistency, or restore tests.
5. **Execution-plane admission integration** (`C003`, `C024`, `C030`, `C054`, `C083`) — no PLN-04 adapter, admission controller, capability token validation, queueing, or load-shedding implementation.
6. **High-performance I/O integration** (`C003`, `C030`, `C061-C066`, `C083`) — INV-35 remains optional and absent; no local datapath implementation or throughput evidence.

## Architecture, requirements, ownership, and traceability gaps

7. **Accountable owner/escalation artifact** (`C009`) — no OWNER/CODEOWNERS/on-call/escalation document.
8. **Approved architecture decision record** (`C010`) — no ADR selecting Firecracker with alternatives, rationale, constraints, consequences, and approval record.
9. **Environment-specific SHALL requirements** (`C011-C014`, `C018-C019`) — no standalone normative requirements specification covering cloud/datacenter/near-edge/far-edge, degraded/network-offline semantics, conflict precedence, and terminal/retryable outcomes.
10. **Requirements traceability matrix** (`C020`) — no machine-readable mapping from all 100 checks to concrete code/test/evidence artifacts.
11. **Compatibility/versioning policy** (`C016`, `C027`, `C093`) — no supported-version matrix for Python, `pk_core`, Firecracker, kernel/KVM, adjacent INV/PLN components, architectures, or schema compatibility.
12. **Complete interface inventory** (`C021`) — contract lists logical interfaces but no exhaustive boundary catalog covering process, socket, file, device, hypervisor, metadata, control-plane, and host-kernel boundaries.
13. **Typed external schemas** (`C022`, `C026`, `C029`, `C082`) — dicts carry schema names, but no JSON Schema/Protobuf/WIT/OpenAPI definitions, structured error schema, fixtures, or schema conformance tests.
14. **Master prompt evidence file** — README previously claimed `MASTER.md`; it is absent from the archive.

## Configuration and supply-chain gaps

15. **Declarative configuration subsystem** (`C032-C038`) — no config schema/file loader, environment/site overlays, provenance, author/activation metadata, transactional update, rollback, or dynamic activation mechanism.
16. **Secret separation/enforcement** (`C039`) — no secret-provider boundary, redaction rules/tests, or diagnostic secret scanning.
17. **Reproducible bootstrap/install packaging** (`C040`) — no `pyproject.toml`/lockfile, install metadata, bootstrap script, pinned dependency manifest, or offline/bootstrap verification.
18. **Artifact integrity/provenance** (`C031`, `C045`) — no Firecracker/kernel/rootfs signature/digest verification, SBOM, provenance attestation, approved-artifact policy, or dependency lock.
19. **License/legal metadata** — no LICENSE/NOTICE file in the supplied archive.

## Security and isolation gaps

20. **Threat model** (`C041`, `C050`, `C087`) — no threat-model document with assets, trust boundaries, attack trees/scenarios, mitigations, residual risk, and test linkage.
21. **Identity/authentication layer** (`C023`, `C044`, `C048`) — no node/peer/control-plane identity mechanism, certificate/attestation verification, or unavailable-identity fail-closed behavior.
22. **Authorization/capability layer** (`C024`, `C042-C043`) — no capability model, host filesystem/network/device/kernel authority reduction, seccomp/jailer/cgroup/namespace policy, or least-privilege execution wrapper.
23. **Tenant isolation enforcement below the model** (`C046`) — immutable tenant labels help the domain object, but there is no actual VM memory, process, network, storage, cgroup, jailer, or device isolation implementation/evidence.
24. **Encryption/key management** (`C047-C048`) — no transport encryption, at-rest encryption, key rotation, KMS integration, or failure policy.
25. **Tamper-evident security audit log** (`C049`) — no append-only/hash-chained audit event implementation.
26. **Adversarial security suite** (`C050`, `C087`) — no tests for escape, privilege escalation, injection, replay, spoofing, side channels, malicious device descriptors, or resource exhaustion.

## Resilience and failure-handling gaps

27. **Health/stall detector** (`C051-C052`, `C071`) — `status()` exposes local state but no active liveness/readiness probes, VMM heartbeat, guest stall detector, dependency health, or thresholds.
28. **Retry/backoff/cancellation/idempotency layer** (`C025`, `C053`) — no operation IDs, cancellation, bounded retry, backoff/jitter, or idempotency keys.
29. **Admission/load shedding/circuit breaking** (`C054`) — no concurrency admission, queue cap, overload shedding, or dependency breaker.
30. **Failover/degraded-mode implementation** (`C055-C056`, `C089`) — no scheduler/failover policy, degraded control-plane behavior, offline semantics, partition/reconnect implementation, or tests.
31. **Crash/restart/duplicate ownership protections** (`C057-C058`) — no persistent ownership lease, fencing, generation/epoch, replay journal, duplicate execution prevention, or restart reconciliation.
32. **Quarantine/freeze/emergency isolation control** (`C059`) — stop/destroy exists per object, but no fleet/operator quarantine, freeze, deny-admission, or node isolation control.
33. **Fault-injection suite** (`C060`, `C089`) — no process kill, VMM crash, node loss, network partition, disk/full, dependency outage, or recovery-objective tests.

## Performance/capacity gaps

34. **Benchmark harness and baselines** (`C061-C064`, `C088`) — no measured startup distribution, throughput, CPU/memory/storage/network overhead, density, steady/burst/overload/scale/recovery, soak, or fleet-scale results.
35. **Tail-latency thresholds beyond boot ceiling** (`C062`) — no p50/p95/p99/worst-case targets and evidence for lifecycle/control/data paths.
36. **Optimization analysis/evidence** (`C065-C066`) — no profiling/copy/context-switch/network-hop analysis or demonstrated zero-copy/batching/kernel-bypass choices.
37. **Full resource fan-out limits** (`C017`, `C028`, `C067`, `C069`) — per-instance vCPU/memory are now bounded, but no fleet instance quota, per-tenant fairness, queue/connection/buffer/concurrency limits, density model, or saturation predictor.
38. **Power/thermal characterization** (`C068`) — no edge-node power or thermal measurements.
39. **Performance regression release gate** (`C070`) — no automated benchmark threshold gate in CI/release tooling.

## Observability gaps

40. **Runtime metrics exporter** (`C071-C072`) — contract names metrics, but no counter/gauge/histogram implementation, exporter, scrape endpoint, or dependency/capability/version health surface.
41. **Structured logging** (`C073`) — no logger/event schema with stable node/tenant/workload/component/operation correlation IDs.
42. **Distributed tracing** (`C074`) — no trace context propagation or spans.
43. **Safe high-cardinality diagnostics/redaction** (`C075`) — no bounded diagnostics endpoint, redaction policy, or leakage tests.
44. **Decision/explain records** (`C076-C078`) — no reason records, topology/policy linkage, release lineage correlation, or live infrastructure graph linkage.
45. **Telemetry governance** (`C079`) — no retention, sampling, privacy, access, or export policy.
46. **Dashboards/alerts** (`C080`) — no dashboard definitions or alert rules distinguishing overload, policy rejection, dependency failure, attack, and defect.

## Testing and certification gaps

47. **Framework-independent contract tests for every interface** (`C082`) — standalone unit tests cover the domain object, but there are no formal schema/consumer contract tests for all external boundaries.
48. **Adjacent-layer integration tests** (`C030`, `C083`) — none are bundled.
49. **Architecture/provider compatibility matrix tests** (`C084`) — no x86_64/aarch64, kernel/KVM, Firecracker-version, provider, or protocol-version matrix.
50. **Fuzz/property testing** (`C085`) — no fuzzers/property tests for configuration, schemas, identifiers, timing inputs, lifecycle sequences, device requests, or external payloads.
51. **Concurrency/race tests** (`C086`) — none; the current in-memory object is not designed for concurrent mutation, and no synchronization contract is specified.
52. **Benchmark/soak/burst/fleet tests** (`C088`) — absent.
53. **Disaster/partition/reconnect tests** (`C089`) — absent.
54. **Machine-readable acceptance evidence** (`C090`, `C100`) — no generated gate result/evidence ledger is included; original conformance tests require external `pk_core` and skip when it is missing.
55. **CI pipeline** (`C070`, `C090`, `C100`) — no GitHub Actions/other CI definition enforcing compile, unit, security, compatibility, benchmark, artifact-integrity, and release gates.

## Operations/release/governance gaps

56. **Production SLO/support policy** (`C091`) — contract has three SLO statements, but no service support commitments, measurement windows, burn-rate/error-budget policy, ownership, or paging criteria.
57. **Canary/staged rollout/rollback procedures** (`C038`, `C092`) — README gives only a conceptual gate; no executable deployment/rollback runbook or emergency-disable mechanism.
58. **Patching/vulnerability/EOL policy** (`C094`) — no SLA/process for CVEs, Firecracker/kernel updates, coordinated disclosure, supported branches, or EOL.
59. **Backup/restore/reconstruction runbook** (`C095`) — absent; contract says snapshot is external but does not define operational reconstruction.
60. **Day-0/day-1/day-2 runbooks** (`C096`) — README has a short outline, not executable/operator-grade procedures with prerequisites, verification, rollback, failure branches, and escalation.
61. **Incident response plan** (`C097`) — no severity taxonomy, paging, escalation, containment, evidence collection, recovery, or post-incident process.
62. **Recurring review controls** (`C098`) — no scheduled access/policy/dependency/configuration/architecture review process or evidence template.
63. **Exception/waiver/debt registry** (`C099`) — no owners, rationale, risk acceptance, expiry, or review dates.
64. **Formal production exit gate** (`C100`) — no local machine-readable gate that aggregates architecture, security, resilience, performance, observability, tests, rollback, and ownership; production readiness cannot be established from this archive alone.

## Verification limitation

`tests/test_runtime.py` passes locally and proves the hardened domain model. `tests/test_component.py` cannot execute its 100-item framework assessment in this archive because `pk_core` is not supplied; those tests are skipped by design. Therefore the repository is **locally hardened but not production-certified**.
