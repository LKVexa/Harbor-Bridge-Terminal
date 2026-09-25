# INV-32 v4.2.0 → v4.3.0 — Checklist execution report

Generated from `RTM.json` by `tools/build_rtm.py`. One row per checklist bullet; statuses are deliberately conservative.
Per the checklist's completion rule no bullet is *complete* until an immutable CI result, operational evidence and
owner approval exist; the production exit gate therefore returns **FAIL** (see `evidence/exit_gate.json`).

**Totals (682 bullets):** IMPLEMENTED 381, DOCUMENTED 144, PARTIAL 115, BLOCKED 42

| WS | Workstream | Implemented | Documented | Partial | Blocked |
|---:|---|---:|---:|---:|---:|
| 0 | Engineering evidence convention | 6 | 1 | 1 | 2 |
| 1 | HyperFlux / hypervisor adapter | 35 | 0 | 8 | 3 |
| 2 | pk_core packaging & bootstrap | 14 | 5 | 5 | 1 |
| 3 | Formal schemas & protocol | 27 | 4 | 1 | 1 |
| 4 | AuthN / AuthZ / capabilities | 23 | 1 | 3 | 2 |
| 5 | Declarative configuration | 30 | 0 | 2 | 0 |
| 6 | Durable state & audit | 24 | 3 | 6 | 2 |
| 7 | Controller fencing & ownership | 23 | 1 | 1 | 0 |
| 8 | Health, stall, quarantine | 20 | 1 | 3 | 1 |
| 9 | Retry, backpressure, admission | 24 | 0 | 1 | 0 |
| 10 | Failure & failover model | 12 | 9 | 5 | 0 |
| 11 | Performance & capacity | 17 | 6 | 12 | 7 |
| 12 | Observability | 26 | 6 | 7 | 0 |
| 13 | Security program | 17 | 10 | 11 | 5 |
| 14 | Test program | 15 | 2 | 15 | 11 |
| 15 | Requirements & evidence | 19 | 12 | 3 | 1 |
| 16 | Ownership & governance | 3 | 18 | 9 | 2 |
| 17 | Version compatibility | 6 | 14 | 2 | 0 |
| 18 | Tenant quota & fairness | 14 | 1 | 11 | 1 |
| 19 | Runbooks | 0 | 46 | 0 | 1 |
| 20 | Release hygiene & CI | 26 | 4 | 9 | 2 |

## What is blocking the remainder

| Blocker | Rows |
|---|---:|
| Hosted CI runner + immutable result store not available to this execution (workflow file provided) | 28 |
| HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed | 23 |
| Accountable owners/approvers must be named by the organisation (governance.json owners = null) | 20 |
| Real hardware classes / disposable test VMs / real hypervisor not available | 20 |
| Deployment environment (encrypted volume, central audit sink, dashboards backend) not available | 18 |
| Platform PKI / identity provider / KMS not selected (ADR-0004) | 13 |
| Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied | 7 |
| Consensus lease store (etcd/ZooKeeper/Consul) not selected (ADR-0003) | 5 |
| owner decision | 3 |
| No released, hash-pinnable pk_core artifact supplied (ADR-0002) | 2 |
| Runbooks not yet exercised in a game day (needs a real environment) | 2 |
| License choice is an owner decision | 2 |
| no fuzz crash found yet | 2 |
| tenant SLA model not supplied | 2 |
| no second supported major exists | 1 |
| only one language implementation exists | 1 |
| site/environment identity model not supplied | 1 |
| design decision pending owner review | 1 |
| PITR requires a store with point-in-time capability (ADR-0005) | 1 |
| owner decision: should saturation flip readiness | 1 |
| owner decision: audit circuit transitions | 1 |
| only one store version exists | 1 |
| owner decision: bounded waiting vs reject | 1 |
| audit query API not in scope | 1 |

## Row detail


### WS0 — Engineering evidence convention

- ✅ `CL-00-EVID-01` Source-code path and symbol(s).
- ✅ `CL-00-EVID-02` Versioned schema/API/ABI artifact.
- ✅ `CL-00-EVID-03` Automated unit/contract/integration/security/performance test ID.
- ⛔ `CL-00-EVID-04` CI job and immutable test result. — _blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-00-EVID-05` Configuration sample and validation output.
- 📄 `CL-00-EVID-06` Operator runbook or recovery procedure.
- ◐ `CL-00-EVID-07` Security review or threat-model entry. — _threat-model entries exist per control; human security review not performed; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ✅ `CL-00-EVID-08` Benchmark or SLO evidence where the requirement is performance-sensitive.
- ✅ `CL-00-EVID-09` Release-note entry and compatibility statement where externally visible behavior changes.
- ⛔ `CL-00-EVID-10` Owner, reviewer, approval date, and expiry/re-review date where governance is involved. — _blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_

### WS1 — Architecture and boundary definition

- ✅ `CL-01-AABD-01` Define an explicit `HypervisorAdapter` interface separate from `ElasticHost` policy/state logic.
- ✅ `CL-01-AABD-02` Specify methods for guest discovery, current-memory query, current-vCPU query, memory grow, memory reclaim, memory hot-unplug where supported, vCPU add/remove, free-page query, capability discovery, cancellation, and health probing.
- ⛔ `CL-01-AABD-03` Define whether HyperFlux is a library, daemon, RPC peer, kernel interface, device interface, or composition of these; document every trust boundary. — _blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ⛔ `CL-01-AABD-04` Pin the approved HyperFlux specification/version and record the exact compatibility contract. — _blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-01-AABD-05` Define host identity, guest identity, tenant identity, VM/runtime identity, and how each maps to HyperFlux/hypervisor identifiers. — _identity mapping defined; provider identifier mapping pending spec; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ✅ `CL-01-AABD-06` Define adapter capability negotiation so unsupported features fail before mutation rather than mid-operation.
- ✅ `CL-01-AABD-07` Define atomicity expectations for each primitive: all-or-nothing, partially applied, or compensating rollback required.
- ✅ `CL-01-AABD-08` Specify timeout and cancellation semantics for long-running or stalled balloon/hot-plug operations.
- ◐ `CL-01-AABD-09` Specify whether vCPU topology changes preserve NUMA, socket/core/thread topology constraints. — _NUMA preservation is a provider capability flag only; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-01-AABD-10` Define memory-granularity rules: MiB/page alignment, huge pages, NUMA node affinity, pinned memory, device/DMA memory, and non-balloonable regions. — _block alignment + non-balloonable + boot vCPU enforced; huge pages/NUMA affinity pending provider; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_

### WS1 — Implementation

- ◐ `CL-01-I-01` Add a production adapter module such as `adapters/hyperflux.py` and keep the in-memory model as a deterministic reference adapter. — _adapters/hyperflux.py is a fail-closed shell; FakeHypervisor is the deterministic reference adapter; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ✅ `CL-01-I-02` Implement read-before-write verification of live guest resource state before every mutation.
- ✅ `CL-01-I-03` Implement compare-and-swap or equivalent expected-state fencing so stale policy decisions cannot overwrite newer hypervisor state.
- ✅ `CL-01-I-04` Map `PK_RESOURCE_ADJUSTMENT/2.operation_id` to an adapter idempotency key or local durable deduplication record.
- ✅ `CL-01-I-05` Preserve `from_mib`, `requested_mib`, `target_mib`, `applied_mib`, and rollback identity using values confirmed from the hypervisor, not caller assumptions.
- ✅ `CL-01-I-06` Preserve `from_vcpus`, `requested_vcpus`, and `applied_vcpus` using hypervisor-confirmed state.
- ✅ `CL-01-I-07` Reject any hypervisor-reported result that violates guest floor/ceiling, vCPU limits, or host reserve after reconciliation.
- ✅ `CL-01-I-08` Re-query live state after every mutation and compare the resulting state with the intended state.
- ✅ `CL-01-I-09` Treat guest non-cooperation as a first-class outcome rather than assuming balloon success.
- ✅ `CL-01-I-10` Detect partial ballooning and record actual reclaimed/grown memory separately from requested memory.
- ✅ `CL-01-I-11` Detect partial vCPU hot-plug and fail/compensate according to the defined transaction semantics.
- ✅ `CL-01-I-12` Implement explicit adapter error classes that map provider/hypervisor errors into the package failure taxonomy.
- ✅ `CL-01-I-13` Never expose raw provider error text containing host paths, tokens, guest secrets, or privileged diagnostics to untrusted callers.
- ✅ `CL-01-I-14` Add capability cache invalidation when hypervisor version, guest agent, kernel, or VM state changes.
- ✅ `CL-01-I-15` Add adapter shutdown/drain behavior that prevents new mutations during process termination or upgrade.

### WS1 — Isolation and safety

- ✅ `CL-01-IAS-01` Verify target guest identity immediately before privileged mutation to prevent identifier reuse attacks.
- ✅ `CL-01-IAS-02` Require tenant-to-guest ownership validation before any adjustment.
- ✅ `CL-01-IAS-03` Enforce host reserve using hypervisor-confirmed allocatable memory, including memory unavailable to guests.
- ✅ `CL-01-IAS-04` Account for hypervisor overhead, page tables, device emulation, huge-page fragmentation, and reserved pools when calculating allocatable memory.
- ✅ `CL-01-IAS-05` Fail closed if live host capacity cannot be trusted.
- ✅ `CL-01-IAS-06` Define behavior for paused, migrating, suspended, crashed, booting, and shutting-down guests.
- ✅ `CL-01-IAS-07` Block resource mutation during incompatible migration/snapshot/device operations unless the hypervisor guarantees safety.
- ✅ `CL-01-IAS-08` Validate that removal operations cannot detach a vCPU or memory block required by guest boot/runtime constraints.
- ✅ `CL-01-IAS-09` Record the provider request ID and provider result in the tamper-evident audit event.

### WS1 — Verification and acceptance

- ✅ `CL-01-VAA-01` Build a fake HyperFlux adapter for deterministic contract tests.
- ⛔ `CL-01-VAA-02` Build a real integration harness using disposable test VMs. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ✅ `CL-01-VAA-03` Test memory grow/reclaim at minimum, maximum, floor, ceiling, reserve, and alignment boundaries.
- ✅ `CL-01-VAA-04` Test guest refusal, timeout, partial completion, cancellation, provider restart, and transient RPC failure.
- ◐ `CL-01-VAA-05` Test vCPU add/remove across all supported guest states and topology configurations. — _all lifecycle states tested; topology configurations need a real provider; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ✅ `CL-01-VAA-06` Test stale expected-state rejection when another controller or operator changes the VM first.
- ✅ `CL-01-VAA-07` Test duplicate `operation_id` replay across process restart.
- ✅ `CL-01-VAA-08` Test rollback only against authenticated, matching, current-state records.
- ✅ `CL-01-VAA-09` Test adapter behavior when capabilities change during runtime.
- ◐ `CL-01-VAA-10` Capture p50/p95/p99 adapter latency and provider latency separately. — _controller-side provider latency measured against the fake only; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-01-VAA-11` Demonstrate zero violations of host reserve and guest floors during integration stress tests. — _zero reserve/floor violations under concurrent stress on the fake; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ◐ `CL-01-VAA-12` Produce a compatibility matrix covering HyperFlux version, hypervisor version, guest OS/kernel/agent version, CPU architecture, and feature support. — _matrix exists; production rows unsupported until provider spec; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_

### WS2 — Dependency contract

- 📄 `CL-02-DC-01` Decide whether `pk_core` is vendored, packaged as a separately versioned dependency, or replaced by a local minimal contract implementation.
- 📄 `CL-02-DC-02` Define the minimum and maximum compatible `pk_core` versions.
- ⛔ `CL-02-DC-03` Pin the production dependency using an immutable version and integrity hash. — _blocked on: No released, hash-pinnable pk_core artifact supplied (ADR-0002)_
- 📄 `CL-02-DC-04` Record the `pk_core` API symbols consumed by `contract.py` (`Contract`, `Dependency`, `Slo`) and any transitive expectations.
- ◐ `CL-02-DC-05` Add a dependency compatibility test that imports and exercises every required symbol. — _compat test present; skips until pk_core is installable; blocked on: No released, hash-pinnable pk_core artifact supplied (ADR-0002)_
- ✅ `CL-02-DC-06` Define behavior when an incompatible `pk_core` version is installed: fail at installation/activation, not at first production request.

### WS2 — Packaging

- ✅ `CL-02-P-01` Add `pyproject.toml` with package name, version source, Python version bounds, dependencies, optional test/dev dependencies, and build backend.
- ✅ `CL-02-P-02` Ensure `VERSION` and `__version__` are generated from or validated against one canonical version source.
- ◐ `CL-02-P-03` Generate a lock file or equivalent immutable dependency resolution for CI/release builds. — _runtime has zero dependencies; lock pins build backend; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ◐ `CL-02-P-04` Include dependency hashes where the package manager supports them. — _build-backend hashes recorded in lock; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ◐ `CL-02-P-05` Build wheel and source distribution artifacts in clean CI. — _wheel+sdist built and installed into an empty venv locally (evidence/clean_install.log); blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-02-P-06` Test installation from the built wheel into an empty virtual environment.
- ✅ `CL-02-P-07` Test import and execution without repository-relative path hacks.
- ✅ `CL-02-P-08` Ensure test-only dependencies cannot leak into production requirements.
- 📄 `CL-02-P-09` Define offline/bootstrap behavior for disconnected edge environments.

### WS2 — Deterministic bootstrap

- ✅ `CL-02-DB-01` Add a one-command/bootstrap entry point that checks Python runtime, package integrity, `pk_core`, adapter dependencies, configuration, and writable state directories.
- ✅ `CL-02-DB-02` Add a `--check` or preflight mode that performs no mutation.
- ✅ `CL-02-DB-03` Emit machine-readable bootstrap diagnostics and exit codes.
- ✅ `CL-02-DB-04` Fail closed on missing or untrusted required dependencies.
- ✅ `CL-02-DB-05` Verify installed package digest against release metadata before activation where practical.
- 📄 `CL-02-DB-06` Document recovery when dependency installation is unavailable or corrupt.

### WS2 — Acceptance

- ◐ `CL-02-A-01` CI must create a brand-new environment, install only declared artifacts, and run the full test suite successfully. — _executed locally in a fresh venv from the built wheel; hosted CI pending; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-02-A-02` No required import may depend on an undeclared sibling checkout.
- ✅ `CL-02-A-03` `pip check` or equivalent dependency-consistency validation must pass.
- ✅ `CL-02-A-04` Dependency inventory must appear in the SBOM and release provenance.

### WS3 — Schema design

- 📄 `CL-03-SD-01` Select canonical schema technology per boundary: JSON Schema/OpenAPI, protobuf/gRPC, WIT, or another approved IDL.
- ✅ `CL-03-SD-02` Define `PK_RESOURCE_ADJUSTMENT/2` as a formal tagged union for memory adjust, vCPU adjust, memory revert, and vCPU revert.
- ✅ `CL-03-SD-03` Define required vs optional fields, data types, integer ranges, string length limits, patterns, enumerations, and nullability.
- ✅ `CL-03-SD-04` Define `operation_id`, `host`, `guest`, and `tenant` identifier grammar and maximum lengths.
- ✅ `CL-03-SD-05` Define `PK_HOST_RESOURCES/1` formally, including units and invariant relationships among total/reserve/allocated/free memory.
- ✅ `CL-03-SD-06` Define `PK_RESOURCE_AUDIT/1` formally, including hash algorithm identifier, canonicalization rules, sequence semantics, and previous-hash requirements.
- ✅ `CL-03-SD-07` Define a machine-readable structured error envelope covering validation, policy, authentication, authorization, dependency, timeout, conflict, stale state, integrity, and internal failures.
- ✅ `CL-03-SD-08` Assign stable error codes; never require clients to parse human-readable messages.
- ✅ `CL-03-SD-09` Define request/response size limits and maximum batch/fan-out sizes.
- ✅ `CL-03-SD-10` Define timestamp format and clock semantics once timestamps are added.

### WS3 — Compatibility

- 📄 `CL-03-C-01` Document additive vs breaking schema changes.
- ✅ `CL-03-C-02` Define supported major/minor version negotiation.
- ✅ `CL-03-C-03` Define rejection behavior for unknown major versions.
- ✅ `CL-03-C-04` Define handling of unknown optional fields and unknown enum values.
- 📄 `CL-03-C-05` Define legacy `PK_RESOURCE_ADJUSTMENT/1` retirement criteria and sunset date.
- ✅ `CL-03-C-06` Add golden fixtures for every supported schema version.
- ✅ `CL-03-C-07` Add canonical serialization fixtures for audit-hash verification.
- ◐ `CL-03-C-08` Add upgrade/downgrade fixtures across every supported adjacent version pair. — _v1 legacy revert + v2 fixtures only; no adjacent v2/v3 pair exists yet; blocked on: no second supported major exists_

### WS3 — Interface semantics

- ✅ `CL-03-IS-01` Specify request deadline propagation.
- ✅ `CL-03-IS-02` Specify cancellation behavior before mutation, during provider mutation, and after provider confirmation.
- ✅ `CL-03-IS-03` Specify idempotency-key retention period and conflict behavior.
- ✅ `CL-03-IS-04` Specify retryability per error code.
- ✅ `CL-03-IS-05` Specify backpressure signaling and overload status codes.
- 📄 `CL-03-IS-06` Specify ordering guarantees for events and mutations.
- ✅ `CL-03-IS-07` Specify whether concurrent operations on one guest are serialized, rejected, or merged.
- ✅ `CL-03-IS-08` Specify maximum in-flight operations per guest, tenant, host, and controller.

### WS3 — Conformance and fuzzing

- ✅ `CL-03-CAF-01` Generate schema validators in CI.
- ✅ `CL-03-CAF-02` Validate every external request before it reaches mutation logic.
- ✅ `CL-03-CAF-03` Validate every external response/event before publication.
- ✅ `CL-03-CAF-04` Add positive and negative conformance vectors for every field constraint.
- ✅ `CL-03-CAF-05` Fuzz decoders with malformed lengths, nested structures, invalid Unicode, extreme integers, duplicate fields, unknown fields, and truncated payloads.
- ⛔ `CL-03-CAF-06` Test canonical encoding stability across supported language implementations. — _blocked on: only one language implementation exists_
- ✅ `CL-03-CAF-07` Publish a versioned conformance fixture directory consumers can run independently.

### WS4 — Identity model

- ✅ `CL-04-IM-01` Enumerate identities: node, controller, operator, service, tenant, workload, provider, build artifact, and automation principal.
- ✅ `CL-04-IM-02` Define a stable principal identifier format independent of display names.
- ◐ `CL-04-IM-03` Define authentication mechanism per boundary, preferring mutually authenticated transport for service-to-service control paths. — _signed audience-bound credentials implemented; mTLS transport pending; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ⛔ `CL-04-IM-04` Define node identity bootstrap and rotation. — _blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ⛔ `CL-04-IM-05` Define provider/hypervisor identity verification. — _blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ✅ `CL-04-IM-06` Define operator/admin authentication separately from workload identities.
- ✅ `CL-04-IM-07` Define credential lifetime, renewal, revocation, and emergency invalidation.

### WS4 — Authorization model

- ✅ `CL-04-AM-01` Define explicit actions such as `guest.read`, `memory.adjust`, `vcpu.adjust`, `adjustment.revert`, `audit.read`, `host.read`, `quarantine.set`, and `config.activate`.
- ◐ `CL-04-AM-02` Define resource scope for each action: tenant, host, guest, site, environment. — _tenant + host scopes enforced; site/environment scopes not modelled; blocked on: site/environment identity model not supplied_
- ✅ `CL-04-AM-03` Deny by default when no policy matches.
- ✅ `CL-04-AM-04` Prevent a tenant-scoped principal from naming another tenant's guest.
- ✅ `CL-04-AM-05` Require elevated capability for rollback/revert operations because they mutate live state.
- ✅ `CL-04-AM-06` Require separate capabilities for configuration, emergency disable, audit export, and secret access.
- ✅ `CL-04-AM-07` Define break-glass access with stronger authentication, short TTL, mandatory reason, and enhanced audit.
- ✅ `CL-04-AM-08` Prevent capability escalation through user-controlled `reason`, guest IDs, or operation metadata.

### WS4 — Policy enforcement

- ✅ `CL-04-PE-01` Put authorization before any hypervisor lookup that could leak cross-tenant existence where confidentiality requires it.
- ✅ `CL-04-PE-02` Re-check authorization immediately before privileged provider mutation if requests can queue. — _no request queue exists; authz, lease and live state are checked immediately before the provider call_
- ◐ `CL-04-PE-03` Bind authorization decision to immutable request identity and expected target state. — _decision id + request fingerprint + expected version recorded together; not cryptographically bound; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ✅ `CL-04-PE-04` Record policy version, decision ID, principal, requested action, resource, and result in audit events.
- ✅ `CL-04-PE-05` Cache authorization only with bounded TTL and revocation strategy.
- ✅ `CL-04-PE-06` Fail closed when the policy service is unavailable unless a narrowly documented local-safe policy applies.
- ✅ `CL-04-PE-07` Define clock-skew handling for expiring credentials/tokens.

### WS4 — Security verification

- ✅ `CL-04-SV-01` Unit-test allow, deny, missing-credential, expired-credential, wrong-tenant, wrong-host, and revoked-credential paths.
- ✅ `CL-04-SV-02` Test confused-deputy scenarios through controller/provider chains.
- ✅ `CL-04-SV-03` Test token replay and audience/scope mismatch.
- ✅ `CL-04-SV-04` Test cross-tenant enumeration and error-message leakage.
- ✅ `CL-04-SV-05` Test break-glass expiry and audit completeness.
- ✅ `CL-04-SV-06` Run policy mutation tests proving deny-by-default behavior.
- 📄 `CL-04-SV-07` Require security review for any new capability/action added to the API.

### WS5 — Configuration schema

- ✅ `CL-05-CS-01` Define a versioned configuration schema independent of Python constructor defaults.
- ✅ `CL-05-CS-02` Include host reserve policy, guest bounds policy, operation timeouts, retry limits, concurrency limits, audit settings, telemetry settings, provider endpoint, and feature gates.
- ✅ `CL-05-CS-03` Define min/max values for every numeric setting and allowed values for every enum.
- ✅ `CL-05-CS-04` Mark security-critical settings explicitly.
- ✅ `CL-05-CS-05` Define immutable settings that require process restart vs dynamically reloadable settings.
- ✅ `CL-05-CS-06` Provide a hardened default profile that preserves reserve and isolation invariants.
- ✅ `CL-05-CS-07` Prohibit credentials, private keys, tokens, and raw secret values in ordinary config files.

### WS5 — Layering and provenance

- ✅ `CL-05-LAP-01` Define precedence among package defaults, site config, environment config, node config, and emergency override.
- ✅ `CL-05-LAP-02` Reject ambiguous/conflicting overlays rather than silently choosing an arbitrary value.
- ✅ `CL-05-LAP-03` Record config schema version, config revision, content digest, author/issuer, source, approval, and activation timestamp.
- ✅ `CL-05-LAP-04` Make the effective merged configuration inspectable without revealing secrets.
- ✅ `CL-05-LAP-05` Store the exact effective config digest in every relevant audit event.
- ✅ `CL-05-LAP-06` Correlate configuration revision with release version and runtime process identity.

### WS5 — Validation and activation

- ✅ `CL-05-VAA-01` Parse into an immutable validated configuration object before use.
- ✅ `CL-05-VAA-02` Validate cross-field invariants such as reserve fractions, concurrency limits, retry budgets, and retention bounds.
- ✅ `CL-05-VAA-03` Validate provider capability compatibility before activation.
- ✅ `CL-05-VAA-04` Validate that new config cannot make existing guest state illegal without an explicit migration plan.
- ✅ `CL-05-VAA-05` Use a two-phase or transactional activation model: validate/stage, then atomically publish.
- ✅ `CL-05-VAA-06` Ensure readers see either old or new complete configuration, never a partially updated mix.
- ✅ `CL-05-VAA-07` Persist previous known-good revisions for rollback.
- ✅ `CL-05-VAA-08` Auto-rollback when health gates fail within the activation observation window.
- ✅ `CL-05-VAA-09` Support operator-triggered rollback by immutable revision ID.
- ✅ `CL-05-VAA-10` Audit activation, rejection, rollback, and emergency override events.

### WS5 — Secrets separation

- ✅ `CL-05-SS-01` Reference secrets by opaque secret ID/URI, not inline value.
- ◐ `CL-05-SS-02` Retrieve secrets only in the component that requires them. — _SecretResolver resolves secret:// refs at point of use; real secret backend pending; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ✅ `CL-05-SS-03` Keep secret material out of logs, exceptions, metrics labels, crash dumps, and config inspection output.
- ✅ `CL-05-SS-04` Define secret rotation without full service rebuild.
- ✅ `CL-05-SS-05` Test redaction with representative provider/authentication failures.

### WS5 — Bootstrap acceptance

- ◐ `CL-05-BA-01` Starting from an empty supported node, bootstrap must produce a healthy service using only declared artifacts and configuration. — _bootstrap + controller start on an empty directory in tests; real node pending; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ✅ `CL-05-BA-02` Bootstrap must be repeatable and idempotent.
- ✅ `CL-05-BA-03` Invalid security-critical configuration must prevent readiness.
- ✅ `CL-05-BA-04` Configuration rollback must restore the previous digest and healthy state deterministically.

### WS6 — State inventory

- ✅ `CL-06-SI-01` Classify all mutable state: guest registrations, current expected resource state, idempotency records, free-page reports, configuration revision, controller epoch/lease, audit events, quarantine state, and pending operations.
- ✅ `CL-06-SI-02` Mark each state item as authoritative, cache, reconstructible, or ephemeral.
- ✅ `CL-06-SI-03` Define recovery source of truth for each state item.
- ✅ `CL-06-SI-04` Define retention/TTL for idempotency records and diagnostic/free-page data.

### WS6 — Persistence design

- ◐ `CL-06-PD-01` Select a durable store appropriate to single-node vs distributed deployment. — _single-node store selected; distributed store pending ADR-0003; blocked on: Consensus lease store (etcd/ZooKeeper/Consul) not selected (ADR-0003)_
- ✅ `CL-06-PD-02` Define transactional boundaries between state mutation and audit append.
- ✅ `CL-06-PD-03` Ensure a successful external mutation cannot be acknowledged while its recovery record is non-durable.
- ✅ `CL-06-PD-04` Define write-ahead/journal semantics for in-flight hypervisor mutations.
- ✅ `CL-06-PD-05` Persist monotonically increasing state version/epoch per guest.
- ✅ `CL-06-PD-06` Protect against torn writes and partial records.
- ✅ `CL-06-PD-07` Verify checksums/digests on read.
- ⛔ `CL-06-PD-08` Encrypt sensitive persisted data at rest. — _blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ✅ `CL-06-PD-09` Separate high-cardinality telemetry retention from authoritative control state.

### WS6 — Audit hardening

- ◐ `CL-06-AH-01` Persist every accepted and rejected security-sensitive operation, not just successful mutations. — _authn/authz/policy rejections audited; pre-authentication decode failures are logged+counted, not audited (flood resistance); blocked on: design decision pending owner review_
- ◐ `CL-06-AH-02` Add trusted timestamp or monotonic time source metadata. — _wall + monotonic time recorded; trusted time source pending; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ✅ `CL-06-AH-03` Rotate audit segments with bounded size and deterministic linkage.
- ✅ `CL-06-AH-04` Retain chain linkage across rotation boundaries.
- ✅ `CL-06-AH-05` Sign or attest audit segment heads with a managed key or hardware-backed identity where available.
- ◐ `CL-06-AH-06` Periodically anchor audit head externally so a local attacker cannot rewrite the entire chain undetected. — _anchor sink hook implemented; real external sink pending; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ⛔ `CL-06-AH-07` Export to centralized immutable/audited storage. — _blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ◐ `CL-06-AH-08` Define retention, legal/privacy constraints, and secure deletion rules. — _retention defined; legal/privacy constraints pending owner; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ✅ `CL-06-AH-09` Validate the full chain at startup or use verified checkpoints with bounded replay.

### WS6 — Crash/restart semantics

- ✅ `CL-06-CRS-01` Define states for `prepared`, `provider_requested`, `provider_confirmed`, `state_committed`, and `audit_committed` or equivalent.
- ✅ `CL-06-CRS-02` On startup, reconcile every incomplete operation with live hypervisor state.
- ✅ `CL-06-CRS-03` Never replay a non-idempotent provider mutation solely because the local process crashed.
- ✅ `CL-06-CRS-04` Use operation IDs and expected-state versions to distinguish already-applied operations from unapplied operations.
- ✅ `CL-06-CRS-05` Define recovery for lost connectivity during provider mutation.
- ✅ `CL-06-CRS-06` Block readiness if authoritative state integrity cannot be verified.

### WS6 — Backup, restore, and reconstruction

- 📄 `CL-06-BRAR-01` Define backup frequency and recovery-point objective for authoritative state.
- 📄 `CL-06-BRAR-02` Define recovery-time objective and restore sequence.
- ✅ `CL-06-BRAR-03` Test restore into a clean environment.
- ✅ `CL-06-BRAR-04` Reconcile restored expected state with live hypervisor state before enabling writes.
- ◐ `CL-06-BRAR-05` Test point-in-time recovery where supported. — _PITR = restore last backup + re-read live state; journal replay to arbitrary time not supported; blocked on: PITR requires a store with point-in-time capability (ADR-0005)_
- ✅ `CL-06-BRAR-06` Test corrupted database, missing audit segment, stale backup, and partial restore scenarios.
- 📄 `CL-06-BRAR-07` Document when reconstruction from hypervisor plus external audit is permitted and what information is unrecoverable.

### WS7 — Ownership model

- ✅ `CL-07-OM-01` Define the unit of exclusive ownership: host, guest, tenant shard, or resource class.
- ✅ `CL-07-OM-02` Define lease/epoch semantics and the authoritative lease store.
- ✅ `CL-07-OM-03` Assign a monotonically increasing fencing token on ownership acquisition.
- ✅ `CL-07-OM-04` Include fencing token in every privileged provider mutation where the provider can enforce it.
- ✅ `CL-07-OM-05` If the provider cannot enforce fencing, introduce a single-writer gateway or another hard serialization boundary.
- ◐ `CL-07-OM-06` Define ownership transfer, planned drain, failover, and forced takeover procedures. — _planned drain + expiry takeover implemented; forced takeover is a documented operator procedure; blocked on: Consensus lease store (etcd/ZooKeeper/Consul) not selected (ADR-0003)_
- ✅ `CL-07-OM-07` Define maximum lease duration and renewal cadence.

### WS7 — Mutation safety

- ✅ `CL-07-MS-01` Bind every operation to controller instance ID, ownership epoch, guest state version, and operation ID.
- ✅ `CL-07-MS-02` Reject operations from expired/stale epochs even when their operation ID is unique.
- ✅ `CL-07-MS-03` Re-check lease validity immediately before provider mutation and before commit.
- ✅ `CL-07-MS-04` Prevent old controllers from committing state after a newer controller takes ownership.
- ✅ `CL-07-MS-05` Serialize conflicting operations per guest.
- ✅ `CL-07-MS-06` Define safe concurrent behavior for non-conflicting read/report operations.
- ✅ `CL-07-MS-07` Ensure rollback records cannot cross ownership epochs without explicit reconciliation.

### WS7 — Partition and failover behavior

- ✅ `CL-07-PAFB-01` Define whether loss of quorum/network causes read-only, frozen-write, or bounded-local mode.
- ✅ `CL-07-PAFB-02` Prefer preserving isolation/reserve over availability when ownership cannot be proven.
- 📄 `CL-07-PAFB-03` Define site partition and cross-site ownership policy.
- ✅ `CL-07-PAFB-04` Define recovery when two controllers believe they own the same host.
- ✅ `CL-07-PAFB-05` Define provider-side reconciliation after lease expiration.

### WS7 — Verification

- ✅ `CL-07-V-01` Simulate duplicate controller startup against one host.
- ✅ `CL-07-V-02` Simulate network partition between controller and lease store.
- ✅ `CL-07-V-03` Simulate delayed packets from a stale controller after ownership transfer.
- ✅ `CL-07-V-04` Simulate controller crash at each mutation phase.
- ✅ `CL-07-V-05` Prove at most one writer can successfully commit a resource transition for a guest state version.
- ✅ `CL-07-V-06` Audit ownership acquisition, renewal failure, takeover, stale-write rejection, and release.

### WS8 — Health model

- ✅ `CL-08-HM-01` Define liveness separately from readiness.
- ✅ `CL-08-HM-02` Readiness must include state-store health, audit integrity, configuration validity, identity/policy readiness, provider reachability/capability, ownership validity, and required dependency status.
- ✅ `CL-08-HM-03` Define per-operation stall thresholds for memory reclaim, memory grow, and vCPU changes.
- ◐ `CL-08-HM-04` Define host/controller heartbeat thresholds. — _lease renewal is the heartbeat; no separate heartbeat monitor; blocked on: Consensus lease store (etcd/ZooKeeper/Consul) not selected (ADR-0003)_
- ◐ `CL-08-HM-05` Define guest-agent/free-page-report staleness thresholds. — _threshold configured; guest-agent reporting pending provider; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-08-HM-06` Define saturation conditions that make the service temporarily not ready for new mutations. — _admission rejects at saturation; readiness does not flip; blocked on: owner decision: should saturation flip readiness_

### WS8 — Watchdogs and stall handling

- ✅ `CL-08-WASH-01` Track start time, deadline, last progress, provider request ID, and state phase for every in-flight mutation.
- ✅ `CL-08-WASH-02` Detect operations that exceed expected progress without relying only on client timeout.
- ✅ `CL-08-WASH-03` Distinguish provider slowness from local deadlock and dependency outage.
- ✅ `CL-08-WASH-04` Ensure watchdog actions are idempotent and cannot double-rollback.
- ✅ `CL-08-WASH-05` Emit a structured incident signal when a mutation enters an unknown outcome state.

### WS8 — Quarantine / freeze controls

- ✅ `CL-08-QFC-01` Implement per-guest mutation freeze.
- ✅ `CL-08-QFC-02` Implement per-host mutation freeze.
- ✅ `CL-08-QFC-03` Implement per-tenant or shard freeze where multi-tenant blast radius requires it.
- ✅ `CL-08-QFC-04` Implement global emergency disable for new mutations while preserving read/audit access.
- ✅ `CL-08-QFC-05` Keep safety enforcement active during emergency disable; disabling mutation must not disable reserve/floor checks for recovery actions.
- ✅ `CL-08-QFC-06` Require authenticated/authorized operators for manual quarantine changes.
- ✅ `CL-08-QFC-07` Require reason, ticket/incident ID, TTL, and owner for manual quarantine.
- ✅ `CL-08-QFC-08` Auto-expire temporary quarantine only when explicitly safe; otherwise require manual clear.
- ✅ `CL-08-QFC-09` Audit all set/clear operations and current quarantine state.

### WS8 — Acceptance

- ✅ `CL-08-A-01` Health endpoints must never report ready when audit integrity is failed or ownership is stale.
- ✅ `CL-08-A-02` A quarantined guest/host must reject resource mutation with a stable machine-readable code.
- ✅ `CL-08-A-03` Emergency disable must be testable without process restart.
- ⛔ `CL-08-A-04` Canary and rollout procedures must exercise emergency disable and recovery. — _blocked on: Runbooks not yet exercised in a game day (needs a real environment)_
- 📄 `CL-08-A-05` Alerts must distinguish stall, dependency failure, policy rejection, integrity failure, and overload.

### WS9 — Retry taxonomy

- ✅ `CL-09-RT-01` Classify every error code as retryable, conditionally retryable, or terminal.
- ✅ `CL-09-RT-02` Retry only operations proven idempotent or protected by durable operation IDs/expected-state fencing.
- ✅ `CL-09-RT-03` Never automatically retry authorization denial, malformed input, invariant breach, or stale-state conflict without obtaining new state.
- ✅ `CL-09-RT-04` Define maximum attempts, maximum elapsed retry time, base delay, multiplier, maximum delay, and jitter strategy.
- ✅ `CL-09-RT-05` Respect caller deadline; do not retry beyond it.
- ✅ `CL-09-RT-06` Track retry budget per dependency and operation class.

### WS9 — Backpressure and admission

- ✅ `CL-09-BAA-01` Define maximum in-flight mutations per guest.
- ✅ `CL-09-BAA-02` Define maximum in-flight mutations per host.
- ✅ `CL-09-BAA-03` Define maximum per-tenant concurrency to prevent noisy-neighbor control-plane abuse.
- ✅ `CL-09-BAA-04` Define queue depth and queue wait-time limits.
- ✅ `CL-09-BAA-05` Prefer reject/redirect over unbounded queuing.
- ✅ `CL-09-BAA-06` Reject new low-priority adjustments when provider/state-store saturation crosses threshold.
- ✅ `CL-09-BAA-07` Reserve capacity for safety/recovery operations so normal load cannot starve emergency rollback/quarantine.
- ✅ `CL-09-BAA-08` Define overload response codes and `retry-after`/backoff hints where applicable.

### WS9 — Circuit breaking

- ✅ `CL-09-CB-01` Maintain dependency-specific health/error windows.
- ✅ `CL-09-CB-02` Open the circuit on sustained provider/state-store/policy failures.
- ✅ `CL-09-CB-03` Define half-open probe behavior.
- ✅ `CL-09-CB-04` Prevent all controllers from probing simultaneously after an outage by adding jitter.
- ◐ `CL-09-CB-05` Keep circuit state observable and auditable. — _state observable via inventory/metrics/logs; transitions not written to audit; blocked on: owner decision: audit circuit transitions_

### WS9 — Verification

- ✅ `CL-09-V-01` Load-test at and beyond configured concurrency/queue limits.
- ✅ `CL-09-V-02` Simulate dependency 5xx/unavailable/timeouts and verify bounded retry count.
- ✅ `CL-09-V-03` Verify duplicate external calls cannot produce duplicate resource mutation.
- ✅ `CL-09-V-04` Verify queue memory remains bounded under overload.
- ✅ `CL-09-V-05` Verify high-priority safety actions remain serviceable under normal-load saturation.
- ✅ `CL-09-V-06` Verify recovery does not create a thundering-herd retry spike.

### WS10 — Outcome taxonomy

- ✅ `CL-10-OT-01` Define machine-readable outcomes: success, partial success, degraded success, rejected, retryable failure, terminal failure, unknown outcome, and rolled back.
- ✅ `CL-10-OT-02` Define which outcomes may be returned after a provider reports partial application.
- ✅ `CL-10-OT-03` Define whether partial success requires immediate compensation, operator intervention, or reconciliation loop.
- ✅ `CL-10-OT-04` Ensure human-readable messages do not substitute for outcome codes.

### WS10 — Failure catalog

- 📄 `CL-10-FC-01` Enumerate local process crash, thread/task deadlock, state-store outage, state-store corruption, audit corruption, provider timeout, provider restart, guest-agent stall, guest crash, VM pause, VM migration, host reboot, host pressure, node isolation, site loss, controller partition, identity outage, policy outage, key service outage, clock/time failure, telemetry outage, and dependency version mismatch.
- 📄 `CL-10-FC-02` For each failure, document detection signal, safety risk, allowed operations, automatic recovery, manual recovery, escalation, and data-loss potential.
- 📄 `CL-10-FC-03` Define behavior for intermittent or absent network separately for control-plane, provider, state-store, and telemetry paths.
- 📄 `CL-10-FC-04` Define a precedence matrix: security/integrity > isolation/residency > state correctness > SLO/availability > cost/efficiency unless governance explicitly approves another ordering.

### WS10 — Degraded modes

- ✅ `CL-10-DM-01` Define read-only mode.
- ✅ `CL-10-DM-02` Define freeze-new-mutations mode.
- ◐ `CL-10-DM-03` Define local-safe mode only if ownership and state integrity remain provable. — _LOCAL_SAFE defined; no separate local agent API; blocked on: Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied_
- 📄 `CL-10-DM-04` Define behavior when telemetry is unavailable but control remains healthy.
- ◐ `CL-10-DM-05` Define behavior when external audit export is unavailable but local durable audit remains healthy. — _anchors retained locally when sink fails; no EXPORT_DOWN health flag; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- 📄 `CL-10-DM-06` Define behavior when optional free-page reporting is unavailable.
- 📄 `CL-10-DM-07` Define exit criteria from each degraded mode.

### WS10 — Failover and recovery

- 📄 `CL-10-FAR-01` Define state required before another controller may take ownership.
- ✅ `CL-10-FAR-02` Reconcile live hypervisor state before resuming writes after failover.
- ✅ `CL-10-FAR-03` Preserve residency/tenant constraints during failover.
- 📄 `CL-10-FAR-04` Do not move or control guests from another site solely to improve availability unless policy authorizes it.
- ◐ `CL-10-FAR-05` Record failover reason, old/new owner, epoch, reconciled state, and anomalies. — _ownership_acquired + reconciled events recorded; no single 'failover' event with old owner; blocked on: Consensus lease store (etcd/ZooKeeper/Consul) not selected (ADR-0003)_

### WS10 — Fault-injection acceptance

- ◐ `CL-10-FIA-01` Inject each cataloged failure at pre-mutation, mid-mutation, post-provider/pre-commit, and post-commit phases where applicable. — _11 of 20 catalog failures injected; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ◐ `CL-10-FIA-02` Define expected invariant outcome for every injection point. — _invariant asserted for injected cases; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ✅ `CL-10-FIA-03` Assert host reserve and guest floor are never violated by recovery logic.
- ✅ `CL-10-FIA-04` Assert no stale controller can commit after takeover.
- ✅ `CL-10-FIA-05` Assert unknown outcomes remain blocked from blind retry until reconciled.
- ✅ `CL-10-FIA-06` Store fault-test results as release evidence.

### WS11 — Benchmark specification

- ⛔ `CL-11-BS-01` Define benchmark hardware classes and record CPU model, NUMA topology, memory size/speed, storage, NIC, hypervisor, kernel, firmware, and power mode. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ◐ `CL-11-BS-02` Define benchmark software matrix: Python/runtime, package version, HyperFlux/provider version, guest OS/agent version. — _Python/platform/package recorded; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-11-BS-03` Separate controller decision latency, serialization latency, RPC latency, provider execution latency, guest cooperation latency, and end-to-end latency. — _decision/provider/e2e separated; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-11-BS-04` Measure cold-start and warm-start paths separately. — _cold start recorded; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ◐ `CL-11-BS-05` Measure single-guest and many-guest density. — _guest count parameter; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ✅ `CL-11-BS-06` Measure memory grow, memory reclaim, vCPU add, vCPU remove, rollback, snapshot query, and audit append independently.

### WS11 — Latency/throughput objectives

- ✅ `CL-11-LTO-01` Define p50, p95, p99, p99.9 where sample size supports it, and maximum/worst-case bounds for each operation class.
- ✅ `CL-11-LTO-02` Define throughput in accepted mutations/s and reconciliations/s per host/controller.
- ◐ `CL-11-LTO-03` Define startup/readiness target. — _cold start measured; target not approved; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-11-LTO-04` Define maximum controller CPU and RSS overhead at idle and target load. — _max RSS measured; CPU target not approved; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ✅ `CL-11-LTO-05` Define maximum bytes/op for persisted state and telemetry.
- ✅ `CL-11-LTO-06` Explicitly state which portion of “microsecond-scale” is under this component's control and which is provider/guest bound.

### WS11 — Load scenarios

- ◐ `CL-11-LS-01` Steady-state load at 25/50/75/100% target throughput. — _single load level; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-11-LS-02` Burst load above target throughput.
- ✅ `CL-11-LS-03` Sustained overload until load shedding/circuit breaking activates.
- ◐ `CL-11-LS-04` Rapid scale-out and scale-in of guest count. — _guest creation in fixtures only; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-11-LS-05` Concurrent operations across many tenants.
- ✅ `CL-11-LS-06` Hot-spot workload targeting one host/guest.
- ◐ `CL-11-LS-07` Recovery after provider/state-store outage. — _crash recovery only; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ◐ `CL-11-LS-08` Audit rotation/checkpoint load. — _rotation in unit tests only; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ◐ `CL-11-LS-09` Configuration reload/rollout under traffic. — _reload tested for atomicity without traffic; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_

### WS11 — Efficiency analysis

- ✅ `CL-11-EA-01` Profile serialization/deserialization overhead.
- ◐ `CL-11-EA-02` Measure memory copies and data structure allocation on hot paths. — _allocation findings via profiling only; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ⛔ `CL-11-EA-03` Measure lock contention and context switches. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- 📄 `CL-11-EA-04` Measure provider/control-plane network hops.
- ✅ `CL-11-EA-05` Identify duplicate state snapshots and redundant queries.
- 📄 `CL-11-EA-06` Evaluate batching only where it does not weaken per-guest isolation or latency guarantees.
- 📄 `CL-11-EA-07` Evaluate zero-copy/direct I/O/kernel-bypass only after profiling demonstrates material benefit.
- ✅ `CL-11-EA-08` Preserve a reference implementation path so optimization cannot bypass safety checks.

### WS11 — Capacity model

- 📄 `CL-11-CM-01` Model max guests/host, operations/second, audit growth/hour, state-store IOPS, queue capacity, and controller CPU/memory.
- 📄 `CL-11-CM-02` Define saturation signals and warning/critical thresholds.
- ✅ `CL-11-CM-03` Define headroom required for recovery and emergency operations.
- 📄 `CL-11-CM-04` Define tenant density limits and fairness interaction.
- ⛔ `CL-11-CM-05` Validate model predictions against load tests. — _blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_

### WS11 — Power and thermal

- ⛔ `CL-11-PAT-01` On edge-class hardware, record energy/op and sustained controller power overhead where measurement is practical. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ⛔ `CL-11-PAT-02` Measure thermal throttling impact on tail latency. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ⛔ `CL-11-PAT-03` Correlate performance results with frequency/power state. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ⛔ `CL-11-PAT-04` Define whether resource reallocation must pause or degrade under thermal constraints supplied by upstream scheduling. — _blocked on: Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied_

### WS11 — CI release gates

- ✅ `CL-11-CRG-01` Store benchmark baselines as versioned machine-readable data.
- ✅ `CL-11-CRG-02` Fail release qualification on statistically/materially significant regression beyond approved thresholds.
- ✅ `CL-11-CRG-03` Require explicit waiver with owner/expiry for accepted regressions.
- ✅ `CL-11-CRG-04` Preserve raw benchmark artifacts and environment metadata for reproducibility.

### WS12 — Health and inventory surfaces

- ✅ `CL-12-HAIS-01` Expose liveness and readiness separately.
- ✅ `CL-12-HAIS-02` Expose build/version, schema versions, config revision/digest, provider version/capabilities, controller epoch, dependency health, and active feature gates.
- ✅ `CL-12-HAIS-03` Do not expose secrets, raw tokens, private keys, or unrestricted cross-tenant guest identifiers.

### WS12 — Metrics

- ✅ `CL-12-M-01` Counter: requests by operation type and outcome.
- ✅ `CL-12-M-02` Histogram: decision latency, provider latency, end-to-end latency, queue wait, reconciliation latency.
- ✅ `CL-12-M-03` Gauge: in-flight operations, queue depth, guest count, allocated/free/reserved memory, audit backlog, state-store health, ownership lease age.
- ✅ `CL-12-M-04` Counter: reserve refusals, floor refusals, authorization denials, stale-state conflicts, replay conflicts, guest refusal, timeouts, retries, circuit opens, quarantines, audit-integrity failures.
- ✅ `CL-12-M-05` Define metric units and stable names.
- ✅ `CL-12-M-06` Avoid unbounded tenant/guest IDs as metric labels; use controlled aggregation or exemplars.

### WS12 — Structured logging

- ✅ `CL-12-SL-01` Emit JSON or equivalent structured logs with timestamp, severity, component, host, tenant-safe identifier, guest-safe identifier, operation ID, trace ID, controller epoch, config digest, and outcome code.
- ✅ `CL-12-SL-02` Separate operator message from machine-readable fields.
- ✅ `CL-12-SL-03` Redact secrets and sensitive provider diagnostics.
- ✅ `CL-12-SL-04` Define log severity policy.
- ✅ `CL-12-SL-05` Log every rejected security-sensitive request at an appropriate level with safe reason code.
- ✅ `CL-12-SL-06` Correlate logs with the audit event sequence/hash without duplicating sensitive payloads.

### WS12 — Distributed tracing

- ✅ `CL-12-DT-01` Adopt a trace-context standard at RPC boundaries.
- ◐ `CL-12-DT-02` Propagate trace/span context through controller → policy/state → provider adapter calls. — _propagated through controller spans; provider hop pending; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ✅ `CL-12-DT-03` Create spans for authorization, state read, decision, provider mutation, verification, commit, and audit append.
- ✅ `CL-12-DT-04` Record outcome/error code and latency attributes.
- ✅ `CL-12-DT-05` Apply sampling rules that retain errors and high-latency traces while bounding cost.
- ✅ `CL-12-DT-06` Ensure trace baggage cannot inject untrusted high-cardinality or secret data.

### WS12 — Explainability

- ✅ `CL-12-E-01` Persist structured decision inputs: requested change, current state version, floor/ceiling, host reserve/free memory, policy revision, capability set, ownership epoch, and selected outcome.
- ✅ `CL-12-E-02` Provide an operator explain endpoint/command keyed by operation ID.
- ✅ `CL-12-E-03` Show why a target was clamped or rejected.
- ✅ `CL-12-E-04` Show which policy/invariant controlled the decision.
- ✅ `CL-12-E-05` Show whether result came from replay/idempotency cache.
- ✅ `CL-12-E-06` Link decision to release/build, config revision, and infrastructure/guest identity.

### WS12 — Retention/privacy/export

- 📄 `CL-12-RPE-01` Define retention by telemetry class.
- 📄 `CL-12-RPE-02` Define sampling policy and high-cardinality limits.
- 📄 `CL-12-RPE-03` Define tenant privacy and access rules for diagnostics.
- ◐ `CL-12-RPE-04` Define export destination, transport security, buffering, and outage behavior. — _policy defined; export destination not deployed; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- 📄 `CL-12-RPE-05` Define deletion requirements and auditability of deletion where applicable.

### WS12 — Dashboards and alerts

- ◐ `CL-12-DAA-01` Dashboard: host resource safety/invariants. — _definition authored; not deployed to a dashboard backend; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ◐ `CL-12-DAA-02` Dashboard: operation rate/latency/errors/saturation. — _definition authored; not deployed to a dashboard backend; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ◐ `CL-12-DAA-03` Dashboard: provider/dependency health. — _definition authored; not deployed to a dashboard backend; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ◐ `CL-12-DAA-04` Dashboard: controller ownership/failover. — _definition authored; not deployed to a dashboard backend; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ◐ `CL-12-DAA-05` Dashboard: security denials/integrity/quarantine. — _definition authored; not deployed to a dashboard backend; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- 📄 `CL-12-DAA-06` Alerts must distinguish ordinary load, overload, dependency outage, policy rejection, attack signal, software defect, state corruption, and audit corruption.
- 📄 `CL-12-DAA-07` Every page-worthy alert must link to a runbook and include scope/blast-radius fields.

### WS13 — Threat model

- 📄 `CL-13-TM-01` Identify assets: guest resources, host availability, controller authority, tenant isolation, audit integrity, config, secrets, provider credentials, software artifacts, and state store.
- 📄 `CL-13-TM-02` Draw trust boundaries among caller/controller, policy, state store, provider/hypervisor, guest agent, telemetry, artifact registry, and operators.
- 📄 `CL-13-TM-03` Enumerate threat actors: malicious tenant, compromised guest, compromised controller, malicious operator, compromised dependency, supply-chain attacker, network attacker, and stale controller.
- 📄 `CL-13-TM-04` Analyze spoofing, tampering, repudiation, information disclosure, denial of service, privilege escalation, replay, and side channels.
- 📄 `CL-13-TM-05` Map every threat to preventive, detective, and recovery controls.
- ◐ `CL-13-TM-06` Assign residual risk, owner, and review date. — _residual risk + review date assigned; owner unassigned; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_

### WS13 — Least privilege and ambient authority removal

- 📄 `CL-13-LPAAA-01` Run the service as a dedicated non-admin identity wherever provider requirements permit.
- 📄 `CL-13-LPAAA-02` Grant only required device/socket/API access.
- 📄 `CL-13-LPAAA-03` Deny arbitrary filesystem traversal; scope read/write directories explicitly.
- 📄 `CL-13-LPAAA-04` Deny general outbound network access when only fixed provider/state/policy endpoints are required.
- ✅ `CL-13-LPAAA-05` Isolate secret access by purpose and identity.
- ✅ `CL-13-LPAAA-06` Avoid shell execution in privileged paths; if unavoidable, use fixed executable paths and argument arrays without shell interpolation.
- ✅ `CL-13-LPAAA-07` Prevent caller-controlled paths, module names, or provider endpoints unless allowlisted.

### WS13 — Artifact and supply-chain trust

- ✅ `CL-13-AASCT-01` Verify release digest before deployment.
- ◐ `CL-13-AASCT-02` Verify signature/provenance for package, policy bundle, configuration bundle, and provider adapter artifacts. — _HMAC-signed manifest; policy/config bundles unsigned; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ◐ `CL-13-AASCT-03` Require approved version allowlist. — _provider allowlist empty until spec; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ✅ `CL-13-AASCT-04` Generate and verify SBOM.
- ◐ `CL-13-AASCT-05` Scan dependencies for known vulnerabilities and license policy issues. — _no runtime deps; license undecided; blocked on: License choice is an owner decision_
- ◐ `CL-13-AASCT-06` Record builder identity and source revision in provenance. — _builder identity env + git commit captured when available; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ⛔ `CL-13-AASCT-07` Protect CI/release credentials with short-lived scoped identities. — _blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_

### WS13 — Isolation

- ✅ `CL-13-I-01` Validate tenant ownership before guest lookup/mutation.
- ⛔ `CL-13-I-02` Verify hypervisor isolation assumptions for memory, CPU, device, and network boundaries. — _blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ✅ `CL-13-I-03` Prevent one tenant's growth from consuming another tenant's guaranteed allocation.
- ✅ `CL-13-I-04` Treat guest-reported free pages as untrusted advisory input.
- ✅ `CL-13-I-05` Bound and validate all guest/provider-reported numeric values.
- ✅ `CL-13-I-06` Test VM identifier reuse and stale cache attacks.
- ◐ `CL-13-I-07` Ensure provider adapter cannot mutate arbitrary host resources outside assigned scope. — _fake adapter scoped to its guests; real adapter pending; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_

### WS13 — Encryption and key management

- ⛔ `CL-13-EAKM-01` Encrypt all remote control-plane traffic. — _blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ⛔ `CL-13-EAKM-02` Encrypt durable authoritative state and sensitive audit data at rest. — _blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ◐ `CL-13-EAKM-03` Use managed keys with rotation and revocation. — _kid rotation/retire implemented; managed KMS pending; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- 📄 `CL-13-EAKM-04` Define behavior during key service outage.
- ◐ `CL-13-EAKM-05` Define certificate/key expiry alerts before service impact. — _alert defined; cert exporter pending; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ✅ `CL-13-EAKM-06` Never log plaintext key material or bearer tokens.

### WS13 — Adversarial testing

- ✅ `CL-13-AT-01` Privilege-escalation tests.
- ✅ `CL-13-AT-02` Cross-tenant authorization tests.
- ✅ `CL-13-AT-03` Parser/schema injection and malformed payload tests.
- ✅ `CL-13-AT-04` Replay and stale-record attacks.
- ◐ `CL-13-AT-05` Node/controller/provider spoofing tests. — _controller/credential spoofing tested; node/provider spoofing pending; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ⛔ `CL-13-AT-06` Hypervisor escape assumptions review and environment hardening validation. — _blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-13-AT-07` Resource exhaustion: IDs, history, queue, connection, CPU, memory, audit volume. — _IDs/size/queue/tenant table bounded; connection/CPU not; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ◐ `CL-13-AT-08` Side-channel review for timing/error differences that reveal cross-tenant state. — _identical errors for missing vs foreign guest; timing not measured; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ✅ `CL-13-AT-09` Audit-chain tampering and persistence-layer tampering tests.
- ✅ `CL-13-AT-10` Security regression suite must run in CI for release candidates.

### WS14 — Test architecture

- 📄 `CL-14-TA-01` Define test tiers: pure unit, contract/schema, adapter simulation, single-host integration, multi-controller integration, security, fuzz, performance, soak, disaster, and release acceptance.
- ◐ `CL-14-TA-02` Make every tier independently runnable with documented prerequisites. — _unit/contract/fault/security/fuzz/bench tiers runnable; integration tiers need infra; blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ✅ `CL-14-TA-03` Use deterministic seeds and record environment metadata.
- 📄 `CL-14-TA-04` Isolate destructive hypervisor tests to disposable infrastructure.

### WS14 — Adjacent-layer integration

- ◐ `CL-14-ALI-01` Test upstream virtualization-controller request flow. — _request flow simulated in-process; blocked on: Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied_
- ⛔ `CL-14-ALI-02` Test elasticity-plane capacity-target flow. — _blocked on: Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied_
- ⛔ `CL-14-ALI-03` Test power/thermal ceiling input. — _blocked on: Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied_
- ⛔ `CL-14-ALI-04` Test downstream microVM runtime/provider integration. — _blocked on: Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied_
- ◐ `CL-14-ALI-05` Test state store, identity, policy, secret/key, audit export, and telemetry dependencies. — _fake dependencies only; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ◐ `CL-14-ALI-06` Verify version negotiation and error propagation across each boundary. — _schema major negotiation + error envelope; blocked on: Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied_

### WS14 — Compatibility matrix

- ⛔ `CL-14-CM-01` CPU architecture matrix for all supported architectures. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ⛔ `CL-14-CM-02` Hypervisor/provider version matrix. — _blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ⛔ `CL-14-CM-03` Guest OS/kernel/agent matrix. — _blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-14-CM-04` Python/runtime version matrix. — _CI matrix 3.10-3.13 declared; executed locally on 3.11; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-14-CM-05` Protocol/schema version matrix.
- ◐ `CL-14-CM-06` State-store version matrix. — _single store format version; blocked on: only one store version exists_
- ⛔ `CL-14-CM-07` Cross-version rolling-upgrade matrix N↔N-1 as policy allows. — _blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ◐ `CL-14-CM-08` Mark unsupported combinations explicitly and test that activation rejects them. — _unsupported provider + old Python rejected; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_

### WS14 — Fuzz testing

- ✅ `CL-14-FT-01` Fuzz all external schema decoders.
- ✅ `CL-14-FT-02` Fuzz rollback records and audit import/verification paths.
- ✅ `CL-14-FT-03` Fuzz identifier lengths/Unicode/control characters.
- ✅ `CL-14-FT-04` Fuzz numeric boundaries and overflow-adjacent values.
- ✅ `CL-14-FT-05` Fuzz sequence/hash fields and canonicalization.
- ◐ `CL-14-FT-06` Persist minimizing reproducers for every discovered crash/invariant violation. — _deterministic seeds make every case reproducible; no crash found to minimise; blocked on: no fuzz crash found yet_
- ◐ `CL-14-FT-07` Convert each fixed fuzz finding into a regression test. — _concurrency test finding (reserve race) converted to regression; blocked on: no fuzz crash found yet_

### WS14 — Fault/disaster testing

- ✅ `CL-14-FDT-01` Kill controller process at every mutation phase.
- ✅ `CL-14-FDT-02` Restart provider/hypervisor during mutation.
- ✅ `CL-14-FDT-03` Partition controller from state store.
- ✅ `CL-14-FDT-04` Partition controller from provider.
- ✅ `CL-14-FDT-05` Partition controllers from each other/lease service.
- ✅ `CL-14-FDT-06` Inject corrupt state/audit entries.
- ◐ `CL-14-FDT-07` Revoke/expire credentials mid-operation. — _revocation between requests tested; mid-operation revocation not; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ◐ `CL-14-FDT-08` Simulate time skew/time-service outage. — _skew window tested; time-service outage not; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ⛔ `CL-14-FDT-09` Simulate site failover and reconnect. — _blocked on: Consensus lease store (etcd/ZooKeeper/Consul) not selected (ADR-0003)_
- ✅ `CL-14-FDT-10` Verify post-recovery reconciliation before writes resume.

### WS14 — Soak and fleet scale

- ⛔ `CL-14-SAFS-01` Run sustained mutation/reconciliation workload for a duration sufficient to expose leaks/rotation defects. — _blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ◐ `CL-14-SAFS-02` Verify bounded memory, queue, idempotency store, and audit growth. — _bounded structures by construction + pruning; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ⛔ `CL-14-SAFS-03` Test thousands of guest identities or the documented maximum scale target. — _blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ◐ `CL-14-SAFS-04` Verify fairness and no starvation under multi-tenant contention. — _400-op randomised two-tenant property test; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ⛔ `CL-14-SAFS-05` Capture latency distribution drift over soak duration. — _blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_

### WS14 — Certification evidence

- ◐ `CL-14-CE-01` Emit machine-readable results per test tier. — _unittest summary JSON per run; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ◐ `CL-14-CE-02` Record source commit, build digest, dependency lock digest, config digest, environment, start/end time, and result. — _commit/lock/env captured when available; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-14-CE-03` Require all P0/P1 mandatory suites green before production certification.

### WS15 — Requirement specification

- 📄 `CL-15-RS-01` Rewrite the core function as SHALL-level statements with stable requirement IDs.
- 📄 `CL-15-RS-02` Define memory adjustment functional requirements.
- 📄 `CL-15-RS-03` Define vCPU adjustment functional requirements.
- 📄 `CL-15-RS-04` Define rollback/reconciliation requirements.
- 📄 `CL-15-RS-05` Define host reserve and guest floor invariants.
- 📄 `CL-15-RS-06` Define cloud/datacenter/near-edge/far-edge applicability and exclusions.
- 📄 `CL-15-RS-07` Define latency, availability, durability, consistency, isolation, determinism, and recovery objectives.
- 📄 `CL-15-RS-08` Define success/partial/degraded/retryable/terminal semantics.
- 📄 `CL-15-RS-09` Define lifecycle states and legal transitions.
- 📄 `CL-15-RS-10` Define capacity/quota/fairness requirements.
- 📄 `CL-15-RS-11` Define disconnected/intermittent-network behavior.
- 📄 `CL-15-RS-12` Define precedence among security, residency, correctness, SLO, and cost constraints.

### WS15 — Traceability matrix

- ✅ `CL-15-TM-01` Create a version-controlled machine-readable RTM (JSON/YAML/CSV) with one row/object per requirement.
- ✅ `CL-15-TM-02` Include requirement ID, text, rationale, priority, owner, implementation path/symbol, schema/API reference, test IDs, operational evidence, status, and waiver ID if any.
- ✅ `CL-15-TM-03` Prevent duplicate requirement IDs.
- ✅ `CL-15-TM-04` Fail CI when a mandatory requirement has no implementation reference.
- ✅ `CL-15-TM-05` Fail CI when a mandatory requirement has no automated verification reference unless explicitly marked manual with approval.
- ✅ `CL-15-TM-06` Validate referenced files/tests exist.
- ✅ `CL-15-TM-07` Link audit controls (`INV-32-Cxxx`) to engineering requirements.

### WS15 — Acceptance evidence manifest

- ✅ `CL-15-AEM-01` Generate a release evidence manifest in JSON.
- ◐ `CL-15-AEM-02` Include release version, source commit, artifact digests, SBOM digest, provenance signature, dependency lock digest, schema versions, config schema version, compatibility matrix version, test suite results, benchmark result IDs, security scan result IDs, and approval records. — _all fields emitted; approvals/provenance empty; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-15-AEM-03` Sign the evidence manifest. — _HMAC reference signature; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ◐ `CL-15-AEM-04` Store it with immutable release artifacts. — _stored beside local build; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ⛔ `CL-15-AEM-05` Make production deployment tooling verify the manifest before promotion. — _blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_

### WS15 — Production exit gate

- ✅ `CL-15-PEG-01` Gate architecture approval. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-02` Gate requirements/RTM completeness. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-03` Gate interface/schema compatibility. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-04` Gate security/threat-model controls. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-05` Gate resilience/fault evidence. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-06` Gate performance regression thresholds. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-07` Gate observability/readiness. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-08` Gate rollback/emergency-disable rehearsal. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-09` Gate operational ownership/on-call readiness. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-10` Gate open waiver count/severity/expiry. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_
- ✅ `CL-15-PEG-11` Produce a single machine-readable PASS/FAIL certification result with reasons. — _gate check implemented; current result FAIL (see evidence/exit_gate.json)_

### WS16 — Ownership

- ⛔ `CL-16-O-01` Name an accountable service owner/team. — _blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ⛔ `CL-16-O-02` Name security owner and operations/on-call owner. — _blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- 📄 `CL-16-O-03` Define escalation chain for availability, integrity, security, and tenant-isolation incidents.
- 📄 `CL-16-O-04` Define ownership boundaries with virtualization controller, elasticity plane, thermal scheduler, and microVM runtime teams.
- ◐ `CL-16-O-05` Define review cadence and backup/deputy ownership. — _cadence defined; deputy unnamed; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_

### WS16 — Architecture decision record

- 📄 `CL-16-ADR-01` Create an ADR for selecting HyperFlux/provider architecture.
- 📄 `CL-16-ADR-02` Record problem statement, constraints, alternatives considered, decision, consequences, failure assumptions, and rollback/migration strategy.
- 📄 `CL-16-ADR-03` Record why microsecond-scale reassignment is required and where that budget is measured.
- 📄 `CL-16-ADR-04` Record single-controller vs distributed-controller design decision.
- 📄 `CL-16-ADR-05` Record durable state technology choice.
- 📄 `CL-16-ADR-06` Record identity/authz and schema technology choices.
- 📄 `CL-16-ADR-07` Require re-review on major provider/protocol/state-model change.

### WS16 — Incident management

- 📄 `CL-16-IM-01` Define severity levels with concrete triggers: reserve violation risk, cross-tenant mutation, audit corruption, widespread mutation failure, performance degradation, telemetry-only issue, etc.
- 📄 `CL-16-IM-02` Define paging targets and escalation time limits.
- 📄 `CL-16-IM-03` Define initial containment actions: emergency disable, host quarantine, credential revoke, controller drain, provider isolation.
- 📄 `CL-16-IM-04` Define evidence preservation steps.
- ◐ `CL-16-IM-05` Define customer/tenant communication ownership where applicable. — _owner role assigned; person unnamed; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- 📄 `CL-16-IM-06` Define recovery validation before clearing incident state.
- 📄 `CL-16-IM-07` Require post-incident review for qualifying incidents.
- 📄 `CL-16-IM-08` Track corrective actions to closure.

### WS16 — Recurring governance

- ◐ `CL-16-RG-01` Schedule access review. — _cadence defined; not scheduled in a calendar/ticket system; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-16-RG-02` Schedule authorization/policy review. — _cadence defined; not scheduled in a calendar/ticket system; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-16-RG-03` Schedule dependency/vulnerability review. — _cadence defined; not scheduled in a calendar/ticket system; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-16-RG-04` Schedule configuration/defaults review. — _cadence defined; not scheduled in a calendar/ticket system; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-16-RG-05` Schedule architecture/threat-model review. — _cadence defined; not scheduled in a calendar/ticket system; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-16-RG-06` Schedule SLO/capacity/benchmark review. — _cadence defined; not scheduled in a calendar/ticket system; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-16-RG-07` Record completion and findings in durable governance evidence. — _cadence defined; not scheduled in a calendar/ticket system; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_

### WS16 — Exceptions, waivers, and technical debt

- ✅ `CL-16-EWATD-01` Use a structured waiver record with ID, requirement/control, rationale, risk, compensating controls, owner, approver, issue link, creation date, expiry date, and renewal limit.
- ✅ `CL-16-EWATD-02` Block expired waivers in release qualification.
- 📄 `CL-16-EWATD-03` Track deprecated schemas/behaviors with removal version/date.
- 📄 `CL-16-EWATD-04` Track technical debt that can weaken safety, isolation, or recovery separately from ordinary backlog work.
- ✅ `CL-16-EWATD-05` Surface high-risk/open waivers in production exit review.

### WS17 — Version policy

- 📄 `CL-17-VP-01` Define semantic/versioning policy for the Python package.
- 📄 `CL-17-VP-02` Define schema/protocol versioning policy independently from package version.
- 📄 `CL-17-VP-03` Define support window for current and previous versions.
- 📄 `CL-17-VP-04` Define legacy `PK_RESOURCE_ADJUSTMENT/1` deprecation and removal plan.
- 📄 `CL-17-VP-05` Define minimum supported Python/runtime version.

### WS17 — Matrix

- ✅ `CL-17-M-01` Matrix columns: INV-32 package, HyperFlux/provider, hypervisor, `pk_core`, Python/runtime, guest agent, state store, schema/API, OS/kernel, CPU architecture.
- ✅ `CL-17-M-02` Mark each combination supported, conditionally supported, deprecated, experimental, or unsupported.
- ✅ `CL-17-M-03` Record required feature flags/capabilities per combination.
- ✅ `CL-17-M-04` Record known limitations and migration notes.
- ✅ `CL-17-M-05` Version-control the matrix and include its digest in release evidence.

### WS17 — Mixed-version behavior

- 📄 `CL-17-MVB-01` Define peer negotiation behavior for N/N-1.
- 📄 `CL-17-MVB-02` Define rolling-upgrade order for controllers/providers/state schema.
- 📄 `CL-17-MVB-03` Define when a new controller may write a new schema version.
- 📄 `CL-17-MVB-04` Define downgrade safety and irreversible migrations.
- ◐ `CL-17-MVB-05` Prevent activation when a required peer/provider version is outside policy. — _provider version allowlist gate; peer versions not negotiated; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ✅ `CL-17-MVB-06` Test unknown newer fields and older peers according to compatibility policy.

### WS17 — Patching and EOL

- 📄 `CL-17-PAE-01` Define vulnerability severity classes and patch SLAs.
- 📄 `CL-17-PAE-02` Define emergency out-of-band release process.
- 📄 `CL-17-PAE-03` Define dependency update cadence.
- 📄 `CL-17-PAE-04` Define end-of-support and end-of-life notice periods.
- ◐ `CL-17-PAE-05` Define behavior for unsupported versions in bootstrap/readiness checks. — _Python floor enforced; matrix-driven EOL check not wired; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- 📄 `CL-17-PAE-06` Require explicit waiver for production use past EOL.

### WS18 — Resource model

- ◐ `CL-18-RM-01` Define tenant memory guarantee, soft target, hard cap, and burst allowance. — _guarantee + hard cap; soft target/burst not modelled; blocked on: tenant SLA model not supplied_
- ◐ `CL-18-RM-02` Define tenant vCPU guarantee/cap. — _vCPU cap; no vCPU guarantee; blocked on: tenant SLA model not supplied_
- ✅ `CL-18-RM-03` Define per-guest floor/ceiling relationship to tenant-level limits.
- ✅ `CL-18-RM-04` Define host reserve as non-allocatable before tenant distribution.
- ✅ `CL-18-RM-05` Define whether unused tenant entitlement is borrowable and under what reclaim rules.
- ✅ `CL-18-RM-06` Define priority classes if supported.

### WS18 — Fairness algorithm

- ✅ `CL-18-FA-01` Select and document fairness model: weighted share, dominant-resource fairness, strict quota, or approved alternative.
- ✅ `CL-18-FA-02` Define deterministic tie-breaking.
- ✅ `CL-18-FA-03` Prevent a high-frequency requester from monopolizing mutation slots.
- ✅ `CL-18-FA-04` Define reclaim order when host pressure requires reduction.
- ✅ `CL-18-FA-05` Never violate a guest working-set floor solely to satisfy fairness.
- ◐ `CL-18-FA-06` Define starvation bounds for queued eligible operations. — _no queue: eligible requests are admitted or rejected immediately; blocked on: owner decision: bounded waiting vs reject_

### WS18 — Control-plane quotas

- ✅ `CL-18-CPQ-01` Rate-limit requests per tenant/principal.
- ✅ `CL-18-CPQ-02` Limit in-flight mutations per tenant.
- ✅ `CL-18-CPQ-03` Limit queued operations per tenant.
- ◐ `CL-18-CPQ-04` Bound free-page-report frequency and payload size. — _payload bounded; report frequency not rate-limited; blocked on: HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed_
- ◐ `CL-18-CPQ-05` Bound audit/diagnostic query cost. — _explain store bounded; audit query API not exposed; blocked on: audit query API not in scope_
- 📄 `CL-18-CPQ-06` Define abuse response and temporary tenant throttling.

### WS18 — Capacity and observability

- ◐ `CL-18-CAO-01` Expose tenant allocation, entitlement, borrow, throttle, and rejection metrics without leaking other tenants' identities. — _aggregate refusal metrics only; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ◐ `CL-18-CAO-02` Model saturation based on guaranteed plus burst capacity. — _guarantee check in quota.py; blocked on: Accountable owners/approvers must be named by the organisation (governance.json owners = null)_
- ◐ `CL-18-CAO-03` Alert before guarantees become unsatisfiable. — _unsatisfiable_guarantees() exists; no alert wired; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ⛔ `CL-18-CAO-04` Benchmark per-tenant overhead and fairness under contention. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ◐ `CL-18-CAO-05` Test many-tenant burst scenarios and long-running starvation cases. — _randomised many-op test; long-running not; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_

### WS18 — Acceptance

- ✅ `CL-18-A-01` Property-test that total allocatable memory never exceeds host capacity minus reserve.
- ✅ `CL-18-A-02` Property-test that no guest drops below floor.
- ◐ `CL-18-A-03` Property-test tenant cap enforcement under concurrent requests. — _sequential property test; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ◐ `CL-18-A-04` Demonstrate bounded waiting for eligible operations under configured fairness policy. — _reject-based admission bounds wait to zero; blocked on: owner decision_

### WS19 — Day-0 bootstrap runbook

- 📄 `CL-19-D0BR-01` Supported hardware/OS/hypervisor prerequisites.
- 📄 `CL-19-D0BR-02` Network/DNS/time prerequisites.
- 📄 `CL-19-D0BR-03` Identity/certificate prerequisites.
- 📄 `CL-19-D0BR-04` State-store and audit-store prerequisites.
- 📄 `CL-19-D0BR-05` Artifact verification steps.
- 📄 `CL-19-D0BR-06` Configuration creation/validation steps.
- 📄 `CL-19-D0BR-07` Provider capability preflight.
- 📄 `CL-19-D0BR-08` Initial ownership/lease initialization.
- 📄 `CL-19-D0BR-09` Readiness verification.
- 📄 `CL-19-D0BR-10` Safe test adjustment on a disposable guest.
- 📄 `CL-19-D0BR-11` Abort/cleanup steps for every failed stage.

### WS19 — Day-1 deployment/rollout runbook

- 📄 `CL-19-D1DRR-01` Canary selection criteria.
- 📄 `CL-19-D1DRR-02` Pre-deployment backup/checkpoint.
- 📄 `CL-19-D1DRR-03` Deployment order across controllers/adapters/state schema.
- 📄 `CL-19-D1DRR-04` Health and metric observation windows.
- 📄 `CL-19-D1DRR-05` Success thresholds and automatic rollback thresholds.
- 📄 `CL-19-D1DRR-06` Staged expansion percentages or host groups.
- 📄 `CL-19-D1DRR-07` Emergency disable procedure.
- 📄 `CL-19-D1DRR-08` Rollback to previous artifact/config/schema.
- 📄 `CL-19-D1DRR-09` Post-deploy audit/evidence capture.

### WS19 — Day-2 operations runbook

- 📄 `CL-19-D2OR-01` Routine health verification.
- 📄 `CL-19-D2OR-02` Capacity and saturation review.
- 📄 `CL-19-D2OR-03` Audit-chain/anchor verification.
- 📄 `CL-19-D2OR-04` Certificate/key rotation.
- 📄 `CL-19-D2OR-05` Dependency/provider upgrade.
- 📄 `CL-19-D2OR-06` Configuration change and rollback.
- 📄 `CL-19-D2OR-07` Quarantine/clear procedure.
- 📄 `CL-19-D2OR-08` Drain/shutdown/restart procedure.
- 📄 `CL-19-D2OR-09` Backup verification and restore drill.
- 📄 `CL-19-D2OR-10` Expired idempotency/audit/telemetry cleanup verification.

### WS19 — Incident runbooks

- 📄 `CL-19-IR-01` Host reserve/invariant threat.
- 📄 `CL-19-IR-02` Cross-tenant authorization anomaly.
- 📄 `CL-19-IR-03` Audit-chain corruption.
- 📄 `CL-19-IR-04` State-store corruption/outage.
- 📄 `CL-19-IR-05` Provider/hypervisor outage.
- 📄 `CL-19-IR-06` Stuck resource mutation.
- 📄 `CL-19-IR-07` Split-brain/stale controller.
- 📄 `CL-19-IR-08` Credential/key compromise.
- 📄 `CL-19-IR-09` Performance overload/retry storm.
- 📄 `CL-19-IR-10` Telemetry outage.
- 📄 `CL-19-IR-11` Site/network partition.
- 📄 `CL-19-IR-12` Recovery validation and service unfreeze.

### WS19 — Runbook quality gate

- 📄 `CL-19-RQG-01` Every step includes command/action, expected output, decision branch, rollback, and escalation contact/role.
- 📄 `CL-19-RQG-02` Runbooks avoid relying on undocumented tribal knowledge.
- 📄 `CL-19-RQG-03` Commands default to read-only/preflight before mutation where possible.
- 📄 `CL-19-RQG-04` Destructive steps require explicit confirmation and scope display.
- ⛔ `CL-19-RQG-05` Runbooks are exercised in scheduled game days and updated from findings. — _blocked on: Runbooks not yet exercised in a game day (needs a real environment)_

### WS20 — Repository metadata

- ⛔ `CL-20-RM-01` Add an approved `LICENSE`. — _blocked on: License choice is an owner decision_
- 📄 `CL-20-RM-02` Add `NOTICE` where required by project policy/dependencies.
- ✅ `CL-20-RM-03` Add `pyproject.toml` and canonical build metadata.
- 📄 `CL-20-RM-04` Add contributor/development instructions.
- 📄 `CL-20-RM-05` Add security reporting policy.
- 📄 `CL-20-RM-06` Add release process documentation.
- ✅ `CL-20-RM-07` Keep generated artifacts out of source unless intentionally versioned.

### WS20 — Code quality gates

- ✅ `CL-20-CQG-01` Configure formatter and lint rules.
- ✅ `CL-20-CQG-02` Configure static type checking for public/internal APIs.
- ◐ `CL-20-CQG-03` Configure import/dependency boundary checks where useful. — _ruff import rules; no layered boundary contract; blocked on: owner decision_
- ◐ `CL-20-CQG-04` Add dead-code/unreachable-code checks where supported. — _ruff F-codes only; blocked on: owner decision_
- ✅ `CL-20-CQG-05` Add secret scanning.
- ◐ `CL-20-CQG-06` Add dependency vulnerability scanning. — _no runtime deps; pip-audit step in CI; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-20-CQG-07` Add SAST focused on privileged/provider interfaces.
- ◐ `CL-20-CQG-08` Establish line/branch coverage thresholds, while requiring explicit critical-path tests rather than treating coverage as sufficient evidence. — _coverage threshold configured (85%); measured locally; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_

### WS20 — CI pipeline

- ✅ `CL-20-CP-01` Clean checkout/build on every change. — _step defined in workflow and executed locally_
- ✅ `CL-20-CP-02` Install only declared dependencies. — _step defined in workflow and executed locally_
- ◐ `CL-20-CP-03` Verify lockfile integrity. — _lock hash checked in CI step; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-20-CP-04` Run unit tests. — _step defined in workflow and executed locally_
- ✅ `CL-20-CP-05` Run schema/contract tests. — _step defined in workflow and executed locally_
- ✅ `CL-20-CP-06` Run security regression tests. — _step defined in workflow and executed locally_
- ✅ `CL-20-CP-07` Run fuzz smoke corpus. — _step defined in workflow and executed locally_
- ✅ `CL-20-CP-08` Run package/version consistency check. — _step defined in workflow and executed locally_
- ✅ `CL-20-CP-09` Build wheel/sdist. — _step defined in workflow and executed locally_
- ✅ `CL-20-CP-10` Install built artifact into a clean environment and rerun critical tests. — _step defined in workflow and executed locally_
- ⛔ `CL-20-CP-11` Run integration/performance suites on protected release pipelines. — _blocked on: Real hardware classes / disposable test VMs / real hypervisor not available_
- ✅ `CL-20-CP-12` Archive machine-readable results. — _step defined in workflow and executed locally_

### WS20 — SBOM and provenance

- ✅ `CL-20-SAP-01` Generate SBOM for each release artifact.
- ✅ `CL-20-SAP-02` Include direct and transitive dependencies with versions/hashes.
- ◐ `CL-20-SAP-03` Generate signed build provenance containing source commit, builder identity, build inputs, commands/workflow identity, artifact digests, and timestamps. — _HMAC reference; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ◐ `CL-20-SAP-04` Sign release artifacts or an immutable manifest covering them. — _HMAC reference; blocked on: Platform PKI / identity provider / KMS not selected (ADR-0004)_
- ◐ `CL-20-SAP-05` Verify provenance/signature before deployment. — _verify-evidence command; blocked on: Deployment environment (encrypted volume, central audit sink, dashboards backend) not available_
- ✅ `CL-20-SAP-06` Store SBOM/provenance/evidence manifest alongside the release.

### WS20 — Release regression gates

- ✅ `CL-20-RRG-01` Fail release on mandatory test failure.
- ✅ `CL-20-RRG-02` Fail release on incompatible dependency/provider matrix.
- ◐ `CL-20-RRG-03` Fail release on unapproved high/critical vulnerability according to policy. — _SAST gate; no vulnerability feed; blocked on: Hosted CI runner + immutable result store not available to this execution (workflow file provided)_
- ✅ `CL-20-RRG-04` Fail release on benchmark regression beyond approved thresholds.
- ✅ `CL-20-RRG-05` Fail release on missing SBOM/provenance/signature.
- ✅ `CL-20-RRG-06` Fail release on expired waiver.
- ✅ `CL-20-RRG-07` Fail release when RTM/acceptance manifest is incomplete.
- ✅ `CL-20-RRG-08` Require protected approval for production promotion.

## Final Definition of Done

- ⛔ NOT MET — Every fully missing control in Appendix A is implemented and has evidence.
- ⛔ NOT MET — Every partial control in Appendix B is closed or has a formally approved, unexpired waiver.
- ⛔ NOT MET — The real provider/hypervisor adapter passes the integration and compatibility matrix.
- ⛔ NOT MET — Authentication, authorization, ownership fencing, durable state, and audit persistence are active in the production path.
- ⛔ NOT MET — All mutation paths preserve host reserve, guest floor/ceiling, tenant authorization, idempotency, and stale-state fencing invariants.
- ⛔ NOT MET — Fault injection demonstrates deterministic recovery or safe halt for each documented failure mode.
- ⛔ NOT MET — Performance gates pass with reproducible p50/p95/p99/worst-case evidence on the approved hardware/software matrix.
- ⛔ NOT MET — Observability provides actionable health, metrics, logs, traces, decision explanations, dashboards, and alerts without secret/tenant leakage.
- ⛔ NOT MET — Day-0/day-1/day-2 and incident runbooks have been exercised successfully.
- ⛔ NOT MET — SBOM, signed provenance, compatibility matrix, RTM, benchmark evidence, security evidence, and test evidence are attached to the release.
- ⛔ NOT MET — Production exit gate returns machine-readable PASS with no expired waivers or unresolved P0 blockers.
