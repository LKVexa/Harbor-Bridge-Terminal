# Remaining Components - INV-35 v4.3.0

Regenerated from `CLOSURE_LEDGER.json` after the v4.3.0 closure pass. The v4.2.0 inventory is preserved at `audit/MISSING_COMPONENTS_v4.2.0.md`.

**Audit rows:** {'present': 8, 'partial': 91, 'missing': 1}  **Work packages:** {'implemented_pending': 102, 'open': 1}

Every open item below is a *closure input* the build cannot supply itself (a person's approval or decision, an external artifact, or hardware). Nothing in this list is unimplemented code in the repository except C068 (power/thermal), which needs physical far-edge hardware.

## Blockers by kind

- **owner/reviewer approval not yet recorded (governance/APPROVALS.json)** — 103 package(s): C005, C009, C010, C011, C012, C013, C014, C015, C016, C017, C018, C019, C020, C021, C022, C023, C024, C025, C026, C027, C028, C029, C030, C031, C032, C033, C034, C035, C036, C037, C038, C039, C040, C041, C042, C043, C044, C045, C046, C047, C048, C049, C050, C051, C052, C053, C054, C055, C056, C057, C058, C059, C060, C061, C062, C063, C064, C065, C066, C067, C068, C069, C070, C071, C072, C073, C074, C075, C076, C077, C078, C079, C080, C082, C083, C084, C085, C086, C087, C088, C089, C090, C091, C092, C093, C094, C095, C096, C097, C098, C099, C100, REPO-001, REPO-002, REPO-003, REPO-004, REPO-005, REPO-006, REPO-007, REPO-008, REPO-009, REPO-010, REPO-011
- **needs a real production virtio/vhost backend or adjacent-layer build (WVR-002/WVR-003)** — 6 package(s): C013, C030, C061, C083, C084, C093
- **evidence sealing key not provisioned; Sigstore signing is TD-002** — 5 package(s): C045, C090, C100, REPO-006, REPO-010
- **approved pinned pk_core unavailable; full certification path cannot run** — 4 package(s): C040, C093, C100, REPO-002
- **OWNERS roles UNASSIGNED (governance/OWNERS.json)** — 3 package(s): C009, C100, REPO-011
- **repository license not selected (governance/LICENSE_DECISION.json)** — 2 package(s): C100, REPO-001
- **ADR status is Proposed, not Accepted** — 1 package(s): C010
- **Nexus spec manifest is generated but not approved** — 1 package(s): C031
- **node/peer mTLS and attestation are production bindings** — 1 package(s): C044
- **production KMS/HSM binding** — 1 package(s): C047
- **microarchitectural side channels owned by INV-43** — 1 package(s): C050
- **zero-copy/kernel-bypass are backend-owned (WVR-003)** — 1 package(s): C066
- **needs physical far-edge hardware (WVR-001)** — 1 package(s): C068
- **fleet-scale runs need a real fleet** — 1 package(s): C088
- **canary/rollback not yet exercised on a candidate (G13)** — 1 package(s): C092
- **OWNERS roles UNASSIGNED (governance/OWNERS.json) (on-call destination)** — 1 package(s): C097
- **waivers WVR-001..003 await approval** — 1 package(s): C099
- **CI not yet executed on a hosted runner** — 1 package(s): REPO-003
- **scanners run only in CI (not installed here)** — 1 package(s): REPO-004

## Fastest path to production-green

1. Assign the five OWNERS roles and have each accept (`governance/OWNERS.json`), set the on-call destination.
2. Choose the repository license; add `LICENSE`; set `governance/LICENSE_DECISION.json` to approved.
3. Obtain the approved `pk_core` version + digest; pin it in `release/dependencies.json` and `pyproject.toml`; run with `PK_CORE_PATH`.
4. Review and approve the documents in `governance/APPROVALS.json` (ADR-0001 → Accepted) and the three waivers.
5. Provision `INV35_EVIDENCE_KEY` in CI; run the canary/rollback drill and record `evidence/rollout-4.3.0.json`.
6. Run the fixtures against a real vhost-user/vDPA backend to retire WVR-002/003; measure power/thermal on far-edge hardware (WVR-001).
