# Telemetry policy (items 46, 47)
* No object names, image refs, env values or annotation values as metric labels (cardinality + privacy); labels are limited to `reason`, `namespace`-class values.
* Logs are JSON, redacted by key (`token|secret|password|key|credential|authorization`); retention 30 days.
* Every log line and span inside a reconcile carries the trace id; the release version and config digest are exported on `/version` and `/configz` so incidents correlate to a release and a config activation.
* Release/infrastructure correlation: the release manifest digest is stamped into the Deployment annotation `inv67.linearfinance.org/release-manifest` by the release workflow.
