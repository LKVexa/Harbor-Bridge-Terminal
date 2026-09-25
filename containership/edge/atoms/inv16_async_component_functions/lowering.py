"""Reference async state-machine lowering (closure item #8, reference half).

Lowers a tiny structured IR of an async function into an explicit resumable
state machine whose locals live in a per-call ``Frame`` (never in instance
storage).  It fixes the *semantics* a production compiler backend must
reproduce - discriminants, suspension/resume, per-call storage, exactly-once
cleanup on every terminal path - and is differentially tested against a native
Python coroutine (``tests/test_lowering.py``).  The production compiler
backend itself is outside this archive and remains BLOCKED in the ledger.

IR ops (tuples):
    ("let", var, fn, *argvars)   var = fn(*args)              no suspension
    ("await", var, subtask)      suspend; resume value -> var
    ("if", var, then_ops, else_ops)
    ("return", var)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

LOWERING_VERSION = 1


class InvalidResume(RuntimeError):
    """Resume with a wrong/unknown discriminant or on a finished frame."""


@dataclass(frozen=True)
class State:
    index: int
    ops: tuple            # straight-line ops executed on entry to this state
    awaits: tuple | None  # (var, subtask) suspension that ends the state, or None
    next: int | None


@dataclass
class Machine:
    name: str
    states: tuple[State, ...]
    version: int = LOWERING_VERSION

    def describe(self) -> list[dict]:
        return [{"state": s.index, "ops": [o[0] for o in s.ops],
                 "suspend": None if s.awaits is None else s.awaits[1], "next": s.next} for s in self.states]


@dataclass
class Frame:
    """Per-call storage: every local that crosses a suspension point lives here."""

    machine: Machine
    locals: dict = field(default_factory=dict)
    pc: int = 0
    status: str = "ready"   # ready | suspended | returned | cancelled | trapped
    pending: str | None = None
    result: Any = None
    cleanups: int = 0


def lower(name: str, ops: list) -> Machine:
    """Flatten branches by guarding, split at every await into a numbered state."""
    flat = _flatten(ops)
    states: list[State] = []
    cur: list = []
    for op in flat:
        if op[0] == "await":
            states.append(State(len(states), tuple(cur), (op[1], op[2]), len(states) + 1))
            cur = []
        else:
            cur.append(op)
    states.append(State(len(states), tuple(cur), None, None))
    return Machine(name, tuple(states))


def _flatten(ops: list, guard: tuple = ()) -> list:
    out = []
    for op in ops:
        if op[0] == "if":
            _, var, then_ops, else_ops = op
            out += _flatten(then_ops, guard + ((var, True),))
            out += _flatten(else_ops, guard + ((var, False),))
        elif guard:
            if op[0] == "await":
                raise ValueError("await inside a branch is not supported by lowering v1")
            out.append(("guarded", guard, op))
        else:
            out.append(op)
    return out


def start(machine: Machine) -> Frame:
    return Frame(machine)


def step(frame: Frame, env: dict[str, Callable], resume_value: Any = None,
         discriminant: int | None = None) -> tuple[str, Any]:
    """Run until the next suspension or return.

    Returns ("suspend", subtask) or ("return", value).  Resuming requires the
    discriminant the frame suspended at; anything else fails closed.
    """
    if frame.status in ("returned", "cancelled", "trapped"):
        raise InvalidResume(f"frame is {frame.status}")
    if frame.status == "suspended":
        if discriminant != frame.pc:
            raise InvalidResume(f"resume discriminant {discriminant!r} != suspended state {frame.pc}")
        var = frame.machine.states[frame.pc].awaits[0]
        frame.locals[var] = resume_value
        frame.pc += 1
    elif discriminant not in (None, 0):
        raise InvalidResume("initial step takes no discriminant")
    if not 0 <= frame.pc < len(frame.machine.states):
        frame.status = "trapped"
        raise InvalidResume(f"impossible state {frame.pc}")
    st = frame.machine.states[frame.pc]
    try:
        for op in st.ops:
            ret = _exec(op, frame, env)
            if ret is not _NORET:
                frame.status, frame.result = "returned", ret
                _cleanup(frame)
                return "return", ret
    except Exception:
        frame.status = "trapped"
        _cleanup(frame)
        raise
    if st.awaits is not None:
        frame.status, frame.pending = "suspended", st.awaits[1]
        return "suspend", st.awaits[1]
    frame.status = "returned"
    _cleanup(frame)
    return "return", None


def cancel(frame: Frame) -> None:
    """Cancel between suspension and resume; cleanup runs exactly once."""
    if frame.status in ("returned", "cancelled", "trapped"):
        return
    frame.status = "cancelled"
    _cleanup(frame)


_NORET = object()


def _exec(op, frame: Frame, env):
    kind = op[0]
    if kind == "guarded":
        _, guard, inner = op
        if all(bool(frame.locals.get(v)) is want for v, want in guard):
            return _exec(inner, frame, env)
        return _NORET
    if kind == "let":
        _, var, fn, *args = op
        frame.locals[var] = env[fn](*(frame.locals[a] for a in args))
        return _NORET
    if kind == "return":
        return frame.locals[op[1]]
    raise ValueError(f"unknown op {kind!r}")


def _cleanup(frame: Frame) -> None:
    frame.cleanups += 1
    frame.locals.clear()     # drop per-call storage; asserted exactly once in tests
    frame.pending = None
