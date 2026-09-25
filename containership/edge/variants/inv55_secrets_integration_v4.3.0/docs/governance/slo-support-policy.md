# SLO and support policy

| ID | INV55-GOV-SLO | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| SLO | Objective | Error budget | Source | Measured? |
|---|---|---|---|---|
| No leakage | zero secret values in logs/errors | none | `contract.py` | No production data |
| Scoping | zero resolutions outside scope | none | `contract.py` | No |
| Resolution latency | p99 < 5 ms from cache | 1 % may exceed | `contract.py` | Single host only: met sequentially, not at 16 threads (WVR-030) |
| Availability | NFR-001 99.9 % | 43 min/month | NFR.md | No |

Budget policy: exhausting a no-budget SLO MUST trigger SEV1 and a release freeze. Exhausting latency/availability budget SHOULD freeze feature releases until recovered.

Support: latest minor fully supported; previous minor receives security fixes for 6 months (proposed). Supported environments: compatibility-matrix.md.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Benchmark status |
