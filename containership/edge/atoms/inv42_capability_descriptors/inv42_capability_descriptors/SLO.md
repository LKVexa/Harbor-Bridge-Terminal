# SLOs, error budgets and support — INV-42 (MC-035)

| SLO | SLI (from `telemetry.Metrics`) | Objective | Budget / window | Alert |
|---|---|---|---|---|
| Table binding | foreign descriptors resolved (always 0 by construction); `foreign_descriptor` rejections are monitored for attack | 0 wrongful accepts | none | `INV42SecurityInvariant` pages immediately |
| Non-reuse | numbers reused | 0 | none | invariant test in CI |
| Type fidelity | wrong-type resolutions | 0 | none | invariant test in CI |
| Local availability | 1 − (internal_error + component_disabled + key_unavailable) / all ops | 99.99% | 4.3 min per 30 days | burn rates 14.4× over 1h and 6× over 6h (`alerts/inv42_alerts.yml`) |
| Latency | `inv42_operation_duration_seconds` p99 for resolve | ≤ 170 µs | 1% of 5-minute windows per 30 days | `INV42LatencyP99` |

Emergency-disable time is excluded from the availability budget only when it's recorded as a declared incident.

**Support commitment:** business hours, America/Los_Angeles. SEV1 and SEV2 page 24/7 once the on-call rotation is staffed (W-003). Until then, the accountable owner is the single escalation point.

**Budget policy:** while the availability budget is exhausted, only reliability and security changes may ship. When the budget has burned past 50%, a review entry is required in `REVIEWS.json`.
