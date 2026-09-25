# Request lifecycle state machine (aio.py)

| From | Legal targets |
|---|---|
| ACCEPTED | DISPATCHED, CANCELLED, FAILED |
| DISPATCHED | HEAD_SENT, CANCELLED, FAILED |
| HEAD_SENT | BODY_STREAMING, TRAILERS_DONE, CANCELLED, FAILED |
| BODY_STREAMING | TRAILERS_DONE, CANCELLED, FAILED |
| TRAILERS_DONE / CANCELLED / FAILED | RELEASED |
| RELEASED | — |

Any other transition raises `E_ILLEGAL_STATE`.

**Invariants.** One head per response (`ResponseOutparam.set`); trailers resolve once; after
CANCELLED/FAILED no body write, head or trailer is accepted; `release()` is idempotent and runs every
registered releaser (handler task cancel, admission slot, stream abort, live-set removal).

**Trap / disconnect behaviour.**
- Trap before head → `E_HANDLER_TRAP` returned to caller; nothing was committed.
- Trap after head → body stream aborted with `E_HANDLER_TRAP`, trailers future fails; the partial
  response is *not* retried (`RetryPolicy.classify(head_committed=True)` is always False).
- Peer disconnect at any stage → `release()` → CANCELLED, handler task cancelled.

**Cancellation precedence.** The *first* terminal cause wins (`Lifecycle.fail` ignores later causes).
If timeout, client disconnect and upstream error race, whichever the event loop observes first is
recorded; all three produce the same externally visible effect (terminated, resources released), and
the recorded code is used for metrics.

**Retry classes.** Safe-to-retry codes: `E_DNS_FAILURE`, `E_UPSTREAM_CONNECT`, `E_CIRCUIT_OPEN`,
`E_OVERLOADED`. Idempotent methods (GET/HEAD/PUT/DELETE/OPTIONS/TRACE) or requests carrying an
idempotency key may retry those; non-idempotent requests retry only `E_UPSTREAM_CONNECT` (peer never
reached). Attempts ≤ `max_attempts`, cumulative ≤ `budget_ms`, equal-jitter exponential backoff capped
at `max_backoff_ms`, `Retry-After` honoured up to `retry_after_cap_ms`, never past the deadline.
Idempotency-key replay storage is **not** provided in 4.3.0 (keys only affect retry eligibility).

**Backpressure.** Per stream ≤ `stream_chunks_in_flight` chunks and ≤ `body_bytes`; admission bounds
global/tenant/workload concurrency and queue depth; a tenant at its cap is shed immediately
(`E_OVERLOADED`, reason `tenant_limit`) so it cannot occupy shared queue slots.
