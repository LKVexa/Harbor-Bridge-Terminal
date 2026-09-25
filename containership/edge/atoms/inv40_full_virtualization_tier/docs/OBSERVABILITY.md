# Observability (INV-40-C071..C080)

* **Health/readiness/version/config/dependencies/capabilities:** `FullVmService.health()` (C071).
* **Metrics** (C072): `ops_total{op,result}`, `op_latency_ms` histogram, `boot_ms{status}`, `resident_mib{guest}`, `full_vm_instances{state}`, `primitive_refusals`, `authz_denials{op,code}`, `retries{code}`, `invalid_requests`, plus admission gauges in health.
* **Logs** (C073): JSON lines — ts, level, node, component, operation, tenant (hashed), workload, trace_id, msg; secret-looking keys redacted.
* **Trace** (C074): W3C `traceparent` accepted on create/boot/stop/destroy; child span per op recorded in log and audit. Propagation *into* QEMU is not applicable (no trace-aware peer).
* **High-cardinality safety** (C075): tenant ids hashed; series capped at 2000 with `dropped_series` counter.
* **Decision reasons** (C076) and **explain view** (C077): `Decisions.record/explain` for authz denials, image refusals, primitive refusals, degraded boots, quarantine.
* **Release lineage** (C078): health reports package version and config digest; correlation with an application release graph / live infra graph is **not implemented** (no such service in repo).
* **Retention / sampling / privacy / export** (C079): `log_retention_days` (default 30), `trace_sample_ratio` (0.1), `telemetry_export` none|stdout|otlp — **OTLP exporter not implemented**; retention is a declared policy, enforcement belongs to the collector (PARTIAL).
* **Dashboards & alerts** (C080): `ops/alerts.json`, `ops/dashboard.json` distinguish load, degradation, policy rejection, dependency failure, attack indicators, defects. Not deployed to any monitoring system (PROD-ENV).
