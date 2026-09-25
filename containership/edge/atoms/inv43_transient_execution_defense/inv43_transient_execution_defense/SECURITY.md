# Security policy — INV-43 transient-execution defense

**Status:** DRAFT — contact and owner are unassigned (remediation item 51 BLOCKED on `governance/OWNERS.json`).

## Reporting
Report vulnerabilities privately to the security contact in `governance/OWNERS.json` (currently unassigned). Do not open public issues.

## Response SLA (proposed)
| Severity (CVSS v3.1) | Acknowledge | Fix or mitigation released |
|---|---|---|
| Critical ≥ 9.0, or any false-permit bug | 24 h | 7 days |
| High 7.0–8.9 | 3 days | 30 days |
| Medium 4.0–6.9 | 7 days | 90 days |
| Low | 14 days | next minor |

A new transient-execution vulnerability class (a new `/sys/.../vulnerabilities/*` entry) is handled as a **policy** change: the component already reports it and fails closed once it is in a required set; the SLA applies to adding it to the policy.

## Supported versions and end of life
| Version | Status | Security fixes until |
|---|---|---|
| 4.3.x | current | 12 months after 4.4.0 ships |
| 4.2.x | superseded | 2026-12-31 (proposed) |
| ≤ 4.1.x | EOL | none (had a skipped-tests-as-green defect) |

Runtime dependencies: none (stdlib only). Dev dependency `jsonschema` is tracked in `requirements-dev.lock`.
