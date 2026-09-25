# SCH-01 4.2.0 Post-Update Missing Components

This is the complete gap inventory found in the supplied standalone archive after the 4.2.0 hardening pass. “Missing” means the capability, artifact, proof, or external prerequisite is not present here at a level sufficient to independently verify the corresponding checklist requirement. Items explicitly outside SCH-01 ownership are separated from SCH-01-owned gaps rather than being misreported as local implementation defects.

## A. Missing or incomplete SCH-01-owned components

| ID | Missing component | Why it is still missing after 4.2.0 | Checklist coverage |
|---|---|---|---|
| MC-01 | Original `MASTER.md` evidence | README 4.1.0 claimed 100 master prompt/workflow documents were carried verbatim, but the supplied archive contains no `MASTER.md`. 4.2.0 corrects the claim and does not fabricate the source. | Evidence provenance; supports C020/C090/C100 |
| MC-02 | Reproducible package/install manifest | No `pyproject.toml`, lock file, pinned dependency manifest, wheel/sdist metadata, or approved install recipe is present. | C031, C040, C093 |
| MC-03 | Accountable owner and escalation record | No named service owner, backup owner, escalation path, or on-call mapping exists. | C009, C097 |
| MC-04 | Approved architecture decision record | `ARCHITECTURE.md` documents the current design, but there is no approval record, decision status, approver, supersession chain, or governed ADR covering the full source function. | C010, C098 |
| MC-05 | System-specific SHALL requirements specification | `CHECKLIST.json` contains generic requirements, not a normalized SCH-01 functional/nonfunctional SHALL specification with identifiers and acceptance criteria. | C011-C013 |
| MC-06 | Requirements-to-evidence traceability matrix | There is no generated matrix mapping each of the 100 checks to concrete code, test, runtime evidence, owner, and release gate result. | C020, C090, C100 |
| MC-07 | Deployment-context semantics | Cloud, datacenter, near-edge, far-edge, disconnected-site, and site-boundary behavior are not fully specified. | C012, C018 |
| MC-08 | Complete result/failure/lifecycle state machine | Success, partial success, degraded operation, retryable failure, terminal failure, lifecycle states, and legal transitions are not formally modeled. | C014, C015 |
| MC-09 | Versioning/backward-compatibility policy | A version exists, but there is no supported-version policy, deprecation window, schema compatibility rule, or migration contract. | C016, C027, C093 |
| MC-10 | Quota/fair-share accounting | The engine has slot capacity and local tenant isolation, but no persistent quota ledger, reservation model, starvation guard, or fair-share policy. | C017, C058 |
| MC-11 | Runtime/execution-target selector | Placement selects a node and tier, but does not select a concrete runtime implementation/execution target beyond the tier label. | C010, C011, C031 |
| MC-12 | Latency-aware placement policy | `latency_class` is classified but is not consumed by candidate filtering or scoring, so interactive and batch workloads currently place identically given the same other inputs. | C011, C013, C061-C063 |
| MC-13 | Topology-aware placement | No topology graph, hop/zone/NUMA locality input, cost function, or topology constraint is implemented in the local engine. | C010, C019, C031, C066, C078 |
| MC-14 | Data-path/residency selector | No data locality, residency jurisdiction, storage path, data-plane affinity, or data-path binding is represented. | C010, C019, C031, C078 |
| MC-15 | Accelerator allocator | Generic hardware capabilities are checked, but there is no accelerator identity, quantity, partition, exclusivity, locality, health, or lease allocation. | C010, C011, C031, C064, C069 |
| MC-16 | Governed policy-input engine | Provenance, site affinity, thermal exclusion, tier and capabilities are hard-coded model fields; there is no signed/versioned policy bundle, precedence engine, policy revision, or policy provenance. | C019, C031-C037, C045, C076-C078 |
| MC-17 | Formal machine-readable schema artifacts | `SCHEMAS.md` documents fields, but no JSON Schema/Protobuf/WIT/IDL files, schema validators, compatibility fixtures, or generated bindings are present. | C021, C022, C027, C029, C082 |
| MC-18 | Unified public error contract | `Unplaceable` now has `PK_SCHEDULER_ERROR/1`, but `ValueError`/`TypeError` remain out-of-band and there is no governed full error-code catalog with retryability and caller action. | C026 |
| MC-19 | Boundary authentication | No caller, node, peer, provider, or control-plane authentication mechanism is implemented in this archive. | C023, C044, C048 |
| MC-20 | Authorization/capability enforcement | No caller permissions, tenant authorization, capability tokens, least-privilege identity model, or administrative authorization layer is implemented. | C024, C042, C043 |
| MC-21 | Timeout/cancellation/retry/idempotency/backpressure contract | The in-process calls are synchronous and bounded only by local execution; external request semantics and overload contracts are unspecified. | C025, C028, C053, C054 |
| MC-22 | Declarative configuration subsystem | No separate config schema/store/loader exists for policy, freshness, scoring, environment, site, or feature flags. | C032-C035 |
| MC-23 | Configuration provenance and transactional activation | No config author/version/activation timestamp, atomic apply, validation gate, or transactional rollback mechanism exists. | C034, C036-C038 |
| MC-24 | Secret/key management integration | No credential boundary, secret provider, key rotation policy, or safe unavailable-key behavior exists; no secrets are needed by the pure engine today, but production integrations would require this control. | C039, C047, C048 |
| MC-25 | Cryptographic node/workload/artifact attestation | `NodeReport` validation checks shape and clock sanity only. It does not authenticate the producer or verify signatures, digests, provenance attestations, approved versions, or anti-replay data. | C041, C044, C045, C048 |
| MC-26 | Rich occupancy/isolation metadata | Occupancy stores only workload->tenant. It lacks occupant trust class, tier instance, runtime identity, device assignment, namespace, and attestation needed to prove safe shared placement; 4.2.0 therefore fails cross-tenant placement closed. | C046 |
| MC-27 | Tamper-evident security audit ledger | No append-only/hash-chained signed audit stream is emitted for classification, refusal, placement, policy changes, or admin actions. | C049, C073, C090 |
| MC-28 | Adversarial security suite | No systematic tests for spoofing, replay, injection, malicious policy/artifact inputs, privilege escalation, escape, side channels, or resource exhaustion are present. | C050, C085, C087 |
| MC-29 | Exhaustive failure model and health/stall thresholds | The contract lists four failure modes, but process/VM/node/site/network/provider/dependency/control-plane failure handling and health/stall thresholds are incomplete. | C051, C052 |
| MC-30 | Retry/load-shed/circuit-breaker/failover controls | There is no bounded retry policy, admission controller for scheduler request load, circuit breaker, failover algorithm, or formal degraded mode. | C053-C056 |
| MC-31 | Durable scheduler state and restart/replay model | Placement mutates caller-owned in-memory `NodeReport` objects. There is no WAL/database, crash-consistent state, restart reconstruction, replay, or snapshot format. | C057, C095 |
| MC-32 | Distributed fencing/consensus | The new lock prevents in-process races only. Multiple scheduler processes can still race unless an external transactional owner/fencing mechanism exists. | C058, C086 |
| MC-33 | Operator quarantine/freeze/disable control | A `quarantined` workload maps to the strongest tier, but there is no administrative freeze, node quarantine, scheduler disable, or kill-switch API. | C059, C092 |
| MC-34 | Fault-injection/recovery suite | No automated dependency failure, node loss, clock fault, partition, reconnect, controller loss, or recovery-objective tests are included. | C060, C089 |
| MC-35 | Reproducible performance benchmark suite | No committed baseline harness or stored baseline covers decision latency, throughput, startup, CPU, memory, storage/network overhead, or power. | C061, C063-C068 |
| MC-36 | Full performance thresholds and release regression gate | Only a p99/1,000-node objective is declared. p50/p95/worst-case, saturation, capacity model, and machine-enforced regression thresholds are absent. | C062, C067, C069, C070 |
| MC-37 | Runtime health/readiness/dependency status surface | There is no status endpoint or command exposing health, readiness, version, active configuration, external dependency health, and capability set. | C071 |
| MC-38 | Metrics implementation | Metric names are declared in `contract.py`, but the engine emits no counters/histograms/gauges and has no exporter. | C072 |
| MC-39 | Structured operational logging | No stable structured log/event emission exists for workload, tenant, node, operation, decision, and error identifiers. | C073 |
| MC-40 | Distributed tracing | No trace/span context propagation or trace export exists. | C074 |
| MC-41 | Production explainability surface | 4.2.0 adds deterministic decision metadata and aggregate refusal counts, but there is no operator explain API/UI linking decisions to policy revision, topology, data path, infrastructure graph, and release lineage. | C075-C078 |
| MC-42 | Telemetry governance, dashboards, and alerts | No retention/sampling/privacy/export policy, dashboards, or alerts distinguish load, degradation, rejection, dependency failure, attack, and software defect. | C079, C080 |
| MC-43 | Complete public contract tests | Core unit tests exercise behavior, but there are no schema-level conformance tests for every public payload/error/version transition. | C082 |
| MC-44 | Adjacent-layer integration matrix | No executable tests are bundled for PLN-02, PLN-04, PLN-05, GAP-02, GAP-03, GAP-10, execution tiers, or provider variants. | C030, C083 |
| MC-45 | Platform/runtime compatibility matrix tests | No CI matrix spans CPU architectures, OSes, hypervisors, runtime implementations, providers, or protocol/schema versions. | C084, C093 |
| MC-46 | Fuzz/property-based testing | No fuzz corpus/property suite targets constructors, schema boundaries, classifier inputs, candidate sets, or error serialization. | C085 |
| MC-47 | Distributed concurrency/race tests | A local two-thread oversubscription test now exists, but there is no multi-process/distributed race, stale-writer, ABA/fencing, or split-brain test. | C086 |
| MC-48 | Benchmark/soak/burst/fleet-scale certification | No soak, burst, overload, fleet-scale, scale-in/out, or recovery benchmark suite is committed. | C088 |
| MC-49 | Machine-readable release evidence bundle | No generated evidence ledger, signed gate result, SBOM, provenance attestation, checksum manifest, or release certificate is included. | C090, C100 |
| MC-50 | Support commitment and error-budget operating policy | SLOs exist, but support hours, paging policy, escalation ownership, budget burn action, and breach procedure are absent. | C091, C097 |
| MC-51 | Canary/staged rollout automation | `OPERATIONS.md` describes manual rollback intent, but there is no canary controller, staged rollout policy, automated health gate, or rollback trigger. | C092 |
| MC-52 | Vulnerability/patch/EOL policy | No patch SLA, vulnerability triage process, supported branch policy, dependency update cadence, or EOL schedule exists. | C094 |
| MC-53 | State backup/reconstruction procedure | No formal backup/restore/reconstruction method exists for placement state because durable state is not implemented locally. | C095 |
| MC-54 | Production-grade runbook set | `OPERATIONS.md` adds day-0/day-1/day-2 guidance, but it does not include environment-specific commands, ownership, rollback verification, dependency recovery, or tested operational drills. | C096 |
| MC-55 | Incident response procedure | No severity model, paging tree, containment steps, communications path, evidence preservation, or recovery checklist exists. | C097 |
| MC-56 | Recurring review program | No scheduled access, policy, dependency, configuration, threat-model, or architecture review record exists. | C098 |
| MC-57 | Exception/waiver/technical-debt register | No owner/expiry-based waiver register or deprecated-behavior ledger exists. | C099 |
| MC-58 | Formal production exit gate implementation | README names `pk_core gate`, but the required framework/evidence are not bundled and no local executable gate proves all architecture/security/resilience/performance/operations prerequisites. | C100 |
| MC-59 | CI workflow | No repository CI configuration runs compile, unit, security, compatibility, benchmark, or release gates on change. | C070, C084-C090, C100 |
| MC-60 | License/SBOM/release provenance artifacts | The archive contains no license file, SBOM, dependency inventory, build provenance statement, or release checksums. License terms cannot be inferred. | Supply-chain support for C041, C045, C090, C094 |

## B. Unresolved external prerequisites named by the architecture

These are not necessarily defects in SCH-01 because the contract says they belong to adjacent elements, but a standalone production certification cannot close without them:

| External element | Required role | Current archive state |
|---|---|---|
| `pk_core` | 100-check assessment, evidence ledger, gate and verification framework | Not bundled or importable in the audit environment; integration tests skip |
| `PLN-02 Application plane` | Resolved application revision/components | Not bundled; no integration fixture |
| `PLN-05 Elasticity plane` | Desired instance count | Not bundled; no integration fixture |
| `GAP-02 Hardware capability discovery` | Authoritative node capability/attestation reports | Not bundled; engine accepts already-constructed reports |
| `PLN-04 Execution plane` | Enforce selected isolation tier/admit workload | Not bundled; no end-to-end enforcement proof |
| `GAP-03 Topology-aware scheduler` | Topology/locality and fair-share guard | Not bundled; conformance adapter marks fair-share partial when absent |
| `GAP-10 Power/thermal-aware scheduling` | Optional thermal exclusion input | Not bundled; local engine only consumes a boolean exclusion flag |
| `INV-33 Virtualization controller` | Execution-side lease lifecycle/reclamation | Not bundled; conformance adapter marks lease reclamation partial when absent |

## C. What is no longer missing after 4.2.0

The post-update audit verified these previously weak areas locally: a dependency-independent engine test surface; strict input validation; canonical classification enforcement; future-report rejection; deterministic placement; duplicate node/workload protection; process-local race protection; stable structured placement refusal codes; aggregate safe diagnostics; corrected component class naming with compatibility alias; standalone optimized-mode execution; and accurate documentation of the missing `MASTER.md` and external `pk_core` dependency.
