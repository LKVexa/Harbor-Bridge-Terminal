# MC-01 — Source recovery record

**Status: UNRESOLVED.** The original `MASTER.md` (Post-Kubernetes Master Prompt & Workflow Series v4.0.0,
element PLN-02) was not present in the v4.1.0 or v4.2.0 archives, nor in the v4.3.0 work-order inputs
(`pln02_application_plane_v4.2.0_hardened.zip`, `PLN02_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md`).

- No text has been reconstructed. Nothing in this repository is labelled verbatim source.
- `MASTER.provenance.json` records the search and the unresolved state.
- Requirement origin today: `contract.py` + `CHECKLIST.json` (derived artifacts) → `docs/spec/REQUIREMENTS.md`.

## Recovery procedure (when the source is located)
1. Place exact bytes at `docs/source/MASTER.md` (no normalisation).
2. Write `MASTER.sha256` (`sha256sum` format) and update `MASTER.provenance.json` (locator, repository,
   revision, retrieval date, custodian, method, licence/confidentiality constraints, signature if any).
3. If several candidates exist, keep all as `MASTER.candidate-N.md` with digests and record the selection.
4. Diff against `contract.py`, `CHECKLIST.json`, schemas; add a requirement-origin map to `TRACEABILITY.json`.
5. `tools/gate.py` then verifies the digest on every run and flips MC-01 to PASS.
