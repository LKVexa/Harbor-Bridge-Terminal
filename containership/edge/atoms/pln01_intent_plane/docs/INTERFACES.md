# Interfaces, limits, timeouts and error contract (MC-009, MC-012, MC-013)

| Interface | Schema file | Entry point | Capability |
|---|---|---|---|
| PK_DECLARATION/1 | schemas/pk_declaration_1.schema.json | `IntentPlaneService.submit`, `.transaction` | intent:declare / intent:retract / intent:transaction |
| PK_INTENT_GRAPH/1 | schemas/pk_intent_graph_1.schema.json | `.graph_view` | any authenticated principal |
| PK_RECONCILIATION_PLAN/1 | schemas/pk_reconciliation_plan_1.schema.json | `.plan` | intent:plan (tenant) / intent:admin (all) |
| PK_ACTUAL_STATE/1 | schemas/pk_actual_state_1.schema.json | `.report` | intent:report, reporter/service principals only |
| PK_ERROR/1 | schemas/pk_error_1.schema.json | every failure | — |
| PLN01_CONFIG/1 | schemas/pln01_config_1.schema.json | `config.build_config` | deploy pipeline |

Canonical fixtures (valid and invalid): `tests/fixtures/*.json`, all verified by `test_all_schemas_load_and_fixtures_validate`.
The validator (`validation.py`) refuses schema keywords it does not implement, so a schema cannot silently weaken.

## Timeouts, cancellation, retries, backpressure
* Every request runs under a `Deadline` (default 5 s, `timeouts.request_deadline_seconds`); queue wait counts against it.
* Callers may cancel via the deadline token → `PLN01-E0014`.
* Retries: only codes with `retryable: true`; full-jitter exponential backoff, bounded attempts (≤ 10) and never beyond
  the deadline (`controls.retry`). Mutations are safe to retry because `request_id` de-duplicates.
* Backpressure: bounded concurrency + bounded queue; overflow is shed immediately with `PLN01-E0012` (retryable).
* Circuit breaker for downstream calls (`controls.CircuitBreaker`) → `PLN01-E0015`.

## Error codes
See `schemas/error_codes.v1.json` (code, HTTP status, retryable, terminal). Messages are redacted and capped at 512 chars;
internal errors never echo exception text.
