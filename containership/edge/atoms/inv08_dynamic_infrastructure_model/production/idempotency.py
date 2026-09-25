"""Component 22 - idempotency, retry and backpressure contract.

* Operation ids: ``op-<16 hex>`` from an injected ``random.Random``; the
  idempotency key is (principal, op_id); the request is bound by its canonical
  digest.
* Dedup store: entries live for ``window`` seconds after completion.  Same key
  + same digest -> cached result (no re-execution); same key + different
  digest -> INV08.IDEMP.KEY_REUSE; same key while running ->
  INV08.IDEMP.IN_PROGRESS (retryable).  Capacity is bounded (``max_entries``);
  expired entries are evicted first, otherwise INV08.IDEMP.STORE_FULL.
  Failed terminal executions are cached; retryable failures are not (the
  client may retry with the same key).
* Budgets: ``Budget(total, clock)`` - ``remaining()``, ``child(fraction)``
  never exceeds the parent; ``check()`` raises INV08.IDEMP.DEADLINE or
  INV08.IDEMP.CANCELLED.
* Retry classes: NEVER, IDEMPOTENT (retry any retryable Inv08Error),
  SAFE_READ (as IDEMPOTENT with more attempts).  Backoff = full jitter:
  uniform(0, min(cap, base * 2**attempt)); never sleeps past the budget.
* Admission: ``AdmissionQueue(max_depth, shed_at)``: depth < shed_at accepts
  all; shed_at <= depth < max_depth accepts only priority >= 1; depth ==
  max_depth sheds everything with INV08.BACKPRESSURE.SHED + retry_after.
"""
from __future__ import annotations

from collections import OrderedDict, deque

from .core import Inv08Error, digest
from .errors_catalog import error

RETRY_CLASSES = {"NEVER": 1, "IDEMPOTENT": 4, "SAFE_READ": 6}


def new_op_id(rng) -> str:
    return "op-%016x" % rng.getrandbits(64)


class IdempotencyStore:
    def __init__(self, *, clock, window: float = 600.0, max_entries: int = 10000) -> None:
        self.clock, self.window, self.max_entries = clock, window, max_entries
        self._e: OrderedDict = OrderedDict()   # key -> {digest, state, result, done_at}
        self.executions = 0

    def _evict(self) -> None:
        now = self.clock()
        for k in [k for k, v in self._e.items() if v["state"] == "done" and now - v["done_at"] >= self.window]:
            del self._e[k]

    def execute(self, principal: str, op_id: str, request: dict, fn):
        key, d = (principal, op_id), digest(request)
        self._evict()
        ent = self._e.get(key)
        if ent is not None:
            if ent["digest"] != d:
                raise error("INV08.IDEMP.KEY_REUSE", op_id, details={"principal": principal})
            if ent["state"] == "running":
                raise error("INV08.IDEMP.IN_PROGRESS", op_id)
            if "error" in ent:
                raise ent["error"]
            return ent["result"]
        if len(self._e) >= self.max_entries:
            raise error("INV08.IDEMP.STORE_FULL", f"{len(self._e)} entries")
        self._e[key] = ent = {"digest": d, "state": "running"}
        self.executions += 1
        try:
            res = fn()
        except Inv08Error as exc:
            if exc.retryable:
                del self._e[key]
            else:
                ent.update(state="done", error=exc, done_at=self.clock())
            raise
        except BaseException:
            del self._e[key]
            raise
        ent.update(state="done", result=res, done_at=self.clock())
        return res


class Budget:
    def __init__(self, total: float, clock, *, parent: "Budget | None" = None) -> None:
        if total < 0:
            raise ValueError("budget must be >= 0")
        self.clock, self.parent = clock, parent
        self.deadline = clock() + total
        if parent is not None:
            self.deadline = min(self.deadline, parent.deadline)
        self.cancelled = False

    def remaining(self) -> float:
        return max(0.0, self.deadline - self.clock())

    def child(self, fraction: float) -> "Budget":
        if not 0 < fraction <= 1:
            raise ValueError("fraction must be in (0, 1]")
        return Budget(self.remaining() * fraction, self.clock, parent=self)

    def cancel(self) -> None:
        self.cancelled = True

    def is_cancelled(self) -> bool:
        return self.cancelled or (self.parent is not None and self.parent.is_cancelled())

    def check(self) -> None:
        if self.is_cancelled():
            raise error("INV08.IDEMP.CANCELLED", "cancelled")
        if self.remaining() <= 0:
            raise error("INV08.IDEMP.DEADLINE", "budget exhausted")


def backoff(attempt: int, rng, *, base: float = 0.1, cap: float = 10.0) -> float:
    return rng.uniform(0, min(cap, base * (2 ** attempt)))


def retry(fn, *, klass: str, budget: Budget, rng, sleep, base: float = 0.1, cap: float = 10.0):
    """Call fn() under the retry class; ``sleep`` is injected (tests advance a fake clock)."""
    attempts = RETRY_CLASSES[klass]
    last = None
    for attempt in range(attempts):
        budget.check()
        try:
            return fn()
        except Inv08Error as exc:
            last = exc
            if not exc.retryable or attempt == attempts - 1:
                raise
            delay = backoff(attempt, rng, base=base, cap=cap)
            if delay >= budget.remaining():
                raise error("INV08.IDEMP.DEADLINE", "next retry would exceed budget", cause=exc) from exc
            sleep(delay)
    raise last  # pragma: no cover


class AdmissionQueue:
    def __init__(self, max_depth: int, shed_at: int, *, retry_after: float = 1.0) -> None:
        if not 0 < shed_at <= max_depth:
            raise ValueError("need 0 < shed_at <= max_depth")
        self.max_depth, self.shed_at, self.retry_after = max_depth, shed_at, retry_after
        self.q: deque = deque()
        self.stats = {"accepted": 0, "shed": 0}

    def offer(self, item, priority: int = 0) -> dict:
        depth = len(self.q)
        if depth >= self.max_depth or (depth >= self.shed_at and priority < 1):
            self.stats["shed"] += 1
            raise error("INV08.BACKPRESSURE.SHED", f"depth {depth}",
                        details={"retry_after": self.retry_after * (1 + depth - self.shed_at),
                                 "depth": depth})
        self.q.append(item)
        self.stats["accepted"] += 1
        return {"accepted": True, "depth": depth + 1}

    def take(self):
        return self.q.popleft() if self.q else None
