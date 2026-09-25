# GAP-11 dashboards (GAP11-P1-28 .08) — specification, not deployed

Built around operator decisions, one panel group per question:

1. **Can tenants get accelerators?** allocation success ratio by refusal class (`refusal_class()`), p50/p99 `request_latency`, queue depth, quota refusals.
2. **Is lease safety intact?** STALE_FENCE count (must be 0 outside failover windows), leader epoch over time, IDEMPOTENCY_CONFLICT, REPLAY_DETECTED.
3. **Is scrub healthy?** scrub outcomes by code, quarantined device count and age, SCRUB_OUTCOME_UNKNOWN.
4. **Is reconciliation keeping up?** reconcile lag, SUSPECT leases, reclaimed per hour.
5. **Are dependencies up?** readiness, identity/policy/store/KMS status.
6. **Capacity:** free vs unusable GB (`fragmentation()`), per-kind utilisation.

Each alert in `ALERT_RULES` links to the panel group and runbook it belongs to. Deployment needs GAP-09 (BLK-ENV).
