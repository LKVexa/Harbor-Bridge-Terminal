# INV-41 Post-update audit

**Audited version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** files contained in this repository archive only. External estate components are not assumed present.

## Result

- VERIFIED: 15
- PARTIAL: 30
- MISSING: 51
- UNVERIFIED_EXTERNAL: 4

The security primitive itself is materially hardened and independently testable, but this repository is **not yet a complete production-ready implementation of all 100 checklist requirements**. The former claim that all 100 requirements were satisfied cannot be reproduced from this archive because `pk_core` is absent and the integration tests skip.

## Verified hardening

- Direct `Reference` construction is refused.
- References are sealed per authority domain, immutable, non-serializable, and token-redacted.
- Same-textual-ID impostor authorities are rejected because each authority has a distinct seal.
- Holders are immutable and bind only authentic references from the same authority domain.
- Attenuation fails closed on widening and revoked references cannot be delegated.
- Nested membrane revocation survives outer wrapping; live-descendant accounting includes derived references.
- Core imports/tests/self-checks no longer require `pk_core`.
- `PK_REFERENCE/1` and `PK_MEMBRANE/1` schemas are present.
- The hostile same-interpreter limitation is explicit in `SECURITY.md`.

## Verification executed

- `python -m compileall -q inv41_capability_security` — PASS
- `python inv41_capability_security/tests/test_primitives.py -q` — PASS (19 tests)
- `python -m inv41_capability_security.selfcheck` — PASS
- `python -O -m inv41_capability_security.selfcheck` — PASS
- `python inv41_capability_security/tests/test_component.py -v` — 3 tests SKIPPED because `pk_core` is unavailable

## All remaining missing/unverified component families

1. **Ownership and governance metadata** (C009) — Accountable owner and escalation path.
2. **Architecture decision record** (C010) — Approved ADR for explicit-capability technology and least-authority design.
3. **Formal requirements and operating semantics** (C011-C019) — SHALL requirements, deployment-context profile, NFRs, outcomes, lifecycle, compatibility, capacity, disconnected behavior, precedence.
4. **Traceability matrix** (C020) — Requirement -> implementation -> verification evidence mapping.
5. **Complete interface contract pack** (C021-C028) — Exhaustive boundary catalog, authn/authz, timeout/retry/backpressure, stable error codes, version compatibility, resource limits.
6. **Estate integration dependency and fixtures** (C030, C083, C090, C100) — pk_core and adjacent-layer fixtures/evidence/gate execution are absent from the archive.
7. **Pinned implementation/spec and dependency provenance** (C031, C045) — Approved implementation/spec reference, dependency lock/SBOM, artifact digest/signature/provenance verification.
8. **Configuration lifecycle subsystem** (C033, C036-C038) — Versioned config schema/defaults, provenance, activation metadata, transactional update and rollback.
9. **Full threat model** (C041, C050) — Tenant, hostile-input, supply-chain, control-plane, replay/spoofing/side-channel/resource-exhaustion analysis and tests.
10. **Stronger runtime isolation boundary** (C043, C046) — Process/Wasm/VM/hardware enforcement for adversarial code; pure Python object controls are insufficient.
11. **External identity/authentication integration** (C044, C048) — Node/peer/provider/control-plane authentication and fail-closed behavior when identity/attestation/key/time services are unavailable.
12. **Data protection policy** (C047) — Encryption/key-rotation applicability and controls for any sensitive adjacent data that leaves process-local references.
13. **Tamper-evident audit subsystem** (C049) — Security event ledger with integrity chaining/sealing and export policy.
14. **Infrastructure failure/resilience specification** (C051-C060) — Failure taxonomy, health/stall detection, retry policy, admission control, failover/degraded mode, crash semantics, split-brain disposition, fault injection.
15. **Performance engineering suite** (C061-C070) — Baselines, percentiles, load profiles, overhead, efficiency analysis, bounds, power/thermal, capacity model, regression gate.
16. **Health/metrics/logging/tracing stack** (C071-C074) — Runtime health/readiness/dependency status, metrics, structured logs and trace propagation.
17. **Diagnostics/explainability/telemetry operations** (C075-C080) — Safe high-cardinality diagnostics, reason records, explain view, lineage correlation, retention policy, dashboards/alerts.
18. **Exhaustive interface contract tests** (C082) — Tests for every public boundary/schema, beyond current core primitive behavior tests.
19. **Compatibility certification** (C084, C093) — Supported CPU/runtime/provider/protocol/version matrix and automated certification tests.
20. **Fuzz/property-based tests** (C085) — Fuzzing for policy/resource/operation inputs and any schema/protocol boundary.
21. **Expanded concurrency/race suite** (C086) — Stress races across grant/bind/attenuate/wrap/revoke/use and multi-membrane chains.
22. **Scale/soak/disaster test suites** (C088, C089) — Benchmark/soak/burst/fleet-scale plus partition/reconnect/degraded-control-plane tests.
23. **Support and release governance** (C091-C099) — Support commitments, canary/staged rollout, vulnerability/EOL SLA, state-reconstruction procedure, full runbooks, incident process, recurring reviews, waiver/debt ledger.
24. **Repository supply-chain metadata** (outside checklist) — No license/NOTICE, SBOM, signed release manifest, or reproducible build/package metadata is present; these are production packaging gaps beyond the 100-item checklist.

## 100-requirement status matrix

| Check | Status | Audit note |
|---|---|---|
| INV-41-C001 | VERIFIED | Production responsibility is defined in contract.py and README.md. |
| INV-41-C002 | VERIFIED | Owns/not-owns are explicit, including the hostile same-interpreter non-goal. |
| INV-41-C003 | VERIFIED | Upstream/downstream/peer dependencies are enumerated in contract.py. |
| INV-41-C004 | VERIFIED | The sealed capability + explicit Authority domain is defined as source of truth. |
| INV-41-C005 | PARTIAL | Some runtime assumptions are documented, but not a complete node/network/storage/control-plane assumption set. |
| INV-41-C006 | VERIFIED | Tenant/environment/site/workload boundaries are documented. |
| INV-41-C007 | VERIFIED | Mandatory and optional capabilities are separated. |
| INV-41-C008 | VERIFIED | Unsupported hostile same-interpreter isolation and other non-goals are documented. |
| INV-41-C009 | MISSING | No accountable human/service owner or escalation path is present. |
| INV-41-C010 | MISSING | No approved ADR artifact is present. |
| INV-41-C011 | PARTIAL | Security invariants exist, but there is no complete SHALL-level requirements specification. |
| INV-41-C012 | MISSING | No cloud/datacenter/near-edge/far-edge applicability profile is present. |
| INV-41-C013 | PARTIAL | Three zero-budget security SLOs exist, but latency/availability/determinism and other applicable NFRs are not fully specified. |
| INV-41-C014 | MISSING | No formal success/partial/degraded/retryable/terminal outcome model is present. |
| INV-41-C015 | MISSING | No lifecycle state machine or legal transition specification is present. |
| INV-41-C016 | MISSING | No backward-compatibility/versioning policy beyond the package version/changelog is present. |
| INV-41-C017 | MISSING | No capacity ceilings, quotas, or fairness model is present. |
| INV-41-C018 | MISSING | No explicit disconnected/intermittent-network semantics document is present. |
| INV-41-C019 | MISSING | No documented precedence rules among security/residency/SLO/cost constraints are present. |
| INV-41-C020 | MISSING | No requirement-to-implementation-to-evidence traceability matrix is present. |
| INV-41-C021 | PARTIAL | Core Python APIs are documented, but there is no exhaustive cross-layer boundary catalog. |
| INV-41-C022 | PARTIAL | Two result JSON schemas are provided; Python object/API contracts and all external boundaries are not schema-complete. |
| INV-41-C023 | PARTIAL | Authority-domain checks exist, but authentication requirements for every adjacent boundary are not defined. |
| INV-41-C024 | VERIFIED | Grant, holder binding, attenuation, use, and cross-authority rejection enforce explicit capability authorization. |
| INV-41-C025 | MISSING | No timeout/cancellation/retry/idempotency/backpressure contract is present. |
| INV-41-C026 | PARTIAL | Typed exception classes exist, but no stable machine-readable error-code/detail schema is defined. |
| INV-41-C027 | MISSING | No peer-version compatibility behavior is defined. |
| INV-41-C028 | MISSING | No payload/concurrency/queue/connection/resource-limit contract is present. |
| INV-41-C029 | VERIFIED | Standalone tests and selfcheck provide conformance examples/fixtures for the core primitives. |
| INV-41-C030 | UNVERIFIED_EXTERNAL | Adjacent-layer integration tests cannot be verified; pk_core and sibling layers are absent from this archive. |
| INV-41-C031 | PARTIAL | Version is pinned locally, but no approved implementation/specification/dependency lock is present. |
| INV-41-C032 | PARTIAL | Core policy/holders/references are immutable, but repository-wide artifact/config/state separation is not specified. |
| INV-41-C033 | PARTIAL | Authority policy is declarative in memory, but no versioned config file/schema/default-profile system exists. |
| INV-41-C034 | VERIFIED | Authority/resource/operation/holder inputs are validated and security failures fail closed. |
| INV-41-C035 | VERIFIED | Runtime bootstrap policy can vary by site/environment without rebuilding code. |
| INV-41-C036 | MISSING | No configuration provenance record with author/version/activation time is implemented. |
| INV-41-C037 | PARTIAL | Config is immutable after Authority creation, reducing partial-update risk, but there is no transactional reconfiguration protocol. |
| INV-41-C038 | MISSING | No automatic/operator configuration rollback mechanism is implemented. |
| INV-41-C039 | VERIFIED | References are process-local/non-serializable and tokens are redacted from repr; ordinary config carries no capability secret. |
| INV-41-C040 | VERIFIED | Dependency-free deterministic bootstrap/selfcheck exists. |
| INV-41-C041 | PARTIAL | SECURITY.md documents important threats and trust boundaries, but not a full tenant/supply-chain/control-plane threat model. |
| INV-41-C042 | VERIFIED | Explicit grant policy, immutable holders, narrowing delegation, and revocation implement least privilege. |
| INV-41-C043 | PARTIAL | The package itself does not open filesystem/network/device authority, but Python/runtime ambient authority is outside this layer and not eliminated. |
| INV-41-C044 | MISSING | No node/peer/artifact/provider/control-plane actor authentication subsystem is included. |
| INV-41-C045 | MISSING | No executable/policy artifact signature, digest, provenance, or approved-version verification pipeline is included. |
| INV-41-C046 | PARTIAL | Authority domains provide logical separation; process/memory/network/device isolation requires external sandboxing and is not implemented here. |
| INV-41-C047 | PARTIAL | References are process-local and non-serializable, but no broader encryption-at-rest/in-transit control is implemented/documented for adjacent data. |
| INV-41-C048 | PARTIAL | Fail-closed capability checks exist, but unavailable identity/attestation/policy/key/time service behavior is not fully specified. |
| INV-41-C049 | MISSING | No tamper-evident security audit event chain is implemented. |
| INV-41-C050 | PARTIAL | Privilege/widening/forgery/revocation tests exist, but replay/spoofing/side-channel/resource-exhaustion/adversarial coverage is incomplete. |
| INV-41-C051 | PARTIAL | Capability-specific failures are listed, but process/VM/node/site/network/provider/control-plane failure taxonomy is incomplete. |
| INV-41-C052 | MISSING | No health/stall thresholds or detector implementation is present. |
| INV-41-C053 | MISSING | No bounded retry/backoff/jitter policy is implemented/documented. |
| INV-41-C054 | MISSING | No admission control/load shedding/circuit breaker is present. |
| INV-41-C055 | MISSING | No failover design is present. |
| INV-41-C056 | MISSING | No degraded-operation mode is defined. |
| INV-41-C057 | PARTIAL | State is in-memory and rebuildable, but crash/restart/replay semantics are not formally specified. |
| INV-41-C058 | PARTIAL | No split-brain/stale-controller/duplicate-execution model is specified; relevance is not formally dispositioned. |
| INV-41-C059 | PARTIAL | Membrane revocation provides a disable primitive, but broader quarantine/freeze/isolation controls are absent. |
| INV-41-C060 | MISSING | No fault-injection recovery suite is present. |
| INV-41-C061 | MISSING | No reproducible latency/throughput/startup/CPU/memory/storage/network/power baseline exists. |
| INV-41-C062 | MISSING | No p50/p95/p99/worst-case thresholds exist. |
| INV-41-C063 | MISSING | No steady/burst/overload/scale/recovery performance suite exists. |
| INV-41-C064 | MISSING | No per-workload/per-tenant overhead measurements exist. |
| INV-41-C065 | MISSING | No measured analysis of serialization/copies/context switches/hops/duplication exists. |
| INV-41-C066 | MISSING | No benchmark-backed locality/caching/batching/zero-copy optimization program exists. |
| INV-41-C067 | MISSING | No explicit bounds for memory growth/concurrency/fan-out are documented or tested. |
| INV-41-C068 | MISSING | No edge power/thermal measurement exists. |
| INV-41-C069 | MISSING | No capacity model or saturation signals are implemented. |
| INV-41-C070 | MISSING | No performance-regression release gate exists. |
| INV-41-C071 | PARTIAL | Version and active held capabilities are inspectable, but no complete health/readiness/config/dependency status endpoint exists. |
| INV-41-C072 | MISSING | Signals are named in the contract but no metrics emitter/exporter is implemented. |
| INV-41-C073 | MISSING | No structured logging subsystem with stable node/tenant/workload/component/operation IDs is present. |
| INV-41-C074 | MISSING | No trace-context propagation is implemented. |
| INV-41-C075 | PARTIAL | repr redaction exists, but there is no high-cardinality diagnostic subsystem/privacy enforcement. |
| INV-41-C076 | MISSING | No automated-decision reason ledger is implemented. |
| INV-41-C077 | MISSING | No operator explain view is implemented. |
| INV-41-C078 | MISSING | No release-lineage/infrastructure-graph correlation is implemented. |
| INV-41-C079 | MISSING | No telemetry retention/sampling/privacy/export policy is present. |
| INV-41-C080 | MISSING | No dashboards or alert definitions are present. |
| INV-41-C081 | VERIFIED | 19 dependency-free unit/security tests cover deterministic core behavior and state transitions. |
| INV-41-C082 | PARTIAL | Core API behavior is tested, but no exhaustive schema/public-boundary contract suite exists. |
| INV-41-C083 | UNVERIFIED_EXTERNAL | Supported adjacent-layer integration tests are absent/unverifiable because required sibling layers/pk_core are not included. |
| INV-41-C084 | MISSING | No CPU/runtime/provider/protocol compatibility test matrix is present. |
| INV-41-C085 | MISSING | No fuzz/property-based harness for untrusted inputs or schemas is present. |
| INV-41-C086 | PARTIAL | One post-revocation concurrency test exists; broader race/stress coverage is incomplete. |
| INV-41-C087 | PARTIAL | Security tests cover direct construction, widening, cross-authority injection, same-ID impostors, revocation escape, and token leakage; broader threat-model tests remain. |
| INV-41-C088 | MISSING | No benchmark/soak/burst/fleet-scale test suite is present. |
| INV-41-C089 | MISSING | No disaster/partition/reconnect/degraded-control-plane suite is present. |
| INV-41-C090 | UNVERIFIED_EXTERNAL | Machine-readable estate acceptance evidence cannot be generated/verified without pk_core. |
| INV-41-C091 | PARTIAL | Three production security SLOs exist, but support commitments and a complete error-budget operating policy are absent. |
| INV-41-C092 | PARTIAL | README gives basic rollback/emergency guidance, but no canary/staged rollout procedure is defined. |
| INV-41-C093 | MISSING | No supported-version compatibility matrix is present. |
| INV-41-C094 | MISSING | No vulnerability response/patch/EOL SLA is present. |
| INV-41-C095 | PARTIAL | State is intentionally ephemeral/reconstructable, but formal backup/restore/migration applicability and procedure are incomplete. |
| INV-41-C096 | PARTIAL | Basic day-0/day-1/day-2 guidance exists, but it is not a full operational runbook. |
| INV-41-C097 | MISSING | No incident severity/paging/escalation/containment/recovery runbook is present. |
| INV-41-C098 | MISSING | No recurring access/policy/dependency/config/architecture review schedule/process is present. |
| INV-41-C099 | MISSING | No exception/waiver/technical-debt/deprecation ledger with owners/expiry exists. |
| INV-41-C100 | UNVERIFIED_EXTERNAL | Formal production exit gate remains external and cannot be executed without pk_core and the rest of the estate evidence chain. |

## Security conclusion

Version 4.2.0 is suitable as a **standalone capability-model/reference implementation and testable library primitive**. It is not sufficient by itself as a production security boundary for hostile same-interpreter code, nor does this archive contain the governance, observability, performance, resilience, integration, and certification machinery required by the complete 100-item production checklist. Those gaps are explicitly listed above and in the machine-readable JSON companion.
