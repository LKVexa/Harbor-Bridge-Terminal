# INV-40 Full Virtualization Tier — Comprehensive Open-Component Implementation Checklist

**Baseline repository:** `inv40_full_virtualization_tier` v4.2.0  
**Checklist generated from:** `INV40_MISSING_COMPONENTS_v4.2.0.json`  
**Audit date:** 2026-09-22  
**Scope:** 6 repository-level missing components + 91 open checklist requirements (65 missing, 26 partial).

## How to use this checklist

- `[ ]` means the work or evidence is not yet complete. Mark an item complete only when both the implementation and its referenced verification evidence exist.
- **P0** = production/security/release blocker; **P1** = required production-hardening work; **P2** = performance/operational maturity work that should be completed before broad-scale certification unless explicitly scoped out.
- A **partial** finding is treated as a completion task: preserve the verified behavior already present and close only the missing portions without regressing existing tests.
- A **missing** finding is treated as a build-from-zero task and requires design, implementation, tests, operational evidence, and traceability.
- “Done” is evidence-based. Prose, TODO markers, skipped tests, or an external dependency that is not available in the release environment do not constitute completion.

## Global definition of done

- [ ] All P0 items applicable to the declared production profile are closed or have a time-bounded, approved waiver in the exception register.
- [ ] Every `INV-40-Cxxx` requirement has a traceability entry linking requirement -> design -> implementation -> tests -> machine-readable evidence -> owner.
- [ ] Mandatory tests execute in CI; unexpected `SKIPPED`, missing dependency, unavailable hardware, or stale evidence causes a non-passing release gate.
- [ ] The production artifact, dependency lock, configuration/schema revision, provider compatibility profile, SBOM, signatures/attestations, and test evidence are cryptographically bound by digest.
- [ ] Security/isolation invariants are demonstrated under success, failure, restart, concurrency, partition, and adversarial conditions.
- [ ] Operational runbooks, alerts, rollback, quarantine, incident escalation, backup/restore, and support ownership have been exercised, not merely written.
- [ ] The final production gate (`INV-40-C100`) returns GO only for the exact artifact/profile whose evidence was verified.

## Prioritized gap index

| ID | Priority | Status | Dimension / component | Gap |
|---|---|---|---|---|
| REPO-001 | P0 | missing | Repository | pk_core dependency packaging/pin |
| REPO-002 | P1 | missing | Repository | MASTER.md source artifact |
| REPO-003 | P0 | missing | Repository | production hypervisor/provider adapter |
| REPO-004 | P0 | missing | Repository | build/install metadata |
| REPO-005 | P0 | missing | Repository | license file |
| REPO-006 | P0 | missing | Repository | CI/release workflow |
| INV-40-C005 | P1 | partial | Architecture & Scope | Document assumptions Full virtualization tier makes about nodes, runtimes, networks, storage, and control planes. |
| INV-40-C009 | P0 | missing | Architecture & Scope | Assign an accountable owner and escalation path for Full virtualization tier. |
| INV-40-C010 | P0 | missing | Architecture & Scope | Approve an architecture decision record for Full virtualization tier, its technologies (EC2/QEMU-style full VMs), and its function (Maximum legacy compatibility/compliance isolation). |
| INV-40-C011 | P0 | partial | Requirements & Semantics | Translate the source function of Full virtualization tier — Maximum legacy compatibility/compliance isolation — into testable SHALL-level requirements. |
| INV-40-C012 | P1 | missing | Requirements & Semantics | Define functional requirements for Full virtualization tier across cloud, datacenter, near-edge, and far-edge contexts where applicable. |
| INV-40-C013 | P0 | partial | Requirements & Semantics | Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable. |
| INV-40-C014 | P0 | partial | Requirements & Semantics | Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Full virtualization tier. |
| INV-40-C016 | P0 | missing | Requirements & Semantics | Define versioning and backward-compatibility requirements for Full virtualization tier. |
| INV-40-C017 | P1 | partial | Requirements & Semantics | Define capacity ceilings, quotas, and fairness semantics relevant to Full virtualization tier. |
| INV-40-C018 | P1 | missing | Requirements & Semantics | Define behavior when network connectivity is intermittent or absent. |
| INV-40-C019 | P0 | missing | Requirements & Semantics | Define precedence rules when Full virtualization tier requirements conflict with security, residency, SLO, or cost constraints. |
| INV-40-C020 | P0 | missing | Requirements & Semantics | Maintain a requirements traceability matrix from each Full virtualization tier requirement to implementation and verification evidence. |
| INV-40-C021 | P0 | partial | Interfaces & Integration | Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Full virtualization tier. |
| INV-40-C022 | P0 | partial | Interfaces & Integration | Use versioned typed schemas for all externally visible Full virtualization tier contracts. |
| INV-40-C023 | P0 | missing | Interfaces & Integration | Define authentication requirements at each Full virtualization tier boundary. |
| INV-40-C024 | P0 | missing | Interfaces & Integration | Define authorization and explicit capability requirements at each Full virtualization tier boundary. |
| INV-40-C025 | P0 | partial | Interfaces & Integration | Define timeout, cancellation, retry, idempotency, and backpressure semantics for Full virtualization tier. |
| INV-40-C026 | P0 | partial | Interfaces & Integration | Define structured failure codes and machine-readable error details for Full virtualization tier. |
| INV-40-C027 | P0 | missing | Interfaces & Integration | Define compatibility behavior when peers use different supported versions. |
| INV-40-C028 | P0 | partial | Interfaces & Integration | Document payload, concurrency, queue, connection, or resource limits at Full virtualization tier interfaces. |
| INV-40-C029 | P1 | missing | Interfaces & Integration | Provide reference examples and conformance fixtures for Full virtualization tier. |
| INV-40-C030 | P0 | missing | Interfaces & Integration | Create automated integration tests proving Full virtualization tier interoperates with adjacent architectural layers. |
| INV-40-C031 | P0 | missing | Implementation & Configuration | Select and pin approved implementations, versions, or specifications for Full virtualization tier: EC2/QEMU-style full VMs. |
| INV-40-C032 | P0 | missing | Implementation & Configuration | Separate immutable artifacts from mutable configuration and state for Full virtualization tier. |
| INV-40-C033 | P0 | missing | Implementation & Configuration | Define declarative configuration and secure defaults for Full virtualization tier. |
| INV-40-C034 | P0 | partial | Implementation & Configuration | Validate configuration before activation and fail closed on security-critical errors. |
| INV-40-C035 | P1 | missing | Implementation & Configuration | Support site- and environment-specific configuration without rebuilding immutable artifacts. |
| INV-40-C036 | P0 | missing | Implementation & Configuration | Record configuration provenance, version, author, and activation time. |
| INV-40-C037 | P0 | missing | Implementation & Configuration | Apply atomic or transactional configuration updates where partial application is unsafe. |
| INV-40-C038 | P0 | missing | Implementation & Configuration | Define automatic and operator-driven rollback for failed Full virtualization tier changes. |
| INV-40-C039 | P0 | partial | Implementation & Configuration | Keep credentials and secret material out of ordinary Full virtualization tier configuration and diagnostics. |
| INV-40-C040 | P0 | missing | Implementation & Configuration | Provide a deterministic bootstrap path from an empty node/environment to healthy Full virtualization tier operation. |
| INV-40-C041 | P0 | partial | Security, Trust & Isolation | Threat-model Full virtualization tier against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse. |
| INV-40-C042 | P0 | missing | Security, Trust & Isolation | Apply least privilege to every identity and capability used by Full virtualization tier. |
| INV-40-C043 | P0 | missing | Security, Trust & Isolation | Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Full virtualization tier permits. |
| INV-40-C044 | P0 | missing | Security, Trust & Isolation | Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted. |
| INV-40-C045 | P0 | missing | Security, Trust & Isolation | Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Full virtualization tier. |
| INV-40-C046 | P0 | partial | Security, Trust & Isolation | Enforce tenant/workload isolation across Full virtualization tier execution, memory, state, network, and device boundaries as applicable. |
| INV-40-C047 | P0 | missing | Security, Trust & Isolation | Encrypt sensitive Full virtualization tier data in transit and at rest with managed key rotation. |
| INV-40-C048 | P0 | missing | Security, Trust & Isolation | Define safe behavior when identity, attestation, policy, key, or time services are unavailable. |
| INV-40-C049 | P0 | missing | Security, Trust & Isolation | Emit tamper-evident audit events for security-sensitive Full virtualization tier operations. |
| INV-40-C050 | P0 | partial | Security, Trust & Isolation | Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion. |
| INV-40-C051 | P0 | partial | Resilience & Failure Handling | Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Full virtualization tier. |
| INV-40-C052 | P0 | missing | Resilience & Failure Handling | Define automated health and stall detection thresholds for Full virtualization tier. |
| INV-40-C053 | P0 | missing | Resilience & Failure Handling | Implement bounded retry with backoff and jitter only where operations are safe to retry. |
| INV-40-C054 | P0 | missing | Resilience & Failure Handling | Implement admission control, load shedding, or circuit breaking to prevent Full virtualization tier failure cascades. |
| INV-40-C055 | P0 | missing | Resilience & Failure Handling | Define failover behavior without violating isolation, residency, or consistency requirements. |
| INV-40-C056 | P1 | missing | Resilience & Failure Handling | Provide degraded operation when noncritical dependencies are unavailable. |
| INV-40-C057 | P0 | partial | Resilience & Failure Handling | Define crash-consistency, restart, resume, or replay semantics for mutable Full virtualization tier state. |
| INV-40-C058 | P0 | partial | Resilience & Failure Handling | Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant. |
| INV-40-C059 | P0 | partial | Resilience & Failure Handling | Provide quarantine, freeze, disable, or isolation controls for unsafe Full virtualization tier behavior. |
| INV-40-C060 | P0 | missing | Resilience & Failure Handling | Run fault-injection tests proving Full virtualization tier recovery against documented objectives. |
| INV-40-C061 | P2 | missing | Performance & Resource Efficiency | Establish reproducible baselines for Full virtualization tier latency, throughput, startup, CPU, memory, storage, network, and power overhead. |
| INV-40-C062 | P2 | missing | Performance & Resource Efficiency | Define p50, p95, p99, and worst-case performance thresholds for Full virtualization tier. |
| INV-40-C063 | P2 | missing | Performance & Resource Efficiency | Measure Full virtualization tier under steady load, burst load, overload, scale-out, scale-in, and recovery. |
| INV-40-C064 | P2 | missing | Performance & Resource Efficiency | Measure per-workload and per-tenant overhead introduced by Full virtualization tier. |
| INV-40-C065 | P2 | missing | Performance & Resource Efficiency | Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Full virtualization tier. |
| INV-40-C066 | P2 | missing | Performance & Resource Efficiency | Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit. |
| INV-40-C067 | P0 | partial | Performance & Resource Efficiency | Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out. |
| INV-40-C068 | P2 | missing | Performance & Resource Efficiency | Measure power and thermal impact on constrained edge nodes where relevant. |
| INV-40-C069 | P2 | missing | Performance & Resource Efficiency | Define capacity models and saturation signals that predict when Full virtualization tier needs more resources. |
| INV-40-C070 | P2 | missing | Performance & Resource Efficiency | Block releases that regress approved Full virtualization tier startup, density, throughput, or tail-latency thresholds. |
| INV-40-C071 | P0 | missing | Observability & Explainability | Expose Full virtualization tier health, readiness, version, configuration, dependency status, and active capability set. |
| INV-40-C072 | P0 | missing | Observability & Explainability | Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use. |
| INV-40-C073 | P0 | missing | Observability & Explainability | Emit structured logs with stable node, tenant, workload, component, and operation identifiers. |
| INV-40-C074 | P0 | missing | Observability & Explainability | Propagate trace context across all relevant Full virtualization tier boundaries. |
| INV-40-C075 | P2 | missing | Observability & Explainability | Expose high-cardinality diagnostic detail safely without leaking tenant or secret data. |
| INV-40-C076 | P2 | missing | Observability & Explainability | Record the reason for every automated decision made by Full virtualization tier. |
| INV-40-C077 | P2 | missing | Observability & Explainability | Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints. |
| INV-40-C078 | P2 | missing | Observability & Explainability | Correlate Full virtualization tier events with application release lineage and the live infrastructure graph. |
| INV-40-C079 | P2 | missing | Observability & Explainability | Define telemetry retention, sampling, privacy, and export policy. |
| INV-40-C080 | P2 | missing | Observability & Explainability | Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect. |
| INV-40-C082 | P0 | partial | Testing & Certification | Create contract tests for every public Full virtualization tier interface. |
| INV-40-C083 | P0 | missing | Testing & Certification | Create integration tests with every supported adjacent layer and execution tier. |
| INV-40-C084 | P0 | missing | Testing & Certification | Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Full virtualization tier. |
| INV-40-C085 | P0 | missing | Testing & Certification | Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Full virtualization tier. |
| INV-40-C086 | P0 | partial | Testing & Certification | Create concurrency and race-condition tests for shared/distributed Full virtualization tier state. |
| INV-40-C087 | P0 | partial | Testing & Certification | Create security tests derived directly from the Full virtualization tier threat model. |
| INV-40-C088 | P2 | missing | Testing & Certification | Create benchmark, soak, burst, and fleet-scale tests appropriate to Full virtualization tier. |
| INV-40-C089 | P0 | missing | Testing & Certification | Create disaster, partition, reconnect, and degraded-control-plane tests. |
| INV-40-C090 | P0 | missing | Testing & Certification | Require machine-readable acceptance evidence before certifying a Full virtualization tier release for production. |
| INV-40-C091 | P0 | partial | Operations, Release & Governance | Define production SLOs, error budgets, and support commitments for Full virtualization tier. |
| INV-40-C092 | P0 | partial | Operations, Release & Governance | Define canary, staged rollout, rollback, and emergency-disable procedures for Full virtualization tier. |
| INV-40-C093 | P0 | missing | Operations, Release & Governance | Maintain a supported-version compatibility matrix for Full virtualization tier and adjacent dependencies. |
| INV-40-C094 | P0 | missing | Operations, Release & Governance | Define patching, vulnerability response, and end-of-life SLAs for Full virtualization tier. |
| INV-40-C095 | P0 | missing | Operations, Release & Governance | Provide backup, restore, migration, or reconstruction procedures for Full virtualization tier state where applicable. |
| INV-40-C096 | P0 | partial | Operations, Release & Governance | Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks. |
| INV-40-C097 | P0 | missing | Operations, Release & Governance | Define incident severity, paging, escalation, containment, and recovery procedures. |
| INV-40-C098 | P1 | missing | Operations, Release & Governance | Perform recurring access, policy, dependency, configuration, and architecture reviews. |
| INV-40-C099 | P0 | missing | Operations, Release & Governance | Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates. |
| INV-40-C100 | P0 | missing | Operations, Release & Governance | Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness. |

# Part I — Repository-level missing components

## REPO-001 — Package and pin the pk_core dependency

**Priority:** P0  
**Audit status:** missing  
**Observed gap:** pk_core is required by component.py/contract.py but is not bundled and there is no requirements/lock/package metadata declaring an installable version.

### Implementation checklist

- [ ] Choose the supported `pk_core` distribution source (internal package index, Git tag/commit, vendored package, or monorepo workspace) and document why that source is authoritative.
- [ ] Declare an explicit compatible version range for development and runtime; do not rely on an undeclared ambient installation.
- [ ] Generate a reproducible lock/constraints artifact containing exact transitive dependency versions and cryptographic hashes where the packaging tool supports them.
- [ ] Define the minimum supported `pk_core` API/ABI contract used by `component.py` and `contract.py`, including the imported symbols and behavioral assumptions.
- [ ] Add a startup/import compatibility check that reports a stable diagnostic when the installed `pk_core` version falls outside the supported range.
- [ ] Separate optional standalone-runtime operation from integration operation in package extras (for example, base package vs. `pk_core` integration extra) so dependency intent is explicit.
- [ ] Document offline installation/bootstrap behavior and the approved dependency cache/mirror for disconnected environments.
- [ ] Record license, provenance, publisher, source repository, integrity hash, and vulnerability-scanning expectations for `pk_core` in the dependency inventory/SBOM.

### Verification and acceptance checklist

- [ ] Create a clean virtual environment and prove installation from only declared metadata succeeds.
- [ ] Run standalone tests without `pk_core`, then integration tests with the minimum supported, maximum supported, and intentionally unsupported versions.
- [ ] Verify lockfile reproducibility by resolving/installing twice in clean environments and comparing package/version/hash manifests.
- [ ] Fail CI when `component.py` or `contract.py` imports a `pk_core` symbol that is not represented by the compatibility test.

### Required evidence / suggested artifacts

- [ ] `pyproject.toml` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `requirements.lock or uv.lock/poetry.lock` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `constraints.txt (if used)` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `docs/dependencies.md` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `tests/test_dependency_contract.py` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] Release evidence records the implementation commit and artifact digest that was actually verified.
- [ ] An accountable owner and reviewer approve closure of this component.

**Definition of done:** A clean checkout can deterministically install the declared integration dependency, compatibility is tested, unsupported versions fail clearly, and no hidden ambient dependency is required.

## REPO-002 — Restore or formally retire the MASTER.md source artifact

**Priority:** P1  
**Audit status:** missing  
**Observed gap:** README 4.1.0 claimed MASTER.md was bundled, but the file is absent. 4.2.0 corrects the claim rather than fabricating the missing source.

### Implementation checklist

- [ ] Determine whether `MASTER.md` is an authoritative source artifact, a generated artifact, or an obsolete historical reference.
- [ ] If authoritative, recover it from the controlled source history and add it without reconstructing unverifiable content.
- [ ] If retired, create an ADR that identifies the replacement source of truth (`CHECKLIST.json`, external specification, etc.) and records the retirement decision.
- [ ] Update every reference in README, audit, scripts, and CI so documentation cannot claim an artifact is bundled when it is not.
- [ ] Define ownership and change-control rules for the source artifact, including who may approve requirement changes and how generated derivatives are synchronized.
- [ ] Add a consistency check that fails CI when documentation references a required repository file that is absent.

### Verification and acceptance checklist

- [ ] Search the repository for stale `MASTER.md` references and verify each is accurate.
- [ ] Validate that the chosen source-of-truth artifact produces exactly the intended 100 requirement identifiers without duplication or loss.
- [ ] Record a source digest/revision identifier in release evidence so later audits can reproduce the requirement baseline.

### Required evidence / suggested artifacts

- [ ] `MASTER.md or docs/source-traceability.md` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `README.md` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `CHANGELOG.md` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `docs/adr/ADR-source-of-truth.md` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] Release evidence records the implementation commit and artifact digest that was actually verified.
- [ ] An accountable owner and reviewer approve closure of this component.

**Definition of done:** The authoritative requirements source is present or formally retired, all references are consistent, and releases capture a reproducible source revision/digest.

## REPO-003 — Implement a production hypervisor/provider adapter

**Priority:** P0  
**Audit status:** missing  
**Observed gap:** No QEMU/KVM/libvirt/cloud provider adapter exists; runtime.py is a deterministic reference model only.

### Implementation checklist

- [ ] Define a provider abstraction covering create, configure, start, stop, destroy, inspect, attach/detach device, console/log retrieval, and capability discovery.
- [ ] Implement at least one approved production backend (for example QEMU/KVM through libvirt) with exact pinned API/specification versions.
- [ ] Translate provider-native identifiers and state into stable INV-40 identifiers/states without leaking provider-specific ambiguity through the public contract.
- [ ] Perform host capability checks for CPU virtualization extensions, IOMMU/device passthrough features, firmware/UEFI, storage/network primitives, and required kernel modules before admission.
- [ ] Create VM resources transactionally; on mid-create failure, reconcile or roll back orphaned disks, network interfaces, processes/domains, leases, and device assignments.
- [ ] Enforce concrete device ownership at the provider boundary as well as in the in-memory reference model; never rely solely on process-local bookkeeping.
- [ ] Implement provider timeouts, cancellation, bounded retries for explicitly idempotent operations, and provider error normalization into the stable error catalog.
- [ ] Add lifecycle reconciliation so observed hypervisor state can repair stale controller state after process/node restart.
- [ ] Harden command/API invocation against argument injection and shell interpolation; use typed API bindings or argument vectors, not constructed shell strings.
- [ ] Define privilege separation: the control process should not run with unrestricted root/device/network authority when narrower helper capabilities can be used.

### Verification and acceptance checklist

- [ ] Run integration tests against an actual supported hypervisor in CI or a controlled hardware runner, including successful boot and clean teardown.
- [ ] Force provider failures at each create/start/stop/destroy phase and verify no leaked domains, devices, storage artifacts, or network state remain.
- [ ] Attempt duplicate passthrough/device assignment from two VMs and verify the provider-level fencing rejects the second claimant.
- [ ] Restart the controller during active VMs and verify reconciliation preserves or safely recovers lifecycle/device ownership.
- [ ] Collect end-to-end evidence proving the VM has its own kernel/full device model and hardware acceleration is active.

### Required evidence / suggested artifacts

- [ ] `inv40_full_virtualization_tier/providers/base.py` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `inv40_full_virtualization_tier/providers/qemu_libvirt.py` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `inv40_full_virtualization_tier/providers/cloud.py (if supported)` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `tests/integration/providers/` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `docs/provider-contract.md` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] Release evidence records the implementation commit and artifact digest that was actually verified.
- [ ] An accountable owner and reviewer approve closure of this component.

**Definition of done:** At least one real hypervisor/provider is supported, integration-tested on real virtualization hardware, reconciles state safely, and enforces isolation beyond the reference model.

## REPO-004 — Add deterministic build/install metadata

**Priority:** P0  
**Audit status:** missing  
**Observed gap:** No pyproject.toml/setup metadata, dependency lock, or reproducible environment definition is present.

### Implementation checklist

- [ ] Create PEP 517/518-compliant package metadata with package name, version source, supported Python versions, dependencies, optional extras, entry points, and included data files.
- [ ] Use a single authoritative version source and add a test preventing divergence among `VERSION`, package metadata, and `__version__`.
- [ ] Lock transitive dependencies and define hash-verified installation for release builds.
- [ ] Define reproducible build inputs, locale/timezone assumptions, toolchain versions, and environment variables.
- [ ] Ensure source distributions/wheels contain all required runtime, schema, license, and documentation artifacts but exclude caches, secrets, local evidence, and build junk.
- [ ] Generate an SBOM and provenance/attestation for release artifacts.
- [ ] Provide Windows- and Linux-safe bootstrap commands/scripts if both are supported; fail early with actionable diagnostics for unsupported systems.

### Verification and acceptance checklist

- [ ] Build wheel and sdist in a clean isolated environment; install each into a second clean environment and run the full standalone test suite.
- [ ] Compare repeated builds under controlled inputs and document whether byte-for-byte reproducibility is achieved; otherwise enumerate nondeterministic fields.
- [ ] Inspect archive contents automatically for missing required files, path traversal, secret material, and unexpected binaries.
- [ ] Verify package uninstall leaves no unmanaged persistent state.

### Required evidence / suggested artifacts

- [ ] `pyproject.toml` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `lockfile` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `MANIFEST.in only if needed` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `README installation section` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `scripts/bootstrap.*` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `SBOM` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] Release evidence records the implementation commit and artifact digest that was actually verified.
- [ ] An accountable owner and reviewer approve closure of this component.

**Definition of done:** The project builds and installs from declared metadata in a clean environment with reproducible dependencies, consistent versioning, and verified release contents.

## REPO-005 — Add license and notice artifacts

**Priority:** P0  
**Audit status:** missing  
**Observed gap:** No repository license/notice file is present in the supplied archive.

### Implementation checklist

- [ ] Select and approve the repository license with the project owner/legal process; do not infer a license from unrelated repositories.
- [ ] Add the complete license text at repository root and ensure package/build metadata declares the same license expression.
- [ ] Create a NOTICE/third-party attribution inventory for bundled or redistributed code, schemas, assets, and dependencies where required.
- [ ] Identify generated or vendored files and preserve upstream copyright/license notices.
- [ ] Add SPDX identifiers to source files if project policy requires them.
- [ ] Configure dependency/license scanning and a deny/approval policy for incompatible or unknown licenses.

### Verification and acceptance checklist

- [ ] Run an automated license inventory over direct/transitive dependencies and reconcile unknown entries.
- [ ] Verify release archives include LICENSE/NOTICE artifacts.
- [ ] Fail CI when a new dependency introduces an unapproved license or missing attribution.

### Required evidence / suggested artifacts

- [ ] `LICENSE` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `NOTICE` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `THIRD_PARTY_NOTICES.md` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `SBOM` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] Release evidence records the implementation commit and artifact digest that was actually verified.
- [ ] An accountable owner and reviewer approve closure of this component.

**Definition of done:** The repository and distributable artifacts carry an approved license, required notices, and automated third-party license evidence.

## REPO-006 — Create CI, release, signing, and automated quality gates

**Priority:** P0  
**Audit status:** missing  
**Observed gap:** No continuous-integration, packaging, signing, release, or automated gate workflow is present.

### Implementation checklist

- [ ] Run lint/static analysis, bytecode compilation, unit tests, optimized-Python tests, integration tests, security scans, dependency checks, and packaging validation on every change.
- [ ] Define protected release branches/tags and require reviewed, passing checks before release promotion.
- [ ] Build release artifacts only in controlled CI; attach provenance/attestation, SBOM, checksums, and signatures using protected signing identity/keyless signing as policy permits.
- [ ] Make the production gate machine-readable and fail closed when mandatory evidence is absent, skipped unexpectedly, stale, or refers to a different commit/artifact hash.
- [ ] Add compatibility matrix jobs for supported Python/platform/provider combinations and dedicated hardware-backed jobs for virtualization tests.
- [ ] Add performance-regression jobs using versioned baselines and approved tolerance thresholds.
- [ ] Archive test logs, coverage, scan results, gate result, artifact digests, and release metadata under a retention policy.
- [ ] Prevent CI secrets from being exposed to untrusted pull-request code and minimize workflow token permissions.

### Verification and acceptance checklist

- [ ] Deliberately break a unit test, skip mandatory evidence, change a locked dependency, and exceed a performance/security threshold; verify each condition blocks release.
- [ ] Verify produced artifact signatures/checksums against the exact uploaded release asset.
- [ ] Re-run the release verification script outside CI against downloaded artifacts and obtain the same GO/NO_GO result.

### Required evidence / suggested artifacts

- [ ] `.github/workflows/ci.yml or equivalent` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `.github/workflows/release.yml` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `scripts/verify_release.py` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `release/evidence-schema.json` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] `docs/release-process.md` exists (or an approved equivalent) and is linked from the traceability matrix.
- [ ] Release evidence records the implementation commit and artifact digest that was actually verified.
- [ ] An accountable owner and reviewer approve closure of this component.

**Definition of done:** Every release is reproducibly built, tested, scanned, signed/attested, and blocked automatically when mandatory evidence or thresholds are not satisfied.

# Part II — Open INV-40 requirements

# Architecture & Scope

## INV-40-C005 — Document assumptions Full virtualization tier makes about nodes, runtimes, networks, storage, and control planes.

**Priority:** P1  
**Audit status:** partial  
**Current evidence/gap:** Assumptions cover guest trust, boot time, and memory, but not the required network, storage, runtime, node, and control-plane assumptions.

### Design and implementation checklist

- [ ] Create an assumptions register covering host CPU/firmware/IOMMU, supported operating systems, hypervisor runtime, network underlay/overlay, storage semantics, DNS/NTP/time, control-plane reachability, identity/key services, and site power/thermal constraints.
- [ ] Classify each assumption as hard prerequisite, degraded-mode condition, tunable constraint, or optimization assumption.
- [ ] For each hard prerequisite, define a machine-detectable preflight check and stable refusal code.
- [ ] For each environmental assumption, identify the owner/source of truth and the maximum tolerated staleness.
- [ ] Document what happens when an assumption becomes false after VM start, including containment and reconciliation.
- [ ] Update architecture documentation and diagrams so the new control/boundary is visible to reviewers.
- [ ] Identify ownership and dependencies introduced by the change and add them to the traceability inventory.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Perform architecture review against the current trust-boundary/dependency diagram and record approval.
- [ ] Verify repository documentation and implementation do not contradict the newly approved scope.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/architecture/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/adr/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `OWNERS.md or CODEOWNERS` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `traceability/requirements.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C009 — Assign an accountable owner and escalation path for Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Accountable owner and escalation path.

### Design and implementation checklist

- [ ] Name a service owner, code owner, security owner, operations owner, and release approver; use role aliases rather than only individual names where practical.
- [ ] Define primary/secondary escalation paths, on-call coverage, paging targets, and maximum acknowledgement/escalation intervals by severity.
- [ ] Document decision authority for emergency disable, rollback, risk acceptance, and security isolation actions.
- [ ] Add CODEOWNERS/reviewer rules for runtime, provider, security policy, and release workflow changes.
- [ ] Exercise the escalation path in a tabletop or game-day and capture evidence of the handoff.
- [ ] Update architecture documentation and diagrams so the new control/boundary is visible to reviewers.
- [ ] Identify ownership and dependencies introduced by the change and add them to the traceability inventory.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Perform architecture review against the current trust-boundary/dependency diagram and record approval.
- [ ] Verify repository documentation and implementation do not contradict the newly approved scope.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/architecture/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/adr/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `OWNERS.md or CODEOWNERS` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `traceability/requirements.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C010 — Approve an architecture decision record for Full virtualization tier, its technologies (EC2/QEMU-style full VMs), and its function (Maximum legacy compatibility/compliance isolation).

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Approved architecture decision record for EC2/QEMU-style full VMs and the compatibility/isolation rationale.

### Design and implementation checklist

- [ ] Write an ADR stating the decision to provide EC2/QEMU-style full-machine virtualization for hostile/foreign guest compatibility and compliance isolation.
- [ ] Record considered alternatives such as containers, microVMs, WASM/SFI, bare metal, and managed cloud instances, with explicit rejection/selection criteria.
- [ ] Document trust boundaries, device model/attack-surface consequences, expected boot/memory cost, operational complexity, and portability trade-offs.
- [ ] Define the hardware virtualization primitive and any IOMMU/secure-boot/TPM requirements as architectural constraints.
- [ ] Include architecture/context and deployment diagrams and record approvers plus supersession rules.
- [ ] Update architecture documentation and diagrams so the new control/boundary is visible to reviewers.
- [ ] Identify ownership and dependencies introduced by the change and add them to the traceability inventory.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Perform architecture review against the current trust-boundary/dependency diagram and record approval.
- [ ] Verify repository documentation and implementation do not contradict the newly approved scope.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/architecture/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/adr/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `OWNERS.md or CODEOWNERS` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `traceability/requirements.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Requirements & Semantics

## INV-40-C011 — Translate the source function of Full virtualization tier — Maximum legacy compatibility/compliance isolation — into testable SHALL-level requirements.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Mandatory behavior exists as prose, but there is no normative SHALL-level requirements specification with identifiers and acceptance criteria.

### Design and implementation checklist

- [ ] Create a normative requirements specification using unique immutable requirement IDs and RFC 2119-style SHALL/SHALL NOT language.
- [ ] Convert “maximum legacy compatibility/compliance isolation” into measurable obligations for guest OS opacity, full device model, hardware acceleration, tenant isolation, device exclusivity, and accounting.
- [ ] Attach explicit preconditions, inputs, expected outputs, failure behavior, and acceptance thresholds to every normative requirement.
- [ ] Separate functional, security, performance, operational, and governance requirements and identify which are release-blocking.
- [ ] Map every requirement to implementation component(s), tests, and evidence placeholders before claiming completion.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C012 — Define functional requirements for Full virtualization tier across cloud, datacenter, near-edge, and far-edge contexts where applicable.

**Priority:** P1  
**Audit status:** missing  
**Current evidence/gap:** Cloud/datacenter/near-edge/far-edge functional requirement variants.

### Design and implementation checklist

- [ ] Define deployment profiles for cloud, datacenter, near-edge, and far-edge, explicitly marking unsupported profiles rather than leaving applicability ambiguous.
- [ ] For each supported profile, specify host prerequisites, networking, storage, identity/key access, image distribution, observability, update strategy, and failure-domain model.
- [ ] Document provider-specific constraints such as nested virtualization, passthrough availability, instance families, maintenance events, and quota behavior.
- [ ] Define disconnected/low-bandwidth variants for edge where relevant and state the minimum local services required to continue operating.
- [ ] Create profile-specific conformance tests or admission checks.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C013 — Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Some SLOs and ceilings exist, but availability, durability/consistency where applicable, and comprehensive non-functional thresholds are not defined.

### Design and implementation checklist

- [ ] Define latency/startup, availability, recovery, durability, consistency, isolation, determinism, and capacity NFRs with units and measurement windows.
- [ ] Specify which NFRs apply per operation (`create`, `start`, `stop`, `destroy`, reconcile, attach/detach, migration if supported).
- [ ] Define SLI calculation rules, excluded maintenance windows, percentile methodology, and error-budget policy.
- [ ] Establish hard safety ceilings separately from aspirational performance targets.
- [ ] Record measurement environment, workload shape, and hardware class so thresholds are reproducible and not context-free.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C014 — Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Full virtualization tier.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Runtime returns ok/degraded for boot budget and raises terminal operational errors, but success/partial/retryable/terminal semantics are not comprehensively specified.

### Design and implementation checklist

- [ ] Define a finite result taxonomy: success, accepted/in-progress if asynchronous, partial success, degraded success, retryable failure, terminal failure, policy rejection, and dependency unavailable.
- [ ] Assign each public operation and error code to exactly one result class and state whether side effects may have occurred.
- [ ] Define client behavior for each class, including retry eligibility, reconciliation, compensation, and operator escalation.
- [ ] Specify how degraded state is cleared and how partial operations expose remaining work.
- [ ] Prohibit ambiguous “success with hidden failure” responses; machine status and human message must agree.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C016 — Define versioning and backward-compatibility requirements for Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Versioning and backward-compatibility policy for code and wire schemas.

### Design and implementation checklist

- [ ] Adopt semantic versioning or another documented scheme separately for package code, public schemas, provider adapters, and persisted state formats.
- [ ] Define backward/forward compatibility guarantees for each major/minor change type.
- [ ] Establish a deprecation policy with minimum notice window, telemetry for deprecated use, and removal criteria.
- [ ] Define schema negotiation or explicit rejection for unsupported peer versions.
- [ ] Add migration strategy for persisted configuration/state when versions change.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C017 — Define capacity ceilings, quotas, and fairness semantics relevant to Full virtualization tier.

**Priority:** P1  
**Audit status:** partial  
**Current evidence/gap:** Per-guest resident memory is capped, but quotas, fleet capacity ceilings, and fairness semantics are absent.

### Design and implementation checklist

- [ ] Define per-VM, per-tenant, per-node, per-site, and fleet ceilings for vCPU, memory, storage, network, devices, concurrent lifecycle operations, and VM count.
- [ ] Implement admission accounting using reserved and observed resources; prevent overcommit where it would violate isolation/compliance.
- [ ] Define fairness policy (strict quota, weighted fair share, priority classes, reservations) and starvation prevention.
- [ ] Expose quota usage and denial reason codes to operators/clients.
- [ ] Test quota races under concurrent admission and ensure the ceiling cannot be oversubscribed by TOCTOU behavior.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C018 — Define behavior when network connectivity is intermittent or absent.

**Priority:** P1  
**Audit status:** missing  
**Current evidence/gap:** Disconnected/intermittent-network behavior.

### Design and implementation checklist

- [ ] Classify operations as locally executable, cacheable, queueable, or prohibited when control-plane/network connectivity is absent.
- [ ] Define maximum offline duration, lease TTL behavior, credential/key validity rules, and stale-policy handling.
- [ ] Persist only the minimum restart-safe queue/state needed for disconnected operation and cap its growth.
- [ ] Specify reconciliation ordering and conflict resolution after reconnect, including duplicate/late command handling.
- [ ] Create deterministic refusal behavior for operations that cannot safely proceed offline.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C019 — Define precedence rules when Full virtualization tier requirements conflict with security, residency, SLO, or cost constraints.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Conflict-precedence policy for security, residency, SLO, and cost constraints.

### Design and implementation checklist

- [ ] Create a precedence matrix covering security/isolation, legal/residency, safety, correctness, SLO, availability, performance, and cost.
- [ ] State non-overridable constraints (for example, never weaken hardware-isolation or residency controls to meet latency/cost).
- [ ] Define who may authorize an exception, required evidence, scope, expiration, and audit logging.
- [ ] Encode enforceable precedence rules in admission/policy logic rather than relying only on prose.
- [ ] Test representative conflicts and verify the selected outcome and reason are recorded.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C020 — Maintain a requirements traceability matrix from each Full virtualization tier requirement to implementation and verification evidence.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Requirements traceability matrix mapping requirements to implementation and verification evidence.

### Design and implementation checklist

- [ ] Create a machine-readable requirements traceability matrix keyed by every `INV-40-Cxxx` ID.
- [ ] Link each requirement to design/ADR, code/module, configuration/policy, test IDs, evidence files, owner, and current status.
- [ ] Require evidence hashes/commit IDs so references cannot silently drift.
- [ ] Fail release gating when a mandatory requirement has no implementation link, no verification evidence, stale evidence, or an unapproved waiver.
- [ ] Generate human-readable coverage summaries from the same matrix to avoid divergent inventories.
- [ ] Use normative, testable language and assign stable requirement identifiers to newly defined behavior.
- [ ] Define edge cases and prohibited behavior, not only the nominal success path.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Create positive, boundary, and negative acceptance tests for the new normative semantics.
- [ ] Verify requirement-to-test traceability is complete and current.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `requirements/INV40_REQUIREMENTS.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `requirements/traceability.json` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/acceptance/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Interfaces & Integration

## INV-40-C021 — Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Full virtualization tier.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Contract lists create/boot/stop/destroy/error logical interfaces, but actual hypervisor, device, event, file, RPC, and control-plane boundaries are not fully enumerated.

### Design and implementation checklist

- [ ] Inventory every northbound/southbound/east-west boundary: Python API, CLI, RPC/HTTP, events, files, sockets, hypervisor API, device/ioctl, image store, network, storage, identity/key/policy service, and operator interface.
- [ ] For each boundary record direction, transport, endpoint, caller/callee identity, trust level, schema, authentication, authorization, timeout, retry, rate/size limits, and ownership.
- [ ] Mark internal-only boundaries and prevent accidental public exposure.
- [ ] Document host-kernel/hypervisor/device trust crossings explicitly because they are security boundaries even when no network protocol is involved.
- [ ] Keep the boundary inventory version-controlled and validated against generated API/schema definitions where possible.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C022 — Use versioned typed schemas for all externally visible Full virtualization tier contracts.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** String schema identifiers exist, but there are no versioned schema definitions or generated/validated typed wire contracts.

### Design and implementation checklist

- [ ] Replace prose-only `PK_FULL_VM/*` strings with concrete versioned schemas (JSON Schema/Protobuf/OpenAPI/Pydantic/dataclass contract or equivalent).
- [ ] Define required/optional fields, types, numeric bounds, enums, identifier formats, unknown-field policy, and canonical serialization.
- [ ] Generate or centrally implement validators used by both producer and consumer paths.
- [ ] Define additive vs. breaking schema evolution rules and fixture versions.
- [ ] Validate outbound responses as well as inbound requests so implementation drift is detected.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C023 — Define authentication requirements at each Full virtualization tier boundary.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Authentication requirements for every boundary.

### Design and implementation checklist

- [ ] Identify the authenticating principal at every control, provider, node, artifact, and operator boundary.
- [ ] Select approved mechanisms such as mTLS workload identity, signed service tokens, cloud IAM, SSH certificates, or local peer credentials as appropriate.
- [ ] Define credential issuance, rotation, revocation, expiry, clock-skew, and bootstrap trust.
- [ ] Bind authenticated identity to stable audit fields and reject anonymous/ambiguous principals on privileged operations.
- [ ] Fail closed when authentication infrastructure is unavailable unless an explicitly approved offline mode applies.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C024 — Define authorization and explicit capability requirements at each Full virtualization tier boundary.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Authorization/capability model for every boundary.

### Design and implementation checklist

- [ ] Define an authorization model covering tenant, project/site, VM, device, image, network, storage, lifecycle action, console/debug access, and emergency operations.
- [ ] Use deny-by-default policy and narrow capabilities/scopes; avoid role grants that implicitly provide unrelated host authority.
- [ ] Separate duties for deployer, operator, security responder, release approver, and platform administrator.
- [ ] Evaluate authorization at the authoritative enforcement point before side effects and include policy revision in decision evidence.
- [ ] Test cross-tenant and privilege-escalation attempts, stale grants, revoked access, and confused-deputy scenarios.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C025 — Define timeout, cancellation, retry, idempotency, and backpressure semantics for Full virtualization tier.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Destroy is idempotent and lifecycle errors are bounded, but timeout, cancellation, retry, and backpressure semantics are absent.

### Design and implementation checklist

- [ ] Define per-operation timeout budgets including provider call, network, storage, and cleanup phases.
- [ ] Specify cancellation semantics: which operations are cancellable, when cancellation becomes best-effort, and how callers discover final state.
- [ ] Classify operations as naturally idempotent, idempotent with request key, retryable after reconcile, or never automatically retryable.
- [ ] Implement idempotency/request tokens for create-like operations so retries cannot duplicate VMs/resources.
- [ ] Define bounded queues, client/server backpressure signals, overload responses, and retry-after guidance.
- [ ] Use deadline propagation so nested provider operations cannot outlive the caller budget indefinitely.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C026 — Define structured failure codes and machine-readable error details for Full virtualization tier.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Operational VM failures expose PK_FULL_VM_ERROR/1 codes; validation/configuration failures still use generic Python exceptions and no complete error catalog exists.

### Design and implementation checklist

- [ ] Create a complete error catalog with stable code, category, retryability, HTTP/RPC mapping if applicable, operator action, and security disclosure level.
- [ ] Convert validation/configuration/provider errors from generic Python exceptions into typed domain failures at public boundaries.
- [ ] Include structured context such as operation ID, VM ID, provider, dependency, policy decision ID, and safe diagnostic details.
- [ ] Preserve causal chains internally while redacting secrets/tenant-private data from user-visible messages.
- [ ] Add tests preventing accidental code reuse or incompatible semantic changes to existing error identifiers.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C027 — Define compatibility behavior when peers use different supported versions.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Mixed-version compatibility behavior.

### Design and implementation checklist

- [ ] Define the supported peer/provider/schema version matrix and the negotiation mechanism for versioned interfaces.
- [ ] Specify downgrade behavior and explicitly forbid silent downgrade when it weakens security/isolation semantics.
- [ ] Define rolling-upgrade order and mixed-version windows for controllers, nodes, adapters, and schemas.
- [ ] Add compatibility shims only with bounded lifetime and explicit tests.
- [ ] Reject unsupported combinations before mutating state and return a stable incompatibility code.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C028 — Document payload, concurrency, queue, connection, or resource limits at Full virtualization tier interfaces.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Boot and resident-memory bounds exist, but payload, queue, concurrency, connection, and broader resource limits are not specified.

### Design and implementation checklist

- [ ] Define maximum request/response sizes, device counts, metadata lengths, image references, and diagnostic payloads.
- [ ] Set connection/session limits, concurrent operations per VM/node/tenant, queue depths, worker pools, and provider-call concurrency.
- [ ] Bound in-memory buffers and streamed data; avoid unbounded reads from sockets/files/provider output.
- [ ] Define overload response and observability for every enforced limit.
- [ ] Test just-below, at-limit, and over-limit behavior including concurrent races.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C029 — Provide reference examples and conformance fixtures for Full virtualization tier.

**Priority:** P1  
**Audit status:** missing  
**Current evidence/gap:** Reference examples and conformance fixtures.

### Design and implementation checklist

- [ ] Create canonical request/response/error fixtures for every public operation and schema version.
- [ ] Include positive, boundary, invalid, degraded, retryable, terminal, and compatibility examples.
- [ ] Provide a minimal provider/mock fixture and at least one real-provider fixture showing expected normalization.
- [ ] Version fixtures and make contract tests consume them rather than duplicating handwritten expectations.
- [ ] Document how downstream consumers can run the fixture suite as a conformance test.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C030 — Create automated integration tests proving Full virtualization tier interoperates with adjacent architectural layers.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Automated adjacent-layer integration tests.

### Design and implementation checklist

- [ ] Identify adjacent layers (`INV-23`, `PLN-04`, `INV-32`, `INV-33`, plus identity, storage, network, image, policy, telemetry services actually supported).
- [ ] Create integration environments using real interfaces or production-faithful emulators for each supported adjacency.
- [ ] Test success, rejected admission, dependency timeout, version mismatch, restart/reconcile, and cleanup across each boundary.
- [ ] Verify tenant/context/correlation identity propagates end-to-end.
- [ ] Gate releases on mandatory adjacency integration tests and surface skipped tests as non-passing evidence unless explicitly waived.
- [ ] Keep public contract behavior provider-neutral and versioned; provider-specific details belong behind adapters.
- [ ] Specify security, limits, timeout/retry behavior, and failure semantics for the interface, not only field shape.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run producer/consumer contract tests and at least one failure/timeout/version-mismatch integration case.
- [ ] Validate that unsupported/malformed inputs fail before unsafe side effects.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/interfaces.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `schemas/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/providers/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Implementation & Configuration

## INV-40-C031 — Select and pin approved implementations, versions, or specifications for Full virtualization tier: EC2/QEMU-style full VMs.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Pinned/approved hypervisor/provider implementations and versions (for example QEMU/KVM/libvirt or cloud API versions).

### Design and implementation checklist

- [ ] Choose the approved hypervisor/provider stack(s) and pin exact supported versions/ranges (QEMU, KVM kernel, libvirt, cloud API/SDK, firmware, virtio specifications as applicable).
- [ ] Publish minimum host kernel/CPU/firmware requirements and required feature flags.
- [ ] Document security support lifecycle/CVE response expectations for each pinned component.
- [ ] Maintain compatibility tests before accepting a new provider/hypervisor version.
- [ ] Prevent unapproved runtime/provider versions from silently entering production through capability/admission checks.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C032 — Separate immutable artifacts from mutable configuration and state for Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Immutable-artifact versus mutable-config/state separation.

### Design and implementation checklist

- [ ] Classify repository/package artifacts as immutable code, immutable schemas/policies, mutable configuration, secrets, ephemeral runtime state, and durable control state.
- [ ] Place mutable state outside the installed package/read-only image and define ownership/permissions for each storage location.
- [ ] Use content-addressed or versioned immutable artifacts for releases/images where practical.
- [ ] Prevent runtime code from editing its own package/release files.
- [ ] Document persistence/backup requirements and cleanup lifecycle for each mutable state class.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C033 — Define declarative configuration and secure defaults for Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Declarative configuration schema and secure defaults.

### Design and implementation checklist

- [ ] Define a typed declarative configuration schema covering provider selection, resource ceilings, device policy, image sources, network/storage integration, timeouts, observability, and security controls.
- [ ] Assign secure defaults; dangerous/experimental features must require explicit opt-in.
- [ ] Define required vs optional fields, ranges, enums, cross-field invariants, and unknown-key behavior.
- [ ] Support configuration layering with deterministic precedence and a way to render the effective configuration.
- [ ] Version the configuration schema and provide migration/deprecation rules.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C034 — Validate configuration before activation and fail closed on security-critical errors.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Runtime inputs fail closed, but there is no declarative configuration subsystem to validate before activation.

### Design and implementation checklist

- [ ] Validate syntax, types, ranges, cross-field invariants, referenced resources, provider capabilities, and security policy before activation.
- [ ] Perform dry-run/preflight validation without mutating active runtime state.
- [ ] Fail closed on invalid identity, isolation, key, device, network, storage, or provider-security configuration.
- [ ] Return structured validation errors with precise field paths and remediation hints.
- [ ] Add negative tests proving invalid configuration cannot partially activate.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C035 — Support site- and environment-specific configuration without rebuilding immutable artifacts.

**Priority:** P1  
**Audit status:** missing  
**Current evidence/gap:** Site/environment-specific configuration without rebuild.

### Design and implementation checklist

- [ ] Define configuration overlays for environment/site/host class without recompiling or rebuilding the immutable artifact.
- [ ] Keep site-local values in controlled configuration stores/files and reference secrets indirectly.
- [ ] Document merge/precedence semantics and prohibit ambiguous duplicate keys.
- [ ] Provide validation that an overlay is compatible with the package/provider version before activation.
- [ ] Test two or more site profiles from the same immutable artifact and compare effective configuration evidence.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C036 — Record configuration provenance, version, author, and activation time.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Configuration provenance/version/author/activation-time recording.

### Design and implementation checklist

- [ ] Assign each configuration revision a stable ID/hash and schema version.
- [ ] Record author/automation identity, source repository/path, commit/digest, approval reference, activation timestamp, target scope, and previous revision.
- [ ] Expose active configuration revision in health/diagnostic output.
- [ ] Emit immutable audit events for configuration proposal, validation, activation, rollback, and rejection.
- [ ] Retain sufficient history to reconstruct the effective configuration for any incident/release window.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C037 — Apply atomic or transactional configuration updates where partial application is unsafe.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Atomic/transactional configuration update mechanism.

### Design and implementation checklist

- [ ] Identify configuration changes that span multiple resources or enforcement points and would be unsafe if partially applied.
- [ ] Implement stage/validate/commit semantics or a versioned desired-state pointer so readers observe either old or new configuration, not a mixture.
- [ ] Use compare-and-swap/revision checks to prevent lost updates from concurrent operators/controllers.
- [ ] Define rollback/compensation if commit fails after partial external side effects.
- [ ] Crash-test updates at every transition and verify recovery chooses a single coherent revision.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C038 — Define automatic and operator-driven rollback for failed Full virtualization tier changes.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Automatic and operator-driven configuration rollback.

### Design and implementation checklist

- [ ] Define automatic rollback triggers for failed health checks, security regression, provider incompatibility, and performance/SLO threshold breach.
- [ ] Provide an operator rollback command/workflow referencing a known-good immutable artifact and configuration revision.
- [ ] Validate rollback compatibility with persisted state/schema before activation.
- [ ] Preserve audit evidence linking failed change, rollback decision, resulting version, and unresolved residue.
- [ ] Exercise rollback in CI/staging and during periodic game days.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C039 — Keep credentials and secret material out of ordinary Full virtualization tier configuration and diagnostics.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** The repository currently contains no embedded credentials, but there is no explicit secret/configuration/diagnostic handling policy or test.

### Design and implementation checklist

- [ ] Define secret classes and approved storage/transport mechanisms; configurations should contain references/handles rather than plaintext secret values.
- [ ] Prevent secrets from appearing in logs, exceptions, trace attributes, metrics labels, crash dumps, test fixtures, repository history, or release artifacts.
- [ ] Use least-privilege secret access with short-lived credentials and rotation support.
- [ ] Add automated secret scanning pre-commit/CI and redaction tests for diagnostic paths.
- [ ] Document secure local-development and break-glass secret handling separately from production.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C040 — Provide a deterministic bootstrap path from an empty node/environment to healthy Full virtualization tier operation.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Deterministic bootstrap/install path from an empty environment; pk_core and packaging metadata are not bundled.

### Design and implementation checklist

- [ ] Define a clean-machine bootstrap procedure including OS prerequisites, Python/toolchain, virtualization packages, kernel modules, permissions, package installation, configuration, provider setup, and initial trust material.
- [ ] Make bootstrap idempotent and safe to rerun; detect already-satisfied prerequisites.
- [ ] Provide preflight checks with explicit PASS/FAIL diagnostics before mutating the host.
- [ ] Support an offline/restricted-network bootstrap path if that is an intended deployment context.
- [ ] End bootstrap with automated readiness/conformance verification and evidence capture.
- [ ] Prefer declarative, versioned configuration and deterministic bootstrap over environment-dependent implicit behavior.
- [ ] Ensure partial failure cannot leave an untracked or insecure resource/configuration state.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Exercise clean install/bootstrap plus upgrade/rollback on a fresh environment.
- [ ] Verify effective configuration/state can be reconstructed from declared artifacts and provenance.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `pyproject.toml` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `config/defaults.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `scripts/bootstrap.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/config/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Security, Trust & Isolation

## INV-40-C041 — Threat-model Full virtualization tier against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** contract.py lists four threats, but no complete threat model covers supply chain, control-plane abuse, side channels, identity, network, storage, or host compromise.

### Design and implementation checklist

- [ ] Expand the threat model to assets, actors, trust boundaries, entry points, abuse cases, and security assumptions for guest, host, control plane, provider, supply chain, network, storage, identity/key services, and operators.
- [ ] Cover VMM/hypervisor escape, malicious device emulation, DMA/IOMMU failure, image tampering, compromised controller, API abuse, replay, downgrade, side channel, denial of service, and supply-chain compromise.
- [ ] Score or prioritize threats using the organization’s chosen risk method and assign an owner/mitigation status.
- [ ] Map each accepted threat to preventive/detective controls and concrete tests.
- [ ] Review the threat model whenever trust boundaries/provider versions/device capabilities change.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C042 — Apply least privilege to every identity and capability used by Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Least-privilege identities/capabilities for the real virtualization implementation.

### Design and implementation checklist

- [ ] Inventory every runtime identity (controller, node agent, hypervisor helper, provider service account, CI/release identity, operator role).
- [ ] Grant only the filesystem, device, network, kernel, cloud, secret, and API permissions required by each identity.
- [ ] Split privileged operations into narrow helpers/capabilities rather than running the full control process as root/administrator.
- [ ] Remove wildcard cloud/IAM permissions and broad device access; scope permissions to tenant/site/resource where supported.
- [ ] Continuously test denied operations to prove privilege boundaries remain effective.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C043 — Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Full virtualization tier permits.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Ambient filesystem/network/device/kernel/secret authority reduction for the real hypervisor/control-plane integration.

### Design and implementation checklist

- [ ] Run the control process with a minimal filesystem view, read-only code, dedicated writable state directories, and restrictive OS permissions.
- [ ] Restrict outbound network destinations/ports to approved dependencies and deny unnecessary inbound listeners.
- [ ] Expose only required `/dev` devices/ioctls and kernel capabilities to virtualization helpers; isolate passthrough operations from ordinary control logic.
- [ ] Use sandboxing/service hardening (namespaces, seccomp, AppArmor/SELinux, systemd hardening, Windows service restrictions, or platform equivalent).
- [ ] Keep secret mounts/handles scoped to the component and operation that requires them, then revoke/close promptly.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C044 — Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Authentication of nodes, peers, artifacts, providers, and control-plane actors.

### Design and implementation checklist

- [ ] Establish trust roots for node identity, service identity, provider APIs, artifact registries, and operator authentication.
- [ ] Verify identity before accepting node registration, provider response, image/config artifact, or privileged command.
- [ ] Bind node identity to attested host attributes where required by compliance/isolation policy.
- [ ] Support revocation and compromised-credential containment with bounded propagation time.
- [ ] Log authentication success/failure with safe principal and reason codes.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C045 — Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Artifact signature/digest/provenance/version verification.

### Design and implementation checklist

- [ ] Require cryptographic digest verification for VM images, firmware, policy bundles, plugins/adapters, package artifacts, and configuration bundles as applicable.
- [ ] Verify signatures/attestations against an approved trust policy before use; do not trust filename/tag alone.
- [ ] Record builder/source revision, dependency/SBOM provenance, signature identity, and verification result in release/runtime evidence.
- [ ] Define an allowlist/approval policy for versions and provenance predicates.
- [ ] Test tampered, unsigned, expired/revoked, wrong-subject, and downgraded artifacts and verify fail-closed behavior.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C046 — Enforce tenant/workload isolation across Full virtualization tier execution, memory, state, network, and device boundaries as applicable.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Concrete device-instance exclusivity is now enforced in-process, but execution, memory, network, persistent-state, IOMMU, and hypervisor isolation are not implemented here.

### Design and implementation checklist

- [ ] Enforce CPU/memory isolation through the selected hardware virtualization primitive and supported hypervisor configuration.
- [ ] Enforce storage isolation with per-tenant/VM volumes, access controls, secure deletion/rekeying, and snapshot policy.
- [ ] Enforce network isolation with explicit tenant segmentation/security policy and anti-spoofing at the authoritative data-plane point.
- [ ] Enforce DMA/device isolation using IOMMU groups and validate passthrough safety before assignment.
- [ ] Ensure persistent/control state is namespaced by stable tenant/VM IDs and never selected by display name alone.
- [ ] Add cross-tenant negative tests for memory, disk, network, device, console, snapshot, metadata, and management APIs.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C047 — Encrypt sensitive Full virtualization tier data in transit and at rest with managed key rotation.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Managed encryption in transit/at rest and key rotation.

### Design and implementation checklist

- [ ] Classify sensitive data in control traffic, configuration, VM metadata, disks/snapshots, logs, and evidence.
- [ ] Require approved TLS/mTLS versions/cipher policy for in-transit management/control traffic and verify peer identity.
- [ ] Use platform/storage encryption for sensitive data at rest with centrally managed KMS/HSM keys where appropriate.
- [ ] Define key hierarchy, tenant separation, rotation cadence, revocation, backup/recovery, and key-unavailable behavior.
- [ ] Prove rotation can occur without silent data loss or indefinite use of retired keys.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C048 — Define safe behavior when identity, attestation, policy, key, or time services are unavailable.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Fail-safe behavior for unavailable identity, attestation, policy, key, or time services.

### Design and implementation checklist

- [ ] For identity, attestation, policy, key, and time services, define which operations fail closed, which may continue from cached state, and maximum cache/lease age.
- [ ] Never bypass isolation/security checks merely to preserve availability.
- [ ] Define startup vs. steady-state behavior separately; a running VM may have different safe options than a new admission.
- [ ] Emit distinct dependency-unavailable and stale-trust diagnostics.
- [ ] Test prolonged outage, expired cache/credentials, clock skew, and recovery/reconciliation.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C049 — Emit tamper-evident audit events for security-sensitive Full virtualization tier operations.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Tamper-evident security audit event pipeline.

### Design and implementation checklist

- [ ] Define the security audit event schema with actor, action, target, tenant/site, decision, reason, policy/config/version, timestamp, correlation ID, and outcome.
- [ ] Emit events for authentication/authorization, VM lifecycle, device assignment, image verification, config/policy changes, secret/key operations, emergency actions, and security failures.
- [ ] Send events to append-only/tamper-evident storage with integrity protection and access control distinct from ordinary application logs.
- [ ] Define clock integrity/order handling and duplicate event behavior.
- [ ] Test that audit emission cannot silently disappear on success paths and that failure to record critical audit events triggers the approved safety behavior.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C050 — Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Tests cover primitive refusal, footprint exhaustion, device-sharing conflict, and a lease race, but not the full adversarial set (escape, injection, replay, spoofing, side channels, etc.).

### Design and implementation checklist

- [ ] Derive an adversarial test catalog directly from the threat model with a traceable test ID per threat/control.
- [ ] Test privilege escalation and authorization bypass across operator, controller, provider, and tenant boundaries.
- [ ] Test command/schema/log injection, malformed provider data, oversized input, path traversal, and unsafe serialization.
- [ ] Test replay/spoofing/downgrade for control messages, identity tokens, image/policy artifacts, and state updates.
- [ ] Test guest-to-host escape defenses and dangerous device emulation/passthrough cases on isolated security test infrastructure.
- [ ] Test timing/cache/resource side-channel mitigations where they are in scope, plus CPU/memory/storage/network exhaustion and noisy-neighbor pressure.
- [ ] Fail closed for security-critical ambiguity and preserve tenant/isolation invariants across every error path.
- [ ] Map the control to a threat-model entry and produce negative/adversarial verification evidence.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run targeted negative/adversarial tests and retain security audit evidence.
- [ ] Verify the control remains effective during restart, failure, and concurrent/racing operations.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `security/THREAT_MODEL.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/policy/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `security/audit-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Resilience & Failure Handling

## INV-40-C051 — Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Full virtualization tier.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Several failure modes are documented, but process/node/site/network/provider/dependency/control-plane failure modes are not exhaustively modeled.

### Design and implementation checklist

- [ ] Build a failure-mode catalog spanning local component exception/deadlock, control process crash, guest crash/hang, hypervisor failure, node reboot/loss, storage/network outage, site partition, cloud/provider API failure, identity/key/policy/time dependency failure, and controller split-brain.
- [ ] For each failure, record detection signal, blast radius, safety invariant, automatic action, operator action, recovery objective, and expected data/state loss.
- [ ] Separate transient/retryable conditions from corruption/safety failures requiring quarantine.
- [ ] Identify correlated failures and common-mode dependencies rather than modeling components independently.
- [ ] Link every high-severity failure mode to a fault-injection or game-day test.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C052 — Define automated health and stall detection thresholds for Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Health/stall detectors and thresholds.

### Design and implementation checklist

- [ ] Define liveness/readiness health checks for controller, provider/hypervisor connectivity, reconciliation loop, device lease/fencing service, state store, identity/key/policy dependencies, and node virtualization capabilities.
- [ ] Define stall detectors using operation age, queue age, reconciliation lag, heartbeat age, and provider progress where available.
- [ ] Use thresholds based on measured normal/tail behavior and include hysteresis to avoid flapping.
- [ ] Distinguish unhealthy, degraded, dependency-blocked, and overloaded states.
- [ ] Tie health state to automated remediation and alert severity rather than exposing passive status only.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C053 — Implement bounded retry with backoff and jitter only where operations are safe to retry.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Bounded retry with backoff/jitter and retry-safety classification.

### Design and implementation checklist

- [ ] Classify every external operation by retry safety and side-effect model.
- [ ] Use exponential backoff with bounded jitter, maximum attempts/elapsed time, and deadline awareness.
- [ ] Use idempotency keys or post-timeout reconciliation before retrying create/attach-like side-effecting operations.
- [ ] Stop retrying on policy, authentication, validation, unsupported-version, and deterministic resource-conflict failures.
- [ ] Instrument retry count, delay, final reason, and exhausted-retry events.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C054 — Implement admission control, load shedding, or circuit breaking to prevent Full virtualization tier failure cascades.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Admission control, load shedding, and/or circuit breaking.

### Design and implementation checklist

- [ ] Define admission checks for host/provider capacity, quotas, dependency health, required security capabilities, and controller backlog.
- [ ] Set queue/concurrency limits and reject/load-shed before resource exhaustion causes global failure.
- [ ] Use circuit breakers for failing external dependencies with explicit half-open recovery behavior.
- [ ] Prioritize safety/recovery/control traffic over best-effort provisioning during overload.
- [ ] Load-test threshold behavior and verify overload remains bounded without starvation or retry storms.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C055 — Define failover behavior without violating isolation, residency, or consistency requirements.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Failover behavior preserving isolation, residency, and consistency.

### Design and implementation checklist

- [ ] Define which state is authoritative during controller/node/site failover and how ownership is transferred/fenced.
- [ ] Preserve tenant isolation and residency: never fail over a workload to an unapproved region/site/device pool.
- [ ] Define consistency level and RPO/RTO for control state, VM metadata, images, snapshots, and attached storage.
- [ ] Require positive fencing of the old owner before activating a replacement where duplicate execution is unsafe.
- [ ] Test failover under partitions and delayed messages, not only clean shutdown.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C056 — Provide degraded operation when noncritical dependencies are unavailable.

**Priority:** P1  
**Audit status:** missing  
**Current evidence/gap:** Defined degraded mode for noncritical dependency failures.

### Design and implementation checklist

- [ ] Classify dependencies as critical, admission-critical, runtime-critical, or optional.
- [ ] Define allowed degraded operations when optional/noncritical dependencies fail and explicitly disable unsafe features.
- [ ] Expose degraded capability set and reason through health/API/telemetry.
- [ ] Define time limits for operating from cached/stale data and how recovery reconciles changes.
- [ ] Test that degraded mode cannot accidentally bypass security, quota, residency, or device-fencing controls.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C057 — Define crash-consistency, restart, resume, or replay semantics for mutable Full virtualization tier state.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Stopped guests can restart and destroyed guests cannot, but crash consistency, persisted restart state, replay, and recovery semantics are absent.

### Design and implementation checklist

- [ ] Identify mutable state that must survive controller/process/node restart: desired VM state, provider IDs, device leases, request idempotency records, config revision, and reconciliation checkpoints.
- [ ] Define atomic persistence/transaction boundaries and write ordering needed to avoid impossible states.
- [ ] Make reconciliation idempotent so replay after crash converges safely.
- [ ] Define handling of partially created/destroyed VMs and orphan resources discovered on restart.
- [ ] Crash the process at instrumented points around state/provider mutations and verify deterministic recovery.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C058 — Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** The in-process lease registry blocks duplicate device ownership, but there is no distributed lease/fencing protection for split-brain, stale controllers, or duplicate execution.

### Design and implementation checklist

- [ ] Move ownership from process-local leases to a durable/distributed lease or fencing mechanism when multiple controllers/nodes can act on the same resources.
- [ ] Use monotonic fencing tokens/epochs so a stale owner cannot perform privileged mutations after lease loss.
- [ ] Define lease TTL, renewal interval, clock assumptions, partition behavior, and ownership transfer protocol.
- [ ] Reconcile provider-observed state against lease ownership before acting.
- [ ] Test dual-controller, pause/resume, network partition, delayed renewal, stale token, and failover races.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C059 — Provide quarantine, freeze, disable, or isolation controls for unsafe Full virtualization tier behavior.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** destroy() provides a terminal local disable path, but there is no quarantine/freeze/isolate control plane or operator workflow.

### Design and implementation checklist

- [ ] Define independent controls for quarantine (deny new actions), freeze/pause, network isolate, detach/revoke devices, stop, destroy, and provider/site disable.
- [ ] Specify authorization and break-glass requirements for each high-impact action.
- [ ] Make emergency actions idempotent and available even when normal orchestration dependencies are impaired, within safety constraints.
- [ ] Record immutable audit evidence and reason codes for each containment action.
- [ ] Create operator runbooks and game-day tests for hostile guest, suspected escape, compromised image, device fault, and runaway resource scenarios.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C060 — Run fault-injection tests proving Full virtualization tier recovery against documented objectives.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Fault-injection recovery tests.

### Design and implementation checklist

- [ ] Build a deterministic fault-injection harness for provider/API timeouts, process crash, node reboot, network partition/loss, storage errors, identity/key/policy outages, clock skew, and state-store failures.
- [ ] Inject failures during every lifecycle phase, including cleanup and rollback.
- [ ] Assert safety invariants (no duplicate device ownership, no unauthorized failover, no leaked privileged resources) during and after faults.
- [ ] Measure detection time, recovery time, retries, data/control-state loss, and orphan cleanup against objectives.
- [ ] Make critical fault scenarios release-gating and archive machine-readable results.
- [ ] Make recovery convergent and idempotent; do not assume a clean shutdown or perfectly ordered messages.
- [ ] Define both automatic remediation and operator-visible escalation/containment behavior.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Inject the relevant failure during active operations and confirm recovery objectives/invariants.
- [ ] Verify no orphaned privileged resources, duplicate execution, or stale ownership remains after recovery.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `docs/failure-model.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/reconcile.py` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fault/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `runbooks/recovery/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Performance & Resource Efficiency

## INV-40-C061 — Establish reproducible baselines for Full virtualization tier latency, throughput, startup, CPU, memory, storage, network, and power overhead.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Reproducible performance/resource/power baseline harness and results.

### Design and implementation checklist

- [ ] Create a versioned benchmark harness with fixed host profiles, hypervisor/provider versions, VM image, guest workload, resource sizes, and warm/cold conditions.
- [ ] Measure create/start/stop/destroy/reconcile latency, CPU utilization, resident memory, disk I/O, network throughput/latency, storage footprint, and power where available.
- [ ] Record raw samples plus environment metadata; do not store only aggregate summaries.
- [ ] Separate control-plane overhead from guest workload performance and host baseline.
- [ ] Publish baseline artifact hashes so later regressions compare equivalent workloads/environments.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C062 — Define p50, p95, p99, and worst-case performance thresholds for Full virtualization tier.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** p50/p95/p99/worst-case thresholds.

### Design and implementation checklist

- [ ] Define percentile thresholds for each latency-sensitive operation and relevant throughput/resource SLI.
- [ ] Specify p50/p95/p99 computation window, minimum sample count, treatment of warmup/outliers/timeouts, and worst-case cap.
- [ ] Use different thresholds for host classes/profiles where hardware materially changes expected performance.
- [ ] Define hard release-blocking thresholds separately from alerting/SLO thresholds.
- [ ] Validate thresholds against repeated baseline runs to avoid gates dominated by benchmark noise.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C063 — Measure Full virtualization tier under steady load, burst load, overload, scale-out, scale-in, and recovery.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Steady/burst/overload/scale-out/scale-in/recovery performance tests.

### Design and implementation checklist

- [ ] Create workload phases for idle/steady state, burst admission, sustained overload, scale-out, scale-in, dependency slowdown, and recovery.
- [ ] Measure queueing, fairness, tail latency, error/rejection rate, resource saturation, and recovery hysteresis in each phase.
- [ ] Verify overload causes bounded rejection/degradation rather than unbounded memory/queue growth.
- [ ] Test scale transitions with active VMs and device/resource ownership, not only empty-node provisioning.
- [ ] Retain time-series results so regressions in transient behavior are visible.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C064 — Measure per-workload and per-tenant overhead introduced by Full virtualization tier.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Per-workload and per-tenant overhead measurements.

### Design and implementation checklist

- [ ] Measure control-plane CPU/memory and hypervisor overhead attributable to each VM/workload at multiple VM sizes and tenant densities.
- [ ] Quantify storage/image duplication, network encapsulation/control traffic, page-table/IOMMU/device overhead, and observability overhead where relevant.
- [ ] Measure noisy-neighbor effects and fairness under mixed tenant workloads.
- [ ] Define an overhead budget or planning coefficient for capacity models.
- [ ] Use tenant-safe aggregation so measurements do not expose another tenant’s workload data.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C065 — Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Full virtualization tier.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Documented analysis of avoidable copies/context switches/network hops/duplicated state/images.

### Design and implementation checklist

- [ ] Profile provisioning and steady-state paths for serialization/deserialization, memory copies, process/context switches, syscalls, provider round trips, network hops, and disk/image duplication.
- [ ] Use tracing/profiling evidence rather than assumptions to rank the dominant costs.
- [ ] Document which costs are required for isolation/correctness and therefore intentionally retained.
- [ ] Create optimization issues with expected gain, risk, and measurement method for avoidable costs.
- [ ] Re-profile after optimization to prove the cost moved rather than shifting elsewhere.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C066 — Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Implemented and evidenced locality/caching/zero-copy/batching/kernel-bypass optimizations where applicable.

### Design and implementation checklist

- [ ] Apply host/site locality for images, storage, and provider/control interactions where it does not violate residency or failure-domain policy.
- [ ] Use verified image caching/content addressing with bounded eviction and integrity checks.
- [ ] Batch provider/control operations only when batching preserves ordering, authorization, and failure semantics.
- [ ] Use zero-copy/direct I/O/kernel-bypass only after demonstrating measurable benefit and preserving isolation/accounting.
- [ ] Keep a fallback path and regression tests for environments that cannot support an optimization.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C067 — Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Resident footprint is bounded per guest and the device set is finite, but queues, concurrency, buffers, and fleet fan-out are not bounded.

### Design and implementation checklist

- [ ] Set hard bounds for process memory, per-request allocations, queue lengths, diagnostic buffers, worker pools, concurrent provider calls, VM/device fan-out, and cached state.
- [ ] Define eviction/drop/rejection behavior at each bound.
- [ ] Use resource accounting keyed by tenant/node/site so one principal cannot consume the global pool unchecked.
- [ ] Expose saturation/high-water metrics and alert thresholds before hard exhaustion.
- [ ] Stress-test bounds under adversarial concurrency and verify memory/descriptor/thread counts converge after load ends.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C068 — Measure power and thermal impact on constrained edge nodes where relevant.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Power/thermal measurement for constrained nodes.

### Design and implementation checklist

- [ ] Select representative constrained/edge hardware and define sensor sources for package power, system power, temperature, throttling, and fan behavior.
- [ ] Measure idle, VM boot burst, steady workload, dense multi-VM, and recovery power/thermal profiles.
- [ ] Record ambient/hardware configuration and sampling method so results are comparable.
- [ ] Define thermal throttling/safety limits and admission response for sustained heat/power pressure.
- [ ] Include performance-per-watt or energy-per-operation metrics where meaningful.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C069 — Define capacity models and saturation signals that predict when Full virtualization tier needs more resources.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Capacity model and saturation signals.

### Design and implementation checklist

- [ ] Develop a capacity model using host CPU, memory, I/O, network, storage, device/IOMMU groups, provider quotas, control-loop throughput, and safety headroom.
- [ ] Differentiate allocatable, reserved, committed, observed, and reclaimable resources.
- [ ] Identify leading saturation signals and threshold bands before hard capacity exhaustion.
- [ ] Validate model predictions against load tests at multiple densities and workload mixes.
- [ ] Expose capacity forecast/headroom per node/site/tenant for placement/admission consumers.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C070 — Block releases that regress approved Full virtualization tier startup, density, throughput, or tail-latency thresholds.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Automated performance-regression release gate.

### Design and implementation checklist

- [ ] Select release-blocking metrics such as cold-start p99, steady memory overhead, VM density, lifecycle throughput, and tail control latency.
- [ ] Store approved baselines keyed by hardware/provider/test profile and compare statistically appropriate samples.
- [ ] Define tolerance bands and explicit review/waiver workflow for intentional regressions.
- [ ] Make CI fail automatically when a regression exceeds the threshold or benchmark evidence is missing.
- [ ] Archive raw benchmark evidence with commit/artifact hashes.
- [ ] Measure on controlled, versioned environments and retain raw samples plus environment metadata.
- [ ] Ensure optimization never weakens isolation, correctness, residency, or auditability.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Repeat the benchmark enough times to characterize variance and tail behavior.
- [ ] Compare against an approved baseline and fail the gate when hard thresholds regress.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `benchmarks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `performance/baselines/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/performance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/capacity.md` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Observability & Explainability

## INV-40-C071 — Expose Full virtualization tier health, readiness, version, configuration, dependency status, and active capability set.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Health/readiness/version/config/dependency/capability endpoint or report.

### Design and implementation checklist

- [ ] Expose a machine-readable status surface containing health, readiness, software version, schema version, provider/hypervisor version, active config revision, dependency states, and enabled capabilities.
- [ ] Separate liveness from readiness so orchestration does not restart a healthy-but-not-ready component blindly.
- [ ] Include stale/degraded state and the last successful reconciliation timestamp.
- [ ] Redact secrets and tenant-private data while retaining enough context for operators.
- [ ] Add CLI/API and test fixtures for the status schema.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C072 — Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Runtime structured metrics emission.

### Design and implementation checklist

- [ ] Define stable metrics for request/lifecycle rate, successes/errors/rejections by code, latency histograms, queue/backlog, retries, reconciliation lag, VM counts/states, resource usage, device leases, dependency health, and provider saturation.
- [ ] Use bounded-cardinality labels; tenant/workload identifiers should not be uncontrolled metric labels.
- [ ] Define units, histogram buckets, reset semantics, and ownership for each metric.
- [ ] Instrument failure and degraded paths as thoroughly as success paths.
- [ ] Create automated tests asserting critical metrics increment/change on representative operations.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C073 — Emit structured logs with stable node, tenant, workload, component, and operation identifiers.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Structured logs with stable correlation identifiers.

### Design and implementation checklist

- [ ] Emit structured JSON/event logs with timestamp, severity, component/version, node/site, tenant/workload/VM IDs, operation/request/correlation ID, provider, action, outcome, and stable error code.
- [ ] Propagate identifiers from ingress through provider/reconciliation operations.
- [ ] Define redaction rules for secrets, guest data, tokens, file contents, and sensitive provider responses.
- [ ] Rate-limit or sample noisy repeated logs without hiding distinct failures.
- [ ] Test log schema stability and redaction using representative error paths.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C074 — Propagate trace context across all relevant Full virtualization tier boundaries.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Trace-context propagation.

### Design and implementation checklist

- [ ] Adopt a trace-context standard such as W3C Trace Context/OpenTelemetry for RPC/event boundaries.
- [ ] Create spans for admission, provider calls, image/storage/network setup, lease/fencing, boot wait, reconciliation, and cleanup.
- [ ] Propagate trace context through asynchronous queues/events and record links when strict parent-child structure is inappropriate.
- [ ] Attach bounded attributes such as operation type, provider, status/error code, site, and anonymized/stable resource IDs.
- [ ] Test trace continuity across at least one full create-to-running and destroy workflow.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C075 — Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Safe high-cardinality diagnostic interface with privacy controls.

### Design and implementation checklist

- [ ] Separate high-cardinality diagnostics from ordinary metrics and protect them with explicit authorization.
- [ ] Provide targeted query/filter capability by operation/VM/tenant/site/time without exposing unrelated tenant data.
- [ ] Apply redaction, field allowlists, result-size/time bounds, and audit logging to diagnostic access.
- [ ] Define short retention for sensitive debug payloads and a secure support-bundle workflow.
- [ ] Test cross-tenant queries and secret-bearing error paths for leakage.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C076 — Record the reason for every automated decision made by Full virtualization tier.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Decision-reason recording for automated decisions.

### Design and implementation checklist

- [ ] Define a stable decision record for admission, provider selection, degraded-mode entry, retry, failover, quarantine, and policy rejection.
- [ ] Record inputs/constraints considered, policy/config revision, selected action, alternatives rejected if useful, and a stable reason code.
- [ ] Keep reason generation deterministic enough for testing and avoid including secrets/raw guest data.
- [ ] Correlate the decision record with request/trace/audit identifiers.
- [ ] Test that every automated branch that materially changes workload state emits a reason.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C077 — Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Operator explain view linking decisions to inputs/policy/topology/constraints.

### Design and implementation checklist

- [ ] Create an operator explain command/API that reconstructs why a VM/action is in its current state.
- [ ] Show relevant desired/observed state, policy decisions, quota/capacity, provider capability, dependency health, topology/residency constraints, config revision, and last errors.
- [ ] Distinguish current facts from historical decisions and stale cached values.
- [ ] Link to correlated logs/traces/audit events without requiring manual ID hunting.
- [ ] Redact cross-tenant/security-sensitive details based on operator authorization.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C078 — Correlate Full virtualization tier events with application release lineage and the live infrastructure graph.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Correlation with release lineage and live infrastructure graph.

### Design and implementation checklist

- [ ] Attach release/artifact digest, code commit, configuration revision, policy revision, provider version, node identity, and image digest to lifecycle/incident telemetry.
- [ ] Integrate VM/node/network/storage/device relationships with the authoritative infrastructure inventory/graph.
- [ ] Update graph edges transactionally or reconcile them from authoritative provider state.
- [ ] Make incident queries able to answer “which release/config/provider affected these VMs?” and “which resources were attached at time T?”.
- [ ] Test lineage continuity across rolling upgrades and VM migration/restart scenarios.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C079 — Define telemetry retention, sampling, privacy, and export policy.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Telemetry retention/sampling/privacy/export policy.

### Design and implementation checklist

- [ ] Classify telemetry fields by operational need, sensitivity, tenant privacy, and regulatory retention requirements.
- [ ] Define metrics/log/trace/audit retention separately and specify aggregation/downsampling behavior.
- [ ] Define sampling rules that preserve errors/security events while reducing ordinary high-volume traces.
- [ ] Control export destinations, encryption, access, deletion, and cross-region residency.
- [ ] Document and test redaction before export rather than relying solely on downstream processors.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C080 — Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Dashboards and differentiated alerting.

### Design and implementation checklist

- [ ] Build dashboards for service health, lifecycle latency/error, capacity/saturation, device/fencing state, dependency health, security events, and release regressions.
- [ ] Define alert classes for ordinary capacity pressure, SLO degradation, policy rejection spikes, dependency outage, suspected attack/isolation violation, and software defect.
- [ ] Attach runbook links, ownership, severity, dedup/grouping, and escalation policy to alerts.
- [ ] Use symptom-based alerts for user impact plus cause-oriented diagnostics; avoid paging on every raw metric threshold.
- [ ] Test alerts with synthetic failures/game days and verify they route to the documented owner.
- [ ] Use stable schemas/identifiers and bounded-cardinality telemetry fields.
- [ ] Protect tenant/private/secret information with redaction and access control in every diagnostic surface.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Generate success, degraded, and failure scenarios and confirm telemetry/explain output is complete and correlated.
- [ ] Run privacy/redaction checks against representative sensitive values.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `observability/metrics.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/log-schema.*` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `observability/dashboards/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `inv40_full_virtualization_tier/diagnostics.py` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Testing & Certification

## INV-40-C082 — Create contract tests for every public Full virtualization tier interface.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Public runtime methods are unit-tested, but there are no schema fixtures/consumer contract tests and pk_core contract tests cannot run without the external dependency.

### Design and implementation checklist

- [ ] Create contract tests for every public runtime/provider/API operation, every schema version, and every stable error code.
- [ ] Validate canonical fixtures against producer and consumer implementations.
- [ ] Test backward-compatible optional fields, unknown-field policy, numeric/string bounds, and invalid enum/schema cases.
- [ ] Run `pk_core` integration contract tests in an environment where the dependency is actually installed rather than counting skips as evidence.
- [ ] Gate interface changes on contract-test updates and compatibility review.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C083 — Create integration tests with every supported adjacent layer and execution tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Integration tests against every supported adjacent layer/tier.

### Design and implementation checklist

- [ ] Enumerate all supported adjacent systems and create at least one test suite per integration boundary.
- [ ] Use real hypervisor/provider and real or production-faithful identity/network/storage/policy dependencies for release certification.
- [ ] Exercise lifecycle, authorization, version negotiation, failure propagation, timeout, cancellation, and cleanup end-to-end.
- [ ] Verify identifiers/correlation and tenant isolation remain intact across the boundary.
- [ ] Make unsupported/skipped adjacency tests explicit release blockers unless an approved profile excludes that adjacency.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C084 — Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Compatibility matrix tests across CPU architectures, runtimes, hypervisors, providers, and protocol versions.

### Design and implementation checklist

- [ ] Publish a compatibility matrix covering x86_64/ARM64 if supported, host OS/kernel, Python runtime, hypervisor/provider, firmware, CPU virtualization features, IOMMU, schema/protocol, and guest OS classes.
- [ ] Automate matrix jobs for all required combinations and sample optional combinations based on risk.
- [ ] Include upgrade/downgrade and mixed-version tests, not only fresh installation.
- [ ] Validate architecture-specific device and performance assumptions.
- [ ] Remove a combination from “supported” when it cannot be continuously tested or when its upstream security support expires.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C085 — Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Fuzzing of schemas/protocol/untrusted-input boundaries.

### Design and implementation checklist

- [ ] Identify all untrusted parsers/decoders: configuration, schemas, RPC/events, provider responses, image metadata, identifiers, logs/diagnostic inputs, and any binary protocol boundaries.
- [ ] Add coverage-guided fuzz targets with seed corpora from canonical fixtures and previously discovered failures.
- [ ] Use sanitizers/native hardening for native provider bindings where applicable and run long-lived fuzz jobs for high-risk boundaries.
- [ ] Assert no crashes, hangs, unbounded allocation, path traversal, injection, or invariant violation.
- [ ] Minimize and retain regression corpus cases for every discovered defect.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C086 — Create concurrency and race-condition tests for shared/distributed Full virtualization tier state.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** There is a concurrent device-lease race test, but no broader race testing across lifecycle, configuration, persistence, or distributed ownership.

### Design and implementation checklist

- [ ] Expand race tests to lifecycle operations (`start/stop/destroy`), idempotent retries, config activation/rollback, persistent state updates, reconciliation, and distributed leases/fencing.
- [ ] Use barriers/fault hooks to force harmful interleavings instead of relying on probabilistic timing alone.
- [ ] Run stress repetitions under thread/process concurrency and across multiple controller instances where supported.
- [ ] Assert invariants after every race: single owner, legal state, no leaked devices/resources, monotonic fencing, coherent config revision.
- [ ] Use a race-capable/native sanitizer or deterministic scheduler for native components if introduced.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C087 — Create security tests derived directly from the Full virtualization tier threat model.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Some tests derive from documented threats (missing primitive/device conflict/resource exhaustion), but the threat model is not fully translated into security tests.

### Design and implementation checklist

- [ ] Create a traceable mapping from each threat-model entry to one or more preventive/detective test cases.
- [ ] Include negative authorization/isolation, artifact tampering, stale/replayed control messages, compromised dependency responses, provider escape-risk configuration, and resource-exhaustion scenarios.
- [ ] Define expected failure mode and audit evidence for each attack test.
- [ ] Run high-risk security tests on isolated infrastructure with safe cleanup and artifact retention.
- [ ] Treat untested critical threats as open release blockers unless formally risk-accepted.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C088 — Create benchmark, soak, burst, and fleet-scale tests appropriate to Full virtualization tier.

**Priority:** P2  
**Audit status:** missing  
**Current evidence/gap:** Benchmark, soak, burst, and fleet-scale tests.

### Design and implementation checklist

- [ ] Create microbenchmarks for deterministic hot paths and end-to-end benchmarks for lifecycle operations.
- [ ] Run multi-hour/day soak tests for memory/file-descriptor/thread leaks, queue accumulation, state divergence, and provider resource leakage.
- [ ] Run burst tests with sudden concurrent provisioning/teardown and verify backpressure/fairness.
- [ ] Run fleet-scale tests at the intended maximum controller/node/VM cardinality or a validated scale model.
- [ ] Collect raw performance/resource/telemetry evidence and compare against baselines automatically.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C089 — Create disaster, partition, reconnect, and degraded-control-plane tests.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Disaster/partition/reconnect/degraded-control-plane tests.

### Design and implementation checklist

- [ ] Test control-plane partition from nodes/providers while VMs remain running, including commands issued on both sides of the partition.
- [ ] Test reconnect with stale messages, expired leases, duplicated requests, and changed desired state.
- [ ] Test site/provider outage and recovery according to residency/fencing/failover rules.
- [ ] Test identity/key/policy/telemetry degradation simultaneously with control-plane issues to expose dependency coupling.
- [ ] Verify reconciliation converges to one safe state and produces complete audit/incident evidence.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C090 — Require machine-readable acceptance evidence before certifying a Full virtualization tier release for production.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Machine-readable release acceptance evidence artifact and certification rule.

### Design and implementation checklist

- [ ] Define a signed/versioned release-evidence schema containing artifact digest, commit, dependency lock, test results, coverage, security scans, compatibility matrix, performance results, waivers, approvers, and gate verdict.
- [ ] Generate evidence automatically in CI from authoritative tool outputs; do not permit manual green status without underlying artifacts.
- [ ] Bind every evidence item to the exact candidate artifact and configuration/schema revisions tested.
- [ ] Require explicit states for PASS/FAIL/SKIPPED/NOT_APPLICABLE and make unexpected SKIPPED non-passing.
- [ ] Implement an offline verifier that recomputes hashes/signatures and validates completeness before production certification.
- [ ] Make test results machine-readable and bind them to the exact artifact/commit under test.
- [ ] Treat skipped or unavailable mandatory tests as missing evidence, not as a pass.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run the suite in CI from a clean environment and archive results with artifact hashes.
- [ ] Demonstrate at least one intentional failing condition is correctly detected by the test/gate.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `tests/contract/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/integration/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/security/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `tests/fuzz/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/evidence/` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Operations, Release & Governance

## INV-40-C091 — Define production SLOs, error budgets, and support commitments for Full virtualization tier.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** Three SLO/error-budget statements exist; support commitments, service windows, and ownership/escalation commitments are absent.

### Design and implementation checklist

- [ ] Define user-facing and internal SLOs for admission/lifecycle availability, latency, isolation safety, reconciliation, and critical dependency recovery.
- [ ] Define error-budget accounting, burn-rate alerts, maintenance treatment, and release policy when budgets are exhausted.
- [ ] Publish support hours/on-call coverage, incident response targets, escalation contacts/roles, and dependency support assumptions.
- [ ] Separate zero-tolerance safety/isolation invariants from availability SLOs that permit an error budget.
- [ ] Review SLOs periodically against measured production behavior and capacity.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C092 — Define canary, staged rollout, rollback, and emergency-disable procedures for Full virtualization tier.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** README mentions rollback and emergency disable, but canary/staged rollout, rollback validation, and executable procedures are absent.

### Design and implementation checklist

- [ ] Define staged rollout rings/canaries by site/node/provider/tenant risk class and the maximum blast radius per stage.
- [ ] Specify automated promotion criteria based on health, errors, security, performance, and reconciliation signals.
- [ ] Define rollback triggers, exact rollback command/workflow, state/schema compatibility checks, and validation after rollback.
- [ ] Implement an emergency disable/kill switch with narrow authorization, audit logging, and tested behavior under degraded control plane.
- [ ] Exercise rollout and rollback procedures in staging/game days and capture timing/evidence.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C093 — Maintain a supported-version compatibility matrix for Full virtualization tier and adjacent dependencies.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Supported-version compatibility matrix.

### Design and implementation checklist

- [ ] Maintain a version matrix for INV-40 package/schema, `pk_core`, Python, host OS/kernel, hypervisor/provider, firmware, CPU architecture, cloud SDK/API, and adjacent tier versions.
- [ ] Mark combinations as supported, deprecated, experimental, or unsupported with end dates.
- [ ] Link each supported combination to automated test evidence and security support status.
- [ ] Define mixed-version rolling-upgrade compatibility windows.
- [ ] Publish the matrix with every release and fail certification if the candidate was not tested against its declared combinations.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C094 — Define patching, vulnerability response, and end-of-life SLAs for Full virtualization tier.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Patching, vulnerability-response, and end-of-life SLAs.

### Design and implementation checklist

- [ ] Define severity-based vulnerability response SLAs for critical/high/medium/low issues affecting code, hypervisor/provider, guest-facing devices, dependencies, and build/release chain.
- [ ] Define patch qualification, emergency release, rollback, customer/operator notification, and compensating-control procedures.
- [ ] Track upstream end-of-life dates for Python, OS/kernel, QEMU/libvirt/provider SDKs, and critical dependencies.
- [ ] Establish deprecation/EOL notice windows and removal dates for unsupported versions.
- [ ] Run continuous dependency/CVE scanning and route findings to an accountable owner.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C095 — Provide backup, restore, migration, or reconstruction procedures for Full virtualization tier state where applicable.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Backup/restore/migration/reconstruction procedures for applicable state.

### Design and implementation checklist

- [ ] Classify state as reconstructible, backup-required, externally authoritative, or ephemeral.
- [ ] Define backup scope for control metadata, configuration history, audit/evidence, images/snapshots if owned, and lease/fencing state where persistence is appropriate.
- [ ] Encrypt backups, separate access roles, define retention/immutability, and test key recovery.
- [ ] Document restore/migration ordering and reconciliation with provider-observed VM/device state.
- [ ] Perform periodic restore drills and measure RPO/RTO; never claim backup coverage without a tested restore.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C096 — Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks.

**Priority:** P0  
**Audit status:** partial  
**Current evidence/gap:** README contains day-0/day-1/day-2 bullets, but they are not operational runbooks with prerequisites, commands, validation, rollback, and recovery steps.

### Design and implementation checklist

- [ ] Expand Day-0 into prerequisites, bootstrap commands, preflight, trust/config initialization, provider setup, validation, and rollback/cleanup.
- [ ] Expand Day-1 into deployment, canary promotion, health/SLO validation, integration checks, and rollback criteria.
- [ ] Expand Day-2 into monitoring, capacity, patching, certificate/key rotation, backup verification, reconciliation, incident response, and upgrade procedures.
- [ ] For every runbook step include expected output, failure branches, safe retry/idempotency notes, and verification commands.
- [ ] Test runbooks with an operator who did not author them and fix hidden assumptions.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The remaining portions are implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C097 — Define incident severity, paging, escalation, containment, and recovery procedures.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Incident severity, paging, escalation, containment, and recovery procedures.

### Design and implementation checklist

- [ ] Define incident severity levels with concrete examples such as suspected VM escape, cross-tenant device assignment, control-plane outage, provider degradation, release regression, and routine VM failure.
- [ ] Map each severity to paging target, acknowledgement time, escalation chain, incident commander/security/legal/comms participation, and update cadence.
- [ ] Create containment procedures for quarantine/network isolation/device revocation/provider disable and evidence preservation.
- [ ] Define recovery validation, customer/tenant impact assessment, post-incident review, and corrective-action tracking.
- [ ] Run tabletop/game-day exercises and retain evidence that contacts and procedures work.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C098 — Perform recurring access, policy, dependency, configuration, and architecture reviews.

**Priority:** P1  
**Audit status:** missing  
**Current evidence/gap:** Recurring access/policy/dependency/configuration/architecture review process.

### Design and implementation checklist

- [ ] Schedule recurring reviews for privileged access, authorization policy, trust roots/certificates, dependencies/CVEs/licenses, configuration drift, provider versions, threat model, architecture ADRs, capacity/SLOs, and exceptions.
- [ ] Assign review cadence and accountable owner per review type.
- [ ] Automate evidence collection/diff generation so reviewers see changes since the previous review.
- [ ] Track findings to closure with severity, owner, due date, and waiver process.
- [ ] Require review completion/evidence as part of periodic compliance or production recertification.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C099 — Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Exception/waiver/technical-debt/deprecation register with owners and expiries.

### Design and implementation checklist

- [ ] Create a machine-readable register for exceptions, waivers, known defects, technical debt, deprecated behavior, and unsupported deviations.
- [ ] Record scope, rationale, risk, affected requirements/assets, owner, approver, compensating controls, creation date, expiry/review date, and closure evidence.
- [ ] Disallow permanent waivers without periodic reapproval; expired waivers must fail the release/production gate.
- [ ] Surface active high-risk waivers in release evidence and operator status.
- [ ] Link debt/deprecations to planned removal milestones and compatibility communications.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

## INV-40-C100 — Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

**Priority:** P0  
**Audit status:** missing  
**Current evidence/gap:** Formal production exit-gate artifact/results. README references pk_core gate, but pk_core and gate evidence are absent from this archive.

### Design and implementation checklist

- [ ] Define a formal production gate schema covering all ten checklist dimensions plus repository packaging/dependency/license/release prerequisites.
- [ ] Require complete traceability to current implementation and machine-readable verification evidence for every mandatory requirement.
- [ ] Treat missing, failed, stale, hash-mismatched, or unexpectedly skipped evidence as NO_GO; allow waivers only through the governed exception process.
- [ ] Require explicit sign-off roles for architecture, security, operations/SRE, quality, and service ownership.
- [ ] Bind the gate verdict to the exact release artifact digest and configuration/provider compatibility profile.
- [ ] Archive the signed gate result and make deployment tooling verify it before production promotion.
- [ ] Assign an accountable owner and ensure procedures are executable under incident conditions, not just documented.
- [ ] Tie governance records to release artifacts/configuration versions and enforce expiries automatically where applicable.
- [ ] Preserve all already-passing v4.2.0 behavior and add a regression test before refactoring any code path currently providing partial evidence.
- [ ] Add/update the requirement traceability entry with owner, implementation location, test IDs, evidence location, status, and last-verification timestamp.

### Verification checklist

- [ ] Run a tabletop/game-day or dry-run of the procedure and capture remediation for discovered gaps.
- [ ] Verify owner, contact, expiry, and evidence links are valid at release time.
- [ ] Include at least one negative/boundary case that proves the control fails safely rather than merely exercising the happy path.
- [ ] Run verification from a clean checkout/environment using only declared dependencies and configuration.
- [ ] Record PASS/FAIL/SKIPPED explicitly; an unexpected `SKIPPED` is not accepted as satisfying this requirement.

### Evidence and documentation checklist

- [ ] Update or add `runbooks/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/slo.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `docs/release-process.md` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `governance/` (or an approved equivalent) and reference it in traceability.
- [ ] Update or add `release/gate-schema.json` (or an approved equivalent) and reference it in traceability.
- [ ] Archive machine-readable test/gate output with commit SHA, package/version, provider/hardware profile when relevant, and artifact digest.
- [ ] Update `README.md`, `CHANGELOG.md`, and operator/security documentation when externally visible behavior or support claims change.
- [ ] If the item is intentionally not applicable to a deployment profile, record an approved, reasoned `NOT_APPLICABLE` decision rather than silently omitting evidence.

### Closure criteria

- [ ] The requirement is implemented in executable code/configuration/process as applicable, verified by non-skipped tests or review evidence, and linked in the release gate.
- [ ] No unresolved high/critical security, correctness, or isolation defect contradicts the claimed completion.
- [ ] The evidence is current for the exact release candidate and supported deployment profile.

# Part III — Recommended closure sequence

## Phase 0 — Evidence integrity and packaging

- [ ] Complete the following items in dependency order, or document why parallel execution is safe:
  - [ ] `REPO-001`
  - [ ] `REPO-004`
  - [ ] `REPO-005`
  - [ ] `REPO-006`
  - [ ] `INV-40-C011`
  - [ ] `INV-40-C020`
  - [ ] `INV-40-C090`
  - [ ] `INV-40-C100`

## Phase 1 — Real virtualization implementation and trust boundary

- [ ] Complete the following items in dependency order, or document why parallel execution is safe:
  - [ ] `REPO-003`
  - [ ] `INV-40-C021`
  - [ ] `INV-40-C022`
  - [ ] `INV-40-C023`
  - [ ] `INV-40-C024`
  - [ ] `INV-40-C031`
  - [ ] `INV-40-C041`
  - [ ] `INV-40-C042`
  - [ ] `INV-40-C043`
  - [ ] `INV-40-C044`
  - [ ] `INV-40-C045`
  - [ ] `INV-40-C046`
  - [ ] `INV-40-C047`
  - [ ] `INV-40-C049`

## Phase 2 — Configuration, lifecycle correctness, and distributed ownership

- [ ] Complete the following items in dependency order, or document why parallel execution is safe:
  - [ ] `INV-40-C025`
  - [ ] `INV-40-C026`
  - [ ] `INV-40-C027`
  - [ ] `INV-40-C028`
  - [ ] `INV-40-C032`
  - [ ] `INV-40-C033`
  - [ ] `INV-40-C034`
  - [ ] `INV-40-C035`
  - [ ] `INV-40-C036`
  - [ ] `INV-40-C037`
  - [ ] `INV-40-C038`
  - [ ] `INV-40-C039`
  - [ ] `INV-40-C040`
  - [ ] `INV-40-C057`
  - [ ] `INV-40-C058`
  - [ ] `INV-40-C059`

## Phase 3 — Failure handling and operations

- [ ] Complete the following items in dependency order, or document why parallel execution is safe:
  - [ ] `INV-40-C018`
  - [ ] `INV-40-C048`
  - [ ] `INV-40-C051`
  - [ ] `INV-40-C052`
  - [ ] `INV-40-C053`
  - [ ] `INV-40-C054`
  - [ ] `INV-40-C055`
  - [ ] `INV-40-C056`
  - [ ] `INV-40-C060`
  - [ ] `INV-40-C091`
  - [ ] `INV-40-C092`
  - [ ] `INV-40-C094`
  - [ ] `INV-40-C095`
  - [ ] `INV-40-C096`
  - [ ] `INV-40-C097`
  - [ ] `INV-40-C098`
  - [ ] `INV-40-C099`

## Phase 4 — Observability and certification

- [ ] Complete the following items in dependency order, or document why parallel execution is safe:
  - [ ] `INV-40-C071`
  - [ ] `INV-40-C072`
  - [ ] `INV-40-C073`
  - [ ] `INV-40-C074`
  - [ ] `INV-40-C075`
  - [ ] `INV-40-C076`
  - [ ] `INV-40-C077`
  - [ ] `INV-40-C078`
  - [ ] `INV-40-C079`
  - [ ] `INV-40-C080`
  - [ ] `INV-40-C082`
  - [ ] `INV-40-C083`
  - [ ] `INV-40-C084`
  - [ ] `INV-40-C085`
  - [ ] `INV-40-C086`
  - [ ] `INV-40-C087`
  - [ ] `INV-40-C089`

## Phase 5 — Capacity/performance maturity

- [ ] Complete the following items in dependency order, or document why parallel execution is safe:
  - [ ] `INV-40-C061`
  - [ ] `INV-40-C062`
  - [ ] `INV-40-C063`
  - [ ] `INV-40-C064`
  - [ ] `INV-40-C065`
  - [ ] `INV-40-C066`
  - [ ] `INV-40-C067`
  - [ ] `INV-40-C068`
  - [ ] `INV-40-C069`
  - [ ] `INV-40-C070`
  - [ ] `INV-40-C088`

# Part IV — Final certification checklist

- [ ] A production hypervisor/provider adapter, not only the reference model, has passed hardware-backed integration tests.
- [ ] All public contracts are versioned, typed, authenticated, authorized, bounded, and covered by contract tests.
- [ ] Configuration is declarative, validated before activation, provenance-tracked, transactional where required, and rollback-tested.
- [ ] Tenant isolation is enforced across execution, memory, storage, network, devices, state, and management access.
- [ ] Artifact/image/policy provenance and signatures are verified, and sensitive data is encrypted with managed key rotation.
- [ ] Distributed ownership/fencing prevents split-brain and stale-controller actions under partitions and failover.
- [ ] Failure injection demonstrates bounded detection/recovery with no orphaned privileged resources or isolation violations.
- [ ] Health, metrics, logs, traces, audit events, decision reasons, dashboards, and alerts are implemented with privacy controls.
- [ ] Compatibility, fuzz, security, concurrency, disaster, soak, burst, fleet-scale, and performance-regression tests are passing for the declared support matrix.
- [ ] Day-0/day-1/day-2, rollback, emergency-disable, incident, backup/restore, patching, and EOL procedures are exercised and owned.
- [ ] No P0 item remains open except an approved time-bounded waiver captured in the exception register.
- [ ] The machine-readable production exit gate validates the exact release artifact digest and returns GO.

