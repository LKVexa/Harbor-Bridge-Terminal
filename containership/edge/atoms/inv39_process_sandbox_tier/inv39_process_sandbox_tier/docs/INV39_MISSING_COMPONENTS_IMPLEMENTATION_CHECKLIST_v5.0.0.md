# INV-39 v5.0.0 — Comprehensive Missing-Component Implementation Checklist

**Repository:** INV-39 Process Sandbox Tier  
**Baseline:** hardened v5.0.0  
**Source inventory:** `INV39_MISSING_COMPONENTS_v5.0.0.md`  
**Coverage:** all 106 residual missing/incomplete components  

## Purpose and completion standard

This checklist converts every residual audit finding into an implementation-and-certification work package. A checkbox is complete only when the implementation, negative-path behavior, tests, operational visibility, and release evidence all exist in the repository or in an explicitly linked, verifiable external system. Design prose alone does not satisfy an implementation checkbox, and requested configuration does not count as proof of OS enforcement.

### Global non-negotiable invariants

- [ ] **Fail closed:** failure to authenticate, authorize, validate, apply, verify, or attest a mandatory isolation control MUST prevent workload execution.
- [ ] **No intent-as-proof:** requested policy and actual applied/verified controls MUST be represented separately.
- [ ] **Pre-exec containment:** no untrusted workload instruction may execute before all mandatory controls are active.
- [ ] **Least privilege:** launcher/backend privileges, capabilities, FDs, namespaces, credentials, and control-plane permissions are minimized and bounded.
- [ ] **Deterministic identity:** node, tenant, workload, sandbox, operation, profile, artifact, and evidence identities are canonical and collision-resistant.
- [ ] **Crash-safe cleanup:** abnormal termination must not leave runnable descendants, privileged helpers, mounts, namespaces, cgroups, sockets, or stale ownership.
- [ ] **Evidence binding:** release and runtime evidence is bound to exact artifact/profile/configuration digests and cannot be replayed across nodes/workloads/releases.
- [ ] **No silent skips:** certification prerequisites that are absent on a claimed production target fail the gate rather than becoming green skipped tests.
- [ ] **Bounded resources:** attacker-controlled inputs, queues, logs, diagnostic records, retries, and per-sandbox resources have explicit hard limits.
- [ ] **Traceable completion:** each implemented control maps to requirement, code, test, evidence, owner, and production gate.

## Recommended implementation order

1. **P0 enforcement core:** MC-030–MC-055, because the repository is not a production sandbox until OS controls and trustworthy evidence exist.
2. **P0 certification:** MC-085–MC-094, especially real-backend integration, adversarial testing, and signed acceptance evidence.
3. **P0 release integrity:** MC-103–MC-105, so an incomplete or unverifiable build cannot be promoted.
4. **P1 control-plane/configuration/resilience/observability/operations:** MC-013–MC-029, MC-056–MC-065, MC-075–MC-084, MC-095–MC-102, MC-106.
5. **P2 governance/performance maturity:** MC-001–MC-012 and MC-066–MC-074; these still remain required before declaring full production readiness.

## Component index

| ID | Priority | Category | Missing / incomplete component | Audit linkage |
|---|---|---|---|---|
| MC-001 | P2 / Required production readiness | Architecture, requirements, and governance | Named accountable owner and escalation path | C009 |
| MC-002 | P2 / Required production readiness | Architecture, requirements, and governance | Approved ADR selecting and justifying Linux bubblewrap/seccomp and macOS Seatbelt, including rejected alternatives | C010 |
| MC-003 | P2 / Required production readiness | Architecture, requirements, and governance | Formal SHALL-level functional requirements specification with deployment-context applicability | C011-C012 |
| MC-004 | P2 / Required production readiness | Architecture, requirements, and governance | Quantified non-functional objectives for startup latency, availability, determinism, isolation, CPU/memory overhead, and tail latency | C013, C061-C062, C091 |
| MC-005 | P2 / Required production readiness | Architecture, requirements, and governance | Machine-readable success / partial / degraded / retryable / terminal outcome semantics | C014 |
| MC-006 | P2 / Required production readiness | Architecture, requirements, and governance | Enforced production lifecycle state machine covering create, apply, verify, exec, terminate, and cleanup | C015 |
| MC-007 | P2 / Required production readiness | Architecture, requirements, and governance | Backward-compatibility, deprecation, and migration policy for schemas/backends | C016, C027, C093 |
| MC-008 | P2 / Required production readiness | Architecture, requirements, and governance | Capacity ceilings, tenant quotas, fairness rules, and concurrency limits | C017, C067 |
| MC-009 | P2 / Required production readiness | Architecture, requirements, and governance | Explicit behavior for disconnected/offline operation and unavailable control-plane dependencies | C018 |
| MC-010 | P2 / Required production readiness | Architecture, requirements, and governance | Precedence rules for security vs residency vs SLO vs cost conflicts | C019 |
| MC-011 | P2 / Required production readiness | Architecture, requirements, and governance | Requirements traceability matrix linking all 100 checks to code, tests, evidence, owner, and status | C020 |
| MC-012 | P2 / Required production readiness | Architecture, requirements, and governance | Supported platform/kernel/runtime/backend compatibility matrix | C031, C084, C093 |
| MC-013 | P1 / High | Interfaces and integration | Authentication requirements for control-plane/profile/evidence boundaries | C023, C044 |
| MC-014 | P1 / High | Interfaces and integration | Authorization/capability model for who may create, update, launch, inspect, or terminate a sandbox | C024 |
| MC-015 | P1 / High | Interfaces and integration | Timeout, cancellation, retry, idempotency, and backpressure semantics for backend calls | C025 |
| MC-016 | P1 / High | Interfaces and integration | Stable machine-readable error code taxonomy and structured error payload schema | C026 |
| MC-017 | P1 / High | Interfaces and integration | Version negotiation / mixed-version peer behavior | C027 |
| MC-018 | P1 / High | Interfaces and integration | Explicit interface payload, concurrency, queue, connection, and resource limits | C028 |
| MC-019 | P1 / High | Interfaces and integration | Reference request/response fixtures for both public schemas, including negative fixtures | C029 |
| MC-020 | P1 / High | Interfaces and integration | Automated interoperability tests with PLN-04, GAP-13, GAP-09, and any runtime launcher/control-plane neighbor | C030, C083 |
| MC-021 | P1 / High | Packaging, configuration, and release inputs | Dependency/package manifest declaring and pinning `pk_core` and supported Python versions | C031-C032 |
| MC-022 | P1 / High | Packaging, configuration, and release inputs | Immutable release artifact definition and reproducible build metadata | C032 |
| MC-023 | P1 / High | Packaging, configuration, and release inputs | Declarative profile/configuration loader with secure defaults and schema validation before activation | C033-C034 |
| MC-024 | P1 / High | Packaging, configuration, and release inputs | Site/environment-specific configuration overlay mechanism without rebuilding artifacts | C035 |
| MC-025 | P1 / High | Packaging, configuration, and release inputs | Configuration provenance record: version, author/actor, source, digest, and activation time | C036 |
| MC-026 | P1 / High | Packaging, configuration, and release inputs | Atomic/transactional configuration activation | C037 |
| MC-027 | P1 / High | Packaging, configuration, and release inputs | Automatic and operator-driven configuration rollback implementation | C038 |
| MC-028 | P1 / High | Packaging, configuration, and release inputs | Secret/credential handling policy and secret-redaction tests for configuration/diagnostics | C039 |
| MC-029 | P1 / High | Packaging, configuration, and release inputs | Deterministic bootstrap/install path from an empty supported node | C040 |
| MC-030 | P0 / Release-blocking | Production sandbox enforcement backends | Native Linux seccomp filter compiler/installer | C031, C034, C042-C046 |
| MC-031 | P0 / Release-blocking | Production sandbox enforcement backends | Linux bubblewrap (`bwrap`) launcher/integration adapter | C010, C031, C046 |
| MC-032 | P0 / Release-blocking | Production sandbox enforcement backends | macOS Seatbelt profile compiler/launcher/verification adapter | C010, C031, C084 |
| MC-033 | P0 / Release-blocking | Production sandbox enforcement backends | Backend capability discovery and fail-closed platform feature probing | C031, C034, C084 |
| MC-034 | P0 / Release-blocking | Production sandbox enforcement backends | `PR_SET_NO_NEW_PRIVS` enforcement before child execution | C042-C043 |
| MC-035 | P0 / Release-blocking | Production sandbox enforcement backends | UID/GID switching, supplementary-group clearing, user-namespace mapping, and setuid/file-capability regain prevention | C042-C046 |
| MC-036 | P0 / Release-blocking | Production sandbox enforcement backends | Complete Linux capability handling: bounding, permitted, effective, inheritable, and ambient set reduction | C042-C043 |
| MC-037 | P0 / Release-blocking | Production sandbox enforcement backends | Mount namespace hardening, private propagation, root/pivot isolation, read-only bind policy, and safe temporary filesystem setup | C043, C046 |
| MC-038 | P0 / Release-blocking | Production sandbox enforcement backends | Optional Landlock/filesystem policy backend promised by the contract | C043, C046 |
| MC-039 | P0 / Release-blocking | Production sandbox enforcement backends | Network namespace setup, interface policy, inherited-socket control, and network egress policy | C043, C046 |
| MC-040 | P0 / Release-blocking | Production sandbox enforcement backends | Device isolation and `/proc`/`/sys` exposure policy | C043, C046 |
| MC-041 | P0 / Release-blocking | Production sandbox enforcement backends | File-descriptor inheritance closure / allow-list | C043, C046 |
| MC-042 | P0 / Release-blocking | Production sandbox enforcement backends | Environment-variable sanitization and dangerous loader-variable stripping | C043, C046 |
| MC-043 | P0 / Release-blocking | Production sandbox enforcement backends | Resource enforcement using rlimits and/or cgroup v2 for processes, CPU, memory, I/O, and file descriptors | C017, C043, C050, C054, C067 |
| MC-044 | P0 / Release-blocking | Production sandbox enforcement backends | Child launcher that guarantees no workload code executes before all containment controls are active | C034, C046 |
| MC-045 | P0 / Release-blocking | Production sandbox enforcement backends | PID 1/subreaper behavior, signal forwarding, child reaping, timeout termination, and cleanup | C051-C057 |
| MC-046 | P0 / Release-blocking | Production sandbox enforcement backends | Trustworthy backend applied-state attestation/read-back bound to `profile_digest` | C004, C034, C045, C049 |
| MC-047 | P0 / Release-blocking | Production sandbox enforcement backends | Kernel/backend evidence adapter for facts that cannot be exactly read back from normal kernel APIs (notably installed seccomp rule contents) | C004, C045, C090 |
| MC-048 | P0 / Release-blocking | Security, trust, and audit | Backend-specific threat model with attack paths, mitigations, owners, and tests linked to each threat | C041, C050, C087 |
| MC-049 | P0 / Release-blocking | Security, trust, and audit | Signed policy/artifact verification, digest pinning, provenance validation, and downgrade protection | C045 |
| MC-050 | P0 / Release-blocking | Security, trust, and audit | Node/control-plane identity and attestation mechanism before trusting profile or evidence sources | C044 |
| MC-051 | P0 / Release-blocking | Security, trust, and audit | Isolation proof/tests spanning execution, memory, filesystem/state, network, and device boundaries | C046 |
| MC-052 | P0 / Release-blocking | Security, trust, and audit | Encryption design for any remote sensitive profile/evidence transport and at-rest sensitive state | C047 |
| MC-053 | P0 / Release-blocking | Security, trust, and audit | Fail-safe behavior when identity, attestation, policy, key, or trusted-time services are unavailable | C048 |
| MC-054 | P0 / Release-blocking | Security, trust, and audit | Tamper-evident security audit-event sink / append-only evidence chain | C049 |
| MC-055 | P0 / Release-blocking | Security, trust, and audit | Adversarial escape suite covering privilege escalation, injection, replay, spoofing, sandbox escape, side channels, and resource exhaustion | C050, C087 |
| MC-056 | P1 / High | Resilience and failure handling | Comprehensive failure-mode matrix for process, runtime, node, site, dependency, and control-plane failures | C051 |
| MC-057 | P1 / High | Resilience and failure handling | Health/readiness/stall detection with quantified thresholds | C052 |
| MC-058 | P1 / High | Resilience and failure handling | Bounded retry/backoff/jitter implementation for operations that are actually safe to retry | C053 |
| MC-059 | P1 / High | Resilience and failure handling | Admission control/load shedding/circuit breaking around sandbox creation and backend saturation | C054 |
| MC-060 | P1 / High | Resilience and failure handling | Failover semantics preserving isolation/residency guarantees | C055 |
| MC-061 | P1 / High | Resilience and failure handling | Defined and tested degraded mode when noncritical dependencies are unavailable | C056 |
| MC-062 | P1 / High | Resilience and failure handling | Crash-consistency/restart/resume semantics for launcher/backend/evidence state | C057 |
| MC-063 | P1 / High | Resilience and failure handling | Duplicate ownership/stale-controller/duplicate-execution prevention | C058 |
| MC-064 | P1 / High | Resilience and failure handling | Quarantine/freeze/disable/kill control with authorization and audit | C059 |
| MC-065 | P1 / High | Resilience and failure handling | Automated fault-injection suite proving recovery objectives | C060 |
| MC-066 | P2 / Required production readiness | Performance and resource efficiency | Reproducible startup, CPU, memory, storage, network, and density benchmark harness | C061, C063-C064 |
| MC-067 | P2 / Required production readiness | Performance and resource efficiency | p50/p95/p99/worst-case release thresholds | C062 |
| MC-068 | P2 / Required production readiness | Performance and resource efficiency | Steady/burst/overload/scale/recovery performance scenarios | C063 |
| MC-069 | P2 / Required production readiness | Performance and resource efficiency | Per-workload/per-tenant overhead accounting | C064 |
| MC-070 | P2 / Required production readiness | Performance and resource efficiency | Profiling evidence for serialization/copy/context-switch/hop inefficiencies | C065 |
| MC-071 | P2 / Required production readiness | Performance and resource efficiency | Verified optimization implementation/evidence for locality, batching, zero-copy, or equivalent where applicable | C066 |
| MC-072 | P2 / Required production readiness | Performance and resource efficiency | Capacity model and saturation signals predicting resource exhaustion | C067, C069 |
| MC-073 | P2 / Required production readiness | Performance and resource efficiency | Power/thermal measurements for constrained edge nodes | C068 |
| MC-074 | P2 / Required production readiness | Performance and resource efficiency | Automated release gate that blocks startup/density/throughput/tail-latency regressions | C070 |
| MC-075 | P1 / High | Observability and explainability | Runtime status surface exposing health, readiness, version, active config digest, dependency status, and actual active controls | C071 |
| MC-076 | P1 / High | Observability and explainability | Structured metrics implementation for rate/errors/latency/saturation/backlog/resource use | C072 |
| MC-077 | P1 / High | Observability and explainability | Structured logging implementation with stable node/tenant/workload/component/operation identifiers | C073 |
| MC-078 | P1 / High | Observability and explainability | Trace-context propagation across control-plane/backend/launcher boundaries | C074 |
| MC-079 | P1 / High | Observability and explainability | High-cardinality diagnostic channel with redaction/privacy controls | C075 |
| MC-080 | P1 / High | Observability and explainability | Persistent reason record for every automated admission/rejection/rollback/termination decision | C076 |
| MC-081 | P1 / High | Observability and explainability | Operator explain view tying decisions to profile, policy, topology, constraints, and evidence | C077 |
| MC-082 | P1 / High | Observability and explainability | Correlation with release lineage and live infrastructure graph | C078 |
| MC-083 | P1 / High | Observability and explainability | Telemetry retention, sampling, privacy, and export policy | C079 |
| MC-084 | P1 / High | Observability and explainability | Dashboards and alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defect | C080 |
| MC-085 | P0 / Release-blocking | Testing and certification | Public-schema contract tests validating positive and negative fixtures | C082 |
| MC-086 | P0 / Release-blocking | Testing and certification | Real backend integration tests with adjacent layers and actual OS enforcement | C083 |
| MC-087 | P0 / Release-blocking | Testing and certification | Compatibility matrix test suite across supported CPU architectures, kernels, Python/runtime versions, bubblewrap/Seatbelt versions, and schema versions | C084 |
| MC-088 | P0 / Release-blocking | Testing and certification | Fuzz testing for profile parsing, schema boundaries, backend arguments, and untrusted identifiers | C085 |
| MC-089 | P0 / Release-blocking | Testing and certification | Concurrency/race tests for simultaneous create/update/terminate operations and evidence handling | C086 |
| MC-090 | P0 / Release-blocking | Testing and certification | Security test suite mechanically derived from the threat model | C087 |
| MC-091 | P0 / Release-blocking | Testing and certification | Benchmark, soak, burst, and fleet-scale certification tests | C088 |
| MC-092 | P0 / Release-blocking | Testing and certification | Disaster/partition/reconnect/degraded-control-plane tests | C089 |
| MC-093 | P0 / Release-blocking | Testing and certification | Machine-readable signed acceptance evidence required before release certification | C090 |
| MC-094 | P0 / Release-blocking | Testing and certification | Full 100-check `pk_core` conformance evidence from this archive; current integration tests skip because `pk_core` is absent | C090, C100 |
| MC-095 | P1 / High | Operations and release governance | Executable canary/staged rollout workflow with tested rollback and emergency disable | C092 |
| MC-096 | P1 / High | Operations and release governance | Supported-version compatibility matrix for backend/kernel/runtime/adjacent dependencies | C093 |
| MC-097 | P1 / High | Operations and release governance | Patching, vulnerability response, security advisory, and end-of-life SLA/process | C094 |
| MC-098 | P1 / High | Operations and release governance | Backup/restore/reconstruction procedure for policy, configuration, evidence, and exception state where external state exists | C095 |
| MC-099 | P1 / High | Operations and release governance | Detailed executable day-0/day-1/day-2 runbooks rather than README-level guidance | C096 |
| MC-100 | P1 / High | Operations and release governance | Incident severity, paging, escalation, containment, and recovery runbook | C097 |
| MC-101 | P1 / High | Operations and release governance | Recurring access/policy/dependency/configuration/architecture review process | C098 |
| MC-102 | P1 / High | Operations and release governance | Exception/waiver/technical-debt/deprecation register with owner and expiry | C099 |
| MC-103 | P0 / Release-blocking | Operations and release governance | Formal automated production exit gate spanning architecture through ownership readiness | C100 |
| MC-104 | P0 / Release-blocking | Operations and release governance | CI workflow executing compile, unit, optimized-mode, schema, backend integration, security, benchmark, and release gates | C081-C090, C100 |
| MC-105 | P0 / Release-blocking | Operations and release governance | SBOM/provenance generation and signed release artifact pipeline | C045, C090 |
| MC-106 | P1 / High | Operations and release governance | Distribution license/NOTICE and package metadata suitable for redistribution | Release hygiene; not explicitly enumerated by `CHECKLIST.json` |

# Architecture, requirements, and governance

## MC-001 — Named accountable owner and escalation path

**Audit status:** Missing  
**Checklist linkage:** C009  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **named accountable owner and escalation path** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-001 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Named accountable owner and escalation path** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Create a RACI covering design authority, code ownership, production operations, incident command, security approval, and emergency disable authority.
- [ ] Define escalation targets and acknowledgement/resolution objectives for Sev-1/Sev-2 security or availability incidents; test the contact path at least quarterly.
- [ ] Add repository ownership metadata and a machine-readable owner field to release evidence so orphaned components are detectable automatically.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-001; define the error returned on limit breach.
- [ ] Make MC-001 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Named accountable owner and escalation path** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-001 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-001 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-001 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-001 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-001 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-001 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-001 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-001 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-001.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Named accountable owner and escalation path**.

## MC-002 — Approved ADR selecting and justifying Linux bubblewrap/seccomp and macOS Seatbelt, including rejected alternatives

**Audit status:** Missing  
**Checklist linkage:** C010  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **approved ADR selecting and justifying Linux bubblewrap/seccomp and macOS Seatbelt, including rejected alternatives** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-002 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Approved ADR selecting and justifying Linux bubblewrap/seccomp and macOS Seatbelt, including rejected alternatives** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Write an ADR comparing direct syscalls, bubblewrap, nsjail/containerized approaches, Landlock augmentation, and platform-specific mechanisms against threat, portability, maintenance, and observability criteria.
- [ ] Record minimum kernel/OS/backend versions, required privileges, known semantic gaps, and why rejected alternatives do not satisfy the target isolation contract.
- [ ] Require ADR re-review when supported platforms, trust assumptions, or enforcement primitives materially change.
- [ ] Compile a canonical syscall policy into BPF using a maintained binding/toolchain; define default action, architecture checks, argument filters, and explicit behavior for unknown syscalls.
- [ ] Install seccomp only after `no_new_privs` and before exec; verify the process is in seccomp filter mode and cannot reset or loosen the filter.
- [ ] Generate architecture-specific syscall resolution tables and test x86_64/aarch64 differences plus x32/compat ABI rejection where relevant.
- [ ] Add kill/errno/log action tests and adversarial attempts using `ptrace`, `clone3`, `unshare`, `bpf`, `perf_event_open`, keyrings, and namespace-sensitive syscalls according to policy.
- [ ] Invoke `bwrap` without a shell using a prevalidated argv vector; pin/verify executable path and version and reject environment/PATH substitution.
- [ ] Construct namespaces, binds, tmpfs, proc/dev exposure, uid/gid, capabilities, network, and working directory from the canonical profile using a deterministic argument builder.
- [ ] Capture child PID/exit status and differentiate bwrap setup failure from workload failure; scrub inherited FDs/environment before launch.
- [ ] Run integration tests against real bwrap on supported distributions and assert mount/network/process views from inside the sandbox.
- [ ] Define a deterministic mapping from canonical profile controls to Seatbelt profile syntax and document controls with no macOS-equivalent semantics.
- [ ] Compile/validate profiles before launch and invoke the supported sandbox mechanism without shell interpolation or untrusted textual substitution.
- [ ] Version-gate against macOS releases and maintain regression tests because Seatbelt behavior is private/OS-sensitive.
- [ ] Verify representative file/network/process denials from inside the launched process and fail closed for unrepresentable mandatory controls.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-002; define the error returned on limit breach.
- [ ] Make MC-002 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Approved ADR selecting and justifying Linux bubblewrap/seccomp and macOS Seatbelt, including rejected alternatives** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-002 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-002 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-002 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-002 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-002 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-002 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-002 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-002 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-002.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Approved ADR selecting and justifying Linux bubblewrap/seccomp and macOS Seatbelt, including rejected alternatives**.

## MC-003 — Formal SHALL-level functional requirements specification with deployment-context applicability

**Audit status:** Missing  
**Checklist linkage:** C011-C012  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **formal SHALL-level functional requirements specification with deployment-context applicability** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-003 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Formal SHALL-level functional requirements specification with deployment-context applicability** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Define normative requirements for profile validation, backend selection, control application order, evidence production, process execution, termination, and cleanup.
- [ ] For each requirement specify applicable platform/deployment modes, negative requirements, measurable acceptance criteria, and traceability IDs.
- [ ] Validate the specification for contradictions such as “best effort” language on controls that are security-mandatory.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-003; define the error returned on limit breach.
- [ ] Make MC-003 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Formal SHALL-level functional requirements specification with deployment-context applicability** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-003 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-003 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-003 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-003 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-003 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-003 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-003 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-003 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-003.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Formal SHALL-level functional requirements specification with deployment-context applicability**.

## MC-004 — Quantified non-functional objectives for startup latency, availability, determinism, isolation, CPU/memory overhead, and tail latency

**Audit status:** Missing  
**Checklist linkage:** C013, C061-C062, C091  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **quantified non-functional objectives for startup latency, availability, determinism, isolation, CPU/memory overhead, and tail latency** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-004 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Quantified non-functional objectives for startup latency, availability, determinism, isolation, CPU/memory overhead, and tail latency** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Set target and hard-limit budgets for startup latency, steady CPU/RSS, isolation failure rate, cleanup latency, and p95/p99/p99.9 control-plane latency.
- [ ] Define measurement windows, workload distributions, hardware classes, warm/cold cache conditions, and allowed confidence intervals.
- [ ] Specify whether SLO violation blocks admission, triggers degraded mode, pages operators, or blocks release.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-004; define the error returned on limit breach.
- [ ] Make MC-004 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Quantified non-functional objectives for startup latency, availability, determinism, isolation, CPU/memory overhead, and tail latency** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-004 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-004 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-004 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-004 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-004 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-004 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-004 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-004 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-004.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Quantified non-functional objectives for startup latency, availability, determinism, isolation, CPU/memory overhead, and tail latency**.

## MC-005 — Machine-readable success / partial / degraded / retryable / terminal outcome semantics

**Audit status:** Missing  
**Checklist linkage:** C014  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **machine-readable success / partial / degraded / retryable / terminal outcome semantics** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-005 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Machine-readable success / partial / degraded / retryable / terminal outcome semantics** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Define a closed enum for success, rejected, retryable failure, terminal failure, degraded-but-safe, cancelled, timed out, and cleanup-pending outcomes.
- [ ] Attach stable reason codes, retryability, operator action, HTTP/RPC mapping where relevant, and security significance to every outcome.
- [ ] Prohibit “partial success” when any mandatory isolation control failed to apply or verify.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-005; define the error returned on limit breach.
- [ ] Make MC-005 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Machine-readable success / partial / degraded / retryable / terminal outcome semantics** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-005 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-005 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-005 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-005 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-005 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-005 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-005 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-005 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-005.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Machine-readable success / partial / degraded / retryable / terminal outcome semantics**.

## MC-006 — Enforced production lifecycle state machine covering create, apply, verify, exec, terminate, and cleanup

**Audit status:** Partial: model only  
**Checklist linkage:** C015  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **enforced production lifecycle state machine covering create, apply, verify, exec, terminate, and cleanup** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-006 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Enforced production lifecycle state machine covering create, apply, verify, exec, terminate, and cleanup** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Implement a single authoritative state machine such as NEW -> VALIDATED -> APPLYING -> VERIFIED -> EXECUTING -> TERMINATING -> CLEANED plus explicit FAILED/QUARANTINED terminals.
- [ ] Enforce transition guards atomically and reject duplicate start/exec/cleanup calls that do not satisfy idempotency rules.
- [ ] Property-test forbidden transitions and crash recovery from every nonterminal state.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-006; define the error returned on limit breach.
- [ ] Make MC-006 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Enforced production lifecycle state machine covering create, apply, verify, exec, terminate, and cleanup** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-006 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-006 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-006 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-006 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-006 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-006 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-006 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-006 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-006.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Enforced production lifecycle state machine covering create, apply, verify, exec, terminate, and cleanup**.

## MC-007 — Backward-compatibility, deprecation, and migration policy for schemas/backends

**Audit status:** Missing  
**Checklist linkage:** C016, C027, C093  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **backward-compatibility, deprecation, and migration policy for schemas/backends** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-007 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Backward-compatibility, deprecation, and migration policy for schemas/backends** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Define schema/backend semantic-version rules and the exact changes considered breaking, additive, or operationally incompatible.
- [ ] Implement dual-read/single-write or explicit migration tooling where rolling upgrades require mixed versions.
- [ ] Add downgrade/replay protections so an older peer or profile cannot silently remove mandatory security fields.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-007; define the error returned on limit breach.
- [ ] Make MC-007 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Backward-compatibility, deprecation, and migration policy for schemas/backends** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-007 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-007 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-007 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-007 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-007 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-007 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-007 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-007 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-007.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Backward-compatibility, deprecation, and migration policy for schemas/backends**.

## MC-008 — Capacity ceilings, tenant quotas, fairness rules, and concurrency limits

**Audit status:** Missing  
**Checklist linkage:** C017, C067  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **capacity ceilings, tenant quotas, fairness rules, and concurrency limits** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-008 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Capacity ceilings, tenant quotas, fairness rules, and concurrency limits** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Define hard maxima for concurrent sandboxes, queued launches, profile size, environment entries, bind mounts, FDs, processes, memory, and per-tenant resource shares.
- [ ] Enforce quotas before allocating scarce resources and return deterministic limit-exceeded codes without partial sandbox creation.
- [ ] Test fairness under noisy-neighbor load and confirm one tenant cannot starve control-plane cleanup or security operations.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-008; define the error returned on limit breach.
- [ ] Make MC-008 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Capacity ceilings, tenant quotas, fairness rules, and concurrency limits** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-008 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-008 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-008 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-008 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-008 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-008 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-008 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-008 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-008.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Capacity ceilings, tenant quotas, fairness rules, and concurrency limits**.

## MC-009 — Explicit behavior for disconnected/offline operation and unavailable control-plane dependencies

**Audit status:** Missing  
**Checklist linkage:** C018  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **explicit behavior for disconnected/offline operation and unavailable control-plane dependencies** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-009 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Explicit behavior for disconnected/offline operation and unavailable control-plane dependencies** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Specify which cached policies/credentials/evidence remain valid offline, their TTL/epoch rules, and which actions are prohibited without authoritative dependencies.
- [ ] Prevent stale-policy replay by binding cached authorization to version/epoch and enforce expiration using monotonic/trusted time where required.
- [ ] Test disconnect during create, after verification, during execution, and during cleanup, including reconnect reconciliation.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-009; define the error returned on limit breach.
- [ ] Make MC-009 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Explicit behavior for disconnected/offline operation and unavailable control-plane dependencies** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-009 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-009 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-009 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-009 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-009 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-009 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-009 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-009 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-009.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Explicit behavior for disconnected/offline operation and unavailable control-plane dependencies**.

## MC-010 — Precedence rules for security vs residency vs SLO vs cost conflicts

**Audit status:** Missing  
**Checklist linkage:** C019  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **precedence rules for security vs residency vs SLO vs cost conflicts** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-010 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Precedence rules for security vs residency vs SLO vs cost conflicts** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Define a deterministic precedence lattice where isolation/security requirements cannot be traded away to satisfy cost or latency objectives.
- [ ] Encode conflicts as machine-readable rejection reasons and include the violated constraints in operator-facing explanations.
- [ ] Test pairwise and multi-constraint conflicts to prove the same inputs always yield the same decision.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-010; define the error returned on limit breach.
- [ ] Make MC-010 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Precedence rules for security vs residency vs SLO vs cost conflicts** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-010 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-010 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-010 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-010 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-010 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-010 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-010 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-010 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-010.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Precedence rules for security vs residency vs SLO vs cost conflicts**.

## MC-011 — Requirements traceability matrix linking all 100 checks to code, tests, evidence, owner, and status

**Audit status:** Missing  
**Checklist linkage:** C020  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **requirements traceability matrix linking all 100 checks to code, tests, evidence, owner, and status** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-011 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Requirements traceability matrix linking all 100 checks to code, tests, evidence, owner, and status** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Create a RACI covering design authority, code ownership, production operations, incident command, security approval, and emergency disable authority.
- [ ] Define escalation targets and acknowledgement/resolution objectives for Sev-1/Sev-2 security or availability incidents; test the contact path at least quarterly.
- [ ] Add repository ownership metadata and a machine-readable owner field to release evidence so orphaned components are detectable automatically.
- [ ] Generate the matrix from source-controlled metadata and fail CI when a requirement lacks implementation, test, evidence, owner, or disposition.
- [ ] Include residual-risk/waiver links for intentionally unmet checks and enforce waiver expiry.
- [ ] Publish the exact matrix used for each release as signed evidence.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-011; define the error returned on limit breach.
- [ ] Make MC-011 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Requirements traceability matrix linking all 100 checks to code, tests, evidence, owner, and status** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-011 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-011 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-011 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-011 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-011 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-011 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-011 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-011 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-011.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Requirements traceability matrix linking all 100 checks to code, tests, evidence, owner, and status**.

## MC-012 — Supported platform/kernel/runtime/backend compatibility matrix

**Audit status:** Missing  
**Checklist linkage:** C031, C084, C093  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **supported platform/kernel/runtime/backend compatibility matrix** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-012 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Supported platform/kernel/runtime/backend compatibility matrix** across each supported OS/backend/deployment mode.
- [ ] Assign a directly responsible engineering owner, security reviewer, operations reviewer, and release approver; encode ownership in repository CODEOWNERS/metadata rather than relying on tribal knowledge.
- [ ] Write normative requirements using SHALL/SHALL NOT/MAY language and assign stable requirement IDs that can be referenced from code, tests, telemetry, and release evidence.
- [ ] Document trust boundaries, actors, protected assets, deployment assumptions, dependency assumptions, and failure-domain boundaries affected by this component.
- [ ] Define explicit preconditions, postconditions, invariants, state transitions, and prohibited states; make undefined states fail closed where security can be affected.

### B. Component-specific implementation

- [ ] Record supported CPU architecture, OS release, kernel build/config, libc, Python/runtime, bubblewrap/Seatbelt version, and required kernel feature flags.
- [ ] Automate environment detection and block unsupported combinations before workload launch.
- [ ] Continuously test N-1/current versions and explicitly document unsupported/EOL combinations.
- [ ] Record compatibility impact, rollout sequencing, rollback constraints, and migration behavior for existing profiles, callers, or evidence consumers.
- [ ] Add machine-readable traceability from requirement -> implementation symbol -> test case -> evidence artifact -> release gate.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-012; define the error returned on limit breach.
- [ ] Make MC-012 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Supported platform/kernel/runtime/backend compatibility matrix** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-012 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-012 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-012 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-012 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-012 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-012 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-012 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-012 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-012.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Supported platform/kernel/runtime/backend compatibility matrix**.


# Interfaces and integration

## MC-013 — Authentication requirements for control-plane/profile/evidence boundaries

**Audit status:** Missing  
**Checklist linkage:** C023, C044  
**Priority:** P1 / High  
**Objective:** Implement and prove **authentication requirements for control-plane/profile/evidence boundaries** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-013 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Authentication requirements for control-plane/profile/evidence boundaries** across each supported OS/backend/deployment mode.
- [ ] Define a versioned interface contract with canonical request/response types, field constraints, nullability, defaults, size limits, and stable error semantics.
- [ ] Specify authentication context, authorization decision points, tenant/workload identity propagation, replay resistance, and caller accountability for every externally reachable operation.
- [ ] Define timeout, cancellation, idempotency, retry-safety, concurrency, ordering, and backpressure semantics; identify operations that MUST NOT be retried automatically.
- [ ] Reject unknown/ambiguous fields where they could weaken policy; canonicalize identifiers before comparison, logging, hashing, or authorization.

### B. Component-specific implementation

- [ ] Select workload/control-plane authentication mechanisms and define credential binding to node, tenant, service identity, and intended audience.
- [ ] Require freshness/replay controls and verify credentials before accepting policy, launch, inspection, termination, or evidence-upload requests.
- [ ] Add negative tests for expired, wrong-audience, wrong-tenant, replayed, unsigned, and algorithm-downgrade credentials.
- [ ] Create positive, boundary, malformed, adversarial, and mixed-version fixtures and run them as contract tests against every implementation.
- [ ] Make protocol/version negotiation observable and include peer version, negotiated version, and rejection reason in structured diagnostics.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-013; define the error returned on limit breach.
- [ ] Make MC-013 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Authentication requirements for control-plane/profile/evidence boundaries** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-013 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-013 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-013 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-013 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-013 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-013 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-013 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-013 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-013.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Authentication requirements for control-plane/profile/evidence boundaries**.

## MC-014 — Authorization/capability model for who may create, update, launch, inspect, or terminate a sandbox

**Audit status:** Missing  
**Checklist linkage:** C024  
**Priority:** P1 / High  
**Objective:** Implement and prove **authorization/capability model for who may create, update, launch, inspect, or terminate a sandbox** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-014 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Authorization/capability model for who may create, update, launch, inspect, or terminate a sandbox** across each supported OS/backend/deployment mode.
- [ ] Define a versioned interface contract with canonical request/response types, field constraints, nullability, defaults, size limits, and stable error semantics.
- [ ] Specify authentication context, authorization decision points, tenant/workload identity propagation, replay resistance, and caller accountability for every externally reachable operation.
- [ ] Define timeout, cancellation, idempotency, retry-safety, concurrency, ordering, and backpressure semantics; identify operations that MUST NOT be retried automatically.
- [ ] Reject unknown/ambiguous fields where they could weaken policy; canonicalize identifiers before comparison, logging, hashing, or authorization.

### B. Component-specific implementation

- [ ] Define least-privilege actions for profile author, launcher, inspector, terminator, operator, auditor, and break-glass roles.
- [ ] Evaluate authorization on the authoritative resource identity and deny cross-tenant references even when identifiers collide.
- [ ] Log policy decision ID, principal, action, resource, result, and reason without exposing bearer secrets.
- [ ] Create positive, boundary, malformed, adversarial, and mixed-version fixtures and run them as contract tests against every implementation.
- [ ] Make protocol/version negotiation observable and include peer version, negotiated version, and rejection reason in structured diagnostics.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-014; define the error returned on limit breach.
- [ ] Make MC-014 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Authorization/capability model for who may create, update, launch, inspect, or terminate a sandbox** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-014 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-014 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-014 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-014 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-014 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-014 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-014 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-014 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-014.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Authorization/capability model for who may create, update, launch, inspect, or terminate a sandbox**.

## MC-015 — Timeout, cancellation, retry, idempotency, and backpressure semantics for backend calls

**Audit status:** Missing  
**Checklist linkage:** C025  
**Priority:** P1 / High  
**Objective:** Implement and prove **timeout, cancellation, retry, idempotency, and backpressure semantics for backend calls** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-015 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Timeout, cancellation, retry, idempotency, and backpressure semantics for backend calls** across each supported OS/backend/deployment mode.
- [ ] Define a versioned interface contract with canonical request/response types, field constraints, nullability, defaults, size limits, and stable error semantics.
- [ ] Specify authentication context, authorization decision points, tenant/workload identity propagation, replay resistance, and caller accountability for every externally reachable operation.
- [ ] Define timeout, cancellation, idempotency, retry-safety, concurrency, ordering, and backpressure semantics; identify operations that MUST NOT be retried automatically.
- [ ] Reject unknown/ambiguous fields where they could weaken policy; canonicalize identifiers before comparison, logging, hashing, or authorization.

### B. Component-specific implementation

- [ ] Assign per-stage deadlines and cancellation points; ensure cancellation cannot leave a partially isolated child runnable.
- [ ] Use operation IDs/idempotency keys for retriable create/terminate requests and persist enough state to de-duplicate after controller restart.
- [ ] Bound queues and return overload errors before resource exhaustion; never apply unbounded client-side retries.
- [ ] Define whether the sandbox launcher is namespace PID 1 or a subreaper and implement correct orphan adoption/zombie reaping.
- [ ] Forward permitted signals with documented translation/escalation; use process groups/pidfds to avoid PID-reuse races.
- [ ] Implement timeout TERM->grace->KILL sequencing and verify all descendants are terminated before cleanup is reported complete.
- [ ] Test double-fork, daemonization, signal storms, stuck uninterruptible processes, launcher crash, and descendant escape attempts.
- [ ] Create positive, boundary, malformed, adversarial, and mixed-version fixtures and run them as contract tests against every implementation.
- [ ] Make protocol/version negotiation observable and include peer version, negotiated version, and rejection reason in structured diagnostics.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-015; define the error returned on limit breach.
- [ ] Make MC-015 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Timeout, cancellation, retry, idempotency, and backpressure semantics for backend calls** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-015 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-015 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-015 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-015 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-015 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-015 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-015 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-015 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-015.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Timeout, cancellation, retry, idempotency, and backpressure semantics for backend calls**.

## MC-016 — Stable machine-readable error code taxonomy and structured error payload schema

**Audit status:** Missing  
**Checklist linkage:** C026  
**Priority:** P1 / High  
**Objective:** Implement and prove **stable machine-readable error code taxonomy and structured error payload schema** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-016 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Stable machine-readable error code taxonomy and structured error payload schema** across each supported OS/backend/deployment mode.
- [ ] Define a versioned interface contract with canonical request/response types, field constraints, nullability, defaults, size limits, and stable error semantics.
- [ ] Specify authentication context, authorization decision points, tenant/workload identity propagation, replay resistance, and caller accountability for every externally reachable operation.
- [ ] Define timeout, cancellation, idempotency, retry-safety, concurrency, ordering, and backpressure semantics; identify operations that MUST NOT be retried automatically.
- [ ] Reject unknown/ambiguous fields where they could weaken policy; canonicalize identifiers before comparison, logging, hashing, or authorization.

### B. Component-specific implementation

- [ ] Define namespaced stable codes by domain: validation, authn, authz, unsupported feature, backend apply, verification, launch, timeout, cleanup, overload, and internal defect.
- [ ] Include retryability, stage, component, operation ID, profile digest, and safe diagnostic detail in the error schema.
- [ ] Test that changing human-readable text does not change machine behavior and that secrets never appear in payloads.
- [ ] Create positive, boundary, malformed, adversarial, and mixed-version fixtures and run them as contract tests against every implementation.
- [ ] Make protocol/version negotiation observable and include peer version, negotiated version, and rejection reason in structured diagnostics.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-016; define the error returned on limit breach.
- [ ] Make MC-016 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Stable machine-readable error code taxonomy and structured error payload schema** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-016 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-016 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-016 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-016 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-016 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-016 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-016 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-016 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-016.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Stable machine-readable error code taxonomy and structured error payload schema**.

## MC-017 — Version negotiation / mixed-version peer behavior

**Audit status:** Missing  
**Checklist linkage:** C027  
**Priority:** P1 / High  
**Objective:** Implement and prove **version negotiation / mixed-version peer behavior** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-017 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Version negotiation / mixed-version peer behavior** across each supported OS/backend/deployment mode.
- [ ] Define a versioned interface contract with canonical request/response types, field constraints, nullability, defaults, size limits, and stable error semantics.
- [ ] Specify authentication context, authorization decision points, tenant/workload identity propagation, replay resistance, and caller accountability for every externally reachable operation.
- [ ] Define timeout, cancellation, idempotency, retry-safety, concurrency, ordering, and backpressure semantics; identify operations that MUST NOT be retried automatically.
- [ ] Reject unknown/ambiguous fields where they could weaken policy; canonicalize identifiers before comparison, logging, hashing, or authorization.

### B. Component-specific implementation

- [ ] Define schema/backend semantic-version rules and the exact changes considered breaking, additive, or operationally incompatible.
- [ ] Implement dual-read/single-write or explicit migration tooling where rolling upgrades require mixed versions.
- [ ] Add downgrade/replay protections so an older peer or profile cannot silently remove mandatory security fields.
- [ ] Create positive, boundary, malformed, adversarial, and mixed-version fixtures and run them as contract tests against every implementation.
- [ ] Make protocol/version negotiation observable and include peer version, negotiated version, and rejection reason in structured diagnostics.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-017; define the error returned on limit breach.
- [ ] Make MC-017 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Version negotiation / mixed-version peer behavior** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-017 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-017 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-017 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-017 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-017 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-017 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-017 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-017 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-017.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Version negotiation / mixed-version peer behavior**.

## MC-018 — Explicit interface payload, concurrency, queue, connection, and resource limits

**Audit status:** Missing  
**Checklist linkage:** C028  
**Priority:** P1 / High  
**Objective:** Implement and prove **explicit interface payload, concurrency, queue, connection, and resource limits** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-018 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Explicit interface payload, concurrency, queue, connection, and resource limits** across each supported OS/backend/deployment mode.
- [ ] Define a versioned interface contract with canonical request/response types, field constraints, nullability, defaults, size limits, and stable error semantics.
- [ ] Specify authentication context, authorization decision points, tenant/workload identity propagation, replay resistance, and caller accountability for every externally reachable operation.
- [ ] Define timeout, cancellation, idempotency, retry-safety, concurrency, ordering, and backpressure semantics; identify operations that MUST NOT be retried automatically.
- [ ] Reject unknown/ambiguous fields where they could weaken policy; canonicalize identifiers before comparison, logging, hashing, or authorization.

### B. Component-specific implementation

- [ ] Define hard maxima for concurrent sandboxes, queued launches, profile size, environment entries, bind mounts, FDs, processes, memory, and per-tenant resource shares.
- [ ] Enforce quotas before allocating scarce resources and return deterministic limit-exceeded codes without partial sandbox creation.
- [ ] Test fairness under noisy-neighbor load and confirm one tenant cannot starve control-plane cleanup or security operations.
- [ ] Create positive, boundary, malformed, adversarial, and mixed-version fixtures and run them as contract tests against every implementation.
- [ ] Make protocol/version negotiation observable and include peer version, negotiated version, and rejection reason in structured diagnostics.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-018; define the error returned on limit breach.
- [ ] Make MC-018 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Explicit interface payload, concurrency, queue, connection, and resource limits** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-018 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-018 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-018 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-018 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-018 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-018 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-018 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-018 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-018.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Explicit interface payload, concurrency, queue, connection, and resource limits**.

## MC-019 — Reference request/response fixtures for both public schemas, including negative fixtures

**Audit status:** Missing  
**Checklist linkage:** C029  
**Priority:** P1 / High  
**Objective:** Implement and prove **reference request/response fixtures for both public schemas, including negative fixtures** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-019 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Reference request/response fixtures for both public schemas, including negative fixtures** across each supported OS/backend/deployment mode.
- [ ] Define a versioned interface contract with canonical request/response types, field constraints, nullability, defaults, size limits, and stable error semantics.
- [ ] Specify authentication context, authorization decision points, tenant/workload identity propagation, replay resistance, and caller accountability for every externally reachable operation.
- [ ] Define timeout, cancellation, idempotency, retry-safety, concurrency, ordering, and backpressure semantics; identify operations that MUST NOT be retried automatically.
- [ ] Reject unknown/ambiguous fields where they could weaken policy; canonicalize identifiers before comparison, logging, hashing, or authorization.

### B. Component-specific implementation

- [ ] Create canonical minimal, typical, maximal-boundary, deprecated-version, unknown-field, malformed, and hostile fixtures for every public schema.
- [ ] Hash fixtures and run them against schema validators plus implementation parsers to detect schema/runtime drift.
- [ ] Include expected normalized form and expected stable error code for every negative fixture.
- [ ] Create positive, boundary, malformed, adversarial, and mixed-version fixtures and run them as contract tests against every implementation.
- [ ] Make protocol/version negotiation observable and include peer version, negotiated version, and rejection reason in structured diagnostics.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-019; define the error returned on limit breach.
- [ ] Make MC-019 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Reference request/response fixtures for both public schemas, including negative fixtures** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-019 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-019 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-019 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-019 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-019 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-019 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-019 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-019 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-019.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Reference request/response fixtures for both public schemas, including negative fixtures**.

## MC-020 — Automated interoperability tests with PLN-04, GAP-13, GAP-09, and any runtime launcher/control-plane neighbor

**Audit status:** Missing  
**Checklist linkage:** C030, C083  
**Priority:** P1 / High  
**Objective:** Implement and prove **automated interoperability tests with PLN-04, GAP-13, GAP-09, and any runtime launcher/control-plane neighbor** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-020 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Automated interoperability tests with PLN-04, GAP-13, GAP-09, and any runtime launcher/control-plane neighbor** across each supported OS/backend/deployment mode.
- [ ] Define a versioned interface contract with canonical request/response types, field constraints, nullability, defaults, size limits, and stable error semantics.
- [ ] Specify authentication context, authorization decision points, tenant/workload identity propagation, replay resistance, and caller accountability for every externally reachable operation.
- [ ] Define timeout, cancellation, idempotency, retry-safety, concurrency, ordering, and backpressure semantics; identify operations that MUST NOT be retried automatically.
- [ ] Reject unknown/ambiguous fields where they could weaken policy; canonicalize identifiers before comparison, logging, hashing, or authorization.

### B. Component-specific implementation

- [ ] Define exact cross-component handshake, identity, schema version, timeout, and error-propagation expectations with each neighbor.
- [ ] Run contract tests against version-pinned real or hermetic neighbor implementations, not only mocks.
- [ ] Exercise mixed-version upgrade/downgrade, dependency timeout, malformed response, and cancellation propagation scenarios.
- [ ] Create positive, boundary, malformed, adversarial, and mixed-version fixtures and run them as contract tests against every implementation.
- [ ] Make protocol/version negotiation observable and include peer version, negotiated version, and rejection reason in structured diagnostics.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-020; define the error returned on limit breach.
- [ ] Make MC-020 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Automated interoperability tests with PLN-04, GAP-13, GAP-09, and any runtime launcher/control-plane neighbor** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-020 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-020 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-020 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-020 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-020 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-020 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-020 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-020 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-020.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Automated interoperability tests with PLN-04, GAP-13, GAP-09, and any runtime launcher/control-plane neighbor**.


# Packaging, configuration, and release inputs

## MC-021 — Dependency/package manifest declaring and pinning `pk_core` and supported Python versions

**Audit status:** Missing  
**Checklist linkage:** C031-C032  
**Priority:** P1 / High  
**Objective:** Implement and prove **dependency/package manifest declaring and pinning `pk_core` and supported Python versions** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-021 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Dependency/package manifest declaring and pinning `pk_core` and supported Python versions** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Add `pyproject.toml` or equivalent with explicit Python support range, hashes/locks for runtime dependencies, and optional test/dev groups.
- [ ] Pin a compatible `pk_core` range and make missing required runtime dependencies a startup/build failure rather than a silent test skip.
- [ ] Run dependency resolution and test suites on every supported Python minor version.
- [ ] Vendor, declare, or reliably resolve the approved `pk_core` dependency in certification environments and pin the compatible contract/version.
- [ ] Change release certification so missing `pk_core` causes a failed prerequisite for the conformance job, not a green build with skipped tests.
- [ ] Execute and archive all 100-check conformance outputs against the exact release artifact.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-021; define the error returned on limit breach.
- [ ] Make MC-021 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Dependency/package manifest declaring and pinning `pk_core` and supported Python versions** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-021 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-021 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-021 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-021 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-021 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-021 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-021 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-021 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-021.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Dependency/package manifest declaring and pinning `pk_core` and supported Python versions**.

## MC-022 — Immutable release artifact definition and reproducible build metadata

**Audit status:** Missing  
**Checklist linkage:** C032  
**Priority:** P1 / High  
**Objective:** Implement and prove **immutable release artifact definition and reproducible build metadata** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-022 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Immutable release artifact definition and reproducible build metadata** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Define byte-for-byte reproducibility requirements or document unavoidable non-deterministic fields and normalize them.
- [ ] Embed source revision, build recipe/toolchain versions, dependency lock digest, and build timestamp policy into provenance.
- [ ] Rebuild in an isolated environment and compare artifact digests as a release gate.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-022; define the error returned on limit breach.
- [ ] Make MC-022 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Immutable release artifact definition and reproducible build metadata** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-022 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-022 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-022 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-022 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-022 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-022 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-022 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-022 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-022.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Immutable release artifact definition and reproducible build metadata**.

## MC-023 — Declarative profile/configuration loader with secure defaults and schema validation before activation

**Audit status:** Missing  
**Checklist linkage:** C033-C034  
**Priority:** P1 / High  
**Objective:** Implement and prove **declarative profile/configuration loader with secure defaults and schema validation before activation** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-023 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Declarative profile/configuration loader with secure defaults and schema validation before activation** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Implement a loader that parses only documented encodings, caps document depth/size/counts, validates schema before semantic processing, and canonicalizes before hashing.
- [ ] Default optional security controls to the more restrictive behavior and require explicit opt-in for any relaxation.
- [ ] Reject duplicate keys, path traversal constructs, invalid Unicode/control characters, and unsupported schema versions.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-023; define the error returned on limit breach.
- [ ] Make MC-023 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Declarative profile/configuration loader with secure defaults and schema validation before activation** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-023 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-023 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-023 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-023 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-023 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-023 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-023 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-023 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-023.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Declarative profile/configuration loader with secure defaults and schema validation before activation**.

## MC-024 — Site/environment-specific configuration overlay mechanism without rebuilding artifacts

**Audit status:** Missing  
**Checklist linkage:** C035  
**Priority:** P1 / High  
**Objective:** Implement and prove **site/environment-specific configuration overlay mechanism without rebuilding artifacts** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-024 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Site/environment-specific configuration overlay mechanism without rebuilding artifacts** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Define deterministic overlay precedence and allowed override paths; prohibit overlays from weakening immutable security baselines without an approved exception.
- [ ] Compute and persist the digest of the fully resolved effective configuration, not only the base layer.
- [ ] Test conflicting overlays, deletion semantics, secret references, and rollback across site/environment changes.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-024; define the error returned on limit breach.
- [ ] Make MC-024 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Site/environment-specific configuration overlay mechanism without rebuilding artifacts** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-024 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-024 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-024 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-024 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-024 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-024 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-024 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-024 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-024.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Site/environment-specific configuration overlay mechanism without rebuilding artifacts**.

## MC-025 — Configuration provenance record: version, author/actor, source, digest, and activation time

**Audit status:** Partial: digest only  
**Checklist linkage:** C036  
**Priority:** P1 / High  
**Objective:** Implement and prove **configuration provenance record: version, author/actor, source, digest, and activation time** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-025 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Configuration provenance record: version, author/actor, source, digest, and activation time** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Record source URI/identifier, actor/service principal, schema version, base/overlay digests, signing identity, review/approval references, and activation timestamp.
- [ ] Bind provenance to the effective configuration digest and active sandbox evidence.
- [ ] Expose provenance via read-only status APIs while applying tenant and secret redaction rules.
- [ ] Define canonical bytes to sign, approved algorithms/key sizes, key IDs, trust roots, signature envelope, expiry/epoch, and multi-signature rules if required.
- [ ] Verify signature and digest before parsing/activation side effects; pin minimum schema/policy/backend versions to prevent downgrade.
- [ ] Implement key rotation/revocation and test stale/revoked/unknown-key/replayed policy rejection.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-025; define the error returned on limit breach.
- [ ] Make MC-025 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Configuration provenance record: version, author/actor, source, digest, and activation time** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-025 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-025 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-025 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-025 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-025 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-025 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-025 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-025 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-025.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Configuration provenance record: version, author/actor, source, digest, and activation time**.

## MC-026 — Atomic/transactional configuration activation

**Audit status:** Missing  
**Checklist linkage:** C037  
**Priority:** P1 / High  
**Objective:** Implement and prove **atomic/transactional configuration activation** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-026 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Atomic/transactional configuration activation** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Stage candidate configuration separately, validate all dependent backends, and use compare-and-swap/version guards when publishing active state.
- [ ] Guarantee readers see either the old complete configuration or the new complete configuration, never an intermediate mix.
- [ ] Crash-test every activation step and prove restart deterministically selects the last committed version.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-026; define the error returned on limit breach.
- [ ] Make MC-026 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Atomic/transactional configuration activation** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-026 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-026 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-026 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-026 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-026 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-026 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-026 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-026 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-026.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Atomic/transactional configuration activation**.

## MC-027 — Automatic and operator-driven configuration rollback implementation

**Audit status:** Missing  
**Checklist linkage:** C038  
**Priority:** P1 / High  
**Objective:** Implement and prove **automatic and operator-driven configuration rollback implementation** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-027 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Automatic and operator-driven configuration rollback implementation** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Retain a bounded history of known-good signed configurations and support rollback by immutable version/digest.
- [ ] Verify rollback compatibility with current binaries/backends before activation and require reason/actor/audit evidence.
- [ ] Exercise automatic rollback on failed verification plus operator-driven rollback during live load.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-027; define the error returned on limit breach.
- [ ] Make MC-027 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Automatic and operator-driven configuration rollback implementation** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-027 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-027 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-027 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-027 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-027 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-027 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-027 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-027 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-027.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Automatic and operator-driven configuration rollback implementation**.

## MC-028 — Secret/credential handling policy and secret-redaction tests for configuration/diagnostics

**Audit status:** Missing  
**Checklist linkage:** C039  
**Priority:** P1 / High  
**Objective:** Implement and prove **secret/credential handling policy and secret-redaction tests for configuration/diagnostics** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-028 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Secret/credential handling policy and secret-redaction tests for configuration/diagnostics** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Represent secrets as references/handles rather than embedding plaintext in profiles, logs, evidence, crash dumps, or provenance.
- [ ] Zero or release secret material promptly where runtime permits and scope credentials to least privilege, audience, and lifetime.
- [ ] Seed canary secrets in tests and assert they never appear in stdout/stderr/logs/traces/errors/evidence artifacts.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-028; define the error returned on limit breach.
- [ ] Make MC-028 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Secret/credential handling policy and secret-redaction tests for configuration/diagnostics** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-028 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-028 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-028 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-028 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-028 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-028 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-028 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-028 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-028.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Secret/credential handling policy and secret-redaction tests for configuration/diagnostics**.

## MC-029 — Deterministic bootstrap/install path from an empty supported node

**Audit status:** Missing  
**Checklist linkage:** C040  
**Priority:** P1 / High  
**Objective:** Implement and prove **deterministic bootstrap/install path from an empty supported node** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-029 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Deterministic bootstrap/install path from an empty supported node** across each supported OS/backend/deployment mode.
- [ ] Define the configuration/release input as an immutable, content-addressed object with a canonical serialization and SHA-256 or stronger digest.
- [ ] Validate all configuration against a versioned schema before activation; reject ambiguous, duplicate, unknown, or out-of-range values before side effects occur.
- [ ] Separate immutable release content from environment/site overlays and secrets; prohibit rebuilding binaries merely to change operational configuration.
- [ ] Make activation transactional: stage, validate, apply, verify, publish active version, and only then retire the previous version.

### B. Component-specific implementation

- [ ] Automate prerequisite checks, package installation, backend feature detection, directory/permission creation, and service registration from a clean node.
- [ ] Make installation idempotent and support offline/cache-backed installation where required by deployment context.
- [ ] Validate the installed node with a signed smoke-test sandbox and capture bootstrap evidence.
- [ ] Persist provenance sufficient to answer who/what/when/where/why for every active configuration and retain the immediately previous known-good configuration.
- [ ] Provide deterministic bootstrap/recovery procedures that are testable from an empty supported node without undocumented manual state.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-029; define the error returned on limit breach.
- [ ] Make MC-029 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Deterministic bootstrap/install path from an empty supported node** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-029 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-029 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-029 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-029 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-029 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-029 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-029 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-029 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-029.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Deterministic bootstrap/install path from an empty supported node**.


# Production sandbox enforcement backends

## MC-030 — Native Linux seccomp filter compiler/installer

**Audit status:** Missing  
**Checklist linkage:** C031, C034, C042-C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **native Linux seccomp filter compiler/installer** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-030 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Native Linux seccomp filter compiler/installer** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Compile a canonical syscall policy into BPF using a maintained binding/toolchain; define default action, architecture checks, argument filters, and explicit behavior for unknown syscalls.
- [ ] Install seccomp only after `no_new_privs` and before exec; verify the process is in seccomp filter mode and cannot reset or loosen the filter.
- [ ] Generate architecture-specific syscall resolution tables and test x86_64/aarch64 differences plus x32/compat ABI rejection where relevant.
- [ ] Add kill/errno/log action tests and adversarial attempts using `ptrace`, `clone3`, `unshare`, `bpf`, `perf_event_open`, keyrings, and namespace-sensitive syscalls according to policy.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-030; define the error returned on limit breach.
- [ ] Make MC-030 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Native Linux seccomp filter compiler/installer** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-030 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-030 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-030 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-030 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-030 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-030 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-030 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-030 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-030.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Native Linux seccomp filter compiler/installer**.

## MC-031 — Linux bubblewrap (`bwrap`) launcher/integration adapter

**Audit status:** Missing  
**Checklist linkage:** C010, C031, C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **linux bubblewrap (`bwrap`) launcher/integration adapter** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-031 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Linux bubblewrap (`bwrap`) launcher/integration adapter** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Invoke `bwrap` without a shell using a prevalidated argv vector; pin/verify executable path and version and reject environment/PATH substitution.
- [ ] Construct namespaces, binds, tmpfs, proc/dev exposure, uid/gid, capabilities, network, and working directory from the canonical profile using a deterministic argument builder.
- [ ] Capture child PID/exit status and differentiate bwrap setup failure from workload failure; scrub inherited FDs/environment before launch.
- [ ] Run integration tests against real bwrap on supported distributions and assert mount/network/process views from inside the sandbox.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-031; define the error returned on limit breach.
- [ ] Make MC-031 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Linux bubblewrap (`bwrap`) launcher/integration adapter** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-031 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-031 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-031 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-031 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-031 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-031 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-031 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-031 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-031.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Linux bubblewrap (`bwrap`) launcher/integration adapter**.

## MC-032 — macOS Seatbelt profile compiler/launcher/verification adapter

**Audit status:** Missing  
**Checklist linkage:** C010, C031, C084  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **macOS Seatbelt profile compiler/launcher/verification adapter** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-032 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **macOS Seatbelt profile compiler/launcher/verification adapter** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Define a deterministic mapping from canonical profile controls to Seatbelt profile syntax and document controls with no macOS-equivalent semantics.
- [ ] Compile/validate profiles before launch and invoke the supported sandbox mechanism without shell interpolation or untrusted textual substitution.
- [ ] Version-gate against macOS releases and maintain regression tests because Seatbelt behavior is private/OS-sensitive.
- [ ] Verify representative file/network/process denials from inside the launched process and fail closed for unrepresentable mandatory controls.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-032; define the error returned on limit breach.
- [ ] Make MC-032 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **macOS Seatbelt profile compiler/launcher/verification adapter** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-032 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-032 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-032 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-032 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-032 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-032 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-032 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-032 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-032.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **macOS Seatbelt profile compiler/launcher/verification adapter**.

## MC-033 — Backend capability discovery and fail-closed platform feature probing

**Audit status:** Missing  
**Checklist linkage:** C031, C034, C084  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **backend capability discovery and fail-closed platform feature probing** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-033 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Backend capability discovery and fail-closed platform feature probing** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Probe kernel features using direct capability tests or authoritative files/syscalls, not version-number assumptions alone.
- [ ] Return a machine-readable feature set including seccomp, user/mount/net/PID namespaces, cgroup v2 controllers, Landlock ABI, unprivileged userns policy, and backend binary versions.
- [ ] Bind the discovered feature snapshot to admission decisions and release evidence; re-probe after reboot/kernel/backend change.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-033; define the error returned on limit breach.
- [ ] Make MC-033 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Backend capability discovery and fail-closed platform feature probing** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-033 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-033 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-033 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-033 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-033 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-033 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-033 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-033 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-033.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Backend capability discovery and fail-closed platform feature probing**.

## MC-034 — `PR_SET_NO_NEW_PRIVS` enforcement before child execution

**Audit status:** Missing  
**Checklist linkage:** C042-C043  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **`PR_SET_NO_NEW_PRIVS` enforcement before child execution** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-034 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **`PR_SET_NO_NEW_PRIVS` enforcement before child execution** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Set `PR_SET_NO_NEW_PRIVS=1` in the child setup path before seccomp or exec and treat any failure as terminal.
- [ ] Read back `NoNewPrivs` from `/proc/<pid>/status` where available and include the result in enforcement evidence.
- [ ] Test that setuid/file-capability executables cannot regain privilege after the flag is set.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-034; define the error returned on limit breach.
- [ ] Make MC-034 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **`PR_SET_NO_NEW_PRIVS` enforcement before child execution** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-034 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-034 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-034 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-034 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-034 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-034 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-034 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-034 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-034.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **`PR_SET_NO_NEW_PRIVS` enforcement before child execution**.

## MC-035 — UID/GID switching, supplementary-group clearing, user-namespace mapping, and setuid/file-capability regain prevention

**Audit status:** Missing  
**Checklist linkage:** C042-C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **uID/GID switching, supplementary-group clearing, user-namespace mapping, and setuid/file-capability regain prevention** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-035 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **UID/GID switching, supplementary-group clearing, user-namespace mapping, and setuid/file-capability regain prevention** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Clear supplementary groups before uid/gid drop; configure uid/gid maps with correct setgroups ordering and minimal mapping ranges.
- [ ] Ensure the final effective/real/saved IDs satisfy the profile and cannot regain host privileges through saved IDs, setuid binaries, file capabilities, or namespace mapping.
- [ ] Validate filesystem ownership/mount behavior under user namespaces and test host-uid escape attempts.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-035; define the error returned on limit breach.
- [ ] Make MC-035 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **UID/GID switching, supplementary-group clearing, user-namespace mapping, and setuid/file-capability regain prevention** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-035 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-035 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-035 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-035 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-035 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-035 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-035 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-035 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-035.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **UID/GID switching, supplementary-group clearing, user-namespace mapping, and setuid/file-capability regain prevention**.

## MC-036 — Complete Linux capability handling: bounding, permitted, effective, inheritable, and ambient set reduction

**Audit status:** Missing  
**Checklist linkage:** C042-C043  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **complete Linux capability handling: bounding, permitted, effective, inheritable, and ambient set reduction** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-036 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Complete Linux capability handling: bounding, permitted, effective, inheritable, and ambient set reduction** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Compute the exact final bounding/permitted/effective/inheritable/ambient capability sets and drop every capability not explicitly required.
- [ ] Clear ambient capabilities and securebits interactions; apply bounding-set drops before uid transitions where kernel semantics require it.
- [ ] Read `/proc/<pid>/status` capability masks and compare to expected bitsets; test attempted capability regain across exec.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-036; define the error returned on limit breach.
- [ ] Make MC-036 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Complete Linux capability handling: bounding, permitted, effective, inheritable, and ambient set reduction** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-036 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-036 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-036 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-036 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-036 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-036 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-036 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-036 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-036.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Complete Linux capability handling: bounding, permitted, effective, inheritable, and ambient set reduction**.

## MC-037 — Mount namespace hardening, private propagation, root/pivot isolation, read-only bind policy, and safe temporary filesystem setup

**Audit status:** Missing  
**Checklist linkage:** C043, C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **mount namespace hardening, private propagation, root/pivot isolation, read-only bind policy, and safe temporary filesystem setup** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-037 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Mount namespace hardening, private propagation, root/pivot isolation, read-only bind policy, and safe temporary filesystem setup** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Create a private mount namespace and make propagation private/slave as designed before constructing the sandbox filesystem.
- [ ] Use pivot_root/chroot-equivalent only with verified mount topology; prevent access to the host root through old-root FDs, mount propagation, proc magic links, or writable bind parents.
- [ ] Canonicalize bind sources/targets, reject traversal/symlink races, enforce ro/rw/noexec/nosuid/nodev flags, and create tmpfs with explicit size/inode limits.
- [ ] Test host-path escape, symlink swap, bind-over-sensitive-path, mount propagation, and cleanup after abnormal termination.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-037; define the error returned on limit breach.
- [ ] Make MC-037 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Mount namespace hardening, private propagation, root/pivot isolation, read-only bind policy, and safe temporary filesystem setup** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-037 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-037 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-037 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-037 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-037 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-037 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-037 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-037 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-037.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Mount namespace hardening, private propagation, root/pivot isolation, read-only bind policy, and safe temporary filesystem setup**.

## MC-038 — Optional Landlock/filesystem policy backend promised by the contract

**Audit status:** Missing  
**Checklist linkage:** C043, C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **optional Landlock/filesystem policy backend promised by the contract** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-038 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Optional Landlock/filesystem policy backend promised by the contract** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Detect Landlock ABI at runtime and map filesystem rights conservatively; reject mandatory profiles if required rights are unsupported.
- [ ] Set `no_new_privs`, create the ruleset, add canonical path-beneath rules using race-resistant file descriptors, and restrict self before exec.
- [ ] Test allowed/denied reads, writes, creation, rename, truncate, execute, and referenced-object operations across ABI versions.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-038; define the error returned on limit breach.
- [ ] Make MC-038 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Optional Landlock/filesystem policy backend promised by the contract** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-038 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-038 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-038 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-038 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-038 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-038 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-038 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-038 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-038.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Optional Landlock/filesystem policy backend promised by the contract**.

## MC-039 — Network namespace setup, interface policy, inherited-socket control, and network egress policy

**Audit status:** Missing  
**Checklist linkage:** C043, C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **network namespace setup, interface policy, inherited-socket control, and network egress policy** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-039 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Network namespace setup, interface policy, inherited-socket control, and network egress policy** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Create or join an explicit network namespace before exec and define loopback/interface/DNS/routing policy from the profile.
- [ ] Close inherited network sockets and other communication FDs unless explicitly allow-listed; verify no host-network socket survives setup.
- [ ] Enforce egress/ingress restrictions using namespace routing/firewall/eBPF or an approved broker and bind rules to workload identity.
- [ ] Test raw sockets, localhost-to-host confusion, IPv6, abstract Unix sockets, DNS bypass, inherited sockets, and reconnect behavior.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-039; define the error returned on limit breach.
- [ ] Make MC-039 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Network namespace setup, interface policy, inherited-socket control, and network egress policy** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-039 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-039 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-039 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-039 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-039 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-039 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-039 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-039 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-039.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Network namespace setup, interface policy, inherited-socket control, and network egress policy**.

## MC-040 — Device isolation and `/proc`/`/sys` exposure policy

**Audit status:** Missing  
**Checklist linkage:** C043, C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **device isolation and `/proc`/`/sys` exposure policy** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-040 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Device isolation and `/proc`/`/sys` exposure policy** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Expose only required device nodes and mount proc/sys with hidepid/read-only/masked paths appropriate to the threat model.
- [ ] Prevent access to host block devices, `/dev/mem`, kvm, fuse, tun, gpu, perf, input, and other privileged devices unless explicitly mediated.
- [ ] Test procfs/sysfs information leaks and write paths, including namespace-crossing pid/proc references.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-040; define the error returned on limit breach.
- [ ] Make MC-040 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Device isolation and `/proc`/`/sys` exposure policy** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-040 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-040 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-040 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-040 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-040 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-040 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-040 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-040 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-040.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Device isolation and `/proc`/`/sys` exposure policy**.

## MC-041 — File-descriptor inheritance closure / allow-list

**Audit status:** Missing  
**Checklist linkage:** C043, C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **file-descriptor inheritance closure / allow-list** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-041 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **File-descriptor inheritance closure / allow-list** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Enumerate open descriptors immediately before exec and close everything except an explicit allow-list using close_range/proc-fd fallback.
- [ ] Set CLOEXEC defensively at creation time and validate passed FDs by type, ownership, flags, peer, path/inode where applicable.
- [ ] Test inherited files, sockets, memfd, pidfd, eventfd, directory FDs, deleted-but-open files, and privileged broker channels.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-041; define the error returned on limit breach.
- [ ] Make MC-041 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **File-descriptor inheritance closure / allow-list** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-041 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-041 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-041 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-041 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-041 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-041 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-041 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-041 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-041.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **File-descriptor inheritance closure / allow-list**.

## MC-042 — Environment-variable sanitization and dangerous loader-variable stripping

**Audit status:** Missing  
**Checklist linkage:** C043, C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **environment-variable sanitization and dangerous loader-variable stripping** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-042 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Environment-variable sanitization and dangerous loader-variable stripping** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Construct the child environment from an allow-list rather than mutating the parent environment in place.
- [ ] Strip dynamic-loader/interpreter injection variables such as `LD_PRELOAD`, `LD_LIBRARY_PATH`, `DYLD_*`, language startup hooks, proxy variables, and tool-specific plugin paths unless explicitly required.
- [ ] Normalize PATH, locale, HOME, TMPDIR, working directory, and encoding behavior and test hostile variable values including NUL/control/Unicode edge cases.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-042; define the error returned on limit breach.
- [ ] Make MC-042 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Environment-variable sanitization and dangerous loader-variable stripping** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-042 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-042 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-042 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-042 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-042 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-042 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-042 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-042 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-042.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Environment-variable sanitization and dangerous loader-variable stripping**.

## MC-043 — Resource enforcement using rlimits and/or cgroup v2 for processes, CPU, memory, I/O, and file descriptors

**Audit status:** Missing  
**Checklist linkage:** C017, C043, C050, C054, C067  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **resource enforcement using rlimits and/or cgroup v2 for processes, CPU, memory, I/O, and file descriptors** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-043 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Resource enforcement using rlimits and/or cgroup v2 for processes, CPU, memory, I/O, and file descriptors** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Create a per-sandbox cgroup v2 subtree and apply pids.max, memory.max/high/swap, cpu.max/weight, io.max/weight, and appropriate pressure/accounting controls.
- [ ] Apply RLIMIT_NOFILE, NPROC, CORE, FSIZE, AS/DATA/STACK and other relevant rlimits as defense in depth, documenting namespace/root caveats.
- [ ] Verify controller delegation and read back effective limits before exec; treat inability to enforce mandatory limits as admission failure.
- [ ] Test OOM, fork bombs, FD exhaustion, disk/I/O pressure, CPU saturation, cleanup, and accounting accuracy.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-043; define the error returned on limit breach.
- [ ] Make MC-043 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Resource enforcement using rlimits and/or cgroup v2 for processes, CPU, memory, I/O, and file descriptors** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-043 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-043 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-043 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-043 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-043 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-043 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-043 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-043 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-043.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Resource enforcement using rlimits and/or cgroup v2 for processes, CPU, memory, I/O, and file descriptors**.

## MC-044 — Child launcher that guarantees no workload code executes before all containment controls are active

**Audit status:** Missing  
**Checklist linkage:** C034, C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **child launcher that guarantees no workload code executes before all containment controls are active** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-044 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Child launcher that guarantees no workload code executes before all containment controls are active** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Use a fork/clone/posix_spawn design that keeps the child blocked on a synchronization barrier until the parent/backend completes setup and verification.
- [ ] Perform sensitive child-side operations in a minimal async-signal-safe path and avoid running language runtime hooks after fork where unsafe.
- [ ] Close the barrier only after namespaces, mounts, IDs, capabilities, no_new_privs, seccomp/Landlock, rlimits/cgroup, environment, FDs, and cwd are final.
- [ ] Add an instrumented test workload that attempts a forbidden action as its first instruction to prove ordering.
- [ ] Define incident classes for sandbox escape/suspected escape, policy bypass, evidence forgery, widespread launch failure, cleanup leak, and control-plane compromise.
- [ ] Specify paging targets, severity criteria, containment actions, evidence preservation, forensic acquisition, communication, recovery, and post-incident review.
- [ ] Run tabletop and live game-day exercises including emergency disable and credential/key rotation.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-044; define the error returned on limit breach.
- [ ] Make MC-044 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Child launcher that guarantees no workload code executes before all containment controls are active** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-044 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-044 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-044 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-044 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-044 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-044 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-044 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-044 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-044.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Child launcher that guarantees no workload code executes before all containment controls are active**.

## MC-045 — PID 1/subreaper behavior, signal forwarding, child reaping, timeout termination, and cleanup

**Audit status:** Missing  
**Checklist linkage:** C051-C057  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **pID 1/subreaper behavior, signal forwarding, child reaping, timeout termination, and cleanup** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-045 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **PID 1/subreaper behavior, signal forwarding, child reaping, timeout termination, and cleanup** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Define whether the sandbox launcher is namespace PID 1 or a subreaper and implement correct orphan adoption/zombie reaping.
- [ ] Forward permitted signals with documented translation/escalation; use process groups/pidfds to avoid PID-reuse races.
- [ ] Implement timeout TERM->grace->KILL sequencing and verify all descendants are terminated before cleanup is reported complete.
- [ ] Test double-fork, daemonization, signal storms, stuck uninterruptible processes, launcher crash, and descendant escape attempts.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-045; define the error returned on limit breach.
- [ ] Make MC-045 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **PID 1/subreaper behavior, signal forwarding, child reaping, timeout termination, and cleanup** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-045 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-045 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-045 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-045 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-045 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-045 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-045 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-045 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-045.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **PID 1/subreaper behavior, signal forwarding, child reaping, timeout termination, and cleanup**.

## MC-046 — Trustworthy backend applied-state attestation/read-back bound to `profile_digest`

**Audit status:** Missing  
**Checklist linkage:** C004, C034, C045, C049  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **trustworthy backend applied-state attestation/read-back bound to `profile_digest`** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-046 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Trustworthy backend applied-state attestation/read-back bound to `profile_digest`** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Define an evidence envelope containing canonical profile digest, node identity, workload/sandbox ID, backend/version, control results, monotonic sequence/nonce, timestamps, and release lineage.
- [ ] Separate directly read-back facts from asserted installer actions and label evidence strength per field; never represent installer intent as kernel proof.
- [ ] Sign/MAC evidence at a trust boundary inaccessible to the untrusted workload and validate freshness plus node/profile binding on consumption.
- [ ] For seccomp and other non-introspectable controls, generate install-time evidence from the exact compiled artifact and pair it with independent behavioral probes.
- [ ] Create a dependency-criticality table stating whether each unavailable trust service causes reject, quarantine, cached-read-only mode, or another approved safe state.
- [ ] Bound cached trust decisions by signed epoch/TTL and prevent clock rollback from extending validity.
- [ ] Fault-inject each trust dependency during admission and execution and verify the documented fail-safe behavior.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-046; define the error returned on limit breach.
- [ ] Make MC-046 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Trustworthy backend applied-state attestation/read-back bound to `profile_digest`** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-046 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-046 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-046 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-046 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-046 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-046 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-046 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-046 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-046.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Trustworthy backend applied-state attestation/read-back bound to `profile_digest`**.

## MC-047 — Kernel/backend evidence adapter for facts that cannot be exactly read back from normal kernel APIs (notably installed seccomp rule contents)

**Audit status:** Missing  
**Checklist linkage:** C004, C045, C090  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **kernel/backend evidence adapter for facts that cannot be exactly read back from normal kernel APIs (notably installed seccomp rule contents)** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-047 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Kernel/backend evidence adapter for facts that cannot be exactly read back from normal kernel APIs (notably installed seccomp rule contents)** across each supported OS/backend/deployment mode.
- [ ] Implement the control in the privileged launcher/backend, not only in the policy model; the backend must return evidence derived from enforcement actions or trustworthy kernel/runtime read-back.
- [ ] Guarantee ordering so no untrusted workload instruction executes before all mandatory containment controls are active and verified.
- [ ] Treat partial application as failure: terminate the child, clean up namespaces/cgroups/mounts/files, emit evidence, and never report a verified sandbox.
- [ ] Use allow-lists and explicit deny-by-default semantics for security-sensitive resources; canonicalize all paths, identifiers, capability names, syscall names, and backend arguments.

### B. Component-specific implementation

- [ ] Compile a canonical syscall policy into BPF using a maintained binding/toolchain; define default action, architecture checks, argument filters, and explicit behavior for unknown syscalls.
- [ ] Install seccomp only after `no_new_privs` and before exec; verify the process is in seccomp filter mode and cannot reset or loosen the filter.
- [ ] Generate architecture-specific syscall resolution tables and test x86_64/aarch64 differences plus x32/compat ABI rejection where relevant.
- [ ] Add kill/errno/log action tests and adversarial attempts using `ptrace`, `clone3`, `unshare`, `bpf`, `perf_event_open`, keyrings, and namespace-sensitive syscalls according to policy.
- [ ] Define an evidence envelope containing canonical profile digest, node identity, workload/sandbox ID, backend/version, control results, monotonic sequence/nonce, timestamps, and release lineage.
- [ ] Separate directly read-back facts from asserted installer actions and label evidence strength per field; never represent installer intent as kernel proof.
- [ ] Sign/MAC evidence at a trust boundary inaccessible to the untrusted workload and validate freshness plus node/profile binding on consumption.
- [ ] For seccomp and other non-introspectable controls, generate install-time evidence from the exact compiled artifact and pair it with independent behavioral probes.
- [ ] Prevent confused-deputy behavior by binding backend operations to tenant/workload/profile identity and a canonical `profile_digest`.
- [ ] Expose backend capability discovery and reject profiles requiring unavailable primitives rather than silently degrading isolation.
- [ ] Make cleanup idempotent and crash-safe; leaked namespaces, mounts, cgroups, FDs, sockets, helper processes, or temporary files are release-blocking defects.
- [ ] Add real-OS integration tests that inspect resulting kernel/runtime state and attempt representative escapes, not only unit tests of requested policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-047; define the error returned on limit breach.
- [ ] Make MC-047 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Kernel/backend evidence adapter for facts that cannot be exactly read back from normal kernel APIs (notably installed seccomp rule contents)** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-047 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-047 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-047 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-047 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-047 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-047 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-047 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-047 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-047.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Kernel/backend evidence adapter for facts that cannot be exactly read back from normal kernel APIs (notably installed seccomp rule contents)**.


# Security, trust, and audit

## MC-048 — Backend-specific threat model with attack paths, mitigations, owners, and tests linked to each threat

**Audit status:** Partial: high-level `SECURITY.md` only  
**Checklist linkage:** C041, C050, C087  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **backend-specific threat model with attack paths, mitigations, owners, and tests linked to each threat** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-048 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Backend-specific threat model with attack paths, mitigations, owners, and tests linked to each threat** across each supported OS/backend/deployment mode.
- [ ] Model attacker goals, entry points, privileges, trust anchors, replay/downgrade paths, cross-tenant paths, and evidence-forgery paths before implementation.
- [ ] Bind policy, identity, enforcement evidence, timestamps/counters, and release lineage cryptographically so evidence from another sandbox/profile/node cannot be replayed as current proof.
- [ ] Fail closed when identity, attestation, keys, policy, trusted time, or evidence verification is unavailable unless an explicitly approved degraded mode proves equivalent isolation.
- [ ] Ensure security-relevant logs/evidence are tamper-evident, append-only or externally anchored, access-controlled, privacy-reviewed, and protected from attacker-controlled log injection.

### B. Component-specific implementation

- [ ] Create a RACI covering design authority, code ownership, production operations, incident command, security approval, and emergency disable authority.
- [ ] Define escalation targets and acknowledgement/resolution objectives for Sev-1/Sev-2 security or availability incidents; test the contact path at least quarterly.
- [ ] Add repository ownership metadata and a machine-readable owner field to release evidence so orphaned components are detectable automatically.
- [ ] Use STRIDE/attack-tree style analysis for malicious workload, malicious tenant, compromised control plane, compromised node agent, insider, and supply-chain adversaries.
- [ ] Cover kernel escape, namespace confusion, mount/path races, FD leaks, capability regain, syscall gaps, evidence forgery, policy downgrade, side channels, and denial of service.
- [ ] Assign each threat likelihood/impact, mitigation owner, verification test, and residual-risk disposition.
- [ ] Derive adversarial tests directly from the threat model and maintain bidirectional links between threat IDs, mitigations, tests, and residual-risk approvals.
- [ ] Require independent security review for changes that modify privilege boundaries, namespace/capability/seccomp policy, evidence verification, signing, or trust-root handling.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-048; define the error returned on limit breach.
- [ ] Make MC-048 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Backend-specific threat model with attack paths, mitigations, owners, and tests linked to each threat** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-048 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-048 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-048 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-048 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-048 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-048 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-048 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-048 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-048.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Backend-specific threat model with attack paths, mitigations, owners, and tests linked to each threat**.

## MC-049 — Signed policy/artifact verification, digest pinning, provenance validation, and downgrade protection

**Audit status:** Missing  
**Checklist linkage:** C045  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **signed policy/artifact verification, digest pinning, provenance validation, and downgrade protection** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-049 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Signed policy/artifact verification, digest pinning, provenance validation, and downgrade protection** across each supported OS/backend/deployment mode.
- [ ] Model attacker goals, entry points, privileges, trust anchors, replay/downgrade paths, cross-tenant paths, and evidence-forgery paths before implementation.
- [ ] Bind policy, identity, enforcement evidence, timestamps/counters, and release lineage cryptographically so evidence from another sandbox/profile/node cannot be replayed as current proof.
- [ ] Fail closed when identity, attestation, keys, policy, trusted time, or evidence verification is unavailable unless an explicitly approved degraded mode proves equivalent isolation.
- [ ] Ensure security-relevant logs/evidence are tamper-evident, append-only or externally anchored, access-controlled, privacy-reviewed, and protected from attacker-controlled log injection.

### B. Component-specific implementation

- [ ] Define canonical bytes to sign, approved algorithms/key sizes, key IDs, trust roots, signature envelope, expiry/epoch, and multi-signature rules if required.
- [ ] Verify signature and digest before parsing/activation side effects; pin minimum schema/policy/backend versions to prevent downgrade.
- [ ] Implement key rotation/revocation and test stale/revoked/unknown-key/replayed policy rejection.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Derive adversarial tests directly from the threat model and maintain bidirectional links between threat IDs, mitigations, tests, and residual-risk approvals.
- [ ] Require independent security review for changes that modify privilege boundaries, namespace/capability/seccomp policy, evidence verification, signing, or trust-root handling.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-049; define the error returned on limit breach.
- [ ] Make MC-049 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Signed policy/artifact verification, digest pinning, provenance validation, and downgrade protection** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-049 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-049 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-049 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-049 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-049 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-049 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-049 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-049 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-049.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Signed policy/artifact verification, digest pinning, provenance validation, and downgrade protection**.

## MC-050 — Node/control-plane identity and attestation mechanism before trusting profile or evidence sources

**Audit status:** Missing  
**Checklist linkage:** C044  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **node/control-plane identity and attestation mechanism before trusting profile or evidence sources** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-050 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Node/control-plane identity and attestation mechanism before trusting profile or evidence sources** across each supported OS/backend/deployment mode.
- [ ] Model attacker goals, entry points, privileges, trust anchors, replay/downgrade paths, cross-tenant paths, and evidence-forgery paths before implementation.
- [ ] Bind policy, identity, enforcement evidence, timestamps/counters, and release lineage cryptographically so evidence from another sandbox/profile/node cannot be replayed as current proof.
- [ ] Fail closed when identity, attestation, keys, policy, trusted time, or evidence verification is unavailable unless an explicitly approved degraded mode proves equivalent isolation.
- [ ] Ensure security-relevant logs/evidence are tamper-evident, append-only or externally anchored, access-controlled, privacy-reviewed, and protected from attacker-controlled log injection.

### B. Component-specific implementation

- [ ] Define node identity issuance, key storage/protection, rotation, revocation, and workload/control-plane identity binding.
- [ ] If hardware attestation is required, specify measured components, nonce freshness, reference values, verifier policy, and failure semantics.
- [ ] Bind accepted policy/evidence to the authenticated node/controller identity and reject cross-node replay.
- [ ] Create a dependency-criticality table stating whether each unavailable trust service causes reject, quarantine, cached-read-only mode, or another approved safe state.
- [ ] Bound cached trust decisions by signed epoch/TTL and prevent clock rollback from extending validity.
- [ ] Fault-inject each trust dependency during admission and execution and verify the documented fail-safe behavior.
- [ ] Derive adversarial tests directly from the threat model and maintain bidirectional links between threat IDs, mitigations, tests, and residual-risk approvals.
- [ ] Require independent security review for changes that modify privilege boundaries, namespace/capability/seccomp policy, evidence verification, signing, or trust-root handling.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-050; define the error returned on limit breach.
- [ ] Make MC-050 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Node/control-plane identity and attestation mechanism before trusting profile or evidence sources** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-050 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-050 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-050 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-050 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-050 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-050 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-050 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-050 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-050.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Node/control-plane identity and attestation mechanism before trusting profile or evidence sources**.

## MC-051 — Isolation proof/tests spanning execution, memory, filesystem/state, network, and device boundaries

**Audit status:** Missing  
**Checklist linkage:** C046  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **isolation proof/tests spanning execution, memory, filesystem/state, network, and device boundaries** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-051 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Isolation proof/tests spanning execution, memory, filesystem/state, network, and device boundaries** across each supported OS/backend/deployment mode.
- [ ] Model attacker goals, entry points, privileges, trust anchors, replay/downgrade paths, cross-tenant paths, and evidence-forgery paths before implementation.
- [ ] Bind policy, identity, enforcement evidence, timestamps/counters, and release lineage cryptographically so evidence from another sandbox/profile/node cannot be replayed as current proof.
- [ ] Fail closed when identity, attestation, keys, policy, trusted time, or evidence verification is unavailable unless an explicitly approved degraded mode proves equivalent isolation.
- [ ] Ensure security-relevant logs/evidence are tamper-evident, append-only or externally anchored, access-controlled, privacy-reviewed, and protected from attacker-controlled log injection.

### B. Component-specific implementation

- [ ] Build black-box probes for filesystem, process, memory, network, IPC, device, credentials, namespace, and resource boundaries from inside the sandbox.
- [ ] Add cross-sandbox and sandbox-to-host attack cases including shared-memory, procfs, Unix sockets, abstract sockets, pid namespace, and writable mount probes.
- [ ] Require every mandatory control to have at least one positive and one negative behavioral proof.
- [ ] Derive adversarial tests directly from the threat model and maintain bidirectional links between threat IDs, mitigations, tests, and residual-risk approvals.
- [ ] Require independent security review for changes that modify privilege boundaries, namespace/capability/seccomp policy, evidence verification, signing, or trust-root handling.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-051; define the error returned on limit breach.
- [ ] Make MC-051 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Isolation proof/tests spanning execution, memory, filesystem/state, network, and device boundaries** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-051 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-051 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-051 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-051 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-051 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-051 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-051 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-051 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-051.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Isolation proof/tests spanning execution, memory, filesystem/state, network, and device boundaries**.

## MC-052 — Encryption design for any remote sensitive profile/evidence transport and at-rest sensitive state

**Audit status:** Missing / conditional on deployment  
**Checklist linkage:** C047  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **encryption design for any remote sensitive profile/evidence transport and at-rest sensitive state** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-052 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Encryption design for any remote sensitive profile/evidence transport and at-rest sensitive state** across each supported OS/backend/deployment mode.
- [ ] Model attacker goals, entry points, privileges, trust anchors, replay/downgrade paths, cross-tenant paths, and evidence-forgery paths before implementation.
- [ ] Bind policy, identity, enforcement evidence, timestamps/counters, and release lineage cryptographically so evidence from another sandbox/profile/node cannot be replayed as current proof.
- [ ] Fail closed when identity, attestation, keys, policy, trusted time, or evidence verification is unavailable unless an explicitly approved degraded mode proves equivalent isolation.
- [ ] Ensure security-relevant logs/evidence are tamper-evident, append-only or externally anchored, access-controlled, privacy-reviewed, and protected from attacker-controlled log injection.

### B. Component-specific implementation

- [ ] Classify profile/evidence fields by sensitivity and define TLS/mTLS or equivalent transport protection plus at-rest encryption requirements.
- [ ] Specify certificate/key lifecycle, cipher/protocol minimums, hostname/service identity validation, and rotation behavior.
- [ ] Test plaintext downgrade, invalid peer identity, expired/revoked credentials, and secret leakage through diagnostics.
- [ ] Derive adversarial tests directly from the threat model and maintain bidirectional links between threat IDs, mitigations, tests, and residual-risk approvals.
- [ ] Require independent security review for changes that modify privilege boundaries, namespace/capability/seccomp policy, evidence verification, signing, or trust-root handling.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-052; define the error returned on limit breach.
- [ ] Make MC-052 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Encryption design for any remote sensitive profile/evidence transport and at-rest sensitive state** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-052 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-052 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-052 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-052 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-052 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-052 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-052 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-052 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-052.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Encryption design for any remote sensitive profile/evidence transport and at-rest sensitive state**.

## MC-053 — Fail-safe behavior when identity, attestation, policy, key, or trusted-time services are unavailable

**Audit status:** Missing  
**Checklist linkage:** C048  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **fail-safe behavior when identity, attestation, policy, key, or trusted-time services are unavailable** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-053 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Fail-safe behavior when identity, attestation, policy, key, or trusted-time services are unavailable** across each supported OS/backend/deployment mode.
- [ ] Model attacker goals, entry points, privileges, trust anchors, replay/downgrade paths, cross-tenant paths, and evidence-forgery paths before implementation.
- [ ] Bind policy, identity, enforcement evidence, timestamps/counters, and release lineage cryptographically so evidence from another sandbox/profile/node cannot be replayed as current proof.
- [ ] Fail closed when identity, attestation, keys, policy, trusted time, or evidence verification is unavailable unless an explicitly approved degraded mode proves equivalent isolation.
- [ ] Ensure security-relevant logs/evidence are tamper-evident, append-only or externally anchored, access-controlled, privacy-reviewed, and protected from attacker-controlled log injection.

### B. Component-specific implementation

- [ ] Create a dependency-criticality table stating whether each unavailable trust service causes reject, quarantine, cached-read-only mode, or another approved safe state.
- [ ] Bound cached trust decisions by signed epoch/TTL and prevent clock rollback from extending validity.
- [ ] Fault-inject each trust dependency during admission and execution and verify the documented fail-safe behavior.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Derive adversarial tests directly from the threat model and maintain bidirectional links between threat IDs, mitigations, tests, and residual-risk approvals.
- [ ] Require independent security review for changes that modify privilege boundaries, namespace/capability/seccomp policy, evidence verification, signing, or trust-root handling.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-053; define the error returned on limit breach.
- [ ] Make MC-053 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Fail-safe behavior when identity, attestation, policy, key, or trusted-time services are unavailable** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-053 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-053 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-053 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-053 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-053 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-053 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-053 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-053 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-053.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Fail-safe behavior when identity, attestation, policy, key, or trusted-time services are unavailable**.

## MC-054 — Tamper-evident security audit-event sink / append-only evidence chain

**Audit status:** Missing  
**Checklist linkage:** C049  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **tamper-evident security audit-event sink / append-only evidence chain** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-054 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Tamper-evident security audit-event sink / append-only evidence chain** across each supported OS/backend/deployment mode.
- [ ] Model attacker goals, entry points, privileges, trust anchors, replay/downgrade paths, cross-tenant paths, and evidence-forgery paths before implementation.
- [ ] Bind policy, identity, enforcement evidence, timestamps/counters, and release lineage cryptographically so evidence from another sandbox/profile/node cannot be replayed as current proof.
- [ ] Fail closed when identity, attestation, keys, policy, trusted time, or evidence verification is unavailable unless an explicitly approved degraded mode proves equivalent isolation.
- [ ] Ensure security-relevant logs/evidence are tamper-evident, append-only or externally anchored, access-controlled, privacy-reviewed, and protected from attacker-controlled log injection.

### B. Component-specific implementation

- [ ] Use hash chaining, signed batches, WORM storage, transparency anchoring, or equivalent controls to make deletion/reordering/modification detectable.
- [ ] Include event sequence, actor, sandbox/workload, node, operation, profile digest, decision, result, and prior-event digest where appropriate.
- [ ] Test gap detection, duplicate/reordered events, sink outage buffering, overflow behavior, and recovery without silent loss.
- [ ] Derive adversarial tests directly from the threat model and maintain bidirectional links between threat IDs, mitigations, tests, and residual-risk approvals.
- [ ] Require independent security review for changes that modify privilege boundaries, namespace/capability/seccomp policy, evidence verification, signing, or trust-root handling.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-054; define the error returned on limit breach.
- [ ] Make MC-054 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Tamper-evident security audit-event sink / append-only evidence chain** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-054 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-054 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-054 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-054 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-054 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-054 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-054 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-054 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-054.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Tamper-evident security audit-event sink / append-only evidence chain**.

## MC-055 — Adversarial escape suite covering privilege escalation, injection, replay, spoofing, sandbox escape, side channels, and resource exhaustion

**Audit status:** Missing  
**Checklist linkage:** C050, C087  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **adversarial escape suite covering privilege escalation, injection, replay, spoofing, sandbox escape, side channels, and resource exhaustion** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-055 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Adversarial escape suite covering privilege escalation, injection, replay, spoofing, sandbox escape, side channels, and resource exhaustion** across each supported OS/backend/deployment mode.
- [ ] Model attacker goals, entry points, privileges, trust anchors, replay/downgrade paths, cross-tenant paths, and evidence-forgery paths before implementation.
- [ ] Bind policy, identity, enforcement evidence, timestamps/counters, and release lineage cryptographically so evidence from another sandbox/profile/node cannot be replayed as current proof.
- [ ] Fail closed when identity, attestation, keys, policy, trusted time, or evidence verification is unavailable unless an explicitly approved degraded mode proves equivalent isolation.
- [ ] Ensure security-relevant logs/evidence are tamper-evident, append-only or externally anchored, access-controlled, privacy-reviewed, and protected from attacker-controlled log injection.

### B. Component-specific implementation

- [ ] Create a RACI covering design authority, code ownership, production operations, incident command, security approval, and emergency disable authority.
- [ ] Define escalation targets and acknowledgement/resolution objectives for Sev-1/Sev-2 security or availability incidents; test the contact path at least quarterly.
- [ ] Add repository ownership metadata and a machine-readable owner field to release evidence so orphaned components are detectable automatically.
- [ ] Create reproducible attack cases for privilege regain, setuid/file caps, namespace/mount escape, ptrace, procfs/sysfs abuse, dangerous syscalls, FD/socket inheritance, environment injection, and backend argument injection.
- [ ] Add resource exhaustion/fork bomb/OOM/I/O pressure and representative timing/cache/shared-resource side-channel probes appropriate to the isolation claim.
- [ ] Run the suite on every supported kernel/backend combination and retain exact exploit/probe versions plus expected denial evidence.
- [ ] Derive adversarial tests directly from the threat model and maintain bidirectional links between threat IDs, mitigations, tests, and residual-risk approvals.
- [ ] Require independent security review for changes that modify privilege boundaries, namespace/capability/seccomp policy, evidence verification, signing, or trust-root handling.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-055; define the error returned on limit breach.
- [ ] Make MC-055 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Adversarial escape suite covering privilege escalation, injection, replay, spoofing, sandbox escape, side channels, and resource exhaustion** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-055 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-055 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-055 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-055 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-055 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-055 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-055 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-055 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-055.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Adversarial escape suite covering privilege escalation, injection, replay, spoofing, sandbox escape, side channels, and resource exhaustion**.


# Resilience and failure handling

## MC-056 — Comprehensive failure-mode matrix for process, runtime, node, site, dependency, and control-plane failures

**Audit status:** Missing  
**Checklist linkage:** C051  
**Priority:** P1 / High  
**Objective:** Implement and prove **comprehensive failure-mode matrix for process, runtime, node, site, dependency, and control-plane failures** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-056 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Comprehensive failure-mode matrix for process, runtime, node, site, dependency, and control-plane failures** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Build an FMEA table with failure source, detection signal, safety impact, availability impact, automatic action, operator action, retryability, cleanup obligation, and test ID.
- [ ] Include correlated failures and failures that occur while handling another failure.
- [ ] Convert high-severity failure modes into fault-injection tests and release gates.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-056; define the error returned on limit breach.
- [ ] Make MC-056 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Comprehensive failure-mode matrix for process, runtime, node, site, dependency, and control-plane failures** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-056 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-056 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-056 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-056 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-056 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-056 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-056 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-056 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-056.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Comprehensive failure-mode matrix for process, runtime, node, site, dependency, and control-plane failures**.

## MC-057 — Health/readiness/stall detection with quantified thresholds

**Audit status:** Missing  
**Checklist linkage:** C052  
**Priority:** P1 / High  
**Objective:** Implement and prove **health/readiness/stall detection with quantified thresholds** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-057 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Health/readiness/stall detection with quantified thresholds** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Separate liveness, readiness, backend capability, dependency reachability, queue saturation, and cleanup backlog signals.
- [ ] Use stage deadlines/heartbeats to detect APPLYING/TERMINATING/CLEANUP stalls and expose age-of-oldest operation.
- [ ] Define exact thresholds and hysteresis to avoid alert flapping or premature restarts.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-057; define the error returned on limit breach.
- [ ] Make MC-057 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Health/readiness/stall detection with quantified thresholds** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-057 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-057 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-057 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-057 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-057 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-057 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-057 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-057 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-057.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Health/readiness/stall detection with quantified thresholds**.

## MC-058 — Bounded retry/backoff/jitter implementation for operations that are actually safe to retry

**Audit status:** Missing  
**Checklist linkage:** C053  
**Priority:** P1 / High  
**Objective:** Implement and prove **bounded retry/backoff/jitter implementation for operations that are actually safe to retry** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-058 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Bounded retry/backoff/jitter implementation for operations that are actually safe to retry** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Classify errors by retryability and prohibit retries for validation/authz/policy/security failures.
- [ ] Use bounded exponential backoff with full/decorrelated jitter, global attempt/time budgets, and cancellation propagation.
- [ ] Test duplicate requests, controller restart between attempts, thundering-herd recovery, and idempotency-key reuse.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-058; define the error returned on limit breach.
- [ ] Make MC-058 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Bounded retry/backoff/jitter implementation for operations that are actually safe to retry** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-058 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-058 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-058 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-058 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-058 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-058 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-058 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-058 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-058.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Bounded retry/backoff/jitter implementation for operations that are actually safe to retry**.

## MC-059 — Admission control/load shedding/circuit breaking around sandbox creation and backend saturation

**Audit status:** Missing  
**Checklist linkage:** C054  
**Priority:** P1 / High  
**Objective:** Implement and prove **admission control/load shedding/circuit breaking around sandbox creation and backend saturation** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-059 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Admission control/load shedding/circuit breaking around sandbox creation and backend saturation** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Gate admission on queue depth, cgroup/controller availability, memory pressure, PID availability, cleanup backlog, backend latency, and tenant quota.
- [ ] Reserve capacity for termination/cleanup/security operations so overload cannot prevent containment cleanup.
- [ ] Test gradual saturation and sudden bursts and verify predictable rejection without node destabilization.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-059; define the error returned on limit breach.
- [ ] Make MC-059 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Admission control/load shedding/circuit breaking around sandbox creation and backend saturation** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-059 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-059 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-059 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-059 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-059 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-059 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-059 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-059 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-059.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Admission control/load shedding/circuit breaking around sandbox creation and backend saturation**.

## MC-060 — Failover semantics preserving isolation/residency guarantees

**Audit status:** Missing  
**Checklist linkage:** C055  
**Priority:** P1 / High  
**Objective:** Implement and prove **failover semantics preserving isolation/residency guarantees** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-060 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Failover semantics preserving isolation/residency guarantees** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Define which sandbox lifecycle stages are movable/reconstructible and which require termination/recreation on another node.
- [ ] Carry policy digest, identity, residency constraints, and evidence continuity across failover without trusting stale controller ownership.
- [ ] Test failover during admission, verified-but-not-exec, execution, and cleanup.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-060; define the error returned on limit breach.
- [ ] Make MC-060 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Failover semantics preserving isolation/residency guarantees** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-060 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-060 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-060 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-060 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-060 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-060 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-060 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-060 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-060.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Failover semantics preserving isolation/residency guarantees**.

## MC-061 — Defined and tested degraded mode when noncritical dependencies are unavailable

**Audit status:** Missing  
**Checklist linkage:** C056  
**Priority:** P1 / High  
**Objective:** Implement and prove **defined and tested degraded mode when noncritical dependencies are unavailable** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-061 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Defined and tested degraded mode when noncritical dependencies are unavailable** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Specify which cached policies/credentials/evidence remain valid offline, their TTL/epoch rules, and which actions are prohibited without authoritative dependencies.
- [ ] Prevent stale-policy replay by binding cached authorization to version/epoch and enforce expiration using monotonic/trusted time where required.
- [ ] Test disconnect during create, after verification, during execution, and during cleanup, including reconnect reconciliation.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-061; define the error returned on limit breach.
- [ ] Make MC-061 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Defined and tested degraded mode when noncritical dependencies are unavailable** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-061 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-061 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-061 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-061 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-061 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-061 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-061 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-061 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-061.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Defined and tested degraded mode when noncritical dependencies are unavailable**.

## MC-062 — Crash-consistency/restart/resume semantics for launcher/backend/evidence state

**Audit status:** Missing  
**Checklist linkage:** C057  
**Priority:** P1 / High  
**Objective:** Implement and prove **crash-consistency/restart/resume semantics for launcher/backend/evidence state** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-062 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Crash-consistency/restart/resume semantics for launcher/backend/evidence state** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Persist the minimum journal needed to reconstruct ownership and cleanup state after crash without persisting sensitive transient data unnecessarily.
- [ ] On restart reconcile OS reality (processes/cgroups/namespaces/mounts) against journal state before accepting new work.
- [ ] Test power-loss/crash injection at every lifecycle boundary and prove no duplicate execution or orphaned privileged resource remains.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-062; define the error returned on limit breach.
- [ ] Make MC-062 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Crash-consistency/restart/resume semantics for launcher/backend/evidence state** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-062 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-062 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-062 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-062 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-062 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-062 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-062 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-062 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-062.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Crash-consistency/restart/resume semantics for launcher/backend/evidence state**.

## MC-063 — Duplicate ownership/stale-controller/duplicate-execution prevention

**Audit status:** Missing  
**Checklist linkage:** C058  
**Priority:** P1 / High  
**Objective:** Implement and prove **duplicate ownership/stale-controller/duplicate-execution prevention** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-063 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Duplicate ownership/stale-controller/duplicate-execution prevention** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Create a RACI covering design authority, code ownership, production operations, incident command, security approval, and emergency disable authority.
- [ ] Define escalation targets and acknowledgement/resolution objectives for Sev-1/Sev-2 security or availability incidents; test the contact path at least quarterly.
- [ ] Add repository ownership metadata and a machine-readable owner field to release evidence so orphaned components are detectable automatically.
- [ ] Use leases/epochs/fencing tokens for ownership and require the current fence on every state mutation.
- [ ] Prevent a stale controller from launch/terminate/cleanup after leadership changes.
- [ ] Test network partitions, delayed messages, duplicated requests, lease expiry, and clock skew.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-063; define the error returned on limit breach.
- [ ] Make MC-063 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Duplicate ownership/stale-controller/duplicate-execution prevention** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-063 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-063 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-063 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-063 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-063 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-063 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-063 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-063 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-063.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Duplicate ownership/stale-controller/duplicate-execution prevention**.

## MC-064 — Quarantine/freeze/disable/kill control with authorization and audit

**Audit status:** Missing  
**Checklist linkage:** C059  
**Priority:** P1 / High  
**Objective:** Implement and prove **quarantine/freeze/disable/kill control with authorization and audit** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-064 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Quarantine/freeze/disable/kill control with authorization and audit** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Define scoped controls at sandbox, workload, tenant, node, backend, and fleet levels with least-privilege authorization.
- [ ] Implement freeze where supported, graceful terminate, forced kill, admission disable, and evidence preservation semantics.
- [ ] Require break-glass reason, audit event, operator identity, expiry/re-enable path, and post-action verification.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-064; define the error returned on limit breach.
- [ ] Make MC-064 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Quarantine/freeze/disable/kill control with authorization and audit** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-064 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-064 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-064 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-064 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-064 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-064 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-064 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-064 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-064.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Quarantine/freeze/disable/kill control with authorization and audit**.

## MC-065 — Automated fault-injection suite proving recovery objectives

**Audit status:** Missing  
**Checklist linkage:** C060  
**Priority:** P1 / High  
**Objective:** Implement and prove **automated fault-injection suite proving recovery objectives** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-065 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Automated fault-injection suite proving recovery objectives** across each supported OS/backend/deployment mode.
- [ ] Enumerate failure modes before coding: launcher crash, child crash, backend timeout, node reboot, dependency loss, stale controller, partial cleanup, partition, disk pressure, and overload.
- [ ] Classify operations by retry safety and idempotency; assign bounded retry budgets with exponential backoff/jitter only where duplicate execution cannot violate isolation or ownership.
- [ ] Define deterministic terminal states and cleanup obligations for every failure transition, including failures during rollback and recovery.
- [ ] Instrument health, readiness, queue depth, saturation, stalled operations, leaked resources, recovery attempts, and last-success timestamps with quantified thresholds.

### B. Component-specific implementation

- [ ] Build deterministic injectors for process crash, syscall/backend error, latency, dependency outage, disk full, OOM pressure, network partition, and corrupted/stale evidence.
- [ ] Assert RTO/RPO-style recovery objectives plus invariants for isolation, ownership, cleanup, and audit continuity.
- [ ] Run a defined subset in CI and a broader chaos suite in preproduction certification.
- [ ] Define incident classes for sandbox escape/suspected escape, policy bypass, evidence forgery, widespread launch failure, cleanup leak, and control-plane compromise.
- [ ] Specify paging targets, severity criteria, containment actions, evidence preservation, forensic acquisition, communication, recovery, and post-incident review.
- [ ] Run tabletop and live game-day exercises including emergency disable and credential/key rotation.
- [ ] Exercise recovery under fault injection and require the system to preserve isolation, single ownership, audit continuity, and resource bounds throughout the fault.
- [ ] Document operator intervention paths for quarantine, force cleanup, disable, and recovery, with authorization and immutable audit records.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-065; define the error returned on limit breach.
- [ ] Make MC-065 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Automated fault-injection suite proving recovery objectives** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-065 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-065 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-065 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-065 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-065 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-065 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-065 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-065 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-065.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Automated fault-injection suite proving recovery objectives**.


# Performance and resource efficiency

## MC-066 — Reproducible startup, CPU, memory, storage, network, and density benchmark harness

**Audit status:** Missing  
**Checklist linkage:** C061, C063-C064  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **reproducible startup, CPU, memory, storage, network, and density benchmark harness** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-066 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Reproducible startup, CPU, memory, storage, network, and density benchmark harness** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Implement machine-readable benchmark scenarios and emit raw samples plus summary statistics; avoid relying only on wall-clock shell timing.
- [ ] Pin workload binaries/profile fixtures and warm-up strategy, and record CPU governor/NUMA/cgroup/background-load context.
- [ ] Include baseline unsandboxed execution to quantify incremental sandbox overhead.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-066; define the error returned on limit breach.
- [ ] Make MC-066 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Reproducible startup, CPU, memory, storage, network, and density benchmark harness** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-066 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-066 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-066 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-066 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-066 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-066 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-066 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-066 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-066.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Reproducible startup, CPU, memory, storage, network, and density benchmark harness**.

## MC-067 — p50/p95/p99/worst-case release thresholds

**Audit status:** Missing  
**Checklist linkage:** C062  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **p50/p95/p99/worst-case release thresholds** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-067 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **p50/p95/p99/worst-case release thresholds** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Choose sample counts and statistical treatment sufficient for stable tail estimates and store baseline distributions by platform class.
- [ ] Define regression thresholds separately for median, p95, p99, max/timeouts, and resource usage.
- [ ] Block release when confidence-adjusted regression exceeds the allowed budget unless an approved waiver exists.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-067; define the error returned on limit breach.
- [ ] Make MC-067 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **p50/p95/p99/worst-case release thresholds** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-067 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-067 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-067 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-067 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-067 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-067 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-067 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-067 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-067.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **p50/p95/p99/worst-case release thresholds**.

## MC-068 — Steady/burst/overload/scale/recovery performance scenarios

**Audit status:** Missing  
**Checklist linkage:** C063  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **steady/burst/overload/scale/recovery performance scenarios** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-068 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Steady/burst/overload/scale/recovery performance scenarios** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Generate closed-loop and open-loop load at steady, burst, overload, and recovery phases and record admission/drop behavior.
- [ ] Vary profile complexity, bind count, syscall rule count, process count, and concurrent sandbox density.
- [ ] Verify the system recovers after overload without persistent queue, leaked resources, or elevated latency.
- [ ] Define incident classes for sandbox escape/suspected escape, policy bypass, evidence forgery, widespread launch failure, cleanup leak, and control-plane compromise.
- [ ] Specify paging targets, severity criteria, containment actions, evidence preservation, forensic acquisition, communication, recovery, and post-incident review.
- [ ] Run tabletop and live game-day exercises including emergency disable and credential/key rotation.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-068; define the error returned on limit breach.
- [ ] Make MC-068 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Steady/burst/overload/scale/recovery performance scenarios** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-068 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-068 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-068 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-068 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-068 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-068 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-068 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-068 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-068.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Steady/burst/overload/scale/recovery performance scenarios**.

## MC-069 — Per-workload/per-tenant overhead accounting

**Audit status:** Missing  
**Checklist linkage:** C064  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **per-workload/per-tenant overhead accounting** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-069 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Per-workload/per-tenant overhead accounting** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Attribute CPU, memory, I/O, storage, network, process, and control-plane overhead to sandbox/workload/tenant IDs.
- [ ] Reconcile usage with cgroup/kernel counters and define treatment of shared launcher/backend overhead.
- [ ] Test accounting accuracy under short-lived workloads and high concurrency.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-069; define the error returned on limit breach.
- [ ] Make MC-069 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Per-workload/per-tenant overhead accounting** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-069 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-069 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-069 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-069 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-069 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-069 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-069 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-069 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-069.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Per-workload/per-tenant overhead accounting**.

## MC-070 — Profiling evidence for serialization/copy/context-switch/hop inefficiencies

**Audit status:** Missing  
**Checklist linkage:** C065  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **profiling evidence for serialization/copy/context-switch/hop inefficiencies** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-070 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Profiling evidence for serialization/copy/context-switch/hop inefficiencies** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Capture CPU profiles, syscall profiles, allocation profiles, context switches, page faults, and I/O traces on representative workloads.
- [ ] Tag time spent in parse/validate, backend setup, mount/cgroup operations, evidence generation, and launch handoff.
- [ ] Retain before/after profiles for accepted optimizations and guard against trading away isolation for speed.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-070; define the error returned on limit breach.
- [ ] Make MC-070 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Profiling evidence for serialization/copy/context-switch/hop inefficiencies** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-070 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-070 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-070 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-070 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-070 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-070 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-070 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-070 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-070.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Profiling evidence for serialization/copy/context-switch/hop inefficiencies**.

## MC-071 — Verified optimization implementation/evidence for locality, batching, zero-copy, or equivalent where applicable

**Audit status:** Missing  
**Checklist linkage:** C066  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **verified optimization implementation/evidence for locality, batching, zero-copy, or equivalent where applicable** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-071 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Verified optimization implementation/evidence for locality, batching, zero-copy, or equivalent where applicable** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Select optimizations only after measurement and document security invariants that must remain unchanged.
- [ ] Use batching/cache/locality/zero-copy only where object lifetime and tenant isolation are explicit and testable.
- [ ] Add correctness, memory-safety/resource-lifetime, and performance regression tests for each optimization.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-071; define the error returned on limit breach.
- [ ] Make MC-071 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Verified optimization implementation/evidence for locality, batching, zero-copy, or equivalent where applicable** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-071 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-071 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-071 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-071 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-071 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-071 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-071 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-071 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-071.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Verified optimization implementation/evidence for locality, batching, zero-copy, or equivalent where applicable**.

## MC-072 — Capacity model and saturation signals predicting resource exhaustion

**Audit status:** Missing  
**Checklist linkage:** C067, C069  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **capacity model and saturation signals predicting resource exhaustion** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-072 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Capacity model and saturation signals predicting resource exhaustion** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Model node capacity from memory headroom, PID budget, cgroup/controller limits, mount namespace cost, FD limits, CPU, I/O, and cleanup reserve.
- [ ] Expose leading saturation indicators and predict safe admission headroom rather than waiting for OOM/ENOSPC/EMFILE.
- [ ] Validate predictions against load tests on every hardware class.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-072; define the error returned on limit breach.
- [ ] Make MC-072 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Capacity model and saturation signals predicting resource exhaustion** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-072 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-072 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-072 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-072 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-072 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-072 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-072 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-072 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-072.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Capacity model and saturation signals predicting resource exhaustion**.

## MC-073 — Power/thermal measurements for constrained edge nodes

**Audit status:** Missing  
**Checklist linkage:** C068  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **power/thermal measurements for constrained edge nodes** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-073 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Power/thermal measurements for constrained edge nodes** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Measure package/system power, thermal throttling, frequency, and energy per sandbox/work unit using platform-appropriate counters.
- [ ] Run sustained density scenarios on constrained edge hardware and correlate thermal state with latency/failure rate.
- [ ] Define thermal admission/degradation thresholds if the product targets thermally constrained nodes.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-073; define the error returned on limit breach.
- [ ] Make MC-073 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Power/thermal measurements for constrained edge nodes** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-073 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-073 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-073 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-073 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-073 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-073 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-073 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-073 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-073.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Power/thermal measurements for constrained edge nodes**.

## MC-074 — Automated release gate that blocks startup/density/throughput/tail-latency regressions

**Audit status:** Missing  
**Checklist linkage:** C070  
**Priority:** P2 / Required production readiness  
**Objective:** Implement and prove **automated release gate that blocks startup/density/throughput/tail-latency regressions** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-074 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Automated release gate that blocks startup/density/throughput/tail-latency regressions** across each supported OS/backend/deployment mode.
- [ ] Create a reproducible benchmark harness that records hardware, kernel, runtime, backend versions, configuration digest, workload shape, warm/cold state, and run variance.
- [ ] Measure p50/p95/p99/max latency plus CPU, RSS, page faults, context switches, I/O, network, temporary storage, and density impact where applicable.
- [ ] Separate fixed sandbox startup cost from workload-dependent cost and attribute overhead per tenant/workload/backend stage.
- [ ] Test steady-state, burst, overload, saturation, recovery, and scale-out/scale-in behavior; capture the knee where latency or failure rate becomes nonlinear.

### B. Component-specific implementation

- [ ] Create or join an explicit network namespace before exec and define loopback/interface/DNS/routing policy from the profile.
- [ ] Close inherited network sockets and other communication FDs unless explicitly allow-listed; verify no host-network socket survives setup.
- [ ] Enforce egress/ingress restrictions using namespace routing/firewall/eBPF or an approved broker and bind rules to workload identity.
- [ ] Test raw sockets, localhost-to-host confusion, IPv6, abstract Unix sockets, DNS bypass, inherited sockets, and reconnect behavior.
- [ ] Store approved baselines keyed by platform/workload and compare candidate distributions using deterministic thresholds/statistical tests.
- [ ] Fail CI/release on startup, density, throughput, tail-latency, CPU, or memory regressions beyond budget.
- [ ] Require signed waiver metadata with owner and expiry for temporary performance exceptions.
- [ ] Profile before optimizing and preserve evidence tying each optimization to a measured bottleneck and a regression test.
- [ ] Encode release thresholds as automated gates with statistically defensible baselines and explicit variance/tolerance policy.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-074; define the error returned on limit breach.
- [ ] Make MC-074 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Automated release gate that blocks startup/density/throughput/tail-latency regressions** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-074 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-074 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-074 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-074 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-074 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-074 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-074 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-074 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-074.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Automated release gate that blocks startup/density/throughput/tail-latency regressions**.


# Observability and explainability

## MC-075 — Runtime status surface exposing health, readiness, version, active config digest, dependency status, and actual active controls

**Audit status:** Missing  
**Checklist linkage:** C071  
**Priority:** P1 / High  
**Objective:** Implement and prove **runtime status surface exposing health, readiness, version, active config digest, dependency status, and actual active controls** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-075 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Runtime status surface exposing health, readiness, version, active config digest, dependency status, and actual active controls** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Expose liveness/readiness, build version, backend/version, supported features, active config/profile digest, last successful verification, dependency state, and cleanup backlog.
- [ ] Report requested controls and verified applied controls in separate fields with evidence-strength markers.
- [ ] Make status read-only, authenticated/authorized as appropriate, bounded in size, and safe under partial dependency failure.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-075; define the error returned on limit breach.
- [ ] Make MC-075 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Runtime status surface exposing health, readiness, version, active config digest, dependency status, and actual active controls** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-075 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-075 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-075 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-075 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-075 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-075 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-075 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-075 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-075.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Runtime status surface exposing health, readiness, version, active config digest, dependency status, and actual active controls**.

## MC-076 — Structured metrics implementation for rate/errors/latency/saturation/backlog/resource use

**Audit status:** Missing  
**Checklist linkage:** C072  
**Priority:** P1 / High  
**Objective:** Implement and prove **structured metrics implementation for rate/errors/latency/saturation/backlog/resource use** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-076 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Structured metrics implementation for rate/errors/latency/saturation/backlog/resource use** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Define counters/histograms/gauges for admission, rejection by reason, setup stage latency, verification failures, active sandboxes, queues, cleanup, leaks, resource usage, and backend errors.
- [ ] Use bounded labels; never label metrics with raw untrusted path/profile contents or unbounded workload identifiers.
- [ ] Document units, monotonicity, reset semantics, aggregation, and alerting thresholds.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-076; define the error returned on limit breach.
- [ ] Make MC-076 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Structured metrics implementation for rate/errors/latency/saturation/backlog/resource use** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-076 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-076 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-076 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-076 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-076 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-076 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-076 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-076 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-076.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Structured metrics implementation for rate/errors/latency/saturation/backlog/resource use**.

## MC-077 — Structured logging implementation with stable node/tenant/workload/component/operation identifiers

**Audit status:** Missing  
**Checklist linkage:** C073  
**Priority:** P1 / High  
**Objective:** Implement and prove **structured logging implementation with stable node/tenant/workload/component/operation identifiers** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-077 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Structured logging implementation with stable node/tenant/workload/component/operation identifiers** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Emit JSON or equivalent schema-stable events with timestamp, severity, event code, component, operation ID, sandbox/workload/tenant IDs, profile digest, backend, result, and reason.
- [ ] Sanitize CR/LF/control characters and size-limit attacker-controlled fields to prevent log injection and storage DoS.
- [ ] Define which security/audit events are mandatory and non-sampled.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-077; define the error returned on limit breach.
- [ ] Make MC-077 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Structured logging implementation with stable node/tenant/workload/component/operation identifiers** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-077 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-077 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-077 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-077 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-077 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-077 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-077 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-077 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-077.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Structured logging implementation with stable node/tenant/workload/component/operation identifiers**.

## MC-078 — Trace-context propagation across control-plane/backend/launcher boundaries

**Audit status:** Missing  
**Checklist linkage:** C074  
**Priority:** P1 / High  
**Objective:** Implement and prove **trace-context propagation across control-plane/backend/launcher boundaries** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-078 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Trace-context propagation across control-plane/backend/launcher boundaries** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Propagate W3C Trace Context or approved equivalent through control-plane, backend, launcher, and evidence paths while preserving trust-boundary validation.
- [ ] Create spans for validation, admission, backend setup stages, verification, exec handoff, termination, and cleanup.
- [ ] Do not blindly trust workload-provided trace IDs; re-root or sanitize at the trust boundary.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-078; define the error returned on limit breach.
- [ ] Make MC-078 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Trace-context propagation across control-plane/backend/launcher boundaries** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-078 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-078 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-078 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-078 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-078 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-078 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-078 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-078 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-078.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Trace-context propagation across control-plane/backend/launcher boundaries**.

## MC-079 — High-cardinality diagnostic channel with redaction/privacy controls

**Audit status:** Missing  
**Checklist linkage:** C075  
**Priority:** P1 / High  
**Objective:** Implement and prove **high-cardinality diagnostic channel with redaction/privacy controls** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-079 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **High-cardinality diagnostic channel with redaction/privacy controls** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Provide a separately controlled debug channel with bounded retention/quotas and explicit enablement rather than polluting production metrics.
- [ ] Apply field-level redaction and access controls and log who enabled diagnostics for which tenant/workload and for how long.
- [ ] Stress-test cardinality and volume limits with attacker-controlled identifiers.
- [ ] Classify telemetry by operational/security/privacy need and set retention, sampling, aggregation, regional residency, and deletion rules.
- [ ] Guarantee audit/security events bypass ordinary sampling while bounding debug data volume.
- [ ] Authorize/export telemetry using least privilege and test redaction at every exporter boundary.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-079; define the error returned on limit breach.
- [ ] Make MC-079 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **High-cardinality diagnostic channel with redaction/privacy controls** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-079 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-079 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-079 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-079 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-079 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-079 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-079 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-079 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-079.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **High-cardinality diagnostic channel with redaction/privacy controls**.

## MC-080 — Persistent reason record for every automated admission/rejection/rollback/termination decision

**Audit status:** Missing  
**Checklist linkage:** C076  
**Priority:** P1 / High  
**Objective:** Implement and prove **persistent reason record for every automated admission/rejection/rollback/termination decision** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-080 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Persistent reason record for every automated admission/rejection/rollback/termination decision** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Define immutable decision records with policy/version, input digest, evaluated constraints, selected backend, reason code, evidence references, actor, and timestamp.
- [ ] Persist records for admissions, rejections, degraded-mode decisions, rollbacks, quarantine, kill, and cleanup failures.
- [ ] Test deterministic reproduction of the decision from retained non-secret inputs where feasible.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-080; define the error returned on limit breach.
- [ ] Make MC-080 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Persistent reason record for every automated admission/rejection/rollback/termination decision** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-080 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-080 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-080 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-080 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-080 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-080 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-080 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-080 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-080.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Persistent reason record for every automated admission/rejection/rollback/termination decision**.

## MC-081 — Operator explain view tying decisions to profile, policy, topology, constraints, and evidence

**Audit status:** Missing  
**Checklist linkage:** C077  
**Priority:** P1 / High  
**Objective:** Implement and prove **operator explain view tying decisions to profile, policy, topology, constraints, and evidence** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-081 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Operator explain view tying decisions to profile, policy, topology, constraints, and evidence** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Render the decision path from tenant/workload request through resolved profile, policy constraints, platform capabilities, applied controls, and verification evidence.
- [ ] Clearly label unknown/unverified facts and never infer “enforced” from requested configuration.
- [ ] Provide safe drill-down links to evidence, logs, traces, release lineage, and runbooks with authorization checks.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-081; define the error returned on limit breach.
- [ ] Make MC-081 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Operator explain view tying decisions to profile, policy, topology, constraints, and evidence** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-081 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-081 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-081 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-081 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-081 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-081 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-081 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-081 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-081.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Operator explain view tying decisions to profile, policy, topology, constraints, and evidence**.

## MC-082 — Correlation with release lineage and live infrastructure graph

**Audit status:** Missing  
**Checklist linkage:** C078  
**Priority:** P1 / High  
**Objective:** Implement and prove **correlation with release lineage and live infrastructure graph** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-082 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Correlation with release lineage and live infrastructure graph** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Attach source revision, build/provenance digest, deployment/canary wave, node image, backend/runtime versions, and configuration lineage to runtime telemetry.
- [ ] Integrate node/workload/backend relationships with the live infrastructure graph using stable IDs and lifecycle updates.
- [ ] Test correlation after redeploy, node replacement, rollback, and failover.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-082; define the error returned on limit breach.
- [ ] Make MC-082 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Correlation with release lineage and live infrastructure graph** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-082 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-082 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-082 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-082 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-082 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-082 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-082 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-082 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-082.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Correlation with release lineage and live infrastructure graph**.

## MC-083 — Telemetry retention, sampling, privacy, and export policy

**Audit status:** Missing  
**Checklist linkage:** C079  
**Priority:** P1 / High  
**Objective:** Implement and prove **telemetry retention, sampling, privacy, and export policy** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-083 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Telemetry retention, sampling, privacy, and export policy** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Classify telemetry by operational/security/privacy need and set retention, sampling, aggregation, regional residency, and deletion rules.
- [ ] Guarantee audit/security events bypass ordinary sampling while bounding debug data volume.
- [ ] Authorize/export telemetry using least privilege and test redaction at every exporter boundary.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-083; define the error returned on limit breach.
- [ ] Make MC-083 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Telemetry retention, sampling, privacy, and export policy** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-083 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-083 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-083 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-083 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-083 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-083 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-083 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-083 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-083.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Telemetry retention, sampling, privacy, and export policy**.

## MC-084 — Dashboards and alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defect

**Audit status:** Missing  
**Checklist linkage:** C080  
**Priority:** P1 / High  
**Objective:** Implement and prove **dashboards and alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defect** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-084 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Dashboards and alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defect** across each supported OS/backend/deployment mode.
- [ ] Define a stable telemetry schema with component, node, tenant, workload, sandbox, operation, profile digest, backend, version, and correlation identifiers.
- [ ] Prevent secret/profile leakage through logs, labels, traces, or high-cardinality diagnostics; add automated redaction tests using seeded canary secrets.
- [ ] Expose requested policy separately from applied/verified controls so operators cannot confuse intent with enforcement evidence.
- [ ] Make every automated rejection, rollback, quarantine, kill, or degraded-mode transition emit a durable reason code and human-readable explanation.

### B. Component-specific implementation

- [ ] Create separate views/alerts for demand load, resource saturation, backend degradation, policy rejection, dependency outage, suspected attack, cleanup leak, and software defect.
- [ ] Tune alerts to actionable SLO/security thresholds with deduplication, inhibition, escalation, and runbook links.
- [ ] Validate alerts through synthetic failures and fault-injection exercises rather than dashboard inspection alone.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Bound telemetry cardinality and retention; sampling must never discard mandatory security/audit events.
- [ ] Create dashboards/alerts around symptoms and causes, and document runbook links directly in actionable alerts.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-084; define the error returned on limit breach.
- [ ] Make MC-084 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Dashboards and alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defect** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-084 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-084 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-084 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-084 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-084 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-084 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-084 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-084 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-084.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Dashboards and alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defect**.


# Testing and certification

## MC-085 — Public-schema contract tests validating positive and negative fixtures

**Audit status:** Partial: schemas exist; no full contract suite  
**Checklist linkage:** C082  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **public-schema contract tests validating positive and negative fixtures** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-085 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Public-schema contract tests validating positive and negative fixtures** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Create canonical minimal, typical, maximal-boundary, deprecated-version, unknown-field, malformed, and hostile fixtures for every public schema.
- [ ] Hash fixtures and run them against schema validators plus implementation parsers to detect schema/runtime drift.
- [ ] Include expected normalized form and expected stable error code for every negative fixture.
- [ ] Generate validators from or directly execute both public JSON Schemas and test canonical positive/negative fixture corpora.
- [ ] Check unknown fields, min/max sizes, enums, numeric/string boundaries, Unicode, duplicate-key parser behavior, and schema-version negotiation.
- [ ] Run contract tests against the packaged artifact and publish fixture/result digests.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-085; define the error returned on limit breach.
- [ ] Make MC-085 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Public-schema contract tests validating positive and negative fixtures** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-085 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-085 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-085 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-085 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-085 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-085 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-085 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-085 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-085.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Public-schema contract tests validating positive and negative fixtures**.

## MC-086 — Real backend integration tests with adjacent layers and actual OS enforcement

**Audit status:** Missing  
**Checklist linkage:** C083  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **real backend integration tests with adjacent layers and actual OS enforcement** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-086 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Real backend integration tests with adjacent layers and actual OS enforcement** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Run privileged/hermetic tests on real Linux/macOS hosts and verify OS state plus behavioral denies from inside the sandbox.
- [ ] Include setup and teardown assertions for namespaces, mounts, capabilities, seccomp/Landlock/Seatbelt, cgroups/rlimits, FDs, environment, and descendant cleanup.
- [ ] Gate releases on these tests for every platform claimed as production-supported.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-086; define the error returned on limit breach.
- [ ] Make MC-086 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Real backend integration tests with adjacent layers and actual OS enforcement** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-086 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-086 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-086 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-086 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-086 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-086 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-086 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-086 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-086.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Real backend integration tests with adjacent layers and actual OS enforcement**.

## MC-087 — Compatibility matrix test suite across supported CPU architectures, kernels, Python/runtime versions, bubblewrap/Seatbelt versions, and schema versions

**Audit status:** Missing  
**Checklist linkage:** C084  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **compatibility matrix test suite across supported CPU architectures, kernels, Python/runtime versions, bubblewrap/Seatbelt versions, and schema versions** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-087 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Compatibility matrix test suite across supported CPU architectures, kernels, Python/runtime versions, bubblewrap/Seatbelt versions, and schema versions** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Invoke `bwrap` without a shell using a prevalidated argv vector; pin/verify executable path and version and reject environment/PATH substitution.
- [ ] Construct namespaces, binds, tmpfs, proc/dev exposure, uid/gid, capabilities, network, and working directory from the canonical profile using a deterministic argument builder.
- [ ] Capture child PID/exit status and differentiate bwrap setup failure from workload failure; scrub inherited FDs/environment before launch.
- [ ] Run integration tests against real bwrap on supported distributions and assert mount/network/process views from inside the sandbox.
- [ ] Define a deterministic mapping from canonical profile controls to Seatbelt profile syntax and document controls with no macOS-equivalent semantics.
- [ ] Compile/validate profiles before launch and invoke the supported sandbox mechanism without shell interpolation or untrusted textual substitution.
- [ ] Version-gate against macOS releases and maintain regression tests because Seatbelt behavior is private/OS-sensitive.
- [ ] Verify representative file/network/process denials from inside the launched process and fail closed for unrepresentable mandatory controls.
- [ ] Generate CI jobs from the authoritative compatibility matrix rather than manually maintaining divergent job lists.
- [ ] Test architecture/kernel/runtime/backend/schema combinations including minimum supported, current, and upgrade/mixed-version paths.
- [ ] Record unsupported skips separately from test failures and prevent accidental expansion of the support claim.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-087; define the error returned on limit breach.
- [ ] Make MC-087 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Compatibility matrix test suite across supported CPU architectures, kernels, Python/runtime versions, bubblewrap/Seatbelt versions, and schema versions** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-087 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-087 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-087 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-087 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-087 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-087 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-087 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-087 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-087.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Compatibility matrix test suite across supported CPU architectures, kernels, Python/runtime versions, bubblewrap/Seatbelt versions, and schema versions**.

## MC-088 — Fuzz testing for profile parsing, schema boundaries, backend arguments, and untrusted identifiers

**Audit status:** Missing  
**Checklist linkage:** C085  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **fuzz testing for profile parsing, schema boundaries, backend arguments, and untrusted identifiers** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-088 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Fuzz testing for profile parsing, schema boundaries, backend arguments, and untrusted identifiers** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Use coverage-guided fuzzers against profile decoding, canonicalization, schema/semantic validation, path handling, backend argv/profile generation, and evidence parsing.
- [ ] Seed corpora with real valid profiles and adversarial Unicode, deep nesting, huge counts, duplicate keys, path traversal, and boundary numeric values.
- [ ] Run with sanitizers/native hardening where applicable, retain minimizing crash inputs, and convert every bug into a regression test.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-088; define the error returned on limit breach.
- [ ] Make MC-088 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Fuzz testing for profile parsing, schema boundaries, backend arguments, and untrusted identifiers** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-088 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-088 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-088 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-088 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-088 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-088 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-088 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-088 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-088.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Fuzz testing for profile parsing, schema boundaries, backend arguments, and untrusted identifiers**.

## MC-089 — Concurrency/race tests for simultaneous create/update/terminate operations and evidence handling

**Audit status:** Missing  
**Checklist linkage:** C086  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **concurrency/race tests for simultaneous create/update/terminate operations and evidence handling** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-089 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Concurrency/race tests for simultaneous create/update/terminate operations and evidence handling** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Stress simultaneous create/update/start/terminate/cleanup for the same and different sandbox IDs using barriers to force adverse interleavings.
- [ ] Race configuration activation, ownership changes, evidence writes, backend timeout, and cleanup against controller restart.
- [ ] Use thread/process sanitizers or race detectors where available and assert single execution, single ownership, and idempotent cleanup invariants.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-089; define the error returned on limit breach.
- [ ] Make MC-089 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Concurrency/race tests for simultaneous create/update/terminate operations and evidence handling** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-089 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-089 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-089 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-089 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-089 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-089 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-089 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-089 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-089.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Concurrency/race tests for simultaneous create/update/terminate operations and evidence handling**.

## MC-090 — Security test suite mechanically derived from the threat model

**Audit status:** Missing  
**Checklist linkage:** C087  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **security test suite mechanically derived from the threat model** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-090 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Security test suite mechanically derived from the threat model** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Use STRIDE/attack-tree style analysis for malicious workload, malicious tenant, compromised control plane, compromised node agent, insider, and supply-chain adversaries.
- [ ] Cover kernel escape, namespace confusion, mount/path races, FD leaks, capability regain, syscall gaps, evidence forgery, policy downgrade, side channels, and denial of service.
- [ ] Assign each threat likelihood/impact, mitigation owner, verification test, and residual-risk disposition.
- [ ] Assign stable threat IDs and generate/validate a mapping requiring at least one mitigation and one executable test per accepted threat.
- [ ] Fail certification when threat coverage regresses or tests are skipped on a claimed supported target.
- [ ] Include abuse cases for malformed inputs, privilege boundary crossing, evidence forgery, downgrade, replay, resource exhaustion, and cleanup escape.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-090; define the error returned on limit breach.
- [ ] Make MC-090 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Security test suite mechanically derived from the threat model** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-090 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-090 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-090 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-090 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-090 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-090 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-090 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-090 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-090.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Security test suite mechanically derived from the threat model**.

## MC-091 — Benchmark, soak, burst, and fleet-scale certification tests

**Audit status:** Missing  
**Checklist linkage:** C088  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **benchmark, soak, burst, and fleet-scale certification tests** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-091 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Benchmark, soak, burst, and fleet-scale certification tests** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Run long-duration soak tests to detect leaks/zombies/cgroup buildup/mount leaks/FD growth and compare start/end resource baselines.
- [ ] Exercise burst and fleet-scale launch/terminate waves with realistic tenant distribution and backend limits.
- [ ] Publish capacity/performance certification results and block release when thresholds or cleanup invariants fail.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-091; define the error returned on limit breach.
- [ ] Make MC-091 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Benchmark, soak, burst, and fleet-scale certification tests** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-091 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-091 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-091 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-091 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-091 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-091 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-091 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-091 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-091.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Benchmark, soak, burst, and fleet-scale certification tests**.

## MC-092 — Disaster/partition/reconnect/degraded-control-plane tests

**Audit status:** Missing  
**Checklist linkage:** C089  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **disaster/partition/reconnect/degraded-control-plane tests** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-092 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Disaster/partition/reconnect/degraded-control-plane tests** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Specify which cached policies/credentials/evidence remain valid offline, their TTL/epoch rules, and which actions are prohibited without authoritative dependencies.
- [ ] Prevent stale-policy replay by binding cached authorization to version/epoch and enforce expiration using monotonic/trusted time where required.
- [ ] Test disconnect during create, after verification, during execution, and during cleanup, including reconnect reconciliation.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-092; define the error returned on limit breach.
- [ ] Make MC-092 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Disaster/partition/reconnect/degraded-control-plane tests** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-092 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-092 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-092 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-092 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-092 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-092 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-092 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-092 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-092.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Disaster/partition/reconnect/degraded-control-plane tests**.

## MC-093 — Machine-readable signed acceptance evidence required before release certification

**Audit status:** Missing  
**Checklist linkage:** C090  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **machine-readable signed acceptance evidence required before release certification** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-093 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Machine-readable signed acceptance evidence required before release certification** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Define an acceptance-evidence schema containing release artifact digest, source revision, test manifest/results digests, environment matrix, approvers, exceptions, and timestamp/epoch.
- [ ] Sign evidence with protected release credentials and verify it before promotion.
- [ ] Make evidence immutable and independently retrievable for audit/reconstruction.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-093; define the error returned on limit breach.
- [ ] Make MC-093 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Machine-readable signed acceptance evidence required before release certification** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-093 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-093 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-093 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-093 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-093 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-093 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-093 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-093 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-093.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Machine-readable signed acceptance evidence required before release certification**.

## MC-094 — Full 100-check `pk_core` conformance evidence from this archive; current integration tests skip because `pk_core` is absent

**Audit status:** Missing in archive  
**Checklist linkage:** C090, C100  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **full 100-check `pk_core` conformance evidence from this archive; current integration tests skip because `pk_core` is absent** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-094 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Full 100-check `pk_core` conformance evidence from this archive; current integration tests skip because `pk_core` is absent** across each supported OS/backend/deployment mode.
- [ ] Define a test manifest with stable test IDs, environment prerequisites, exact assertions, expected evidence, ownership, and release-blocking severity.
- [ ] Run both positive and negative paths and prove fail-closed behavior; test skipped prerequisites as explicit certification failures unless the release target excludes that platform.
- [ ] Capture machine-readable results including source revision, artifact digest, environment fingerprint, start/end time, pass/fail/skip reason, and test-tool versions.
- [ ] Exercise hostile/malformed inputs, concurrency, process crashes, cancellation, timeouts, and cleanup; verify no leaked privileges/resources or stale evidence remains.

### B. Component-specific implementation

- [ ] Vendor, declare, or reliably resolve the approved `pk_core` dependency in certification environments and pin the compatible contract/version.
- [ ] Change release certification so missing `pk_core` causes a failed prerequisite for the conformance job, not a green build with skipped tests.
- [ ] Execute and archive all 100-check conformance outputs against the exact release artifact.
- [ ] Run certification against the built release artifact, not only the source tree, and verify the artifact digest before and after the suite.
- [ ] Require signed acceptance evidence and make the release gate consume that evidence rather than relying on manual declarations.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-094; define the error returned on limit breach.
- [ ] Make MC-094 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Full 100-check `pk_core` conformance evidence from this archive; current integration tests skip because `pk_core` is absent** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-094 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-094 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-094 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-094 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-094 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-094 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-094 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-094 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-094.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Full 100-check `pk_core` conformance evidence from this archive; current integration tests skip because `pk_core` is absent**.


# Operations and release governance

## MC-095 — Executable canary/staged rollout workflow with tested rollback and emergency disable

**Audit status:** Missing  
**Checklist linkage:** C092  
**Priority:** P1 / High  
**Objective:** Implement and prove **executable canary/staged rollout workflow with tested rollback and emergency disable** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-095 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Executable canary/staged rollout workflow with tested rollback and emergency disable** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Define scoped controls at sandbox, workload, tenant, node, backend, and fleet levels with least-privilege authorization.
- [ ] Implement freeze where supported, graceful terminate, forced kill, admission disable, and evidence preservation semantics.
- [ ] Require break-glass reason, audit event, operator identity, expiry/re-enable path, and post-action verification.
- [ ] Define promotion waves, eligibility criteria, health/security metrics, automatic abort thresholds, and minimum observation windows.
- [ ] Exercise rollback of code, backend, and configuration and verify running/new sandboxes follow the documented semantics.
- [ ] Implement fleet/node/backend admission-disable and emergency kill/quarantine controls with strong authorization and audit.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-095; define the error returned on limit breach.
- [ ] Make MC-095 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Executable canary/staged rollout workflow with tested rollback and emergency disable** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-095 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-095 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-095 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-095 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-095 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-095 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-095 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-095 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-095.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Executable canary/staged rollout workflow with tested rollback and emergency disable**.

## MC-096 — Supported-version compatibility matrix for backend/kernel/runtime/adjacent dependencies

**Audit status:** Missing  
**Checklist linkage:** C093  
**Priority:** P1 / High  
**Objective:** Implement and prove **supported-version compatibility matrix for backend/kernel/runtime/adjacent dependencies** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-096 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Supported-version compatibility matrix for backend/kernel/runtime/adjacent dependencies** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Record supported CPU architecture, OS release, kernel build/config, libc, Python/runtime, bubblewrap/Seatbelt version, and required kernel feature flags.
- [ ] Automate environment detection and block unsupported combinations before workload launch.
- [ ] Continuously test N-1/current versions and explicitly document unsupported/EOL combinations.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-096; define the error returned on limit breach.
- [ ] Make MC-096 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Supported-version compatibility matrix for backend/kernel/runtime/adjacent dependencies** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-096 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-096 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-096 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-096 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-096 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-096 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-096 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-096 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-096.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Supported-version compatibility matrix for backend/kernel/runtime/adjacent dependencies**.

## MC-097 — Patching, vulnerability response, security advisory, and end-of-life SLA/process

**Audit status:** Missing  
**Checklist linkage:** C094  
**Priority:** P1 / High  
**Objective:** Implement and prove **patching, vulnerability response, security advisory, and end-of-life SLA/process** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-097 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Patching, vulnerability response, security advisory, and end-of-life SLA/process** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Define severity taxonomy, triage SLA, patch SLA, coordinated disclosure intake, advisory publication process, and emergency out-of-band release path.
- [ ] Track kernel/backend/runtime CVEs against the compatibility matrix and identify affected deployed versions automatically.
- [ ] Publish deprecation/EOL dates and block new deployments after support expiration unless an approved exception exists.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-097; define the error returned on limit breach.
- [ ] Make MC-097 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Patching, vulnerability response, security advisory, and end-of-life SLA/process** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-097 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-097 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-097 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-097 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-097 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-097 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-097 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-097 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-097.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Patching, vulnerability response, security advisory, and end-of-life SLA/process**.

## MC-098 — Backup/restore/reconstruction procedure for policy, configuration, evidence, and exception state where external state exists

**Audit status:** Missing  
**Checklist linkage:** C095  
**Priority:** P1 / High  
**Objective:** Implement and prove **backup/restore/reconstruction procedure for policy, configuration, evidence, and exception state where external state exists** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-098 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Backup/restore/reconstruction procedure for policy, configuration, evidence, and exception state where external state exists** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Classify durable state and explicitly identify what must be backed up versus reconstructed from signed source-of-truth artifacts.
- [ ] Encrypt/version backups, test restore into a clean environment, and verify digests/signatures plus tenant/residency constraints.
- [ ] Define recovery point/recovery time targets and test loss/corruption of policy, config, evidence, and exception stores.
- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-098; define the error returned on limit breach.
- [ ] Make MC-098 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Backup/restore/reconstruction procedure for policy, configuration, evidence, and exception state where external state exists** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-098 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-098 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-098 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-098 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-098 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-098 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-098 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-098 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-098.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Backup/restore/reconstruction procedure for policy, configuration, evidence, and exception state where external state exists**.

## MC-099 — Detailed executable day-0/day-1/day-2 runbooks rather than README-level guidance

**Audit status:** Partial  
**Checklist linkage:** C096  
**Priority:** P1 / High  
**Objective:** Implement and prove **detailed executable day-0/day-1/day-2 runbooks rather than README-level guidance** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-099 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Detailed executable day-0/day-1/day-2 runbooks rather than README-level guidance** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Create executable runbooks for install/bootstrap, deploy, verify, capacity expansion, config update, rollback, rotate credentials, diagnose, quarantine, drain, upgrade, and decommission.
- [ ] For every command/API step document prerequisites, expected output, failure branches, rollback checkpoint, and postcondition verification.
- [ ] Continuously test critical runbooks in staging and after material version changes.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-099; define the error returned on limit breach.
- [ ] Make MC-099 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Detailed executable day-0/day-1/day-2 runbooks rather than README-level guidance** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-099 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-099 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-099 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-099 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-099 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-099 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-099 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-099 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-099.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Detailed executable day-0/day-1/day-2 runbooks rather than README-level guidance**.

## MC-100 — Incident severity, paging, escalation, containment, and recovery runbook

**Audit status:** Missing  
**Checklist linkage:** C097  
**Priority:** P1 / High  
**Objective:** Implement and prove **incident severity, paging, escalation, containment, and recovery runbook** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-100 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Incident severity, paging, escalation, containment, and recovery runbook** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Create a RACI covering design authority, code ownership, production operations, incident command, security approval, and emergency disable authority.
- [ ] Define escalation targets and acknowledgement/resolution objectives for Sev-1/Sev-2 security or availability incidents; test the contact path at least quarterly.
- [ ] Add repository ownership metadata and a machine-readable owner field to release evidence so orphaned components are detectable automatically.
- [ ] Define incident classes for sandbox escape/suspected escape, policy bypass, evidence forgery, widespread launch failure, cleanup leak, and control-plane compromise.
- [ ] Specify paging targets, severity criteria, containment actions, evidence preservation, forensic acquisition, communication, recovery, and post-incident review.
- [ ] Run tabletop and live game-day exercises including emergency disable and credential/key rotation.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-100; define the error returned on limit breach.
- [ ] Make MC-100 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Incident severity, paging, escalation, containment, and recovery runbook** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-100 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-100 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-100 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-100 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-100 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-100 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-100 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-100 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-100.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Incident severity, paging, escalation, containment, and recovery runbook**.

## MC-101 — Recurring access/policy/dependency/configuration/architecture review process

**Audit status:** Missing  
**Checklist linkage:** C098  
**Priority:** P1 / High  
**Objective:** Implement and prove **recurring access/policy/dependency/configuration/architecture review process** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-101 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Recurring access/policy/dependency/configuration/architecture review process** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Set review cadences and owners for privileged access, policy baselines, dependencies/CVEs, exceptions, compatibility claims, and architecture assumptions.
- [ ] Automate stale-access/dependency/exception detection and require tracked remediation for findings.
- [ ] Archive review evidence and feed material changes back into threat model, ADRs, and test plans.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-101; define the error returned on limit breach.
- [ ] Make MC-101 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Recurring access/policy/dependency/configuration/architecture review process** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-101 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-101 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-101 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-101 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-101 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-101 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-101 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-101 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-101.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Recurring access/policy/dependency/configuration/architecture review process**.

## MC-102 — Exception/waiver/technical-debt/deprecation register with owner and expiry

**Audit status:** Missing  
**Checklist linkage:** C099  
**Priority:** P1 / High  
**Objective:** Implement and prove **exception/waiver/technical-debt/deprecation register with owner and expiry** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-102 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Exception/waiver/technical-debt/deprecation register with owner and expiry** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Create a RACI covering design authority, code ownership, production operations, incident command, security approval, and emergency disable authority.
- [ ] Define escalation targets and acknowledgement/resolution objectives for Sev-1/Sev-2 security or availability incidents; test the contact path at least quarterly.
- [ ] Add repository ownership metadata and a machine-readable owner field to release evidence so orphaned components are detectable automatically.
- [ ] Define schema/backend semantic-version rules and the exact changes considered breaking, additive, or operationally incompatible.
- [ ] Implement dual-read/single-write or explicit migration tooling where rolling upgrades require mixed versions.
- [ ] Add downgrade/replay protections so an older peer or profile cannot silently remove mandatory security fields.
- [ ] Use a machine-readable register with unique ID, affected requirement, rationale, risk, compensating control, owner, approver, creation date, expiry, and remediation milestone.
- [ ] Block releases on expired exceptions and surface approaching expiries in dashboards/CI.
- [ ] Require closure evidence and remove compensating controls only after the underlying gap is verified fixed.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-102; define the error returned on limit breach.
- [ ] Make MC-102 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Exception/waiver/technical-debt/deprecation register with owner and expiry** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-102 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-102 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-102 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-102 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-102 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-102 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-102 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-102 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-102.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Exception/waiver/technical-debt/deprecation register with owner and expiry**.

## MC-103 — Formal automated production exit gate spanning architecture through ownership readiness

**Audit status:** Missing  
**Checklist linkage:** C100  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **formal automated production exit gate spanning architecture through ownership readiness** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-103 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Formal automated production exit gate spanning architecture through ownership readiness** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Create a RACI covering design authority, code ownership, production operations, incident command, security approval, and emergency disable authority.
- [ ] Define escalation targets and acknowledgement/resolution objectives for Sev-1/Sev-2 security or availability incidents; test the contact path at least quarterly.
- [ ] Add repository ownership metadata and a machine-readable owner field to release evidence so orphaned components are detectable automatically.
- [ ] Implement a policy-as-code gate requiring ownership, ADR/requirements, supported-platform evidence, threat-model coverage, backend integration, performance, observability, runbooks, and supply-chain evidence.
- [ ] Consume signed machine-readable artifacts and reject missing/stale/waived-without-approval evidence.
- [ ] Version the gate policy and include its digest in release acceptance evidence.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-103; define the error returned on limit breach.
- [ ] Make MC-103 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Formal automated production exit gate spanning architecture through ownership readiness** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-103 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-103 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-103 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-103 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-103 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-103 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-103 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-103 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-103.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Formal automated production exit gate spanning architecture through ownership readiness**.

## MC-104 — CI workflow executing compile, unit, optimized-mode, schema, backend integration, security, benchmark, and release gates

**Audit status:** Missing  
**Checklist linkage:** C081-C090, C100  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **cI workflow executing compile, unit, optimized-mode, schema, backend integration, security, benchmark, and release gates** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-104 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **CI workflow executing compile, unit, optimized-mode, schema, backend integration, security, benchmark, and release gates** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Create protected CI stages for lint/compile, unit, optimized-mode, schema/contract, backend integration, fuzz/security, compatibility matrix, performance, packaging, SBOM/provenance, signing, and final release gate.
- [ ] Run security-sensitive jobs in isolated ephemeral workers with least privilege and protected credentials; prevent untrusted PRs from accessing signing or production secrets.
- [ ] Pin CI actions/images/toolchains by digest/version and preserve machine-readable logs/results as provenance inputs.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-104; define the error returned on limit breach.
- [ ] Make MC-104 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **CI workflow executing compile, unit, optimized-mode, schema, backend integration, security, benchmark, and release gates** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-104 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-104 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-104 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-104 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-104 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-104 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-104 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-104 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-104.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **CI workflow executing compile, unit, optimized-mode, schema, backend integration, security, benchmark, and release gates**.

## MC-105 — SBOM/provenance generation and signed release artifact pipeline

**Audit status:** Missing  
**Checklist linkage:** C045, C090  
**Priority:** P0 / Release-blocking  
**Objective:** Implement and prove **sBOM/provenance generation and signed release artifact pipeline** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-105 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **SBOM/provenance generation and signed release artifact pipeline** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Define canonical bytes to sign, approved algorithms/key sizes, key IDs, trust roots, signature envelope, expiry/epoch, and multi-signature rules if required.
- [ ] Verify signature and digest before parsing/activation side effects; pin minimum schema/policy/backend versions to prevent downgrade.
- [ ] Implement key rotation/revocation and test stale/revoked/unknown-key/replayed policy rejection.
- [ ] Generate SPDX or CycloneDX SBOM including direct/transitive packages, native tools/backends, licenses, versions, hashes, and supplier metadata.
- [ ] Produce SLSA-style provenance/attestation tying source, build environment, dependency lock, CI identity, artifact digest, SBOM digest, and test evidence together.
- [ ] Sign artifacts and attestations with protected keys/keyless workload identity, publish verification instructions, and test signature/provenance enforcement before install.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-105; define the error returned on limit breach.
- [ ] Make MC-105 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **SBOM/provenance generation and signed release artifact pipeline** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-105 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-105 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-105 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-105 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-105 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-105 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-105 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-105 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-105.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **SBOM/provenance generation and signed release artifact pipeline**.

## MC-106 — Distribution license/NOTICE and package metadata suitable for redistribution

**Audit status:** Missing  
**Checklist linkage:** Release hygiene; not explicitly enumerated by `CHECKLIST.json`  
**Priority:** P1 / High  
**Objective:** Implement and prove **distribution license/NOTICE and package metadata suitable for redistribution** as a production-grade capability, with fail-closed security behavior, deterministic lifecycle semantics, measurable operational behavior, and release evidence tied to the exact artifact.

### A. Requirements, ownership, and design

- [ ] Create a stable requirement/work-item ID for MC-106 and assign an accountable engineering owner plus named reviewers.
- [ ] Define the production applicability and explicit out-of-scope cases for **Distribution license/NOTICE and package metadata suitable for redistribution** across each supported OS/backend/deployment mode.
- [ ] Define an executable production lifecycle covering build, sign, stage, canary, promote, rollback, emergency disable, patch, deprecate, and end-of-life.
- [ ] Separate duties for build/sign/release/exception approval where feasible and record every privileged release action in immutable audit evidence.
- [ ] Automate environment compatibility checks before rollout and block promotion when kernel/runtime/backend/dependency combinations are unsupported.
- [ ] Maintain day-0/day-1/day-2 procedures with exact commands/API calls, expected outputs, rollback checkpoints, and validation steps.

### B. Component-specific implementation

- [ ] Select/confirm the redistribution license, add complete LICENSE and NOTICE files, and document third-party license obligations from dependencies and bundled tooling.
- [ ] Add package metadata: name, version, description, authors/maintainers, license expression, supported Python/platform classifiers, repository/issues URLs, and dependency declarations.
- [ ] Run automated license/SBOM policy checks and verify source and binary distributions contain required legal notices.
- [ ] Track exceptions and technical debt with owner, risk statement, compensating control, creation date, expiry, review cadence, and closure evidence.
- [ ] Make the final production gate machine-enforced and require architecture, security, testing, operations, supply-chain, and ownership evidence to be complete.
- [ ] Add explicit hard limits and validation for every attacker- or tenant-controlled collection/string/count introduced by MC-106; define the error returned on limit breach.
- [ ] Make MC-106 idempotent where repeated execution is permitted; otherwise detect and reject duplicate/stale operations deterministically.

### C. Security and failure-mode checklist

- [ ] Identify how compromise, spoofing, replay, downgrade, race, resource exhaustion, or partial failure of **Distribution license/NOTICE and package metadata suitable for redistribution** could weaken isolation; link the findings to threat IDs.
- [ ] Ensure a failure in MC-106 cannot be converted into “success”, “verified”, or executable state through fallback, exception swallowing, skipped validation, or missing evidence.
- [ ] Define cleanup/rollback behavior for failures before side effects, during partial application, after verification, during workload execution, and during teardown.
- [ ] Bound and sanitize diagnostics derived from untrusted inputs; verify secrets, credentials, host paths, tokens, and sensitive policy data are redacted.
- [ ] Add explicit authorization/audit requirements for any MC-106 operator action that can weaken, bypass, disable, override, or force a security control.

### D. Verification and adversarial testing

- [ ] Add unit tests for normal, boundary, malformed, and fail-closed paths specific to this component; assertions must verify externally observable state, not merely that helper functions were called.
- [ ] Add integration tests at the component trust boundary and inject at least one representative failure before, during, and after the critical side effect.
- [ ] Add regression tests for every defect discovered while implementing this component and assign each test a stable traceability ID.
- [ ] Run tests under normal Python and optimized mode where Python assertions must not carry security semantics; treat unexpected skips as failures in release certification.
- [ ] Add at least one adversarial test specific to MC-106 that demonstrates a plausible bypass/abuse attempt is blocked and produces the expected evidence.
- [ ] Add concurrency or ordering tests if MC-106 can overlap with create/apply/verify/exec/terminate/cleanup or configuration activation.
- [ ] Validate behavior at minimum supported values, maximum supported values, one-past-maximum values, empty values, malformed values, and unsupported-version/platform cases.

### E. Observability and operability

- [ ] Emit stable result/reason codes for MC-106 success, rejection, retryable failure, terminal failure, degraded-safe state where allowed, and cleanup failure.
- [ ] Expose health/status/metrics sufficient to distinguish MC-106 misconfiguration, dependency failure, saturation, policy rejection, attack/abuse, and internal software defect.
- [ ] Add runbook steps for diagnosing, containing, recovering, rolling back, and verifying MC-106 without requiring undocumented host manipulation.

### F. Evidence and acceptance gate

- [ ] Update the requirements traceability matrix with implementation symbols, test IDs, evidence locations, responsible owner, and current disposition.
- [ ] Emit machine-readable evidence containing source revision, release/artifact digest, configuration/profile digest where applicable, environment fingerprint, test result, and timestamp.
- [ ] Document residual risks and any platform limitations; create time-bounded waivers only through the approved exception process.
- [ ] Require code review plus security/operations review appropriate to the component criticality before marking the item complete.
- [ ] **Acceptance gate:** MC-106 is not marked complete until implementation and required tests pass on every production-supported target to which the requirement applies.
- [ ] **Acceptance gate:** there are no unresolved P0/P1 defects, unexpected test skips, TODO-only security paths, or undocumented best-effort fallbacks associated with MC-106.
- [ ] **Acceptance gate:** the post-implementation audit can locate concrete code, tests, operational documentation, and machine-readable evidence for **Distribution license/NOTICE and package metadata suitable for redistribution**.

# Final production-readiness closure checklist

- [ ] Re-run the original 106-item residual audit against the implemented repository and mark each component Complete / Partial / Not Applicable with verifiable evidence.
- [ ] Re-run the 100-check `pk_core` conformance suite with the dependency present and archive zero-skipped release evidence.
- [ ] Execute real Linux and macOS backend certification on every claimed supported target and retain environment fingerprints plus evidence digests.
- [ ] Execute the threat-model-derived adversarial suite and verify no mandatory isolation boundary is bypassable.
- [ ] Execute concurrency, fault-injection, soak, burst, overload, and recovery certification and verify no leaked resources or duplicate execution.
- [ ] Generate final SBOM, provenance, signed artifacts, signed acceptance evidence, and verify them from a clean consumer environment.
- [ ] Exercise canary promotion, rollback, emergency disable, incident response, and node reconstruction runbooks before general availability.
- [ ] Confirm every waiver has a valid owner, compensating control, approval, and future expiry; no expired waiver may pass the release gate.
- [ ] Produce a final traceability matrix covering requirement -> implementation -> test -> evidence -> owner -> release decision for every C001-C100 check and MC-001-MC-106 work item.
- [ ] Only after all applicable release-blocking gates pass, update repository assurance language from “reference policy/verifier” to the precise, evidence-supported production claim.

---

**Completion rule:** checking a box means the corresponding evidence is reviewable and reproducible. A design statement, manual assertion, or requested-but-unverified policy is not completion evidence.
