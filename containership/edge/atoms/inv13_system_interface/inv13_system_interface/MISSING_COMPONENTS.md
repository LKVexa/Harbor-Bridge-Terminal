# INV-13 — Missing Production Components

## v4.3.0 execution status (2026-09-22)

The v4.3.0 pass executed `inv13_system_interface_v4.2.0_COMPONENT_CHECKLISTS.md` against this package. Per-item marks are in `COMPONENT_CHECKLISTS_v4.3.0_STATUS.md` (`[x]` evidenced by an automated test/artifact here, `[~]` partial, `[ ]` not evidenced); machine-readable status in `COMPONENT_STATUS.json`. **No component is declared production-closed**: the completion rule requires human security review and organisational/fleet evidence that a build cannot produce.

| ID | v4.3.0 status | Remaining gap |
|---|---|---|
| MC-001 | PARTIAL | No wit-bindgen generated bindings, canonical-ABI validation, cross-language conformance or generated docs (toolchain absent); security approval of the world set pending named reviewers. |
| MC-002 | PARTIAL | Engine is V8 via Node for core Wasm only (process-per-run, wall-time limit, no fuel/memory caps inside the engine); Component-model binaries refused; no Wasmtime binding, canonical ABI, multi-runtime tests; fs/net/http providers not yet bound into the engine import table. |
| MC-003 | IMPLEMENTED (POSIX host provider) | Windows handle-relative implementation absent (fails closed); FIFO/device special-file policy only via O_NOFOLLOW + type checks on read; independent static review pending. |
| MC-004 | IMPLEMENTED (reference table; INV-42 service external) | No expiry, persistence, reconciliation, serialization/migration; authoritative INV-42 service must implement the DescriptorTable interface. |
| MC-005 | IMPLEMENTED | No policy simulation/dry-run tooling, no decision caching, policy bundles unsigned, independent tenant-isolation review pending. |
| MC-006 | PARTIAL (reference HMAC identity; PKI/attestation external) | Shared-key HMAC is not production identity; no X.509/SPIFFE, key custody, revocation lists, channel binding or real TEE verifier. Fuzzing found and fixed a token-malleability defect (non-canonical base64). |
| MC-007 | IMPLEMENTED (host provider); engine binding open | Accepted-socket inheritance, proxy semantics, UDP data path, race tests and platform matrix not done; not bound into guest ABI yet. |
| MC-008 | IMPLEMENTED | Locale/timezone, cwd semantics, fd inheritance for spawned engine only partly (clean env passed to node), secret rotation. |
| MC-009 | IMPLEMENTED | No timer/sleep API, no trusted-time dependency handling, side-channel review needs a human reviewer. |
| MC-010 | IMPLEMENTED | FIPS mode and fork/snapshot reseed semantics are delegated to the OS; no dependency review sign-off. |
| MC-011 | IMPLEMENTED | 12-bit generation counter wraps after 4095 reuses of one slot (documented residual risk T-10). |
| MC-012 | IMPLEMENTED | Localization boundary not addressed; security review pending. |
| MC-013 | PARTIAL | asyncio reference only; not wired to engine pollables/futures; no fairness, partial-I/O or load tests. |
| MC-014 | IMPLEMENTED (single node) | No distributed consistency / multi-node activation, approval gates, impact analysis or schema migration. |
| MC-015 | PARTIAL (durable local sink; WORM/KMS external) | No remote/WORM transport, checkpoint key rotation/custody, tenant-separated streams, access monitoring. |
| MC-016 | PARTIAL | No OTLP exporter, secure transport, dashboards, alert rules or runbook links (needs the org's observability stack). |
| MC-017 | PARTIAL | No priority classes, soft limits/burst, dynamic updates, memory-pressure limits inside the engine, operator overrides. |
| MC-018 | PARTIAL | No connection pooling, proxy semantics, retry policy, HTTP/2 controls; not bound to guest ABI. |
| MC-019 | IMPLEMENTED | No rolling-upgrade/state-compat scenarios, generated-binding matrix. |
| MC-020 | PARTIAL (1 of 16 declared cells executed) | Only linux/x86_64/Python 3.11/Node 22 executed; Windows fs provider absent; ARM64/macOS unrun. |
| MC-021 | IMPLEMENTED (stdlib seeded fuzzing) | No coverage-guided fuzzer (Atheris/libFuzzer), sanitizers, corpus minimisation or long campaigns. |
| MC-022 | PARTIAL | No race detectors/sanitizers (pure Python), deterministic scheduler, identity-rotation or audit-chain race suites. |
| MC-023 | IMPLEMENTED (in-process) | No network partition, split-brain or memory-pressure chaos; no alert validation. |
| MC-024 | IMPLEMENTED — with finding B-01 (resolve SLO missed) | Lexical resolve p99 ≈ 61 µs vs the contract's 1 µs target (see AUDIT_REPORT B-01); single-host, short soak; no cross-platform baselines. |
| MC-025 | PARTIAL | Artifacts unsigned (no KMS), no vulnerability/secret scanning service, pk_core version unpinned. |
| MC-026 | IMPLEMENTED | No signature verification on install, uninstall/upgrade tests. |
| MC-027 | IMPLEMENTED | No two-person rule, partition behaviour or alerting; artifact (binary) rollback relies on release tooling. |
| MC-028 | OPEN (template only) | Named owners, on-call, escalation, reviews and drills must be supplied by the organisation. |
| MC-029 | PARTIAL (enforced in code; legal sign-off open) | Retention/deletion enforcement, regional routing, access logging are policy text only. |
| MC-030 | PARTIAL | Power/thermal/battery measurements need physical edge hardware. |
| MC-031 | IMPLEMENTED (unsigned) | Manifest not signed; human approval step pending. |
| MC-032 | PARTIAL (drafted; approvals pending) | No ADRs for network/HTTP, identity, async/resource; ADR approval by named deciders pending. |

## Original v4.2.0 register (unchanged)

This register distinguishes a hardened reference policy model from a complete production system interface. Priority meanings: **P0** blocks a credible production security boundary; **P1** blocks normal production readiness/certification; **P2** is an important maturity/scale capability.

| ID | Priority | Missing component | Required production capability / acceptance evidence |
|---|---|---|---|
| MC-001 | P0 | Concrete versioned WIT/world definitions | Checked-in, pinned interface packages for the exact WASI target; schema compatibility rules; generated bindings; contract tests proving the exposed surface equals the declared world. |
| MC-002 | P0 | Real WASI host/runtime adapter | Integration with the selected Wasm runtime(s), component instantiation, resource tables, canonical ABI boundary, lifecycle/error mapping, and adjacent-layer integration tests. |
| MC-003 | P0 | Descriptor/handle-relative filesystem resolver | Preopens represented by already-open directory handles; symlink-safe, race-resistant relative opens; no host path re-resolution by string; adversarial tests for symlink swaps, mount changes, rename races, and traversal. |
| MC-004 | P0 | Capability-descriptor integration | Bind the world/preopen policy to the authoritative descriptor system (the declared INV-42 dependency), including stable IDs, ownership, revocation, inheritance rules, and provenance. |
| MC-005 | P0 | Authorization policy enforcement point | Policy engine or equivalent that decides which world/preopens a workload may receive, with deny-by-default behavior, tenant scoping, change control, and machine-readable reasons. |
| MC-006 | P0 | Host/control-plane identity and attestation | Authenticated runtime/node/control-plane actors, workload identity binding, attestation validation where required, and safe behavior when identity/attestation is unavailable. |
| MC-007 | P0 | Network/socket capability implementation | Explicit socket/address/DNS authority, egress policy, bind/connect/listen rules, protocol/address-family restrictions, quotas, and tests proving no ambient network access. |
| MC-008 | P0 | Environment/stdio/argument/secret boundary | Concrete adapters defining exactly what environment variables, arguments, stdin/stdout/stderr, and secret references are visible; secret redaction and non-inheritance tests. |
| MC-009 | P0 | Clock providers and precision policy | Separate wall/monotonic implementations, precision reduction where needed, denial semantics, deterministic/replay mode, and side-channel tests. |
| MC-010 | P0 | Cryptographic randomness provider | Approved host CSPRNG binding, error/unavailability handling, quota/backpressure, and optional deterministic test/replay provider that cannot be enabled accidentally in production. |
| MC-011 | P0 | Resource-table lifecycle | Typed descriptors/resources, ownership/borrowing rules, close/drop semantics, leak detection, generation protection against stale handles, and exhaustion behavior. |
| MC-012 | P0 | Structured error taxonomy | Stable machine-readable codes mapping host/WASI failures to capability denial, invalid input, unavailable dependency, quota, timeout/cancel, and terminal errors without leaking sensitive host details. |
| MC-013 | P1 | Async polling, cancellation, timeout, and backpressure semantics | Pollables/futures/streams or target-runtime equivalents, cancellation propagation, bounded queues, timeout policy, retry safety, and overload behavior. |
| MC-014 | P1 | Atomic configuration and policy activation | Versioned declarative world/preopen configuration, validation, staged activation, provenance, transactional update, rollback, and recovery from partial control-plane failure. |
| MC-015 | P1 | Durable tamper-evident audit sink | Export the in-process hash chain to append-only/durable storage, bind records to node/workload/release identity, protect integrity, define retention/privacy, and independently verify chains. |
| MC-016 | P1 | Metrics/logs/tracing/exporters | Rate/error/latency/saturation/resource metrics; structured IDs; trace-context propagation; safe high-cardinality diagnostics; dashboards/alerts separating denial, attack, dependency failure, overload, and defect. |
| MC-017 | P1 | Resource quotas and admission control | Per-tenant/workload limits for descriptors, preopens, sockets, streams, memory/buffers, concurrent operations, and provider fan-out; fairness and load shedding. |
| MC-018 | P1 | Real HTTP outgoing adapter | If `http-outgoing` remains a capability: typed request/response resources, destination policy, TLS validation, redirect rules, connection pooling, limits, timeout/cancel behavior, and SSRF defenses. |
| MC-019 | P1 | Interface/version negotiation and compatibility matrix | Supported runtime/WASI/WIT versions, backward/forward compatibility behavior, deprecation/EOL dates, negative tests for unsupported peers, and release gating. |
| MC-020 | P1 | Cross-platform/architecture certification | Windows/Linux/macOS where supported; x86-64/ARM64 and other target CPUs; runtime/provider matrix; filesystem semantic differences; repeatable CI evidence. |
| MC-021 | P1 | Fuzz/property/adversarial test harness | Fuzz paths, capability/world parsing, WIT boundaries, error mapping, resource IDs, malformed provider responses, and property-test invariants such as “no undeclared authority becomes reachable.” |
| MC-022 | P1 | Concurrency/race test suite | Parallel grant/revoke/use/resolve in the real host layer, descriptor reuse, cancellation races, resource-table races, shutdown, and TOCTOU adversarial cases under sanitizers/race detectors where available. |
| MC-023 | P1 | Fault-injection and degraded-operation suite | Runtime crash/restart, provider loss, time/identity/policy outage, network partition/reconnect, disk pressure, control-plane staleness, and proof that failures do not create ambient authority. |
| MC-024 | P1 | Performance/scale benchmark harness | Reproducible p50/p95/p99/worst-case latency, startup, throughput, CPU/memory, descriptor density, burst/overload/recovery, soak, and regression gates. The current 1 µs target is not production-certified evidence. |
| MC-025 | P1 | Supply-chain/provenance controls | Dependency lock/manifest, SBOM, artifact digests/signatures, reproducible build inputs, vulnerability scanning/response, provenance attestation, and approved-version enforcement. |
| MC-026 | P1 | Packaging/build metadata | A defined build/install artifact and dependency declaration for `pk_core` and the selected runtime/bindings; deterministic package creation; supported Python/runtime version policy if Python remains part of the toolchain. |
| MC-027 | P1 | Production rollback/quarantine/emergency-disable control | Operator/API controls to revoke worlds/preopens, quarantine a workload/runtime, freeze unsafe mutations, roll back policy/artifacts, and record who/what/why. |
| MC-028 | P1 | Ownership, incident, and escalation package | Named accountable owner/team, on-call/escalation path, severity model, containment/recovery runbooks, access reviews, policy reviews, and exception/waiver expiry tracking. |
| MC-029 | P2 | Data residency/privacy policy for interface telemetry | Define what host paths, tenant/workload IDs, environment metadata, denial details, traces, and audit records may be retained/exported by region and for how long. |
| MC-030 | P2 | Power/thermal and constrained-edge characterization | For far-edge targets: power/thermal overhead, resource ceilings, offline operation, restart/replay behavior, and node-specific capacity model. |
| MC-031 | P2 | Formal traceability/evidence bundle | Per-check mapping from requirements to code/config/test/benchmark/security evidence; immutable release evidence manifest; independent verification of all mandatory production gates. |
| MC-032 | P2 | Architecture decision and threat-model artifacts | Approved ADRs for runtime/WASI target, capability model, filesystem strategy, error model, audit/export design, and a maintained threat model tied directly to security tests. |

## Completion rule

A component should leave this list only when there is a concrete implementation/configuration artifact **and** objective verification evidence. Prose, a generic checklist PASS, or a mocked provider is not sufficient for a P0/P1 production item.
