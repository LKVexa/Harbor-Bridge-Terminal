# 05 — Applied

- Backup: the original v4.2.0 archive is unchanged (the attachment). All 12 original files are retained. Changed: `__init__.py` (version, exports), `VERSION`, `README.md`, `CHANGELOG.md`, `AUDIT_REPORT.md` (appended), `MISSING_COMPONENTS.md` (pointer), and `tests/test_component.py` (the version check now reads VERSION and also checks pyproject and CHANGELOG). `brokers.py`, `contract.py`, `component.py` and `CHECKLIST.json` are byte-identical.
- Added: 19 Python modules (6 of them under `adapters/`), 6 schemas, 7 config files, 29 documents under `docs/` (plus a copy of the governing checklist), 6 tools and a component registry, the bench harness, a CI workflow, 5 new test files (including `fakes.py`), `CHECKLIST_STATUS.md`, and `evidence/` (10 files).
- Verification: 105 tests → 103 pass, 2 skip (pk_core). Green under `python -O`. Clean-venv bootstrap without extras: pass (3 skips). Benchmark gate passes on the build host. Schema drift check, ownership check and provider certification (all SKIPPED, as expected) were run.
- Components: 48 LOCAL_VERIFIED / 30 PARTIAL / 18 DOCUMENTED_UNAPPROVED / 4 UNVERIFIED_EXTERNAL. **Exit gate NO_GO.**
- Seven defects were found by this pass's own tests and generator, and fixed (listed in `AUDIT_REPORT.md`).
- Graph deltas: not available (no `rcg`).
- THIRD-PARTY-NOTICES: none needed. Nothing was vendored; optional extras are installed from PyPI (licenses listed in `LICENSE-PENDING.md`).
