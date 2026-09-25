# INV-68 telemetry policy (MC-26, MC-28; C072–C080)

**Metrics** — catalog `ops/metrics.json` (name, type, unit, labels). RED: requests by
code, latency histogram; USE: in-flight, queue depth, shed count (status); contract
signals: hosts_used, unplaced, stranded cpu/mem; safety: mem_overcommit_hosts.
Cardinality: ≤ 200 series per metric, overflow folded into `{overflow="true"}` and
counted; `tenant` label only on three allow-listed metrics; label values redacted
and ≤ 64 chars.

**Logs** — one JSON object per line: `ts, level, component, event, correlation_id,
trace_id, span_id, tenant, fields`; `fields` redacted. Events: `pack.request`,
`pack.internal`. A bounded in-memory tail (500) supports support bundles.

**Traces** — W3C `traceparent` accepted and continued; responses return the child
`traceparent`. Exporters (OTLP) are a deployment adapter concern; IDs are already
propagated.

**Correlation** — every request gets a correlation id (caller-supplied or UUID4)
present in the response, error, log and audit record.

**Governance** — retention: metrics 30 d, logs 30 d, audit ledger ≥ 1 y (proposed;
service_owner/security_owner to confirm). Sampling: logs 100 % (volume bounded by
admission), traces head-sampled at the adapter. Privacy: workload names and lineage
are tenant data — never metric labels; exported only through redaction.
Export: Prometheus text (`Metrics.prometheus()`), JSON snapshot.

**Dashboards/alerts** — `dashboards/inv68-overview.json`, `ops/alerts.json` (9 rules
classifying load, degradation, policy rejection, dependency failure, attack, software
defect, safety, audit integrity). Every rule is validated against synthetic windows
on each run (evidence/ALERTS.json). Changes to alerts are versioned with the release.
