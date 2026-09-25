# Operations — PLN-06 data plane (4.3.0)

Runbooks moved to `docs/RUNBOOKS.md` (day-0 bootstrap, day-1 canary/staged rollout, day-2 controls, dependency outages, backup/restore, incident severities and escalation).

## Transfer lifecycle

`admitted → in_flight → completed | failed | quarantined | cancelled | expired` (also `admitted → failed | cancelled | expired`). Every transition is written to the fsync'd journal before it takes effect. On restart, non-terminal transfers are reconciled to `expired` and a `restore` audit event is written. Outcome meaning and caller action: `lifecycle.OUTCOMES`; degraded behaviour per lost dependency: `lifecycle.DEGRADED_MODES`.

## Configuration lifecycle

Declarative JSON (`config/base.json` + `config/overlays/*.json`) validated against `PK_DATA_PLANE_CONFIG/1`; security switches cannot be disabled outside `dev`. `ConfigController` keeps durable history, requires an independent approver, supports canary with auto-rollback, operator rollback to any prior revision, and emergency disable.

## Health, metrics, logs, traces

`GovernedDataPlane.health()` → `PK_DATA_PLANE_HEALTH/2` with dependency status; `metrics_text()` → Prometheus exposition; logs `PK_LOG/1`; W3C trace context. Alerts and dashboard: `ops/`. Retention/sampling/privacy: `docs/TELEMETRY_GOVERNANCE.md`.

## Failure handling

Failure catalog with detection/recovery/RTO: `resilience.FAILURE_MODEL`. Retries only for retryable errors under `RetryPolicy`; residency-safe failover when candidates are configured; stalled transfers reaped by `reap_stalled()`.
