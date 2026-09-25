"""Component 46 - deterministic fault-injection harness.

Contract ``PK_DYN_FAULTS/1``:
* ``FakeClock`` - the only time source in fault tests; ``sleep`` advances it.
* ``FaultyProvider(inner, plan)`` - per-operation faults: ``transient``,
  ``terminal``, ``latency`` (advances clock), ``lost_response`` (the call
  succeeds at the provider but the caller sees a transient error - the classic
  duplicate-create hazard).  Faults fire by explicit count or seeded
  probability (``random.Random(seed)``), so every run is reproducible.
* ``Crash`` / ``crash_at(point)`` - raises ``Crash`` at a named controller
  crash point (``create:after_pending``, ``create:after_call``,
  ``delete:after_drain`` ...), modelling process death between journal and
  side effect.  Restart = build a new Controller via ``Controller.recover``.
* ``Partition`` - wraps a LeaseStore: ``partitioned`` makes every call raise
  INV08.STORE.UNAVAILABLE; ``loss`` drops calls with seeded probability;
  ``latency`` advances the clock per call.
* Objective helpers: ``rounds_to_converge`` (convergence RTO in rounds and
  clock seconds) and ``rpo_lost_ops`` (committed DONE ops missing after
  recovery; objective = 0).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .adapters import ProviderTransient
from .core import Inv08Error, Outcome, wrap_provider_error


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, dt: float) -> None:
        if dt < 0:
            raise ValueError("time cannot go backwards")
        self.now += dt

    sleep = advance


class Crash(BaseException):
    """Simulated process death (BaseException so no handler swallows it)."""


def crash_at(point: str, *, times: int = 1):
    remaining = [times]

    def hook(p: str) -> None:
        if p == point and remaining[0] > 0:
            remaining[0] -= 1
            raise Crash(p)
    return hook


FAULT_KINDS = ("transient", "terminal", "latency", "lost_response")


@dataclass
class Fault:
    op: str                     # create|drain|delete|list|*
    kind: str
    count: int = 1              # fire this many times (-1 = unlimited, subject to probability)
    probability: float = 1.0
    latency: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in FAULT_KINDS:
            raise ValueError(f"unknown fault kind {self.kind}")
        if not 0 <= self.probability <= 1:
            raise ValueError("probability in [0, 1]")


@dataclass
class FaultPlan:
    faults: list[Fault] = field(default_factory=list)
    seed: int = 0
    fired: list[tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def pick(self, op: str) -> Fault | None:
        for f in self.faults:
            if f.op in (op, "*") and f.count != 0 and self.rng.random() < f.probability:
                if f.count > 0:
                    f.count -= 1
                self.fired.append((op, f.kind))
                return f
        return None


class FaultyProvider:
    def __init__(self, inner, plan: FaultPlan, clock: FakeClock) -> None:
        self.inner, self.plan, self.clock = inner, plan, clock
        self.name, self.kind = inner.name, inner.kind

    def _do(self, op: str, fn):
        f = self.plan.pick(op)
        if f is None:
            return fn()
        if f.kind == "latency":
            self.clock.advance(f.latency)
            return fn()
        if f.kind == "transient":
            raise wrap_provider_error(self.name, ProviderTransient(f"injected transient on {op}"), retryable=True)
        if f.kind == "terminal":
            raise wrap_provider_error(self.name, RuntimeError(f"injected terminal on {op}"), retryable=False)
        fn()  # lost_response: side effect happens, reply lost
        raise wrap_provider_error(self.name, ProviderTransient(f"response lost on {op}"), retryable=True)

    def capabilities(self):
        return self._do("capabilities", self.inner.capabilities)

    def create(self, node_id, spec, *, idempotency_key, fence):
        return self._do("create", lambda: self.inner.create(node_id, spec, idempotency_key=idempotency_key,
                                                            fence=fence))

    def drain(self, node_id, *, idempotency_key, fence):
        return self._do("drain", lambda: self.inner.drain(node_id, idempotency_key=idempotency_key, fence=fence))

    def delete(self, node_id, *, idempotency_key, fence):
        return self._do("delete", lambda: self.inner.delete(node_id, idempotency_key=idempotency_key, fence=fence))

    def list(self):
        return self._do("list", self.inner.list)


class Partition:
    """Proxy around a LeaseStore simulating partition / loss / latency."""

    def __init__(self, store, clock: FakeClock, *, seed: int = 0) -> None:
        self._store, self._clock = store, clock
        self.partitioned = False
        self.loss = 0.0
        self.latency = 0.0
        self._rng = random.Random(seed)
        self.dropped = 0

    def __getattr__(self, name):
        attr = getattr(self._store, name)
        if not callable(attr):
            return attr

        def wrapped(*a, **kw):
            if self.latency:
                self._clock.advance(self.latency)
            if self.partitioned or (self.loss and self._rng.random() < self.loss):
                self.dropped += 1
                raise Inv08Error("INV08.STORE.UNAVAILABLE", f"partition: {name} unreachable",
                                 outcome=Outcome.RETRYABLE_FAILURE)
            return attr(*a, **kw)
        return wrapped


def rounds_to_converge(controller, demand: float, clock: FakeClock, *, interval: float,
                       max_rounds: int = 20) -> tuple[int, float, dict]:
    start = clock()
    rep: dict = {}
    for i in range(1, max_rounds + 1):
        rep = controller.reconcile(demand)
        if rep.get("converged"):
            return i, clock() - start, rep
        clock.advance(interval)
    return -1, clock() - start, rep


def rpo_lost_ops(before: dict, after: dict) -> list[str]:
    """Ops DONE in ``before`` that are not DONE in ``after`` (RPO objective: none)."""
    return sorted(k for k, v in before.get("ops", {}).items()
                  if v["status"] == "DONE" and after.get("ops", {}).get(k, {}).get("status") != "DONE")
