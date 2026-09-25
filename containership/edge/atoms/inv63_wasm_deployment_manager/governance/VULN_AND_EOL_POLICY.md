# INV-63 Vulnerability Response, Patching and EOL Policy

| Field | Value |
|---|---|
| Document ID | INV63-GOV-VULN-EOL |
| INV-63 C-IDs covered | C094 |
| Status | DRAFT — pending approval (all SLAs PROPOSED) |
| Owner | Security contact (role) — UNASSIGNED |
| Reviewers | Service owner (role), Release approver (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when a dependency in `pins.json` changes support status. |

## Scope
INV-63 package code, `cryptography` (46.0.7), Python runtime, Wadm (once pinned), NATS transport, pk_core.

## Intake
Sources: upstream advisories (Python, cryptography/OpenSSL, wasmCloud/Wadm, NATS), internal findings, reporters via the security contact (UNASSIGNED). No automated dependency scanner is configured in the package — open item.

## Remediation SLAs (proposed; from triage confirmation to fix deployed in prod)
| Severity (CVSS v3/v4) | SLA | Mitigation if no fix |
|---|---|---|
| Critical (9.0–10) | 72 h | emergency_disable / freeze affected paths within 24 h |
| High (7.0–8.9) | 7 days | compensating control within 72 h |
| Medium (4.0–6.9) | 30 days | — |
| Low (< 4.0) | 90 days or next release | — |

Exceptions require a dated waiver with owner and expiry in `governance/WAIVERS.json` (C099); expired waivers block release (gate G-06).

## Patching process
1. Update pin in `pins.json` (+ digest) and `requirements.lock`; record approval in `governance/APPROVALS.json` after release-approver review.
2. `python -m unittest discover -s tests`, `python perf/bench.py --gate`, `python audit.py`, `python gate.py` (verdict must be GO or CONDITIONAL_GO).
3. Roll out via `ops/runbooks/DAY1_DEPLOY.md`; staged per environment/site.

## Support window and EOL (proposed)
- Supported: current minor (4.3.x) and previous minor (4.2.x) for security fixes; 12 months after the next minor's GA.
- Schema majors: supported until the `schema.DEPRECATED` date (PK_DEPLOY_DESIRED/1 → 2027-09-30).
- Python: follow CPython EOL; drop a Python minor no later than its upstream EOL.
- EOL notice: >= 6 months before end of support, via release notes and INV-64/INV-66 owners.
