# 05 — Applied

Backup: the unmodified v4.2.0 tree was copied before any change (session workspace).

**Added (47 paths, see 05-FILE-DELTA.txt):** `service.py`, `adapters.py`, `identity.py`, `trust.py`, `errors.py`, `audit.py`, `config.py`, `compat.py`, `resilience.py`, `observability.py`, `planner.py`, `modeling.py`, `schema_check.py`, `__main__.py`, `pyproject.toml`, `OWNERS.md`, `AUDIT_REPORT_v4.3.0.md`, `CERTIFICATION_MANIFEST.json`, 17 schemas, `docs/` (6 files incl. the checklist), `tools/` (gen_schemas, bench, release_evidence, build_manifest), `tests/fixtures/estate.py` and 8 test modules, `evidence/` (test report, SBOM, release evidence, 4 bench runs).
**Changed:** `__init__.py`, `contract.py`, `VERSION`, `README.md`, `CHANGELOG.md`, `MISSING_COMPONENTS.md`, `MANIFEST.sha256`, `tests/test_component.py`. **Unchanged:** `engine.py`, `component.py`, `CHECKLIST.json`, `MASTER.md`, v4.2.0 schemas.

**Verification.** 170 tests: 168 pass, 2 skipped (pk_core absent). Fuzz at 3,000 iterations clean. Fault matrix single + pairwise clean. Bench: single worker p99 ≈ 1.3 ms, 8 threads/process p99 ≈ 63 ms (finding → default concurrency 4/process). Independent manifest sampling ×2, all 22 findings resolved. RCG before/after deltas: not available (yard office unreachable).

**Skipped / not possible here.** Live estate runs, certified pk_core, Windows / Python 3.12–3.13, wheel build + signing, human exercises, named owners.
