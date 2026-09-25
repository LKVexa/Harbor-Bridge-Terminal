# Dashboards and alerts

| ID | INV55-OPS-ALERTS | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: operations-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

Metrics emitted (`service.py`, `telemetry.py::Metrics`):

| Metric | Type | Labels |
|---|---|---|
| `inv55_requests_total` | counter | `op`, `outcome` |
| `inv55_denials_total` | counter | `reason` (unauthenticated, role_lacks_action, no_matching_rule, out_of_scope) |
| `inv55_request_seconds` | histogram (buckets 0.5 ms–2.5 s) | `op` |
| `inv55_audit_failures_total` | counter | — |
| `inv55_state_transitions_total` | counter | `to` |
| `inv55_resolutions_total` | counter | `outcome` (success, degraded) |
| `inv55_rotations_total` | counter | — |
| `inv55_lease_expiries_total` | counter | — |
| `inv55_internal_errors_total` | counter | `kind` (exception class name, ≤64 chars) |

Exposition is `Metrics.exposition()`; serving it over HTTP is the host's job (NOT IMPLEMENTED here). No gauges for state, circuit, in-flight — use `health()`.

## Alert rules (Prometheus)

```yaml
groups:
- name: inv55
  rules:
  - alert: Inv55AuditFailing
    expr: increase(inv55_audit_failures_total[5m]) > 0
    labels: {severity: page}
  - alert: Inv55ProviderErrors
    expr: sum(rate(inv55_requests_total{outcome="retryable"}[5m])) / clamp_min(sum(rate(inv55_requests_total[5m])), 1e-9) > 0.05
    for: 5m
    labels: {severity: page}
  - alert: Inv55DeniedSpike
    expr: sum(rate(inv55_denials_total[5m])) > 3 * sum(rate(inv55_denials_total[1h] offset 1d))
    for: 10m
    labels: {severity: ticket}
  - alert: Inv55UnauthenticatedSpike
    expr: rate(inv55_denials_total{reason="unauthenticated"}[5m]) > 1
    for: 10m
    labels: {severity: ticket}
  - alert: Inv55LatencyP99
    expr: histogram_quantile(0.99, sum by (le, op) (rate(inv55_request_seconds_bucket{op="resolve"}[5m]))) > 0.005
    for: 15m
    labels: {severity: ticket}
  - alert: Inv55QuarantinedOrFrozen
    expr: increase(inv55_state_transitions_total{to=~"quarantined|frozen"}[5m]) > 0
    labels: {severity: page}
  - alert: Inv55Degraded
    expr: increase(inv55_state_transitions_total{to="degraded"}[5m]) > 0
    labels: {severity: ticket}
  - alert: Inv55DegradedServing
    expr: increase(inv55_resolutions_total{outcome="degraded"}[5m]) > 0
    labels: {severity: ticket}
  - alert: Inv55InternalErrors
    expr: increase(inv55_internal_errors_total[5m]) > 0
    labels: {severity: ticket}
  - alert: Inv55NoRotations
    expr: increase(inv55_rotations_total[30d]) == 0
    labels: {severity: info}
```

Thresholds are proposed. Note `inv55_request_seconds` uses `time.perf_counter`, not the injected clock.

## Dashboard panels
Request rate by op/outcome; denials by reason; p50/p99 by op; audit failures; state transitions; resolutions success vs degraded; rotations; lease expiries. Plus a `health()` scrape for state, circuit, in-flight, leases_active.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | inv55_internal_errors_total |
