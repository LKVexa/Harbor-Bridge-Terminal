# GAP-03 patch, vulnerability and end-of-life policy (MC-044)

**Status:** PROPOSED — not approved (no accountable owner). Machine-readable twin: `policy/support_policy.json`.

- **Support window:** each minor release is supported for 12 months after the next minor ships; majors 24 months.
- **Supported releases:** 4.3.x current (EoS 2027-09-30); 4.2.x security fixes only (EoS 2027-03-31); <=4.1 end-of-life. Maintenance window Tue 02:00-04:00 UTC.
- **Vulnerability response SLA (from triage):** actively exploited 24 h; Critical 72 h to patched release; High 7 days; Medium 30 days; Low next minor.
- **Intake:** security reports to the security on-call (UNASSIGNED); advisories published with CVE/CVSS and affected versions.
- **Scanning:** every release runs `supply_chain.vulnerability_scan` against a *sourced* advisory snapshot; an unsourced
  snapshot yields INDETERMINATE and blocks release (never reported as clean).
- **Runtime EOL:** a Python minor is removed from the compatibility matrix 30 days before upstream EOL (e.g. 3.10 EOL
  2026-10-31 → removal PR due 2026-10-01).
- **Backports:** Critical/High fixes are backported to every supported minor.
- **End of life:** announced ≥ 90 days ahead; after EOL no fixes; the exit gate refuses EOL artifacts.
- **Patch qualification:** targeted regression tests, full unit+contract suite (incl. `python -O`), security verification,
  compatibility matrix cells, benchmark smoke vs thresholds, 1% canary bake.
- **Emergency release path:** protected; still produces a signed artifact, audit trail and minimum qualification.
- **Runtime upgrade cadence:** adopt each new CPython minor within 6 months of GA.
