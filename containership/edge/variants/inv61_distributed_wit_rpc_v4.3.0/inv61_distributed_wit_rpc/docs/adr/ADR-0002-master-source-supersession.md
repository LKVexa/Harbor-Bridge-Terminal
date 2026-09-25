# ADR-0002 — `MASTER.md` supersession

* **Status:** Proposed (W-001 approval pending) · **Date:** 2026-09-22

## Context
The 4.1.0 README claimed the 100 master prompt/workflow documents lived in `MASTER.md`. The file is absent from the supplied archive; 4.2.0 removed the claim. See `docs/MASTER_LOSS_RECORD.md`.

## Decision
`CHECKLIST.json` is the single authoritative source for the 100 controls (C001–C100). `MASTER.md` is not recreated: fabricating its historical wording would be worse than its absence. The per-control narrative now lives in `TRACEABILITY.json` (generated, never hand-edited) which links each control to requirements, artifacts and tests.

## Enforcement
`tests/test_traceability.py` fails when: count ≠ 100, IDs not unique/sequential, any control lacks a traceability row, any row references a missing file or test, or `TRACEABILITY.json` differs from a fresh regeneration. `CHECKLIST.json`'s SHA-256 is recorded in the release manifest.

## If the original is found
Import it read-only under `docs/historical/MASTER.md` with its recovered provenance; do not edit; add a digest to the release manifest.
