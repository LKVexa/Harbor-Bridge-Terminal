# INV-07 GitOps transition layer — MASTER (v5.0.0)

> **Provenance of this document.** The v4.2.0 archive referenced a `MASTER.md` that was not shipped. This file is **regenerated** by `components/tools/master.py` from `CHECKLIST.json` (100 architecture requirements) and the 54-component professional checklist, both present in the archive. It does not claim to reproduce the missing original; if the original surfaces it supersedes this file.

## Identity

* Element: `INV-07` · Name: GitOps transition layer · Version: `5.0.0` (VERSION, pyproject, `__version__` and `controller.VERSION` are checked for consistency by `tools/gates.py docs`).
* Contract: `contract.py` (requires the external `pk_core`); production overlay: `components/`.

## External dependencies (disclosure)

| Dependency | Needed for | Present in archive |
|---|---|---|
| `pk_core` | 100-item architecture conformance gate | **no** |
| git ≥ 2.31 | transport | host-provided |
| Git server, Kubernetes, Argo CD/Flux, KMS, OPA, GAP-07 verifier | production acceptance | **no** (BLOCKED items) |
| INV-05 / INV-06 / INV-63 sibling components | adjacent integration | **no** |

## Global completion rules (from the 54-component checklist)

1. Every checklist ID must map to implementation and reproducible evidence.
2. A skipped required test is not a pass.
3. Production mutation fails closed on unresolved identity, authorization, trust, provenance, policy, or integrity.
4. Secrets and sensitive tenant data are excluded from ordinary diagnostics/evidence.
5. All public contracts and durable formats are versioned.
6. Every release artifact and evidence bundle is bound to immutable digests.
7. Waivers are time-bounded and reviewed.
8. No P0 item may remain open for a production-mutating deployment.

## Architecture requirements (CHECKLIST.json, stable IDs)

| ID | Dimension | Requirement |
|---|---|---|
| `INV-07-C001` | Architecture & Scope | Define the exact production responsibility of GitOps transition layer. |
| `INV-07-C002` | Architecture & Scope | Document what GitOps transition layer owns and explicitly does not own. |
| `INV-07-C003` | Architecture & Scope | Identify upstream, downstream, and peer dependencies of GitOps transition layer. |
| `INV-07-C004` | Architecture & Scope | Define the authoritative source of truth used by GitOps transition layer. |
| `INV-07-C005` | Architecture & Scope | Document assumptions GitOps transition layer makes about nodes, runtimes, networks, storage, and control planes. |
| `INV-07-C006` | Architecture & Scope | Define tenant, environment, site, and workload boundaries relevant to GitOps transition layer. |
| `INV-07-C007` | Architecture & Scope | Separate mandatory GitOps transition layer capabilities from optional optimizations. |
| `INV-07-C008` | Architecture & Scope | Document unsupported deployment patterns and non-goals for GitOps transition layer. |
| `INV-07-C009` | Architecture & Scope | Assign an accountable owner and escalation path for GitOps transition layer. |
| `INV-07-C010` | Architecture & Scope | Approve an architecture decision record for GitOps transition layer, its technologies (GitOps, ArgoCD, Flux), and its function (Reconcile declarative configuration with live infrastructure). |
| `INV-07-C011` | Requirements & Semantics | Translate the source function of GitOps transition layer — Reconcile declarative configuration with live infrastructure — into testable SHALL-level requirements. |
| `INV-07-C012` | Requirements & Semantics | Define functional requirements for GitOps transition layer across cloud, datacenter, near-edge, and far-edge contexts where applicable. |
| `INV-07-C013` | Requirements & Semantics | Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable. |
| `INV-07-C014` | Requirements & Semantics | Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for GitOps transition layer. |
| `INV-07-C015` | Requirements & Semantics | Define lifecycle states and legal state transitions managed or exposed by GitOps transition layer. |
| `INV-07-C016` | Requirements & Semantics | Define versioning and backward-compatibility requirements for GitOps transition layer. |
| `INV-07-C017` | Requirements & Semantics | Define capacity ceilings, quotas, and fairness semantics relevant to GitOps transition layer. |
| `INV-07-C018` | Requirements & Semantics | Define behavior when network connectivity is intermittent or absent. |
| `INV-07-C019` | Requirements & Semantics | Define precedence rules when GitOps transition layer requirements conflict with security, residency, SLO, or cost constraints. |
| `INV-07-C020` | Requirements & Semantics | Maintain a requirements traceability matrix from each GitOps transition layer requirement to implementation and verification evidence. |
| `INV-07-C021` | Interfaces & Integration | Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by GitOps transition layer. |
| `INV-07-C022` | Interfaces & Integration | Use versioned typed schemas for all externally visible GitOps transition layer contracts. |
| `INV-07-C023` | Interfaces & Integration | Define authentication requirements at each GitOps transition layer boundary. |
| `INV-07-C024` | Interfaces & Integration | Define authorization and explicit capability requirements at each GitOps transition layer boundary. |
| `INV-07-C025` | Interfaces & Integration | Define timeout, cancellation, retry, idempotency, and backpressure semantics for GitOps transition layer. |
| `INV-07-C026` | Interfaces & Integration | Define structured failure codes and machine-readable error details for GitOps transition layer. |
| `INV-07-C027` | Interfaces & Integration | Define compatibility behavior when peers use different supported versions. |
| `INV-07-C028` | Interfaces & Integration | Document payload, concurrency, queue, connection, or resource limits at GitOps transition layer interfaces. |
| `INV-07-C029` | Interfaces & Integration | Provide reference examples and conformance fixtures for GitOps transition layer. |
| `INV-07-C030` | Interfaces & Integration | Create automated integration tests proving GitOps transition layer interoperates with adjacent architectural layers. |
| `INV-07-C031` | Implementation & Configuration | Select and pin approved implementations, versions, or specifications for GitOps transition layer: GitOps, ArgoCD, Flux. |
| `INV-07-C032` | Implementation & Configuration | Separate immutable artifacts from mutable configuration and state for GitOps transition layer. |
| `INV-07-C033` | Implementation & Configuration | Define declarative configuration and secure defaults for GitOps transition layer. |
| `INV-07-C034` | Implementation & Configuration | Validate configuration before activation and fail closed on security-critical errors. |
| `INV-07-C035` | Implementation & Configuration | Support site- and environment-specific configuration without rebuilding immutable artifacts. |
| `INV-07-C036` | Implementation & Configuration | Record configuration provenance, version, author, and activation time. |
| `INV-07-C037` | Implementation & Configuration | Apply atomic or transactional configuration updates where partial application is unsafe. |
| `INV-07-C038` | Implementation & Configuration | Define automatic and operator-driven rollback for failed GitOps transition layer changes. |
| `INV-07-C039` | Implementation & Configuration | Keep credentials and secret material out of ordinary GitOps transition layer configuration and diagnostics. |
| `INV-07-C040` | Implementation & Configuration | Provide a deterministic bootstrap path from an empty node/environment to healthy GitOps transition layer operation. |
| `INV-07-C041` | Security, Trust & Isolation | Threat-model GitOps transition layer against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse. |
| `INV-07-C042` | Security, Trust & Isolation | Apply least privilege to every identity and capability used by GitOps transition layer. |
| `INV-07-C043` | Security, Trust & Isolation | Eliminate ambient filesystem, network, device, kernel, and secret authority wherever GitOps transition layer permits. |
| `INV-07-C044` | Security, Trust & Isolation | Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted. |
| `INV-07-C045` | Security, Trust & Isolation | Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by GitOps transition layer. |
| `INV-07-C046` | Security, Trust & Isolation | Enforce tenant/workload isolation across GitOps transition layer execution, memory, state, network, and device boundaries as applicable. |
| `INV-07-C047` | Security, Trust & Isolation | Encrypt sensitive GitOps transition layer data in transit and at rest with managed key rotation. |
| `INV-07-C048` | Security, Trust & Isolation | Define safe behavior when identity, attestation, policy, key, or time services are unavailable. |
| `INV-07-C049` | Security, Trust & Isolation | Emit tamper-evident audit events for security-sensitive GitOps transition layer operations. |
| `INV-07-C050` | Security, Trust & Isolation | Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion. |
| `INV-07-C051` | Resilience & Failure Handling | Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting GitOps transition layer. |
| `INV-07-C052` | Resilience & Failure Handling | Define automated health and stall detection thresholds for GitOps transition layer. |
| `INV-07-C053` | Resilience & Failure Handling | Implement bounded retry with backoff and jitter only where operations are safe to retry. |
| `INV-07-C054` | Resilience & Failure Handling | Implement admission control, load shedding, or circuit breaking to prevent GitOps transition layer failure cascades. |
| `INV-07-C055` | Resilience & Failure Handling | Define failover behavior without violating isolation, residency, or consistency requirements. |
| `INV-07-C056` | Resilience & Failure Handling | Provide degraded operation when noncritical dependencies are unavailable. |
| `INV-07-C057` | Resilience & Failure Handling | Define crash-consistency, restart, resume, or replay semantics for mutable GitOps transition layer state. |
| `INV-07-C058` | Resilience & Failure Handling | Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant. |
| `INV-07-C059` | Resilience & Failure Handling | Provide quarantine, freeze, disable, or isolation controls for unsafe GitOps transition layer behavior. |
| `INV-07-C060` | Resilience & Failure Handling | Run fault-injection tests proving GitOps transition layer recovery against documented objectives. |
| `INV-07-C061` | Performance & Resource Efficiency | Establish reproducible baselines for GitOps transition layer latency, throughput, startup, CPU, memory, storage, network, and power overhead. |
| `INV-07-C062` | Performance & Resource Efficiency | Define p50, p95, p99, and worst-case performance thresholds for GitOps transition layer. |
| `INV-07-C063` | Performance & Resource Efficiency | Measure GitOps transition layer under steady load, burst load, overload, scale-out, scale-in, and recovery. |
| `INV-07-C064` | Performance & Resource Efficiency | Measure per-workload and per-tenant overhead introduced by GitOps transition layer. |
| `INV-07-C065` | Performance & Resource Efficiency | Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in GitOps transition layer. |
| `INV-07-C066` | Performance & Resource Efficiency | Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit. |
| `INV-07-C067` | Performance & Resource Efficiency | Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out. |
| `INV-07-C068` | Performance & Resource Efficiency | Measure power and thermal impact on constrained edge nodes where relevant. |
| `INV-07-C069` | Performance & Resource Efficiency | Define capacity models and saturation signals that predict when GitOps transition layer needs more resources. |
| `INV-07-C070` | Performance & Resource Efficiency | Block releases that regress approved GitOps transition layer startup, density, throughput, or tail-latency thresholds. |
| `INV-07-C071` | Observability & Explainability | Expose GitOps transition layer health, readiness, version, configuration, dependency status, and active capability set. |
| `INV-07-C072` | Observability & Explainability | Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use. |
| `INV-07-C073` | Observability & Explainability | Emit structured logs with stable node, tenant, workload, component, and operation identifiers. |
| `INV-07-C074` | Observability & Explainability | Propagate trace context across all relevant GitOps transition layer boundaries. |
| `INV-07-C075` | Observability & Explainability | Expose high-cardinality diagnostic detail safely without leaking tenant or secret data. |
| `INV-07-C076` | Observability & Explainability | Record the reason for every automated decision made by GitOps transition layer. |
| `INV-07-C077` | Observability & Explainability | Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints. |
| `INV-07-C078` | Observability & Explainability | Correlate GitOps transition layer events with application release lineage and the live infrastructure graph. |
| `INV-07-C079` | Observability & Explainability | Define telemetry retention, sampling, privacy, and export policy. |
| `INV-07-C080` | Observability & Explainability | Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect. |
| `INV-07-C081` | Testing & Certification | Create unit tests for deterministic GitOps transition layer logic and state transitions. |
| `INV-07-C082` | Testing & Certification | Create contract tests for every public GitOps transition layer interface. |
| `INV-07-C083` | Testing & Certification | Create integration tests with every supported adjacent layer and execution tier. |
| `INV-07-C084` | Testing & Certification | Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to GitOps transition layer. |
| `INV-07-C085` | Testing & Certification | Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by GitOps transition layer. |
| `INV-07-C086` | Testing & Certification | Create concurrency and race-condition tests for shared/distributed GitOps transition layer state. |
| `INV-07-C087` | Testing & Certification | Create security tests derived directly from the GitOps transition layer threat model. |
| `INV-07-C088` | Testing & Certification | Create benchmark, soak, burst, and fleet-scale tests appropriate to GitOps transition layer. |
| `INV-07-C089` | Testing & Certification | Create disaster, partition, reconnect, and degraded-control-plane tests. |
| `INV-07-C090` | Testing & Certification | Require machine-readable acceptance evidence before certifying a GitOps transition layer release for production. |
| `INV-07-C091` | Operations, Release & Governance | Define production SLOs, error budgets, and support commitments for GitOps transition layer. |
| `INV-07-C092` | Operations, Release & Governance | Define canary, staged rollout, rollback, and emergency-disable procedures for GitOps transition layer. |
| `INV-07-C093` | Operations, Release & Governance | Maintain a supported-version compatibility matrix for GitOps transition layer and adjacent dependencies. |
| `INV-07-C094` | Operations, Release & Governance | Define patching, vulnerability response, and end-of-life SLAs for GitOps transition layer. |
| `INV-07-C095` | Operations, Release & Governance | Provide backup, restore, migration, or reconstruction procedures for GitOps transition layer state where applicable. |
| `INV-07-C096` | Operations, Release & Governance | Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks. |
| `INV-07-C097` | Operations, Release & Governance | Define incident severity, paging, escalation, containment, and recovery procedures. |
| `INV-07-C098` | Operations, Release & Governance | Perform recurring access, policy, dependency, configuration, and architecture reviews. |
| `INV-07-C099` | Operations, Release & Governance | Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates. |
| `INV-07-C100` | Operations, Release & Governance | Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness. |

## Production components (54-component checklist)

| # | Component | Priority | Checks | Closure objective |
|---|---|---|---|---|
| 01 | Real Git transport and repository adapter | P0 | 40 | Implement production clone/fetch/pull/ref-resolution, credential flow, shallow/full fetch policy, remote pinning, repository identity verification, and repository availability handling. |
| 02 | Approved-branch/ref policy enforcement | P0 | 40 | Bind every reconciliation to configured repositories and explicitly approved branches, tags, namespaces, ancestry rules, and immutable commit OIDs. |
| 03 | Asymmetric commit/tag signature verification | P0 | 40 | Verify Git commits/tags with production SSH, OpenPGP, or Sigstore trust, including trust roots, revocation, expiry, algorithm policy, and signer identity mapping. |
| 04 | Artifact provenance integration | P0 | 40 | Integrate GAP-07 provenance verification, attestation parsing, certificate-chain validation, transparency-log verification, subject digest binding, builder identity, and policy evaluation. |
| 05 | Argo CD/Flux/controller adapter | P0 | 40 | Implement production reconciliation adapters for supported Kubernetes GitOps controllers and manifest renderers with normalized status and bounded operations. |
| 06 | Live-state reader and applier | P0 | 40 | Replace the in-memory live-state stand-in with authenticated production control-plane readers/writers using concurrency preconditions, field ownership, and safe destructive-operation handling. |
| 07 | Atomic apply/transaction strategy | P0 | 40 | Provide deterministic dependency ordering, preflight/dry-run, transaction boundaries, partial-failure detection, compensation/rollback, and recovery quarantine. |
| 08 | Persistent controller state | P0 | 40 | Persist commits, applied history, drift reports, leases, cursors, checkpoints, reconciliation intent, recovery metadata, and schema versions durably. |
| 09 | Leader election / duplicate-controller protection | P0 | 40 | Provide leases, fencing tokens/epochs, CAS ownership, stale-leader suppression, takeover rules, and split-brain prevention. |
| 10 | Authentication and authorization boundary | P0 | 40 | Authenticate operators/services and enforce least-privilege RBAC/ABAC/capability checks, tenant scope, privileged approvals, and auditable authorization decisions. |
| 11 | Secret/key management integration | P0 | 40 | Use managed KMS/HSM/secret-store integration for trust/key material, rotation, revocation, least-privilege access, short-lived credentials, and memory/log hygiene. |
| 12 | Tamper-evident audit ledger | P0 | 40 | Create an append-only durable audit trail with canonical events, hash chaining/signatures, retention, WORM/immutability controls, verification, and export. |
| 13 | Versioned interface schemas | P0 | 40 | Ship typed, versioned schemas for PK_GITOPS_SYNC/1, PK_GITOPS_DRIFT/1, PK_GITOPS_VERIFY/1, status, and error envelopes with compatibility rules. |
| 14 | Machine-readable error model | P0 | 40 | Define stable error codes, categories, retryability, severity, causal metadata, correlation IDs, safe details, and cross-version meaning guarantees. |
| 15 | Production bootstrap/deployment packaging | P0 | 40 | Ship deterministic OCI/deployment assets, least-privilege manifests, SBOM/provenance/signing, install/upgrade/rollback paths, and clean-environment verification. |
| 16 | Retry/backoff/jitter policy | P1 | 40 | Define operation-specific bounded retry, exponential backoff with jitter, idempotency keys, replay suppression, cancellation, deadlines, retry budgets, and backpressure. |
| 17 | Dependency circuit breaking / admission control | P1 | 40 | Implement bounded queues, rate limits, tenant quotas, fair scheduling, circuit breakers, saturation detection, and prioritized load shedding. |
| 18 | Offline/disconnected operation policy | P1 | 40 | Define fail-closed/read-only/cache-backed modes, cached-ref and trust age limits, stale-state rules, backlog bounds, reconnect reconciliation, and divergence handling. |
| 19 | Crash recovery and replay | P1 | 40 | Provide WAL/journaling, intent-before-effect recording, checkpoints, resume cursors, duplicate suppression, ambiguous-outcome readback, and crash-consistency tests. |
| 20 | Quarantine/freeze/emergency disable | P1 | 40 | Provide global and scoped reconciliation pause, target quarantine, kill switch, durable freeze state, audited override, expiry, and recovery workflow. |
| 21 | Multi-tenant hard isolation | P1 | 40 | Enforce tenant separation across identities, credentials, namespaces, storage, caches, network, quotas, controller scope, telemetry, and audit evidence. |
| 22 | Residency/site policy enforcement | P1 | 40 | Enforce region/site/locality allowlists, credential-to-site binding, failover constraints, data/control-plane residency, backup/telemetry locality, and exceptions. |
| 23 | Policy engine integration | P1 | 40 | Integrate OPA/CEL/Rego or equivalent policy evaluation with signed/versioned bundles, deterministic inputs, deny reasons, waivers, availability semantics, and resource bounds. |
| 24 | Manifest/input parser hardening | P1 | 40 | Harden YAML/JSON/Helm/Kustomize parsing/rendering using safe parsers, schema validation, duplicate-key rejection, expansion/depth/size limits, sandboxing, and hostile-input tests. |
| 25 | Supply-chain dependency controls | P1 | 40 | Pin dependencies and images, generate SBOMs, scan vulnerabilities/licenses, verify provenance/signatures, prevent dependency confusion, and record reproducible-build metadata. |
| 26 | Network security profile | P1 | 40 | Enforce TLS/mTLS policy, certificate validation/rotation, DNS and redirect controls, egress allowlists, proxy rules, timeout/pool bounds, and MITM/downgrade resistance. |
| 27 | Replay/freshness protection | P1 | 40 | Bind acceptance to immutable digests and policy/trust context, enforce generations/freshness, prevent protected-ref rollback, invalidate stale verification, and audit rollback exceptions. |
| 28 | Time service behavior | P1 | 40 | Define trusted time, monotonic-vs-wall-clock use, skew limits, certificate/provenance/lease semantics, clock-jump detection, degraded mode, and time-source protection. |
| 29 | Configuration system | P1 | 40 | Provide versioned typed configuration, explicit precedence, secure defaults, offline validation, hot-reload boundaries, atomic activation/rollback, provenance, and secret references. |
| 30 | Compatibility matrix | P1 | 40 | Declare and test supported Git servers, Argo CD, Flux, Kubernetes, Helm, Kustomize, Python, OS/CPU, container runtime, storage, KMS, policy engines, schemas, and adjacent components. |
| 31 | Migration plan from traditional IaC | P1 | 40 | Provide inventory, coexistence states, dual-observe/dual-run safety, ownership partitioning, authority cutover, stabilization criteria, rollback boundary, and lineage preservation. |
| 32 | Backup/restore/reconstruction procedure | P1 | 40 | Define protected datasets, RPO/RTO, encrypted backup formats, integrity validation, isolated restore testing, point-in-time/reconstruction paths, and evidence. |
| 33 | Incident runbook | P1 | 40 | Define severity, paging, roles, containment, trust/key compromise procedures, rollback criteria, evidence preservation, communication/escalation, and exercised playbooks. |
| 34 | Patch/EOL/vulnerability SLA | P1 | 40 | Define supported lifetime, maintenance windows, CVE triage/remediation objectives, emergency patch path, deprecation, rolling upgrade, rollback, and EOL evidence. |
| 35 | Metrics endpoint | P2 | 40 | Expose authenticated/bounded counters, gauges, and histograms for reconciliation, verification, policy, drift, backlog, latency, saturation, dependencies, leader state, and resources. |
| 36 | Structured operational logging | P2 | 40 | Emit versioned structured events with stable codes, identity/context fields, correlation, centralized redaction, bounded size/cardinality, severity rules, and collector-failure safety. |
| 37 | Distributed tracing | P2 | 40 | Propagate trace context across Git, trust/provenance, rendering, policy, state reads, apply, persistence, retries, queues, and controller calls with safe bounded attributes. |
| 38 | Operator explain view | P2 | 40 | Expose durable, read-only explanations linking source revision, signer/provenance, policy version, live delta, target, resource actions, overrides, audit IDs, and traces. |
| 39 | Dashboards and alerts | P2 | 40 | Ship actionable dashboards and alerts for SLO burn, drift, unsigned/untrusted refs, stalls, partial apply, rollback failures, dependency health, saturation, and leader churn. |
| 40 | Telemetry retention/privacy policy | P2 | 40 | Define sensitivity classification, sampling, retention, redaction, high-cardinality limits, access control, residency, export destinations, deletion, and privacy review. |
| 41 | Integration tests against real Git and target control planes | P2 | 40 | Exercise real supported Git servers and target control planes end-to-end, including signed refs, drift, outages, upgrades, controller compatibility, and evidence capture. |
| 42 | Contract tests for all public interfaces | P2 | 40 | Provide schema-derived valid/invalid fixtures, consumer/provider compatibility, N-1/N behavior, stable error validation, language-neutral conformance runners, and machine-readable results. |
| 43 | Security/adversarial test suite | P2 | 40 | Test signature confusion, revocation, replay, injection, SSRF, parser bombs, auth bypass, privilege escalation, tenant escape, resource exhaustion, and sensitive-data leakage. |
| 44 | Fuzz testing | P2 | 40 | Fuzz repository metadata, refs, signatures, provenance, manifests, schemas, renderer inputs, policy inputs, and APIs with structure-aware corpora, minimization, and regression retention. |
| 45 | Fault-injection/chaos tests | P2 | 40 | Inject Git/KMS/policy/database/target outages, DNS/TLS faults, crashes, stale leaders, clock skew, disk failure, partial apply, and recovery races with objective measurement. |
| 46 | Scale/soak/burst benchmarks | P2 | 40 | Benchmark repository/object/tenant/target scale, fan-out, latency percentiles, CPU/memory/storage/network, cold/warm start, saturation, recovery, and long-duration stability. |
| 47 | Release regression gates | P2 | 40 | Machine-enforce correctness, security, compatibility, migration, coverage, vulnerability, latency, resource, and reliability thresholds against immutable baselines. |
| 48 | Cross-platform/runtime certification | P2 | 40 | Verify declared CPU, OS, Python/runtime, container runtime, Kubernetes/provider combinations, filesystem/locale/time/cert differences, and deterministic serialization/hashing. |
| 49 | Coverage/reporting artifacts | P2 | 40 | Generate risk-weighted coverage, branch/condition coverage, mutation results, static type/lint/security analysis, machine-readable test reports, and revision-bound evidence. |
| 50 | Full checklist evidence bundle | P2 | 40 | Ship MASTER.md, traceability matrix, gate outputs, dependency evidence, tests, scans, SBOM, provenance, benchmark/chaos results, waivers, and integrity manifest. |
| 51 | MASTER.md | DOC | 40 | Ship the canonical master requirements/checklist document with stable IDs, version consistency, external-dependency disclosure, traceability, and packaging verification. |
| 52 | Standalone packaging metadata | DOC | 40 | Add pyproject/package metadata, Python/dependency constraints, build-system definition, isolated wheel/sdist builds, package-data rules, and installation/import smoke tests. |
| 53 | License/NOTICE files | DOC | 40 | Ship governing license and required notices/attributions in every distributable, automate dependency license inventory, and define contribution/licensing expectations. |
| 54 | Generated API/reference documentation | DOC | 40 | Generate release-versioned schema/API/config/error/operator reference docs with executable examples, security guidance, compatibility/deprecation data, and CI validation. |

## Traceability and evidence

* Requirement → design: `components/docs/REQUIREMENTS.md`, `components/docs/ADR-001-v5-production-overlay.md`.
* Design → implementation → test → evidence: `components/checklist/bindings.py` and the engine output `components/evidence/CHECKLIST_STATUS.json` (2,160 records), hash-chained in `GATE_LEDGER.jsonl`.
* Packaging verification: `MANIFEST.sha256` over every shipped file; `tests/test_overlay_integrity.py`.
* A skipped or NOT_RUN required check is never a pass; PASS additionally requires a named owner and an independent human reviewer (none assigned — `components/docs/OWNERS.md`).
