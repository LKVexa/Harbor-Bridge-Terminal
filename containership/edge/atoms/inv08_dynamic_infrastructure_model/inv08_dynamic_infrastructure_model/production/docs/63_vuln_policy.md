# INV-08 vulnerability, patch and EOL policy (PROPOSED)

Machine-readable matrix: `production/vuln_policy.json`; logic: `production/vuln_policy.py`.

| Severity (CVSS) | Triage | Fix / release |
|---|---|---|
| critical (>= 9.0) | 1 day | 7 days, emergency release |
| high (7.0-8.9) | 3 days | 30 days |
| medium (4.0-6.9) | 7 days | 90 days |
| low (0.1-3.9) | 30 days | 180 days |

- Supported releases: latest 2 minor lines; a superseded line receives security fixes for 6 months, EOL notice 90 days.
- Dependency intake: the runtime has zero third-party dependencies; `pk_core` (optional) advisories are triaged via `vuln_policy.intake` once component 01 pins it.
- Emergency release: critical -> patch branch, full test suite normal and `-O`, SBOM + provenance (component 04), staged rollout (60) with canary gate; signing with a production key is BLOCKED.
- Notification and upgrade enforcement: `enforce_upgrade` refuses unsupported versions or overdue critical/high fixes; notification channels are UNASSIGNED (blocker).
