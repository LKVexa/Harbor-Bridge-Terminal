# INV-31 Missing Components — Post-Hardening Audit

**Version audited:** 4.2.0  
**Audit date:** 2026-09-22  
**Checklist status:** 25 implemented, 22 partial, 53 missing.

This inventory is conservative: a requirement is marked implemented only when concrete repository-local code/specification/test evidence exists for the owned scope. The external `pk_core` gate could not be executed because `pk_core` is not present in the supplied archive/environment.

## Archive-level missing components

- **pk_core framework** (blocking): Required by component.py and contract.py and by the 100-item gate, but not bundled or otherwise available in the supplied archive.
- **MASTER.md source artifact** (high): The prior README claimed it was carried verbatim, but it is absent; 4.2.0 removes the inaccurate claim rather than fabricating the source.
- **Dandelion implementation/specification pin** (blocking): CHECKLIST C031 requires an approved Dandelion implementation/version/specification; no Dandelion artifact or version pin is present.
- **reproducible package/dependency manifest** (high): No pyproject.toml/setup.py/requirements lock declares how to install this package and its pk_core dependency reproducibly.
- **production conformance/evidence outputs** (blocking): No sealed evidence ledger or PK_GATE_RESULTS artifact is included, and the gate cannot be regenerated without pk_core.
- **adjacent-layer integration adapters/tests** (high): No executable integration with PLN-04, INV-26, PLN-05, or GAP-09 is included.
- **CI/release automation** (medium): No CI workflow runs tests, optimized-mode checks, schema validation, security scans, or release gates.
- **license/notice metadata** (medium): No LICENSE/NOTICE or package license metadata is present, so redistribution terms are unspecified in this archive.
- **ownership/support metadata** (high): No accountable owner, CODEOWNERS, support contact, or escalation path is defined.
- **performance/fault/security certification harnesses** (high): No benchmark/soak/fleet, fault-injection, fuzz, or comprehensive adversarial test harnesses are included.

## Architecture & Scope

- **INV-31-C005 — PARTIAL:** Document assumptions Function execution architecture makes about nodes, runtimes, networks, storage, and control planes.  
  Gap: Assumptions are documented for the local runtime, but node/runtime/network/storage/control-plane assumptions are not exhaustively specified.
- **INV-31-C009 — MISSING:** Assign an accountable owner and escalation path for Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C010 — MISSING:** Approve an architecture decision record for Function execution architecture, its technologies (Dandelion), and its function (HTTP/RPC pure-compute functions represented as DAGs).  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.

## Requirements & Semantics

- **INV-31-C011 — MISSING:** Translate the source function of Function execution architecture — HTTP/RPC pure-compute functions represented as DAGs — into testable SHALL-level requirements.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C012 — MISSING:** Define functional requirements for Function execution architecture across cloud, datacenter, near-edge, and far-edge contexts where applicable.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C013 — PARTIAL:** Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.  
  Gap: Isolation and warm-rate SLOs exist, but latency, availability, determinism and other production NFR thresholds are not complete.
- **INV-31-C016 — PARTIAL:** Define versioning and backward-compatibility requirements for Function execution architecture.  
  Gap: Schemas are versioned, but backward/forward compatibility and deprecation rules are incomplete.
- **INV-31-C017 — PARTIAL:** Define capacity ceilings, quotas, and fairness semantics relevant to Function execution architecture.  
  Gap: Concurrency and local pool ceilings exist; tenant quotas and fairness semantics are not implemented.
- **INV-31-C018 — MISSING:** Define behavior when network connectivity is intermittent or absent.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C019 — MISSING:** Define precedence rules when Function execution architecture requirements conflict with security, residency, SLO, or cost constraints.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.

## Interfaces & Integration

- **INV-31-C023 — MISSING:** Define authentication requirements at each Function execution architecture boundary.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C024 — MISSING:** Define authorization and explicit capability requirements at each Function execution architecture boundary.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C025 — PARTIAL:** Define timeout, cancellation, retry, idempotency, and backpressure semantics for Function execution architecture.  
  Gap: Concurrency refusal/backpressure is local; timeout, cancellation, retry and idempotency contracts are not implemented.
- **INV-31-C026 — MISSING:** Define structured failure codes and machine-readable error details for Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C027 — MISSING:** Define compatibility behavior when peers use different supported versions.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C029 — PARTIAL:** Provide reference examples and conformance fixtures for Function execution architecture.  
  Gap: Examples and tests exist, but a versioned fixture corpus covering both schemas and failure cases is incomplete.
- **INV-31-C030 — MISSING:** Create automated integration tests proving Function execution architecture interoperates with adjacent architectural layers.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.

## Implementation & Configuration

- **INV-31-C031 — MISSING:** Select and pin approved implementations, versions, or specifications for Function execution architecture: Dandelion.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C033 — PARTIAL:** Define declarative configuration and secure defaults for Function execution architecture.  
  Gap: Secure defaults are present, but configuration is constructor-based rather than a declarative, versioned configuration artifact.
- **INV-31-C036 — MISSING:** Record configuration provenance, version, author, and activation time.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C037 — MISSING:** Apply atomic or transactional configuration updates where partial application is unsafe.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C038 — MISSING:** Define automatic and operator-driven rollback for failed Function execution architecture changes.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C040 — PARTIAL:** Provide a deterministic bootstrap path from an empty node/environment to healthy Function execution architecture operation.  
  Gap: Bootstrap commands are documented, but production bootstrap cannot complete from this archive because pk_core and adjacent services are absent.

## Security, Trust & Isolation

- **INV-31-C041 — PARTIAL:** Threat-model Function execution architecture against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.  
  Gap: Local lifecycle threats are documented, but malicious workload, supply-chain and control-plane abuse coverage is incomplete.
- **INV-31-C042 — MISSING:** Apply least privilege to every identity and capability used by Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C043 — MISSING:** Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Function execution architecture permits.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C044 — MISSING:** Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C045 — MISSING:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C047 — MISSING:** Encrypt sensitive Function execution architecture data in transit and at rest with managed key rotation.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C048 — MISSING:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C049 — MISSING:** Emit tamper-evident audit events for security-sensitive Function execution architecture operations.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C050 — MISSING:** Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.

## Resilience & Failure Handling

- **INV-31-C051 — PARTIAL:** Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Function execution architecture.  
  Gap: Local failure modes are documented, but node/site/provider/network/control-plane failure coverage is incomplete.
- **INV-31-C052 — MISSING:** Define automated health and stall detection thresholds for Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C053 — MISSING:** Implement bounded retry with backoff and jitter only where operations are safe to retry.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C055 — MISSING:** Define failover behavior without violating isolation, residency, or consistency requirements.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C056 — MISSING:** Provide degraded operation when noncritical dependencies are unavailable.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C058 — MISSING:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C060 — MISSING:** Run fault-injection tests proving Function execution architecture recovery against documented objectives.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.

## Performance & Resource Efficiency

- **INV-31-C061 — MISSING:** Establish reproducible baselines for Function execution architecture latency, throughput, startup, CPU, memory, storage, network, and power overhead.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C062 — MISSING:** Define p50, p95, p99, and worst-case performance thresholds for Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C063 — MISSING:** Measure Function execution architecture under steady load, burst load, overload, scale-out, scale-in, and recovery.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C064 — MISSING:** Measure per-workload and per-tenant overhead introduced by Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C065 — MISSING:** Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C066 — MISSING:** Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C067 — PARTIAL:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.  
  Gap: Concurrency, identifiers and instance count are bounded; arbitrary scratch value size and external queue/buffer fan-out are not comprehensively bounded here.
- **INV-31-C068 — MISSING:** Measure power and thermal impact on constrained edge nodes where relevant.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C069 — PARTIAL:** Define capacity models and saturation signals that predict when Function execution architecture needs more resources.  
  Gap: Pool saturation counters exist, but a validated fleet capacity model is absent.
- **INV-31-C070 — MISSING:** Block releases that regress approved Function execution architecture startup, density, throughput, or tail-latency thresholds.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.

## Observability & Explainability

- **INV-31-C071 — PARTIAL:** Expose Function execution architecture health, readiness, version, configuration, dependency status, and active capability set.  
  Gap: Pool readiness/configuration is exposed, but package version, external dependency health and active-capability status are incomplete.
- **INV-31-C072 — PARTIAL:** Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.  
  Gap: Counters exist in-memory, but there is no metrics exporter or external telemetry integration in this archive.
- **INV-31-C073 — MISSING:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C074 — MISSING:** Propagate trace context across all relevant Function execution architecture boundaries.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C075 — PARTIAL:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.  
  Gap: Scratch is excluded from diagnostics, but a formal high-cardinality diagnostic/redaction policy is absent.
- **INV-31-C077 — PARTIAL:** Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.  
  Gap: Decision reasons and snapshots are operator-readable, but there is no complete explain surface tying topology/policy/constraints together.
- **INV-31-C078 — MISSING:** Correlate Function execution architecture events with application release lineage and the live infrastructure graph.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C079 — MISSING:** Define telemetry retention, sampling, privacy, and export policy.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C080 — MISSING:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.

## Testing & Certification

- **INV-31-C082 — PARTIAL:** Create contract tests for every public Function execution architecture interface.  
  Gap: Both interfaces have schemas and unit coverage, but no independent schema validator/transport-level contract suite is bundled.
- **INV-31-C083 — MISSING:** Create integration tests with every supported adjacent layer and execution tier.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C084 — MISSING:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C085 — MISSING:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C087 — PARTIAL:** Create security tests derived directly from the Function execution architecture threat model.  
  Gap: Isolation/resource tests cover several local threats, but the full threat model does not have adversarial tests.
- **INV-31-C088 — MISSING:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C089 — MISSING:** Create disaster, partition, reconnect, and degraded-control-plane tests.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C090 — MISSING:** Require machine-readable acceptance evidence before certifying a Function execution architecture release for production.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.

## Operations, Release & Governance

- **INV-31-C091 — PARTIAL:** Define production SLOs, error budgets, and support commitments for Function execution architecture.  
  Gap: SLO/error-budget declarations exist; support commitments and operational ownership are absent.
- **INV-31-C092 — PARTIAL:** Define canary, staged rollout, rollback, and emergency-disable procedures for Function execution architecture.  
  Gap: Drain and rollback responsibilities are documented, but canary/staged rollout automation and procedures are absent.
- **INV-31-C093 — MISSING:** Maintain a supported-version compatibility matrix for Function execution architecture and adjacent dependencies.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C094 — MISSING:** Define patching, vulnerability response, and end-of-life SLAs for Function execution architecture.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C096 — PARTIAL:** Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks.  
  Gap: Day-0/day-1/day-2 notes exist, but they are not full production runbooks with commands, decision trees and escalation paths.
- **INV-31-C097 — MISSING:** Define incident severity, paging, escalation, containment, and recovery procedures.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C098 — MISSING:** Perform recurring access, policy, dependency, configuration, and architecture reviews.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C099 — MISSING:** Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.  
  Gap: No complete repository-local implementation, specification, test, or production evidence for this requirement was found in the supplied archive.
- **INV-31-C100 — PARTIAL:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.  
  Gap: The parent pk_core gate is referenced, but no completed production-exit evidence/gate artifact is included and pk_core is unavailable in this archive.

## Machine-readable inventory

See `POST_AUDIT.json` for all 100 checklist items, including implemented items and evidence paths.
