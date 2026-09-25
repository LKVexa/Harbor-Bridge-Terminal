# Observability catalogue (MC-24) — reference

Allowed metric labels (cardinality control, enforced in `ops.Telemetry`): `code, level, result, site, op`. Node ids, nonces and challenge ids are **never** labels.

| Metric | Type | Labels | Emitted by |
|---|---|---|---|
| `gap06_challenges_total` | counter | op | `service.challenge` |
| `gap06_attest_total` | counter | result, code | `service.attest` (every outcome incl. replay) |
| `gap06_admission_rejected` | counter (field `Admission.rejected`) | — | `ratelimit` — not yet exported |
| `gap06_telemetry_dropped_series` | gauge (`Telemetry.dropped_series`) | — | not yet exported |

Structured logs: `Telemetry.log(event, trace_id=…, **fields)`, values redacted and truncated to 256 chars. Trace context: W3C `traceparent` via `ops.trace_context`.

## Proposed alerts (not deployed — no alerting platform)
| Alert | Condition | Severity | Runbook |
|---|---|---|---|
| ReplayAttempts | rate(`gap06_attest_total{code="E_REPLAY"}`) > 0 for 5m | SEV2 | RUNBOOKS.md › Replay-state storage pressure |
| MeasurementDriftSpike | reject ratio `E_MEASUREMENT_REJECTED` > 2× 1h baseline | SEV2 | RUNBOOKS.md › Policy publication / rollback |
| TimeUntrusted | any `E_TIME_UNTRUSTED` | SEV1 | RUNBOOKS.md › Time-integrity failure |
| LedgerTamper | `AuditLedger.verify` raises | SEV1 | RUNBOOKS.md › Audit verification |
