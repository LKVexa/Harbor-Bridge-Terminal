> **Superseded in v5.0.0** by `COMPONENT_STATUS.json` and `CHECKLIST_v5.0.0_ANNOTATED.md`, which record what each component now has and what remains open. This file is kept unchanged below as the v4.2.0 baseline.

# INV-02 v4.2.0 - Missing production components

This inventory distinguishes the hardened in-memory reference model from a complete production container substrate. Presence of a requirement in `CHECKLIST.json` does **not** prove that the corresponding implementation exists in this package.

## P0 - Core container and OCI substrate

1. **OCI Image Specification implementation** - full descriptor, config, manifest, index, platform, annotation, media-type, and artifact handling rather than the package's intentionally small private manifest schema.
2. **OCI Distribution/registry client** - authenticated HTTPS pull/push, blob upload/download, redirects, range requests, resumability, pagination, and registry error semantics.
3. **Persistent content-addressable store** - durable blob/index storage with crash consistency, fsync policy, checksums, leases, garbage collection, compaction, and recovery.
4. **Snapshotter/root filesystem manager** - overlayfs/native snapshot support, layer unpack, whiteouts, copy-up behavior, mount lifecycle, and snapshot garbage collection.
5. **Container runtime integration** - OCI Runtime Spec bundle generation and an integration boundary to a runtime such as runc/crun or another approved runtime.
6. **Container lifecycle controller** - create, prepare, start, exec, signal, stop, kill, delete, inspect, wait, restart, and terminal state semantics.
7. **Linux namespace manager** - PID, mount, network, IPC, UTS, user, and cgroup namespace construction and teardown.
8. **cgroups v2 manager** - CPU, memory, I/O, pids, cpuset, hugetlb, device-related controls, delegation, pressure signals, and cleanup.
9. **Container rootfs/mount policy** - read-only roots, bind mounts, tmpfs, masked/read-only paths, propagation, recursive mount safety, and mount validation.
10. **Container networking integration** - network namespace plumbing, veth lifecycle, IPAM, routes, DNS, service connectivity, and policy integration.
11. **Runtime storage/volume integration** - volume lifecycle, ownership mapping, SELinux labeling where applicable, mount propagation, quotas, and detach/recovery.
12. **Process supervision** - init/reaping behavior, stdio/log pipe ownership, exit status capture, orphan cleanup, and runtime-shim failure handling.
13. **Image unpack/decompression pipeline** - streamed decompression, digest verification during transfer/unpack, decompression-bomb limits, whiteout validation, and atomic commit.
14. **Multi-platform image selection** - OS/architecture/variant matching and deterministic rejection of unsupported platform manifests.
15. **Container metadata/state database** - durable image/container/task/snapshot metadata with transactional updates and migrations.

## P0 - Security, trust, and isolation

16. **Registry authentication provider** - credential helpers, short-lived tokens, OIDC/workload identity, token refresh, scope minimization, and secret redaction.
17. **Transport security policy** - CA trust policy, hostname verification, optional mTLS, TLS-version/cipher policy, proxy controls, and insecure-registry denial by default.
18. **Artifact signature verification** - pluggable signature verification tied to resolved digests before admission/execution.
19. **Provenance/attestation verification** - SLSA/in-toto-style provenance or equivalent, builder identity checks, predicate policy, and trusted-root management.
20. **SBOM ingestion and binding** - SBOM discovery, digest binding, parsing, retention, and policy correlation.
21. **Vulnerability scanning/admission** - scanner integration, severity/exploitability policy, freshness requirements, exception workflow, and fail-closed behavior where required.
22. **Seccomp profile enforcement** - default-deny syscall policy, profile selection, validation, audit mode, and compatibility testing.
23. **Linux capability policy** - drop-by-default capability sets, explicit grants, bounding/ambient-set controls, and validation.
24. **User-namespace/rootless execution** - UID/GID mapping, subordinate-ID management, idmapped mounts where supported, and rootless runtime constraints.
25. **MAC integration** - SELinux/AppArmor policy selection, labeling/profile loading, denial telemetry, and rollout compatibility.
26. **No-new-privileges/setuid controls** - enforcement against privilege amplification inside containers.
27. **Device access broker** - explicit device allowlists, GPU/accelerator mediation, hotplug handling, ownership, and cleanup.
28. **Secrets isolation** - tmpfs/in-memory secret delivery, rotation, revocation, no-image/no-log guarantees, and teardown scrubbing.
29. **Tenant/workload isolation policy** - explicit trust domains and rules for namespace, storage, network, device, cache, and metadata sharing.
30. **Durable quarantine/admission store** - authoritative quarantine state shared across nodes/controllers, not the current process-local dictionary.
31. **Tamper-evident audit ledger** - append-only/security-protected events for pushes, tag moves, resolutions, verification failures, quarantine actions, and policy decisions.
32. **Security policy engine integration** - externalized, versioned policy decisions instead of only local immutable-environment settings.
33. **Sandboxed-runtime option** - policy-driven integration with stronger isolation technologies where threat models require it.

## P1 - Registry/content correctness and concurrency

34. **Compare-and-swap tag updates** - optimistic concurrency/ETag-style protection so concurrent publishers cannot silently overwrite one another.
35. **Distributed locking/lease semantics** - safe multi-process/multi-node ownership for downloads, unpack, GC, snapshots, and metadata mutation.
36. **Resumable blob transfer manager** - partial-download checkpoints, range validation, digest continuity, retry budgeting, and stale-part cleanup.
37. **Content leases and garbage collection** - prevent deletion of blobs/snapshots still referenced by images, containers, or in-flight pulls.
38. **Corruption repair workflow** - detect, quarantine, re-fetch, verify, and atomically replace corrupt local content with operator-visible evidence.
39. **Registry mirror/fallback support** - ordered mirrors, trust-equivalence policy, digest consistency checks, and failover without tag drift.
40. **Disconnected/offline cache mode** - explicit stale-data policy, pre-seeding, pinned-digest operation, reconnect reconciliation, and storage-pressure behavior.
41. **Rate limits and quotas** - per-tenant/workload/node transfer, storage, concurrent pull, unpack, and metadata limits.
42. **Backpressure/admission control** - bounded queues and rejection/load-shedding behavior under disk, CPU, memory, network, or registry saturation.
43. **Retry/circuit-breaker library** - bounded exponential backoff with jitter, retry classification, deadline propagation, and dependency circuit state.
44. **Time/deadline abstraction** - monotonic deadlines, cancellation propagation, timeout budgets, and deterministic testing hooks.

## P1 - Observability and operations

45. **Structured metrics exporter** - pull latency/throughput, cache hit rate, bytes saved, verification failures, tag refusals, saturation, GC, and error classes.
46. **Structured logging pipeline** - stable operation/request/node/tenant/workload identifiers and strict secret/token redaction.
47. **Distributed tracing** - trace context over registry, policy, signature, metadata, unpack, and runtime boundaries.
48. **Health/readiness endpoints** - content-store, registry, policy, signer/verifier, snapshotter, runtime, and disk-pressure status.
49. **Decision explain API** - operator-readable explanation for why a reference was accepted/refused/quarantined and which policy/evidence caused it.
50. **Dashboards and alerts** - ordinary load vs. registry outage, corruption, policy rejection, disk pressure, attack indicators, and software defects.
51. **Capacity/saturation model** - predictive disk, inode, network, unpack CPU, memory, pull concurrency, and cache-pressure thresholds.
52. **Backup/restore/reconstruction procedure** - metadata recovery, content rehydration, trust-material handling, and disaster validation.
53. **Rolling upgrade and rollback controller** - schema/runtime compatibility gates, canarying, rollback, and emergency disable.
54. **Configuration system** - typed configuration schema, validation, secure defaults, environment/site overlays, provenance, atomic activation, and rollback.
55. **Credential/key rotation workflow** - runtime-safe refresh and revocation without process-wide restart where possible.
56. **Incident runbook and escalation metadata** - severity mapping, containment, registry compromise procedures, quarantine, recovery, and evidence preservation.

## P1 - Testing and certification

57. **OCI conformance fixtures** - valid/invalid manifests, indexes, foreign/unknown media types, whiteouts, platform selection, and registry protocol cases.
58. **Real registry integration tests** - authenticated TLS registry, mirror, outage, redirect, range, resume, token-expiry, and corruption scenarios.
59. **Real runtime integration tests** - bundle creation and lifecycle tests against supported runtime/runtime versions.
60. **Namespace/cgroup isolation tests** - privilege, resource, PID, mount, network, and device boundary verification on supported Linux kernels.
61. **Fuzzing corpus/harnesses** - references, manifests, descriptors, registry responses, decompression paths, metadata migrations, and policy inputs.
62. **Adversarial/escape tests** - path traversal, symlink/hardlink attacks, malicious layers, decompression bombs, capability escalation, namespace escape attempts, and resource exhaustion.
63. **Race/concurrency stress suite** - concurrent tag writes, pulls, GC, quarantine, unpack, snapshot operations, and process restarts.
64. **Fault-injection suite** - disk-full, ENOSPC/inode exhaustion, torn writes, process kill, network partitions, registry 5xx, TLS failures, and metadata corruption.
65. **Performance/soak/fleet benchmarks** - cold/warm pulls, shared-layer density, startup latency, unpack throughput, tail latency, GC impact, and long-duration leak detection.
66. **Cross-architecture/kernel/runtime matrix** - supported CPU architectures, Linux distributions/kernels, filesystems, cgroup modes, runtimes, and registry versions.
67. **Machine-readable release evidence** - signed test/gate outputs tied to source/version/artifact digests before production certification.

## P2 - Packaging, governance, and missing artifacts

68. **`MASTER.md`** - referenced by the prior README but absent from the supplied archive; restore the authoritative master prompt/workflow artifact or remove it from the distribution contract.
69. **Package/build metadata** - `pyproject.toml` or equivalent with dependency/version constraints, build backend, supported Python versions, and reproducible packaging rules if this component is distributed independently.
70. **Dependency lock/SBOM for the package** - pinned `pk_core` compatibility plus a generated software bill of materials for release artifacts.
71. **License/NOTICE files** - no license or notice artifact is present in this upload; add the estate-approved legal metadata if this package is distributable.
72. **Architecture Decision Record** - approved technology/scope decision covering OCI/container-runtime choices and rejected alternatives.
73. **Named ownership/escalation metadata** - accountable team/service owner, on-call route, security owner, and escalation path.
74. **Compatibility matrix** - supported `pk_core`, Python, OCI spec, runtime, registry, Linux kernel/cgroup, snapshotter, and architecture versions.
75. **Release automation/CI** - compile, unit, integration, fuzz, security, benchmark, packaging, SBOM, signature, and evidence gates.
76. **Migration framework** - forward/backward metadata migrations, rollback compatibility, downgrade policy, and migration evidence.
77. **Exception/waiver registry** - owned, expiring exceptions for unsupported runtimes, registries, security profiles, or operational constraints.
78. **End-of-life/vulnerability SLA** - patch windows, CVE response, deprecation policy, supported-version lifetime, and emergency release process.

## Current validation gap

The uploaded archive does not include `pk_core`. Therefore the three estate-wide conformance tests in `tests/test_component.py` cannot be executed in this isolated package and are skipped by design. The v4.2.0 standalone registry suite executes without `pk_core`; full certification still requires rerunning the conformance suite in the complete estate checkout.
