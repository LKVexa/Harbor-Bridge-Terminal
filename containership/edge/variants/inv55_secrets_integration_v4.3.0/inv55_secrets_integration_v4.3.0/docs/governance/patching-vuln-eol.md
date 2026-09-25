# Patching, vulnerability response, EOL

| ID | INV55-GOV-PATCH | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

- Runtime surface: CPython stdlib only (THIRD-PARTY-NOTICES.md) + Vault server. Advisories to track: CPython (`ssl`, `urllib`, `json`), OpenSSL linked by CPython, HashiCorp Vault.

| Severity (CVSS) | Triage | Fix released |
|---|---|---|
| Critical ≥ 9.0 | 24 h | 7 days |
| High 7.0–8.9 | 3 days | 30 days |
| Medium | 14 days | 90 days |
| Low | 30 days | next minor |

(Targets proposed; `status: PENDING-OWNER-APPROVAL`.)

- EOL: a Python version is dropped when upstream EOL is reached; a Vault minor is dropped from `SUPPORTED_SERVER_VERSIONS` when HashiCorp ends support. Changes follow compatibility-policy.md.
- Reporting: SECURITY.md. Credential scanning: `tools/secret_scan.py` in CI. Dependency vulnerability scanning / SBOM: NOT IMPLEMENTED (only test dependency is `jsonschema`, pinned in `requirements-test.txt`).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Secret scan, test deps |
