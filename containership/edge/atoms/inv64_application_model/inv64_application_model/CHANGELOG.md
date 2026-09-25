# Changelog - INV-64

## 4.3.0 - 2026-09-23

Missing-component remediation against `source/INV64_v4.2.0_MISSING_COMPONENTS_CHECKLIST.md` (MC-01..MC-40, 750 items). Junkyard chop-shop work order `inv64_application_model-20260923`.

### Defects found and fixed by this pass's own checks

- **Deep nesting crashed the parser with `RecursionError`** (not a `ValueError`) — 4.2.0 defect, reproduced with `json.loads('['*100000 + ']'*100000)`. Now a linear pre-scan refuses nesting > 64 (`ManifestDepthError`, `manifest.too_deep`), also for already-decoded objects. Regression fixture R001.
- **Credential material was accepted and hashed into the canonical identity** (4.2.0 had no secret rule). Now `secret.inline` refuses it anywhere (incl. base64/percent/Unicode-obfuscated forms); only `secretref://` references are allowed.
- **Validation messages echoed credential-like names** — found by `tools/fuzz.py` (seed 64, case 1304) during this pass: an embedded AWS-format key escaped the `\b`-anchored pattern and was echoed in `duplicate name`. Pattern fixed; `manifest._show` redacts credential-like values in every message. Regression fixture R005.
- **Audit loss marker could be lost** when the buffer was full at recovery — found by fault scenario f07; backlog is now drained before the loss record is chained.
- **Submit could register before its audit record was durable** — reordered: audit (fail-closed) first, registry second, compensating `reverted` record on registry failure.
- **Overlay `set`/`unset` of non-list type raised `TypeError`** — now `overlay.invalid` (fuzz boundary target).
- Limits were internally inconsistent: 10,000 minimal components exceed the 1 MiB byte ceiling (~7,000 fit). Documented in SPECIFICATION §6; benchmarks use 5,000.

### Added (by component)

- Security boundary: `service.py` (authn → authz → tenancy → deadline → admission → idempotency → validate → canonical → audit/decision/telemetry), `auth.py`, `authz.py`, `tenancy.py`, `redaction.py`, `trust.py`, `provenance.py`, `crypto_policy.py`, `audit.py` (MC-07/08/14/15/16/17/18).
- Contracts: `errors.py` (`PK_APP_ERROR/1`), 10 JSON Schemas, WIT contract, INTERFACES.md, SPECIFICATION.md (MC-05/06); `semantics.py` (MC-09).
- Configuration: `overlay.py`, `activation.py` (journal, CAS, crash recovery, auto/operator rollback, quarantine) (MC-12/13); `rollout.py` + ROLLOUT_POLICY (MC-40).
- Operability: `service.status()` (MC-23), `telemetry.py` (MC-24), `explain.py` (MC-25), TELEMETRY_POLICY, alerts and dashboard as code (MC-26), runbooks, incident response, reviews, register (MC-33..36), BACKUP_RESTORE + `tools/backup_restore.py` (MC-32).
- Adjacent layers: `adjacent.py` emulators + `tools/integration.py` (MC-10, emulated profile only); OAM v0.3.0 baseline pinned by commit with `oam_profile.py` (MC-11).
- Verification: `tools/fuzz.py`, `tools/faults.py`, `tools/stress.py`, `bench/perf.py` (MC-19..22, 28); `tests/test_v43.py` (74 tests incl. abuse cases).
- Supply chain and release: `pyproject.toml`, `tools/build_check.py`, `tools/release.py` (CycloneDX SBOM, SHA256SUMS, in-toto/SLSA provenance, Ed25519 DSSE), `release_gate.py` + `ops/GATE_POLICY.json`, `tools/run_evidence.py`, `.github/workflows/ci.yml` (MC-03/29/37/39); LICENSING/NOTICE/THIRD-PARTY-NOTICES (MC-38).
- Governance data: `ops/owners.json`, ADR-0001 (proposed), `compatibility.json` (first matrix; `PK_APP_SUBMIT/1` deprecated), `provenance/master-source.json`, generated `COMPONENTS_STATUS.json`, `evidence/ITEM_LEDGER.json`, traceability (MC-01/04/30).

### Changed

- `schema/` now holds all contract schemas; `contract.py` lists the new interfaces and threats; `VERSION`/`__version__` 4.3.0 with a single source (`pyproject` reads `VERSION`).
- Validation is ~7x slower than 4.2.0 (secret scanning); still ≥ 30x inside the 5 ms SLO for typical manifests (REG-004).

### Verification

- Standalone suites 88/88 passing (normal and `-O`); full run 92 with `test_component` failing/skipping by design (no pk_core).
- Fuzz 3,000 iterations (seed 64) + 5 regressions: 0 findings; faults 13/13; stress 7/7; emulated integration 12/12; build: wheel and sdist install into fresh venvs with identical API/digest; perf gate PASS.
- Exit gate: **NO_GO** — blockers are pk_core, real adjacent layers, owners/ADR/license, reviews/drills, managed signing, multi-platform CI (see AUDIT_REPORT.md).

## 4.2.0 - 2026-09-22

Second audit, parser hardening, evidence correction, and version bump.

### Fixed / hardened

- Isolated the untrusted manifest parser/validator/canonicalizer into stdlib-only `manifest.py`.
- Added aggregate machine-readable validation issues and stable error codes.
- Added raw JSON size limits, duplicate-key rejection, finite-number enforcement, collection ceilings, and stricter identifier validation.
- Canonicalization now requires a valid manifest, emits deterministic compact UTF-8 JSON, and never mutates input.
- Added `schema/app-v1.schema.json`, `SCHEMA.md`, `ERRORS.md`, `SECURITY.md`, examples, and 14 standalone regression tests.
- Corrected the false README claim that `MASTER.md` was present.
- Changed integration testing so missing `pk_core` is a visible failure rather than an all-skipped false-green run.
- Added `AUDIT_REPORT.md` and a 100-item `REQUIREMENTS_TRACEABILITY.md`; the standalone archive no longer claims unsupported 100/100 production completion.

### Verification

- Standalone manifest suite: 14/14 passing on Python 3.13.5.
- `compileall`: passing.
- Full `pk_core` conformance: blocked because `pk_core` is not included in this archive.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::validate: malformed manifests (non-dict, entries missing name/from/to/component, non-list sections) crashed with KeyError/TypeError instead of being refused with errors -> defensive .get access and reported errors

### Gate

Historical estate-level claim: all 100 requirements were reported satisfied under python and python -O when run with the external framework. The standalone archive cannot independently substantiate this claim; see the 4.2.0 audit.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
