# INV-70 Post-Update Audit Report — v4.2.0

**Audit date:** 2026-09-22  
**Scope:** supplied archive, patched repository, dependency-free runtime tests, optimized-mode tests, randomized bounded-program campaign, and a second-pass local-evidence audit against all 100 `CHECKLIST.json` requirements.

## Executive result

- Version bumped **4.1.0 → 4.2.0**.
- The custom stack runtime was materially hardened, but the repository still **does not implement the checklist-required per-operation Wasm sandbox**.
- `pk_core` is not included/installed in the supplied repository, so the framework conformance suite cannot be independently executed here; its three tests skip. A skip is not counted as certification.
- The previous README referenced `MASTER.md`, but no such file was present. The claim was corrected; the missing source artifact was not fabricated.
- Post-update checklist evidence: **12 PRESENT, 35 PARTIAL, 50 MISSING, 3 NOT_APPLICABLE**.

## Defects fixed / hardening applied

1. **Real logical memory ceiling:** added `max_memory_bytes` and `max_value_bytes`; stack depth alone is no longer described as the entire memory boundary.
2. **Program-size ceiling:** added `max_program_instructions` and exact program/instruction container validation.
3. **Exact opcode arity:** missing/extra operands now trap as `invalid instruction` instead of being ignored or misreported as stack underflow.
4. **Validated jumps:** targets must be exact integers and in range.
5. **Python object escape hardening:** guest values are restricted to exact inert scalar types, blocking attacker-controlled magic methods such as `__add__`/`__mul__` from executing ambient Python.
6. **Bounded expansion:** integer multiplication and string/bytes growth are preflighted before potentially large allocations.
7. **Deterministic operand order:** `add` now uses conventional stack order (`left op right`), fixing reversed string concatenation.
8. **Capability hardening:** capability names are validated; denied, unbound, and non-callable capabilities have distinct deterministic traps.
9. **Host-boundary hardening:** capability identifiers are bounded/sanitized, host lookups and return values are guarded, non-finite floats are rejected, and ordinary host exceptions are converted to class-only trap reasons so exception messages do not leak secrets.
10. **Configuration validation:** bool/negative resource limits, invalid capability collections, invalid host mappings, and impossible value-vs-memory limits fail closed.
11. **Runtime/framework separation:** moved execution into dependency-free `runtime.py`, allowing real tests even when `pk_core` is unavailable.
12. **Security truthfulness:** README/component documentation now states that host callbacks are trusted and that this Python VM is not the required Wasm isolation layer.

## Validation performed

- `python -m py_compile` over package and tests: **PASS**.
- `python tests/test_runtime.py`: **12/12 PASS**.
- `python -O tests/test_runtime.py`: **12/12 PASS**.
- 20,000 deterministic randomized bounded programs: **PASS** with no uncaught exceptions and all returned fuel values within configured limits.
- `python tests/test_component.py`: **3 SKIPPED** because `pk_core` is unavailable; this is an unresolved dependency/evidence gap, not a failure in `runtime.py`.

## Highest-priority missing components

1. **Production per-operation Wasm sandbox** plus approved/pinned engine/specification, import policy, linear-memory/table limits, epoch/fuel interruption, and module validation (`C010`, `C031`).
2. **Pinned `pk_core` dependency and reproducible package/bootstrap metadata**, so the 100-item conformance suite can actually run instead of skip (`C031`, `C040`, `C082`, `C100`).
3. **Approved ADR and ownership/escalation records** (`C009`, `C010`).
4. **Typed external schemas/WIT/IDL and compatibility policy** for run/result/hostcall (`C022`, `C026`, `C027`, `C093`).
5. **Identity/authentication/attestation and artifact provenance/signature verification** (`C023`, `C044`, `C045`, `C048`).
6. **Bounded host-call execution layer** with timeout/cancellation/backpressure/admission control/idempotency semantics; the in-process callback remains outside guest pre-emption (`C025`, `C054`, `C058`).
7. **Tamper-evident audit + real observability pipeline** (metrics/logs/traces/health/explain/dashboard/retention) (`C049`, `C071`–`C080`).
8. **Integration/fuzz/fault/performance/soak/compatibility certification suites and machine-readable release evidence** (`C030`, `C060`–`C070`, `C083`–`C090`).
9. **Deployment/release governance artifacts**: rollout, vulnerability/EOL, incident response, reviews, waivers/debt, formal exit gate (`C092`–`C100`).
10. **Original `MASTER.md` source artifact** referenced by the pre-audit README; source content was not available, so it remains missing rather than reconstructed and mislabeled as verbatim.

## Complete 100-requirement post-update matrix

| ID | Status | Evidence | Remaining gap |
|---|---|---|---|
| INV-70-C001 | **PRESENT** | contract.py responsibility | Production responsibility is explicitly stated. |
| INV-70-C002 | **PRESENT** | contract.py owns/not_owns | Ownership and exclusions are explicit. |
| INV-70-C003 | **PRESENT** | contract.py dependencies | Upstream, peer, and downstream dependencies are listed. |
| INV-70-C004 | **PRESENT** | contract.py source_of_truth | Fuel/memory counters are named as authoritative runtime state. |
| INV-70-C005 | **PARTIAL** | contract.py assumptions | Assumptions exist but are generic and do not fully cover runtime, storage, network, node, and control-plane failure assumptions. |
| INV-70-C006 | **PRESENT** | contract.py boundaries | Tenant, environment, site, and workload boundaries are defined contractually. |
| INV-70-C007 | **PRESENT** | contract.py mandatory/optional | Mandatory and optional capabilities are separated. |
| INV-70-C008 | **PRESENT** | contract.py non_goals | Unsupported/native-code, network-by-default, and persistence patterns are declared. |
| INV-70-C009 | **MISSING** | — | No accountable human/team owner, on-call alias, or escalation path is shipped. |
| INV-70-C010 | **MISSING** | — | No approved ADR exists; additionally, the required per-operation Wasm technology is not implemented. |
| INV-70-C011 | **PARTIAL** | contract.py mandatory; RUNTIME_SPEC.md | Runtime obligations are testable in places, but there is no complete SHALL-level requirements specification covering the source function. |
| INV-70-C012 | **MISSING** | — | No cloud/datacenter/near-edge/far-edge applicability and behavior matrix. |
| INV-70-C013 | **PARTIAL** | contract.py slos | Termination/containment/startup SLOs exist, but availability, isolation, determinism, and other applicable NFRs are not fully specified. |
| INV-70-C014 | **PARTIAL** | runtime.py result/trap shape | Success and terminal traps are defined; partial success, degraded, retryable, and terminal classes are not formally modeled. |
| INV-70-C015 | **MISSING** | — | No lifecycle state model or legal transition table. |
| INV-70-C016 | **PARTIAL** | VERSION; CHANGELOG.md; RUNTIME_SPEC.md | Version is explicit and 4.2.0 preserves result shape, but there is no supported backward-compatibility/deprecation policy. |
| INV-70-C017 | **PARTIAL** | runtime.py bounded limits | Per-run fuel/stack/value/memory/program limits exist; tenant quotas and fairness are absent. |
| INV-70-C018 | **PARTIAL** | contract.py non_goals; SECURITY.md | Core guest has no network authority, but behavior for unavailable/intermittent network-dependent host capabilities is not defined. |
| INV-70-C019 | **MISSING** | — | No precedence policy for conflicts among security, residency, SLO, and cost. |
| INV-70-C020 | **MISSING** | — | No requirements traceability matrix mapping all 100 requirements to implementation and evidence. |
| INV-70-C021 | **PRESENT** | contract.py interfaces | run/result/hostcall boundaries are enumerated. |
| INV-70-C022 | **PARTIAL** | contract.py interface names | Interfaces carry /1 names, but there are no WIT/JSON Schema/IDL artifacts or schema validators. |
| INV-70-C023 | **MISSING** | — | No authentication model for caller, workload, node, peer, artifact, or control plane. |
| INV-70-C024 | **PARTIAL** | runtime.py capability gate | Host calls enforce explicit capabilities, but authorization is not defined for every external boundary and is not identity-bound. |
| INV-70-C025 | **MISSING** | — | No timeout/cancellation/retry/idempotency/backpressure contract for host calls or orchestration. |
| INV-70-C026 | **PARTIAL** | runtime.py trap strings | Failures are machine-readable at the top level but lack stable enumerated error codes and structured details. |
| INV-70-C027 | **MISSING** | — | No peer-version negotiation or mixed-version compatibility rules. |
| INV-70-C028 | **PARTIAL** | runtime.py limits; RUNTIME_SPEC.md | Guest execution limits are documented; concurrency, queue, connection, and embedding limits are not. |
| INV-70-C029 | **PARTIAL** | tests/test_runtime.py; RUNTIME_SPEC.md | Reference examples/tests exist, but no portable conformance fixture set for external implementations. |
| INV-70-C030 | **MISSING** | — | No integration tests with INV-69, INV-09, INV-71, GAP-09, or a Wasm layer. |
| INV-70-C031 | **MISSING** | — | Checklist requires a pinned per-operation Wasm sandbox implementation/specification; repository contains a custom Python VM and no pinned Wasm runtime. |
| INV-70-C032 | **PARTIAL** | runtime.py stateless execution | Runtime state is per-run and ephemeral, but immutable artifact vs mutable configuration/state packaging is not formally defined. |
| INV-70-C033 | **PARTIAL** | runtime.py defaults | Secure code defaults exist, but there is no declarative configuration schema/file. |
| INV-70-C034 | **PARTIAL** | runtime.py configuration validation | Runtime limit/capability parameters are validated; no deployment configuration activation pipeline exists. |
| INV-70-C035 | **MISSING** | — | No site/environment overlay mechanism independent of rebuilding artifacts. |
| INV-70-C036 | **MISSING** | — | No configuration provenance record with version, author, source digest, and activation time. |
| INV-70-C037 | **MISSING** | — | No atomic/transactional configuration update mechanism. |
| INV-70-C038 | **PARTIAL** | README.md day-0/day-1/day-2 | Rollback is discussed at a high level; no executable automatic/operator rollback control exists. |
| INV-70-C039 | **PARTIAL** | SECURITY.md; runtime.py host error redaction | No ordinary secret store is present and host exception messages are redacted, but no formal secret/config/diagnostic handling policy exists. |
| INV-70-C040 | **PARTIAL** | README.md bootstrap commands | Bootstrap commands are documented, but package metadata and the required pk_core dependency are not bundled/pinned, so empty-node bootstrap is not reproducible. |
| INV-70-C041 | **PARTIAL** | contract.py threats; SECURITY.md | Threats and residual limitations are documented, but malicious-tenant, supply-chain, control-plane abuse, replay/spoofing, and side-channel analysis is incomplete. |
| INV-70-C042 | **PARTIAL** | runtime.py capset enforcement | Capabilities are deny-by-default, but identities/roles/service accounts and least-privilege deployment permissions are not modeled. |
| INV-70-C043 | **PRESENT** | runtime.py; SECURITY.md | Guest bytecode has no ambient filesystem/network/device/kernel/secret primitive; host authority requires an explicit granted callback. |
| INV-70-C044 | **MISSING** | — | No node/peer/artifact/provider/control-plane authentication or attestation. |
| INV-70-C045 | **MISSING** | — | No signature, digest, provenance, SBOM, or approved-version verification path for executable/policy artifacts. |
| INV-70-C046 | **PARTIAL** | runtime.py clean per-run stack | Runs start with fresh guest state; tenant/workload identity binding and process-level memory/network/device isolation are not implemented. |
| INV-70-C047 | **NOT_APPLICABLE** | contract.py non_goals | Core runtime owns neither persistent storage nor network transport; encryption belongs to embedding boundaries. This N/A must be revisited if either is added. |
| INV-70-C048 | **MISSING** | — | No explicit fail-closed behavior for unavailable identity, attestation, policy, key, or time services. |
| INV-70-C049 | **MISSING** | — | No tamper-evident/append-only security audit event sink. |
| INV-70-C050 | **PARTIAL** | tests/test_runtime.py | Resource exhaustion, capability denial, malformed input, object-magic-method execution, and host-error leakage are tested; replay, spoofing, side-channel, supply-chain, and broader escape campaigns are absent. |
| INV-70-C051 | **PARTIAL** | contract.py failure_modes | Guest runtime failures are enumerated, but process/VM/node/site/network/provider/dependency/control-plane failure matrices are absent. |
| INV-70-C052 | **PARTIAL** | runtime.py fuel | Fuel deterministically bounds guest instruction stalls, but no component health/readiness/stall detector or thresholds exist for host callbacks/processes. |
| INV-70-C053 | **MISSING** | — | No retry policy/backoff/jitter implementation or proof that operations are safe to retry. |
| INV-70-C054 | **MISSING** | — | No admission control, concurrency limiter, load shedding, or circuit breaker. |
| INV-70-C055 | **MISSING** | — | No failover policy across nodes/sites/providers and no residency/isolation constraints for failover. |
| INV-70-C056 | **MISSING** | — | No defined degraded mode for unavailable noncritical dependencies. |
| INV-70-C057 | **PRESENT** | contract.py non_goals; runtime.py local state | Core runtime has no persistent mutable state and starts each run from clean state; there is nothing to replay/resume internally. |
| INV-70-C058 | **MISSING** | — | No duplicate-execution/idempotency protection for side-effecting host callbacks or stale-controller ownership model. |
| INV-70-C059 | **PARTIAL** | README.md emergency disable description | Registry removal is described as an emergency disable concept; no first-class quarantine/freeze/disable control is implemented. |
| INV-70-C060 | **MISSING** | — | No fault-injection harness/results for dependency/process/node/site/control-plane recovery objectives. |
| INV-70-C061 | **MISSING** | — | No reproducible benchmark baseline artifact for latency, throughput, startup, CPU, memory, storage, network, or power. |
| INV-70-C062 | **PARTIAL** | contract.py startup p99 SLO | One p99 startup target is declared, but p50/p95/p99/worst-case thresholds across key metrics are absent and the target is unmeasured. |
| INV-70-C063 | **MISSING** | — | No steady/burst/overload/scale-out/scale-in/recovery performance suite. |
| INV-70-C064 | **MISSING** | — | No per-workload/per-tenant overhead measurements. |
| INV-70-C065 | **MISSING** | — | No serialization/copy/context-switch/network-hop/image/state duplication analysis. |
| INV-70-C066 | **MISSING** | — | No documented or measured locality/caching/direct-composition/batching/zero-copy/kernel-bypass optimization work. |
| INV-70-C067 | **PRESENT** | runtime.py; RUNTIME_SPEC.md | Fuel, stack, scalar, logical-memory, and program-length growth are bounded. |
| INV-70-C068 | **MISSING** | — | No edge-node power/thermal measurement methodology or results. |
| INV-70-C069 | **PARTIAL** | runtime.py hard limits | Hard limits provide local saturation boundaries, but there is no capacity model or operational saturation signal. |
| INV-70-C070 | **MISSING** | — | No benchmark gate that blocks releases on startup/density/throughput/tail-latency regression. |
| INV-70-C071 | **PARTIAL** | __init__.py VERSION exposure | Version is exposed; no health/readiness/config/dependency-status/active-capability status endpoint or view. |
| INV-70-C072 | **MISSING** | contract.py signals are declarations only | Counters/histogram names are declared but runtime emits no metrics for rate/errors/latency/saturation/backlog/resource use. |
| INV-70-C073 | **MISSING** | — | No structured logging with stable node/tenant/workload/component/operation identifiers. |
| INV-70-C074 | **MISSING** | — | No trace-context input/output propagation. |
| INV-70-C075 | **MISSING** | — | No safe high-cardinality diagnostic channel; redacting host exception messages is only a narrow safeguard. |
| INV-70-C076 | **PARTIAL** | runtime.py deterministic trap reasons | Termination/refusal reasons are returned, but no general decision record links every automated decision to inputs/policy. |
| INV-70-C077 | **MISSING** | — | No operator-readable explain view. |
| INV-70-C078 | **MISSING** | — | No correlation with release lineage or live infrastructure graph. |
| INV-70-C079 | **MISSING** | — | No telemetry retention/sampling/privacy/export policy. |
| INV-70-C080 | **MISSING** | — | No dashboards or alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defects. |
| INV-70-C081 | **PRESENT** | tests/test_runtime.py | Dependency-free unit tests cover deterministic opcode/resource/capability behavior. |
| INV-70-C082 | **PARTIAL** | tests/test_runtime.py; tests/test_component.py | Runtime interface behavior is tested; framework contract tests depend on external pk_core and are skipped when absent. |
| INV-70-C083 | **MISSING** | — | No tests with every supported adjacent architectural layer/execution tier. |
| INV-70-C084 | **MISSING** | — | No compatibility matrix/test execution across CPU architectures, Python runtimes, Wasm runtimes, hypervisors, providers, or protocol versions. |
| INV-70-C085 | **MISSING** | — | No fuzz harness/corpus/property-based campaign for bytecode/schema/untrusted input. |
| INV-70-C086 | **NOT_APPLICABLE** | runtime.py per-call local state | Core VM has no shared/distributed mutable runtime state. Reassess if shared caches/registries are introduced. |
| INV-70-C087 | **PARTIAL** | tests/test_runtime.py; SECURITY.md | Several threat-derived tests exist, but the full threat model categories are not covered. |
| INV-70-C088 | **MISSING** | — | No benchmark, soak, burst, or fleet-scale certification tests. |
| INV-70-C089 | **MISSING** | — | No disaster/partition/reconnect/degraded-control-plane test suite for embedding/deployment. |
| INV-70-C090 | **MISSING** | — | No machine-readable release acceptance evidence is shipped; CHECKLIST.json is a requirement list, not acceptance proof. |
| INV-70-C091 | **PARTIAL** | contract.py slos | Three SLOs/error-budget statements exist, but support commitments and measured evidence are absent. |
| INV-70-C092 | **PARTIAL** | README.md operations section | Rollback/emergency-disable concepts exist; no canary/staged rollout specification or executable rollback procedure. |
| INV-70-C093 | **MISSING** | — | No supported-version compatibility matrix for Python/pk_core/Wasm/adjacent components. |
| INV-70-C094 | **MISSING** | — | No patching, vulnerability response, security advisory, or end-of-life SLA/policy. |
| INV-70-C095 | **NOT_APPLICABLE** | contract.py non_goals | Core runtime persists no state, so backup/restore/migration is not applicable internally; deployment evidence/config still needs external reconstruction procedures. |
| INV-70-C096 | **PARTIAL** | README.md day-0/day-1/day-2 | Lifecycle guidance exists but is not an operator-grade runbook with prerequisites, commands, expected outputs, rollback, and escalation. |
| INV-70-C097 | **MISSING** | — | No incident severity/paging/escalation/containment/recovery procedure. |
| INV-70-C098 | **MISSING** | — | No recurring access/policy/dependency/configuration/architecture review cadence or owner. |
| INV-70-C099 | **MISSING** | — | No exception/waiver/technical-debt/deprecation register with owners and expiry dates. |
| INV-70-C100 | **PARTIAL** | README.md pk_core gate commands | A gate command is referenced, but there is no local gate policy/result/evidence and pk_core is absent, so formal exit readiness cannot be verified. |

## Repository-level omissions not represented cleanly by a single checklist row

- **`MASTER.md`**: referenced before the audit but absent from the supplied archive.
- **License/NOTICE**: no license grant or notice file is present; release/legal status is therefore undefined from this repository alone.
- **Package/build metadata**: no `pyproject.toml`, wheel metadata, dependency lock, or reproducible environment definition.
- **CI pipeline**: no workflow that runs tests, optimized-mode checks, fuzzing, benchmark gates, provenance/SBOM generation, or release gating.
- **SBOM/provenance/signatures**: no software bill of materials, build attestation, signed digest, or verification policy.
- **Generated conformance evidence**: no `evidence/` ledger or `conformance/PK_GATE_RESULTS.json` is shipped.

## Release disposition

**4.2.0 is a hardened reference runtime, not a production-complete Fast Agent Sandbox.** The dependency-free VM is substantially safer and better specified than 4.1.0, but production readiness remains blocked primarily by the absence of a real Wasm isolation engine, the unavailable/unpinned `pk_core` conformance dependency, identity/provenance controls, observability, integration/fuzz/fault/performance certification, and release/operations governance artifacts.
