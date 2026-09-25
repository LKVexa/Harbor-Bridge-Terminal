"""Broker-independent in-process reference implementation for INV-52.

This module intentionally has no dependency on ``pk_core`` so applications and
unit tests can exercise the messaging contract even when the audit framework is
not installed.  It is a reference abstraction, not a durable broker.

4.3.0 additions (all backward compatible with the 4.2.0 API):

* every caller-visible failure carries ``code`` and ``retryable`` (C014, C025)
* payload size / JSON depth / fan-out bounds (C028, C067)
* optional message-id de-duplication window for idempotent redelivery (C025)
* topic lifecycle: ACTIVE, FROZEN, QUARANTINED, DISABLED (C015, C059)
* optional admission hook for quotas / load shedding (C017, C054)
* a bounded decision record for every publish with a reason for every route,
  and an ``explain`` view (C076, C077)
* W3C ``traceparent`` validation and propagation (C074)
* latency histogram, outcome counters, health/readiness (C052, C071, C072)
* ``subscribe`` returns a subscription id and ``unsubscribe`` removes it
"""
from __future__ import annotations

from collections import Counter, OrderedDict, deque
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import itertools
import json
import math
import re
import threading
import time as _time
import uuid
from types import MappingProxyType
from typing import Any, Callable

REQUIRED = ("id", "source", "type", "time", "data")
DEFAULT_MAX_ROUTES_PER_TOPIC = 256
DEFAULT_MAX_DEAD_LETTERS = 10_000
DEFAULT_MAX_PAYLOAD_BYTES = 1_048_576
DEFAULT_MAX_JSON_DEPTH = 32
DEFAULT_MAX_DECISIONS = 10_000
DEFAULT_MAX_TOPICS = 10_000
TRACEPARENT = re.compile(r"^00-(?!0{32})[0-9a-f]{32}-(?!0{16})[0-9a-f]{16}-[0-9a-f]{2}$")

# Topic lifecycle states (C015 / C059)
ACTIVE, FROZEN, QUARANTINED, DISABLED = "ACTIVE", "FROZEN", "QUARANTINED", "DISABLED"
TOPIC_STATES = (ACTIVE, FROZEN, QUARANTINED, DISABLED)
TOPIC_TRANSITIONS = {
    ACTIVE: {FROZEN, QUARANTINED, DISABLED},
    FROZEN: {ACTIVE, QUARANTINED, DISABLED},
    QUARANTINED: {ACTIVE, FROZEN, DISABLED},
    DISABLED: {ACTIVE},
}

# Publish outcome vocabulary (C014)
DELIVERED = "success"
PARTIAL = "partial_success"
DEAD_LETTERED = "dead_lettered"
DUPLICATE = "duplicate_suppressed"
QUARANTINED_OUTCOME = "quarantined"
REJECTED_RETRYABLE = "retryable_failure"
REJECTED_TERMINAL = "terminal_failure"
OUTCOMES = (DELIVERED, PARTIAL, DEAD_LETTERED, DUPLICATE, QUARANTINED_OUTCOME, REJECTED_RETRYABLE,
            REJECTED_TERMINAL)


class MessagingError(Exception):
    """Base class for machine-classifiable messaging failures."""

    code = "PK_MSG_ERROR"
    retryable = False

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "retryable": self.retryable,
                "details": deepcopy(self.details)}


class TopicDenied(MessagingError, PermissionError):
    code = "PK_MSG_TOPIC_DENIED"


class IncompleteEnvelope(MessagingError, ValueError):
    code = "PK_MSG_ENVELOPE_INVALID"


class InvalidArgument(MessagingError, ValueError):
    code = "PK_MSG_ARGUMENT_INVALID"


class InvalidSubscription(MessagingError, ValueError):
    code = "PK_MSG_SUBSCRIPTION_INVALID"


class ResourceLimitExceeded(MessagingError, RuntimeError):
    code = "PK_MSG_RESOURCE_LIMIT"


class TopicUnavailable(MessagingError, RuntimeError):
    """The topic is frozen: the caller may retry after the operator unfreezes it."""

    code = "PK_MSG_TOPIC_UNAVAILABLE"
    retryable = True


class TopicDisabled(MessagingError, RuntimeError):
    code = "PK_MSG_TOPIC_DISABLED"


class Overloaded(MessagingError, RuntimeError):
    """Admission refused (quota, rate, circuit): back off and retry."""

    code = "PK_MSG_OVERLOADED"
    retryable = True


class InvalidTransition(MessagingError, ValueError):
    code = "PK_MSG_STATE_TRANSITION_INVALID"


def _nonempty_text(value: Any, field_name: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds {max_length} characters")
    return value


def _argument_text(value: Any, field_name: str, *, max_length: int = 512) -> str:
    try:
        return _nonempty_text(value, field_name, max_length=max_length)
    except ValueError as exc:
        raise InvalidArgument(str(exc), details={"field": field_name}) from exc


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


_SCALARS = frozenset({int, float, str, bool, type(None), bytes})


def json_depth(obj: Any, limit: int = 10_000) -> int:
    """Nesting depth of a JSON-like value.  Iterative (no recursion bomb) and
    only containers are visited, so scalar-heavy payloads cost O(containers)."""
    if not isinstance(obj, (Mapping, list, tuple)):
        return 0
    stack = [(obj, 1)]
    best = 0
    while stack:
        o, d = stack.pop()
        if d > best:
            best = d
            if best > limit:
                return best
        vals = o.values() if isinstance(o, Mapping) else o
        for v in vals:
            t = type(v)
            if t is dict or t is list or t is tuple or (t not in _SCALARS and isinstance(v, (Mapping, list, tuple))):
                stack.append((v, d + 1))
    return best


def payload_size(msg: Mapping[str, Any]) -> int:
    """Canonical JSON size in bytes; non-JSON values are sized via ``str``."""
    try:
        return len(json.dumps(msg, default=str, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise IncompleteEnvelope("message is not serialisable", details={"error_type": type(exc).__name__}) from exc


def envelope(
    source: str,
    etype: str,
    data: Any,
    time: int | float | str | None = None,
    *,
    message_id: str | None = None,
    traceparent: str | None = None,
) -> dict[str, Any]:
    """Create a complete version-1 message envelope.

    ``time`` remains compatible with numeric callers; when omitted it is an
    RFC-3339 UTC timestamp.  UUID-backed IDs remain unique across process
    restarts.  ``traceparent`` is an optional W3C trace-context extension.
    """
    try:
        source = _nonempty_text(source, "source")
        etype = _nonempty_text(etype, "type")
    except ValueError as exc:
        raise IncompleteEnvelope(str(exc)) from exc
    if data is None:
        raise IncompleteEnvelope("data may not be None", details={"missing": ["data"]})
    if message_id is None:
        message_id = f"m-{uuid.uuid4()}"
    try:
        message_id = _nonempty_text(message_id, "id")
    except ValueError as exc:
        raise IncompleteEnvelope(str(exc), details={"field": "id"}) from exc
    timestamp: int | float | str = _utc_timestamp() if time is None else time
    msg = {"id": message_id, "source": source, "type": etype, "time": timestamp, "data": data}
    if traceparent is not None:
        msg["traceparent"] = traceparent
    validate_envelope(msg)
    return msg


def validate_envelope(msg: Mapping[str, Any]) -> None:
    """Validate the public envelope shape and mandatory field semantics."""
    if not isinstance(msg, Mapping):
        raise IncompleteEnvelope("message must be a mapping", details={"type": type(msg).__name__})
    missing = [key for key in REQUIRED if key not in msg or msg[key] is None or msg[key] == ""]
    if missing:
        raise IncompleteEnvelope(f"missing or empty envelope fields: {missing}", details={"missing": missing})
    for key in ("id", "source", "type"):
        try:
            _nonempty_text(msg[key], key)
        except ValueError as exc:
            raise IncompleteEnvelope(str(exc), details={"field": key}) from exc
    if isinstance(msg["time"], bool) or not isinstance(msg["time"], (int, float, str)):
        raise IncompleteEnvelope(
            "time must be an integer, float, or non-empty timestamp string",
            details={"field": "time", "type": type(msg["time"]).__name__},
        )
    if isinstance(msg["time"], str) and not msg["time"].strip():
        raise IncompleteEnvelope("time may not be blank", details={"field": "time"})
    if isinstance(msg["time"], float) and not math.isfinite(msg["time"]):
        raise IncompleteEnvelope("time must be finite", details={"field": "time"})
    tp = msg.get("traceparent")
    if tp is not None and (not isinstance(tp, str) or not TRACEPARENT.match(tp)):
        raise IncompleteEnvelope("traceparent must be a W3C trace-context value", details={"field": "traceparent"})


def _freeze(obj: Any) -> Any:
    """Deep read-only view used for predicate evaluation (one copy per publish)."""
    if isinstance(obj, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return tuple(_freeze(v) for v in obj)
    if isinstance(obj, (set, frozenset)):
        return frozenset(_freeze(v) for v in obj)
    return deepcopy(obj) if isinstance(obj, (bytearray,)) else obj


class LatencyHistogram:
    """Fixed-bucket latency histogram in nanoseconds (bounded memory)."""

    BOUNDS_NS = (1_000, 5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000, 5_000_000,
                 10_000_000, 50_000_000)

    def __init__(self) -> None:
        self.counts = [0] * (len(self.BOUNDS_NS) + 1)
        self.total = 0
        self.sum_ns = 0
        self.max_ns = 0

    def observe(self, ns: int) -> None:
        i = 0
        while i < len(self.BOUNDS_NS) and ns > self.BOUNDS_NS[i]:
            i += 1
        self.counts[i] += 1
        self.total += 1
        self.sum_ns += ns
        self.max_ns = max(self.max_ns, ns)

    def quantile(self, q: float) -> int | None:
        """Upper bucket bound containing quantile ``q`` (conservative)."""
        if not self.total:
            return None
        target = q * self.total
        run = 0
        for i, c in enumerate(self.counts):
            run += c
            if run >= target:
                return self.BOUNDS_NS[i] if i < len(self.BOUNDS_NS) else self.max_ns
        return self.max_ns

    def snapshot(self) -> dict[str, Any]:
        return {"bounds_ns": list(self.BOUNDS_NS), "counts": list(self.counts), "count": self.total,
                "sum_ns": self.sum_ns, "max_ns": self.max_ns, "p50_ns": self.quantile(.5),
                "p95_ns": self.quantile(.95), "p99_ns": self.quantile(.99)}


@dataclass
class PubSub:
    """Thread-safe, bounded reference pub/sub abstraction.

    This class deliberately does not implement broker durability, retries, or
    redelivery guarantees; those belong to the downstream reliability layer.
    All new 4.3.0 knobs default to values that keep 4.2.0 behaviour.
    """

    max_routes_per_topic: int = DEFAULT_MAX_ROUTES_PER_TOPIC
    max_dead_letters: int = DEFAULT_MAX_DEAD_LETTERS
    publishers: dict[str, frozenset[str]] = field(default_factory=dict)
    routes: dict[str, list[tuple[Any, Any]]] = field(default_factory=dict)
    dead_letter: list[dict[str, Any]] = field(default_factory=list)
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES
    max_json_depth: int = DEFAULT_MAX_JSON_DEPTH
    max_decisions: int = DEFAULT_MAX_DECISIONS
    max_topics: int = DEFAULT_MAX_TOPICS
    dedup_window: int = 0
    predicate_view: str = "copy"
    admission: Callable[[str, str], None] | None = None
    observer: Callable[[dict[str, Any]], None] | None = None
    clock_ns: Callable[[], int] = _time.perf_counter_ns
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _stats: Counter = field(default_factory=Counter, init=False, repr=False)
    dropped_dead_letters: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        for name in ("max_routes_per_topic", "max_dead_letters", "max_payload_bytes", "max_json_depth",
                     "max_decisions", "max_topics"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise InvalidArgument(f"{name} must be a positive integer", details={"field": name})
        if isinstance(self.dedup_window, bool) or not isinstance(self.dedup_window, int) or self.dedup_window < 0:
            raise InvalidArgument("dedup_window must be a non-negative integer", details={"field": "dedup_window"})
        if self.predicate_view not in ("copy", "frozen"):
            raise InvalidArgument("predicate_view must be 'copy' or 'frozen'", details={"field": "predicate_view"})
        if self.admission is not None and not callable(self.admission):
            raise InvalidArgument("admission must be callable", details={"field": "admission"})
        self.topic_state: dict[str, str] = {}
        self._route_ids: dict[str, list[str]] = {}
        self._sub_seq = itertools.count(1)
        self._decision_seq = itertools.count(1)
        self._id_prefix = uuid.uuid4().hex[:12]  # unique per bus instance; sequence within it
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._decisions: deque[dict[str, Any]] = deque(maxlen=self.max_decisions)
        self._decision_index: dict[str, dict[str, Any]] = {}
        self._latency = LatencyHistogram()
        self._outcomes: Counter = Counter()
        self._reasons: Counter = Counter()
        self._state = "READY"
        self._last_publish_ns: int | None = None

    # ------------------------------------------------------------ policy
    def _touch_topic(self, topic: str) -> None:
        if topic not in self.topic_state:
            if len(self.topic_state) >= self.max_topics:
                raise ResourceLimitExceeded("topic limit reached", details={"limit": self.max_topics})
            self.topic_state[topic] = ACTIVE

    def allow(self, topic: str, *apps: str) -> None:
        """Replace the set of applications allowed to publish to ``topic``."""
        topic = _argument_text(topic, "topic")
        normalized = frozenset(_argument_text(app, "app") for app in apps)
        with self._lock:
            self._touch_topic(topic)
            self.publishers[topic] = normalized
            self._stats["policy_changes"] += 1
        self._emit({"event": "policy.allow", "topic": topic, "apps": sorted(normalized)})

    def set_topic_state(self, topic: str, state: str, *, reason: str = "operator") -> str:
        """Operator control: freeze, quarantine, disable or re-activate a topic."""
        topic = _argument_text(topic, "topic")
        if state not in TOPIC_STATES:
            raise InvalidArgument("unknown topic state", details={"state": state})
        with self._lock:
            self._touch_topic(topic)
            current = self.topic_state[topic]
            if state != current and state not in TOPIC_TRANSITIONS[current]:
                raise InvalidTransition(f"{current} -> {state} is not a legal transition",
                                        details={"from": current, "to": state})
            self.topic_state[topic] = state
            self._stats["state_changes"] += 1
        self._emit({"event": "topic.state", "topic": topic, "from": current, "to": state,
                    "reason": str(reason)[:200]})
        return current

    def subscribe(self, topic: str, predicate: Any, sink: Any) -> str:
        """Register a content predicate and append-capable sink; returns a subscription id."""
        try:
            topic = _nonempty_text(topic, "topic")
        except ValueError as exc:
            raise InvalidSubscription(str(exc), details={"field": "topic"}) from exc
        if not callable(predicate):
            raise InvalidSubscription("predicate must be callable")
        if not callable(getattr(sink, "append", None)):
            raise InvalidSubscription("sink must expose append(message)")
        with self._lock:
            existing = self.routes.setdefault(topic, [])
            if len(existing) >= self.max_routes_per_topic:
                raise ResourceLimitExceeded(
                    f"route limit reached for topic {topic!r}",
                    details={"topic": topic, "limit": self.max_routes_per_topic},
                )
            self._touch_topic(topic)
            sub_id = f"sub-{next(self._sub_seq)}"
            existing.append((predicate, sink))
            self._route_ids.setdefault(topic, []).append(sub_id)
            self._stats["subscriptions"] += 1
        self._emit({"event": "subscription.add", "topic": topic, "subscription": sub_id})
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        with self._lock:
            for topic, ids in self._route_ids.items():
                if subscription_id in ids:
                    i = ids.index(subscription_id)
                    del ids[i]
                    del self.routes[topic][i]
                    self._stats["unsubscriptions"] += 1
                    return True
        return False

    def _route_ids_for(self, topic: str, n: int) -> list[str]:
        ids = self._route_ids.get(topic, [])
        # routes appended directly to ``routes`` (4.2.0 style) get positional ids
        return [ids[i] if i < len(ids) else f"route-{i}" for i in range(n)]

    # ------------------------------------------------------------ helpers
    def _emit(self, event: dict[str, Any]) -> None:
        if self.observer is None:
            return
        try:
            self.observer(dict(event))
        except Exception:  # noqa: BLE001 - telemetry must never break messaging
            with self._lock:
                self._stats["observer_errors"] += 1

    def _record_dead_letter(self, *, topic: str, reason: str, message: Mapping[str, Any], errors=None) -> None:
        entry = {"topic": topic, "reason": reason, "message": deepcopy(dict(message))}
        if errors:
            entry["errors"] = deepcopy(errors)
        with self._lock:
            if len(self.dead_letter) >= self.max_dead_letters:
                del self.dead_letter[0]
                self.dropped_dead_letters += 1
                self._stats["dead_letter_evictions"] += 1
            self.dead_letter.append(entry)
            self._stats["dead_lettered"] += 1
            self._reasons[reason] += 1

    def _decide(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if len(self._decisions) == self._decisions.maxlen:
                old = self._decisions[0]
                if self._decision_index.get(old.get("message_id")) is old:
                    del self._decision_index[old["message_id"]]
            self._decisions.append(record)
            if record.get("message_id"):
                self._decision_index[record["message_id"]] = record
            self._outcomes[record["outcome"]] += 1
        self._emit({"event": "publish.decision", **{k: v for k, v in record.items() if k != "routes"},
                    "route_count": len(record.get("routes", ()))})
        return record

    def _reject(self, exc: MessagingError, base: dict[str, Any], started: int) -> None:
        rec = dict(base, outcome=REJECTED_RETRYABLE if exc.retryable else REJECTED_TERMINAL,
                   reason=exc.code, latency_ns=self.clock_ns() - started, routes=[])
        self._decide(rec)
        raise exc

    # ------------------------------------------------------------ publish
    def publish(self, app: str, topic: str, msg: Mapping[str, Any]) -> int:
        """Publish one message and return the count of successful route deliveries.

        Predicate and sink failures are isolated so one broken subscription does
        not abort other routes.  Subscriber views are deep copies of the
        canonical published envelope, preventing cross-subscriber mutation.
        """
        started = self.clock_ns()
        app = _argument_text(app, "app")
        topic = _argument_text(topic, "topic")
        mid = msg.get("id") if isinstance(msg, Mapping) else None
        base = {"decision_id": f"d-{self._id_prefix}-{next(self._decision_seq)}",
                "message_id": mid if isinstance(mid, str) else None, "app": app, "topic": topic, "ts": _time.time()}
        with self._lock:
            allowed = self.publishers.get(topic, frozenset())
            state = self.topic_state.get(topic, ACTIVE)
            route_snapshot = tuple(self.routes.get(topic, ()))
            route_ids = self._route_ids_for(topic, len(route_snapshot))
        base["topic_state"] = state
        if app not in allowed:
            with self._lock:
                self._stats["denied"] += 1
            self._reject(TopicDenied(f"{app} may not publish to {topic}", details={"app": app, "topic": topic}),
                         base, started)
        if state == DISABLED:
            self._reject(TopicDisabled(f"topic {topic!r} is disabled", details={"topic": topic}), base, started)
        if state == FROZEN:
            self._reject(TopicUnavailable(f"topic {topic!r} is frozen", details={"topic": topic}), base, started)

        try:
            validate_envelope(msg)
        except IncompleteEnvelope as exc:
            with self._lock:
                self._stats["invalid"] += 1
            self._reject(exc, base, started)
        if msg["source"] != app:
            with self._lock:
                self._stats["denied"] += 1
            self._reject(TopicDenied(f"{app} may not publish as source {msg['source']!r}",
                                     details={"app": app, "source": msg["source"], "topic": topic}), base, started)
        size = payload_size(msg)
        if size > self.max_payload_bytes:
            with self._lock:
                self._stats["oversize"] += 1
            self._reject(ResourceLimitExceeded("payload exceeds limit",
                                               details={"bytes": size, "limit": self.max_payload_bytes}),
                         base, started)
        if json_depth(msg, self.max_json_depth + 1) > self.max_json_depth + 1:
            self._reject(ResourceLimitExceeded("payload nesting exceeds limit",
                                               details={"limit": self.max_json_depth}), base, started)
        if self.admission is not None:
            try:
                self.admission(app, topic)
            except MessagingError as exc:
                with self._lock:
                    self._stats["shed"] += 1
                self._reject(exc, base, started)
            except Exception as exc:  # noqa: BLE001 - a broken admission hook fails closed
                with self._lock:
                    self._stats["shed"] += 1
                self._reject(Overloaded("admission control unavailable",
                                        details={"error_type": type(exc).__name__}), base, started)

        try:
            canonical = deepcopy(dict(msg))
        except Exception as exc:
            err = IncompleteEnvelope(
                "message must be safely copyable for subscriber isolation",
                details={"error_type": type(exc).__name__},
            )
            err.__cause__ = exc
            self._reject(err, base, started)
        base["traceparent"] = canonical.get("traceparent")
        base["type"] = canonical["type"]

        if self.dedup_window:
            with self._lock:
                if canonical["id"] in self._seen:
                    self._seen.move_to_end(canonical["id"])
                    self._stats["duplicates"] += 1
                    dup = True
                else:
                    self._seen[canonical["id"]] = None
                    if len(self._seen) > self.dedup_window:
                        self._seen.popitem(last=False)
                    dup = False
            if dup:
                self._decide(dict(base, outcome=DUPLICATE, reason="message id already accepted",
                                  latency_ns=self.clock_ns() - started, routes=[]))
                return 0

        if state == QUARANTINED:
            self._record_dead_letter(topic=topic, reason="quarantined", message=canonical)
            with self._lock:
                self._stats["published"] += 1
                self._stats["quarantined"] += 1
            self._decide(dict(base, outcome=QUARANTINED_OUTCOME, reason="topic quarantined; held in dead letter",
                              latency_ns=self.clock_ns() - started, routes=[]))
            return 0

        delivered = 0
        errors: list[dict[str, Any]] = []
        route_log: list[dict[str, Any]] = []
        view = _freeze(canonical) if self.predicate_view == "frozen" else None
        for index, (predicate, sink) in enumerate(route_snapshot):
            rid = route_ids[index]
            try:
                matched = bool(predicate(view if view is not None else deepcopy(canonical)))
            except Exception as exc:
                errors.append({"route": index, "stage": "predicate", "error_type": type(exc).__name__})
                route_log.append({"route": rid, "matched": None, "delivered": False,
                                  "reason": f"predicate raised {type(exc).__name__}"})
                with self._lock:
                    self._stats["route_errors"] += 1
                continue
            if not matched:
                route_log.append({"route": rid, "matched": False, "delivered": False, "reason": "predicate false"})
                continue
            try:
                sink.append(deepcopy(canonical))
            except Exception as exc:
                code = getattr(exc, "code", None)
                errors.append({"route": index, "stage": "sink", "error_type": type(exc).__name__,
                               **({"code": code} if isinstance(code, str) else {})})
                route_log.append({"route": rid, "matched": True, "delivered": False,
                                  "reason": f"sink raised {type(exc).__name__}"})
                with self._lock:
                    self._stats["sink_errors"] += 1
                continue
            delivered += 1
            route_log.append({"route": rid, "matched": True, "delivered": True, "reason": "delivered"})

        now = self.clock_ns()
        with self._lock:
            self._stats["published"] += 1
            self._stats["delivered"] += delivered
            self._latency.observe(now - started)
            self._last_publish_ns = now

        if delivered == 0:
            if any(e["stage"] == "sink" for e in errors):
                reason = "handler failure"
            elif any(e["stage"] == "predicate" for e in errors):
                reason = "route evaluation failure"
            else:
                reason = "no route matched"
            self._record_dead_letter(topic=topic, reason=reason, message=canonical, errors=errors)
            outcome = DEAD_LETTERED
        else:
            reason = "delivered" if not errors else f"{len(errors)} route(s) failed"
            outcome = DELIVERED if not errors else PARTIAL
            if errors:
                with self._lock:
                    self._stats["partial"] += 1
        self._decide(dict(base, outcome=outcome, reason=reason, delivered=delivered, latency_ns=now - started,
                          routes=route_log))
        return delivered

    # ------------------------------------------------------------ views
    def explain(self, message_id: str) -> dict[str, Any] | None:
        """Operator explain view: why a message went where it went."""
        with self._lock:
            rec = self._decision_index.get(message_id)
            if rec is None:
                return None
            out = deepcopy(rec)
            out["policy"] = {"allowed_publishers": sorted(self.publishers.get(rec["topic"], ())),
                             "topic_state_now": self.topic_state.get(rec["topic"], ACTIVE),
                             "route_count_now": len(self.routes.get(rec["topic"], ()))}
            out["limits"] = {"max_payload_bytes": self.max_payload_bytes, "max_json_depth": self.max_json_depth,
                             "max_routes_per_topic": self.max_routes_per_topic}
            return out

    def decisions(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(list(self._decisions)[-limit:])

    def health(self, *, stall_after_s: float | None = None, backlog_ratio_warn: float = 0.8) -> dict[str, Any]:
        """Health/readiness (C052, C071).  Status: ok | degraded | unhealthy."""
        with self._lock:
            backlog = len(self.dead_letter)
            ratio = backlog / self.max_dead_letters
            checks = {"state": self._state,
                      "dead_letter_fill": round(ratio, 4),
                      "quarantined_topics": sorted(t for t, s in self.topic_state.items() if s == QUARANTINED),
                      "frozen_topics": sorted(t for t, s in self.topic_state.items() if s == FROZEN),
                      "observer_errors": self._stats["observer_errors"]}
            last = self._last_publish_ns
        problems = []
        if ratio >= backlog_ratio_warn:
            problems.append("dead-letter backlog above warning ratio")
        if checks["quarantined_topics"] or checks["frozen_topics"]:
            problems.append("topics withheld from service")
        if stall_after_s is not None and last is not None and (self.clock_ns() - last) / 1e9 > stall_after_s:
            problems.append("no publish completed within stall window")
        status = "ok" if not problems else "degraded"
        if self._state != "READY":
            status = "unhealthy"
        return {"status": status, "ready": self._state == "READY", "problems": problems, "checks": checks}

    def metrics(self) -> dict[str, Any]:
        """Return a copy of stable in-process counters for tests and adapters.

        Integer counters keep their 4.2.0 names; ``latency`` / ``outcomes`` /
        ``dead_letter_reasons`` are 4.3.0 structured additions.
        """
        with self._lock:
            metrics: dict[str, Any] = dict(self._stats)
            metrics["topics"] = len(self.publishers)
            metrics["routes"] = sum(len(v) for v in self.routes.values())
            metrics["dead_letter_backlog"] = len(self.dead_letter)
            metrics["dead_letter_evictions"] = self.dropped_dead_letters
            metrics["latency"] = self._latency.snapshot()
            metrics["outcomes"] = dict(self._outcomes)
            metrics["dead_letter_reasons"] = dict(self._reasons)
            return metrics
