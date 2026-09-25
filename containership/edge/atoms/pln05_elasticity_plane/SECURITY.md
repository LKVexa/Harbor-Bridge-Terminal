# Security policy — PLN-05 elasticity plane

## Supported versions
| Version | Supported |
|---|---|
| 4.2.x | yes |
| < 4.2 | no |

## Reporting a vulnerability
Report privately to the role `pln05.security-contact` (resolved through the owner's directory; see `ops/oncall.json`). Do **not** open a public issue for an unpatched vulnerability. Include version, reproduction, impact. Acknowledgement within 2 business days; remediation targets: critical 7 days, high 30, medium 90, low next release.

## Coordinated disclosure
We publish an advisory with the fixed version once a patched release is available, or 90 days after the report, whichever is first, unless agreed otherwise with the reporter. Advisories name the first fixed version; `security/approved-versions.json` drops vulnerable versions.

Policy owner: `pln05.security-contact`. Last reviewed: 2026-09-23 (drafted by the 4.2.0 pass; owner review pending).
