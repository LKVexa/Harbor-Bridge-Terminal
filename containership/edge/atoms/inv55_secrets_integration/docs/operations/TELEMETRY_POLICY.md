# Telemetry retention, sampling, privacy and export (checklist #79, DRAFT)

* Metrics: labels limited to op/tenant/outcome/reason; never secret names or subjects; retained 13 months at 5-min resolution (platform).
* Logs: JSON, scrubbed; warn+ always kept, debug sampled at `sample_debug` (default 0); retained 30 days; no values ever.
* Traces: 1 % head sampling in production, 100 % for errors; spans carry op and outcome only; retained 7 days.
* Audit: not sampled; retained ≥ 1 year (or tenant contract), append-only, head exported with every release and daily.
* Export: Prometheus text (`Metrics.prometheus`), JSON lines, W3C traceparent. Shipping pipelines are platform components and are not present here (W-008).
