# Disconnected / intermittent-connectivity policy

| ID | INV55-ARCH-DISCONNECTED | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

Implemented in `service.py::SecretsService.resolve` with `ServiceLimits.cache_ttl_s` (30 s) and `stale_grace_s` (0 s).

1. Fresh cache (age <= `cache_ttl_s`): served without contacting the provider, outcome `success`.
2. Cache miss/expired: provider read via retry + circuit breaker.
3. Provider unavailable and `stale_grace_s == 0` (default): request fails `PROVIDER_UNAVAILABLE`. **Default is offline-deny.**
4. Provider unavailable, `stale_grace_s > 0`, cached entry age <= `cache_ttl_s + stale_grace_s`: served with outcome `degraded`, audit reason `granted_degraded`, service transitions `ready → degraded`.
5. On the next successful provider read the service transitions `degraded → ready`.

Normative:

- Deployments MUST keep `stale_grace_s = 0` unless the owner records a waiver accepting stale reads (a rotated or retired-elsewhere secret may be served for up to `cache_ttl_s + stale_grace_s`).
- Authorization, scope and audit are never skipped offline: `_guard` and `_audit` run on every call; if the audit sink is down the request fails.
- `use` of an existing lease does not contact the provider and continues to work offline until lease expiry.
- `rotate`, `retire(destroy=true)` and provider-backed `revoke` require the provider; there is no write queue. NOT IMPLEMENTED.
- Edge synchronisation / local replica: NOT IMPLEMENTED.
- DENIED from the provider is never served from cache.

Evidence: `tests/test_resilience.py::FaultInjection.test_offline_default_is_deny`, `test_partition_degraded_then_reconnect`, `test_provider_denied_maps_to_denied_not_retry`.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Test evidence |
