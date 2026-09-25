# INV-41 observability

* **Health** `Broker.health()` → `INV41_HEALTH/1`: live, ready, state, quarantined, status_code (200/503), version, config digest, lineage (release, source revision, config digest, instance), dependency status, self-check, degraded reason. No secrets or policy contents.
* **Metrics** (`telemetry.py`, version `INV41_METRICS/1`): counters `inv41_{grants,binds,attenuations,wraps,revocations,uses_allowed,uses_denied,invalid_references,cross_authority,auth_failures,overload_rejections}_total`; histograms `inv41_operation_latency_seconds`, `inv41_dependency_latency_seconds` (buckets 1 µs–1 s); gauges `inv41_active_authorities`, `inv41_in_flight_checks`, `inv41_degraded_dependencies`, `inv41_queue_depth`. Labels limited to `op`, `outcome`, `code` with fixed domains; series cap 512.
* **Logs** `INV41_LOG/1` JSON lines: ts, severity, component, version, operation, outcome, reason, correlation_id + redacted fields. Successes sampled 1/N; failures never.
* **Traces** W3C `traceparent` parse/propagate; spans `inv41.<op>`; trace context never participates in authorization.
* **Reason ledger** `INV41_REASON/1` for every broker decision; `Broker.explain(correlation_id)` is the read-only historical explain view (distinct from current state).
* **Lineage** release, source revision, config digest, instance id in every reason record and health output.
* **Alerts/dashboards** `ops/alerts.json` (10 alerts with owner + runbook anchor, DASH-01). Not wired to a backend (B-DEPLOY-01).
* **Policy**: docs/OPERATIONS.md §Telemetry policy.
