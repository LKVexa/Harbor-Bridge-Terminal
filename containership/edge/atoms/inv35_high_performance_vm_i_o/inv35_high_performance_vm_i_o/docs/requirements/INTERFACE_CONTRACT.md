# Timeout, cancellation, retry, idempotency and backpressure contract (C025)

| Aspect | Contract |
|---|---|
| Timeout | Caller passes `deadline: Deadline`; checked before admission. Expired ⇒ E203 (retryable), nothing applied. INV-35 never blocks: there is no internal wait on the bulk path. |
| Cancellation | Caller passes `cancel: CancelToken`; checked before admission ⇒ E204 (terminal for that request). Once admitted a chain cannot be cancelled; it completes normally. |
| Idempotency | Optional `idempotency_key` scoped per tenant. A repeat returns the original result with `replayed: true`; survives restart via journal. Keys are evicted LRU after 4 096; callers MUST NOT reuse a key for a different request. |
| Retry | Only `retryable` outcomes may be retried, using `RetryPolicy` (full-jitter exponential, ≤ 4 attempts, ≤ 500 ms budget by default). Terminal outcomes MUST NOT be retried. |
| Backpressure | Three layers, all non-blocking refusals: queue depth (E200) → tenant quota/rate (E201) → circuit breaker (E202). The guest-facing effect is "ring not consumed yet"; the VMM re-polls. |
| Ordering | Completions release reservations FIFO per queue (matches virtio used-ring order in the reference model). |
