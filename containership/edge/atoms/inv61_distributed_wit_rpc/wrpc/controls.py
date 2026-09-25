"""M07/M10/M11/M19 - authorization, idempotency/retry/cancellation, admission,
circuit breaking, and fenced leases for duplicate-execution prevention."""
from __future__ import annotations

from dataclasses import dataclass, field
import fnmatch
import random
import threading
import time


# ------------------------------------------------------------------ M07 authz
@dataclass(frozen=True)
class Grant:
    tenant: str
    peer: str            # exact peer id or glob
    interface: str       # exact or glob
    function: str        # exact or glob
    not_after: float = float("inf")


class Authorizer:
    """Default-deny capability table. A decision is (allowed, rule_index|None, reason).

    Precedence: explicit deny beats allow; among allows the first match wins.
    Globs never cross tenants — tenant must match exactly.
    """

    def __init__(self, grants=(), denies=()):
        self.grants = list(grants)
        self.denies = list(denies)
        self._lock = threading.Lock()

    def grant(self, g: Grant) -> None:
        with self._lock:
            self.grants.append(g)

    def revoke(self, pred) -> int:
        with self._lock:
            before = len(self.grants)
            self.grants = [g for g in self.grants if not pred(g)]
            return before - len(self.grants)

    @staticmethod
    def _match(g: Grant, tenant, peer, iface, fn, now) -> bool:
        return (g.tenant == tenant and fnmatch.fnmatchcase(peer, g.peer)
                and fnmatch.fnmatchcase(iface, g.interface) and fnmatch.fnmatchcase(fn, g.function)
                and now < g.not_after)

    def decide(self, tenant: str, peer: str, iface: str, fn: str, now: float | None = None):
        now = time.time() if now is None else now
        with self._lock:
            for i, d in enumerate(self.denies):
                if self._match(d, tenant, peer, iface, fn, now):
                    return False, f"deny[{i}]", "explicit-deny"
            for i, g in enumerate(self.grants):
                if self._match(g, tenant, peer, iface, fn, now):
                    return True, f"grant[{i}]", "granted"
        return False, None, "default-deny"


# ------------------------------------------------------ M10 idempotency/retry
class IdempotencyCache:
    """First *final* outcome per (tenant, request_id), bound to the call it answered.

    * ``fn`` returns ``(outcome, final)``. Only final outcomes are remembered; a
      transient refusal (admission ``overloaded``, argument decode failure before any
      side effect) is returned but NOT cached, so a retry with the same id really runs.
      (Assessor finding: v4.3.0-rc cached ``overloaded`` for the whole TTL.)
    * ``call_digest`` identifies interface+function+fingerprint+argument bytes. Reusing a
      request id for a different call returns ``idempotency-conflict`` instead of the
      other call's result bytes.
    * Durability: the outcome is journaled BEFORE it is published to waiters/callers.
      A crash after the callee ran but before the journal write can still re-execute on
      restart; closing that window needs the callee's own transactional outbox.
    * Capacity: when full, the oldest entry is evicted (counted in ``evictions``) rather
      than refusing all new work; the dedup window is min(TTL, capacity).
    """

    def __init__(self, ttl_s: float = 600.0, max_entries: int = 100_000, journal=None):
        from collections import OrderedDict
        self.ttl, self.max = ttl_s, max_entries
        self._done: "OrderedDict" = OrderedDict()
        self._inflight: dict = {}
        self._lock = threading.Lock()
        self.journal = journal
        self.evictions = 0
        self.journal_failures = 0
        if journal is not None:
            for key, (ts, outcome, digest) in journal.replay().items():
                self._done[key] = (ts, outcome, digest)

    def run(self, key: tuple, fn, now: float | None = None, call_digest: str = ""):
        now = time.time() if now is None else now
        while True:
            with self._lock:
                hit = self._done.get(key)
                if hit and now - hit[0] <= self.ttl:
                    if hit[2] != call_digest:
                        return {"error": "idempotency-conflict"}, True
                    return hit[1], True
                ev = self._inflight.get(key)
                if ev is None:
                    ev = self._inflight[key] = (threading.Event(), call_digest)
                    break
            ev[0].wait()
            with self._lock:
                if key not in self._done:      # original was transient: this waiter runs it itself
                    continue
                hit = self._done[key]
                return ({"error": "idempotency-conflict"} if hit[2] != call_digest else hit[1]), True
        try:
            outcome, final = fn()
        except BaseException:
            outcome, final = {"error": "callee-trap"}, True
        try:
            if final and self.journal is not None:
                try:
                    self.journal.append(key, now, outcome, call_digest)
                except Exception:
                    # the callee already ran: still answer and remember in memory, but record
                    # that this outcome would not survive a restart
                    self.journal_failures += 1
            with self._lock:
                if final:
                    self._done[key] = (now, outcome, call_digest)
                    self._done.move_to_end(key)
                    while len(self._done) > self.max:
                        self._done.popitem(last=False)
                        self.evictions += 1
        finally:
            with self._lock:
                ev = self._inflight.pop(key)
            ev[0].set()
        return outcome, False


RETRYABLE = frozenset({"overloaded", "unavailable", "circuit-open", "transport"})


@dataclass
class RetryPolicy:
    """Exponential backoff with full jitter, bounded attempts, a shared retry budget,
    and never beyond the call deadline. Only idempotent calls are retried."""

    max_attempts: int = 4
    base_s: float = 0.05
    cap_s: float = 2.0
    budget_ratio: float = 0.2      # retries may add at most 20% load
    _calls: int = 0
    _retries: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def backoff(self, attempt: int, rng=random.random) -> float:
        return rng() * min(self.cap_s, self.base_s * (2 ** attempt))

    def call(self, fn, deadline: float, idempotent: bool, clock=time.time, sleep=time.sleep):
        with self._lock:
            self._calls += 1
        attempt = 0
        while True:
            res = fn(attempt)
            err = res.get("error") if isinstance(res, dict) else None
            if err not in RETRYABLE or not idempotent or attempt + 1 >= self.max_attempts:
                return res
            with self._lock:
                if self._retries + 1 > self.budget_ratio * self._calls + 1:
                    return dict(res, retry="budget-exhausted")
                self._retries += 1
            delay = self.backoff(attempt)
            hint = res.get("retry_after_ms") if isinstance(res, dict) else None
            if isinstance(hint, (int, float)) and not isinstance(hint, bool) and 0 < hint <= 60_000:
                delay = max(delay, hint / 1000.0)      # honour the server's backpressure hint
            if clock() + delay >= deadline:
                return {"error": "deadline-exceeded"}
            sleep(delay)
            attempt += 1


class CancelToken:
    def __init__(self):
        self._ev = threading.Event()
        self.reason = None

    def cancel(self, reason: str = "cancelled"):
        self.reason = reason
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()


# ----------------------------------------------------- M11 admission/breaker
class Admission:
    """Bounded concurrency + bounded wait queue, per tenant. Rejects instead of queueing
    unboundedly; the rejection carries retry_after so callers back off (backpressure)."""

    def __init__(self, max_inflight: int = 64, max_queue: int = 128, per_tenant: int = 32):
        self.max_inflight, self.max_queue, self.per_tenant = max_inflight, max_queue, per_tenant
        self.inflight = 0
        self.waiting = 0
        self.by_tenant: dict = {}
        self._cv = threading.Condition()

    def acquire(self, tenant: str, timeout_s: float) -> bool:
        with self._cv:
            if self.by_tenant.get(tenant, 0) >= self.per_tenant:
                return False
            if self.inflight >= self.max_inflight:
                if self.waiting >= self.max_queue:
                    return False
                self.waiting += 1
                try:
                    ok = self._cv.wait_for(lambda: self.inflight < self.max_inflight, timeout=max(0.0, timeout_s))
                finally:
                    self.waiting -= 1
                if not ok or self.by_tenant.get(tenant, 0) >= self.per_tenant:
                    return False
            self.inflight += 1
            self.by_tenant[tenant] = self.by_tenant.get(tenant, 0) + 1
            return True

    def release(self, tenant: str) -> None:
        with self._cv:
            self.inflight -= 1
            self.by_tenant[tenant] -= 1
            if not self.by_tenant[tenant]:
                del self.by_tenant[tenant]
            self._cv.notify()


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive failures; open -> half-open after
    ``cooldown_s``; half-open admits one probe; success closes, failure re-opens."""

    def __init__(self, threshold: int = 5, cooldown_s: float = 5.0, clock=time.monotonic):
        self.threshold, self.cooldown, self.clock = threshold, cooldown_s, clock
        self.state, self.failures, self.opened_at, self.probe = "closed", 0, 0.0, False
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self.state == "open" and self.clock() - self.opened_at >= self.cooldown:
                self.state, self.probe = "half-open", False
            if self.state == "closed":
                return True
            if self.state == "half-open" and not self.probe:
                self.probe = True
                return True
            return False

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self.state, self.failures = "closed", 0
            else:
                self.failures += 1
                if self.state == "half-open" or self.failures >= self.threshold:
                    self.state, self.opened_at = "open", self.clock()


# ------------------------------------------------------- M19 fenced leases
class LeaseTable:
    """Ownership of a mutable key via expiring leases with monotonically increasing
    fencing tokens. A write carrying a stale token is refused, so a paused old
    owner that wakes after failover cannot double-apply."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._leases: dict = {}
        self._fence: dict = {}
        self._frozen: set = set()
        self._lock = threading.Lock()

    def acquire(self, key: str, owner: str, ttl_s: float):
        with self._lock:
            if key in self._frozen:
                return None
            cur = self._leases.get(key)
            now = self.clock()
            if cur and cur[0] != owner and cur[1] > now:
                return None
            token = self._fence.get(key, 0) + (0 if cur and cur[0] == owner and cur[1] > now else 1)
            self._fence[key] = token
            self._leases[key] = (owner, now + ttl_s, token)
            return token

    def check(self, key: str, token: int) -> bool:
        with self._lock:
            cur = self._leases.get(key)
            return bool(cur) and key not in self._frozen and cur[2] == token and cur[1] > self.clock()

    def freeze(self, key: str) -> None:        # quarantine: no owner may write
        with self._lock:
            self._frozen.add(key)

    def thaw(self, key: str) -> None:
        with self._lock:
            self._frozen.discard(key)
