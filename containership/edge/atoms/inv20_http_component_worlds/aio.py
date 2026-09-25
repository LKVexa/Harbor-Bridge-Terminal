"""Asynchronous HTTP world (checklist components 3, 11 and 14).

Reference implementation of the async request lifecycle on ``asyncio``. The component
runtime (wasmtime/jco with wasi:http 0.2/0.3) supplies the real host bindings; this module is
the executable specification that the bindings are tested against, and is what the
dependency-independent suite exercises.

State machine (docs/spec/STATE_MACHINE.md):

    ACCEPTED -> DISPATCHED -> HEAD_SENT -> BODY_STREAMING -> TRAILERS_DONE -> RELEASED
         \\-> CANCELLED / FAILED (from any non-terminal state) -> RELEASED

Illegal transitions raise ``IllegalState``. Head is sent at most once, trailers resolve at most
once, and after a terminal error no body/trailer emission is possible.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
import random
import time
from typing import Awaitable, Callable, Dict, Generic, List, Optional, Protocol, Set, TypeVar

from .errors import Inv20Error
from .egress import DestinationPolicy, Destination
from .identity import CapabilityStore, Principal
from .protocol import Request, Response, Fields, IDEMPOTENT_METHODS
from .runtime import BodyTooLarge, CompletionAlreadyResolved

T = TypeVar("T")


class IllegalState(Inv20Error):
    code = "E_ILLEGAL_STATE"


class DeadlineExceeded(Inv20Error):
    code = "E_DEADLINE"


class Cancelled(Inv20Error):
    code = "E_CANCELLED"


class Overloaded(Inv20Error):
    code = "E_OVERLOADED"


class CircuitOpen(Inv20Error):
    code = "E_CIRCUIT_OPEN"


class UpstreamConnect(Inv20Error):
    code = "E_UPSTREAM_CONNECT"


class UpstreamReset(Inv20Error):
    code = "E_UPSTREAM_RESET"


class HandlerTrap(Inv20Error):
    code = "E_HANDLER_TRAP"


class NoOutgoing(Inv20Error):
    code = "E_NO_OUTGOING"


class NotReady(Inv20Error):
    code = "E_NOT_READY"


# --------------------------------------------------------------------------- deadlines
@dataclass(frozen=True)
class Deadline:
    """Absolute monotonic deadline; remaining budget propagates instead of restarting per hop."""

    at: float

    @classmethod
    def after(cls, ms: int, clock: Callable[[], float] = time.monotonic) -> "Deadline":
        if isinstance(ms, bool) or not isinstance(ms, int) or ms < 0:
            raise ValueError("deadline must be a non-negative integer number of ms")
        return cls(clock() + min(ms, 86_400_000) / 1000.0)

    def remaining(self, clock: Callable[[], float] = time.monotonic) -> float:
        return max(0.0, self.at - clock())

    def child(self, cap_ms: int, clock: Callable[[], float] = time.monotonic) -> "Deadline":
        """Per-stage timeout: min(stage cap, caller's remaining budget)."""
        return Deadline(min(self.at, clock() + max(0, cap_ms) / 1000.0))

    def expired(self, clock: Callable[[], float] = time.monotonic) -> bool:
        return self.remaining(clock) <= 0.0


async def within(dl: Deadline, aw: Awaitable[T]) -> T:
    rem = dl.remaining()
    if rem <= 0:
        if asyncio.iscoroutine(aw):
            aw.close()
        raise DeadlineExceeded("deadline already exhausted")
    try:
        return await asyncio.wait_for(aw, rem)
    except asyncio.TimeoutError:
        raise DeadlineExceeded("stage timed out") from None


# --------------------------------------------------------------------------- state machine
class RState(str, Enum):
    ACCEPTED = "accepted"
    DISPATCHED = "dispatched"
    HEAD_SENT = "head_sent"
    BODY_STREAMING = "body_streaming"
    TRAILERS_DONE = "trailers_done"
    CANCELLED = "cancelled"
    FAILED = "failed"
    RELEASED = "released"


TERMINAL = {RState.CANCELLED, RState.FAILED, RState.RELEASED}
LEGAL: Dict[RState, Set[RState]] = {
    RState.ACCEPTED: {RState.DISPATCHED, RState.CANCELLED, RState.FAILED},
    RState.DISPATCHED: {RState.HEAD_SENT, RState.CANCELLED, RState.FAILED},
    RState.HEAD_SENT: {RState.BODY_STREAMING, RState.TRAILERS_DONE, RState.CANCELLED, RState.FAILED},
    RState.BODY_STREAMING: {RState.TRAILERS_DONE, RState.CANCELLED, RState.FAILED},
    RState.TRAILERS_DONE: {RState.RELEASED},
    RState.CANCELLED: {RState.RELEASED},
    RState.FAILED: {RState.RELEASED},
    RState.RELEASED: set(),
}


class Lifecycle:
    def __init__(self) -> None:
        self.state = RState.ACCEPTED
        self.history: List[RState] = [self.state]
        self.error: Optional[Inv20Error] = None
        self._releasers: List[Callable[[], None]] = []
        self.released_count = 0

    def to(self, new: RState) -> None:
        if new not in LEGAL[self.state]:
            raise IllegalState(f"{self.state.value}->{new.value}")
        self.state = new
        self.history.append(new)

    def fail(self, err: Inv20Error, cancelled: bool = False) -> None:
        """First terminal cause wins (cancellation precedence documented in STATE_MACHINE.md)."""
        if self.state in TERMINAL or self.state == RState.TRAILERS_DONE:
            return
        self.error = err
        self.to(RState.CANCELLED if cancelled else RState.FAILED)

    def on_release(self, fn: Callable[[], None]) -> None:
        self._releasers.append(fn)

    def release(self) -> None:
        """Idempotent resource release."""
        if self.state == RState.RELEASED:
            return
        if self.state not in (RState.TRAILERS_DONE, RState.CANCELLED, RState.FAILED):
            self.fail(Cancelled("released before completion"), cancelled=True)
        for fn in reversed(self._releasers):
            try:
                fn()
            except Exception:
                pass
        self._releasers.clear()
        self.released_count += 1
        self.to(RState.RELEASED)


# --------------------------------------------------------------------------- streams
_EOF = object()


class AsyncBodyStream:
    """Bounded async body stream: producers await capacity; no whole-body buffering."""

    def __init__(self, limit: int = 1 << 20, max_chunks: int = 8) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        if isinstance(max_chunks, bool) or not isinstance(max_chunks, int) or max_chunks < 1:
            raise ValueError("max_chunks must be >= 1")
        self.limit = limit
        self._q: asyncio.Queue = asyncio.Queue(maxsize=max_chunks)
        self.total = 0
        self.peak = 0
        self.closed = False
        self.aborted: Optional[Inv20Error] = None

    async def write(self, chunk: bytes, deadline: Optional[Deadline] = None) -> None:
        if self.closed or self.aborted:
            raise IllegalState("write after close/abort")
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise TypeError("body chunks are bytes-like")
        data = bytes(chunk)
        if self.total + len(data) > self.limit:
            err = BodyTooLarge(f"body would exceed {self.limit} bytes")
            self.abort(err)
            raise err
        self.total += len(data)
        put = self._q.put(data)
        await (within(deadline, put) if deadline else put)
        self.peak = max(self.peak, self._q.qsize())

    async def close(self) -> None:
        if not self.closed and not self.aborted:
            self.closed = True
            await self._q.put(_EOF)

    def abort(self, err: Inv20Error) -> None:
        if self.aborted:
            return
        self.aborted = err
        while not self._q.empty():
            self._q.get_nowait()
        try:
            self._q.put_nowait(_EOF)
        except asyncio.QueueFull:  # pragma: no cover - queue just drained
            pass

    async def read(self, deadline: Optional[Deadline] = None) -> Optional[bytes]:
        """Return next chunk, or None at EOF. Raises the abort cause if the stream was aborted."""
        if self.aborted:
            raise self.aborted
        get = self._q.get()
        item = await (within(deadline, get) if deadline else get)
        if self.aborted:
            raise self.aborted
        if item is _EOF:
            self._q.put_nowait(_EOF) if self._q.empty() else None
            return None
        return item

    @property
    def buffered(self) -> int:
        return self._q.qsize()


class AsyncCompletion(Generic[T]):
    """Exactly-once future used for response head and trailers."""

    def __init__(self) -> None:
        self._fut: asyncio.Future = asyncio.get_event_loop().create_future()

    def resolve(self, value: T) -> None:
        if self._fut.done():
            raise CompletionAlreadyResolved("completion already resolved")
        self._fut.set_result(value)

    def fail(self, err: BaseException) -> None:
        if not self._fut.done():
            self._fut.set_exception(err)
            self._fut.exception()   # mark observed: an unread trailer failure is not a leak warning

    @property
    def done(self) -> bool:
        return self._fut.done()

    async def wait(self, deadline: Optional[Deadline] = None) -> T:
        return await (within(deadline, asyncio.shield(self._fut)) if deadline else self._fut)


# --------------------------------------------------------------------------- retry / breaker / admission
SAFE_RETRY_CODES = frozenset({"E_DNS_FAILURE", "E_UPSTREAM_CONNECT", "E_CIRCUIT_OPEN", "E_OVERLOADED"})


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_ms: int = 50
    max_backoff_ms: int = 2000
    budget_ms: int = 5000
    retry_after_cap_ms: int = 5000
    rng: random.Random = field(default_factory=lambda: random.Random(0))

    def classify(self, method: str, err: Inv20Error, idempotency_key: bool = False, head_committed: bool = False) -> bool:
        if head_committed:
            return False                           # partial response: never replay
        if err.code not in SAFE_RETRY_CODES:
            return False
        if method in IDEMPOTENT_METHODS or idempotency_key:
            return True
        return err.code == "E_UPSTREAM_CONNECT"    # connect never reached peer: safe for any method

    def backoff_ms(self, attempt: int, retry_after_ms: Optional[int] = None) -> int:
        exp = min(self.max_backoff_ms, self.base_ms * (2 ** max(0, attempt - 1)))
        jittered = self.rng.randint(exp // 2, exp)            # bounded "equal jitter"
        if retry_after_ms is not None:
            jittered = max(jittered, min(max(0, retry_after_ms), self.retry_after_cap_ms))
        return jittered


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_after_s: float = 10.0
    clock: Callable[[], float] = time.monotonic
    state: BreakerState = BreakerState.CLOSED
    failures: int = 0
    opened_at: float = 0.0

    def allow(self) -> bool:
        if self.state is BreakerState.OPEN and self.clock() - self.opened_at >= self.reset_after_s:
            self.state = BreakerState.HALF_OPEN
        return self.state is not BreakerState.OPEN

    def success(self) -> None:
        self.state, self.failures = BreakerState.CLOSED, 0

    def failure(self) -> None:
        self.failures += 1
        if self.state is BreakerState.HALF_OPEN or self.failures >= self.failure_threshold:
            self.state, self.opened_at = BreakerState.OPEN, self.clock()


class AdmissionController:
    """Global + per-tenant + per-workload concurrency with bounded wait queue (fair rejection)."""

    def __init__(self, max_concurrency: int = 64, per_tenant: int = 16, per_workload: int = 16,
                 queue_depth: int = 128) -> None:
        self.max, self.per_tenant, self.per_workload, self.queue_depth = max_concurrency, per_tenant, per_workload, queue_depth
        self.active = 0
        self.by_tenant: Dict[str, int] = {}
        self.by_workload: Dict[str, int] = {}
        self.waiting = 0
        self.rejections: Dict[str, int] = {}
        self._cond = asyncio.Condition()

    def _can(self, t: str, w: str) -> bool:
        return (self.active < self.max and self.by_tenant.get(t, 0) < self.per_tenant
                and self.by_workload.get(w, 0) < self.per_workload)

    def _reject(self, reason: str) -> Overloaded:
        self.rejections[reason] = self.rejections.get(reason, 0) + 1
        return Overloaded(reason)

    async def acquire(self, tenant: str, workload: str, deadline: Optional[Deadline] = None) -> None:
        key = f"{tenant}/{workload}"
        # A tenant already at its own cap is shed immediately: it cannot occupy shared queue slots.
        if self.by_tenant.get(tenant, 0) >= self.per_tenant:
            raise self._reject("tenant_limit")
        async with self._cond:
            if self._can(tenant, key):
                self._take(tenant, key)
                return
            if self.waiting >= self.queue_depth:
                raise self._reject("queue_full")
            self.waiting += 1
            try:
                pred = lambda: self._can(tenant, key)
                await (within(deadline, self._cond.wait_for(pred)) if deadline else self._cond.wait_for(pred))
                self._take(tenant, key)
            except DeadlineExceeded:
                raise self._reject("queue_timeout") from None
            finally:
                self.waiting -= 1

    def _take(self, t: str, w: str) -> None:
        self.active += 1
        self.by_tenant[t] = self.by_tenant.get(t, 0) + 1
        self.by_workload[w] = self.by_workload.get(w, 0) + 1

    async def release(self, tenant: str, workload: str) -> None:
        key = f"{tenant}/{workload}"
        async with self._cond:
            self.active -= 1
            self.by_tenant[tenant] -= 1
            self.by_workload[key] -= 1
            self._cond.notify_all()


# --------------------------------------------------------------------------- transport + world
class Transport(Protocol):
    async def send(self, dest: Destination, request: Request, deadline: Deadline) -> Response: ...


Handler = Callable[[Request, "ResponseOutparam"], Awaitable[None]]


class ResponseOutparam:
    """wasi:http response-outparam analogue: set exactly once, then stream body, then trailers."""

    def __init__(self, lc: Lifecycle, body_limit: int, max_chunks: int) -> None:
        self._lc = lc
        self.head: Optional[Response] = None
        self.body = AsyncBodyStream(body_limit, max_chunks)
        self.trailers: AsyncCompletion = AsyncCompletion()
        self.head_ready = asyncio.Event()
        lc.on_release(lambda: self.body.abort(Cancelled("released")) if not self.body.closed else None)

    def set(self, response: Response) -> None:
        if self.head is not None:
            raise IllegalState("response head already sent")
        if self._lc.state in TERMINAL:
            raise IllegalState("response after terminal error")
        self._lc.to(RState.HEAD_SENT)
        self.head = response
        self.head_ready.set()

    async def write(self, chunk: bytes) -> None:
        if self._lc.state in TERMINAL:
            raise IllegalState("body after terminal error")
        if self._lc.state == RState.HEAD_SENT:
            self._lc.to(RState.BODY_STREAMING)
        elif self._lc.state != RState.BODY_STREAMING:
            raise IllegalState(f"body in state {self._lc.state.value}")
        await self.body.write(chunk)

    async def finish(self, trailers: Optional[Fields] = None) -> None:
        if self._lc.state in TERMINAL:
            raise IllegalState("trailers after terminal error")
        self.trailers.resolve(trailers)
        await self.body.close()
        self._lc.to(RState.TRAILERS_DONE)


@dataclass
class AsyncHttpWorld:
    name: str
    handler: Optional[Handler] = None
    outgoing: bool = False
    policy: Optional[DestinationPolicy] = None
    capabilities: Optional[CapabilityStore] = None
    transport: Optional[Transport] = None
    admission: Optional[AdmissionController] = None
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    breakers: Dict[str, CircuitBreaker] = field(default_factory=dict)
    body_limit: int = 1 << 20
    max_chunks: int = 8
    max_fanout: int = 8
    ready: Callable[[], bool] = lambda: True
    on_event: Callable[[str, dict], None] = lambda name, data: None
    live: Set[Lifecycle] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.outgoing and (self.policy is None or self.capabilities is None or self.transport is None):
            raise ValueError("outgoing HTTP requires policy, capability store and transport")
        if not self.outgoing and self.policy is not None and self.policy.allowed_authorities:
            raise ValueError("allow-list without outgoing capability import")

    def export_handler(self, fn: Handler) -> None:
        if self.handler is not None:
            raise ValueError(f"world {self.name} already exports a handler")
        if not callable(fn):
            raise TypeError("handler must be callable")
        self.handler = fn

    async def handle(self, request: Request, principal: Principal, deadline: Deadline) -> ResponseOutparam:
        """Dispatch one incoming request. Returns the outparam once the head is committed."""
        if self.handler is None:
            raise IllegalState(f"world {self.name} exports no handler")
        if not self.ready():
            raise NotReady(self.name)
        if self.capabilities and self.capabilities.is_quarantined(principal.tenant, principal.workload):
            from .identity import Quarantined
            raise Quarantined(principal.id)
        adm = self.admission
        if adm:
            await adm.acquire(principal.tenant, principal.workload, deadline)
        lc = Lifecycle()
        self.live.add(lc)
        out = ResponseOutparam(lc, self.body_limit, self.max_chunks)
        lc.on_release(lambda: self.live.discard(lc))
        if adm:
            lc.on_release(lambda: asyncio.ensure_future(adm.release(principal.tenant, principal.workload)))
        lc.to(RState.DISPATCHED)
        task = asyncio.ensure_future(self.handler(request, out))

        def _done(t: asyncio.Task) -> None:
            if t.cancelled():
                lc.fail(Cancelled("handler cancelled"), cancelled=True)
            elif t.exception() is not None:
                exc = t.exception()
                err = exc if isinstance(exc, Inv20Error) else HandlerTrap(type(exc).__name__)
                lc.fail(err)
                out.body.abort(err)
                out.trailers.fail(err)
            if lc.state in (RState.TRAILERS_DONE, RState.CANCELLED, RState.FAILED):
                lc.release()
        task.add_done_callback(_done)
        lc.on_release(lambda: task.cancel() if not task.done() else None)
        try:
            if out.head is None:
                head_wait = asyncio.ensure_future(out.head_ready.wait())
                try:
                    await within(deadline, asyncio.wait({head_wait, task}, return_when=asyncio.FIRST_COMPLETED))
                finally:
                    head_wait.cancel()
            if out.head is None:
                # Handler finished/trapped before sending a head.
                if lc.error is None:
                    lc.fail(HandlerTrap("handler returned without a response"))
                    lc.release()
                raise lc.error  # type: ignore[misc]
        except (DeadlineExceeded, asyncio.CancelledError) as exc:
            lc.fail(exc if isinstance(exc, Inv20Error) else Cancelled("peer disconnect"), cancelled=True)
            task.cancel()
            lc.release()
            raise
        self.on_event("request.head", {"world": self.name, "status": out.head.status})
        return out

    def _breaker(self, key: str) -> CircuitBreaker:
        return self.breakers.setdefault(key, CircuitBreaker())

    async def fetch(self, principal: Principal, cap_token: str, request: Request, deadline: Deadline,
                    idempotency_key: Optional[str] = None) -> Response:
        """Outgoing HTTP: requires the import, an authenticated principal and a valid capability."""
        if not self.outgoing:
            raise NoOutgoing(self.name)
        assert self.policy and self.capabilities and self.transport  # guarded in __post_init__
        cap = self.capabilities.resolve(cap_token, principal)
        if (request.authority.host, request.authority.port) not in cap.authorities:
            from .egress import EgressPolicyDenied
            self.on_event("egress.denied", {"reason": "capability_scope"})
            raise EgressPolicyDenied("capability_scope")
        dest = self.policy.authorize(request.scheme, request.authority.render())
        key = dest.authority.render()
        attempt, started = 0, time.monotonic()
        while True:
            attempt += 1
            br = self._breaker(key)
            if not br.allow():
                raise CircuitOpen(key)
            try:
                resp = await within(deadline, self.transport.send(dest, request, deadline))
                br.success()
                return resp
            except asyncio.CancelledError:
                raise
            except Inv20Error as err:
                if err.category.value == "upstream_error":
                    br.failure()
                spent = (time.monotonic() - started) * 1000
                if (attempt >= self.retry.max_attempts or not self.retry.classify(
                        request.method, err, idempotency_key is not None) or spent >= self.retry.budget_ms):
                    raise
                pause = self.retry.backoff_ms(attempt) / 1000
                if pause >= deadline.remaining():
                    raise DeadlineExceeded("deadline would expire during backoff") from None
                self.on_event("egress.retry", {"attempt": attempt, "code": err.code})
                await asyncio.sleep(pause)
                self.policy.invalidate(dest.authority.host)
                dest = self.policy.authorize(request.scheme, request.authority.render())

    async def fan_out(self, calls: List[Callable[[], Awaitable[T]]]) -> List[T]:
        if len(calls) > self.max_fanout:
            raise Overloaded("fan-out limit")
        return list(await asyncio.gather(*(c() for c in calls)))
