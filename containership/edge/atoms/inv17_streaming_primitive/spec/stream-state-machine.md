# INV-17 Stream State Machine

**Controls:** C014, C015 (checklist §4). Source of truth: `stream::Stream.state`.

## 1. States

`Stream.state` derives the state from flags, checked in this order (first match wins):

| Order | State | Condition | Terminal |
|-------|-------|-----------|----------|
| 1 | `reader_dropped` | `reader_dropped` | Yes (absorbing) |
| 2 | `writer_dropped` | `writer_dropped` | Yes for writing; reader may drain buffer |
| 3 | `ended` | `ended` | Yes for writing; reader drains then gets `None` |
| 4 | `frozen` | `frozen` | No (reversible via `unfreeze`) |
| 5 | `credit_stalled` | `credit == 0` | No |
| 6 | `open` | otherwise (`credit > 0`) | No |

A freshly constructed stream has `credit == 0`, so its initial state is **`credit_stalled`**. `ended` and `writer_dropped` both zero credit. The derived state hides secondary flags: e.g. an `ended` stream may still hold buffered elements (see `stats().buffered`), and a frozen stream is reported `frozen` regardless of credit.

## 2. Transition table

Operations: G=`grant`, W=`write`, R=`read`, E=`end`, DR=`drop_reader`, DW=`drop_writer`, F=`freeze`, U=`unfreeze`.

| From \ Op | G | W | R | E | DR | DW | F / U |
|-----------|---|---|---|---|----|----|-------|
| credit_stalled | → open | `CreditExhausted` (or earlier error per requirements §2.1) | value / `NOT_READY` | → ended | → reader_dropped | → writer_dropped | → frozen / – |
| open | → open (≤ max_credit) | → open or credit_stalled (credit−1) | value / `NOT_READY` | → ended | → reader_dropped | → writer_dropped | → frozen / – |
| frozen | `StreamFrozen` | `StreamFrozen` | value / `NOT_READY` | → ended (allowed) | → reader_dropped | → writer_dropped | stays / → open or credit_stalled |
| ended | `StreamClosed` | `StreamClosed` | value, then `None` | no-op (idempotent) | → reader_dropped | → writer_dropped | flag set, state stays `ended` |
| writer_dropped | `StreamClosed` | `EndDropped(writer)` | value, then `EndDropped(writer)` | `EndDropped(writer)` | → reader_dropped | no-op | flag only |
| reader_dropped | `EndDropped(reader)` | `EndDropped(reader)` | `EndDropped(reader)` | `EndDropped(reader)` | no-op | → flag set, state stays `reader_dropped` | flag only |

Illegal operations raise and leave state unchanged. There is no transition out of `reader_dropped`, and no transition from `ended`/`writer_dropped` back to a writable state.

## 3. Terminal semantics

- **Graceful EOF** (`ended`): buffered elements remain readable in FIFO order; then `read()` returns `None` forever.
- **Abrupt writer loss** (`writer_dropped`): buffered elements remain readable; then `read()` raises `EndDropped(end="writer")`. Consumers can therefore distinguish truncation from completion.
- **Reader loss** (`reader_dropped`): buffer is cleared eagerly, `dropped_items += len(buffer)`; writer learns via `EndDropped(end="reader")` on its next operation.
- **Registry removal** (`control::StreamRegistry.close`) only forgets the stream id; it does not change the stream's flags. Callers should `end()`/`drop_*` first.

## 4. Waits and wake-ups

`read_wait` wakes on buffer non-empty, `ended`, `writer_dropped`, `reader_dropped`. `write_wait` additionally wakes on `frozen` and on a duplicate idempotency key. Every transition calls `Condition.notify_all()`. See `spec/operation-semantics.md`.
