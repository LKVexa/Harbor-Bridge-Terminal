# Outcome and failure semantics

| ID | INV55-ARCH-OUTCOME | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Source of truth: `errors.py::Outcome`, `errors.py::ErrorCode`, `errors.py::Inv55Error.to_wire`.

## Outcomes

| Outcome | Meaning | Caller MUST |
|---|---|---|
| `success` | Operation completed. | — |
| `degraded` | Served from cache while provider unavailable (`service.py::SecretsService.resolve`, only when `stale_grace_s > 0`). | Treat the value as possibly stale. |
| `retryable` | Transient; `retry_after_ms` given. | Retry with backoff no earlier than `retry_after_ms`. |
| `terminal` | Retrying the same request cannot succeed. | Change the request (e.g. resolve again) or stop. |
| `denied` | Security decision. | MUST NOT retry automatically. |

There is no `partial` outcome: every operation is all-or-nothing from the caller's view. Note `revoke` marks the local lease revoked before the optional provider revoke; if the provider call then fails the response is an error even though the local revocation took effect (fail-closed direction).

## Wire form

`{"protocol":"PK_SECRET_ERROR/1","code","outcome","http_status","message",["retry_after_ms"],["request_id"]}`. `message` is fixed text from the spec, never caller- or secret-derived. Responses on success carry `"ok": true` and `"outcome"`.

## Error codes

| ErrorCode | Code | Outcome | HTTP | retry_after_ms | Raised by |
|---|---|---|---|---|---|
| DENIED | INV55-E001-DENIED | denied | 403 | — | `_guard` (policy), resolve out-of-scope, provider NotFound/Denied (`_provider_call`), non-operator freeze |
| UNAUTHENTICATED | INV55-E002-UNAUTHENTICATED | denied | 401 | — | `HmacJwtAuthenticator.authenticate` |
| LEASE_EXPIRED | INV55-E003-LEASE-EXPIRED | terminal | 410 | — | `use` |
| LEASE_REVOKED | INV55-E004-LEASE-REVOKED | terminal | 410 | — | `use` |
| CONTEXT_MISMATCH | INV55-E005-CONTEXT-MISMATCH | denied | 403 | — | `use`, `revoke` (both audited) |
| VERSION_RETIRED | INV55-E006-VERSION-RETIRED | terminal | 410 | — | `resolve`, `use` |
| INVALID_REFERENCE | INV55-E007-INVALID-REFERENCE | terminal | 400 | — | `_ident`, bad TTL/version/idempotency key, non-dict request (`_run`) |
| CLOCK_ROLLBACK | INV55-E008-CLOCK-ROLLBACK | terminal | 500 | — | `_now` |
| PROVIDER_UNAVAILABLE | INV55-E009-PROVIDER-UNAVAILABLE | retryable | 503 | 1000 | `_provider_call` (unavailable, circuit open, other ProviderError) |
| OVERLOADED | INV55-E010-OVERLOADED | retryable | 429 | 250 | `AdmissionController.admit` (in-flight cap, key table full), lease table full |
| QUOTA_EXCEEDED | INV55-E011-QUOTA-EXCEEDED | retryable | 429 | 1000 | token buckets, `max_leases_per_subject` |
| DEADLINE_EXCEEDED | INV55-E012-DEADLINE-EXCEEDED | retryable | 504 | 100 | `Deadline.check`, `RetryPolicy.run` |
| FROZEN | INV55-E013-FROZEN | denied | 503 | — | `_guard` in STARTING/FROZEN/QUARANTINED/DRAINING/STOPPED |
| AUDIT_UNAVAILABLE | INV55-E014-AUDIT-UNAVAILABLE | retryable | 503 | 1000 | `_audit` on `OSError` |
| UNSUPPORTED_VERSION | INV55-E015-UNSUPPORTED-VERSION | terminal | 400 | — | `negotiate` (unknown version or protocol family not matching the operation) |
| LIMIT_EXCEEDED | INV55-E016-LIMIT-EXCEEDED | terminal | 413 | — | `set_scope` apps count, `rotate` value size |
| CAPACITY_EXHAUSTED | INV55-E017-CAPACITY | retryable | 507 | 5000 | Defined; NOT raised anywhere in 4.3.0 |
| CONFLICT | INV55-E019-CONFLICT | terminal | 409 | — | `rotate` when `expected_version` CAS fails (`ProviderConflict`), or idempotency key reused with a different value |
| CANCELLED | INV55-E018-CANCELLED | terminal | 499 | — | `Deadline.check` when `cancelled` set (no public API sets it in 4.3.0) |
| INTERNAL | INV55-E999-INTERNAL | terminal | 500 | — | `_run`: any unexpected exception in a public op (exception text never leaked; counted in `inv55_internal_errors_total{kind}`) |

Every public operation returns a structured response: `Inv55Error` → its code; any other exception → INTERNAL (`_run`). Evidence: `tests/test_resilience.py::FaultInjection.test_unexpected_exception_fails_closed`, `tests/test_property_fuzz.py::Fuzz.test_public_api_never_raises_and_never_leaks`, `tests/test_service_contract.py::RotateContract.test_cas_conflict`. Completeness of this table is enforced by `tests/test_schemas_fixtures.py::Schemas.test_every_error_code_documented`.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | CONFLICT on idempotency payload mismatch |
| 4.3.0 | 2026-09-22 | Added E019-CONFLICT; INTERNAL fail-closed; non-dict requests; protocol-family check |
