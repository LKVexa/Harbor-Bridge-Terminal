"""INV-14 -> INV-15 migration bridge (component P0-04; C016, C027, C038, C095, C099).

INV-15's real ABI is not part of this archive, so the bridge targets the minimal
future/stream shape INV-15 is specified to expose (``Inv15FutureProtocol``):
``done() -> bool``, ``wait(timeout_s) -> bool``, ``cancel() -> bool``.

Pieces:
  * ``PollableFuture``  -- presents an INV-14 Pollable as an INV-15-shaped future
    (forward shim: new-style consumer, legacy producer).
  * ``FuturePollable``  -- presents an INV-15-shaped future as an INV-14 Pollable
    (reverse shim: legacy consumer, new-style producer).  Signals exactly once.
  * ``MigrationStateMachine`` -- per-consumer stages LEGACY -> DUAL_STACK ->
    CANARY -> MIGRATED, with ROLLED_BACK; a stage may advance only with a passing
    parity check recorded (``record_parity``) and a rollback is always legal
    from DUAL_STACK / CANARY.
  * ``parity_check`` -- runs the same scenario through both paths and compares
    ready/timeout outcomes; divergence blocks advancement.
The claim that a *live* INV-14 consumer can transition against the *real* INV-15
remains BLOCKED until INV-15 is supplied; the shims are proven against the
protocol only.
"""
from __future__ import annotations

import threading
import time
from typing import Protocol

try:
    from .errors import Inv14Error
    from .polling import Pollable, PollSet
except ImportError:
    from errors import Inv14Error
    from polling import Pollable, PollSet

STAGES = ("LEGACY", "DUAL_STACK", "CANARY", "MIGRATED", "ROLLED_BACK")
ADVANCE = {"LEGACY": "DUAL_STACK", "DUAL_STACK": "CANARY", "CANARY": "MIGRATED", "ROLLED_BACK": "DUAL_STACK"}
ROLLBACK_FROM = {"DUAL_STACK", "CANARY"}


class MigrationError(Inv14Error):
    default_code = "PK_MIGRATION_REFUSED"


class Inv15FutureProtocol(Protocol):
    def done(self) -> bool: ...
    def wait(self, timeout_s: float) -> bool: ...
    def cancel(self) -> bool: ...


class PollableFuture:
    """Forward shim: INV-15-shaped future over an INV-14 pollable."""

    def __init__(self, pollable: Pollable, owner: str, *, tick_seconds: float = 0.001):
        if not isinstance(pollable, Pollable):
            raise MigrationError("PollableFuture wraps a Pollable", code="PK_MIGRATION_TYPE")
        self._p, self._ps = pollable, PollSet(owner, tick_seconds=tick_seconds)
        self._cancelled = False

    def done(self) -> bool:
        return not self._cancelled and self._p.is_ready()

    def wait(self, timeout_s: float) -> bool:
        if self._cancelled:
            return False
        ticks = max(1, int(round(float(timeout_s) / self._ps.tick_seconds)))
        ticks = min(ticks, self._ps.max_timeout_ticks)
        return not self._ps.poll([self._p], timeout_ticks=ticks)["timed_out"]

    def cancel(self) -> bool:
        first = not self._cancelled
        self._cancelled = True
        return first


class SimpleFuture:
    """Reference INV-15-shaped future used as the new-style producer in tests."""

    def __init__(self):
        self._ev, self._cb_lock, self._cbs, self._cancelled = threading.Event(), threading.Lock(), [], False

    def set_result(self):
        with self._cb_lock:
            if self._ev.is_set() or self._cancelled:
                return
            self._ev.set()
            cbs = list(self._cbs)
        for cb in cbs:
            cb()

    def add_done_callback(self, cb):
        with self._cb_lock:
            if not self._ev.is_set():
                self._cbs.append(cb)
                return
        cb()

    def done(self):
        return self._ev.is_set()

    def wait(self, timeout_s):
        return self._ev.wait(timeout_s)

    def cancel(self):
        with self._cb_lock:
            first = not self._cancelled and not self._ev.is_set()
            self._cancelled = True
            return first


class FuturePollable(Pollable):
    """Reverse shim: an INV-14 pollable signalled when an INV-15 future completes."""

    def __init__(self, name: str, owner: str, future):
        super().__init__(name, owner)
        if not hasattr(future, "add_done_callback"):
            raise MigrationError("future lacks add_done_callback", code="PK_MIGRATION_TYPE")
        future.add_done_callback(self.signal)


class MigrationStateMachine:
    def __init__(self, consumer: str, *, clock=time.time):
        if not isinstance(consumer, str) or not consumer:
            raise MigrationError("consumer id required", code="PK_MIGRATION_CONSUMER")
        self.consumer, self._clock = consumer, clock
        self._lock = threading.Lock()
        self.stage = "LEGACY"
        self._parity_ok_for: str | None = None
        self.history = [{"stage": "LEGACY", "at": clock()}]

    def record_parity(self, result: dict) -> None:
        with self._lock:
            self._parity_ok_for = self.stage if result.get("equivalent") is True else None

    def advance(self, *, actor: str) -> str:
        with self._lock:
            nxt = ADVANCE.get(self.stage)
            if nxt is None:
                raise MigrationError("no further stage", code="PK_MIGRATION_TERMINAL", details={"stage": self.stage})
            if self.stage in ("DUAL_STACK", "CANARY") and self._parity_ok_for != self.stage:
                raise MigrationError("advancement requires a passing parity check at this stage",
                                     code="PK_MIGRATION_PARITY_REQUIRED", details={"stage": self.stage})
            self.stage, self._parity_ok_for = nxt, None
            self.history.append({"stage": nxt, "actor": str(actor)[:64], "at": self._clock()})
            return nxt

    def rollback(self, *, actor: str, reason: str) -> str:
        with self._lock:
            if self.stage not in ROLLBACK_FROM:
                raise MigrationError("rollback not legal from this stage", code="PK_MIGRATION_ROLLBACK",
                                     details={"stage": self.stage})
            self.stage, self._parity_ok_for = "ROLLED_BACK", None
            self.history.append({"stage": "ROLLED_BACK", "actor": str(actor)[:64], "reason": str(reason)[:256],
                                 "at": self._clock()})
            return self.stage


def parity_check(scenarios=("ready", "timeout", "late_ready")) -> dict:
    """Run each scenario through the legacy poll path and through the forward shim."""
    results = []
    for sc in scenarios:
        outs = []
        for path in ("legacy", "inv15_shim"):
            p = Pollable("res", "t/c/i")
            if sc == "ready":
                p.signal()
            elif sc == "late_ready":
                threading.Timer(0.01, p.signal).start()
            if path == "legacy":
                ok = not PollSet("t/c/i").poll([p], timeout_ticks=200)["timed_out"] if sc != "timeout" \
                    else not PollSet("t/c/i").poll([p], timeout_ticks=5)["timed_out"]
            else:
                f = PollableFuture(p, "t/c/i")
                ok = f.wait(0.2 if sc != "timeout" else 0.005)
            outs.append(ok)
        results.append({"scenario": sc, "legacy": outs[0], "inv15_shim": outs[1], "match": outs[0] == outs[1]})
    return {"equivalent": all(r["match"] for r in results), "scenarios": results}
