# Telemetry retention, privacy and export (M18)

| Signal | Contains | Never contains | Classification | Retention (proposed) |
|---|---|---|---|---|
| Metrics | interface, outcome, (tenant — opt-in) | request ids, arguments, peers | internal | 13 months aggregated |
| Logs | tenant, peer id, interface, function, outcome, duration | arguments, results, keys (key-name redaction) | confidential | 30 days |
| Traces | trace/span ids, interface, function, status | arguments; any attr whose key looks secret | confidential | 7 days, sampled (`trace_sample_ratio`) |
| Audit | authn/authz decisions, record rejects | arguments, keys | restricted | 1 year, off-host head |

Minimisation is enforced in code: label allow-list and series cap (`Metrics`), key-based
redaction (`JsonLogger`, `Tracer`), arguments never logged. Tenant isolation: tenant is a
label only when enabled; exports go to the operator's own collector — no third-party export
is built in. Deletion on request: logs/traces by tenant via the collector; audit records are
retained under the audit policy. Retention numbers are **proposals** pending an owner.

## Sampling trust boundary (open decision)
The node honours an incoming W3C `sampled=01` flag, so any authenticated caller can force its
own calls to be traced. Volume is bounded by per-tenant admission, but the decision to trust
caller sampling (vs. re-sampling locally) belongs to the owner. Recorded as T-16.
