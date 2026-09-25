# INV-40 Missing Components — Post-4.2.0 Audit

> Scope: concrete evidence in this repository only. External `pk_core` defaults or unexecuted gates are not counted as implementation evidence.

**Checklist result:** 9 present, 26 partial, 65 missing; **91 of 100 requirements remain not fully evidenced.**

## Repository-level missing components

| ID | Missing component | Detail |
|---|---|---|
| REPO-001 | pk_core dependency packaging/pin | pk_core is required by component.py/contract.py but is not bundled and there is no requirements/lock/package metadata declaring an installable version. |
| REPO-002 | MASTER.md source artifact | README 4.1.0 claimed MASTER.md was bundled, but the file is absent. 4.2.0 corrects the claim rather than fabricating the missing source. |
| REPO-003 | production hypervisor/provider adapter | No QEMU/KVM/libvirt/cloud provider adapter exists; runtime.py is a deterministic reference model only. |
| REPO-004 | build/install metadata | No pyproject.toml/setup metadata, dependency lock, or reproducible environment definition is present. |
| REPO-005 | license file | No repository license/notice file is present in the supplied archive. |
| REPO-006 | CI/release workflow | No continuous-integration, packaging, signing, release, or automated gate workflow is present. |

## Complete open checklist gap inventory

| Requirement | Status | Missing/partial component |
|---|---|---|
| INV-40-C005 | partial | Assumptions cover guest trust, boot time, and memory, but not the required network, storage, runtime, node, and control-plane assumptions. |
| INV-40-C009 | missing | Accountable owner and escalation path. |
| INV-40-C010 | missing | Approved architecture decision record for EC2/QEMU-style full VMs and the compatibility/isolation rationale. |
| INV-40-C011 | partial | Mandatory behavior exists as prose, but there is no normative SHALL-level requirements specification with identifiers and acceptance criteria. |
| INV-40-C012 | missing | Cloud/datacenter/near-edge/far-edge functional requirement variants. |
| INV-40-C013 | partial | Some SLOs and ceilings exist, but availability, durability/consistency where applicable, and comprehensive non-functional thresholds are not defined. |
| INV-40-C014 | partial | Runtime returns ok/degraded for boot budget and raises terminal operational errors, but success/partial/retryable/terminal semantics are not comprehensively specified. |
| INV-40-C016 | missing | Versioning and backward-compatibility policy for code and wire schemas. |
| INV-40-C017 | partial | Per-guest resident memory is capped, but quotas, fleet capacity ceilings, and fairness semantics are absent. |
| INV-40-C018 | missing | Disconnected/intermittent-network behavior. |
| INV-40-C019 | missing | Conflict-precedence policy for security, residency, SLO, and cost constraints. |
| INV-40-C020 | missing | Requirements traceability matrix mapping requirements to implementation and verification evidence. |
| INV-40-C021 | partial | Contract lists create/boot/stop/destroy/error logical interfaces, but actual hypervisor, device, event, file, RPC, and control-plane boundaries are not fully enumerated. |
| INV-40-C022 | partial | String schema identifiers exist, but there are no versioned schema definitions or generated/validated typed wire contracts. |
| INV-40-C023 | missing | Authentication requirements for every boundary. |
| INV-40-C024 | missing | Authorization/capability model for every boundary. |
| INV-40-C025 | partial | Destroy is idempotent and lifecycle errors are bounded, but timeout, cancellation, retry, and backpressure semantics are absent. |
| INV-40-C026 | partial | Operational VM failures expose PK_FULL_VM_ERROR/1 codes; validation/configuration failures still use generic Python exceptions and no complete error catalog exists. |
| INV-40-C027 | missing | Mixed-version compatibility behavior. |
| INV-40-C028 | partial | Boot and resident-memory bounds exist, but payload, queue, concurrency, connection, and broader resource limits are not specified. |
| INV-40-C029 | missing | Reference examples and conformance fixtures. |
| INV-40-C030 | missing | Automated adjacent-layer integration tests. |
| INV-40-C031 | missing | Pinned/approved hypervisor/provider implementations and versions (for example QEMU/KVM/libvirt or cloud API versions). |
| INV-40-C032 | missing | Immutable-artifact versus mutable-config/state separation. |
| INV-40-C033 | missing | Declarative configuration schema and secure defaults. |
| INV-40-C034 | partial | Runtime inputs fail closed, but there is no declarative configuration subsystem to validate before activation. |
| INV-40-C035 | missing | Site/environment-specific configuration without rebuild. |
| INV-40-C036 | missing | Configuration provenance/version/author/activation-time recording. |
| INV-40-C037 | missing | Atomic/transactional configuration update mechanism. |
| INV-40-C038 | missing | Automatic and operator-driven configuration rollback. |
| INV-40-C039 | partial | The repository currently contains no embedded credentials, but there is no explicit secret/configuration/diagnostic handling policy or test. |
| INV-40-C040 | missing | Deterministic bootstrap/install path from an empty environment; pk_core and packaging metadata are not bundled. |
| INV-40-C041 | partial | contract.py lists four threats, but no complete threat model covers supply chain, control-plane abuse, side channels, identity, network, storage, or host compromise. |
| INV-40-C042 | missing | Least-privilege identities/capabilities for the real virtualization implementation. |
| INV-40-C043 | missing | Ambient filesystem/network/device/kernel/secret authority reduction for the real hypervisor/control-plane integration. |
| INV-40-C044 | missing | Authentication of nodes, peers, artifacts, providers, and control-plane actors. |
| INV-40-C045 | missing | Artifact signature/digest/provenance/version verification. |
| INV-40-C046 | partial | Concrete device-instance exclusivity is now enforced in-process, but execution, memory, network, persistent-state, IOMMU, and hypervisor isolation are not implemented here. |
| INV-40-C047 | missing | Managed encryption in transit/at rest and key rotation. |
| INV-40-C048 | missing | Fail-safe behavior for unavailable identity, attestation, policy, key, or time services. |
| INV-40-C049 | missing | Tamper-evident security audit event pipeline. |
| INV-40-C050 | partial | Tests cover primitive refusal, footprint exhaustion, device-sharing conflict, and a lease race, but not the full adversarial set (escape, injection, replay, spoofing, side channels, etc.). |
| INV-40-C051 | partial | Several failure modes are documented, but process/node/site/network/provider/dependency/control-plane failure modes are not exhaustively modeled. |
| INV-40-C052 | missing | Health/stall detectors and thresholds. |
| INV-40-C053 | missing | Bounded retry with backoff/jitter and retry-safety classification. |
| INV-40-C054 | missing | Admission control, load shedding, and/or circuit breaking. |
| INV-40-C055 | missing | Failover behavior preserving isolation, residency, and consistency. |
| INV-40-C056 | missing | Defined degraded mode for noncritical dependency failures. |
| INV-40-C057 | partial | Stopped guests can restart and destroyed guests cannot, but crash consistency, persisted restart state, replay, and recovery semantics are absent. |
| INV-40-C058 | partial | The in-process lease registry blocks duplicate device ownership, but there is no distributed lease/fencing protection for split-brain, stale controllers, or duplicate execution. |
| INV-40-C059 | partial | destroy() provides a terminal local disable path, but there is no quarantine/freeze/isolate control plane or operator workflow. |
| INV-40-C060 | missing | Fault-injection recovery tests. |
| INV-40-C061 | missing | Reproducible performance/resource/power baseline harness and results. |
| INV-40-C062 | missing | p50/p95/p99/worst-case thresholds. |
| INV-40-C063 | missing | Steady/burst/overload/scale-out/scale-in/recovery performance tests. |
| INV-40-C064 | missing | Per-workload and per-tenant overhead measurements. |
| INV-40-C065 | missing | Documented analysis of avoidable copies/context switches/network hops/duplicated state/images. |
| INV-40-C066 | missing | Implemented and evidenced locality/caching/zero-copy/batching/kernel-bypass optimizations where applicable. |
| INV-40-C067 | partial | Resident footprint is bounded per guest and the device set is finite, but queues, concurrency, buffers, and fleet fan-out are not bounded. |
| INV-40-C068 | missing | Power/thermal measurement for constrained nodes. |
| INV-40-C069 | missing | Capacity model and saturation signals. |
| INV-40-C070 | missing | Automated performance-regression release gate. |
| INV-40-C071 | missing | Health/readiness/version/config/dependency/capability endpoint or report. |
| INV-40-C072 | missing | Runtime structured metrics emission. |
| INV-40-C073 | missing | Structured logs with stable correlation identifiers. |
| INV-40-C074 | missing | Trace-context propagation. |
| INV-40-C075 | missing | Safe high-cardinality diagnostic interface with privacy controls. |
| INV-40-C076 | missing | Decision-reason recording for automated decisions. |
| INV-40-C077 | missing | Operator explain view linking decisions to inputs/policy/topology/constraints. |
| INV-40-C078 | missing | Correlation with release lineage and live infrastructure graph. |
| INV-40-C079 | missing | Telemetry retention/sampling/privacy/export policy. |
| INV-40-C080 | missing | Dashboards and differentiated alerting. |
| INV-40-C082 | partial | Public runtime methods are unit-tested, but there are no schema fixtures/consumer contract tests and pk_core contract tests cannot run without the external dependency. |
| INV-40-C083 | missing | Integration tests against every supported adjacent layer/tier. |
| INV-40-C084 | missing | Compatibility matrix tests across CPU architectures, runtimes, hypervisors, providers, and protocol versions. |
| INV-40-C085 | missing | Fuzzing of schemas/protocol/untrusted-input boundaries. |
| INV-40-C086 | partial | There is a concurrent device-lease race test, but no broader race testing across lifecycle, configuration, persistence, or distributed ownership. |
| INV-40-C087 | partial | Some tests derive from documented threats (missing primitive/device conflict/resource exhaustion), but the threat model is not fully translated into security tests. |
| INV-40-C088 | missing | Benchmark, soak, burst, and fleet-scale tests. |
| INV-40-C089 | missing | Disaster/partition/reconnect/degraded-control-plane tests. |
| INV-40-C090 | missing | Machine-readable release acceptance evidence artifact and certification rule. |
| INV-40-C091 | partial | Three SLO/error-budget statements exist; support commitments, service windows, and ownership/escalation commitments are absent. |
| INV-40-C092 | partial | README mentions rollback and emergency disable, but canary/staged rollout, rollback validation, and executable procedures are absent. |
| INV-40-C093 | missing | Supported-version compatibility matrix. |
| INV-40-C094 | missing | Patching, vulnerability-response, and end-of-life SLAs. |
| INV-40-C095 | missing | Backup/restore/migration/reconstruction procedures for applicable state. |
| INV-40-C096 | partial | README contains day-0/day-1/day-2 bullets, but they are not operational runbooks with prerequisites, commands, validation, rollback, and recovery steps. |
| INV-40-C097 | missing | Incident severity, paging, escalation, containment, and recovery procedures. |
| INV-40-C098 | missing | Recurring access/policy/dependency/configuration/architecture review process. |
| INV-40-C099 | missing | Exception/waiver/technical-debt/deprecation register with owners and expiries. |
| INV-40-C100 | missing | Formal production exit-gate artifact/results. README references pk_core gate, but pk_core and gate evidence are absent from this archive. |

## Requirements with sufficient concrete evidence in this archive

INV-40-C001, INV-40-C002, INV-40-C003, INV-40-C004, INV-40-C006, INV-40-C007, INV-40-C008, INV-40-C015, INV-40-C081.
