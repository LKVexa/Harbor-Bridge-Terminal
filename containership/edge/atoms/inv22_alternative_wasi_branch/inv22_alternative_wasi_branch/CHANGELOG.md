# Changelog

## 4.3.0 - 2026-09-23

Missing-components remediation pass against `INV22_v4.2.0_Missing_Components_Engineering_Checklist.md`
(64 work packages). Status per package: `REMEDIATION_STATUS.md` / `data/remediation.json`.

- Added external contracts with JSON Schemas and canonical JSON: `PK_BRANCH_MATRIX/1`, `PK_BRANCH_SHIM/1`,
  `PK_BRANCH_CERT/1`, `PK_BRANCH_ERROR/1`, `PK_BRANCH_CONFIG/1`, plus version negotiation.
- Structured error registry (stable `INV22.*` codes); legacy exceptions now carry `.code`.
- WIT-subset parser, interface inventory, structural diff, completeness gate, reviewed-override
  matrix generation with a `--check` drift gate.
- Typed translation service with a real bidirectional filesystem open-flags/rights translator,
  exhaustive round-trip proof, mutation testing, capability-monotonicity check, deadlines,
  cancellation and bounded concurrency.
- Ed25519-signed certificates with trust store, rotation/compromise, skew, freshness-bounded revocation.
- Transactional SQLite store: certificates, hash-chained append-only audit log, immutable drift
  history, atomic config activation/rollback, fenced site-branch control, backup/restore, migrations.
- Authentication (signed identity tokens, replay protection), default-deny scoped authorization,
  separation of duties, break-glass; authenticated `ops` API; read-only operator CLI.
- Typed configuration with precedence/provenance, secret references and redaction.
- Governance: fail-closed precedence engine, scoped time-boxed waivers, drift thresholds, admission.
- Bounded telemetry, zero-budget SLO evaluation, readiness model.
- Preflight for pk_core / adjacent elements / baselines; lazy package import so a missing pk_core no
  longer breaks every import.
- `pyproject.toml` (reproducible wheel with `SOURCE_DATE_EPOCH`), runtime lock, CI workflow,
  SECURITY.md, CODEOWNERS template, threat model, runbooks, data policy, evidence bundle and exit gate.
- Production exit gate: **NO_GO** — pk_core, adjacent elements and WASI/WASIX baselines are not in the
  archive; licence, owners, signing identity and deployment target are owner decisions.

## 4.2.0 - 2026-09-23

- Hardened the compatibility matrix as an immutable runtime mapping.
- Added strict input, branch, and classification validation with fail-closed behavior.
- Made same-branch shims identity operations and enriched cross-branch shim provenance.
- Hardened certification counters and component/branch validation.
- Added drift delta reporting and deterministic release-order semantics.
- Added standalone core-logic tests that run without the external `pk_core` package.
- Preserved optimizer-safe behavioral verification (no runtime `assert` dependency).

 - INV-22

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::DriftReport.growing: releases ordered by lexical sort of names ("v10" < "v2"), misreporting growth -> use recording (insertion) order
- component.py::DriftReport.record: only counted the literal DIVERGENT value, so an unknown classification was treated as compatible (contradicts "unclassified is divergent") -> count anything not IDENTICAL/SHIMMABLE; re-recording a release moves it to latest
- component.py::Certification: accepted empty component id and unknown branch names (certifying against a non-existent branch) -> validate in __post_init__ with ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
