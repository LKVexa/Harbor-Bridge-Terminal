# ADR-0001: Credit-based, non-blocking stream primitive

**Controls:** C010 (checklist §2). **Status:** Proposed — awaiting approval. **Decider(s):** UNASSIGNED — owner to fill. **Date proposed:** 2026-09-23.

## Context

INV-17 must move typed elements between a writer and reader under bounded memory, with explicit end-of-stream, detectable peer loss, multi-tenant operation and no third-party dependencies.

## Decision (as implemented in `stream.py` / `control.py`)

1. **Credit-based flow control.** Reader grants credit (`Stream.grant`); each accepted write consumes one unit. Backpressure is explicit, not queue-length based.
2. **Non-blocking core, bounded waits at the edge.** `read`/`write`/`grant`/`end` never block; `CreditExhausted` / `NOT_READY` return control to the scheduler. Opt-in `read_wait`/`write_wait` add timeout and `CancelToken`.
3. **`collections.deque` buffer**, O(1) append/popleft, FIFO.
4. **Per-stream `threading.RLock` + `Condition`** for serialization and wake-ups; reentrant so wait helpers can call the core under the same lock.
5. **Fail-closed ceilings**: `max_credit`, `max_buffer`, `idempotency_window` enforced by raising, never by growth or silent drop.
6. **Explicit termination model**: `end` (graceful) vs `drop_writer`/`drop_reader` (abrupt), distinguishable to the reader.
7. **Control plane separate** (`StreamRegistry`): auth, quotas, load shedding, breaker, quarantine; data plane has no `pk_core` dependency.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| Unbounded `queue.Queue` | No backpressure; memory grows under slow readers |
| Bounded `queue.Queue` with blocking `put` | Blocks writer threads; hides backpressure from async schedulers; no drop signalling |
| asyncio-only streams | Ties primitive to one runtime; embedding in threaded/WASM hosts harder |
| Byte-window (TCP-style) credit | Elements are typed objects, not bytes; per-element credit is simpler to reason about |
| Lock-free ring buffer | Not practical in CPython stdlib; GIL-era gains unproven; harder to verify |
| Drop-oldest on overflow | Silent data loss contradicts fail-closed requirement |

## Consequences

- Callers must handle `CreditExhausted`/`NOT_READY` or use bounded waits.
- Wait latency granularity ~50 ms (polling slices in `Stream._wait`).
- State is ephemeral (see `spec/crash-semantics.md`).
- Performance: this ADR does not restate measurements. See `benchmarks/results/latest.json` (SLO-3, p99 < 1 µs, is **not met** on the measurement host) and `benchmarks/results/version-compare.json` (4.3.0 hot path is slower than 4.2.0). Consequence to decide: accept, or optimise the write/read path.

## Approval

| Role | Name | Decision | Date |
|------|------|----------|------|
| Component owner | UNASSIGNED — owner to fill | pending | – |
| Architecture reviewer | UNASSIGNED — owner to fill | pending | – |
