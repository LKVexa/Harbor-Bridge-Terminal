# Outcome and failure semantics (C014, C026)

The machine-readable taxonomy is `schemas/errors.json` (`inv53.errors/1`), generated from `errors.py`.

| Kind | Meaning | Caller action |
|---|---|---|
| success | Applied. `OK_EMPTY` = nothing visible. | continue |
| duplicate | `OK_DUPLICATE`: identical request already applied; no new effect | continue |
| degraded | Accepted under a declared degraded mode | continue, alert |
| retryable | `E_STORAGE`, `E_INTERNAL`: outcome may be indeterminate (storage) — retry *idempotently* with backoff | retry with full-jitter backoff |
| refused | Capacity, quota, shed, breaker, frozen, draining, security-dependency outage — **nothing changed** | retry after `retry_after` or when the condition clears; `E_FROZEN` needs an operator |
| terminal | Validation, version, authn, authz, stale lease, epoch fenced, corrupt | do not retry the same request |

Partial success does not exist at the operation level: every operation is one journal record (or, for
expiry, a sequence of independent single-message records each of which is atomic).

Dead-letter reasons: `visibility_timeout` (attempts exhausted by expiry), or the caller's `nack` reason.
Capacity refusal is always evaluated *before* the source state is modified.
