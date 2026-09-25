"""MC-026 - Retry, backoff and idempotency layer.

* Operation classes: read_only / idempotent_mutation / non_idempotent_mutation /
  transaction_phase.  Only read_only and idempotent_mutation (with a key) and
  transaction_phase (keyed by txn id) may be retried automatically.
* End-to-end deadline; per-attempt timeout = min(attempt cap, remaining budget).
* Full-jitter exponential backoff (seeded RNG for reproducible tests).
* Only codes marked retryable in GAP03-ERR/1 are retried; retry-after respected.
* Lost responses: ``outcome_probe`` is consulted before re-issuing a mutation.
* Retry budget per dependency (token ratio) prevents overload amplification.
* Poison detection: a key failing terminally ``poison_after`` times is quarantined.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
import threading
import time
from collections import OrderedDict

from .errors import CODES, SchedulerError, classify

OP_CLASSES = {"read_only": True, "idempotent_mutation": True, "transaction_phase": True, "non_idempotent_mutation": False}


@dataclass
class Policy:
    max_attempts: int = 4
    base_s: float = 0.05
    cap_s: float = 2.0
    attempt_timeout_s: float = 1.0
    budget_ratio: float = 0.2   # retries may be at most 20% of first attempts
    budget_min: int = 10
    poison_after: int = 3


class RetryBudget:
    def __init__(self, ratio: float, minimum: int):
        self.ratio, self.minimum, self.requests, self.retries = ratio, minimum, 0, 0
        self._lock = threading.Lock()

    def note_request(self):
        with self._lock:
            self.requests += 1

    def try_spend(self) -> bool:
        with self._lock:
            if self.retries < max(self.minimum, self.requests * self.ratio):
                self.retries += 1
                return True
            return False


class DedupStore:
    """Idempotency outcome store (bounded LRU, window >= max replay window)."""

    def __init__(self, max_entries: int = 100_000, window_s: float = 86400, clock=time.time):
        self._d: "OrderedDict[str, tuple[float, object]]" = OrderedDict()
        self.max_entries, self.window_s, self.clock = max_entries, window_s, clock
        self.hits = 0
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._d.get(key)
            if item and self.clock() - item[0] <= self.window_s:
                self.hits += 1
                return True, item[1]
            return False, None

    def put(self, key, outcome):
        with self._lock:
            self._d[key] = (self.clock(), outcome)
            self._d.move_to_end(key)
            while len(self._d) > self.max_entries:
                self._d.popitem(last=False)


class Retrier:
    def __init__(self, dependency: str, policy: Policy | None = None, *, seed: int | None = None, clock=time.monotonic,
                 sleep=time.sleep, metrics=None, dedup: DedupStore | None = None):
        self.dep, self.p = dependency, policy or Policy()
        self.rng = random.Random(seed)
        self.clock, self.sleep, self.metrics = clock, sleep, metrics
        self.budget = RetryBudget(self.p.budget_ratio, self.p.budget_min)
        self.dedup = dedup or DedupStore()
        self.poison: dict[str, int] = {}
        self.quarantined: set[str] = set()
        self.trace: list[dict] = []

    def backoff(self, attempt: int) -> float:
        return self.rng.uniform(0, min(self.p.cap_s, self.p.base_s * (2 ** attempt)))

    def run(self, fn, *, op_class: str, deadline_s: float, idempotency_key: str | None = None, outcome_probe=None):
        if op_class not in OP_CLASSES:
            raise SchedulerError("INVALID_ARGUMENT", "unknown operation class")
        if op_class in ("idempotent_mutation", "transaction_phase") and not idempotency_key:
            raise SchedulerError("INVALID_ARGUMENT", "mutation requires an idempotency key")
        if idempotency_key in self.quarantined:
            raise SchedulerError("CONFLICT", "operation quarantined as poison")
        if idempotency_key:
            hit, outcome = self.dedup.get(idempotency_key)
            if hit:
                if self.metrics:
                    self.metrics.inc("gap03_idempotent_replays_total")
                self.trace.append({"attempt": 0, "result": "dedup_hit"})
                return outcome
        retry_ok = OP_CLASSES[op_class]
        start = self.clock()
        self.budget.note_request()
        attempt, last = 0, None
        while True:
            remaining = deadline_s - (self.clock() - start)
            if remaining <= 0:
                raise SchedulerError("DEADLINE_EXCEEDED", "end-to-end deadline exhausted", cause=last)
            timeout = min(self.p.attempt_timeout_s, remaining)
            try:
                result = fn(timeout=timeout, attempt=attempt)
                if idempotency_key:
                    self.dedup.put(idempotency_key, result)
                self.trace.append({"attempt": attempt, "result": "ok"})
                return result
            except Exception as exc:  # noqa: BLE001 - classified below
                err = classify(exc)
                last = err
                self.trace.append({"attempt": attempt, "result": err.code})
                if self.metrics:
                    self.metrics.inc("gap03_retry_attempts_total", dependency=self.dep, code=err.code)
                if not CODES[err.code].retryable or not retry_ok:
                    if idempotency_key:
                        self.poison[idempotency_key] = self.poison.get(idempotency_key, 0) + 1
                        if self.poison[idempotency_key] >= self.p.poison_after:
                            self.quarantined.add(idempotency_key)
                    raise err
                if outcome_probe is not None and op_class != "read_only":
                    known, value = outcome_probe()
                    if known:  # server already applied it - do not duplicate
                        if idempotency_key:
                            self.dedup.put(idempotency_key, value)
                        return value
                attempt += 1
                if attempt >= self.p.max_attempts:
                    raise SchedulerError("DEADLINE_EXCEEDED" if err.code == "DEADLINE_EXCEEDED" else err.code,
                                         "retry attempts exhausted", cause=err)
                if not self.budget.try_spend():
                    if self.metrics:
                        self.metrics.inc("gap03_retry_budget_exhausted_total", dependency=self.dep)
                    raise SchedulerError("OVERLOADED", "retry budget exhausted", cause=err)
                delay = max(self.backoff(attempt), float(err.detail.get("retry_after_s") or 0))
                self.sleep(min(delay, max(0.0, deadline_s - (self.clock() - start))))
