# Constraint precedence

| ID | INV55-ARCH-PRECEDENCE | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

When constraints conflict, the higher row MUST win.

| Rank | Constraint | Evidence in code |
|---|---|---|
| 1 | Security (authn, authz, no leakage, audit durability, clock integrity) | `_guard`, `_audit` fail closed; `_now` CLOCK_ROLLBACK |
| 2 | Operator safety controls (freeze/quarantine) | `_guard` returns FROZEN regardless of load or SLO |
| 3 | Residency | Configuration choice only (deployment-patterns.md); no runtime guard |
| 4 | Correctness / consistency (retired versions, CAS) | `_retired` check precedes serving; `write(cas=...)` |
| 5 | Availability / SLO (degraded cache serving) | Only if `stale_grace_s > 0` and never over rows 1–4 |
| 6 | Fairness / capacity (quotas) | `AdmissionController` |
| 7 | Latency | Cache, `request_timeout_s` |
| 8 | Cost | Not modelled |

Operator override MUST NOT bypass rank 1: there is no code path that skips authentication, authorization or audit. Freeze requires role `operator` (`SecretsService.freeze`).

Order of checks in a request (`_run` then handler): request-type check → clock → global admission (`admit`) → deadline → protocol negotiate → input validation → FROZEN state → authenticate → per-tenant quota (`charge`) → authorize → (scope) → provider → retired check → lease limits → audit → act.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Updated check order for admission split |
