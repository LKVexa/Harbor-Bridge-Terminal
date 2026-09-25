# PLN-03 runtime semantics (MC-005, MC-006, MC-009, MC-010, MC-014)

## Outcome model (MC-005)
Every call ends in exactly one outcome class (`envelope.Outcome`); the code→class map is `envelope.CODES` and is append-only.

| Outcome | Meaning | Side effects | Client action |
|---|---|---|---|
| `success` | fully applied | committed | none |
| `degraded` | accepted into the bounded local buffer during partition (`PublishResult.outcome == "degraded"`) | durable locally, not yet at backend | none; reconciliation is automatic and idempotent |
| `retryable` | nothing applied | none | retry with the **same** idempotency key, honouring deadline and backoff |
| `terminal` | nothing applied | none | do not retry unchanged input |

Partial success is impossible by construction: `state_transact` validates every operation before writing and applies with a single swap; `publish` dedupes, persists and enqueues under one lock/journal record.

## Lifecycle (MC-006)
`created → starting → ready ⇄ degraded`; `ready|degraded → frozen → ready`; any serving state → `quarantined → draining → stopped`; `failed → starting`. Illegal transitions raise `PK_LIFECYCLE_REFUSED`. Reads are served in ready/degraded/frozen; writes only in ready/degraded. Every transition requires actor + reason and is audited.

## Timeouts, cancellation, retry, backpressure (MC-014)
- Deadline per call: `deadline_s` (default `Limits.default_deadline_s`, max `max_deadline_s`), propagated as absolute deadline; cancellation is cooperative (`Deadline.cancel`).
- Retry: only `retryable` codes; exponential backoff with full jitter, capped; stops at attempt limit, deadline, or empty retry budget.
- Backpressure: admission refuses with `PK_RATE_LIMITED` (global ceiling / rate) or `PK_QUOTA_EXCEEDED` (tenant share) **before** touching adapters; adjacent planes receive these as retryable envelopes with HTTP 429 / gRPC RESOURCE_EXHAUSTED, which is the cross-plane backpressure signal.
- Circuit breaker per adapter: opens after N consecutive retryable failures, half-opens after reset.

## Disconnected / intermittent networks (MC-009)
| Phase | Behaviour |
|---|---|
| Offline | publishes buffered if `degraded.allow_local_buffer`, else `PK_ADAPTER_UNAVAILABLE`; state reads served locally if the local adapter is up |
| Buffer full | `PK_READ_ONLY` for new writes; nothing dropped |
| Reconnect | `reconcile()` replays FIFO with original idempotency keys; pre-partition duplicates are suppressed |
| Reconciliation conflicts | state: last-writer-wins guarded by fencing epoch; messages: idempotency key |

## Constraint precedence (MC-010)
`security > residency > data-integrity > SLO > cost` (`config.CONSTRAINT_PRECEDENCE`). Enforced in code: tokens cannot be disabled by config; adapter residency outside site zones fails validation; failover filters residency before consistency before latency.

## Error-code registry (MC-015)
Generated from `envelope.CODES`; append-only within a major.

| Code | Outcome | HTTP | gRPC |
|---|---|---|---|
| `PK_OK` | success | 200 | OK |
| `PK_DEGRADED_BUFFERED` | degraded | 202 | OK |
| `PK_RUNTIME_ERROR` | terminal | 500 | INTERNAL |
| `PK_CAPABILITY_DENIED` | terminal | 403 | PERMISSION_DENIED |
| `PK_TOKEN_INVALID` | terminal | 401 | UNAUTHENTICATED |
| `PK_TOKEN_EXPIRED` | terminal | 401 | UNAUTHENTICATED |
| `PK_SECURITY_DEPENDENCY_UNAVAILABLE` | retryable | 503 | UNAVAILABLE |
| `PK_ADAPTER_UNAVAILABLE` | retryable | 503 | UNAVAILABLE |
| `PK_INVALID_ARGUMENT` | terminal | 400 | INVALID_ARGUMENT |
| `PK_PAYLOAD_TOO_LARGE` | terminal | 413 | INVALID_ARGUMENT |
| `PK_SECRET_NOT_FOUND` | terminal | 404 | NOT_FOUND |
| `PK_INVOKE_TARGET_UNAVAILABLE` | retryable | 503 | UNAVAILABLE |
| `PK_DEADLINE_EXCEEDED` | retryable | 504 | DEADLINE_EXCEEDED |
| `PK_CANCELLED` | terminal | 499 | CANCELLED |
| `PK_RATE_LIMITED` | retryable | 429 | RESOURCE_EXHAUSTED |
| `PK_QUOTA_EXCEEDED` | retryable | 429 | RESOURCE_EXHAUSTED |
| `PK_CIRCUIT_OPEN` | retryable | 503 | UNAVAILABLE |
| `PK_LIFECYCLE_REFUSED` | retryable | 503 | UNAVAILABLE |
| `PK_QUARANTINED` | terminal | 403 | FAILED_PRECONDITION |
| `PK_FENCED` | terminal | 409 | ABORTED |
| `PK_VERSION_UNSUPPORTED` | terminal | 505 | UNIMPLEMENTED |
| `PK_CONFIG_INVALID` | terminal | 422 | FAILED_PRECONDITION |
| `PK_READ_ONLY` | retryable | 503 | UNAVAILABLE |
| `PK_RESIDENCY_VIOLATION` | terminal | 451 | FAILED_PRECONDITION |
