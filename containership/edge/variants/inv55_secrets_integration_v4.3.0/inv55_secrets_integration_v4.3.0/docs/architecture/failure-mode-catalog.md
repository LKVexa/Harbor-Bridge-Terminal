# Failure-mode catalog (FMEA)

| ID | INV55-ARCH-FMEA | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

Scoring: Severity (S), Occurrence (O), Detection (D) each 1–10; RPN = S×O×D. Scores are engineering estimates, not measurements.

| # | Failure mode | Detection | Effect | Mitigation (code) | S | O | D | RPN |
|---|---|---|---|---|---|---|---|---|
| F1 | Vault unreachable / 5xx / 429 | `ProviderUnavailable`; circuit `open`; `inv55_requests_total{outcome="retryable"}` | Resolve fails (offline-deny) | `RetryPolicy`, `CircuitBreaker`, optional stale cache | 6 | 5 | 2 | 60 |
| F2 | Vault sealed / uninitialised | `health()` `sealed`, `reachable=false` | Start in `degraded`; resolves fail | `VaultProvider.health` | 6 | 3 | 2 | 36 |
| F3 | Vault token expired / revoked | 401/403 → token cleared | That request DENIED; next call re-logs in | `_request` resets `_token` | 5 | 4 | 4 | 80 |
| F4 | Audit sink write fails (disk full, EIO) | `inv55_audit_failures_total` | All ops fail AUDIT_UNAVAILABLE | fail-closed `_audit` | 7 | 3 | 2 | 42 |
| F5 | Audit file tampered | `audit.verify_chain` (offline) | Loss of forensic integrity | Hash/HMAC chain; verified at boot by `resume_from_file` → quarantine (`bootstrap.py`); runtime verify NOT IMPLEMENTED | 8 | 2 | 4 | 64 |
| F6 | Clock rollback / NaN | `CLOCK_ROLLBACK` errors | All requests fail | `_now` | 7 | 2 | 2 | 28 |
| F7 | Process crash/restart | restart | Leases, cache, idempotency lost (clients re-resolve); scopes/retirements restored from `state_path` | `_save_state`/`_load_state`, fail-closed leases | 4 | 4 | 3 | 48 |
| F8 | Overload | `OVERLOADED`/`QUOTA_EXCEEDED` counts | Requests shed | `AdmissionController` | 4 | 5 | 2 | 40 |
| F9 | Unauthenticated flood consumes global in-flight slots | `OVERLOADED` rate | Shedding for all tenants | `admit()` cap; per-source limiting NOT IMPLEMENTED (quota spoofing fixed by `charge()`) | 5 | 3 | 4 | 60 |
| F10 | Concurrent rotation on two instances | CAS conflict → CONFLICT (E019) | One writer loses | Vault KV v2 CAS when `expected_version` given | 5 | 3 | 3 | 45 |
| F11 | Stale cache after rotate on another instance | none | Old version served up to 30 s | `cache_ttl_s` | 4 | 5 | 8 | 160 |
| F12 | Retire on one instance not seen by others | none | Retired version still served elsewhere | use `destroy=true`; replication NOT IMPLEMENTED (WVR-012) | 7 | 4 | 8 | 224 |
| F13 | Stall (in-flight but no progress) | `health()["stalled"]` | Readiness false | stall detector | 5 | 2 | 3 | 30 |
| F14 | Malformed / oversize Vault response | ProviderError | PROVIDER_UNAVAILABLE | `MAX_RESPONSE_BYTES`, JSON parse guard | 4 | 2 | 3 | 24 |
| F15 | Metric cardinality explosion | `Metrics.dropped_series` | Missing metrics | bounded labels, 2 000 series | 3 | 2 | 5 | 30 |
| F16 | Workload signing key compromise | external | Arbitrary principals forged | key rotation procedure (incident-response.md); multi-key NOT IMPLEMENTED | 10 | 2 | 8 | 160 |
| F17 | Unexpected exception in handler | `inv55_internal_errors_total{kind}` | INTERNAL returned, no text leaked | catch-all in `_run` | 4 | 2 | 2 | 16 |
| F18 | State file write fails | INTERNAL on scope/retire; `inv55_internal_errors_total` | Change rejected; memory and file unchanged | write-ahead `_save_state` + atomic replace; caller retries | 3 | 2 | 2 | 12 |
| F20 | Thread contention under concurrency | `inv55_request_seconds` p99 | p99 21 ms at 16 threads (benchmark) | process-per-core scaling (WVR-030) | 5 | 5 | 3 | 75 |
| F19 | Vault DR secondary targeted | `health()` reachable=false | start degraded | `replication_dr_mode` check | 4 | 2 | 2 | 16 |

Highest RPN (F12, F11, F16) are tracked in waiver-register.md. Fault-injection evidence: `tests/test_resilience.py::FaultInjection`.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | F18 write-ahead; F20 concurrency finding |
| 4.3.0 | 2026-09-22 | Rescored after admission, audit-resume, state persistence, INTERNAL fixes |
