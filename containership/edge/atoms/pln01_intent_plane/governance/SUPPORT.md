# Production support commitments (MC-043)
| Severity | Definition | Response | Update cadence | Target mitigation |
|---|---|---|---|---|
| SEV1 | Intent lost/corrupted, admission bypass, plane down | 15 min, 24x7 | 30 min | 4 h |
| SEV2 | Mutations failing for many tenants, SLO breach | 30 min, 24x7 | 1 h | 8 h |
| SEV3 | Single tenant impact, degraded mode | 1 business day | daily | 5 business days |
| SEV4 | Question / minor defect | 3 business days | weekly | next release |
Supported versions: current minor and previous minor (N, N−1). Staffing of the 24x7 rota is **open** (OWNERS.yaml).
