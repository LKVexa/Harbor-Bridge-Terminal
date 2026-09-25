# PLN-07 v4.2.0 — Post-hardening audit

## Audit conclusion

The supplied 4.1.0 archive contained a capability-grant reference implementation plus a 100-item checklist, but it did not contain enough implementation evidence to justify a blanket production-ready conclusion. Version 4.2.0 fixes concrete grant-model defects, makes the security core testable without `pk_core`, adds typed schemas and a threat-model document, and separates implemented evidence from architectural intent.

`pk_core` and the named sibling planes were not included in the archive. The framework-level gate and cross-plane integrations therefore could not be executed here; the three tests in `tests/test_component.py` remain skipped in this isolated package.

## Changes applied

- Extracted security-critical grant logic into dependency-light `grants.py`.
- Enforced parent/tenant/scope/expiry/depth constraints during construction and verification.
- Added strict input bounds, no-op attenuation rejection, cycle protection, structured errors/results, canonical signing payloads, and optional fail-closed signature verification.
- Preserved the 4.x 16-hex grant ID algorithm and added a full SHA-256 audit fingerprint.
- Added three versioned JSON schemas, 12 standalone tests, `SECURITY.md`, this matrix, and `MISSING_COMPONENTS.md`.
- Corrected the prior README claim that `MASTER.md` was bundled and the prior conflation of checklist answers with production implementation evidence.

## Validation performed

- `python -m compileall -q .` — PASS.
- `python tests/test_grants.py` — 12/12 PASS.
- `python -O tests/test_grants.py` — 12/12 PASS.
- Deterministic invariant fuzz smoke run — 5,000 generated roots/chains PASS.
- Local depth-5 verification smoke benchmark — p99 0.1743 ms over 5,000 iterations; median 0.0301 ms. Diagnostic only, not production certification.
- `python tests/test_component.py` — 3 SKIPPED because `pk_core` is absent.
- All three JSON schema documents parse successfully.

## Requirement traceability summary

- Present: **9**
- Partial: **30**
- Missing: **61**

“Present” means direct repository evidence exists. “Partial” means relevant implementation/documentation exists but is incomplete. “Missing” means the required component/evidence is absent.

## 100-requirement traceability matrix

| Requirement | Status | Requirement summary | Audit evidence / unresolved gap |
|---|---|---|---|
| PLN-07-C001 | Present | Define the exact production responsibility of Security plane. | `contract.py` and README define the responsibility. |
| PLN-07-C002 | Present | Document what Security plane owns and explicitly does not own. | `contract.py` defines `owns` and `not_owns`. |
| PLN-07-C003 | Present | Identify upstream, downstream, and peer dependencies of Security plane. | `contract.py` enumerates upstream/downstream/peer dependencies. |
| PLN-07-C004 | Present | Define the authoritative source of truth used by Security plane. | `contract.py` declares the issued, signature-verified grant as source of truth. |
| PLN-07-C005 | Partial | Document assumptions Security plane makes about nodes, runtimes, networks, storage, and control planes. | Clock/revocation/holder assumptions exist, but node/runtime/network/storage/control-plane assumptions are incomplete. |
| PLN-07-C006 | Partial | Define tenant, environment, site, and workload boundaries relevant to Security plane. | Contract names tenant/environment/site/workload boundaries; runtime enforcement currently models tenant and subject only. |
| PLN-07-C007 | Present | Separate mandatory Security plane capabilities from optional optimizations. | Mandatory and optional capabilities are separated in `contract.py`. |
| PLN-07-C008 | Partial | Document unsupported deployment patterns and non-goals for Security plane. | Non-goals exist, but unsupported deployment patterns are not exhaustively specified. |
| PLN-07-C009 | Missing | Assign an accountable owner and escalation path for Security plane. | No accountable owner or escalation path is supplied. |
| PLN-07-C010 | Missing | Approve an architecture decision record for Security plane, its technologies (Source-derived architectural plane), and its function (WIT capabilities, explicit authority, hardware VM isolation, CHERI/SFI/Spectre mitigations, and workload-specific sandbox boundaries.). | No approved ADR is supplied for WIT capabilities, hardware VM isolation, CHERI/SFI/Spectre controls, or sandbox boundaries. |
| PLN-07-C011 | Partial | Translate the source function of Security plane — WIT capabilities, explicit authority, hardware VM isolation, CHERI/SFI/Spectre mitigations, and workload-specific sandbox boundaries. — into testable SHALL-level requirements. | Mandatory capability statements exist, but the full source function is not translated into SHALL requirements with verification criteria. |
| PLN-07-C012 | Missing | Define functional requirements for Security plane across cloud, datacenter, near-edge, and far-edge contexts where applicable. | No cloud/datacenter/near-edge/far-edge requirement profile exists. |
| PLN-07-C013 | Partial | Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable. | Some SLOs are defined, but availability/durability/consistency/isolation/determinism requirements are incomplete. |
| PLN-07-C014 | Missing | Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Security plane. | No complete success/partial/degraded/retryable/terminal failure state model exists. |
| PLN-07-C015 | Missing | Define lifecycle states and legal state transitions managed or exposed by Security plane. | No explicit lifecycle state machine or legal transition model exists. |
| PLN-07-C016 | Partial | Define versioning and backward-compatibility requirements for Security plane. | Version files exist and legacy grant IDs are preserved, but no supported compatibility policy is defined. |
| PLN-07-C017 | Missing | Define capacity ceilings, quotas, and fairness semantics relevant to Security plane. | No tenant quotas, fairness policy, or system capacity ceilings are defined. |
| PLN-07-C018 | Partial | Define behavior when network connectivity is intermittent or absent. | Disconnected operation is discussed and GAP-04 is referenced, but the dependency is absent and no standalone mechanism exists. |
| PLN-07-C019 | Missing | Define precedence rules when Security plane requirements conflict with security, residency, SLO, or cost constraints. | No precedence rules for security/residency/SLO/cost conflicts are defined. |
| PLN-07-C020 | Present | Maintain a requirements traceability matrix from each Security plane requirement to implementation and verification evidence. | This `POST_AUDIT.md` is the 100-item implementation/evidence traceability matrix. |
| PLN-07-C021 | Partial | Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Security plane. | Four logical interfaces are named, but transport/WIT/RPC/control-plane boundary details are not fully specified. |
| PLN-07-C022 | Present | Use versioned typed schemas for all externally visible Security plane contracts. | Versioned JSON schemas now exist for `PK_GRANT/1`, `PK_GRANT_VERIFICATION/1`, and `PK_REVOCATION/1`. |
| PLN-07-C023 | Missing | Define authentication requirements at each Security plane boundary. | Authentication requirements for each boundary are not defined or implemented. |
| PLN-07-C024 | Partial | Define authorization and explicit capability requirements at each Security plane boundary. | Capability verification exists; issuance authorization still depends on the absent GAP-13 policy engine. |
| PLN-07-C025 | Missing | Define timeout, cancellation, retry, idempotency, and backpressure semantics for Security plane. | No timeout, cancellation, retry, idempotency, or backpressure contract exists. |
| PLN-07-C026 | Partial | Define structured failure codes and machine-readable error details for Security plane. | Grant verification exposes machine-readable codes/results; other interface failure schemas remain incomplete. |
| PLN-07-C027 | Missing | Define compatibility behavior when peers use different supported versions. | No peer-version negotiation or mixed-version behavior is specified. |
| PLN-07-C028 | Partial | Document payload, concurrency, queue, connection, or resource limits at Security plane interfaces. | Scope cardinality and delegation depth are bounded; transport payload, concurrency, queue, connection, and resource limits are not. |
| PLN-07-C029 | Partial | Provide reference examples and conformance fixtures for Security plane. | Unit fixtures exist, but there is no complete reference-example/conformance-fixture set for all public interfaces. |
| PLN-07-C030 | Missing | Create automated integration tests proving Security plane interoperates with adjacent architectural layers. | No executable integration suite covers every adjacent architectural layer. |
| PLN-07-C031 | Missing | Select and pin approved implementations, versions, or specifications for Security plane: Source-derived architectural plane. | No pinned implementation/specification manifest is supplied for `pk_core` or sibling components. |
| PLN-07-C032 | Missing | Separate immutable artifacts from mutable configuration and state for Security plane. | No explicit immutable-artifact versus mutable-config/state model is documented. |
| PLN-07-C033 | Missing | Define declarative configuration and secure defaults for Security plane. | No declarative configuration schema or secure-default configuration package exists. |
| PLN-07-C034 | Missing | Validate configuration before activation and fail closed on security-critical errors. | No configuration validation/activation path exists. |
| PLN-07-C035 | Missing | Support site- and environment-specific configuration without rebuilding immutable artifacts. | No site/environment configuration overlay mechanism exists. |
| PLN-07-C036 | Missing | Record configuration provenance, version, author, and activation time. | No configuration provenance model records version, author, and activation time. |
| PLN-07-C037 | Missing | Apply atomic or transactional configuration updates where partial application is unsafe. | No atomic/transactional configuration-update mechanism exists. |
| PLN-07-C038 | Missing | Define automatic and operator-driven rollback for failed Security plane changes. | No automated/operator rollback mechanism for configuration changes exists. |
| PLN-07-C039 | Missing | Keep credentials and secret material out of ordinary Security plane configuration and diagnostics. | No configuration/diagnostic redaction policy or enforcement exists. |
| PLN-07-C040 | Partial | Provide a deterministic bootstrap path from an empty node/environment to healthy Security plane operation. | README has bootstrap guidance and lazy import works without `pk_core`, but deterministic production bootstrap still needs pinned external dependencies. |
| PLN-07-C041 | Present | Threat-model Security plane against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse. | `SECURITY.md` documents malicious tenants/workloads, hostile inputs, trust boundaries, signing, time, revocation, and residual dependencies. |
| PLN-07-C042 | Partial | Apply least privilege to every identity and capability used by Security plane. | Grant scope/attenuation enforce least authority within the model; operational identities and sibling services are not covered. |
| PLN-07-C043 | Partial | Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Security plane permits. | The model removes ambient capability authority, but filesystem/network/device/kernel/secret enforcement belongs to missing runtime/sandbox components. |
| PLN-07-C044 | Missing | Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted. | No node/peer/artifact/provider/control-plane actor authentication implementation exists. |
| PLN-07-C045 | Partial | Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Security plane. | Canonical signature payloads and fail-closed signature hooks exist; concrete trust roots/provenance and GAP-07 are absent. |
| PLN-07-C046 | Partial | Enforce tenant/workload isolation across Security plane execution, memory, state, network, and device boundaries as applicable. | Tenant crossing is rejected in grant chains, but execution/memory/state/network/device isolation is not implemented here. |
| PLN-07-C047 | Missing | Encrypt sensitive Security plane data in transit and at rest with managed key rotation. | No encryption-at-rest/in-transit implementation or key-rotation integration exists. |
| PLN-07-C048 | Partial | Define safe behavior when identity, attestation, policy, key, or time services are unavailable. | Signature enforcement can fail closed; unavailable identity/attestation/policy/key/time service behavior is otherwise incomplete. |
| PLN-07-C049 | Missing | Emit tamper-evident audit events for security-sensitive Security plane operations. | No tamper-evident audit-event emitter or durable audit ledger exists. |
| PLN-07-C050 | Partial | Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion. | Security tests cover several grant threats, but injection/spoofing/escape/side-channel/resource-exhaustion coverage is incomplete. |
| PLN-07-C051 | Partial | Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Security plane. | Contract lists several grant failure modes, but component/process/VM/node/site/network/provider/control-plane failure enumeration is incomplete. |
| PLN-07-C052 | Missing | Define automated health and stall detection thresholds for Security plane. | No automated health or stall detector exists. |
| PLN-07-C053 | Missing | Implement bounded retry with backoff and jitter only where operations are safe to retry. | No bounded retry/backoff/jitter mechanism exists. |
| PLN-07-C054 | Missing | Implement admission control, load shedding, or circuit breaking to prevent Security plane failure cascades. | No admission-control, load-shedding, or circuit-breaker implementation exists. |
| PLN-07-C055 | Missing | Define failover behavior without violating isolation, residency, or consistency requirements. | No failover design or executable failover mechanism exists. |
| PLN-07-C056 | Partial | Provide degraded operation when noncritical dependencies are unavailable. | GAP-04 integration describes a degraded disconnected case, but GAP-04 is absent and no local degraded-mode controller exists. |
| PLN-07-C057 | Missing | Define crash-consistency, restart, resume, or replay semantics for mutable Security plane state. | No durable mutable-state crash/restart/resume/replay design exists; revocations are currently an in-memory set. |
| PLN-07-C058 | Missing | Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant. | No split-brain, stale-controller, duplicate-ownership, or duplicate-execution control exists. |
| PLN-07-C059 | Missing | Provide quarantine, freeze, disable, or isolation controls for unsafe Security plane behavior. | No quarantine/freeze/disable control surface exists. |
| PLN-07-C060 | Missing | Run fault-injection tests proving Security plane recovery against documented objectives. | No persistent fault-injection test suite exists. |
| PLN-07-C061 | Missing | Establish reproducible baselines for Security plane latency, throughput, startup, CPU, memory, storage, network, and power overhead. | No reproducible performance/resource/power baseline artifact exists. |
| PLN-07-C062 | Partial | Define p50, p95, p99, and worst-case performance thresholds for Security plane. | A p99 depth-5 target exists and an audit-time local smoke benchmark passed; p50/p95/worst-case and release-grade thresholds are incomplete. |
| PLN-07-C063 | Missing | Measure Security plane under steady load, burst load, overload, scale-out, scale-in, and recovery. | No steady/burst/overload/scale/recovery benchmark suite exists. |
| PLN-07-C064 | Missing | Measure per-workload and per-tenant overhead introduced by Security plane. | No per-workload/per-tenant overhead measurements exist. |
| PLN-07-C065 | Missing | Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Security plane. | No serialization/copy/context-switch/network-hop/duplication analysis exists. |
| PLN-07-C066 | Missing | Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit. | No documented optimization implementation/decision record exists. |
| PLN-07-C067 | Partial | Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out. | Depth and scope cardinality are bounded; memory/queue/buffer/concurrency/fan-out limits are not. |
| PLN-07-C068 | Missing | Measure power and thermal impact on constrained edge nodes where relevant. | No edge power/thermal measurements exist. |
| PLN-07-C069 | Missing | Define capacity models and saturation signals that predict when Security plane needs more resources. | No capacity model or saturation predictor exists. |
| PLN-07-C070 | Missing | Block releases that regress approved Security plane startup, density, throughput, or tail-latency thresholds. | No automated release performance regression gate exists. |
| PLN-07-C071 | Missing | Expose Security plane health, readiness, version, configuration, dependency status, and active capability set. | No health/readiness/config/dependency/active-capability endpoint exists. |
| PLN-07-C072 | Partial | Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use. | Metric names are declared in `contract.py`, but no metrics emitter/exporter is implemented. |
| PLN-07-C073 | Missing | Emit structured logs with stable node, tenant, workload, component, and operation identifiers. | No structured logging implementation with stable correlation identifiers exists. |
| PLN-07-C074 | Missing | Propagate trace context across all relevant Security plane boundaries. | No trace-context propagation exists. |
| PLN-07-C075 | Missing | Expose high-cardinality diagnostic detail safely without leaking tenant or secret data. | No high-cardinality diagnostic surface/redaction mechanism exists. |
| PLN-07-C076 | Partial | Record the reason for every automated decision made by Security plane. | `verify_detailed` records verification reason/code; issue/attenuate/revoke and operational decisions are not uniformly reason-logged. |
| PLN-07-C077 | Missing | Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints. | No operator explain view exists. |
| PLN-07-C078 | Missing | Correlate Security plane events with application release lineage and the live infrastructure graph. | No release-lineage/live-infrastructure-graph correlation exists. |
| PLN-07-C079 | Missing | Define telemetry retention, sampling, privacy, and export policy. | No telemetry retention/sampling/privacy/export policy exists. |
| PLN-07-C080 | Missing | Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect. | No dashboards or alert rules exist. |
| PLN-07-C081 | Present | Create unit tests for deterministic Security plane logic and state transitions. | `tests/test_grants.py` provides framework-independent deterministic unit tests and passes under normal and optimized Python. |
| PLN-07-C082 | Partial | Create contract tests for every public Security plane interface. | Grant/verification primitives are tested, but there are no complete contract tests for issue/attenuate/verify/revoke service interfaces and transports. |
| PLN-07-C083 | Missing | Create integration tests with every supported adjacent layer and execution tier. | No integration matrix tests every supported adjacent layer/tier. |
| PLN-07-C084 | Missing | Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Security plane. | No CPU/runtime/hypervisor/provider/protocol compatibility test matrix exists. |
| PLN-07-C085 | Missing | Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Security plane. | No committed fuzz target/corpus exists; only an audit-time deterministic invariant fuzz run was executed. |
| PLN-07-C086 | Missing | Create concurrency and race-condition tests for shared/distributed Security plane state. | No concurrency/race-condition test suite exists. |
| PLN-07-C087 | Partial | Create security tests derived directly from the Security plane threat model. | Several tests are threat-derived, but the complete threat model is not covered by executable security tests. |
| PLN-07-C088 | Missing | Create benchmark, soak, burst, and fleet-scale tests appropriate to Security plane. | No benchmark/soak/burst/fleet-scale test suite exists. |
| PLN-07-C089 | Missing | Create disaster, partition, reconnect, and degraded-control-plane tests. | No disaster/partition/reconnect/degraded-control-plane test suite exists. |
| PLN-07-C090 | Missing | Require machine-readable acceptance evidence before certifying a Security plane release for production. | No machine-readable production acceptance evidence bundle is included. |
| PLN-07-C091 | Partial | Define production SLOs, error budgets, and support commitments for Security plane. | Three SLOs/error budgets are declared; support commitments and a complete SLO set are absent. |
| PLN-07-C092 | Partial | Define canary, staged rollout, rollback, and emergency-disable procedures for Security plane. | README sketches rollback/emergency disable, but canary/staged rollout procedures and executable controls are absent. |
| PLN-07-C093 | Missing | Maintain a supported-version compatibility matrix for Security plane and adjacent dependencies. | No supported-version compatibility matrix exists. |
| PLN-07-C094 | Missing | Define patching, vulnerability response, and end-of-life SLAs for Security plane. | No patching, vulnerability-response, or end-of-life SLA exists. |
| PLN-07-C095 | Missing | Provide backup, restore, migration, or reconstruction procedures for Security plane state where applicable. | No backup/restore/migration/reconstruction procedure exists for revocation/evidence state. |
| PLN-07-C096 | Partial | Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks. | README gives a day-0/day-1/day-2 outline, but detailed executable runbooks are absent. |
| PLN-07-C097 | Missing | Define incident severity, paging, escalation, containment, and recovery procedures. | No incident severity/paging/escalation/containment/recovery runbook exists. |
| PLN-07-C098 | Missing | Perform recurring access, policy, dependency, configuration, and architecture reviews. | No recurring access/policy/dependency/configuration/architecture review schedule or evidence exists. |
| PLN-07-C099 | Missing | Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates. | No exception/waiver/technical-debt/deprecation ledger with owners and expiry dates exists. |
| PLN-07-C100 | Missing | Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness. | No formal production exit-gate result is included; `pk_core` is absent so the framework gate could not be run. |

---

## 4.3.0 re-audit addendum (2026-09-23)

The 72 gaps above were re-assessed after the 4.3.0 remediation pass. Current per-gap status and evidence: `MISSING_COMPONENTS.md` and `evidence/MC_STATUS.json`. Gate run: `evidence/EVIDENCE.json` (verdict CONDITIONAL_GO: all in-package stages pass; 14 external blockers open; pk_core framework stage blocked). The 4.2.0 requirement-level findings in `POST_AUDIT.json` are unchanged until the pk_core conformance run can execute (MC-02).
