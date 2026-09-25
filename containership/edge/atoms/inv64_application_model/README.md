# INV-64 - Application model

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Governing source for 4.3.0:** `source/INV64_v4.2.0_MISSING_COMPONENTS_CHECKLIST.md` (digest in `provenance/master-source.json`). The series `MASTER.md` is **not** included (MC-01, recorded BLOCKED).
**Production status:** release gate verdict **NO_GO** — see "Release status" below.

The application model is the declarative description of an application: its components, the providers they link to, and the traits -- scaling, spread -- attached to each. Its value is validation before anything runs: a link to a component that does not exist, a trait on a component that is not there, or a schema version the platform does not speak is refused at submit.

## Responsibility

Own the application manifest: schema versioning, component and provider declarations, link and trait validation, and a canonical form for diffing and signing.

## Owns

- Manifest schema and versions
- Component and provider declarations
- Link validation
- Trait validation
- Canonical manifest form

## Explicitly does not own

- Running applications
- Reconciliation
- Provider implementations
- Artifact storage
- Policy decisions

## Non-goals

- Running anything
- Reconciling
- Implementing providers

## Interfaces

Full inventory and semantics: **INTERFACES.md**. Contracts (all versioned, schemas in `schema/`):

- `manifest` / `validate` / `canonical` — PK_APP_MANIFEST/1, PK_APP_VALIDATE/1, PK_APP_CANONICAL/1 (pure API, `manifest.py`)
- `submit` — PK_APP_SUBMIT_REQUEST/1 → PK_APP_SUBMIT_RESPONSE/1 over protocol PK_APP_SUBMIT/2 (`service.py`: authn → authz → tenancy → bounds → validate → canonical → audit)
- `error` — PK_APP_ERROR/1 · `status` — PK_APP_STATUS/1 · `overlay` — PK_APP_OVERLAY/1 · `audit` — PK_APP_AUDIT/1 · `decision` — PK_APP_DECISION/1
- WIT contract (no Wasm build yet): `wit/inv64-app-model.wit`

## Service-level objectives

- **fail at submit** - zero dangling links reach deployment (error budget: no budget)
- **canonical identity** - equivalent manifests share one digest (error budget: no budget)
- **validation time** - p99 under 5ms (error budget: 1% may exceed)

## Running it

From the directory that contains `inv64_application_model/`:

```
python inv64_application_model/tests/run_all.py                 # all suites (test_component needs pk_core)
python inv64_application_model/tests/run_all.py --standalone-only
python -m inv64_application_model.tools.run_evidence --out inv64_application_model/evidence   # every evidence producer + exit gate
python -m inv64_application_model.release_gate                    # gate only (exit 0 GO / 2 CONDITIONAL_GO / 3 NO_GO)
python -m inv64_application_model.tools.preflight --certification
sh inv64_application_model/tools/bootstrap.sh [--certification]   # Windows: tools\bootstrap.ps1
```

Installable package: `pyproject.toml` (`inv64-application-model`, Python 3.10–3.13, stdlib-only core, optional `[crypto]`).
Editable development install: `pip install -e inv64_application_model` (dev only); certification installs use the built wheel with `constraints-certification.txt`.
With `pk_core` available: `python -m pk_core list | run INV-64 | gate INV-64` and pass the gate output to `release_gate --pk-gate`.

## Day-0 / day-1 / day-2

Executable runbooks: **ops/RUNBOOK.md**; incidents: **ops/INCIDENT_RESPONSE.md**; rollout policy: **ops/ROLLOUT_POLICY.json** (`rollout.py`); backups: **BACKUP_RESTORE.md**.

## Release status (4.3.0)

`evidence/EXIT_GATE.json` verdict: **NO_GO**. Everything implementable inside the repository is implemented and tested (26 of 40 missing components IMPLEMENTED_LOCAL; 77/100 checklist controls verified). The remaining blockers need the owner or systems outside this archive:

1. `pk_core` source + version + digest (MC-02) — integration conformance cannot run.
2. Real INV-10/63/65/66 implementations (MC-10) — only emulators are tested.
3. Named owners, approved ADR-0001, license decision (MC-04, MC-38) and first reviews/drills (MC-31, MC-33–35).
4. Managed signing key / KMS / trust anchors (MC-15, MC-17, MC-39) — release signatures are ephemeral.
5. CI executed on real runners across the compatibility matrix (MC-27, MC-37) and a designated performance reference environment (MC-21).

## Audit evidence

- `AUDIT_REPORT.md` — 4.3.0 remediation audit: defects found, what was built, verification, residual blockers.
- `COMPONENTS_STATUS.json` — MC-01..MC-40 status, artifacts, tests, blockers (generated).
- `evidence/ITEM_LEDGER.json` — all 750 checklist items with status and basis (generated).
- `REQUIREMENTS_TRACEABILITY.md` / `evidence/REQUIREMENTS_MATRIX.json` — the 100 INV-64-C### controls.
- `evidence/` — machine-readable evidence (tests, fuzz, faults, stress, perf, build, integration, audit, drill, governance, supply chain) and `EXIT_GATE.json`.
- `SPECIFICATION.md`, `INTERFACES.md`, `SECURITY_ARCHITECTURE.md`, `SECURITY_RESPONSE.md`, `CONFIGURATION.md`, `FMEA.md`, `BENCHMARKS.md`, `TELEMETRY_POLICY.md`, `COMPATIBILITY.md`, `OAM_PROFILE.md`, `BACKUP_RESTORE.md`, `DEPENDENCIES.md`, `LICENSING.md`.
