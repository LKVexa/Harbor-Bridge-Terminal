# Patching, Vulnerability Response and End-of-Life Policy (PROPOSED)

* Supported lines: current minor (4.3.x) and previous minor for 6 months after a new minor ships. 4.2.x reaches EOL on 2027-03-23.
* Security patch SLA from confirmed report: Critical 72 h, High 7 days, Medium 30 days, Low next minor.
* CVE intake: security@ contact in `governance/OWNERS.json`; triage within 1 business day; embargoed fixes released as patch versions with advisory.
* Dependencies: runtime is stdlib-only; Python itself follows upstream EOL (3.10 EOL Oct 2026 → drop in 4.4). Build backend pin reviewed quarterly.
* Scanning: SBOM (`evidence/sbom.cdx.json`) is scanned in CI with the estate scanner; the authoring environment had no scanner/index access, so no scan result is recorded (`evidence/vulnerability_scan.json` = NOT_RUN).
