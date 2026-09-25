# Telemetry retention, sampling, privacy, export  (component 80)
- Payload bodies are never logged or traced; only sizes, keys' partitions and outcomes.
- Secret-named fields are redacted at the logger, error and decision layers.
- Trace sampling: `telemetry.trace_sample_ratio` (default 0.1; dev 1.0).
- Retention: in-process buffers are bounded (logs 10k, decisions 10k, histogram reservoir 2048). Backend retention (PROPOSED): metrics 30 d, logs 14 d, audit chain ≥ 1 y with externally retained heads.
- Tenant identifiers are permitted labels; consumer/subscriber names are capped by `max_label_values`.
- Export: Prometheus text exposition; JSON-lines logs to stdout/sink. No telemetry leaves the process except via the configured sink.
