# Audit report — INV-35 v4.3.0 closure pass

**Input:** v4.2.0 archive + `inv35_v4.2.0_COMPREHENSIVE_MISSING_COMPONENT_CHECKLIST.md` (92 open rows + 11 repository omissions = 103 packages, 1 943 checkboxes).
**Baseline preserved:** `audit/AUDIT_MATRIX_v4.2.0.json`, `audit/MISSING_COMPONENTS_v4.2.0.md`, `audit/AUDIT_REPORT_v4.2.0.md`.
**Executed checklist:** `audit/INV35_v4.3.0_EXECUTED_CHECKLIST.md` — every box annotated.

## Before → after

| Measure | v4.2.0 | v4.3.0 |
|---|---|---|
| Audit rows present / partial / missing | 8 / 23 / 69 | 8 / 91 / 1 |
| Work packages with implementation + evidence | — | 102 of 103 (`implemented_pending`) |
| Tests | 35 (3 skipped) | 139 (3 skipped: pk_core) |
| Interface schemas | 0 | 10 generated documents |
| Conformance fixtures | 0 | 19 |
| verify.py verdict | PARTIAL (pk_core only) | PARTIAL (28 enumerated production blockers, 0 technical failures) |

## Why rows are `partial`, not `present`
The checklist's own rules forbid marking a row `present` before owner/reviewer approval is recorded, and forbid
treating the Python model as production virtio/vhost evidence. Approvals, a license choice, the `pk_core` pin, a
signing key, a canary drill and real-backend/hardware runs cannot be produced by the build; they are enumerated
as blockers in `CLOSURE_LEDGER.json` and in `conformance/PK_GATE_RESULTS.json`.

## Notable findings during the pass
1. **Per-call authorisation cost** was 42 % of facade time; a verified-token cache (expiry/scope still checked every call) cut p50 58 %.
2. **Secret-name detector false positive** — substring matching flagged `require_capability`; replaced with word-boundary matching (tested).
3. **Quota refusal after validation** must roll back the io_model reservation; tested (`test_T12_tenant_quota_exhaustion`).
4. **Wire-format slot shadowing** — duplicate slot indices in a JSON request could shadow a descriptor; refused with E101 (fixture `duplicate_slot_shadowing`).
