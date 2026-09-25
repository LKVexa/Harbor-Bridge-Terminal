# Observability and explainability (C072–C080)

| Signal | Implementation | Notes |
|---|---|---|
| Metrics | `telemetry.Metrics`: `runs{status}`, `terminations{reason}`, `fuel_used`, `latency_us{phase}`, `idempotent_replays` | Allow-listed labels, 64-char values, 5,000-series cap with a drop counter, Prometheus text exposition |
| Logs | `telemetry.StructuredLog` JSON lines | Every record has `ts, level, event, run_id, trace_id, component, version`; secrets and payloads are redacted |
| Traces | `telemetry.TraceContext` (W3C traceparent) | Malformed or zero IDs start a new trace; the trace id is carried into logs and the explain view |
| Diagnostics | `telemetry.DiagnosticChannel` | Opt-in per tenant with TTL ≤ 1 h, rate cap, pseudonymous tenant, redacted |
| Explain | `Sandbox.explain(run_id)` | State path, reason code and class, notes (dropped capabilities, disabled host calls, module digest), mode, config digest, release lineage, next step |
| Lineage | `service.RELEASE_LINEAGE` + config digest on every audit and explain record | Set `INV70_SOURCE_REVISION` at build time |
| Policy | `telemetry.TELEMETRY_POLICY` | Retention, sampling, privacy, export |
| Alerts / dashboard | `ops/alerts.yaml`, `ops/dashboard.json` | Keyed on the reason-code classes |

Reason-code classes: `guest, request, security, config, host, timeout, caller, capacity, degraded, dependency, infrastructure`. The full list is in `service.REASON_CODES`.
