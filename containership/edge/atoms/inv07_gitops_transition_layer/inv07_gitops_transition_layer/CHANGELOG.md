# Changelog - INV-07

## 5.0.0 - 2026-09-22

Production overlay built against the *INV-07 54-Component Professional Engineering Checklist v1.0.0*
(54 components; the checklist header says 30+8 controls each but every component actually carries
32 engineering controls + 8 Definition-of-Done items = **40**, so **2,160** checks in total).

### Added (`components/`, stdlib-only, 30 modules)
- Real Git transport over a pinned bare mirror (`gitrepo.py`): remote pinning, root-commit identity, URL/SSRF policy,
  credential via environment (never argv), isolation from user/system git config, bounded reads.
- Asymmetric trust (`signing.py`): Ed25519 signatures in the standard `gpgsig` header (RFC 8032 vectors), OpenPGP lane
  via `git verify-commit --raw`; trust roots with identity, scope, purpose, expiry and hard revocation.
- DSSE/in-toto provenance in `refs/notes/provenance` bound to commit **and** tree (`provenance.py`).
- Ref policy + freshness generations (`refpolicy.py`), hardened YAML/JSON manifest parsing (`manifests.py`),
  signed/versioned policy bundles (`policy.py`), tenancy + residency (`tenancy.py`).
- Fenced reconciliation: file lease with epoch fencing (`lease.py`), durable targets with CAS/ownership
  (`target.py` incl. Kubernetes server-side-apply adapter), journalled transactions with compensation and
  auto-quarantine on partial apply (`apply.py`, `state.py`), Argo CD/Flux OID-pinned adapters (`controllers.py`).
- Operations: retry/backoff/budgets, breakers, fair admission queue (`resilience.py`); freeze/kill switch,
  trusted time, offline modes (`operations.py`); IaC migration state machine (`migration.py`).
- Observability: Prometheus metrics, `PK_GITOPS_EVENT/1` logs, W3C tracing, durable explain records
  (`telemetry.py`); operator HTTP API with PKT1 tokens, RBAC/ABAC and two-person rule (`server.py`, `authz.py`).
- Seven versioned JSON Schemas (`schemas/`), stable error codes (`errors.py`), typed config (`config.py`), CLI.
- Docs (ADR, threat model, runbooks, operations, compatibility, migration, backup/restore, policies, generated
  API reference and requirements), deploy assets, `pyproject.toml`, NOTICE, regenerated `MASTER.md`.
- Evidence: checklist engine over all 2,160 checks (`checklist/engine.py`), hash-chained gate ledger,
  traceability matrix, SBOM, license inventory, lint, coverage, platform report, perf baseline.

### Changed
- `__init__.py`: `pk_core` imported lazily so the package imports without it; version 5.0.0.
- `README.md`, `MISSING_COMPONENTS.md`: point at the overlay and its per-item status.

### Unchanged (byte-identical, enforced by `components/tests/test_overlay_integrity.py`)
- `gitops_model.py`, `contract.py`, `component.py`, `CHECKLIST.json`, `tests/*`, `AUDIT_REPORT.md`.

## 4.2.0 - 2026-09-22

Audit, parsing, corrective hardening, and version bump.

### Reference-model hardening

- Added `gitops_model.py` so core reconciliation behavior can be tested without `pk_core`.
- Replaced `repr`-based signing with canonical JSON serialization and strict deterministic-state validation.
- Replaced 10-character SHA-1 commit ids with full SHA-256 commit ids over a deterministic envelope.
- Deep-copied committed state to prevent nested alias mutation from rewriting retained history.
- Added an `RLock` around state transitions for same-process concurrency safety.
- Made repeat sync of an unchanged head idempotent in applied history.
- Drift reports now identify both the baseline commit and reconciliation target.
- Added explicit `verify_head()` and secret-free `status()` helpers.

### Verification and documentation

- Added nine dependency-free unit tests, including optimized-interpreter compatibility.
- Corrected README claims around the absent `MASTER.md` file and the externally supplied `pk_core` conformance dependency.
- Added `AUDIT_REPORT.md` and prioritized `MISSING_COMPONENTS.md`.
- Updated component evidence pointers to the extracted reference-model implementation.

### Compatibility note

- Public component contract and `GitOps.commit/sync/revert` call shapes are retained. Commit identifiers are intentionally stronger and therefore change from the old 10-character SHA-1 format to 64-character SHA-256 values.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::GitOps.sync: drift was computed against the NEW commit, so every legitimate change delivered by a commit was reported as an out-of-band change "reverted" -> compare live state against the last applied commit's state
- component.py::GitOps.revert: rolled back to commits[-2] regardless of whether it was ever applied, so after a refused unsigned commit the "revert" re-signed and re-published the current state (or an unverified one); unknown key -> KeyError, <2 commits -> IndexError -> revert to the last earlier *applied* commit, raise Unsigned / NothingToSync
- component.py::GitOps.sync: empty history raised IndexError; non-str signatures raised TypeError in compare_digest -> NothingToSync / treated as Unsigned

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
