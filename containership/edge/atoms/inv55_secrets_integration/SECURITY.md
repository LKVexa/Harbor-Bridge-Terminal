# Security policy (checklist #93, #100) — DRAFT, contacts UNASSIGNED

Supported versions: 4.3.x (current), 4.2.x (security fixes until 4.4.0 + 90 days). Earlier: end of life.
Reporting: private channel UNASSIGNED (security owner in `docs/governance/OWNERSHIP.md`). Do not open public issues for vulnerabilities; never include a real secret in a report.
Response targets: acknowledge 2 business days; triage 5; fix critical 7 days, high 30, medium 90; coordinated disclosure after fix or 90 days.
Patching: dependency and CPython advisories reviewed weekly; emergency release may skip the canary only with release-authority approval recorded in `WAIVERS.json`.
Releases must be tagged, carry `evidence/release/` (SBOM, digests, gate results) and be signed/attested by the release authority — **signing identity not yet provisioned (W-009)**.
