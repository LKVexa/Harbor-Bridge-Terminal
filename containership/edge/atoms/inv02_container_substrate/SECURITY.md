# Security policy, vulnerability SLA and end-of-life (MC78)

> Status: **proposed defaults — owner approval required** (see `OWNERS.yaml`, `security_owner`).

## Reporting

Report suspected vulnerabilities privately to the security owner in `OWNERS.yaml`.
Do not open public issues for undisclosed vulnerabilities.

## Response SLA (from triage-confirmed report)

| Severity (CVSS v3.1 / exploitability) | Acknowledge | Fix or mitigation released | Advisory |
|---|---|---|---|
| Critical (≥9.0, or known exploited) | 1 business day | 7 days | with fix |
| High (7.0–8.9) | 2 business days | 30 days | with fix |
| Medium (4.0–6.9) | 5 business days | 90 days | next release notes |
| Low (<4.0) | 10 business days | next minor | release notes |

A missed SLA requires a waiver in `waivers/waivers.json` (owner ≠ approver, expiry, compensating control).

## Supported versions and EOL

| Line | Status | Security fixes until |
|---|---|---|
| 5.0.x | supported | 12 months after 5.1.0 ships |
| 4.2.x | security-only | 2027-03-22 (6 months from 5.0.0) |
| ≤ 4.1.x | end of life | — (read-compatibility of v4.1 manifests is retained in 5.x) |

EOL is announced at least 90 days ahead in `CHANGELOG.md`.

## Scanner-result handling

Vulnerability state is never a boolean: `unscanned`, `scan-failed`, `scan-stale`,
`clean`, `vulnerable`, `exception-approved` (`trust.ScanState`). Results are bound to the
exact image digest with scanner name, database version and scan time; stale results
are re-evaluated when `scan_max_age_s` (config) elapses or the policy bundle changes.

## Cryptography notes

`trust.py` implements Ed25519 in pure Python for verification without dependencies.
It is **not constant-time**: never hold production signing keys in this process —
sign in an HSM/KMS and use this module for verification only.
