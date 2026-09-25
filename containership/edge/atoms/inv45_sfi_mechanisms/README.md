# INV-45 - SFI mechanisms

**Version:** 4.3.0 (see `CHANGELOG.md`) · **Group:** 01_Source_Inventory ·
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0 · **Checklist:** 100 requirements (`CHECKLIST.json`)

Software fault isolation for multi-tenant WebAssembly. Since 4.3.0 the repository contains a real
enforcement layer, not only a model:

* `production/` - strict Wasm parser + type validator, heap-masking **rewriter**, **independent verifier**
  that proves every memory access is confined to the tenant partition, sealed descriptors, and a
  **trusted loader** that re-binds the exact bytes at load time; plus the operational controls
  (capabilities, config generations, quarantine, audit chain, metrics/logs/traces, admission control).
* `sfi_core.py` - the 4.2.0 **reference model**, kept as a differential oracle. It is not the boundary.

Start at **`MASTER.md`** for the full map, trust boundary and data flow.

## Status - read before using

* 100-item checklist: **7 implemented · 61 engineered (unreviewed) · 23 partial · 7 open (human) ·
  2 open (external)** - see `CHECKLIST_AUDIT.json` / `MISSING_COMPONENTS.md`.
* The production exit gate (`tools/release.py gate`) is **NO_GO**: owners are not bound, the ADR and
  thresholds are unapproved, waivers are pending, `pk_core` is absent, and the perf gate fails PERF-01
  (worst-case masking overhead about 36 % against a 15 % contract SLO).
* Confinement is demonstrated in the real V8 engine: two tenants sharing one linear memory, randomised
  escape programs, canary regions untouched; the same harness shows an unrewritten module does escape.

## Quick start

```text
python -m inv45_sfi_mechanisms.production.cli preflight
python -m inv45_sfi_mechanisms.production.cli rewrite in.wasm out.wasm      # verifies before writing
python -m inv45_sfi_mechanisms.production.cli verify out.wasm
python inv45_sfi_mechanisms/tools/ci.py                                      # all lanes
```

Requirements: CPython >= 3.10, `cryptography` (Ed25519), Node.js 20/22/24 for the execution engine and
integration lane, `jsonschema` for the contract lane. `pk_core` is optional; without it the package still
imports and the `pk-core-gate` lane reports NOT RUN.

## Interfaces

Schemas in `schemas/` (proof, sealed descriptor, error, health, audit, config, submit/load/quarantine
requests, artifact statement, plus the 4.2.0 `PK_SFI_MODULE/1`, `PK_SFI_MASK/1`). Boundary table,
interaction semantics and limits: `docs/architecture/INTERFACES.md`. Errors: `docs/security/ERROR_CATALOG.md`.

## Operations

Runbooks (day-0/1/2, canary/rollback, emergency disable, incident): `docs/operations/RUNBOOKS.md`.
SLOs and telemetry: `docs/operations/SLO_AND_TELEMETRY.md`. Ownership: `OWNERSHIP.md` (roles UNASSIGNED).
