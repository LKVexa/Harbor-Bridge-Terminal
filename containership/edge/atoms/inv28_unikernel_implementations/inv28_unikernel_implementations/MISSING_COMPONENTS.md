# INV-28 Missing Components — Post-Hardening Audit (v4.2.0)

> **Historical (v4.2.0 input).** All 100 items were worked in v4.3.0; their current status, owner, implementation, tests, evidence and remaining blockers are in `ops/MC_STATUS.md` (source `ops/MC_STATUS.json`). This file is kept unchanged below as the audit baseline.

This list records every concrete repository-level component that can be identified as missing from the supplied archive after the v4.2.0 hardening pass. It intentionally does not fabricate external evidence or upstream components.

## A. Declared-but-absent repository artifacts

1. **`MASTER.md`** — README lineage says the 100 per-item master prompt/workflow documents exist, but the file is absent.
2. **`pk_core` dependency/package** — required by `component.py`, `contract.py`, and the conformance tests, but not supplied.
3. **Dependency/install manifest** — no `pyproject.toml`, `requirements.txt`, `setup.cfg`, `setup.py`, lockfile, or equivalent describes how to obtain `pk_core` or install this package.
4. **Machine-readable interface schema for `PK_TOOLCHAIN/1`** — interface is named in the contract but no JSON Schema, WIT, protobuf, OpenAPI, or equivalent schema is present.
5. **Machine-readable interface schema for `PK_TOOLCHAIN_SELECTION/1`** — same gap for selection output.
6. **Example register data / supported-toolchain catalog** — no persisted MirageOS/Unikraft/OSv/etc. registry dataset exists; examples live only inside assessment code.
7. **License file** — no `LICENSE` or equivalent licensing artifact is present.
8. **Contribution/security policy** — no `SECURITY.md`, vulnerability-reporting instructions, or maintainer escalation metadata.

## B. Toolchain model and selection capability gaps

9. **Toolchain version field** — entries cannot distinguish supported upstream versions/releases.
10. **Runtime/profile field** — contract ownership includes language/runtime support, but the model stores only language and architecture.
11. **Device-support model** — the repository description explicitly says implementations differ by device set, but `Toolchain` has no device capability field.
12. **Feature/capability model** — selection can only match language and architecture; it cannot enforce workload feature requirements.
13. **Hypervisor/VMM compatibility metadata** — no supported VMM/hypervisor matrix per implementation.
14. **Provider/platform compatibility metadata** — no cloud/edge/bare-metal provider support matrix.
15. **Protocol/ABI compatibility metadata** — no ABI, WIT/component-model, network-stack, filesystem, or API compatibility information.
16. **Security-response metadata beyond a boolean** — `security_contact` records existence only; there is no contact identity/reference, response SLA, advisory feed, or disclosure policy.
17. **Security-review provenance** — `reviewed_at` is a logical integer only; no reviewer, evidence URI/hash, review result, or real timestamp is recorded.
18. **Per-toolchain review interval** — only one global `REVIEW_INTERVAL` exists; no implementation-specific cadence.
19. **Known limitation semantics in selection** — limitations are now representable but are not structured or evaluated against workload requirements.
20. **Explicit deprecation/EOL status** — no lifecycle state prevents selection of deprecated or end-of-life implementations.
21. **Toolchain integrity identity** — no digest, signed release identity, provenance/SBOM reference, or immutable version pin exists to prevent substitution between selection and build.
22. **Policy-driven selection rules** — production logic is hard-coded; there is no injected policy set, environment policy version, waiver model, or tenant/site policy evaluation.
23. **Selection request schema/object** — selection accepts loose keyword strings rather than a validated workload-requirements object.
24. **Selection result type** — returns an untyped dictionary rather than a validated immutable result object/schema-bound record.
25. **Stable reason codes** — elimination/refusal reasons are human strings only; no machine-readable reason enum/code.
26. **Explicit refusal object** — failure is an exception with interpolated text; no structured refusal record listing unmet constraints.
27. **Register update/remove lifecycle** — register supports add only; there is no controlled update, retire, remove, or replace operation.
28. **Registry persistence** — entries are in-memory only; no durable source of truth or serialization/deserialization path.
29. **Registry concurrency control** — no locking/versioning/CAS semantics for concurrent updates.
30. **Registry authenticity/integrity verification** — no signature/hash verification for loaded registry data.

## C. Security and supply-chain gaps

31. **Threat-model artifact** — threats are short contract strings; no dedicated threat model with assets, actors, trust boundaries, mitigations, and test mappings.
32. **SBOM** — no SPDX/CycloneDX or equivalent software bill of materials.
33. **Dependency vulnerability scan configuration/evidence** — no scanner configuration or results.
34. **Static-analysis configuration/evidence** — no Ruff/Pylint/Bandit/Semgrep/mypy configuration or recorded run.
35. **Secret scanning configuration/evidence** — no secret-scanning policy or result.
36. **Artifact signing/provenance** — no signing, SLSA provenance, attestations, checksums, or release verification workflow.
37. **CVE/advisory ingestion** — optional automated upstream CVE tracking is not implemented.
38. **Security exception/waiver mechanism** — no structured exception with owner, scope, approval, and expiry.

## D. Tests and certification gaps

39. **Self-contained unit tests for `Toolchain` validation** — the shipped test file primarily checks inherited `pk_core` conformance and does not directly cover all domain validation cases.
40. **Public-interface contract tests** — no schema/interface tests for register/select payload compatibility.
41. **Integration tests with `INV-27 Unikernel execution`** — declared downstream dependency is not exercised.
42. **Integration tests with `GAP-15 Runtime compatibility certification`** — declared upstream dependency is not exercised.
43. **Integration tests with `GAP-08 OTA lifecycle/rollback`** — optional peer dependency is not exercised.
44. **Cross-architecture compatibility tests** — no executable x86_64/aarch64 compatibility matrix.
45. **Cross-toolchain/version compatibility tests** — no matrix for MirageOS/Unikraft/OSv/Nanos versions.
46. **Fuzz/property tests** — no fuzzing or property-based testing for register inputs and selection constraints.
47. **Concurrency/race tests** — absent.
48. **Threat-derived security tests** — absent as a dedicated suite.
49. **Benchmark suite** — no startup, selection latency, registry scale, memory, throughput, or tail-latency benchmarks.
50. **Soak/burst/fleet-scale tests** — absent.
51. **Disaster/partition/reconnect/degraded-control-plane tests** — absent/not modeled.
52. **Machine-readable production acceptance evidence** — no generated certification artifact is included.
53. **Coverage report/threshold** — no test coverage configuration or evidence.
54. **Mutation testing** — no evidence that refusal/safety branches resist test mutation.
55. **`python -O` full-suite evidence in this archive** — test exists, but cannot run without external `pk_core`.

## E. Observability and explainability gaps

56. **Runtime health/readiness endpoint or function** — absent.
57. **Version/config/dependency-status endpoint** — absent beyond static package version metadata.
58. **Metrics emission** — contract names signals, but no metrics implementation/exporter exists.
59. **Structured logging** — no logger, event schema, stable operation IDs, tenant/workload IDs, or redaction policy.
60. **Trace propagation** — absent.
61. **Safe high-cardinality diagnostics** — absent.
62. **Decision audit log** — returned `reason`/`eliminated` values are ephemeral; no durable selection-decision ledger exists.
63. **Operator explain view** — no CLI/API/report tying selection to policy, input state, compatibility evidence, and constraints.
64. **Release-lineage/infrastructure-graph correlation** — absent.
65. **Telemetry retention/sampling/privacy/export policy** — absent.
66. **Dashboards and alert definitions** — absent.

## F. Resilience and operational gaps

67. **Persistent backup/restore/reconstruction procedure** — no registry persistence means no implemented backup/restore mechanism.
68. **Canary/staged rollout implementation** — README references gate behavior generally, but there is no component-specific rollout automation.
69. **Rollback implementation** — prose references an evidence head, but no component-owned rollback command/state transition exists.
70. **Emergency-disable implementation** — prose says remove from registry package; no explicit disable/quarantine state or safe administrative operation exists.
71. **Supported-version compatibility matrix** — absent.
72. **Patching/vulnerability-response/EOL SLAs** — absent as an operational policy artifact.
73. **Incident response runbook** — no severity, paging, escalation, containment, recovery document.
74. **Recurring review automation** — no job/workflow for access, policy, dependency, configuration, architecture, or security-review freshness.
75. **Technical-debt/deprecation register** — absent.
76. **Formal production exit-gate artifact** — depends on external `pk_core`; no resulting gate report is shipped.
77. **Capacity model and saturation thresholds** — absent.
78. **Resource bounds** — no bounds on registry size, input token lengths, elimination-output size, or selection work.
79. **Timeout/cancellation semantics** — absent (currently local/synchronous, but no defined boundary for future external checks).
80. **Cache/locality behavior** — no compatibility-result cache or defined invalidation strategy.

## G. Packaging, automation, and repository hygiene gaps

81. **CI workflow** — no GitHub Actions/Azure Pipelines/etc. configuration.
82. **Reproducible environment/lockfile** — absent.
83. **Build/package configuration** — absent.
84. **Release automation** — absent.
85. **Generated artifact/checksum manifest** — absent.
86. **Code-format/lint configuration** — absent.
87. **Type-checking configuration** — absent despite type annotations.
88. **Pre-commit hooks** — absent.
89. **Developer setup instructions** — README assumes `pk_core` exists but does not provide a deterministic install/bootstrap path.
90. **Architecture/design document** — no dedicated data-flow, trust-boundary, lifecycle, or dependency diagram/document.
91. **Schema/version migration plan** — no plan for registry/interface schema evolution.
92. **Examples/fixtures directory** — absent.
93. **Changelog release links/evidence references** — changelog describes gates but does not point to immutable test/evidence artifacts.

## H. Scope/contract inconsistencies still requiring an upstream decision

94. **Production maturity wording is ambiguous.** Contract boundary text says production “may permit only mature toolchains,” while mandatory logic only excludes `experimental`, so `beta` remains selectable. The implementation preserves the existing mandatory/SLO interpretation rather than silently changing policy.
95. **OSv is named in repository documentation but not represented by any shipped registry entry or fixture.**
96. **Review time uses abstract logical ticks rather than wall-clock timestamps.** This is deterministic for tests but insufficient as a production security-review freshness record without an upstream time/provenance design.
97. **Toolchain selection does not consume `GAP-15` certification output.** The contract says that dependency certifies tested toolchain/profile pairs, but the selector currently trusts local fields only.
98. **Selection/build anti-substitution is not enforced.** The threat is declared, but the selected record contains no immutable artifact/toolchain digest for downstream binding.
99. **Site boundary is declared but not enforced.** The contract says a site supports a subset of architectures, but `select()` receives no site capability context.
100. **Workload feature needs are declared but not modeled.** The workload boundary says workloads declare language and feature needs, yet `select()` accepts only language, architecture, environment, and logical time.

## Summary

The v4.2.0 pass fixes concrete correctness and hardening defects in the code that is actually present. The remaining 100 items above are missing production components, absent evidence, external dependencies, or contract-to-implementation gaps that cannot be truthfully manufactured from the standalone archive. The highest-priority closure items are: add a real registry schema/catalog with immutable toolchain versions and capability/security metadata; bind selection to GAP-15 certification and artifact identity; ship/install `pk_core` reproducibly; add interface schemas and direct unit/integration/security tests; and create CI plus machine-readable release evidence.
