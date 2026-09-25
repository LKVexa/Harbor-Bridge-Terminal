# INV-18 observability specification (C071–C080)

## Status (C071) and explain view (C077)

`python -m inv18_completion_primitive status` prints `PK_FUTURE_STATUS/1`: version,
state, ready, reasons, config revision, contract versions, capabilities, dependency
state, limits, policy version, lineage, outstanding count, decision summary — never
payloads or tokens. `... explain` prints the operator view: health and *why*, active
config revision with author/approver/rollback source, limits, dependencies, rejection
counts by code, automated decisions, audit head, lineage, and advice per reason.

## Metrics (C072)

Declared in `telemetry.METRICS` (unit, kind, allowed labels); undeclared metrics raise.
Label values are capped at 32 per label (`other` beyond) — bounded cardinality.
Counters: created, values, errors, abandonments, cancellations, takes, double
resolutions, double takes, rejections{code}, limit hits{limit}, invariant violations,
telemetry dropped{sink}. Gauge: futures_open. Histograms: resolution and receive latency
(bounded reservoir of 4096).

## Logs (C073) and diagnostics (C075)

`PK_FUTURE_LOG/1` JSON: ts, severity, component, version, operation, code, future_id,
trace_id, span_id, config_revision, hashed tenant, redacted fields. Raw payloads are
never logged (`payload`/`value` fields are dropped); secrets are redacted by key and by
value pattern; rate limited per second (errors exempt). High-cardinality detail (future
ids, trace ids) is allowed; tenant ids are SHA-256-truncated; retention is the bounded
ring (`telemetry_queue_max`); privileged diagnostics require `diagnostics_privileged`.

## Traces (C074)

W3C `traceparent`. Incoming headers are validated; malformed or all-zero headers start a
new root (untrusted input cannot inject arbitrary metadata). Each governed future gets a
child span of the caller's context; adapters (INV-16 async_call, INV-20 http_trailers,
wire endpoint) propagate it. Tests assert trace-id continuity across layers.

## Automated decisions (C076)

`telemetry.DECISION_REASONS`: RESOLVE_REJECTED, TAKE_REJECTED, ABANDON_TRANSITION,
CANCEL_TRANSITION, COMPAT_REJECTED, AUTHN_REJECTED, AUTHZ_REJECTED, OVERLOAD_REJECTED,
DEGRADED_MODE, DISABLED_REJECTED, PRECEDENCE_APPLIED. Each record carries code, config
revision, policy version, correlation id and redacted input state.

## Lineage (C078)

`conformance/LINEAGE.json` (written by tools/gate.py): release id, version, source
digest, artifact digest, config revision used for certification, environment. Status and
explain expose it; audit `runtime.start` carries the config revision, so any event can be
walked back: event → config revision → release id → artifact digest → source digest.
No live infrastructure graph exists in this estate; the field `infrastructure_graph` is
reserved (null).

## Telemetry policy (C079) — version TP/1

| Data | Class | Retention | Sampling | Export |
|---|---|---|---|---|
| metrics | operational | host-defined; ring in process | 100 % | host scrape |
| traces | operational | host-defined | `trace_sampling` (0.1) | host exporter |
| logs | operational, may contain ids | ring `telemetry_queue_max` | rate-limited, errors exempt | host sink |
| audit events | security | ≥ 1 year recommended by host | 100 % | host sink, never sampled |
| payloads | confidential | never recorded | — | — |
Exporter outage: counted drops, DEGRADED status, core unaffected. Deletion: process exit
clears rings; exported data follows host policy. Tenant privacy: hashed tenant ids.

## Dashboards and alerts (C080)

`dashboards/inv18_dashboard.json` (panels) and `dashboards/inv18_alerts.json` (rules with
severity and runbook links). Alerts distinguish normal load (high created rate, no
rejections), degradation (soft limit, stalls), policy rejection (PERMISSION_DENIED,
DISABLED), dependency failure (DEPENDENCY_UNAVAILABLE, telemetry drops), suspected abuse
(UNAUTHENTICATED/REPLAY bursts, single-tenant quota hits) and invariant violation.
tests/test_observability.py evaluates every rule against synthetic metric snapshots.
