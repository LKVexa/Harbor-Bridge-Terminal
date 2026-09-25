# INV-36 Control transport - audit report

## 5.1.0 missing-component pass (2026-09-22)

**Input:** 5.0.0 hardened archive + `INV36_v5.0.0_MISSING_COMPONENTS_COMPREHENSIVE_CHECKLIST.md` (752 items across MC-01..MC-23, kept verbatim in `docs/source/` with its SHA-256).

**Result:** all 23 missing components now have repository-local implementation, specification or tooling. Item-level ledger (`MC_CHECKLIST_STATUS.json`, rendered in `docs/MC_CHECKLIST_STATUS.md`): **493 DONE, 172 PARTIAL, 18 OPEN_EXTERNAL, 69 OPEN_GOVERNANCE**. DONE means implemented and verified by repository tests/evidence, and the ledger checker refuses DONE on any item that needs a named person, legal decision or approval. The 100-control matrix moved from 10/27/63 (implemented/partial/missing) to **65/34/1** (`AUDIT_MATRIX.json`; per-control 5.0.0 status kept as `status_5_0_0`).

**Still not production-certifiable.** Local gate (`python -m inv36_control_transport.audit`): **9 PASS, 1 FAIL, 3 SKIP**, exit 1. The FAIL is G10 governance (no LICENSE; every owner role UNASSIGNED). The SKIPs are G11 real vsock (kernel paths pass; no end-to-end peer VM), G12 dependency vulnerability scan (pip-audit not installable in the authoring sandbox; the CI `security` job runs it) and G13 pk_core (not supplied). `--certify` exits 2 (infrastructure error) because pk_core is absent. SKIP is never counted as PASS.

### Defects found and fixed while applying the checklist

| ID | Defect | Fix |
|---|---|---|
| B-001 | Quarantine directive signatures failed to verify after round-trip (float vs int canonical JSON) | canonical body always emits floats |
| B-002 | `peer` quarantine scope could not match (context attribute is `subject`) | explicit scope->field mapping |
| B-003 | A channel whose peer reset stayed registered as live on the surviving side (asymmetric failure) | stream failure closes and deregisters the channel |
| B-004 | Audit checkpoint could be attempted while the sink was down (uncaught OSError) | checkpoint only with empty buffer and healthy sink |
| B-005 | Wheel build fails with Debian-patched setuptools 68 (`install_layout`) and `requires >=77` could not be met offline | build via `build_meta` with `SETUPTOOLS_USE_DISTUTILS=stdlib` when setuptools < 70; build requirement set to >=68 |
| B-006 | Metric label normalisation cost ~9 % of round-trip time | bounded memoisation; suite re-run |

### Verification

`python -m unittest` (normal and `-O`): 173 tests, 2 skipped (pk_core estate tests). ruff (E,F,W,B,S) clean; mypy clean. Fuzz: 10 targets x 300 (gate) iterations, seeds reproducible, 0 failures. Wheel + sdist built from `git archive`, manifest check, SBOM, provenance, ephemeral-key sign/verify and tamper detection pass. Benchmarks and soak/fleet results: `docs/PERFORMANCE.md`, work-order evidence.

### What remains (owner or external)

License selection; named owners/approvers; decision on the missing `MASTER.md`; real pk_core integration; certified VM rows (Firecracker/QEMU x86_64/aarch64); production KMS/HSM `KeyProvider`; managed signing identity; external cryptographic review of PK_CTRL_HS/1; CI activation (branch protection, release environment, self-hosted vsock runner); multi-hour soak; power/thermal.

---

# 5.0.0 audit (historical)


**Audited input:** supplied `inv36_control_transport` repository  
**Updated version:** 5.0.0  
**Audit date:** 2026-09-22  
**Scope:** repository-local code, tests, metadata and documentation. External `pk_core` and sibling components were not supplied.

## Executive result

The update compiles, the standalone transport test suite passes, optimized-mode testing passes, and a wheel builds successfully. The security-critical transport was materially hardened, but this archive is **not production-complete**: of the 100 checklist requirements, **10 are implemented with repository-local evidence, 27 are partial, and 63 are missing**. Production certification is therefore not supported by this archive alone.

## High-impact defects found in 4.1.0 and fixed

- **Non-standard encryption construction:** custom SHA-256 counter keystream + HMAC replaced by AES-256-GCM-SIV.
- **Cross-session key/nonce reuse risk:** added mandatory fresh session ID and session-bound HKDF derivation.
- **Reordering semantics were incomplete:** old code accepted any authenticated sequence newer than the last; version 5 accepts only the exact next sequence.
- **No sequence-wrap guard:** added fail-closed 64-bit exhaustion handling.
- **Concurrent sender race:** send/receive state is now lock-protected.
- **Unbounded relay evidence history:** replaced with bounded/disable-able retention and wire-size enforcement.
- **Secret exposure/retention:** establishment secret is omitted from repr and its stored reference is dropped after derivation.
- **Tests could all skip:** security-critical transport is now independent of `pk_core`; only estate integration skips when `pk_core` is absent.
- **Misleading conformance posture:** updated tests no longer require every inherited finding to pass, and this report distinguishes implementation from partial/missing evidence.
- **Missing `MASTER.md` was claimed present:** README corrected; file remains explicitly missing rather than fabricated.

## Versioning decision

The repository was bumped from **4.1.0 to 5.0.0** because the wire/API contract changes are breaking: `PK_CTRL_FRAME/1` and `PK_CTRL_SESSION/1` are replaced by `/2`, the old frame encoding is not accepted, and `Session` now requires a fresh shared `session_id`.

## Validation performed

- `python -m compileall`: PASS.
- `python -m unittest discover`: PASS; 18 tests discovered, 16 passed, 2 estate tests skipped because `pk_core` is absent.
- `python -O tests/test_transport.py`: PASS; 14 standalone transport tests.
- `python -m pip wheel --no-build-isolation --no-deps`: PASS; wheel for 5.0.0 built successfully.
- Manual/static checks: no remaining bare Python `assert` statements, no bare `except:`, version pins synchronized, README no longer references a nonexistent local master file as present.

## Repository-level missing components

- **External estate core / gate runtime** — pk_core is referenced but absent, so the 100-item estate gate and evidence chain cannot be executed from this archive alone. _Related: C020, C090, C100._
- **MASTER.md source prompt/workflow corpus** — README 4.1.0 claimed this file was carried verbatim, but it was not present in the supplied archive. It was not fabricated during this audit. _Related: provenance/source artifact._
- **Real virtio-vsock transport adapter** — No AF_VSOCK/socket/device implementation, framing loop, reconnect logic or host/guest endpoint is present. _Related: C010, C021, C030, C031._
- **Authenticated session-establishment adapter** — Session consumes an authenticated shared secret and session ID but does not perform attestation, ECDH/handshake, certificate validation or identity proof. _Related: C023, C044, C048._
- **Key custody and rotation integration** — No KMS/HSM/secret-store integration, rotation protocol, key epoch manager or revocation path exists. _Related: C039, C047, C048._
- **Typed external protocol schema / IDL** — PK_CTRL_FRAME/2 is defined in Python code, not in an independent WIT/Protobuf/CBOR/other schema with generated compatibility tests. _Related: C022, C082._
- **Authorization / tenant policy layer** — No authorization decision point, tenant ACL/capability policy or workload permission mapping is implemented. _Related: C024, C042, C046._
- **Runtime configuration subsystem** — No schema, secure defaults, validation, provenance, environment/site overlays, atomic activation or rollback implementation exists. _Related: C032-C038._
- **Health, backpressure and failure-control subsystem** — No readiness/stall detector, retry/backoff, circuit breaker, admission/load shedding, failover or degraded-mode controller exists. _Related: C052-C056._
- **Persistent/restart/session recovery design** — No persistence or restart/resume state machine exists; sessions must currently be re-established. _Related: C057._
- **Quarantine / emergency isolation control** — No programmatic freeze/quarantine/disable control exists in the component. _Related: C059, C092._
- **Production observability pipeline** — No metrics exporter, structured logger, trace propagation, explain view, retention policy, dashboards or alerts are included. _Related: C071-C080._
- **Performance certification suite** — No reproducible benchmark harness, load/overload/scale tests, power/thermal measurements, capacity model or regression gate exists. _Related: C061-C070._
- **Protocol fuzzing / property-based robustness suite** — No fuzz corpus, harness, sanitizer/property framework or malformed-input campaign exists. _Related: C085._
- **Platform/hypervisor compatibility test matrix** — No CPU architecture, OS, hypervisor, provider or actual vsock interoperability certification exists. _Related: C084, C093._
- **Integration / disaster / soak / fleet-scale suites** — No adjacent-layer integration, partition/reconnect, disaster, soak, burst or fleet-scale test harness is included. _Related: C030, C083, C088, C089._
- **Supply-chain integrity controls** — No SBOM, lockfile/hash policy, artifact signing, provenance verification, dependency vulnerability scan or release attestation is present. _Related: C045, C090._
- **Tamper-evident security audit log** — No append-only/hash-chained/signature-backed audit event sink is implemented. _Related: C049._
- **Formal ADR for technology selection** — No approved architecture decision record justifies virtio-vsock, crypto selection, trust boundary or alternatives. _Related: C010._
- **Requirements specification + traceability matrix** — The checklist exists, but there is no SHALL-level product requirements document and implementation/test/evidence traceability mapping. _Related: C011-C020._
- **Operational release/governance pack** — No owner/escalation, incident runbook, canary/staged rollout plan, patch/EOL SLA, recurring review schedule or waiver/debt register exists. _Related: C009, C092, C094, C097-C100._
- **Explicit software license** — No LICENSE/NOTICE or other grant is included in the supplied repository. _Related: repository governance._
- **CI workflow** — No automated CI configuration is present to run unit/security/build checks on changes. _Related: C070, C090, C100._

## Complete checklist gap inventory

Every **partial** and **missing** checklist requirement is listed below. The machine-readable equivalent, including the implemented rows, is `AUDIT_MATRIX.json`.

### Architecture & Scope

- **INV-36-C009 — MISSING:** Assign an accountable owner and escalation path for Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C010 — MISSING:** Approve an architecture decision record for Control transport, its technologies (virtio-vsock), and its function (Lightweight host/guest control traffic).  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
### Requirements & Semantics

- **INV-36-C011 — MISSING:** Translate the source function of Control transport — Lightweight host/guest control traffic — into testable SHALL-level requirements.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C012 — MISSING:** Define functional requirements for Control transport across cloud, datacenter, near-edge, and far-edge contexts where applicable.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C013 — PARTIAL:** Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.  
  Audit: Authenticity, relay-blindness and one latency SLO exist, but availability/durability/consistency/isolation/determinism targets are not comprehensively specified or certified. Evidence: contract.py.
- **INV-36-C014 — MISSING:** Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C015 — PARTIAL:** Define lifecycle states and legal state transitions managed or exposed by Control transport.  
  Audit: Open/closed and sequence state exist, but no complete documented lifecycle/state-transition model covers establishment, rotation, draining, reconnect and teardown. Evidence: transport.py.
- **INV-36-C016 — PARTIAL:** Define versioning and backward-compatibility requirements for Control transport.  
  Audit: Frame/session versioning and the 4.x break are documented; formal backward/forward compatibility policy and deprecation windows are absent. Evidence: COMPATIBILITY.md; CHANGELOG.md.
- **INV-36-C017 — MISSING:** Define capacity ceilings, quotas, and fairness semantics relevant to Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C018 — MISSING:** Define behavior when network connectivity is intermittent or absent.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C019 — MISSING:** Define precedence rules when Control transport requirements conflict with security, residency, SLO, or cost constraints.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C020 — MISSING:** Maintain a requirements traceability matrix from each Control transport requirement to implementation and verification evidence.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
### Interfaces & Integration

- **INV-36-C021 — PARTIAL:** Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Control transport.  
  Audit: Logical session/frame/relay interfaces are enumerated, but real virtio-vsock/device/control-plane boundaries are not implemented or enumerated. Evidence: README.md; contract.py; transport.py.
- **INV-36-C022 — PARTIAL:** Use versioned typed schemas for all externally visible Control transport contracts.  
  Audit: Binary frame layout is versioned in code, but there is no independent typed schema/IDL/WIT definition or schema conformance artifact. Evidence: transport.py; COMPATIBILITY.md.
- **INV-36-C023 — PARTIAL:** Define authentication requirements at each Control transport boundary.  
  Audit: Frames are cryptographically authenticated after establishment, but authentication requirements/implementation for every external boundary are missing. Evidence: transport.py; SECURITY.md.
- **INV-36-C024 — MISSING:** Define authorization and explicit capability requirements at each Control transport boundary.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C026 — MISSING:** Define structured failure codes and machine-readable error details for Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C027 — PARTIAL:** Define compatibility behavior when peers use different supported versions.  
  Audit: Typed Python exceptions exist, but no externally versioned error schema, retryability taxonomy or status mapping is defined. Evidence: transport.py.
- **INV-36-C028 — MISSING:** Document payload, concurrency, queue, connection, or resource limits at Control transport interfaces.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C029 — PARTIAL:** Provide reference examples and conformance fixtures for Control transport.  
  Audit: Protocol-level failure injection covers tamper/replay/reorder/size/key mismatch; adjacent service, device and relay boundary failure injection is absent. Evidence: tests/test_transport.py.
- **INV-36-C030 — MISSING:** Create automated integration tests proving Control transport interoperates with adjacent architectural layers.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
### Implementation & Configuration

- **INV-36-C031 — MISSING:** Select and pin approved implementations, versions, or specifications for Control transport: virtio-vsock.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C032 — MISSING:** Separate immutable artifacts from mutable configuration and state for Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C033 — MISSING:** Define declarative configuration and secure defaults for Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C034 — MISSING:** Validate configuration before activation and fail closed on security-critical errors.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C035 — MISSING:** Support site- and environment-specific configuration without rebuilding immutable artifacts.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C036 — MISSING:** Record configuration provenance, version, author, and activation time.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C037 — MISSING:** Apply atomic or transactional configuration updates where partial application is unsafe.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C038 — MISSING:** Define automatic and operator-driven rollback for failed Control transport changes.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C039 — PARTIAL:** Keep credentials and secret material out of ordinary Control transport configuration and diagnostics.  
  Audit: Secret repr exposure is prevented and establishment-secret retention is reduced, but there is no full secret/configuration/diagnostic policy or custody integration. Evidence: transport.py; SECURITY.md.
- **INV-36-C040 — MISSING:** Provide a deterministic bootstrap path from an empty node/environment to healthy Control transport operation.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
### Security, Trust & Isolation

- **INV-36-C041 — PARTIAL:** Threat-model Control transport against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.  
  Audit: A transport threat model exists, but tenant compromise, supply chain, control-plane abuse and deployment-specific threats are not fully analyzed. Evidence: SECURITY.md; contract.py.
- **INV-36-C042 — MISSING:** Apply least privilege to every identity and capability used by Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C043 — MISSING:** Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Control transport permits.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C044 — PARTIAL:** Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.  
  Audit: Possession of session traffic keys authenticates frames, but peer/node/artifact/provider/control-plane identity establishment is external and unimplemented. Evidence: transport.py; SECURITY.md.
- **INV-36-C045 — MISSING:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C046 — MISSING:** Enforce tenant/workload isolation across Control transport execution, memory, state, network, and device boundaries as applicable.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C047 — PARTIAL:** Encrypt sensitive Control transport data in transit and at rest with managed key rotation.  
  Audit: Sensitive frame data is encrypted in transit; at-rest protection and managed key rotation are not implemented. Evidence: transport.py; SECURITY.md.
- **INV-36-C048 — MISSING:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C049 — MISSING:** Emit tamper-evident audit events for security-sensitive Control transport operations.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C050 — PARTIAL:** Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.  
  Audit: Adversarial tests cover tamper, replay, reordering, reflection, wrong key/session and size bounds; privilege escalation, injection, escape, side channels and broader resource attacks remain untested. Evidence: tests/test_transport.py.
### Resilience & Failure Handling

- **INV-36-C051 — PARTIAL:** Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Control transport.  
  Audit: Protocol failure modes are enumerated; process/VM/node/site/provider/control-plane failure modes and objectives are incomplete. Evidence: contract.py.
- **INV-36-C052 — MISSING:** Define automated health and stall detection thresholds for Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C053 — MISSING:** Implement bounded retry with backoff and jitter only where operations are safe to retry.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C054 — MISSING:** Implement admission control, load shedding, or circuit breaking to prevent Control transport failure cascades.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C055 — MISSING:** Define failover behavior without violating isolation, residency, or consistency requirements.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C056 — MISSING:** Provide degraded operation when noncritical dependencies are unavailable.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C057 — PARTIAL:** Define crash-consistency, restart, resume, or replay semantics for mutable Control transport state.  
  Audit: Fresh-session re-establishment is required, but persistent crash-consistency/restart/resume semantics are not implemented or tested. Evidence: SECURITY.md; COMPATIBILITY.md.
- **INV-36-C058 — PARTIAL:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.  
  Audit: Replay/duplicate/out-of-order control frames are handled; split-brain, duplicate ownership and stale-controller behavior are not implemented. Evidence: transport.py; tests/test_transport.py.
- **INV-36-C059 — MISSING:** Provide quarantine, freeze, disable, or isolation controls for unsafe Control transport behavior.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C060 — PARTIAL:** Run fault-injection tests proving Control transport recovery against documented objectives.  
  Audit: Protocol fault tests exist; process/node/site/dependency fault-injection and recovery-objective tests are absent. Evidence: tests/test_transport.py.
### Performance & Resource Efficiency

- **INV-36-C061 — MISSING:** Establish reproducible baselines for Control transport latency, throughput, startup, CPU, memory, storage, network, and power overhead.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C062 — PARTIAL:** Define p50, p95, p99, and worst-case performance thresholds for Control transport.  
  Audit: A p99 small-frame latency objective exists, but p50/p95/worst-case thresholds and certified target profiles are absent. Evidence: contract.py.
- **INV-36-C063 — MISSING:** Measure Control transport under steady load, burst load, overload, scale-out, scale-in, and recovery.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C064 — MISSING:** Measure per-workload and per-tenant overhead introduced by Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C065 — MISSING:** Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C066 — MISSING:** Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C067 — PARTIAL:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.  
  Audit: Plaintext/wire bounds, sequence bounds and relay-history bounds exist; broader queue, concurrency, fan-out and memory ceilings are not modeled. Evidence: transport.py.
- **INV-36-C068 — MISSING:** Measure power and thermal impact on constrained edge nodes where relevant.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C069 — MISSING:** Define capacity models and saturation signals that predict when Control transport needs more resources.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C070 — MISSING:** Block releases that regress approved Control transport startup, density, throughput, or tail-latency thresholds.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
### Observability & Explainability

- **INV-36-C071 — MISSING:** Expose Control transport health, readiness, version, configuration, dependency status, and active capability set.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C072 — PARTIAL:** Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.  
  Audit: In-memory counters are present, but no production metrics exporter covers latency, saturation, backlog and resource usage. Evidence: transport.py; contract.py.
- **INV-36-C073 — MISSING:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C074 — MISSING:** Propagate trace context across all relevant Control transport boundaries.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C075 — MISSING:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C076 — MISSING:** Record the reason for every automated decision made by Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C077 — MISSING:** Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C078 — MISSING:** Correlate Control transport events with application release lineage and the live infrastructure graph.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C079 — MISSING:** Define telemetry retention, sampling, privacy, and export policy.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C080 — MISSING:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
### Testing & Certification

- **INV-36-C082 — PARTIAL:** Create contract tests for every public Control transport interface.  
  Audit: Transport contract behavior has tests and the pk_core adapter has conditional tests; every public/external interface is not contract-tested. Evidence: tests/test_transport.py; tests/test_component.py.
- **INV-36-C083 — MISSING:** Create integration tests with every supported adjacent layer and execution tier.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C084 — MISSING:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C085 — MISSING:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C086 — PARTIAL:** Create concurrency and race-condition tests for shared/distributed Control transport state.  
  Audit: Concurrent send sequence allocation is tested; distributed/shared-state race tests and receive-side concurrency schedules are incomplete. Evidence: tests/test_transport.py.
- **INV-36-C087 — PARTIAL:** Create security tests derived directly from the Control transport threat model.  
  Audit: Several tests are threat-derived, but the full threat model does not have one-to-one security tests. Evidence: tests/test_transport.py; SECURITY.md.
- **INV-36-C088 — MISSING:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C089 — MISSING:** Create disaster, partition, reconnect, and degraded-control-plane tests.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C090 — MISSING:** Require machine-readable acceptance evidence before certifying a Control transport release for production.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
### Operations, Release & Governance

- **INV-36-C091 — PARTIAL:** Define production SLOs, error budgets, and support commitments for Control transport.  
  Audit: Several SLOs/error budgets are listed, but operational support commitments, measurement windows and ownership are absent. Evidence: contract.py.
- **INV-36-C092 — MISSING:** Define canary, staged rollout, rollback, and emergency-disable procedures for Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C093 — PARTIAL:** Maintain a supported-version compatibility matrix for Control transport and adjacent dependencies.  
  Audit: Protocol/runtime compatibility is documented, but CPU/hypervisor/provider/adjacent dependency matrix and certified versions are absent. Evidence: COMPATIBILITY.md.
- **INV-36-C094 — MISSING:** Define patching, vulnerability response, and end-of-life SLAs for Control transport.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C095 — PARTIAL:** Provide backup, restore, migration, or reconstruction procedures for Control transport state where applicable.  
  Audit: The transport is mostly ephemeral and requires re-establishment, but explicit backup/restore/reconstruction procedures and ownership are not documented. Evidence: SECURITY.md; COMPATIBILITY.md.
- **INV-36-C096 — PARTIAL:** Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks.  
  Audit: Basic bootstrap/test guidance exists, but complete day-0/day-1/day-2 production runbooks, deployment steps and troubleshooting are absent. Evidence: README.md.
- **INV-36-C097 — MISSING:** Define incident severity, paging, escalation, containment, and recovery procedures.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C098 — MISSING:** Perform recurring access, policy, dependency, configuration, and architecture reviews.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C099 — MISSING:** Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.
- **INV-36-C100 — MISSING:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.  
  Audit: No repository-local implementation, operational artifact, test evidence, or certifying output was found that fully addresses this requirement.

## Remaining audit limitations

- `pk_core` is not bundled, so estate findings, gate verdicts and evidence-ledger chaining could not be reproduced.
- No network/package-index vulnerability scan was performed; the audit used the locally installed `cryptography 46.0.4` implementation for tests.
- No actual virtio-vsock device was available in this archive, so host/guest interoperability and latency SLOs were not measured.
- No external sibling repositories were assumed present. Requirements that depend on them are marked partial or missing unless this repository contains its own evidence.

## Release posture

Version 5.0.0 is a substantially safer reference transport and is suitable for further integration testing. It should **not** be labeled Production GO until the missing/partial components above are implemented or explicitly provided by the surrounding estate with traceable evidence.
