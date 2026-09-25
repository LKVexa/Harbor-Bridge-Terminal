# INV-17 Operation Semantics: timeout, cancellation, retry, idempotency

**Controls:** C025 (checklist §9). Source: `stream::Stream.read_wait`, `write_wait`, `_wait`, `write`, `_remember`, `CancelToken`.

## 1. Blocking model

The core (`read`, `write`, `grant`, `end`) is **non-blocking**. Waiting is opt-in through two bounded operations:

| Operation | Waits until | Then |
|-----------|-------------|------|
| `read_wait(timeout=None, cancel=None)` | buffer non-empty, or `ended`, `writer_dropped`, `reader_dropped` | calls `read()` |
| `write_wait(element, timeout=None, cancel=None, *, idempotency_key=None)` | (`credit > 0` and buffer below `max_buffer`), or any terminal flag, or `frozen`, or key already seen | calls `write()` |

Because the final step is the ordinary non-blocking call, a wake-up caused by a terminal flag or freeze surfaces the normal error (`EndDropped`, `StreamClosed`, `StreamFrozen`). `read_wait` does **not** wake on freeze (reads are allowed while frozen).

## 2. Timeout

- `timeout` is `None` (unbounded) or a non-negative `int`/`float`; `bool` or negative raises `ValueError`.
- Deadline uses `time.monotonic()`; the condition variable is waited in slices of at most 50 ms, so timeout resolution is ~50 ms.
- Expiry raises `StreamTimeout` (`PK_STREAM_TIMEOUT`, also a `TimeoutError`). **A timeout never implies end-of-stream** and changes no state.
- `timeout=0` performs a single readiness check.

## 3. Cancellation

- `CancelToken.cancel(reason)` sets an `Event`; it is polled at each slice, so cancellation is observed within ~50 ms.
- Raises `StreamCancelled` with `details.reason`. No state is changed; a cancelled `write_wait` did not enqueue.
- A token may be shared across many waits; it is not resettable.

## 4. Retry and idempotency

- `write(..., idempotency_key=k)`: `k` must be a non-empty `str` (`ValueError` otherwise).
- On success the key is remembered in a per-stream FIFO of size `StreamConfig.idempotency_window` (default 1024); older keys are evicted.
- A repeat of a remembered key returns `False`, increments `duplicate_writes`, consumes no credit, and enqueues nothing — i.e. exactly-once **enqueue** within the window.
- Keys are remembered only on **accepted** writes; a write that failed (e.g. `CreditExhausted`) may be retried with the same key.
- Duplicate detection follows drop/ended/frozen and type checks, and precedes credit/buffer checks; a mistyped retry raises `ElementTypeMismatch` (see `spec/requirements.md` §2.1).
- The window is in-memory and per stream; it does not survive restart (see `spec/crash-semantics.md`) and is not shared across streams.

### Recommended client retry policy

| Error | Retry? | Guidance |
|-------|--------|----------|
| `StreamTimeout`, `CreditExhausted`, `BufferLimitExceeded` | Yes | reuse the same key; exponential backoff |
| `QuotaExceeded`, `LoadShed`, `CircuitOpen` | Yes | backoff with jitter; do not hot-loop |
| `StreamCancelled` | Caller decides | |
| `EndDropped`, `StreamClosed`, `ElementTypeMismatch`, `VersionUnsupported` | No | |
| `StreamFrozen`, `ComponentDisabled` | Not automatically | operator action required |

Backoff parameters are client policy; the package does not implement a retry loop.
