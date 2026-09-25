# MASTER.md source corpus - status record (MC-02)

| Field | Value |
|---|---|
| Status | **Missing; not reconstructed.** Retirement proposed, pending repository-owner decision. |
| First referenced | README of 4.1.0 ("carried verbatim") |
| Found in supplied archives | No (neither 4.1.0-era nor the 5.0.0 hardened archive contained it) |
| Action taken in 5.1.0 | Nothing was written in its place. No content was inferred or fabricated. |

## What replaced it as the source of truth

For the 5.1.0 pass, the normative inputs are:

1. `CHECKLIST.json` - the 100 INV-36 controls (shipped since 4.x).
2. `docs/source/INV36_v5.0.0_MISSING_COMPONENTS_COMPREHENSIVE_CHECKLIST.md` - the missing-component checklist supplied by the repository owner on 2026-09-22 (SHA-256 recorded in `docs/source/SOURCES.json` and verified by `tools/docs_check.py`).
3. `requirements/requirements.json` - SHALL requirements derived from the two sources above.

## Decision needed from the repository owner

- (a) Supply the original `MASTER.md` from the Post-Kubernetes Master Prompt & Workflow Series v4.0.0 package, with its source path/commit and SHA-256 - it will then be added under `docs/source/`, recorded in `SOURCES.json`, and its normative sections indexed; **or**
- (b) Confirm retirement - this record then becomes the deprecation record and the "proposed" status is removed.

Either way, reviewer approval that nothing was fabricated is required (MC-02.022). `tools/docs_check.py` fails the build if any document claims `MASTER.md` is present while it is absent.

Regeneration procedure (if restored): add file -> update `SOURCES.json` (sha256, source, retrieval date, role) -> run `tools/docs_check.py` -> reconcile any conflicting requirement into `requirements/requirements.json` -> `tools/traceability.py --write`.

Digest embedding: generated artifacts do not embed a corpus digest directly; gate evidence binds the full repository source digest (which covers `docs/source/`) and records the requirements and IDL digests under `references`, which is sufficient to reconstruct which normative inputs a release was built against.
