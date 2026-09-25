# Governance (MC-083, MC-087, MC-088) — proposed

## Recurring reviews
| Review | Cadence | Evidence |
|---|---|---|
| Access (credential issuers, operator/auditor holders, key custody) | quarterly | signed review record in `governance/reviews/` |
| Policy (role matrix, precedence, residency rules) | quarterly | diff of `auth.ROLE_PERMISSIONS` + sign-off |
| Dependencies (Python, cryptography, pk_core, wasmCloud pins) | monthly | `evidence/sbom.cdx.json` diff + CVE scan |
| Configuration (all site overlays vs defaults) | monthly | config history export |
| Architecture (ADR validity, waivers) | semi-annual | ADR status, `waivers.json` |
| Performance thresholds | each release | perf gate + baseline diff |

## Patching / vulnerability / EOL SLAs
Critical CVE in a runtime dependency: patched release ≤ 7 days; high ≤ 30 days; medium ≤ 90 days; low next
minor. A 4.x minor is supported 180 days after its successor ships; EOL announced 90 days ahead.

## Change control
Changes to wire schemas, error codes, role matrix, precedence, persistence formats, thresholds, or the ADR
require owner review (`CODEOWNERS`) and a CHANGELOG entry; superseded records are kept, never edited.

## Exception / waiver / debt register
`governance/waivers.json` (time-bounded exceptions against checklist items) and `governance/debt.json`
(technical debt, deprecated behaviour). Each waiver needs: requirement ID, scope, quantified risk,
compensating controls, owner, approver, created, expiry, remediation milestone. The exit gate refuses GO while
any waiver is unapproved or expired.
