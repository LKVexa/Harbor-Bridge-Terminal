# INV-30 Capability Hardware Sandbox — Post-Remediation Audit (4.3.0)

**Audited version:** 4.3.0 · **Audit date:** 2026-09-23 · **Auditor:** remediation pass (self-audit — an independent re-audit is still required)
**Scope:** this package, executed against the real estate `pk_core` 4.0.0 and siblings GAP-02, PLN-04, INV-41, INV-45
(UC270). No CHERI hardware, CHERI toolchain or emulator was available.

## Result

| | 4.2.0 | 4.3.0 |
|---|---|---|
| Tests | 10 pass, 3 skip (pk_core absent) | **111: 109 pass, 2 skip** (hardware conformance only) — identical under `python -O` |
| Framework conformance | not executable | runs; pk_core gate **CONDITIONAL_GO** (5 honest partials: C009, C010 sign-off; C031, C068, C084 hardware) |
| Release exit gate | none | **CONDITIONAL_GO_MODEL_ONLY**; hardware tier **NO_GO**; 0 invariant failures; 0 blockers; 3 sign-off conditions |
| Missing components | 71 | 0 absent; 37 closed pending sign-off; 34 partially closed with explicitly blocked items |
| Checklist items | 2 372 open | [x] 1898 · [~] 390 · [!] 84 · [ ] 0 |

## Defects found and fixed while integrating (regression tests added)
1. Lazy-only import hid INV-30 from `pk_core.Registry` → `pk_core run INV-30` said "unknown element" in a full estate.
2. Version parser read `5.0.0rc1` as 5.0.1 (concatenated digits) → could admit a pk_core 5 pre-release.
3. Decision records leaked raw tenant ids.
4. Deadline checked before schema validation → malformed deadlines surfaced as DEADLINE_EXCEEDED.
5. Secret scanner's content-based self-exemption was a loophole → exact-path exemption.

## What remains (cannot be closed from this environment)
* **Hardware (P0):** GAP-004 native CHERI helper, differential and tag-forgery tests; GAP-005 exact toolchain/OS
  tuple; GAP-058 CHERI rows of the matrix; GAP-046 edge power/thermal; GAP-031/032 native fuzz/TSAN; GAP-056/057
  backend runs. The model tier is usable; the hardware tier is NO_GO by construction.
* **People:** security reviewer, independent verifier, deputy, on-call (GAP-006); independent reviews in every
  gap's VAL/ACC items; runbook test by a non-author (GAP-066); tabletop (GAP-067); owner signatures in
  `evidence/SIGNOFFS.json` (owner, architecture approver).
* **Repository/infra:** CI never executed on a runner; branch protection; Sigstore/SLSA signing (DEBT-005);
  fleet-scale soak (DEBT-004).
* **Owner decisions:** confirm or replace the conservative all-rights-reserved LICENSE; approve the CHERI pin.

Full item-level record: `INV30_MISSING_COMPONENTS_REMEDIATION_CHECKLIST.md` (executed). Machine-readable
gap status: `MISSING_COMPONENTS.json` → `remediation`.

---

# Prior audit (4.2.0) — retained for history


**Audited version:** 4.2.0  
**Audit date:** 2026-09-23  
**Scope:** files present in this archive only. External Post-Kubernetes packages and actual CHERI hardware/toolchains were not bundled and therefore were not treated as verified evidence.

## Result

The dependency-free capability model is syntactically valid and its local security semantics now have executable verification. Ten standalone tests pass under normal Python and under `python -O`. Framework-level conformance remains unverified because `pk_core` is absent from the archive; the three framework tests skip rather than execute.

## Fixed in 4.2.0

1. Extracted the security-critical capability model into dependency-free `core.py`.
2. Made package/framework imports lazy so missing `pk_core` no longer prevents local model testing.
3. Added strict integer/type validation and explicitly reject Python booleans as addresses/sizes/bounds.
4. Hardened permission normalization against strings, bytes, non-string members, and mutable caller-owned sets.
5. Preserved attenuation-only bounds and permissions and permanent invalidation.
6. Added stable machine-readable error codes for capability refusals.
7. Added standalone boundary, permissions, attenuation, mutation, invalidation, malformed-input, and error-code tests.
8. Updated package/version tests to 4.2.0.
9. Removed the inaccurate README statement that `MASTER.md` is carried in this archive.

## Verification performed

- `python -m compileall`: PASS.
- Standalone unit suite: 10/10 PASS.
- Standalone suite under `python -O`: 10/10 PASS.
- Full discovered suite: 10 PASS, 3 SKIPPED because `pk_core` is not importable.
- Import/use smoke test for `Capability`: PASS without `pk_core`.
- Direct mutation refusal smoke test: PASS.

## Remaining missing components

The following components are not present or cannot be verified from this archive. Checklist IDs identify the requirements affected.

### A. Framework, hardware, and adjacent-layer dependencies

1. **Pinned `pk_core` runtime/framework dependency and reproducible installation metadata** — no `pyproject.toml`, lock file, vendored framework, or required framework version is supplied. Affects C016, C031, C093.
2. **GAP-02 hardware-capability discovery implementation** — the adapter references `GAP-02`, but it is not present, so real hardware discovery cannot be exercised. Affects C003, C030, C071, C083.
3. **Adjacent integration targets** — `PLN-04`, `INV-41`, and `INV-45` are named in the contract but absent; no cross-layer integration can be executed. Affects C003, C030, C083.
4. **Actual CHERI hardware/runtime/toolchain backend** — this repository models CHERI-shaped semantics only; it contains no Morello/CHERI CPU backend, compiler integration, kernel/runtime adapter, emulator harness, or device interface. Affects C010, C021, C031, C084.
5. **Approved CHERI specification/version pin** — no normative specification URI/version, architecture profile, compiler ABI, or supported CPU matrix is recorded. Affects C031, C084, C093.

### B. Architecture, requirements, and governance artifacts

6. **Named accountable owner and escalation path** — absent. Affects C009.
7. **Approved Architecture Decision Record (ADR)** — absent. Affects C010.
8. **Formal SHALL-level requirements specification** distinct from the generic checklist — absent. Affects C011.
9. **Requirements traceability matrix** linking each requirement to code, test, evidence, and release gate — absent. Affects C020.
10. **Deployment-context requirements** for cloud/datacenter/near-edge/far-edge — not concretely specified. Affects C012.
11. **Non-functional requirement set** for latency, determinism, availability, density, and overhead — absent. Affects C013, C017.
12. **Formal lifecycle and result-state model** covering success/partial/degraded/retryable/terminal states and legal transitions — absent. Affects C014-C015.
13. **Constraint-precedence policy** for security/residency/SLO/cost conflicts — absent. Affects C019.
14. **Exception/waiver/technical-debt register with owners and expiry** — absent. Affects C099.

### C. Public contracts and integration semantics

15. **Versioned typed schema artifacts** for `PK_CAPABILITY/1` and `PK_CAPABILITY_ACCESS/1` — schema names exist, but no JSON Schema, WIT, protobuf, IDL, or equivalent files are present. Affects C021-C022, C029, C082.
16. **Authentication model for external boundaries** — absent. Affects C023.
17. **Authorization/capability acquisition policy** describing who may mint root capabilities and how provenance is established — absent. The Python constructor is explicitly only a semantic model. Affects C024, C041-C044.
18. **Timeout/cancellation/retry/idempotency/backpressure contract** for any external adapter/control-plane boundary — absent. Affects C025.
19. **Complete machine-readable failure envelope** — local capability exceptions now have stable codes, but no external response/error schema, retryability field, correlation ID, or versioning rules exist. Affects C026.
20. **Cross-version compatibility rules and fixtures** — absent. Affects C027, C093.
21. **Interface resource/size/concurrency limits** — no documented maximum address width, capability count, concurrency, queue, payload, or fan-out bounds. Affects C028, C067.
22. **Reference integration fixtures/examples** for adjacent layers — absent. Affects C029-C030.

### D. Configuration, bootstrap, and supply-chain controls

23. **Declarative production configuration system** with secure defaults, validation, environment overlays, provenance, atomic activation, and rollback — absent. Affects C032-C040.
24. **Artifact integrity and supply-chain verification** — no SBOM, signed release metadata, checksums manifest, provenance/attestation, dependency policy, or signature verification path. Affects C045, C090, C094.
25. **Credential/secret handling implementation** — the component currently needs no secrets locally, but there is no explicit production policy or guard proving secret-free diagnostics/configuration. Affects C039, C047-C048.
26. **Deterministic bootstrap/install package** — README commands exist, but there is no environment bootstrap script, dependency installer, package metadata, or deployment manifest. Affects C040, C096.

### E. Security assurance

27. **Expanded threat model artifact** — the contract lists four threats, but there is no structured model covering malicious tenants, compromised workloads, supply chain, control-plane abuse, replay/spoofing, side channels, or exhaustion. Affects C041, C050.
28. **Node/peer/artifact attestation and authentication implementation** — absent. Affects C044-C045, C048.
29. **Tamper-evident security audit ledger** — absent. Affects C049.
30. **Adversarial security test suite** for escalation, injection, replay, spoofing, sandbox escape, side channels, and resource exhaustion — absent. Affects C050, C087.
31. **Fuzz/property-based testing** for constructor inputs, derivations, access checks, schemas, and any future external parser/IDL — absent. Affects C085.
32. **Race/concurrency semantics and tests** for `check()` racing with `invalidate()` or shared capability objects — absent. Affects C086.

### F. Resilience and fault handling

33. **Health/stall detection implementation and thresholds** — absent. Affects C052.
34. **Retry/backoff/jitter policy implementation** — absent/not applicable to the local pure model but not explicitly scoped out for integrations. Affects C053.
35. **Admission control/load shedding/circuit breaking** for any service wrapper — absent. Affects C054.
36. **Failover/degraded-operation policy** preserving capability guarantees — absent. Affects C055-C056.
37. **Crash/restart/replay and duplicate-controller semantics** — absent. Affects C057-C058.
38. **Quarantine/freeze/emergency isolation control** — README mentions registry removal, but no implemented control or tested operator action exists. Affects C059, C092.
39. **Fault-injection/disaster/partition/reconnect tests** — absent. Affects C060, C089.

### G. Performance and capacity certification

40. **Reproducible performance benchmark harness and baseline data** — absent. Affects C061.
41. **p50/p95/p99/worst-case thresholds** — absent. Affects C062.
42. **Steady/burst/overload/scale/recovery workload tests** — absent. Affects C063, C088.
43. **Per-workload/per-tenant overhead measurements** — absent. Affects C064.
44. **Copy/context-switch/locality/zero-copy optimization analysis** — absent. Affects C065-C066.
45. **Memory/concurrency/resource fan-out limits and saturation model** — absent. Affects C067, C069.
46. **Edge power/thermal measurements** — absent. Affects C068.
47. **Performance-regression release gate** — absent. Affects C070.

### H. Observability and operator tooling

48. **Runtime health/readiness/version/config/dependency endpoint** — absent. Affects C071.
49. **Metrics implementation** for rate/errors/latency/saturation/backlog/resources — contract signal names exist but no emitter/exporter. Affects C072.
50. **Structured logging with stable node/tenant/workload/operation IDs** — absent. Affects C073.
51. **Distributed trace propagation** — absent. Affects C074.
52. **Safe high-cardinality diagnostics and redaction policy** — absent. Affects C075.
53. **Decision/explain records** linking outcomes to inputs/policy/topology/constraints — absent. Affects C076-C078.
54. **Telemetry retention/sampling/privacy/export policy** — absent. Affects C079.
55. **Dashboards and actionable alert rules** — absent. Affects C080.

### I. Test, certification, and release operations

56. **Executable contract tests for every public interface** — core unit tests exist, but formal schema/interface contract tests do not. Affects C082.
57. **Executable integration tests against every supported adjacent layer** — absent due missing sibling packages. Affects C083.
58. **CPU/runtime/hypervisor/provider/protocol compatibility test matrix** — absent. Affects C084.
59. **Benchmark/soak/fleet-scale suite** — absent. Affects C088.
60. **Machine-readable release acceptance evidence generated by this archive** — absent; the documented `pk_core gate` path cannot run without external `pk_core`. Affects C090, C100.
61. **Production support commitment/error-budget operations policy** — SLO text exists, but paging/support/error-budget operating rules are absent. Affects C091.
62. **Canary/staged rollout procedure and executable rollback/emergency-disable tooling** — absent. Affects C092.
63. **Supported-version compatibility matrix** — absent. Affects C093.
64. **Patching, vulnerability-response, and end-of-life SLA** — absent. Affects C094.
65. **Backup/restore/migration applicability decision** — no persisted component state exists locally, but the repository does not explicitly document why backup/restore is not applicable or how integration state is reconstructed. Affects C095.
66. **Complete day-0/day-1/day-2 operator runbooks** — README contains a short outline, not an executable or failure-oriented runbook. Affects C096.
67. **Incident severity/paging/escalation/containment/recovery runbook** — absent. Affects C097.
68. **Recurring access/policy/dependency/configuration/architecture review process** — absent. Affects C098.
69. **Formal production exit-gate artifact** aggregating architecture, security, resilience, performance, observability, testing, rollback, and ownership evidence — absent. Affects C100.
70. **Continuous-integration workflow** that runs normal and optimized tests, lint/static checks, packaging checks, and release gates — absent.
71. **Repository license/legal notice** — no `LICENSE` or `NOTICE` file is present, so redistribution terms are undefined in this archive.

## Important interpretation

The repository now has a materially stronger and independently testable *semantic model*. It still does **not** constitute a production CHERI hardware sandbox by itself. Production readiness depends on the missing hardware/toolchain integration, framework dependencies, schemas, operational controls, telemetry, certification evidence, and release governance listed above.
