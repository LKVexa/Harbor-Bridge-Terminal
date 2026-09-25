# Security Policy

## Reporting a vulnerability
Email the component owner listed in `OWNERS.md` with subject `GAP-01 SECURITY`. Do not open public issues. Include version (`VERSION`), reproduction, and impact.

## Response targets
| Severity (CVSS v3.1) | Acknowledge | Fix or mitigation released |
|---|---|---|
| Critical (≥ 9.0) | 1 business day | 7 days |
| High (7.0–8.9) | 2 business days | 30 days |
| Medium | 5 business days | next minor release |
| Low | 10 business days | best effort |

Advisories list affected versions, fixed version, and workaround. The runtime has no third-party dependencies; dev-tool advisories (ruff/mypy/coverage) do not affect shipped artifacts.

## Supported versions
See `SUPPORT.md`.
