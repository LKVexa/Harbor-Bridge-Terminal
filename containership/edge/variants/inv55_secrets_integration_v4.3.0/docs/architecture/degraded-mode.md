# Degraded mode

| ID | INV55-ARCH-DEGRADED | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Trigger | Entry | Behaviour | Exit |
|---|---|---|---|
| Provider unreachable at `start()` | `starting → degraded` | Requests served; provider reads fail unless cache/stale grace | Successful provider read in `resolve` → `ready` |
| Provider unavailable during `resolve` with `stale_grace_s > 0` and cached entry in window | `ready → degraded` | That resolve returns `outcome: degraded` | Successful provider read |
| Unfreeze while provider unreachable | `frozen → degraded` | as above | as above |

- Degraded does NOT relax authentication, authorization, scope, retirement or audit.
- `health()["ready"]` stays true in degraded (load balancers keep routing); `state: "degraded"` and `state_reason` are exposed for alerting.
- Resolves that fail with PROVIDER_UNAVAILABLE while `stale_grace_s == 0` do not change state; the service stays `ready`. State-based alerting therefore under-reports outages with the default config — alert on `inv55_requests_total{outcome="retryable"}` instead (dashboards-alerts.md).
- Evidence: `tests/test_resilience.py::FaultInjection.test_partition_degraded_then_reconnect`.
- Read-only mode (reject rotate while allowing resolve) is NOT IMPLEMENTED.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Test evidence |
