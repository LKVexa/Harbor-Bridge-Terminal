"""Production lifecycle state machine and ownership fencing (C015, C057, C058, C059).

Every legal transition is enumerated with its initiator, guard and emitted
event.  Anything not in ``TRANSITIONS`` is rejected.  A failed teardown can never
collapse into CLOSED: CLOSED is reachable only from VERIFYING_TEARDOWN with a
verified teardown proof.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import threading
from typing import Callable

from .errors import ControlError


class State(str, Enum):
    REQUESTED = "REQUESTED"
    VALIDATING = "VALIDATING"
    ALLOCATING = "ALLOCATING"
    STARTING = "STARTING"
    READY = "READY"
    RUNNING = "RUNNING"
    DRAINING = "DRAINING"
    STOPPING = "STOPPING"
    VERIFYING_TEARDOWN = "VERIFYING_TEARDOWN"
    CLOSED = "CLOSED"
    FAILED = "FAILED"
    FROZEN = "FROZEN"
    QUARANTINED = "QUARANTINED"
    REAPING = "REAPING"


TERMINAL = frozenset({State.CLOSED})
RECOVERABLE_FAILURE = frozenset({State.FAILED})  # must still be reaped + verified
# Intermediate states whose age is watched by the stall detector.
WATCHED = frozenset({State.VALIDATING, State.ALLOCATING, State.STARTING, State.DRAINING,
                     State.STOPPING, State.VERIFYING_TEARDOWN, State.REAPING})


@dataclass(frozen=True)
class Transition:
    src: State
    dst: State
    initiator: str          # controller | node | operator | watchdog
    guard: str              # human-readable guard, enforced in code where named
    timeout_s: float | None # maximum time allowed in dst before stall handling
    event: str
    crash_recovery: str     # what reconciliation does if the controller dies in dst


S = State
TRANSITIONS: tuple[Transition, ...] = (
    Transition(S.REQUESTED, S.VALIDATING, "controller", "authenticated+authorized request", 2.0, "session.validating", "restart validation; idempotent"),
    Transition(S.VALIDATING, S.ALLOCATING, "controller", "admission granted", 5.0, "session.allocating", "release reservation; restart from REQUESTED"),
    Transition(S.VALIDATING, S.FAILED, "controller", "validation/admission rejected", None, "session.failed", "reap (no resources)"),
    Transition(S.ALLOCATING, S.STARTING, "node", "resources reserved; artifacts verified", 10.0, "session.starting", "reap host resources, then FAILED"),
    Transition(S.ALLOCATING, S.FAILED, "node", "allocation failed", None, "session.failed", "reap"),
    Transition(S.STARTING, S.READY, "node", "READY postconditions proven", None, "session.ready", "probe VMM; if absent reap"),
    Transition(S.STARTING, S.FAILED, "node", "boot failed or timed out", None, "session.failed", "reap"),
    Transition(S.READY, S.RUNNING, "controller", "first exec accepted", None, "session.running", "probe VMM"),
    Transition(S.READY, S.DRAINING, "controller", "stop requested", 30.0, "session.draining", "continue drain"),
    Transition(S.RUNNING, S.DRAINING, "controller", "stop requested", 30.0, "session.draining", "continue drain"),
    Transition(S.RUNNING, S.FAILED, "node", "guest crash detected", None, "session.failed", "reap"),
    Transition(S.DRAINING, S.STOPPING, "controller", "drain complete or deadline", 15.0, "session.stopping", "continue stop"),
    Transition(S.STOPPING, S.VERIFYING_TEARDOWN, "node", "VMM exited", 15.0, "session.verifying", "re-run verification"),
    Transition(S.VERIFYING_TEARDOWN, S.CLOSED, "node", "teardown proof verified", None, "session.closed", "none (terminal)"),
    Transition(S.VERIFYING_TEARDOWN, S.QUARANTINED, "node", "teardown proof failed", None, "session.quarantined", "hold for operator"),
    Transition(S.FAILED, S.REAPING, "watchdog", "reaper scheduled", 30.0, "session.reaping", "re-run reap"),
    Transition(S.REAPING, S.VERIFYING_TEARDOWN, "node", "reap finished", 15.0, "session.verifying", "re-run verification"),
    Transition(S.REAPING, S.QUARANTINED, "node", "reap failed", None, "session.quarantined", "hold for operator"),
    Transition(S.READY, S.FROZEN, "operator", "authorized freeze (forensics)", None, "session.frozen", "stay frozen"),
    Transition(S.RUNNING, S.FROZEN, "operator", "authorized freeze (forensics)", None, "session.frozen", "stay frozen"),
    Transition(S.FROZEN, S.QUARANTINED, "operator", "authorized quarantine", None, "session.quarantined", "hold"),
    Transition(S.FROZEN, S.STOPPING, "operator", "authorized terminate", 15.0, "session.stopping", "continue stop"),
    Transition(S.QUARANTINED, S.REAPING, "operator", "authorized release for reap after forensics", 30.0, "session.reaping", "re-run reap"),
)
# Stall handling (C052): the watchdog may fail any watched pre-READY/stop state
# that exceeds its deadline.  A stalled REAPING or VERIFYING_TEARDOWN goes to
# QUARANTINED, never to CLOSED.
TRANSITIONS += tuple(
    Transition(st, S.FAILED, "watchdog", "state deadline exceeded", None, "session.stalled", "reap")
    for st in (S.VALIDATING, S.ALLOCATING, S.STARTING, S.DRAINING, S.STOPPING)
) + (
    Transition(S.REAPING, S.QUARANTINED, "watchdog", "reap deadline exceeded", None, "session.quarantined", "hold"),
    Transition(S.VERIFYING_TEARDOWN, S.QUARANTINED, "watchdog", "verification deadline exceeded", None, "session.quarantined", "hold"),
)

_INDEX = {(t.src, t.dst, t.initiator): t for t in TRANSITIONS}


def legal(src: State, dst: State, initiator: str) -> Transition | None:
    return _INDEX.get((src, dst, initiator))


@dataclass
class Lease:
    """Fencing lease: a monotonically increasing epoch per session owner."""
    owner: str
    epoch: int


class LeaseTable:
    """Authoritative ownership record with fencing tokens (C055-IMP-03, C058).

    Epochs come from one table-wide monotonic counter, so an epoch is never
    reissued - even after a closed session's lease is released and its sid is
    reused.  (v4.3.0: per-sid counters forced the table to keep every lease
    forever; found by tools/bench.py residual-memory growth.)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._leases: dict[str, Lease] = {}
        self._counter = 0

    def acquire(self, sid: str, owner: str) -> Lease:
        with self._lock:
            self._counter += 1
            lease = Lease(owner, self._counter)
            self._leases[sid] = lease
            return lease

    def check(self, sid: str, owner: str, epoch: int) -> None:
        with self._lock:
            cur = self._leases.get(sid)
            if cur is None or cur.owner != owner or cur.epoch != epoch:
                raise ControlError("LIFECYCLE.STALE_EPOCH", f"sid={sid}")

    def release(self, sid: str, owner: str, epoch: int) -> None:
        with self._lock:
            cur = self._leases.get(sid)
            if cur is not None and cur.owner == owner and cur.epoch == epoch:
                del self._leases[sid]

    def current(self, sid: str) -> Lease | None:
        with self._lock:
            return self._leases.get(sid)

    def __len__(self) -> int:
        return len(self._leases)


@dataclass(frozen=True)
class TeardownProof:
    """Evidence that a teardown left nothing behind.  Built only from a guest
    teardown record and a host reconciliation (``from_reconciliation``).

    This is an in-process object, not a signed attestation: code in the same
    process could still construct one.  Production must replace it with a
    node-signed teardown record verified by the controller."""
    sid: str
    guest_verified: bool
    leaked: tuple
    orphans: tuple

    @property
    def verified(self) -> bool:
        return self.guest_verified and not self.leaked

    @classmethod
    def from_reconciliation(cls, sid: str, guest_record: dict, reconciliation) -> "TeardownProof":
        if guest_record.get("sid") != sid:
            raise ControlError("TEARDOWN.VERIFICATION_FAILED", "proof sid mismatch")
        return cls(sid, guest_record.get("verified") is True and guest_record.get("state") == "closed",
                   tuple(reconciliation.leaked), tuple(reconciliation.orphans))


@dataclass
class Lifecycle:
    sid: str
    clock: Callable[[], float]
    state: State = State.REQUESTED
    entered_at: float = 0.0
    history: list[tuple[str, str, str, float]] = field(default_factory=list)
    teardown_proof: "TeardownProof | None" = None

    def __post_init__(self) -> None:
        self.entered_at = self.clock()

    def transition(self, dst: State, *, initiator: str, proof: "TeardownProof | None" = None) -> Transition:
        t = legal(self.state, dst, initiator)
        if t is None:
            raise ControlError("LIFECYCLE.ILLEGAL_TRANSITION",
                               f"{self.state.value}->{dst.value} by {initiator}")
        if dst is State.CLOSED:
            if not isinstance(proof, TeardownProof) or proof.sid != self.sid or not proof.verified:
                raise ControlError("LIFECYCLE.ILLEGAL_TRANSITION", "CLOSED requires a verified TeardownProof for this sid")
            self.teardown_proof = proof
        now = self.clock()
        self.history.append((self.state.value, dst.value, initiator, now))
        self.state, self.entered_at = dst, now
        return t

    def overdue(self) -> bool:
        """True when the current state has exceeded its declared deadline."""
        incoming = [t for t in TRANSITIONS if t.dst is self.state and t.timeout_s is not None]
        if not incoming:
            return False
        limit = max(t.timeout_s for t in incoming)  # type: ignore[type-var]
        return (self.clock() - self.entered_at) > limit
