# Release checklist (INV29-MC103)

Copy to `release/checklist-<version>.md`, complete, and archive it with the evidence bundle. `tools/build_release.py` generates `release/evidence-manifest.json` and fails if any mandatory artifact is absent or stale.

- [ ] `VERSION`, `__init__.__version__`, `pyproject.toml`, `CHANGELOG.md` agree
- [ ] Compatibility review (`docs/COMPATIBILITY.md`) and schema migration notes (`docs/SCHEMA_EVOLUTION.md`) updated
- [ ] `python tools/run_tests.py` — all suites pass normally and under `-O`
- [ ] pk_core conformance run with **zero** certification-critical skips
- [ ] `python tools/fuzz.py 600` — zero findings
- [ ] `python tools/bench.py` — perf gate PASS on reference hardware
- [ ] Secret scan and vulnerability scan clean (`security/*.json`)
- [ ] SBOM, provenance, `SHA256SUMS` regenerated; release signed with the owner's key
- [ ] SLO status reviewed; alerts/dashboards updated for new signals
- [ ] Rollout plan + rollback target recorded (`governance/ROLLOUT.md`)
- [ ] Waivers reviewed; none expired or mismatched
- [ ] `conformance/PK_GATE_RESULTS.json` generated for this exact source digest
- [ ] Approvals per `OWNERS.md`
