# INV-34 5.0.0 Audit Report

## Scope

This audit parsed the supplied 4.1.0 ZIP, compared implementation behavior with all 100 checklist requirements, corrected defects that can be resolved inside a self-contained reference repository, version-bumped the package, and re-audited the resulting tree for remaining production components.

## Baseline findings and disposition

| ID | Severity | Baseline finding | 5.0.0 disposition |
|---|---|---|---|
| A-001 | Critical | Core implementation did not implement the checklist-defined function. `INV-34-C010` requires **ACPI hot-plug / Conventional VM CPU scaling**, while 4.1.0 implemented x86 feature-level matching. | **Fixed.** Contract and implementation now model conventional VM CPU expansion and ACPI capability gating. |
| A-002 | High | The x86 feature sets used by 4.1.0 were not complete standard x86-64-v2/v3/v4 definitions, so they could yield false compatibility positives even for the subsystem they attempted to implement. | **Removed from INV-34.** Feature-level matching is no longer presented as this component's responsibility. |
| A-003 | High | Every behavioral/conformance test was skipped when `pk_core` was absent, allowing the ZIP to report success without exercising repository logic. | **Fixed.** Standalone stdlib tests now run without `pk_core`; only framework-specific tests skip. |
| A-004 | High | The package itself could not be imported without `pk_core`, even though most logic need not depend on the framework. | **Fixed.** Core logic is dependency-free; framework adapter remains optional. |
| A-005 | High | No model distinguished “expansion request accepted” from “new CPU actually online,” a critical correctness distinction for hot-plug. | **Fixed.** Desired and observed vCPU counts are distinct, with convergence only at equality. |
| A-006 | High | No stale-writer protection, idempotency semantics, or concurrency guard existed for CPU expansion state. | **Fixed.** Generation guard, bounded replay cache, conflict detection and per-controller locking added. |
| A-007 | High | No explicit configured-VM ceiling and current host-capacity ceiling were enforced for the actual CPU-expansion function. | **Fixed.** Both ceilings are fail-closed request checks. |
| A-008 | Medium | No stable machine-readable error taxonomy for expansion decisions existed. | **Fixed.** `ExpansionError` subclasses expose stable `code`, `retryable`, and structured context. |
| A-009 | Medium | README claimed `MASTER.md` was bundled, but the file was absent. | **Fixed.** Unsupported claim removed. |
| A-010 | Medium | External interface schemas were described textually but no schema artifacts were bundled. | **Fixed.** Request/result/status JSON Schemas added. |
| A-011 | Medium | No administrative kill switch or explicit refusal of CPU hot-unplug existed for the actual expansion path. | **Fixed.** Expansion enable flag and monotonic-only policy added. |
| A-012 | Medium | Operational, architecture, security and compatibility constraints were undocumented. | **Improved.** Added `ARCHITECTURE.md`, `THREAT_MODEL.md`, `OPERATIONS.md`, and `COMPATIBILITY.md`. |
| A-013 | Medium | There was no durable external state, real hypervisor adapter, authorization layer, telemetry pipeline, performance evidence, or end-to-end compatibility certification. | **Not fabricated.** These remain explicit gaps in `MISSING_COMPONENTS.md`. |

## Version decision

The version was bumped from **4.1.0 to 5.0.0** because the primary contract and behavior changed from an unrelated CPU-feature classifier to the checklist-defined ACPI/conventional-VM expansion subsystem. Treating that as a patch/minor release would hide a breaking semantic correction.

## Verification performed

- Python bytecode compilation over the full repository.
- JSON parsing of `CHECKLIST.json` and all bundled schemas.
- Standalone stdlib unit suite in normal Python mode.
- Same standalone suite under `python -O` to prevent optimizer-dependent checks.
- Concurrency test for duplicate idempotent requests.
- Validation tests for malformed inputs, limits, capability gating, stale generation, shrink refusal, host-capacity failure and observed-state divergence.
- Static reference scan for stale version strings, missing-file claims, TODO/FIXME markers, bare `assert` in production logic, dangerous dynamic execution patterns and shell execution.

`pk_core` is not present in the supplied ZIP/environment, so the two framework-only conformance tests remain skipped. That is a **remaining dependency/certification gap**, not a passing production-gate result.

## Post-fix conclusion

The repository is now internally coherent as a hardened **reference control-plane component** for legacy VM CPU expansion. It is not a complete production CPU-hotplug service. The remaining external/runtime/governance components are exhaustively enumerated in `MISSING_COMPONENTS.md` so they cannot be mistaken for implemented behavior.
