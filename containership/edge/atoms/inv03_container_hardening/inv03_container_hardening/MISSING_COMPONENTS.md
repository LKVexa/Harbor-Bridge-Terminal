# INV-03 Container Hardening - Missing Components

**Version reviewed:** 4.2.0  
**4.3.0 status:** every item below now has a status, evidence and blockers in `CHECKLIST_STATUS.json` (51 LOCAL_VERIFIED, 12 PARTIAL, 7 BLOCKED, 0 complete). The list is kept as the 4.2.0 gap record.  
**Purpose:** enumerate components that are absent from this archive or only declared by the contract/checklist without a concrete implementation.  
**Priority:** P0 = required before production admission; P1 = required for production hardening/certification; P2 = operational maturity/scale.

## P0 - Runtime isolation and admission enforcement

1. **Sandbox runtime enforcement (C010, C031)** - no gVisor/runsc/user-space-kernel runtime-class requirement is evaluated or enforced.
2. **Sandbox runtime discovery and version pinning (C031, C093)** - no inventory of installed runsc/gVisor versions, approved-version matrix, or minimum security version.
3. **Admission-controller/orchestrator adapter (C021, C030, C040)** - no Kubernetes admission webhook, CRI/containerd adapter, OCI hook, or equivalent production binding calls `evaluate()` before execution.
4. **Fail-closed runtime selection (C033-C034)** - no mechanism rejects workloads when the requested sandbox runtime is absent, unhealthy, unsupported, or silently downgraded.
5. **`allowPrivilegeEscalation=false` / no-new-privileges control (C041-C043)** - not enforced by the current baseline.
6. **Host namespace isolation (C043, C046)** - no explicit controls for host PID, IPC, network, UTS, or user namespace sharing.
7. **Host device isolation (C043, C046)** - no device allowlist/denylist, privileged device passthrough control, or device-cgroup policy.
8. **Host filesystem and mount isolation (C043, C046)** - no hostPath, bind-mount, mount-propagation, Docker socket, runtime socket, or sensitive path prohibition.
9. **Kernel surface restrictions (C041-C043)** - no sysctl allowlist, proc/sysfs masking policy, unsafe proc mount control, or kernel keyring restrictions.
10. **Mandatory access-control profile enforcement (C042-C046)** - no AppArmor/SELinux/Landlock profile requirement or profile identity verification.
11. **User/UID resolution hardening (C041-C046)** - named non-root users are accepted, but no image/user database resolver proves the name cannot map to UID 0.
12. **Rootless/user-namespace isolation policy (C043, C046)** - no requirement for rootless execution, user-namespace remapping, or ID-mapped mounts where supported.
13. **Volume write allowlist (C043, C046)** - read-only rootfs is checked, but writable volumes/tmpfs mounts are not enumerated, constrained, or size-limited.
14. **Resource isolation baseline (C017, C054, C067)** - no CPU, memory, PID, file-descriptor, ephemeral-storage, I/O, hugepage, or device resource ceilings.
15. **Network isolation enforcement (C046)** - no namespace/network-policy/eBPF/egress allowlist integration protecting tenant/workload boundaries.
16. **Runtime drift reconciliation (C046, C052, C059)** - no post-admission watcher proves a running container still matches the admitted hardening state.
17. **Quarantine/freeze/terminate mechanism (C059)** - no executable control to isolate a workload that becomes noncompliant after start.
18. **Emergency disable path (C092)** - README describes the need, but no implemented kill switch or orchestrator action exists.

## P0 - Policy integrity and exception authority

19. **Machine-readable schemas (C022, C026, C029)** - `PK_HARDEN_EVAL/1`, `PK_HARDEN_EXCEPTION/1`, and `PK_HARDEN_BASELINE/1` are named but have no JSON Schema/Protobuf/WIT/OpenAPI schema files.
20. **Signed baseline artifact (C045)** - no signature, digest, provenance, signer identity, or verification chain protects the policy baseline from tampering.
21. **Baseline distribution/cache (C018, C048, C055-C057)** - no atomic distribution mechanism, local last-known-good cache, offline semantics, or recovery strategy.
22. **Atomic activation and rollback (C037-C038)** - no transaction/epoch model prevents nodes from evaluating different partial baselines during rollout.
23. **Persistent exception store (C036, C049, C099)** - exceptions are caller-provided data; no durable authority, database, replicated store, or source-of-truth adapter exists.
24. **Exception approval identity (C023-C024, C099)** - no approver identity, role/capability check, ticket/incident binding, owner, or separation-of-duties control.
25. **Exception maximum TTL / renewal workflow (C048, C099)** - expiry is checked, but no maximum lifetime, renewal process, escalation, or stale-waiver sweep exists.
26. **Trusted time source (C048)** - waiver expiry depends on caller-provided integer time; no trusted clock, monotonicity protection, or time-service failure policy exists.
27. **Tenant/environment/site policy scoping (C006, C012, C035)** - the contract declares boundaries but no concrete baseline overlay/precedence implementation exists.
28. **Conflict/precedence engine (C019)** - no deterministic rule resolves hardening requirements against residency, SLO, emergency, cost, or higher-order security constraints.
29. **Policy compatibility/migration engine (C016, C027, C093)** - no baseline upgrade compatibility rules, migration tool, dual-read period, or old-version refusal policy.

## P1 - Trust, provenance, and adjacent-system integration

30. **Node/workload identity and attestation hook (C044, C048)** - no integration verifies the identity or attestation state of the node/runtime executing the workload.
31. **Policy/artifact provenance verification (C045)** - no integration binds admitted workload specs to signed image digests, provenance attestations, or approved artifact versions.
32. **Seccomp `Localhost` profile integrity (C045)** - the string `Localhost` is accepted, but profile path, digest, provenance, existence, and node consistency are not verified.
33. **Authentication boundary implementation (C023, C044)** - contract-level requirements exist, but the evaluator has no authenticated caller/session context.
34. **Authorization/capability boundary implementation (C024, C042)** - no concrete authorization layer controls who may evaluate, install baselines, or issue/revoke exceptions.
35. **Key-management integration (C047-C048)** - no encryption-at-rest/in-transit implementation or key-rotation path for policy/exception state.
36. **Adjacent image-scanning/provenance hook (C041, C045)** - scanning is correctly outside ownership, but there is no typed integration consuming an upstream scan/provenance verdict.
37. **Runtime intrusion-detection hook (C041, C049, C059)** - detection is outside ownership, but there is no correlation/quarantine integration for runtime findings.

## P1 - Observability, audit, and explainability

38. **Tamper-evident security audit ledger (C049)** - no append-only/chained audit event writer for baseline changes, evaluations, exceptions, revocations, or emergency actions.
39. **Metrics exporter (C071-C072)** - no executable counters/histograms for evaluations, failures by control, exception use, latency, saturation, or dependency health.
40. **Structured logging (C073, C075)** - no stable tenant/workload/node/operation identifiers, redaction policy, or secret-safe logging implementation.
41. **Trace propagation (C074)** - no trace-context input/output or spans around evaluation/admission integration.
42. **Decision explain API/view (C076-C077)** - failed controls are named, but there is no operator-facing explanation object linking decisions to policy version, source inputs, exception identity, and constraints.
43. **Release-lineage/infrastructure-graph correlation (C078)** - no link from a decision to application release, image digest, deployment revision, node, or live topology record.
44. **Telemetry retention/export policy (C079)** - no storage duration, sampling, privacy, tenant isolation, or exporter configuration.
45. **Dashboards and alerts (C080)** - no views/alerts separating normal policy rejection, dependency failure, attack indicators, software defects, or exception-expiry risk.

## P1 - Testing and certification

46. **Real `pk_core` dependency pin and full conformance run (C082, C090)** - framework tests skip in this standalone archive because the dependency is not included or declared here.
47. **Orchestrator integration tests (C030, C083)** - no end-to-end tests prove a denied spec cannot start and an admitted spec reaches the intended sandbox runtime.
48. **Runtime/architecture compatibility matrix tests (C084)** - no automated coverage for supported kernels, containerd/CRI versions, gVisor versions, x86-64/ARM64, cloud/edge tiers, or providers.
49. **Fuzz/property tests (C085)** - no fuzzing of policy schemas, exception records, adapters, or hostile/malformed admission payloads.
50. **Concurrency/race tests (C086)** - no tests for simultaneous baseline rollout, exception issue/revoke, duplicate admission, or stale-controller races.
51. **Threat-model-derived adversarial suite (C087)** - no automated privilege-escalation, container-escape, replay, spoofing, side-channel, or resource-exhaustion scenarios.
52. **Benchmark/soak/burst/fleet suite (C061-C070, C088)** - only a local function-level sanity benchmark exists; there is no certified end-to-end capacity/performance gate.
53. **Fault injection/disaster/reconnect suite (C051-C060, C089)** - no node/runtime/policy-store/time-service/network-partition experiments validate recovery semantics.
54. **Machine-readable release gate artifact (C090, C100)** - no generated signed acceptance record aggregates architecture, security, tests, performance, rollback, and ownership readiness.

## P2 - Operations and governance

55. **Named accountable owner and escalation path (C009, C097)** - not present in the archive.
56. **Approved architecture decision record (C010)** - no ADR records the gVisor/user-space-kernel choice, alternatives, trust boundary, or rollback decision.
57. **Patching/vulnerability/EOL SLA (C094)** - no cadence, severity deadlines, supported-version window, or emergency upgrade rule.
58. **Backup/restore/reconstruction procedure (C095)** - no concrete recovery process for baseline/exception/audit state.
59. **Detailed day-0/day-1/day-2 runbooks (C096)** - README contains a short outline, not executable operational runbooks with commands, health checks, failure branches, and rollback verification.
60. **Incident severity/containment/recovery playbook (C097)** - no security incident process tied to runtime quarantine, baseline rollback, or exception revocation.
61. **Recurring review automation (C098)** - no scheduled access/policy/dependency/configuration/architecture review evidence.
62. **Technical-debt/waiver registry (C099)** - individual exception input exists, but no governed fleet-wide inventory, owner, expiry dashboard, or renewal queue.
63. **Canary/staged rollout controller (C092)** - no rollout percentages, cohorts, health gates, automated rollback, or freeze capability.

## P2 - Packaging and repository completeness

64. **Dependency manifest / packaging metadata** - no `pyproject.toml`/equivalent declares supported Python versions and the required `pk_core` dependency.
65. **Reproducible dependency lock** - no lockfile or hash-pinned dependency set.
66. **CI pipeline** - no workflow runs compile, unit, optimized-mode, integration, fuzz, security, and release-gate checks.
67. **Static-analysis configuration** - no linter/type-checker/security-scanner configuration or enforced quality gate.
68. **Reference fixtures/examples (C029)** - no standalone valid/invalid workload fixture corpus and expected machine-readable results.
69. **`MASTER.md` source artifact** - the 4.1.0 README claimed this master prompt/workflow file was carried in the package, but it was absent from the uploaded archive; 4.2.0 removes the inaccurate claim rather than synthesizing missing source material.
70. **Standalone license/notice/SBOM artifacts** - this archive still does not contain a license file, third-party notice, or software bill of materials. Version 4.2.0 does add a release manifest and SHA-256 checksums.

## Recommended implementation order

1. Complete P0 runtime isolation/admission items 1-18.
2. Complete P0 policy-integrity/exception-authority items 19-29.
3. Add trust, audit, and production observability items 30-45.
4. Make the certification suite executable end to end with items 46-54.
5. Close operations/governance and packaging gaps 55-70 before declaring the component independently production-ready.
