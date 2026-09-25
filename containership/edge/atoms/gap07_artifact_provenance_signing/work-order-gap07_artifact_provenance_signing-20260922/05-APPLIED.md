# 05 — Applied

- **Backup:** the original v5.0.0 zip is kept unmodified as the owner's upload.
- **Added modules (20):** errors, canonical, algorithms, keys, trust, signing, dsse, tlog, store, distribution, timesrc,
  policy, sbom, registry, controls, telemetry, audit_export, admission, compromise, service.
- **Changed:** `core.py` (thread-safe AuditLedger, event_id/actor), `__init__.py` (6.0.0, module list), VERSION,
  README, CHANGELOG, AUDIT_REPORT, MISSING_COMPONENTS, `tests/test_component.py` (version).
- **Added assets:**
  - 7 test modules (126 new tests)
  - `vectors/`, `schemas/` (7 new)
  - `docs/`: signature profile, key ceremony, admission paths, threat model, review packet, runbooks, 7 ADRs, checklist copy
  - `ops/` (alerts, dashboard, SLO budgets), `ci/`, `deploy/k8s/`, `fixtures/gap13/`
  - `tools/`: vectors, schemas, benchmark, soak, release, traceability, compat
  - OWNERS.yaml, DEPENDENCIES.md, THIRD-PARTY-NOTICES.md, requirements.txt, COMPATIBILITY.json,
    TRACEABILITY.json/.md, SBOM.cdx.json, RELEASE_EVIDENCE.json, MANIFEST.sha256
- **Verification:**
  - 143 tests: 141 pass, 2 skipped (`pk_core`), both normal and `-O`
  - extra fuzz seeds clean
  - traceability check ok
  - release evidence `all_required_passed: true`
  - release sign/verify round-trip tested on a scratch copy; tamper detected
- **Adversarial review:** a separate reviewer demonstrated 7 defects plus 5 more on a second pass. All were fixed and
  each has a regression test (CHANGELOG 6.0.0).
- **RCG before/after:** not run (runtime absent).
- **Skipped:** `pip-audit` (not installed here; CI runs it). Everything listed as blocked in `MISSING_COMPONENTS.md`.
