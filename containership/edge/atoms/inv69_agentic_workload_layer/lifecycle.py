"""Typed lifecycle state machines for runs, tool invocations and approvals (C015).

All lifecycle mutation goes through ``Lifecycle.transition``; callers cannot
assign state directly (``state`` is a read-only property).  Every transition is
recorded with a monotonically increasing sequence, actor, reason, policy
version and timestamp.  A duplicate request carrying the same ``request_id``
returns the original record (idempotent); an illegal transition raises
``AgentError(AGT-LCY-001)`` and records nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
import threading
import time

from .errors import AgentError


class RunState(str, Enum):
    CREATED = "created"
    ADMITTED = "admitted"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUSPENDED = "suspended"          # durable checkpoint, e.g. failover / offline
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class InvocationState(str, Enum):
    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"
    DISPATCHED = "dispatched"        # handed to a sandbox: side effects possible from here on
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    INDETERMINATE = "indeterminate"  # dispatched, then lost: side effect unknown; never auto-retried


class ApprovalState(str, Enum):
    REQUESTED = "requested"
    GRANTED = "granted"
    REJECTED = "rejected"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"


RUN_TRANSITIONS = {
    RunState.CREATED: {RunState.ADMITTED, RunState.REJECTED, RunState.CANCELLED},
    RunState.ADMITTED: {RunState.RUNNING, RunState.CANCELLED, RunState.REJECTED},
    RunState.RUNNING: {RunState.AWAITING_APPROVAL, RunState.SUSPENDED, RunState.CANCELLING,
                       RunState.SUCCEEDED, RunState.FAILED},
    RunState.AWAITING_APPROVAL: {RunState.RUNNING, RunState.CANCELLING, RunState.FAILED, RunState.SUSPENDED},
    RunState.SUSPENDED: {RunState.RUNNING, RunState.CANCELLING, RunState.FAILED},
    RunState.CANCELLING: {RunState.CANCELLED, RunState.FAILED},
}
INVOCATION_TRANSITIONS = {
    InvocationState.REQUESTED: {InvocationState.AUTHORIZED, InvocationState.DENIED, InvocationState.CANCELLED},
    InvocationState.AUTHORIZED: {InvocationState.PENDING_APPROVAL, InvocationState.DISPATCHED,
                                 InvocationState.DENIED, InvocationState.CANCELLED, InvocationState.TIMED_OUT},
    InvocationState.PENDING_APPROVAL: {InvocationState.AUTHORIZED, InvocationState.DENIED,
                                       InvocationState.CANCELLED, InvocationState.TIMED_OUT},
    InvocationState.DISPATCHED: {InvocationState.COMPLETED, InvocationState.FAILED,
                                 InvocationState.TIMED_OUT, InvocationState.INDETERMINATE},
}
APPROVAL_TRANSITIONS = {
    ApprovalState.REQUESTED: {ApprovalState.GRANTED, ApprovalState.REJECTED, ApprovalState.EXPIRED},
    ApprovalState.GRANTED: {ApprovalState.CONSUMED, ApprovalState.EXPIRED, ApprovalState.REVOKED},
}
TABLES = {"run": (RunState, RUN_TRANSITIONS), "invocation": (InvocationState, INVOCATION_TRANSITIONS),
          "approval": (ApprovalState, APPROVAL_TRANSITIONS)}

# Guard invariants checked by the machine itself.
INVARIANTS = (
    "invocation DISPATCHED requires a prior AUTHORIZED record",
    "invocation of a side-effecting tool reaches DISPATCHED only via PENDING_APPROVAL -> AUTHORIZED",
    "terminal states have no outgoing transitions",
    "INDETERMINATE invocations are never retried automatically",
)


@dataclass(frozen=True)
class Transition:
    seq: int
    machine: str
    entity_id: str
    from_state: str
    to_state: str
    actor: str
    reason: str
    policy_version: str
    at: float
    request_id: str


class Lifecycle:
    """One state machine instance (run, invocation or approval)."""

    def __init__(self, machine: str, entity_id: str, *, policy_version: str = "unset",
                 clock=time.time, side_effect: bool = False):
        if machine not in TABLES:
            raise ValueError(f"unknown machine {machine!r}")
        self.machine = machine
        self.entity_id = entity_id
        self.policy_version = policy_version
        self.side_effect = side_effect
        enum, _ = TABLES[machine]
        self._state = list(enum)[0]
        self._history: list[Transition] = []
        self._by_request: dict[str, Transition] = {}
        self._lock = threading.Lock()
        self._clock = clock

    @property
    def state(self):
        return self._state

    @property
    def history(self) -> tuple[Transition, ...]:
        return tuple(self._history)

    @property
    def terminal(self) -> bool:
        _, table = TABLES[self.machine]
        return self._state not in table

    def _visited(self, state) -> bool:
        return any(t.to_state == state.value for t in self._history)

    def transition(self, to, *, actor: str, reason: str, request_id: str) -> Transition:
        enum, table = TABLES[self.machine]
        to = enum(to)
        with self._lock:
            if request_id in self._by_request:
                prior = self._by_request[request_id]
                if prior.to_state != to.value:
                    raise AgentError("AGT-LCY-001", "request id reused for a different transition",
                                     details={"request_id": request_id})
                return prior
            allowed = table.get(self._state, set())
            if to not in allowed:
                raise AgentError("AGT-LCY-001", details={"machine": self.machine, "from": self._state.value, "to": to.value})
            if self.machine == "invocation" and to is InvocationState.DISPATCHED:
                if self._state is not InvocationState.AUTHORIZED:
                    raise AgentError("AGT-LCY-001", "dispatch requires authorization")
                if self.side_effect and not self._visited(InvocationState.PENDING_APPROVAL):
                    raise AgentError("AGT-LCY-001", "side-effecting dispatch requires an approval step")
            if not actor or not reason:
                raise AgentError("AGT-VAL-001", "transition requires actor and reason")
            rec = Transition(len(self._history), self.machine, self.entity_id, self._state.value, to.value,
                             actor, reason, self.policy_version, self._clock(), request_id)
            self._history.append(rec)
            self._by_request[request_id] = rec
            self._state = to
            return rec

    def snapshot(self) -> dict[str, Any]:
        return {"machine": self.machine, "entity_id": self.entity_id, "state": self._state.value,
                "history": [t.__dict__ for t in self._history]}

    @classmethod
    def restore(cls, snap: dict[str, Any], **kw) -> "Lifecycle":
        """Rebuild by replaying recorded transitions through the same guards (no impossible states)."""
        lc = cls(snap["machine"], snap["entity_id"], **kw)
        for t in snap["history"]:
            lc.policy_version = t.get("policy_version", lc.policy_version)
            lc.transition(t["to_state"], actor=t["actor"], reason=t["reason"], request_id=t["request_id"])
        if lc.state.value != snap["state"]:
            raise AgentError("AGT-INT-001", "snapshot state disagrees with replayed history")
        return lc
