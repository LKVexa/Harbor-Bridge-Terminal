# INV-17 Diagnostic / High-Cardinality / Privacy Policy

**Controls:** C075 (cardinality/privacy guard), C076-C077 (decision explain surface), C073 (structured logging)
**Owner:** UNASSIGNED — owner to fill

## Rules implemented in code

| Rule | Code |
|---|---|
| Tenant and workload are replaced by `tenant_hash`/`workload_hash` (salted SHA-256, first 12 hex chars) | `observability::redact`, `pseudonymise` |
| Keys matching `token|secret|password|authorization|key` (case-insensitive) become `[REDACTED]` | `observability::redact` (`_SECRETish`) |
| `payload`, `element`, `value` fields are replaced by `[<type> omitted]` | `observability::redact` |
| Metric labels limited to `ALLOWED_LABELS`; series capped at `MAX_SERIES` | `MetricsExporter.samples` |
| Stable log schema `LOG_FIELDS` | `observability::LOG_FIELDS`, `StructuredLogger.log` |
| Explain output: last 50 decisions, each passed through `redact`; policy (disabled, frozen scopes, breaker, budget, default quota) and topology (instance-local, stream count) | `observability::explain` |
| Decision log bounded at 256 entries | `control::StreamRegistry._decide` |
| Status reasons truncated to 20 | `observability::status` |

## Caveats found in code

- `_SECRETish` matches substrings, so a field such as `monkey` or `keys` is also redacted (over-redaction, safe direction).
- `explain()` shows `frozen_scopes` as `tenant:<raw value>` — **raw, not pseudonymised** tenant/workload names; health `reasons` contain raw stream ids.
- Default salt is `"inv17"` unless `INV17_TELEMETRY_SALT` is set — PROPOSED requirement: set a secret per-deployment salt in production.
- `serve_status` exposes `/explain` without authentication; keep it on loopback.
- Audit events (`AuditLedger`) store raw tenant/principal values and are *not* redacted — treat audit export as confidential.

## Access (PROPOSED)

| Surface | Audience |
|---|---|
| `/metrics` | Monitoring system |
| `/healthz`, `/readyz`, `/version` | Orchestrator |
| `/explain`, logs | On-call operators |
| Audit export | Security team only |

Emergency debug mode (with expiry and audit) is **not implemented**.

Tests (planned): `tests/test_observability.py`.
