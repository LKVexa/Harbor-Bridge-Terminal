# Security policy — INV-53 Message reliability

## Reporting a vulnerability
Report privately to the security_owner named in `governance/owners.json` (**currently UNASSIGNED** — until a
name and a private channel are bound, there is no working intake, and the exit gate stays NO_GO for that
reason). Do not open public issues for vulnerabilities. Include version, config digest and a minimal
reproduction; never include production payloads or keys.

## Response targets (proposed)
| Severity (CVSS) | Acknowledge | Fix or mitigation | Disclosure |
|---|---|---|---|
| Critical ≥ 9.0 | 24 h | 7 days | coordinated, embargo ≤ 90 days |
| High 7.0–8.9 | 72 h | 30 days | coordinated |
| Medium/Low | 5 days | next minor release | release notes |

## Supported versions and end of life
5.1.x: supported. 5.0.x: security fixes until 5.1 passes its exit gate. ≤ 4.1: end of life (stale-ack defect).
EOL notices are given one minor release in advance in CHANGELOG.md.

## Embargo
Fixes for embargoed issues are developed in a private branch; the release note names the CVE after disclosure.
