# Security and maintenance policy — INV-10 (MC-34)

## Supported versions
| Version | Status | Security fixes until |
|---|---|---|
| 4.3.x | current | 12 months after 4.4.0 GA |
| 4.2.x | maintenance | 6 months after 4.3.0 GA |
| ≤ 4.1.x | **end of life** — identity defect A-02/A-03; migrate with `inv10 migrate` | — |

## Reporting
Report privately to the security owner in `docs/OWNERSHIP.md` (fallback: davidpaulrussell@linearfinance.org).
Do not open public issues for vulnerabilities. Acknowledge ≤ 2 business days.

## Response targets (from triage)
| Severity (CVSS v3.1) | Fix / mitigation |
|---|---|
| Critical ≥ 9.0 | 7 days; emergency freeze/quarantine available immediately (`CompositionService.set_frozen`, `quarantine_*`) |
| High 7.0–8.9 | 30 days |
| Medium 4.0–6.9 | 90 days |
| Low | next minor |

## Process
Triage → CVE request (if externally consumed) → private fix branch → regression test → signed release
(`tools/sign_release.py`) → advisory with affected versions, identity impact, and migration notes.
Dependency monitoring: runtime is stdlib-only; the build toolchain in `requirements.lock` and optional
`pk_core` are reviewed each release (SBOM: `sbom.cdx.json`).
