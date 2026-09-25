# Patching, vulnerability response and EOL (DRAFT — needs an accountable owner to bind)

| Severity (CVSS v3.1/v4) | Acknowledge | Fix released | Deployed |
|---|---|---|---|
| Critical (≥9.0) | 24 h | 7 days | 14 days |
| High (7.0–8.9) | 3 days | 30 days | 45 days |
| Medium | 7 days | 90 days | next release |
| Low | 30 days | best effort | next release |

- Intake: security contact (UNASSIGNED) → private triage → fix on a private branch → release with advisory.
- Rebuild: dependency or base-image advisories trigger rebuild + full release gate.
- Dependencies: runtime has none; test dependency `jsonschema` and framework `pk_core` reviewed monthly.
- EOL: each minor release is supported until two newer minors exist or 12 months, whichever is longer; `governance/compatibility_matrix.json` marks supported/deprecated/eol (4.1.0 is EOL, 4.2.0 deprecated).
