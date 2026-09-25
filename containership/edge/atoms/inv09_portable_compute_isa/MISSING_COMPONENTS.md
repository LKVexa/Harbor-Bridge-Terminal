# INV-09 Portable Compute ISA — Missing Components

> **v4.3.0 status:** every item of the 2,704-item engineering checklist derived from this register has been executed and assessed - see `CHECKLIST_STATUS.md`. P0 components M01-M05 and M07-M13 are implemented in `prod/`; the production gate remains NO_GO.

This list is the post-v4.2.0 production gap register. Priorities reflect security and architectural dependency, not implementation effort.

## P0 — Required before treating INV-09 as a production Wasm validation boundary

1. **Raw Wasm binary decoder and structural validator** — parse magic/version, sections, lengths, ordering, uniqueness, indices, limits, and malformed encodings directly from bytes with bounded allocation and fail-closed errors.
2. **Wasm type validator** — validate function signatures, stacks, control flow, locals/globals, tables, memories, references, imports/exports, element/data segments, and proposal-specific typing rules.
3. **Byte-derived feature detector** — derive `used_features` from opcodes/sections/types actually present; never trust a manifest, header, or caller-provided feature list.
4. **Declared-capability source and binding rule** — define where declarations come from, authenticate them, and cryptographically bind them to the exact module digest.
5. **Specification/version registry** — pin supported WebAssembly Core/WASI/component-model proposal versions and map each recognized opcode/section/type to a feature identifier.
6. **Engine capability registry** — distinguish profile policy from what the selected runtime/engine build actually implements; refuse modules requiring unsupported engine capabilities.
7. **Canonical module digest** — SHA-256 or stronger content identity included in validation results so evidence cannot be replayed against different bytes.
8. **Validation-result attestation** — signed/tamper-evident record binding module digest, validator build, profile version, engine-capability version, policy version, timestamp/sequence, and result.
9. **Validation cache with safe invalidation** — cache only by immutable module digest plus every policy/spec/engine input that can affect the verdict.
10. **Execution admission gate** — runtime integration that makes a successful, current validation token mandatory before instantiation/execution; no bypass path.
11. **TOCTOU protection** — ensure the bytes executed are the same bytes validated, preferably via immutable content-addressed artifacts or descriptor/handle binding.
12. **Structured failure schema** — stable machine-readable error codes, section/offset context, feature IDs, policy rule IDs, retryability, and safe human detail.
13. **Parser resource governor** — byte, section, nesting-depth, type-count, function-count, table/memory, element/data, string/name, and compilation-complexity ceilings enforced during parsing, not after it.
14. **Fuzzing harness and malformed corpus** — coverage-guided fuzzing for binary parser/type validator, regression corpus for parser bombs, integer overflows, malformed LEB128, truncation, duplicate sections, deep nesting, and proposal edge cases.
15. **Differential validation harness** — compare acceptance/rejection and feature detection against multiple mature Wasm validators/runtimes to find semantic drift.

## P1 — Security, determinism, and compatibility

16. **Determinism specification** — normative rules for integer/float/SIMD behaviour, NaN handling, relaxed SIMD, atomics/threads, clocks, randomness, host calls, traps, resource exhaustion, and execution ordering.
17. **Host-import capability contract** — typed allowlist for imported functions/resources with explicit ambient-authority prohibition and capability scope.
18. **WASI policy adapter** — if WASI is supported, explicit preview/version mapping and denied-by-default filesystem, network, clock, random, environment, process, and device capabilities.
19. **Component Model / WIT validator** — validate component-model binaries, WIT worlds/interfaces, canonical ABI options, resource types, adapters, and version compatibility if components are in scope.
20. **Cross-architecture determinism certification** — same module/input corpus across x86-64, Arm64, and any supported edge ISA/runtime combinations with byte-for-byte or normatively equivalent outputs.
21. **Runtime/validator compatibility matrix** — certified validator version × Wasm spec/proposals × runtime engine/build × CPU architecture × OS/host ABI combinations.
22. **Profile schema and signed distribution** — versioned `PK_ISA_PROFILE/1` schema, provenance, signature, activation/rollback semantics, and immutable history.
23. **Policy-engine integration contract** — authenticated, authorized path from GAP-13 policy decisions to profile selection with downgrade protection and audit linkage.
24. **Runtime-hardening handoff contract** — explicit interface with INV-44 covering sandboxing, JIT/AOT protections, memory isolation, CFI, executable-memory policy, and engine CVE posture.
25. **Artifact provenance integration** — verify signatures/SBOM/provenance before validation and bind provenance identity into the verdict.
26. **Tenant isolation model for validation service** — quotas, fair scheduling, per-tenant caches/metrics policy, request authentication, and denial-of-service containment.
27. **Security audit event stream** — tamper-evident events for profile changes, validation refusals, bypass attempts, parser failures, policy changes, and admission decisions.
28. **Side-channel threat assessment** — parser timing, cache sharing, JIT/AOT metadata, feature probing, and multi-tenant information leakage analysis.

## P2 — Reliability, performance, observability, and operations

29. **Benchmark harness** — reproducible p50/p95/p99/worst-case latency, throughput, CPU, peak RSS, allocation count, and power/thermal measurements from tiny through 4 MiB modules.
30. **Release performance gate** — machine-readable thresholds that fail CI/release on validated regressions, including adversarial worst-case inputs.
31. **Soak and fleet-scale test suite** — sustained mixed-validity workloads, cache churn, profile rotation, restart, and dependency degradation.
32. **Fault-injection suite** — corrupted artifacts, partial reads, out-of-memory simulation, disk/cache failures, policy unavailability, validator crashes, stale configuration, and restart/replay tests.
33. **Health/readiness endpoint or contract** — validator build, active profiles, spec registry revision, engine capability revision, dependency status, and degraded state.
34. **Metrics implementation** — validated/refused/error counters, latency histograms by size/profile, cache hit ratio, parser resource usage, feature frequencies, and saturation signals with cardinality controls.
35. **Structured logging** — stable operation/module-digest/tenant/workload IDs, safe error details, policy/profile revisions, and secret/tenant-data redaction.
36. **Trace propagation** — correlation across artifact retrieval, policy selection, validation, admission, compilation, and runtime startup.
37. **Explain view** — operator-readable reason chain showing byte-derived facts, selected profile, policy version, exact refusal rule, and evidence identifiers.
38. **Dashboards and alerts** — distinguish normal refusals from malformed-input attacks, policy misconfiguration, dependency failures, performance saturation, and software defects.
39. **Canary/staged rollout controller** — validator/profile release rollout with compatibility prechecks, abort criteria, rollback, and emergency disable.
40. **Operational runbooks** — day-0 bootstrap, day-1 deployment, day-2 operation, incident containment, profile rollback, cache invalidation, evidence recovery, and emergency bypass policy (preferably no bypass).
41. **Vulnerability response and EOL policy** — supported-version windows, CVE triage SLAs, emergency runtime/validator revocation, and end-of-life enforcement.
42. **Configuration provenance store** — author, signer, revision, activation time, previous revision, and rollback target for profiles/spec registries/limits.
43. **Atomic configuration activation** — validate new profile/spec/engine-capability sets completely before switching; readers see one coherent revision.
44. **Backup/reconstruction procedure** — rebuild caches/evidence indices from immutable artifacts and signed configuration without relying on mutable local state.

## P3 — Packaging, governance, and completeness

45. **Package manifest / dependency pinning** — declare supported Python version, `pk_core` dependency/version range or workspace binding, build metadata, and reproducible installation path.
46. **SBOM and license inventory** — machine-readable SBOM for validator/runtime dependencies plus license and notice verification.
47. **Reproducible build metadata** — source revision, build recipe, toolchain versions, hashes, and deterministic packaging checks.
48. **Requirements traceability matrix** — each INV-09-C001…C100 mapped to concrete code/config/test/benchmark/runbook/evidence artifacts rather than generic base-class findings.
49. **Architecture Decision Records** — approved ADRs for WebAssembly spec baseline, feature profile model, deterministic profile, parser/runtime choice, and compatibility policy.
50. **Named ownership and escalation** — accountable service owner, security owner, runtime owner, on-call route, incident severity model, and exception/waiver authority.
51. **Exception/waiver register** — owner, rationale, compensating controls, scope, expiration, and reapproval requirements for every production deviation.
52. **Formal production exit gate** — machine-readable gate that refuses release unless parser/type validation, security, determinism, compatibility, performance, observability, rollback, provenance, and ownership evidence are current and passing.

## Important interpretation

The existing 100-item checklist and master prompts are a requirements framework; they are not themselves implementation evidence. The current `PortableComputeIsaComponent` can exercise selected policy behaviours, but a production certification should not mark all 100 requirements PASS until the concrete components and evidence above exist in the wider repository/runtime environment.
