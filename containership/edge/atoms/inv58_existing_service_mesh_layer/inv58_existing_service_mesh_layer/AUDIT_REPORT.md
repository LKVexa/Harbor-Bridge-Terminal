# INV-58 Repository Audit Report - v4.2.0

**Element:** INV-58 - Existing service-mesh layer  
**Audit date:** 2026-09-22  
**Input version:** 4.1.0  
**Updated version:** 4.2.0

## Executive result

The repository was parsed, corrected, hardened, version-bumped, and re-audited. The 4.2.0 update fixes a contract-level retry-ownership defect, hardens SPIFFE identity handling and resource bounds, adds atomic/revisioned route migration state, introduces typed interface schemas, and makes critical logic independently testable without the external framework.

The post-update repository audit does **not** treat the prior 4.1.0 statement “all 100 requirements satisfied” as reproducible evidence: `pk_core` is external and is not included/importable in this archive. Local verification discovers 22 tests: 20 pass and 2 framework-level conformance tests skip for that explicit dependency reason, both normally and under `python -O`.

## Baseline defects found and corrected

1. **Duplicate retry ownership was contract-invalid.** `reconcile()` returned `owner="both"` whenever app×mesh attempts fit the numerical budget (for example 2×2 inside budget 4), violating the mandatory requirement to give retries to exactly one layer per route. 4.2.0 always selects one retry owner (preferring the app when both request retries), or none.
2. **Mesh-only over-budget behavior lost intended ownership.** When only the mesh retried above budget, the previous branch could switch ownership to the app even when the app requested one attempt. 4.2.0 keeps mesh ownership and caps mesh attempts.
3. **Route identifiers were not validated.** Empty, non-string, whitespace-padded, control-character, and oversized route values can now be refused before policy activation.
4. **SPIFFE mapping used prefix matching instead of strict URI validation.** 4.2.0 rejects foreign trust domains, malformed URI forms, empty/dot path segments, query/fragment data, percent-encoded ambiguity, backslashes, invalid trust domains, whitespace/control characters, and overlong identities.
5. **Bypass evidence was unbounded and unsynchronized.** The detector now validates mTLS as a strict boolean, bounds configured meshed destinations and retained evidence, uses immutable membership, and protects writes/snapshots with a lock.
6. **Route migration ownership existed only as a statement.** `RoutePolicyRegistry` now provides bounded, revisioned, thread-safe copy-on-write route migration with defensive copies.
7. **Declared interfaces had no schema artifacts.** Draft 2020-12 schemas now exist for all three declared interfaces and are referenced by the binding contract.
8. **Critical behavior could not be tested without `pk_core`.** Dependency-free logic is now isolated in `mesh_logic.py` with independent unit tests; schema tests are also included.
9. **Package metadata import was unnecessarily coupled to `pk_core`.** Framework-bound exports are now lazy, so version metadata and dependency-free logic can be imported without `pk_core`; requesting the framework component still requires it.
10. **README falsely implied `MASTER.md` was present.** The README now records it as a tracked missing authoritative source artifact rather than silently inventing replacement content.

## Files added

- `mesh_logic.py`
- `schemas/PK_MESH_RECONCILE-1.schema.json`
- `schemas/PK_MESH_IDENTITY-1.schema.json`
- `schemas/PK_MESH_BYPASS-1.schema.json`
- `tests/test_mesh_logic.py`
- `tests/test_schemas.py`
- `tests/test_audit_artifacts.py`
- `AUDIT_REPORT.md`
- `POST_AUDIT_MISSING_COMPONENTS.md`
- `MISSING_COMPONENTS.json`

## Files materially updated

- `component.py`
- `contract.py`
- `tests/test_component.py`
- `README.md`
- `CHANGELOG.md`
- `VERSION`
- `__init__.py`

## Verification performed

- Python bytecode compilation (`python -m compileall`).
- Standard-library unit-test discovery.
- Repeat test run under optimized mode (`python -O`).
- Draft 2020-12 JSON Schema validation and representative payload validation (where `jsonschema` is installed in the audit environment).
- Static scan for stale version references, TODO/FIXME/NotImplemented markers, dangerous dynamic execution patterns, and production bare `assert` use.
- Archive integrity check after packaging.

### Local test result

- **22 tests discovered**
- **20 passed**
- **2 skipped**: both are `pk_core` framework-level conformance tests because `pk_core` is not included/importable in the standalone archive.
- **Optimized mode:** same pass/skip result.

This is a material improvement over the baseline because retry/identity/bypass/migration behavior is now directly verifiable even when the ecosystem framework is unavailable.

## Post-update completeness finding

The repository still does not, by itself, demonstrate production completion of the full 100-item checklist. The evidence audit classifies the checklist as:

- **11 implemented**
- **25 partial**
- **64 missing**

All 89 partial/missing checklist items are exhaustively mapped in `POST_AUDIT_MISSING_COMPONENTS.md` and machine-readable `MISSING_COMPONENTS.json`. There are also two repository-level gaps not represented by a single checklist item: the absent authoritative `MASTER.md`, and absent standalone packaging/dependency/CI/license inheritance metadata.

## Verification limitation

A true ecosystem gate still requires the external `pk_core` package at a compatible version and the surrounding component registry. Because neither is shipped in this ZIP, this audit does not claim a live `pk_core run/gate/verify` pass. Once `pk_core` is supplied, the two skipped framework tests and the documented gate commands should be rerun and their machine-readable evidence added to the release.


---

# v4.3.0 — execution of the missing-components implementation checklist

**Input:** 4.2.0 hardened candidate + `INV58_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (41 work packages, 2,770 checkbox lines).
**Output version:** 4.3.0. **Gate:** engineering PASS, production **NO_GO** (exit 3), 36 named blockers.

## Result
| Measure | 4.2.0 audit | 4.3.0 |
|---|---|---|
| Checklist requirements (C001–C100) | 11 implemented / 25 partial / 64 missing | 56 verified-local / 20 defined / 16 partial / 8 blocked |
| Work packages MC-001..041 | 41 open | 20 implemented-local / 16 partial / 5 blocked |
| Checklist lines (2,770) | 0 closed | 1149 done / 863 partial / 758 blocked (358 need a named person, 144 need external systems) |
| Tests | 22 (20 pass, 2 skip) | 185 (all pass; 2 skip = pk_core, counted as production blockers) — identical under `-O` |

No requirement was upgraded on documentation alone where the checklist asks for executable behaviour: rows marked DEFINED are requirements whose text is "define…" and each links the definition plus any behavioural test.

## Performance baseline (after OPT-2 fix)
Per-run gate results (current vs baseline vs limit) are in `release/ACCEPTANCE_RECORD.json` → `evidence.performance_gate`.

| Metric | Baseline |
|---|---|
| memory.routes_10k_kib | 3663.773 |
| mesh.map_identity.p99_us | 14.450 |
| mesh.reconcile.p99_us | 2.752 |
| startup.bootstrap_ms | 0.734 |
| svc.map_identity.p99_us | 66.113 |
| svc.migrate_route.p99_us | 249.068 |
| svc.reconcile.p99_us | 72.027 |
| svc.report_flow.p99_us | 120.222 |
| tenant_overhead.ratio_200_vs_1 | 0.906 |

## Defects found by this pass's own checks
See CHANGELOG 4.3.0 — ten test/fuzz/benchmark-found defects plus one review finding, each with a regression case in `tests/test_security_regression.py` or the suite that caught it.

## Verification performed
- Full suite normal and `python -O` via `tools/run_tests.py`; clean copy in a fresh directory: 185/0/0 with 2 pk_core skips.
- Fresh venv without `jsonschema`: the 7 schema tests skip, and the release gate classifies those skips as UNEXPECTED (engineering failure) — verified.
- `tools/rtm.py --check` (100 rows, every symbol/test/doc/anchor resolves), `tools/gen_fixtures.py --check` (18 fixtures), `tools/bootstrap.py --dev-keys`, `tools/bench.py` gate.
- Source tree digest: recorded in `release/ACCEPTANCE_RECORD.json` (`source_tree_digest`) at the final gate run.

## Not verified (and why)
Independent review, owner approval, pk_core conformance, live mesh / adjacent-layer integration, multi-platform CI, representative-environment rollback rehearsal, power/thermal, fleet/soak beyond in-process — each is a named blocker in `release/ACCEPTANCE_RECORD.json`.
