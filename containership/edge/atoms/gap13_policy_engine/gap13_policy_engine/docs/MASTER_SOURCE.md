# Master audit source (G13-MC-051)

**Finding:** 4.1.0 README claimed a bundled 100-item `MASTER.md`; the uploaded archive never contained it (recorded in the 4.2.0 audit).

**Decision:** `MASTER.md` is treated as a *historical reference* and is **superseded**. The authoritative normative sources for 5.0.0 are:

| Source | Role | Identity |
|---|---|---|
| `CHECKLIST.json` | 100 conformance requirements C001–C100 (pk_core) | digest recorded in each evidence manifest |
| GAP13 Policy Engine Missing Components Professional Checklist v1.0.0 | 51 work packages G13-MC-001…051 + EXT-01…05 | supplied by the owner 2026-09-22; digest recorded in evidence manifest `sources` |
| `docs/REQUIREMENTS.md` | SHALL requirements derived from both | versioned with the release |
| `docs/TRACEABILITY.json` | REQ → code → test → evidence | validated by `test_packaging` |

No file in this package claims `MASTER.md` is bundled (asserted by `test_packaging.test_no_dangling_master_reference`). If the original is recovered from the Post-Kubernetes Master Prompt & Workflow Series source, add it under `docs/legacy/`, record its SHA-256 here, and mark it *legacy* — it does not override the sources above. Changes to master audit logic require service-owner and security-owner review.
