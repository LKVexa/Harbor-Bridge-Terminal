# Telemetry retention and sampling
- Metric labels are restricted to `[A-Za-z0-9_.:-]{1,64}` and to bounded domains (instance, scope, reason enum, ack enum); series capped at 4096 with a dropped-series counter.
- Events: fixed schema (`telemetry.EVENT_FIELDS`), ring of 10,000; non-security events sampled at `event_sample_rate`; security events never sampled.
- Histograms: fixed log2 buckets + a 4,096-sample window for quantiles.
- Audit: hash-chained, capacity 100,000, overflow counted and reported by `verify()`.
- Export: Prometheus text via `Metrics.render_prometheus()`. No exporter process, retention store or privacy review exists in this archive.
