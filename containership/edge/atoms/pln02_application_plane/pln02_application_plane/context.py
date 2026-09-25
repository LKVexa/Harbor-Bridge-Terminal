"""MC-13 / MC-26 - Typed request context, deadlines, cancellation, idempotency.

``RequestContext`` carries tenant, environment, site, principal, deadline,
correlation id and idempotency key explicitly. Nothing in the plane reads
ambient/global request state.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import re
import threading
import time
import uuid
from typing import Any, Callable

from .errors import PlaneError

_SCOPE_ID = re.compile(r"^[a-z0-9][a-z0-9._\-]{0,62}$")
MAX_DEADLINE_SECONDS = 60.0
MAX_IDEMPOTENCY_ENTRIES = 10_000


def _scope(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SCOPE_ID.fullmatch(value):
        raise PlaneError(f"{field_name} is not a valid scope identifier", code="INVALID_APPLICATION",
                         details={"field": field_name})
    return value


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class RequestContext:
    tenant: str
    environment: str
    site: str
    principal: str = "anonymous"
    deadline: float = field(default_factory=lambda: time.monotonic() + 5.0)
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    idempotency_key: str | None = None
    cancellation: CancellationToken = field(default_factory=CancellationToken, compare=False)

    def __post_init__(self) -> None:
        _scope(self.tenant, "tenant")
        _scope(self.environment, "environment")
        _scope(self.site, "site")
        if self.deadline - time.monotonic() > MAX_DEADLINE_SECONDS:
            raise PlaneError("deadline exceeds plane maximum", code="INVALID_APPLICATION",
                             details={"field": "deadline", "limit": MAX_DEADLINE_SECONDS})
        if self.idempotency_key is not None and (not isinstance(self.idempotency_key, str)
                                                 or not 8 <= len(self.idempotency_key) <= 128):
            raise PlaneError("idempotency key must be 8-128 characters", code="INVALID_APPLICATION",
                             details={"field": "idempotency_key"})

    @classmethod
    def create(cls, tenant: str, environment: str, site: str, *, timeout: float = 5.0, **kw: Any) -> "RequestContext":
        return cls(tenant=tenant, environment=environment, site=site, deadline=time.monotonic() + timeout, **kw)

    def remaining(self) -> float:
        return self.deadline - time.monotonic()

    def checkpoint(self) -> None:
        """Raise if the operation was cancelled or its deadline passed."""
        if self.cancellation.cancelled:
            raise PlaneError("operation cancelled", code="CANCELLED")
        if self.remaining() <= 0:
            raise PlaneError("deadline exceeded", code="DEADLINE_EXCEEDED")

    def scope_key(self) -> tuple[str, str, str]:
        return (self.tenant, self.environment, self.site)

    def labels(self) -> dict[str, str]:
        """Stable, low-cardinality telemetry identifiers (no principal, no key)."""
        return {"tenant": self.tenant, "environment": self.environment, "site": self.site}


class IdempotencyCache:
    """Bounded LRU mapping (scope, key) -> (request digest, result).

    Replaying the same key with the same request digest returns the stored
    result; replaying it with a different digest is an ``IDEMPOTENCY_CONFLICT``.
    """

    def __init__(self, capacity: int = MAX_IDEMPOTENCY_ENTRIES) -> None:
        self._capacity = capacity
        self._items: OrderedDict[tuple, tuple[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def run(self, ctx: RequestContext, request_digest: str, fn: Callable[[], Any]) -> Any:
        if ctx.idempotency_key is None:
            return fn()
        key = (*ctx.scope_key(), ctx.idempotency_key)
        with self._lock:
            hit = self._items.get(key)
            if hit is not None:
                if hit[0] != request_digest:
                    raise PlaneError("idempotency key reused with a different request", code="IDEMPOTENCY_CONFLICT")
                self._items.move_to_end(key)
                return hit[1]
        result = fn()
        with self._lock:
            self._items[key] = (request_digest, result)
            self._items.move_to_end(key)
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)
        return result

    def __len__(self) -> int:
        return len(self._items)


def retry_safe(fn: Callable[[], Any], ctx: RequestContext, *, attempts: int = 3, base_delay: float = 0.01,
               retry_codes: frozenset[str] = frozenset({"CATALOGUE_UNAVAILABLE", "CIRCUIT_OPEN"})) -> Any:
    """Bounded retry for *safe (read-only / idempotent)* operations only."""
    attempts = max(1, min(attempts, 5))
    last: Exception | None = None
    for i in range(attempts):
        ctx.checkpoint()
        try:
            return fn()
        except PlaneError as exc:
            if exc.code not in retry_codes:
                raise
            last = exc
            delay = min(base_delay * (2 ** i), max(0.0, ctx.remaining()))
            if delay > 0:
                time.sleep(delay)
    if last is None:
        raise PlaneError("retry loop exited without result", code="INTERNAL")
    raise last
