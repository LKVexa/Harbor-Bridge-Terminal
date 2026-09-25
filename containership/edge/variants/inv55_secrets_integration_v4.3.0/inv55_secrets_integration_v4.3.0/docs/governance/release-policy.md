# Release policy

| ID | INV55-GOV-RELEASE | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: release-manager>` · Approval: `status: PENDING-OWNER-APPROVAL`

## Current status (4.3.0)

`tools/exit_gate.py` → `evidence/exit_gate.json`: **verdict NO_GO** (2026-09-23T07:04:43Z). 4.3.0 MUST NOT be released to production.

- Test run: 137 run — 131 pass, 6 skip, 0 fail. The 6 skips are mandatory: 3 `pk_core` conformance (WVR-002) and 3 real-Vault (WVR-001; no Vault binary and container registry blocked in the authoring environment).
- 13 P0 components not IMPLEMENTED: #15, #18, #19, #38, #41, #45, #58, #82, #91, #94, #95, #96, #100 (each mapped in waiver-register.md). `evidence/exit_gate.json` must be regenerated to reflect #58.
- Traceability (`tools/traceability.py` → `evidence/traceability.json`, 100 rows): output of `python3 tools/traceability.py`: P0 18 IMPLEMENTED / 10 PARTIAL / 3 OPEN; P1 16/15/3; P2 16/15/4.
- Approvals: engineering, security, operations all PENDING (WVR-006).

## Release gate

A release MUST NOT be tagged unless:
1. `VERSION`, `service.py::__version__`, `CHANGELOG.md` agree.
2. CI `.github/workflows/ci.yml` passes: `test` (3.11–3.13), `vault-real` (`hashicorp/vault:1.17`), `secret-scan` (`tools/secret_scan.py`), `gate`.
3. `tools/benchmark.py` shows no > 10 % regression vs `evidence/benchmark_baseline.json` (performance-policy.md).
4. `tools/release_evidence.py` produces `evidence/release_evidence.json` (sha256 of every file, Python/platform versions, test results) and `evidence/sbom.cdx.json`.
5. `tools/exit_gate.py` returns GO: no mandatory skip, no P0 component below IMPLEMENTED; conditions (non-P0 PARTIAL/OPEN) MUST each map to a waiver row with approver and expiry.
6. Service owner, security owner and operations owner approvals recorded.

Skipped tests are reported as skipped, never as passes. Signing: NOT IMPLEMENTED (WVR-003).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | CI jobs and release tools |
| 4.3.0 | 2026-09-23 | Security-review test totals and traceability |
| 4.3.0 | 2026-09-23 | Exit-gate NO_GO status, traceability summary |
