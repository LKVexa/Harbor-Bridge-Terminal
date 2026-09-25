# Patching, vulnerability response and end-of-life (INV29-MC096) — PROPOSED

| Severity (CVSS v3/v4) | Triage | Fix available in main | Released + rolled out |
|---|---|---|---|
| Critical ≥ 9.0, or any bypass of the two-layer invariant / import closure | 24 h | 72 h | 7 d |
| High 7.0–8.9 | 2 business days | 7 d | 14 d |
| Medium 4.0–6.9 | 5 business days | 30 d | next release |
| Low | best effort | next minor | next minor |

* Intake: private advisory to `@inv29-security`; never a public issue.
* Runtime dependencies bundled: **none** (stdlib only), so `security/vuln_scan.json` covers the interpreter + declared externals. pk_core and sibling elements are scanned by their owners; their advisory feeds must be subscribed by the security owner.
* Support window: the latest minor of the current major, plus the previous minor for 90 days after a new minor. A major is end-of-life 12 months after its successor's GA.
* Waivers for unpatched vulnerabilities follow `governance/WAIVERS.json` rules and may never cover a Critical.

**Status: OWNER_ACTION** — SLA values require owner and security-owner sign-off.
