"""Formal lifecycle state machine for INV-15 subtasks (component 7).

The transition table below is normative. Any edge not listed is forbidden and
raises ``IllegalTransition`` (never silently ignored). Terminal states can
never transition anywhere, so a terminal handle cannot be resurrected.
"""
from __future__ import annotations

from enum import Enum

from .errors import AbiError, ErrorCode


class State(str, Enum):
    PENDING = "pending"
    READY = "ready"            # completed successfully, result unread
    TRAPPED = "trapped"        # callee trapped / faulted, error unread
    TIMED_OUT = "timed_out"    # call timeout or inherited deadline, unread
    CANCELLED = "cancelled"    # terminal
    CONSUMED = "consumed"      # terminal
    ABANDONED = "abandoned"    # terminal: result produced, never read
    INVALIDATED = "invalidated"  # terminal: teardown / restart / disable


RESOLVED = frozenset({State.READY, State.TRAPPED, State.TIMED_OUT})
TERMINAL = frozenset({State.CANCELLED, State.CONSUMED, State.ABANDONED, State.INVALIDATED})

TRANSITIONS: dict[State, frozenset[State]] = {
    State.PENDING: frozenset({State.READY, State.TRAPPED, State.TIMED_OUT,
                              State.CANCELLED, State.INVALIDATED}),
    State.READY: frozenset({State.CONSUMED, State.ABANDONED, State.INVALIDATED}),
    State.TRAPPED: frozenset({State.CONSUMED, State.ABANDONED, State.INVALIDATED}),
    State.TIMED_OUT: frozenset({State.CONSUMED, State.ABANDONED, State.INVALIDATED}),
    State.CANCELLED: frozenset(),
    State.CONSUMED: frozenset(),
    State.ABANDONED: frozenset(),
    State.INVALIDATED: frozenset(),
}

# Operation legality per state and the stable error for each forbidden use.
OPERATION_ERRORS = {
    "complete": {State.PENDING: None, **{s: ErrorCode.DUPLICATE_PUBLICATION for s in RESOLVED},
                 **{s: ErrorCode.INVALIDATED for s in TERMINAL}},
    "take": {State.PENDING: ErrorCode.NOT_READY, **{s: None for s in RESOLVED},
             **{s: ErrorCode.HANDLE_CONSUMED for s in TERMINAL}},
    "cancel": {State.PENDING: None, **{s: None for s in RESOLVED},
               **{s: ErrorCode.HANDLE_CONSUMED for s in TERMINAL}},
    "wait": {State.PENDING: None, **{s: None for s in RESOLVED},
             **{s: ErrorCode.HANDLE_CONSUMED for s in TERMINAL}},
}


class IllegalTransition(AbiError):
    code = ErrorCode.HOST_FAILURE


def check(src: State, dst: State) -> None:
    if dst not in TRANSITIONS[src]:
        raise IllegalTransition(f"forbidden edge {src.value} -> {dst.value}")


def table_markdown() -> str:
    states = list(State)
    head = "| from \\ to | " + " | ".join(s.value for s in states) + " |"
    rows = [head, "|" + "---|" * (len(states) + 1)]
    for a in states:
        rows.append(f"| {a.value} | " + " | ".join("allowed" if b in TRANSITIONS[a] else "-" for b in states) + " |")
    return "\n".join(rows)
