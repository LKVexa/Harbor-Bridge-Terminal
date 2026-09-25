# Failure semantics  (C014 · component 05)

Machine-readable form: `errors.py` (`Outcome`, registry) and `schemas/error.schema.json` (generated, drift-checked).

| Outcome | Meaning | Caller action | Side effects |
|---|---|---|---|
| `success` | every mandatory effect happened | none | complete |
| `partial` | some effects happened; `Result.delivered`/`failed` enumerate them | reconcile listed failures | enumerated |
| `degraded` | succeeded under a declared degraded mode (`Result.mode`) | tolerate; alert if prolonged | complete within mode |
| `retryable` | nothing durable happened | retry with same idempotency key, bounded backoff | none |
| `terminal` | will not succeed unchanged | fix input/permissions/state | none |

Rules: (1) a code's outcome class never changes; (2) new codes are append-only; (3) provider adapters MUST translate every native error (conformance check `error_translation`); (4) error details are secret-redacted by construction.
