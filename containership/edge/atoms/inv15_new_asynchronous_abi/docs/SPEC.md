# INV-15 PK_ASYNC 1.1 — Normative specification (reference host 4.3.0)

Status: **normative for this repository; not externally ratified.** Key words MUST/SHOULD/MAY per RFC 2119.
Canonical IDL: `idl/pk_async.wit` (frozen, discriminants permanent). Byte layouts: `handles.py`, `wire/codec.py`.
Every invariant below names the executable test that checks it.

## 1. PK_ASYNC_CALL/1
- C1 A call MUST return exactly one of `value`, `subtask`, `error`. Callers MUST treat an immediate value and a subtask that later yields the same value as semantically equivalent. — `test_host.TestCore.test_immediate_none_is_a_value`, `test_adapters.TestAsyncFunction`
- C2 Admission refusal (BUDGET_EXHAUSTED, DRAINING, DISABLED, MEMORY_EXHAUSTED, RNG_UNAVAILABLE, DEADLINE_EXCEEDED at admission, INVALID_ARGUMENT) MUST be returned synchronously as `error` and MUST NOT create a subtask; execution failure MUST only surface through `take` on a subtask (TRAPPED, CALL_TIMEOUT, DEADLINE_EXCEEDED). — `test_host.TestDeadlines.test_admission_validation`, `TestRng.test_fail_closed`
- C3 `None` MUST be a valid synchronous value. — `test_host.TestCore.test_immediate_none_is_a_value`
- C4 A failed admission MUST roll back every reservation (budget, memory, slot). — `TestGenerations.test_generation_wrap_retires_slot`, `TestMemoryOwnership.test_accounting_and_ceiling`

## 2. PK_WAITABLE_SET/1
- W1 A wait set is a set: duplicates collapse; the canonical wire form is sorted ascending by handle bytes and a decoder MUST reject unsorted or duplicate members. — `test_wire.TestNegotiation.test_wait_is_canonical_set`, vectors `wait.duplicate`, `wait.unsorted`
- W2 Cardinality MUST NOT exceed the instance budget (WAIT_SET_TOO_LARGE); wire maximum 4096. — `TestCore.test_wait_set_bound`
- W3 The iterable MUST be consumed exactly once and outside the host lock. — `TestCore.test_complete_wait_take`
- W4 Result order: request order, first occurrence. Any invalid member fails the whole wait (no partial result).
- W5 A wait timeout MUST NOT change subtask state. — `TestDeadlines.test_wait_timeout_leaves_handle_live`

## 3. PK_SUBTASK_CANCEL/1
- K1 Acks: PROPAGATED (pending → CANCELLED, producer publication refused from now on; external side effects are NOT guaranteed stopped), COMPLETED_BEFORE_CANCEL (resolved result abandoned and released), ALREADY_TERMINAL (idempotent re-cancel of a recently retired handle), UNABLE_TO_CANCEL (non-cancellable call; state unchanged). — `TestCancellation.test_ack_states`
- K2 Reasons MUST be a `CancelReason` code; free-form strings are refused. — same
- K3 Cancelling a parent cancels all non-detached pending descendants, children before parent, reason PARENT_CANCELLED; detached children are re-owned by the instance. Tree depth ≤ 64 levels. — `test_tree_and_detached`, `test_depth_limit`

## 4. Error envelope
`{code:u16, retryable:bool, detail:string}`; callers MUST branch on `code` only. Values 1–23 assigned; 64–254 reserved; 255 forbidden. — `test_wire.TestIdl`

## 5. Handles
30-byte v1 layout (+16-byte HMAC when FLAG_AUTH). Unknown version → UNSUPPORTED_VERSION; unknown must-understand bit → UNSUPPORTED_FEATURE; advisory bits 4–7 ignored. Slot and generation MUST both match; generation wrap retires the slot permanently. — `test_wire.TestHandleEncoding`, `TestGenerations`

## 6. Lifecycle (normative transition table; any other edge raises)
| from \ to | pending | ready | trapped | timed_out | cancelled | consumed | abandoned | invalidated |
|---|---|---|---|---|---|---|---|---|
| pending | - | allowed | allowed | allowed | allowed | - | - | allowed |
| ready | - | - | - | - | - | allowed | allowed | allowed |
| trapped | - | - | - | - | - | allowed | allowed | allowed |
| timed_out | - | - | - | - | - | allowed | allowed | allowed |
| cancelled | - | - | - | - | - | - | - | - |
| consumed | - | - | - | - | - | - | - | - |
| abandoned | - | - | - | - | - | - | - | - |
| invalidated | - | - | - | - | - | - | - | - |

Terminal states have no exits; no edge returns to `pending`. — `test_host.TestLifecycle`, property test `test_certification.TestProperty`

## 7. Timing
Clock: host monotonic ns (`time.monotonic_ns` by default, injectable), clamped so it never runs backwards (regressions counted). Deadline domain is 0..2^63-1; overflow is INVALID_ARGUMENT. Child deadline = min(own, parent). Expiry is applied by `expire()`; **precedence** is lock-acquisition order: whichever of completion / cancel / expire / teardown linearizes first wins and every later one observes a resolved or terminal row. Suspend/resume: the monotonic clock's platform behaviour applies; not tested here.

## 8. Linearization and memory ordering
See `MEMORY_MODEL.md`.
