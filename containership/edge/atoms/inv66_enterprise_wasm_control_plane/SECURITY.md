# Security policy (MC-062)

- **Reporting:** private report to the security owner (`governance/owners.json`; currently UNASSIGNED).
- **Patch SLAs (PROPOSED, need security-owner approval):**

  | Severity | Actively exploited | Otherwise |
  |---|---|---|
  | Critical | 24 h out-of-band | 7 days |
  | High | 72 h | 30 days |
  | Medium | — | 90 days |
  | Low | — | next minor |

- **Dependencies:** runtime needs only `cryptography`, pinned in `constraints.txt`. `jsonschema` is test-only. The SBOM is at `release/sbom.cdx.json`.
- **Vulnerability scanning:** `tools/ci.py` lane `vuln-scan` runs `pip-audit` against `constraints.txt` when it is installed. Otherwise it reports **NOT RUN**, which is never PASS. Continuous monitoring against published SBOMs needs a scanner service (OPEN_EXTERNAL).
- **Exceptions:** `release/waivers.json`, where every exception has an owner, rationale, compensating control and expiry.
