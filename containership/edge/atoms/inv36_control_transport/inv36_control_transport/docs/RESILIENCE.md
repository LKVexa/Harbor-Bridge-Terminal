# Health, backpressure and failure control (MC-09)

Implementation: `health.py`; wiring in `endpoint.py`.

## Health

States: `ready`, `degraded`, `not_ready`; liveness is separate (`live`). Report schema: `schema/health.schema.json` (reason codes such as `required_dependency_down:<name>`, `optional_dependency_down:<name>`, `stalled`, `queue_saturated`, `error_rate_high`).

- Required dependencies (identity/attestation, key service, policy, integrity) -> immediate `not_ready`.
- Optional dependencies (telemetry, config service) -> `degraded` after hysteresis.
- Stall: no progress for `stall_threshold_ms` (monotonic clock) -> `stalled`.
- Hysteresis: `hysteresis` consecutive evaluations before any non-critical transition; transitions are reported via callback (metrics/logs/audit).

## Retries and timeouts

| Operation | Class | Default timeout |
|---|---|---|
| connect, handshake, HEARTBEAT, STATUS_QUERY | idempotent | 2 s / 5 s |
| LEASE_*, PLACEMENT, DRAIN | retry only with the same op_id (dedup token) | write 10 s |
| ERROR_REPORT | non-retryable | - |

`RetryPolicy`: full (default) or decorrelated jitter, max attempts, per-call deadline, caller cancellation, `retry_after_s` honoured, and never retries codes whose `retryable` is false (authentication, authorization, protocol, integrity). `RetryBudget` is shared across sessions so a fleet-wide outage cannot turn into a retry storm.

## Backpressure and overload

`AdmissionController` runs after authentication and authorization: HWM/LWM hysteresis, per-tenant quota, priority classes (CRITICAL: LEASE_REVOKE, DRAIN, PLACEMENT; NORMAL: LEASE_GRANT/RENEW, ERROR_REPORT; OPTIONAL: STATUS_QUERY, HEARTBEAT). Optional traffic is shed first; CRITICAL is admitted up to HWM+16 (absolute bound). Rejections are `OVERLOADED` with `retry_after_s`. Session limits per process and per tenant are enforced at handshake (`CONNECTION_LIMIT`); the vsock listener bounds backlog, concurrent connections and per-CID churn.

## Circuit breaking

`CircuitBreaker` wraps dependency calls: closed -> open after `breaker_failure_threshold` failures -> half-open after `breaker_reset_ms` with bounded probes -> closed on success.

## Failover and degraded mode

`FailoverSelector` only chooses alternates in the same residency region that serve the tenant; ownership uses a monotonically increasing fencing token so a stale owner is rejected (no dual-active). Degraded-mode behaviour per dependency is in `health.DEGRADED_MODE`:

| Dependency down | Behaviour |
|---|---|
| telemetry exporter | continue; bounded buffer, drops counted |
| config service | keep last known-good snapshot; refuse activations |
| policy service | cached policy until `expires_at`, then deny all |
| identity / attestation / revocation / time | existing sessions until max age; new handshakes fail closed |
| key service | no new signatures; existing sessions until max age |
| audit sink | buffer non-critical events; security-critical actions fail closed |

Re-entry: `hysteresis` healthy evaluations; reconnects use jittered backoff.

Tests: `tests/test_resilience_recovery.py`, `tests/test_endpoint_integration.py::DisasterPartitionTest`.
