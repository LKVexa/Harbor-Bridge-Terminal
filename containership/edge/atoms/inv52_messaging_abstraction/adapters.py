"""Broker adapters for INV-52 (C018, C021, C030, C031, C053, C055, C057, C083, C089).

* ``to_cloudevent`` / ``from_cloudevent`` — the PK_MSG_ENVELOPE/1 <-> CloudEvents
  1.0 structured-mode mapping Dapr Pub/Sub uses on the wire
* ``DaprHttpAdapter`` — publishes through the Dapr sidecar HTTP API
  ``POST /v1.0/publish/{pubsubname}/{topic}`` (Dapr API v1.0) with an
  injectable transport, per-call timeout and idempotent bounded retry
* ``dapr_delivery_status`` — maps an inbound Dapr delivery through a local
  ``PubSub`` to Dapr's SUCCESS / RETRY / DROP contract (DROP -> Dapr
  ``deadLetterTopic``)
* ``InMemoryBroker`` — a conformance/fault-injection broker with outage,
  partition and id de-duplication, used by the integration and chaos tests
* ``Outbox`` — bounded store-and-forward for intermittent connectivity: order
  preserved, capacity enforced (backpressure, never unbounded growth), replay
  is idempotent because the broker de-duplicates on the envelope id

No adapter here has been run against a live ``daprd``; see
docs/COMPATIBILITY.md for the pinned target and the open evidence item.
"""
from __future__ import annotations

import json
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict, deque
from typing import Any, Callable, Mapping

from .resilience import CallContext, RetryPolicy
from .runtime import IncompleteEnvelope, MessagingError, Overloaded, validate_envelope

DAPR_API = "v1.0"
CE_SPEC = "1.0"
CE_CONTENT_TYPE = "application/cloudevents+json"


class BrokerUnavailable(MessagingError, ConnectionError):
    code = "PK_MSG_BROKER_UNAVAILABLE"
    retryable = True


class BrokerRejected(MessagingError, RuntimeError):
    code = "PK_MSG_BROKER_REJECTED"


# ------------------------------------------------------------ CloudEvents
def to_cloudevent(msg: Mapping[str, Any], *, topic: str, pubsub: str) -> dict[str, Any]:
    validate_envelope(msg)
    ce = {"specversion": CE_SPEC, "id": msg["id"], "source": msg["source"], "type": msg["type"],
          "datacontenttype": "application/json", "data": msg["data"], "topic": topic, "pubsubname": pubsub}
    t = msg["time"]
    ce["time"] = t if isinstance(t, str) else None
    if not isinstance(t, str):
        ce["pkmsgtime"] = t  # numeric times travel as an extension attribute, losslessly
        del ce["time"]
    if msg.get("traceparent"):
        ce["traceparent"] = msg["traceparent"]
    return ce


def from_cloudevent(ce: Any) -> dict[str, Any]:
    if not isinstance(ce, Mapping):
        raise IncompleteEnvelope("cloudevent must be an object")
    if ce.get("specversion") != CE_SPEC:
        raise IncompleteEnvelope("unsupported cloudevents specversion", details={"specversion": ce.get("specversion")})
    t = ce.get("time", ce.get("pkmsgtime"))
    msg = {"id": ce.get("id"), "source": ce.get("source"), "type": ce.get("type"), "time": t,
           "data": ce.get("data")}
    if ce.get("traceparent"):
        msg["traceparent"] = ce["traceparent"]
    validate_envelope(msg)
    return msg


# ------------------------------------------------------------ Dapr HTTP
Transport = Callable[[str, str, bytes, Mapping[str, str], float], tuple[int, bytes]]


def urllib_transport(method: str, url: str, body: bytes, headers: Mapping[str, str], timeout: float):
    req = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - sidecar URL from config
            return resp.status, resp.read(65536)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(65536)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise BrokerUnavailable("dapr sidecar unreachable", details={"error_type": type(exc).__name__}) from exc


class DaprHttpAdapter:
    def __init__(self, *, pubsub: str, base_url: str = "http://127.0.0.1:3500", timeout: float = 5.0,
                 transport: Transport = urllib_transport, retry: RetryPolicy | None = None,
                 api_token: Callable[[], str] | None = None, sleep=time.sleep, rng: random.Random | None = None):
        parsed = urllib.parse.urlparse(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("base_url must be an http(s) URL")
        if not pubsub or "/" in pubsub:
            raise ValueError("invalid pubsub component name")
        self.pubsub, self.base_url, self.timeout = pubsub, base_url.rstrip("/"), timeout
        self.transport, self.retry = transport, retry or RetryPolicy()
        self.api_token, self.sleep, self.rng = api_token, sleep, rng or random.Random()
        self.attempts = 0

    def _once(self, topic: str, body: bytes) -> None:
        self.attempts += 1
        headers = {"Content-Type": CE_CONTENT_TYPE}
        if self.api_token is not None:
            headers["dapr-api-token"] = self.api_token()  # secret is fetched per call, never stored in config
        url = f"{self.base_url}/{DAPR_API}/publish/{urllib.parse.quote(self.pubsub, safe='')}/" \
              f"{urllib.parse.quote(topic, safe='')}"
        status, _ = self.transport("POST", url, body, headers, self.timeout)
        if status in (200, 204):  # Dapr v1.0: 204 published; 403 scope denied; 404 no such pubsub
            return
        if status in (408, 429, 500, 502, 503, 504):
            raise BrokerUnavailable("dapr publish failed", details={"status": status})
        raise BrokerRejected("dapr rejected the message", details={"status": status})

    def publish(self, topic: str, msg: Mapping[str, Any], ctx: CallContext | None = None) -> None:
        body = json.dumps(to_cloudevent(msg, topic=topic, pubsub=self.pubsub), separators=(",", ":")).encode()
        self.retry.run(lambda: self._once(topic, body), idempotent=True, ctx=ctx, sleep=self.sleep, rng=self.rng)


def dapr_delivery_status(bus: Any, *, app: str, topic: str, cloudevent: Any) -> dict[str, str]:
    """Deliver an inbound Dapr CloudEvent into a local bus; return Dapr's status body.

    * delivered or intentionally held (duplicate / dead-lettered locally) -> SUCCESS
    * retryable failure (frozen topic, overload) -> RETRY (Dapr redelivers)
    * terminal failure (malformed, unauthorised, oversize) -> DROP (Dapr dead-letter topic)
    """
    try:
        msg = from_cloudevent(cloudevent)
        bus.publish(app, topic, msg)
        return {"status": "SUCCESS"}
    except MessagingError as exc:
        return {"status": "RETRY" if exc.retryable else "DROP", "code": exc.code}


# ------------------------------------------------------------ in-memory broker
class InMemoryBroker:
    """Conformance/fault-injection broker (not a production broker)."""

    def __init__(self, *, dedup_window: int = 100_000):
        self.topics: dict[str, list[dict[str, Any]]] = {}
        self.available = True
        self.partitioned: set[str] = set()
        self._seen: OrderedDict[str, None] = OrderedDict()
        self.dedup_window = dedup_window
        self.duplicates = 0
        self._lock = threading.Lock()

    def publish(self, topic: str, msg: Mapping[str, Any], ctx: CallContext | None = None) -> None:
        if ctx:
            ctx.check()
        if not self.available or topic in self.partitioned:
            raise BrokerUnavailable("broker unavailable", details={"topic": topic})
        validate_envelope(msg)
        with self._lock:
            if msg["id"] in self._seen:
                self.duplicates += 1
                return
            self._seen[msg["id"]] = None
            if len(self._seen) > self.dedup_window:
                self._seen.popitem(last=False)
            self.topics.setdefault(topic, []).append(json.loads(json.dumps(msg, default=str)))


# ------------------------------------------------------------ outbox
class Outbox:
    """Bounded store-and-forward for intermittent/absent connectivity (C018)."""

    def __init__(self, adapter: Any, *, capacity: int = 10_000, max_age_s: float | None = None,
                 clock: Callable[[], float] = time.monotonic):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.adapter, self.capacity, self.max_age_s, self.clock = adapter, capacity, max_age_s, clock
        self.pending: deque[tuple[float, str, dict[str, Any]]] = deque()
        self.expired = 0
        self.rejected = 0
        self._lock = threading.RLock()

    def publish(self, topic: str, msg: Mapping[str, Any]) -> str:
        """Returns ``sent`` or ``queued``; raises ``Overloaded`` when full.

        The lock is held across the send so concurrent publishers cannot
        overtake queued messages (order is part of the contract)."""
        validate_envelope(msg)
        with self._lock:
            if self.pending:
                return self._enqueue(topic, msg)
            try:
                self.adapter.publish(topic, msg)
                return "sent"
            except MessagingError as exc:
                if not exc.retryable:
                    raise
                return self._enqueue(topic, msg)

    def _enqueue(self, topic: str, msg: Mapping[str, Any]) -> str:
        if len(self.pending) >= self.capacity:
            raise Overloaded("outbox full; apply backpressure", details={"capacity": self.capacity})
        self.pending.append((self.clock(), topic, json.loads(json.dumps(msg, default=str))))
        return "queued"

    def flush(self) -> dict[str, int]:
        """Replay queued messages in order until the first retryable failure."""
        sent = 0
        with self._lock:
            while self.pending:
                ts, topic, msg = self.pending[0]
                if self.max_age_s is not None and self.clock() - ts > self.max_age_s:
                    self.pending.popleft()
                    self.expired += 1
                    continue
                try:
                    self.adapter.publish(topic, msg)
                except MessagingError as exc:
                    if exc.retryable:
                        break
                    self.pending.popleft()  # terminal: dropped from the outbox and counted
                    self.rejected += 1
                    continue
                self.pending.popleft()
                sent += 1
            return {"sent": sent, "pending": len(self.pending), "expired": self.expired, "rejected": self.rejected}
