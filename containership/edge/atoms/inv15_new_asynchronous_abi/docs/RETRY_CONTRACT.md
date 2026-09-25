# Retry contract
Retry is **caller/host policy**, never performed by the ABI. The ABI supplies:
- `retryable` flag in every error envelope (NOT_READY, BUDGET_EXHAUSTED, WAIT_TIMEOUT, MEMORY_EXHAUSTED, DRAINING).
- `idempotency_key` (1–128 chars, per instance): a duplicate call while the first is live returns the **same handle** (no new work); after retirement the key answers HANDLE_CONSUMED with the recorded terminal state for a bounded window (`Limits.idempotency_window`). Outside the window the key is forgotten and a retry creates new work — callers needing longer guarantees must keep their own ledger.
- Late completions after cancel/teardown are discarded and their payloads released (`discarded_late`).
Tests: `TestIdempotency`.
