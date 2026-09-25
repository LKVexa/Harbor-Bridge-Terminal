# INV-17 Failure Semantics

**Controls:** C015, C048, C054, C059 (checklist §4, §23, §27, §30).

All failures are raised as `stream::StreamError` subclasses with a stable `code` and `details` (`as_dict()`). No failure is signalled by a sentinel except `NOT_READY` (not-yet-ready, not a failure).

## 1. Error catalogue

| Code | Class (module) | Raised when | Retryable? | Caller action |
|------|----------------|-------------|------------|---------------|
| PK_STREAM_CREDIT_EXHAUSTED | `CreditExhausted` (stream) | write with credit 0 | Yes, after grant | wait (`write_wait`) or yield to scheduler |
| PK_STREAM_CREDIT_LIMIT | `CreditLimitExceeded` (stream) | grant over `max_credit` | Yes, smaller grant | reduce grant |
| PK_STREAM_BUFFER_LIMIT | `BufferLimitExceeded` (stream) | buffer at `max_buffer` | Yes, after reads | back off |
| PK_STREAM_END_DROPPED | `EndDropped` (stream) | peer or self end dropped | No | tear down; `details.end` says which |
| PK_STREAM_CLOSED | `StreamClosed` (stream) | write/grant after end | No | stop |
| PK_STREAM_TYPE_MISMATCH | `ElementTypeMismatch` (stream) | wrong element type | No | fix caller |
| PK_STREAM_TIMEOUT | `StreamTimeout` (stream) | bounded wait elapsed | Yes | retry with same idempotency key |
| PK_STREAM_CANCELLED | `StreamCancelled` (stream) | CancelToken set | Caller's choice | – |
| PK_STREAM_FROZEN | `StreamFrozen` (stream) | stream quarantined | After release | escalate / wait |
| PK_STREAM_QUOTA | `QuotaExceeded` (control) | tenant stream/buffer quota | Yes, after drain | back off |
| PK_STREAM_LOAD_SHED | `LoadShed` (control) | instance buffer budget exhausted | Yes, with backoff | back off (breaker records failure) |
| PK_STREAM_CIRCUIT_OPEN | `CircuitOpen` (control) | admission breaker open on `open` | Yes, after cooldown | back off |
| PK_STREAM_DISABLED | `ComponentDisabled` (control) | emergency disable or scope quarantine | No until enabled | escalate |
| PK_STREAM_NOT_FOUND | `StreamNotFound` (control) | unknown id (incl. after restart) | Reopen | reopen, see crash-semantics |
| PK_STREAM_VERSION_UNSUPPORTED | `VersionUnsupported` (control) | no common version | No | upgrade peer |
| (AuthError codes) | `AuthError`, `TokenReplay`, `AuthzDenied` (security) | bad/expired/revoked/replayed token, wrong binding/right | New token | re-issue capability |
| (trust) | `TrustServiceUnavailable` (security) | `KeyRing.available` or `TrustedClock.available` false | Yes, after recovery | fail closed |
| – | `ConfigInvalid`, `ActivationFailed` (configuration) | invalid config / failed probe | Fix config | see runbook |

Exact codes of the security classes are defined in `security.py`; `TokenReplay` uses `PK_STREAM_TOKEN_REPLAY`.

## 2. Fail-closed principles (implemented)

- **Ceilings fail closed**: credit and buffer ceilings raise rather than grow (`Stream.grant`, `Stream.write`).
- **Trust outage fails closed**: `CapabilityAuthority.verify` calls `KeyRing.get` and `TrustedClock.now`; either raising `TrustServiceUnavailable` denies the operation, and `StreamRegistry._authorize` records `trust.unavailable` in the audit ledger. There is no cached-allow path.
- **Overload sheds**: `StreamRegistry.write` raises `LoadShed` when `buffered_total() >= global_buffer_budget` and calls `CircuitBreaker.failure()`; after `threshold` (default 5) consecutive failures the breaker opens and new `open` calls get `CircuitOpen` until `cooldown` (default 5 s) elapses, then `half_open` admits; one failure in `half_open` reopens it. Note: the breaker gates `open` only; `write` is gated by the budget check itself.
- **Drops are visible**: truncation (`writer_dropped`) is never reported as EOF.

## 3. Partial failure

A failed operation leaves stream state unchanged except for the counters it documents (`credit_stalls` on `CreditExhausted`, `duplicate_writes` on duplicate key). There are no multi-stream transactions.
