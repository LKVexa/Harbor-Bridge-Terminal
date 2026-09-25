# PLN-06 Data plane — audit, repair, hardening, and post-audit report

**Input version:** 4.1.0  
**Updated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Input ZIP SHA-256:** `86e91c1e3292cf993e65e80186d022d50f7077ea49bc6aab7211542ba9257afd`  
**Scope:** the uploaded standalone `pln06_data_plane` repository. External components are treated as absent unless executable evidence is physically available to this audit.

## Executive result

The source archive parsed cleanly and had no unsafe ZIP paths or symlinks, but it was not independently verifiable as shipped: all three original tests skipped when `pk_core` was unavailable, so the standalone archive executed **zero** substantive tests. The code also had locality/contract drift, concurrency and completion-integrity weaknesses, weak configuration validation/provenance, and a false README packaging claim for a nonexistent `MASTER.md`.

Version 4.2.0 fixes the repository-local defects that can be corrected without inventing adjacent systems. The dependency-free runtime now passes 13 substantive tests in both normal and optimized Python modes, including a 64-attempt concurrency race. The external `pk_core` conformance suite remains correctly skipped because `pk_core` is not present.

The independent 100-item post-audit in `TRACEABILITY.md` records:

- **21 Implemented**
- **38 Partial**
- **41 Missing**

Therefore this standalone archive is materially stronger and internally testable, but it is **not production-complete** and does not contain enough evidence for a formal production exit gate.

## Source defects found and corrected

1. **Runtime coupled to `pk_core` import.** Importing the package required the external certification framework. The executable runtime now lives in dependency-free `data_plane.py`; certification objects are lazy-loaded.
2. **All original tests could skip.** With `pk_core` absent, the archive had no executing behavioral tests. Added a standalone 13-test runtime/repository suite that runs without external dependencies.
3. **Contract/implementation locality drift.** Documentation said transport selection used payload size and locality, but the code accepted no locality and selected solely by size. Added explicit locality with a backward-compatible `auto` mode and safety-floor promotion.
4. **Concurrent oversubscription race.** Admission checked and incremented mutable state without synchronization. Admission/completion/cancellation/accounting are now protected by an internal `RLock`.
5. **Weak transfer completion binding.** Sequential IDs plus completion keyed only by live ID allowed a mutated/forged live decision to release capacity. IDs are now opaque UUID4 values and completion metadata must exactly match the admitted record.
6. **Boolean admission-limit bug.** `True` was accepted as an integer in-flight limit. Boolean/non-positive/non-integer limits now fail validation.
7. **Weak residency configuration validation.** Strings could be misinterpreted as iterables of classification characters and malformed site/classification data was not rejected consistently. Configuration is now strictly normalized and copied.
8. **No per-tenant capacity option.** A single tenant could consume the global budget. An optional per-tenant in-flight ceiling now provides quota isolation at the admission layer.
9. **No atomic policy update/provenance.** Added `replace_residency()` with full pre-validation, atomic activation, live-transfer safety checks, revision, author, and UTC activation time.
10. **Unstructured errors.** Added stable error codes, retryability metadata, details, and `as_dict()` for machine handling.
11. **Digest metadata not validated.** Optional SHA-256 metadata is now syntax-validated and normalized; actual payload hashing/verification remains an explicit transport dependency.
12. **Sparse runtime telemetry.** Added versioned health/readiness and metrics snapshots, decision reasons, config revision binding, refusal/backpressure/outcome counters, and per-tier byte/admission accounting.
13. **No machine-readable interface schemas.** Added JSON Schema 2020-12 definitions for transfer, residency, transport tier, metrics, and health contracts.
14. **False packaging claim.** `README.md` claimed `MASTER.md` was included, but the file did not exist. The claim was removed rather than fabricating missing source material.
15. **Insufficient architecture/security/operations documentation.** Added a proposed ADR, security model, operations notes, compatibility notes, and a complete 100-item traceability matrix.

## Verification performed after changes

- ZIP source integrity/path audit: **PASS**; no traversal paths or symlinks.
- Python compilation (`compileall`): **PASS**.
- Dependency-free runtime/repository tests: **13/13 PASS**.
- Dependency-free tests under `python -O`: **13/13 PASS**.
- Unified test discovery: **13 PASS, 3 SKIPPED**; the three skips are the `pk_core` conformance tests because `pk_core` is not installed.
- Optimized unified discovery: **13 PASS, 3 SKIPPED**.
- Manual suspicious-API scan: no production use of `eval`, `exec`, pickle/marshal, shell execution, unsafe YAML loading, or bare runtime assertions found.
- `ruff`, `bandit`, and `mypy` were not installed in the audit environment, so no claim is made that those analyzers passed.

## Remaining missing or incomplete components

The table below enumerates the concrete components still required to close every Partial/Missing checklist item. `TRACEABILITY.md` provides the one-to-one 100-requirement evidence matrix.

| # | Severity | Missing / incomplete component | Checklist mapping | What is still required |
|---:|---|---|---|---|
| 1 | Critical | Accountable ownership and escalation | C009, C097 | Named service/repository owner, CODEOWNERS/on-call target, escalation path, incident contacts. |
| 2 | High | Approved architecture decision | C010 | Owner-approved ADR rather than the included Proposed ADR; record chosen production technologies and exceptions. |
| 3 | Critical | Concrete source-architecture transport adapters | C011, C021, C030, C031, C066, C083 | Actual in-process Component Model, cross-node wRPC, VM-control vsock, and shared-memory/RDMA implementations with version pins and integration tests. |
| 4 | High | Deployment-context requirements | C012, C018 | Explicit cloud/datacenter/near-edge/far-edge behavior plus intermittent/offline network semantics. |
| 5 | High | Complete non-functional requirement set | C013, C062, C091 | Availability, durability, consistency, isolation, determinism, p95/p99/worst-case thresholds, support commitments, and measured evidence. |
| 6 | Medium | Complete outcome/degraded-state semantics | C014, C056 | Formal partial-success/degraded-mode semantics and what functionality remains available when dependencies fail. |
| 7 | High | Durable/distributed lifecycle state machine | C015, C057, C058 | Persistent state transitions, restart/resume/replay, duplicate ownership, stale-controller, and split-brain handling. |
| 8 | High | Formal version/compatibility policy | C016, C027, C084, C093 | Supported schema/protocol/runtime/platform/dependency versions, skew rules, deprecation windows, and compatibility CI. |
| 9 | Medium | Fairness/scheduling policy beyond quotas | C017, C028 | Defined fairness algorithm, queue policy if any, transport connection/resource limits, and starvation guarantees. |
| 10 | High | Complete constraint-precedence model | C019 | Document security/residency/SLO/cost conflict ordering and prove it in tests. |
| 11 | Critical | Boundary authentication | C023, C044 | Node, peer, artifact, provider, and control-plane authentication/attestation before trust. |
| 12 | Critical | Authorization/capability enforcement | C024, C042 | Explicit least-privilege capability model for transfer submission, completion, policy update, transport access, and diagnostics. |
| 13 | High | Timeout and bounded retry subsystem | C025, C053 | Timeouts plus safe retry classification, attempt ceilings, exponential backoff, jitter, cancellation propagation. |
| 14 | High | Concrete adjacent-layer integration suite | C030, C083 | Executable fixtures that instantiate all supported adjacent layers rather than conditional hooks only. |
| 15 | Medium | Immutable artifact/release packaging model | C032, C040 | Reproducible install/build artifact, deterministic bootstrap from empty node, and explicit mutable-state/config locations. |
| 16 | Medium | Declarative environment configuration | C033, C035 | Versioned declarative config format with environment overlays, schema validation, and secure defaults. |
| 17 | High | Durable configuration history and rollback controller | C038, C092 | Persist prior revisions, automated rollback/canary/staged rollout, and emergency-disable mechanism. |
| 18 | High | Full reviewed threat model | C041, C050, C087 | Reviewed attacker/use-case matrix with mitigations and tests for malicious tenants, compromised workloads, supply chain, control-plane abuse, replay/spoofing/escape/side channels. |
| 19 | High | Enforced ambient-authority sandboxing | C043 | Capability/sandbox controls proving transports cannot silently gain filesystem/network/device/kernel/secret authority beyond their grants. |
| 20 | Critical | Signed classification/provenance integration | C045, C048 | GAP-07 or equivalent signed-label/provenance verification wired into admission, with outage behavior and trust-root rotation. |
| 21 | Critical | End-to-end payload integrity implementation | C045 | INV-37 or equivalent digest generation, transfer binding, receiver verification, mismatch quarantine, and evidence. |
| 22 | Critical | Strong tenant/workload isolation | C046 | Process/memory/network/device/buffer isolation between hostile tenants; current quota/accounting is not an isolation boundary. |
| 23 | Critical | Encryption and managed key lifecycle | C047, C048 | TLS/mTLS or equivalent in transit, at-rest protection where applicable, KMS/HSM integration, rotation/revocation, key-service outage semantics. |
| 24 | Critical | Tamper-evident security audit ledger | C049 | Append-only/cryptographically chained security events for admissions, refusals, policy changes, completions, cancellations, and administrative actions. |
| 25 | High | Full failure model and stall detection | C051, C052 | Process/VM/node/site/provider/control-plane failure catalog plus automated health/stall timers and thresholds. |
| 26 | Critical | Residency-safe failover controller | C055 | Alternate destination/transport selection that never weakens residency/isolation/consistency during failover. |
| 27 | High | Quarantine/freeze/disable controls | C059 | Runtime/admin capability to freeze admission, quarantine a destination/transport, drain safely, and record the action. |
| 28 | High | Fault-injection recovery suite | C060 | Deterministic injected failures across dependency, node, site, process, policy, and transport paths with recovery objectives. |
| 29 | High | Performance baseline harness | C061 | Reproducible latency/throughput/startup/CPU/memory/storage/network/power benchmark tooling and retained baseline data. |
| 30 | High | Load/scale/recovery performance suite | C063, C064 | Steady, burst, overload, scale-out/in, recovery, per-workload and per-tenant overhead measurements. |
| 31 | Medium | Data-path efficiency profiling | C065, C066 | Copy/serialization/context-switch/hop analysis and real zero-copy/batching/shared-memory/RDMA/kernel-bypass evidence. |
| 32 | Medium | Edge power/thermal evidence | C068 | Power and thermal measurements where constrained edge deployment is supported. |
| 33 | High | Capacity model and performance release gate | C069, C070 | Predictive saturation/scaling model plus CI release blocking for throughput/tail-latency/density/startup regressions. |
| 34 | Medium | Dependency-aware health | C071 | Probe/report actual GAP/INV/PLN transport and policy dependencies, not only local runtime readiness. |
| 35 | High | Full metrics/export stack | C072 | Latency histograms, rates, backlog age, CPU/memory/network/resource metrics plus exporter/scrape integration. |
| 36 | High | Structured logging | C073 | Stable node/tenant/workload/component/operation IDs, event schema, redaction, sink, and tests. |
| 37 | High | Distributed tracing | C074 | Trace-context ingress/egress propagation across transport boundaries and export/provider integration. |
| 38 | Medium | Safe high-cardinality diagnostics | C075, C077 | Redacted operator explain/debug view linking decisions to policy/topology/constraints without leaking tenant/secret data. |
| 39 | Medium | Release lineage/infrastructure graph correlation | C078 | Correlation IDs/links to application release lineage and live infrastructure graph. |
| 40 | High | Telemetry governance | C079 | Retention, sampling, privacy, access, export, deletion, and cardinality policies. |
| 41 | High | Dashboards and alerting | C080 | Operational dashboards and alerts separating ordinary load, degradation, policy rejection, dependency failure, attack, and defect. |
| 42 | Medium | Exhaustive public-interface contract tests | C082 | Schema validation against emitted objects plus exhaustive boundary/version/error cases for all public APIs. |
| 43 | High | Platform/protocol compatibility test matrix | C084 | CI across supported CPU architectures, Python/runtime versions, hypervisors, providers, and transport protocol versions. |
| 44 | High | Fuzz/property-based testing | C085 | Fuzz schemas, identifiers, policy maps, completion records, and any future protocol parsers/handlers. |
| 45 | High | Benchmark/soak/burst/fleet tests | C088 | Long-duration soak, burst/stress, fleet-scale and resource-leak testing. |
| 46 | Critical | Disaster/partition/reconnect testing | C089 | Site/network partition, reconnect, degraded control plane, stale policy, replay, and recovery tests. |
| 47 | Critical | Machine-readable production acceptance evidence | C090, C100 | Current `pk_core` (or equivalent) gate results, evidence ledger, integrity verification, and formal production sign-off. |
| 48 | High | Vulnerability/patch/EOL policy | C094 | Patch cadence, security response SLA, CVE triage process, supported/EOL dates. |
| 49 | High | Durable-state backup/restore/reconstruction | C095 | Define whether open-transfer/policy state must persist; if so, implement backup/restore/migration/reconstruction and tests. |
| 50 | Medium | Production-complete runbooks | C096 | Expand current notes into tested deployment, rollback, drain, recovery, dependency-outage, and operator procedures. |
| 51 | Medium | Recurring control reviews | C098 | Scheduled access, policy, dependency, configuration and architecture review process with retained evidence. |
| 52 | Medium | Exception/waiver/technical-debt registry | C099 | Owner, rationale, risk, expiry, remediation, and deprecated-behavior tracking. |
| 53 | Critical | `pk_core` certification framework availability | C030, C090, C100 | Vendor/install/pin the compatible framework or provide a deterministic dependency acquisition path so conformance/gate tests actually execute. |
| 54 | Critical | GAP-13 policy engine integration | C003, C004, C030 | Fetch/version/authenticate authoritative residency/classification policy instead of constructor-only local input. |
| 55 | High | GAP-14 data-gravity manager integration | C003, C011, C030, C066 | Supply authenticated locality/gravity hints and prove they never override residency. |
| 56 | Critical | PLN-03 distributed runtime integration | C003, C030, C083 | Real hand-off of non-inline payload decisions to the distributed runtime and lifecycle/error propagation. |
| 57 | Critical | INV-37 bulk data-plane integration | C003, C045, C030, C083 | Concrete bulk transport, digest generation/verification, chunk/reassembly behavior, failure handling, and tests. |
| 58 | Critical | INV-36 control-transport isolation proof | C003, C030, C083 | Prove non-inline payload bytes cannot traverse the control transport and measure/control-path starvation. |
| 59 | Medium | Missing original `MASTER.md` source artifact | Repository hygiene | The input README claimed it was shipped, but it was absent. Restore it only from the authoritative source; do not synthesize a supposedly verbatim copy. |
| 60 | Medium | Python distribution/build metadata | Repository hygiene | No `pyproject.toml`/build metadata/lock strategy defines installability, supported Python, package data, or reproducible dependencies. |
| 61 | High | CI pipeline | C070, C084, C090 | No checked-in CI executes tests, optimized mode, schema checks, compatibility matrix, security scans, packaging, benchmarks, or gate evidence. |
| 62 | High | SBOM/dependency provenance/vulnerability scanning | C041, C045, C094 | No SBOM, dependency lock/provenance, signature verification pipeline, or automated vulnerability scanning evidence. |
| 63 | Medium | License file | Repository hygiene | No repository license is present; legal distribution/use terms are therefore not established by this archive. |
| 64 | Medium | Static analysis/type/lint configuration | C050, C081-C087 | No checked-in ruff/mypy/bandit (or equivalent) configuration or CI evidence; these tools were also unavailable in the audit environment. |

## Important external-dependency distinction

The repository's `component.py` correctly reports GAP-07 and INV-37 dependent findings as partial when those siblings are absent. That behavior is retained. The post-audit does **not** convert an external declaration such as “the peer will verify this later” into evidence that the standalone component already implements it.

The same rule applies to `pk_core`: the adapter can participate in the 100-item certification framework, but because the framework was not in the supplied archive or audit environment, its all-100 gate could not be re-executed here. The new standalone tests are therefore intentionally independent of that framework.

## Recommended closure order

1. Wire and pin the authoritative policy, signed-classification, concrete bulk/control transport, and distributed-runtime dependencies.
2. Add authentication/authorization, encryption/key lifecycle, payload-integrity verification, durable state/replay semantics, and tamper-evident audit events.
3. Build concrete transport adapters plus integration/partition/fault/security tests.
4. Add production telemetry/logging/tracing, benchmark/capacity evidence, CI gates, SBOM/vulnerability controls, and compatibility matrices.
5. Finish ownership, incident, rollout, patch/EOL, exception, and production-exit governance; then re-run the full external certification gate and archive the machine-readable evidence.

## Files added or materially changed in 4.2.0

- `data_plane.py` — dependency-free hardened runtime
- `metadata.py` — shared version/element metadata
- `component.py` — thinner `pk_core` certification adapter using hardened runtime
- `__init__.py` — lazy certification exports; standalone runtime exports
- `tests/test_runtime.py` — dependency-free regression/concurrency/config/schema tests
- `tests/test_component.py` — version pin updated to 4.2.0
- `schemas/*.schema.json` — versioned interface schemas
- `docs/ADR-0001-data-plane.md` — proposed architecture decision
- `SECURITY.md` — implemented controls and residual risks
- `OPERATIONS.md` — lifecycle/config/failure/operator semantics
- `COMPATIBILITY.md` — backward-compatibility and missing matrix evidence
- `TRACEABILITY.md` — all 100 requirements with Implemented/Partial/Missing status
- `README.md`, `CHANGELOG.md`, `VERSION` — corrected documentation and versioning
