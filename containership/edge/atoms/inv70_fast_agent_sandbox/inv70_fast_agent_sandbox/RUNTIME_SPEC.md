# Runtime Specification — INV-70 v4.3.0

## Execution model

`runtime.run()` executes immutable canonical bytecode produced from an exact Python `list` or `tuple`. Validation occurs before the first guest instruction. Validation failures consume zero guest fuel. Runtime traps include the fuel count consumed up to the trapping instruction.

Supported instructions:

| Instruction | Stack effect | Semantics |
|---|---|---|
| `("push", value)` | `… -> …, value` | Push an inert scalar after value/size validation. |
| `("add",)` | `…, a, b -> …, a+b` | Numeric add, `str+str`, or `bytes+bytes`; growth is bounded. |
| `("mul",)` | `…, a, b -> …, a*b` | Numeric multiply or bounded string/bytes repetition by an integer. |
| `("dup",)` | `…, a -> …, a, a` | Duplicate top value subject to stack and logical-memory limits. |
| `("jmp", pc)` | unchanged | Absolute validated jump target. |
| `("jz", pc)` | `…, a -> …` | Jump when `a` is `0`, `0.0`, `False`, or `None`. |
| `("call", name)` | `…, arg -> …, result` | Invoke a specifically granted, bound host capability. |
| `("halt",)` | unchanged | Return the top value, or `None` for an empty stack. |

Exact arity is required; extra or missing operands are invalid. Jump targets must be integers in the validated program range.

## Default limits

| Limit | Default |
|---|---:|
| Fuel | 1,000 instructions |
| Stack depth | 64 cells |
| Logical guest memory | 65,536 bytes |
| Per-value payload | 16,384 bytes |
| Program length | 4,096 instructions |
| Capability count | 256 grants |
| Capability identifier | 128 ASCII characters |

Limits are non-negative exact integers (`bool` is rejected). `max_value_bytes` cannot exceed `max_memory_bytes`.

Logical memory is deliberately conservative and deterministic. Each stack cell is charged fixed overhead plus payload size; strings are charged at four bytes per code point without allocating an encoded copy. This is a guest accounting mechanism, not a measurement of CPython process RSS.

## Guest value types

Only exact instances of `NoneType`, `bool`, `int`, `float`, `str`, and `bytes` are accepted. Non-finite floats (`NaN`, `+/-Infinity`) are rejected. Python subclasses and arbitrary objects are rejected. This prevents guest-supplied `__add__`, `__mul__`, `__eq__`, and related magic methods from becoming ambient Python execution paths.

## Capability boundary

The guest can invoke a host function only when:

1. the bytecode names a non-empty, ASCII-safe capability identifier of at most 128 characters;
2. that name is present in `caps`;
3. `host` binds the name to a callable.

The argument is a validated guest scalar. The callback result is revalidated before it is pushed. Ordinary callback exceptions become `host error: <ExceptionClass>` without including the original exception message.

Host callbacks are trusted embedding code. The in-process VM cannot pre-empt a callback that hangs, cannot prevent a granted callback from performing I/O, and cannot constrain the callback's own process memory. Production deployment therefore requires a separately bounded host-call layer and, per the checklist, a real per-operation Wasm isolation implementation.

## Result compatibility

Success remains `{"ok": value, "fuel": N}`. Guest/runtime failure remains `{"trap": reason, "fuel": N}`. Version 4.2.0 intentionally preserves these two top-level result shapes.

## Lifecycle (4.3.0, INV-70-C015) {#lifecycle}

`semantics.Lifecycle`: `received → authenticated → admitted → validated → running → succeeded | trapped`. From any non-terminal state a run can abort to `rejected | cancelled | timed_out | failed`. Terminal states are final, and any other transition raises `IllegalTransition`. The table is tested exhaustively in `tests/test_semantics.py`.

## Governed execution (4.3.0)

Production callers use `service.Sandbox.handle()` rather than `runtime.run()`. `run()` stays as the in-process reference primitive and its result shape is unchanged. In `handle()`:

- The guest runs in a fresh single-use `spawn` child process, which is killed at `wall_clock_ms`.
- Host callbacks run in the parent, each bounded by `host_call_timeout_ms`, with at most 1,000 calls per run.
- Capabilities are the intersection of what the request asks for and what the signed token grants.
- Fuel can only be lowered by the caller.
- Results carry stable `FB-*` reason codes (`service.REASON_CODES`). `fuel: -1` means the worker was killed, so its count is unknown.
- `backend: wasm` routes to `executor.WasmBackend` (ADR-0001) and fails closed if the pinned engine is absent.
