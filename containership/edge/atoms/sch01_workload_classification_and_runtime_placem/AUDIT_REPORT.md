# SCH-01 Repository Audit Report

**Input:** `sch01_workload_classification_and_runtime_placem.zip`  
**Audited source version:** 4.1.0  
**Updated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** source inventory, importability, runtime logic, input validation, placement safety, concurrency, documentation integrity, testability, version consistency, and post-update checklist gap analysis.

## Initial inventory

The supplied archive contained eight files: `CHANGELOG.md`, `CHECKLIST.json`, `README.md`, `VERSION`, `__init__.py`, `component.py`, `contract.py`, and `tests/test_component.py`. The checklist contains exactly 100 items across ten dimensions.

## Material findings in 4.1.0

1. The README claimed `MASTER.md` was included, but the file was absent.
2. Every test was class-level skipped when external `pk_core` was unavailable, including the version test, so the archive could report an apparently clean test run without exercising its scheduler logic.
3. Importing the package required `pk_core`; the core classification/placement algorithm was not independently testable.
4. Future-dated node reports were accepted because freshness used only `now - reported_at > bound`.
5. `candidates()` accepted a caller-supplied classification without proving it matched the workload, creating a public-function downgrade path if used directly.
6. Mutable node slot/occupant state had no synchronization; concurrent placements could race and oversubscribe capacity.
7. Cross-tenant safety was asymmetric: trusted workloads could share a node with another tenant even though occupancy metadata did not include enough trust/tier information to prove the contract boundary.
8. Workload/node input validation was incomplete: unsupported tiers, malformed names, invalid clocks, duplicate node identities, and scalar capability inputs were not comprehensively rejected.
9. Refusal errors were mostly human-readable strings with no stable error code/details envelope.
10. `first-party` and the `wasm` minimum-tier path existed in constants but were unreachable from provenance classification.
11. The component class name was misspelled `...PlacemenComponent`.
12. The archive did not independently contain the evidence needed to support its prior statement that all 100 requirements passed; `pk_core`, adjacent components, evidence ledger, and gate results were absent.

## Changes applied in 4.2.0

- Created `engine.py` and moved the scheduling decision logic behind a dependency-independent API.
- Made package import useful without `pk_core`; the conformance adapter remains available when that external dependency exists.
- Added strict data validation for workload names/tenants/provenance, hardware requirement collections, node names/sites/tiers/capabilities, slot counts, report timestamps, clocks, and lease durations.
- Reject scalar strings where a set/iterable of capability names is expected.
- Added canonical-classification verification before candidate filtering.
- Added future-dated report rejection.
- Changed tenant co-location to fail closed whenever another tenant is already present because current occupancy metadata is insufficient to prove a safe shared tier.
- Added duplicate node identity rejection.
- Added a process-local critical section around duplicate-lease detection, candidate selection, scoring, and node mutation.
- Added `PK_SCHEDULER_ERROR/1`, stable refusal codes, aggregate rejection counts, and deterministic decision metadata.
- Added the `first-party` -> `wasm` classification path.
- Corrected the component class name while preserving the old spelling as an alias.
- Added standalone engine tests and made version testing independent of `pk_core` availability.
- Added architecture, schema, security, operations, audit, and missing-component documentation.
- Bumped all package/version references to 4.2.0.

## Verification executed

Audit environment: Python 3.13.5 on x86_64 Linux.

- `python -m compileall` completed successfully.
- `unittest` discovery ran 18 tests: 16 passed and 2 `pk_core` integration tests were skipped because the dependency is not bundled/importable. No standalone engine test was skipped.
- The standalone suite exercises classification, malformed input, tampered classification, future/stale reports, thermal/site/hardware/tier/tenant filtering, deterministic tier-minimal scoring, duplicate identities, duplicate leases, structured diagnostics, clock/lease validation, optimized mode, and a two-thread one-slot race.
- A static grep found no `eval`, `exec`, `pickle`, unsafe YAML load, `shell=True`, or `os.system` use in Python sources.
- An ad-hoc 120-decision sample over 1,000 candidate nodes measured median 6.283 ms, p95 7.487 ms, p99 8.407 ms, and max 8.616 ms in this audit container. This is encouraging against the declared 100 ms p99 objective but is **not** a reproducible production benchmark or release gate; those remain missing.

The external conformance suite is intentionally not counted as passing because `pk_core` is not bundled in this audit environment. See `MISSING_COMPONENTS.md` for the complete post-update gap inventory.
