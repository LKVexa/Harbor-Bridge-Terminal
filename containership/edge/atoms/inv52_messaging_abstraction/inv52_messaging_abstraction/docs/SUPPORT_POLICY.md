# Support, patching and end-of-life — `DOC-INV52-SUP` v4.3.0 (C091, C094)

Status: PROPOSED — commitments are the organisation's to make; the numbers below are the proposal.

## SLOs and error budgets (C091)

| SLO | Objective | Window | Budget | Measured here |
|---|---|---|---|---|
| No silent drops | 100 % of zero-delivery messages reach dead letter | 30 d | none | enforced by construction + tests |
| Envelope completeness | 0 publishes without id/source | 30 d | none | enforced |
| Publish overhead | p99 ≤ 1 ms | 30 d | 1 % of minutes | bench p99 overhead (see PERFORMANCE.md); production measurement BLOCKED |
| Availability (serving READY/DEGRADED) | 99.9 % per site | 30 d | 43 min | BLOCKED (no production) |

Support commitment (proposed): business-hours support for SEV3, 24×7 for SEV1/2 once owners are assigned.

## Patching and vulnerability response (C094)

| Severity (CVSS) | Triage | Fix released | Deployed |
|---|---|---|---|
| Critical ≥ 9.0 | 24 h | 72 h | 7 d |
| High 7.0–8.9 | 3 d | 14 d | 30 d |
| Medium | 7 d | next minor | 90 d |
| Low | 30 d | best effort | — |

The package has no third-party runtime dependencies; the SBOM (`tools/sbom.py`) lists Dapr as an external optional component. Dapr CVEs follow Dapr's security advisories and the upgrade path in COMPATIBILITY.md.

## End of life

Each INV-52 minor is supported until two later minors are released or 12 months, whichever is later; interface majors get ≥ 12 months overlap after a successor is released. Deprecations are tracked in `governance/waivers.json` (`kind: deprecation`).
