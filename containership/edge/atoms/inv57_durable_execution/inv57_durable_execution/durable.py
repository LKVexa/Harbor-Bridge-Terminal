"""Stdlib-only durable replay reference engine for INV-57.

This module is intentionally independent of ``pk_core`` so that the core crash and
replay semantics can be tested even when the wider conformance framework is not
installed.  It is a reference implementation, not a replacement for a production
history backend such as Dapr's durable workflow runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import math
import threading
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence, runtime_checkable

HISTORY_EVENT_SCHEMA = "PK_WF_HISTORY_EVENT/2"
_ZERO_DIGEST = "0" * 64
_ALLOWED_KINDS = frozenset({"started", "completed", "failed"})


class DurableExecutionError(RuntimeError):
    """Base class for durable execution failures."""


class NonDeterminism(DurableExecutionError):
    """Workflow code no longer agrees with the durable history."""


class HistoryCorruption(DurableExecutionError):
    """The append-only history failed structural or digest validation."""


class HistoryLimitExceeded(DurableExecutionError):
    """The configured history bound would be exceeded."""


class UnsupportedResult(DurableExecutionError):
    """An activity result cannot be encoded deterministically."""


class ActivityInDoubt(DurableExecutionError):
    """An activity started but no durable outcome was recorded.

    Re-executing such an activity automatically could duplicate an external side
    effect.  The safe default is therefore to stop and require reconciliation.
    """


class RecordedActivityFailure(DurableExecutionError):
    """Replay encountered an activity that previously returned by raising."""


class ConcurrentRun(DurableExecutionError):
    """The same Worker instance was asked to run two workflows concurrently."""


class Crash(DurableExecutionError):
    """Simulated worker crash used by the reference tests."""


def _encode_value(value: Any) -> Mapping[str, Any]:
    """Encode a value into a deterministic, JSON-safe tagged representation."""
    if value is None:
        return {"t": "none"}
    if isinstance(value, bool):
        return {"t": "bool", "v": value}
    if isinstance(value, int):
        return {"t": "int", "v": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise UnsupportedResult("non-finite floats are not durable results")
        return {"t": "float", "v": value.hex()}
    if isinstance(value, str):
        return {"t": "str", "v": value}
    if isinstance(value, bytes):
        return {"t": "bytes", "v": base64.b64encode(value).decode("ascii")}
    if isinstance(value, list):
        return {"t": "list", "v": [_encode_value(item) for item in value]}
    if isinstance(value, tuple):
        return {"t": "tuple", "v": [_encode_value(item) for item in value]}
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise UnsupportedResult("durable result mappings require string keys")
        return {
            "t": "dict",
            "v": [[key, _encode_value(value[key])] for key in sorted(value)],
        }
    raise UnsupportedResult(
        f"unsupported durable result type: {type(value).__module__}.{type(value).__qualname__}"
    )


def _decode_value(encoded: Mapping[str, Any]) -> Any:
    """Decode a tagged value; every malformation surfaces as HistoryCorruption."""
    try:
        return _decode_value_unchecked(encoded)
    except HistoryCorruption:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, RecursionError) as exc:
        raise HistoryCorruption(
            f"history payload is malformed ({type(exc).__name__})") from exc


def _decode_value_unchecked(encoded: Mapping[str, Any]) -> Any:
    if not isinstance(encoded, Mapping) or "t" not in encoded:
        raise HistoryCorruption("history payload is not a tagged durable value")
    tag = encoded["t"]
    if tag == "none":
        return None
    if tag == "bool":
        if not isinstance(encoded["v"], bool):
            raise HistoryCorruption("history bool payload is not a boolean")
        return encoded["v"]
    if tag == "int":
        if not isinstance(encoded["v"], str):
            raise HistoryCorruption("history int payload is not a decimal string")
        return int(encoded["v"])
    if tag == "float":
        value = float.fromhex(encoded["v"])
        if not math.isfinite(value):
            raise HistoryCorruption("history contains a non-finite float")
        return value
    if tag == "str":
        if not isinstance(encoded["v"], str):
            raise HistoryCorruption("history str payload is not a string")
        return encoded["v"]
    if tag == "bytes":
        try:
            return base64.b64decode(encoded["v"], validate=True)
        except Exception as exc:  # binascii.Error varies by Python version
            raise HistoryCorruption("history contains invalid base64") from exc
    if tag in ("list", "tuple", "dict") and not isinstance(encoded["v"], (list, tuple)):
        raise HistoryCorruption(f"history {tag} payload is not a sequence")
    if tag == "list":
        return [_decode_value(item) for item in encoded["v"]]
    if tag == "tuple":
        return tuple(_decode_value(item) for item in encoded["v"])
    if tag == "dict":
        result: dict[str, Any] = {}
        previous: str | None = None
        for pair in encoded["v"]:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2 or not isinstance(pair[0], str):
                raise HistoryCorruption("history contains an invalid mapping entry")
            key, value = pair
            if previous is not None and key <= previous:
                raise HistoryCorruption("history mapping keys are not strictly sorted")
            previous = key
            result[key] = _decode_value(value)
        return result
    raise HistoryCorruption(f"history contains unknown durable value tag {tag!r}")


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HistoryCorruption("history is not canonical-JSON encodable") from exc


def _event_digest(fields: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(fields)).hexdigest()


def _default_activity_id(step: int, name: str) -> str:
    return f"step-{step}:{name}"


@runtime_checkable
class HistoryStore(Protocol):
    """Minimal persistence contract required by :class:`Worker`.

    Production backends can implement this protocol with transactional database,
    log, or state-store primitives while preserving the replay engine.
    """

    @property
    def events(self) -> tuple["HistoryEvent", ...]: ...

    def __len__(self) -> int: ...

    def ensure_capacity(self, count: int) -> None: ...

    def append(
        self,
        kind: str,
        *,
        activity_id: str,
        name: str,
        fingerprint: str | None = None,
        result: Any = None,
        has_result: bool = False,
    ) -> "HistoryEvent": ...

    def validate(self) -> None: ...

    def completed_history(self) -> list[tuple[str, Any]]: ...


def _freeze(value: Any) -> Any:
    """Deep-freeze a JSON-shaped payload so history cannot be mutated through a reference."""
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class HistoryEvent:
    """One append-only, hash-chained workflow history event.

    ``payload`` is deep-frozen on construction (v4.3.0): v4.2.0-era payloads were
    plain dicts reachable through ``store.events``, so a caller could rewrite a
    recorded result in place without the incremental validator noticing.
    """

    schema: str
    seq: int
    kind: str
    activity_id: str
    name: str
    fingerprint: str | None
    payload: Mapping[str, Any] | None
    prev_digest: str
    digest: str

    def __post_init__(self) -> None:
        if self.payload is not None and not isinstance(self.payload, MappingProxyType):
            object.__setattr__(self, "payload", _freeze(self.payload))

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "seq": self.seq,
            "kind": self.kind,
            "activity_id": self.activity_id,
            "name": self.name,
            "fingerprint": self.fingerprint,
            "payload": _thaw(self.payload),
            "prev_digest": self.prev_digest,
        }

    def to_dict(self) -> dict[str, Any]:
        data = self.unsigned_dict()
        data["digest"] = self.digest
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HistoryEvent":
        required = {
            "schema",
            "seq",
            "kind",
            "activity_id",
            "name",
            "fingerprint",
            "payload",
            "prev_digest",
            "digest",
        }
        if set(data) != required:
            missing = sorted(required - set(data))
            extra = sorted(set(data) - required)
            raise HistoryCorruption(f"history event shape mismatch; missing={missing}, extra={extra}")
        return cls(
            schema=data["schema"],
            seq=data["seq"],
            kind=data["kind"],
            activity_id=data["activity_id"],
            name=data["name"],
            fingerprint=data["fingerprint"],
            payload=data["payload"],
            prev_digest=data["prev_digest"],
            digest=data["digest"],
        )


class InMemoryHistoryStore:
    """Bounded append-only history with hash-chain validation.

    The store is intentionally simple and process-local.  The interface makes the
    persistence boundary explicit so a real backend can replace it without changing
    workflow replay semantics.
    """

    def __init__(
        self,
        events: Iterable[HistoryEvent] | None = None,
        *,
        max_events: int = 100_000,
    ) -> None:
        if not isinstance(max_events, int) or isinstance(max_events, bool) or max_events < 2:
            raise ValueError("max_events must be an integer >= 2")
        self.max_events = max_events
        self._events = list(events or ())
        self._validated = 0            # length of the prefix already proven intact
        if len(self._events) > self.max_events:
            raise HistoryLimitExceeded("history already exceeds max_events")
        self.validate(full=True)

    @property
    def events(self) -> tuple[HistoryEvent, ...]:
        return tuple(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def event_at(self, index: int) -> HistoryEvent:
        return self._events[index]

    def ensure_capacity(self, count: int) -> None:
        if count < 0:
            raise ValueError("count must be non-negative")
        if len(self._events) + count > self.max_events:
            raise HistoryLimitExceeded(
                f"history limit {self.max_events} would be exceeded by {count} event(s)"
            )

    def append(
        self,
        kind: str,
        *,
        activity_id: str,
        name: str,
        fingerprint: str | None = None,
        result: Any = None,
        has_result: bool = False,
    ) -> HistoryEvent:
        if kind not in _ALLOWED_KINDS:
            raise ValueError(f"unsupported history event kind {kind!r}")
        if not isinstance(activity_id, str) or not activity_id:
            raise ValueError("activity_id must be a non-empty string")
        if not isinstance(name, str) or not name:
            raise ValueError("activity name must be a non-empty string")
        if fingerprint is not None and (not isinstance(fingerprint, str) or not fingerprint):
            raise ValueError("fingerprint must be None or a non-empty string")
        if kind == "completed" and not has_result:
            raise ValueError("completed events require a result")
        if kind != "completed" and has_result:
            raise ValueError("only completed events may contain an activity result")

        self.ensure_capacity(1)
        payload = _encode_value(result) if has_result else None
        unsigned = {
            "schema": HISTORY_EVENT_SCHEMA,
            "seq": len(self._events),
            "kind": kind,
            "activity_id": activity_id,
            "name": name,
            "fingerprint": fingerprint,
            "payload": payload,
            "prev_digest": self._events[-1].digest if self._events else _ZERO_DIGEST,
        }
        event = HistoryEvent(**unsigned, digest=_event_digest(unsigned))
        # Persistence hook: a durable subclass commits the event (conditionally,
        # under its fencing epoch) before it becomes visible in the local cache.
        # If the commit raises, the cache is unchanged.
        self._persist(event)
        self._events.append(event)
        return event

    def _persist(self, event: HistoryEvent) -> None:
        """Commit ``event`` durably.  The in-memory store has nothing to commit."""

    def validate(self, *, full: bool = False) -> None:
        """Validate the hash chain.

        Events are immutable and only this class appends them, so by default only
        the suffix appended since the last successful validation is checked.  This
        keeps replay O(n) instead of O(n^2) (v4.2.0 re-hashed the whole chain on
        every activity: 1000-event replay took ~3.7 s against a 100 ms SLO).
        ``full=True`` re-checks everything and is used on load.
        """
        start = 0 if full or self._validated > len(self._events) else self._validated
        previous = self._events[start - 1].digest if start else _ZERO_DIGEST
        for expected_seq, event in enumerate(self._events[start:], start):
            if not isinstance(event, HistoryEvent):
                raise HistoryCorruption(f"history entry {expected_seq} is not a HistoryEvent")
            if not isinstance(event.schema, str) or event.schema != HISTORY_EVENT_SCHEMA:
                raise HistoryCorruption(
                    f"history entry {expected_seq} uses unsupported schema {event.schema!r}"
                )
            if not isinstance(event.seq, int) or isinstance(event.seq, bool) or event.seq != expected_seq:
                raise HistoryCorruption(
                    f"history entry sequence mismatch: expected {expected_seq}, got {event.seq!r}"
                )
            if not isinstance(event.kind, str) or event.kind not in _ALLOWED_KINDS:
                raise HistoryCorruption(f"history entry {expected_seq} has invalid kind {event.kind!r}")
            if not isinstance(event.activity_id, str) or not event.activity_id:
                raise HistoryCorruption(f"history entry {expected_seq} has invalid activity_id")
            if not isinstance(event.name, str) or not event.name:
                raise HistoryCorruption(f"history entry {expected_seq} has invalid activity name")
            if event.fingerprint is not None and (
                not isinstance(event.fingerprint, str) or not event.fingerprint
            ):
                raise HistoryCorruption(f"history entry {expected_seq} has invalid fingerprint")
            if event.kind == "completed":
                if event.payload is None:
                    raise HistoryCorruption(f"completed event {expected_seq} has no result payload")
                _decode_value(event.payload)
            elif event.payload is not None:
                raise HistoryCorruption(
                    f"non-completed event {expected_seq} unexpectedly contains a payload"
                )
            if not isinstance(event.prev_digest, str) or event.prev_digest != previous:
                raise HistoryCorruption(f"history hash chain breaks at sequence {expected_seq}")
            if event.digest != _event_digest(event.unsigned_dict()):
                raise HistoryCorruption(f"history digest mismatch at sequence {expected_seq}")
            previous = event.digest
        self._validated = len(self._events)

    def to_json(self) -> str:
        self.validate(full=True)
        return json.dumps(
            [event.to_dict() for event in self._events],
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"

    @classmethod
    def from_json(cls, text: str, *, max_events: int = 100_000) -> "InMemoryHistoryStore":
        if not isinstance(text, str):
            raise HistoryCorruption("history JSON must be provided as str")
        try:
            raw = json.loads(text)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise HistoryCorruption("history JSON cannot be decoded") from exc
        if not isinstance(raw, list):
            raise HistoryCorruption("history JSON root must be an array")
        try:
            events = [HistoryEvent.from_dict(item) for item in raw]
        except (TypeError, AttributeError, RecursionError) as exc:
            raise HistoryCorruption("history JSON contains a non-object event") from exc
        return cls(events, max_events=max_events)

    @classmethod
    def from_legacy(
        cls,
        history: Sequence[tuple[str, Any]],
        *,
        max_events: int = 100_000,
    ) -> "InMemoryHistoryStore":
        store = cls(max_events=max_events)
        for step, item in enumerate(history):
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise HistoryCorruption("legacy history entries must be (name, result) pairs")
            name, result = item
            if not isinstance(name, str) or not name:
                raise HistoryCorruption("legacy history activity names must be non-empty strings")
            activity_id = _default_activity_id(step, name)
            store.ensure_capacity(2)
            store.append("started", activity_id=activity_id, name=name)
            store.append(
                "completed",
                activity_id=activity_id,
                name=name,
                result=result,
                has_result=True,
            )
        return store

    def completed_history(self) -> list[tuple[str, Any]]:
        """Return a legacy-compatible view of completed activity results."""
        self.validate()
        completed: list[tuple[str, Any]] = []
        for event in self._events:
            if event.kind == "completed":
                completed.append((event.name, _decode_value(event.payload)))
        return completed


class _EventView:
    """Read-only indexed view over a store's events that avoids per-step copies."""

    __slots__ = ("_store", "_at", "_cached")

    def __init__(self, store: "HistoryStore") -> None:
        self._store = store
        self._at = getattr(store, "event_at", None)
        self._cached = None if self._at else store.events

    def __len__(self) -> int:
        return len(self._store) if self._at else len(self._cached)

    def __getitem__(self, index: int) -> "HistoryEvent":
        return self._at(index) if self._at else self._cached[index]


class Worker:
    """Deterministic workflow runner over an append-only history store."""

    def __init__(
        self,
        history: Sequence[tuple[str, Any]] | HistoryStore | None = None,
        *,
        max_history_events: int = 100_000,
    ) -> None:
        if history is None:
            self.history_store = InMemoryHistoryStore(max_events=max_history_events)
        elif isinstance(history, HistoryStore):
            if max_history_events != 100_000:
                raise ValueError(
                    "max_history_events configures only the built-in/legacy in-memory store; "
                    "configure a supplied HistoryStore directly"
                )
            self.history_store: HistoryStore = history
        else:
            self.history_store = InMemoryHistoryStore.from_legacy(
                history,
                max_events=max_history_events,
            )
        self.executed: list[str] = []
        self._event_pos = 0
        self._step_pos = 0
        self._run_lock = threading.Lock()
        self._poisoned: DurableExecutionError | None = None

    @property
    def history(self) -> list[tuple[str, Any]]:
        """Backward-compatible completed-result view; mutations do not alter the store."""
        return self.history_store.completed_history()

    def _raise_nondeterminism(self, message: str) -> None:
        exc = NonDeterminism(message)
        self._poisoned = exc
        raise exc

    @staticmethod
    def _event_matches(
        event: HistoryEvent,
        *,
        activity_id: str,
        name: str,
        fingerprint: str | None,
    ) -> bool:
        return (
            event.activity_id == activity_id
            and event.name == name
            and event.fingerprint == fingerprint
        )

    def activity(
        self,
        name: str,
        fn: Callable[[], Any],
        *,
        activity_id: str | None = None,
        fingerprint: str | None = None,
    ) -> Any:
        """Run or replay one activity.

        ``activity_id`` and ``fingerprint`` are optional for compatibility.  Supplying
        stable values is recommended whenever two calls may share the same display
        name or whenever inputs/implementation versions must participate in replay
        compatibility checks.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("activity name must be a non-empty string")
        if not callable(fn):
            raise TypeError("fn must be callable")
        if fingerprint is not None and (not isinstance(fingerprint, str) or not fingerprint):
            raise ValueError("fingerprint must be None or a non-empty string")
        resolved_id = activity_id or _default_activity_id(self._step_pos, name)
        if not isinstance(resolved_id, str) or not resolved_id:
            raise ValueError("activity_id must be None or a non-empty string")

        self.history_store.validate()
        # Index access without copying the whole history each step (v4.2.0 built a
        # fresh tuple of every event per activity, another O(n^2) replay term).
        events = _EventView(self.history_store)

        if self._event_pos < len(events):
            started = events[self._event_pos]
            if started.kind != "started":
                self._raise_nondeterminism(
                    f"step {self._step_pos}: expected a started event, history has {started.kind!r}"
                )
            if not self._event_matches(
                started,
                activity_id=resolved_id,
                name=name,
                fingerprint=fingerprint,
            ):
                self._raise_nondeterminism(
                    f"step {self._step_pos}: history has activity "
                    f"{started.activity_id!r}/{started.name!r}/{started.fingerprint!r}, code asked for "
                    f"{resolved_id!r}/{name!r}/{fingerprint!r}"
                )
            self._event_pos += 1

            if self._event_pos >= len(events):
                exc = ActivityInDoubt(
                    f"activity {resolved_id!r} ({name}) started but has no recorded outcome"
                )
                self._poisoned = exc
                raise exc

            outcome = events[self._event_pos]
            if outcome.kind not in {"completed", "failed"}:
                self._raise_nondeterminism(
                    f"step {self._step_pos}: activity outcome is {outcome.kind!r}, not completed/failed"
                )
            if not self._event_matches(
                outcome,
                activity_id=resolved_id,
                name=name,
                fingerprint=fingerprint,
            ):
                self._raise_nondeterminism(
                    f"step {self._step_pos}: activity outcome metadata does not match its start event"
                )
            self._event_pos += 1
            self._step_pos += 1
            if outcome.kind == "failed":
                exc = RecordedActivityFailure(
                    f"activity {resolved_id!r} ({name}) previously failed; automatic re-execution refused"
                )
                self._poisoned = exc
                raise exc
            return _decode_value(outcome.payload)

        # New work needs two durable slots before any user code runs.  That keeps a
        # history-capacity failure from occurring after a side effect has begun.
        self.history_store.ensure_capacity(2)
        self.history_store.append(
            "started",
            activity_id=resolved_id,
            name=name,
            fingerprint=fingerprint,
        )
        self._event_pos += 1

        try:
            result = fn()
            self.executed.append(name)
        except Crash:
            # Crash simulates abrupt process loss: no outcome event is durable, so
            # replay must treat the activity as in doubt instead of re-running it.
            self.executed.append(name)
            raise
        except Exception:
            self.executed.append(name)
            # Do not record exception text: it may contain tenant data or secrets.
            self.history_store.append(
                "failed",
                activity_id=resolved_id,
                name=name,
                fingerprint=fingerprint,
            )
            self._event_pos += 1
            self._step_pos += 1
            raise

        # Encoding happens before appending the completion.  If encoding fails, the
        # started event remains durable and replay becomes ActivityInDoubt rather than
        # risking a duplicate side effect.
        try:
            encoded = _encode_value(result)
            # Decode now as a structural self-check and to return a detached snapshot.
            detached_result = _decode_value(encoded)
        except DurableExecutionError as exc:
            self._poisoned = ActivityInDoubt(
                f"activity {resolved_id!r} ({name}) ran but its result was not durably encodable"
            )
            raise exc

        self.history_store.append(
            "completed",
            activity_id=resolved_id,
            name=name,
            fingerprint=fingerprint,
            result=result,
            has_result=True,
        )
        self._event_pos += 1
        self._step_pos += 1
        return detached_result

    def resolve_in_doubt(self, activity_id: str, result: Any, *, name: str | None = None) -> None:
        """Reconcile the single trailing started event as completed.

        This is deliberately explicit: operators or an external reconciler must first
        establish the activity's real outcome.  The method never re-runs user code.
        """
        self.history_store.validate()
        events = self.history_store.events
        if not events or events[-1].kind != "started":
            raise ActivityInDoubt("history does not end in an unresolved started event")
        started = events[-1]
        if started.activity_id != activity_id:
            raise ActivityInDoubt(
                f"trailing in-doubt activity is {started.activity_id!r}, not {activity_id!r}"
            )
        if name is not None and started.name != name:
            raise ActivityInDoubt(
                f"trailing in-doubt activity is named {started.name!r}, not {name!r}"
            )
        self.history_store.ensure_capacity(1)
        self.history_store.append(
            "completed",
            activity_id=started.activity_id,
            name=started.name,
            fingerprint=started.fingerprint,
            result=result,
            has_result=True,
        )
        self._poisoned = None

    def run(self, workflow: Callable[["Worker"], Any]) -> Any:
        if not callable(workflow):
            raise TypeError("workflow must be callable")
        if not self._run_lock.acquire(blocking=False):
            raise ConcurrentRun("a Worker instance may execute only one workflow at a time")
        try:
            self.history_store.validate()
            self._event_pos = 0
            self._step_pos = 0
            self._poisoned = None
            result = workflow(self)
            if self._poisoned is not None:
                raise self._poisoned
            if self._event_pos < len(self.history_store):
                self._raise_nondeterminism(
                    f"workflow finished after {self._step_pos} step(s) but history still has "
                    f"{len(self.history_store) - self._event_pos} unconsumed event(s)"
                )
            return result
        finally:
            self._run_lock.release()


__all__ = [
    "HISTORY_EVENT_SCHEMA",
    "ActivityInDoubt",
    "ConcurrentRun",
    "Crash",
    "DurableExecutionError",
    "HistoryCorruption",
    "HistoryEvent",
    "HistoryStore",
    "HistoryLimitExceeded",
    "InMemoryHistoryStore",
    "NonDeterminism",
    "RecordedActivityFailure",
    "UnsupportedResult",
    "Worker",
]
