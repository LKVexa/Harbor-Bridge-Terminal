"""Adjacent-layer integration adapters for INV-17 (C030, C083).

Each adapter implements INV-17's side of a dependency declared in ``contract.py`` and
reciprocated (or not -- see ``integration/adjacent-layers.json``) by the sibling's own
contract in the Post-Kubernetes estate:

* INV-15 New asynchronous ABI  -- readiness via a waitable set      (``WaitableSet``)
* INV-12 Language interop      -- lower/lift elements canonically   (``CanonicalCodec``)
* INV-18 Completion primitive  -- one-shot counterpart / trailers    (``Completion``, ``drain_to_completion``)
* INV-20 HTTP component worlds -- bodies are streams                 (``HttpBody``)
* INV-19 OS async analogues    -- OS readiness mapped onto credit    (``OsReadinessBridge``)

The adapters are deliberately small: they fix the seam semantics INV-17 owns and leave
the sibling's own behaviour to the sibling.
"""
from __future__ import annotations

import json
import struct
from threading import RLock
from typing import Any, Callable, Iterable

from .stream import NOT_READY, EndDropped, Stream, StreamError


class AdapterError(StreamError):
    code = "PK_STREAM_ADAPTER"


# ------------------------------------------------------------------ INV-15
class WaitableSet:
    """Minimal waitable-set view: which streams are readable/writable right now."""

    def __init__(self) -> None:
        self._members: dict[str, Stream] = {}

    def join(self, s: Stream) -> None:
        self._members[s.stream_id] = s

    def leave(self, s: Stream) -> None:
        self._members.pop(s.stream_id, None)

    def poll(self) -> dict[str, set[str]]:
        """Readable: value/EOF/drop observable. Writable: credit and capacity available."""
        ready: dict[str, set[str]] = {}
        for sid, s in self._members.items():
            st = s.stats()
            ev: set[str] = set()
            if st.buffered or st.state in ("ended", "writer_dropped", "reader_dropped"):
                ev.add("readable")
            if st.credit > 0 and st.buffered < s.config.max_buffer and st.state not in ("ended", "frozen"):
                ev.add("writable")
            if ev:
                ready[sid] = ev
        return ready


# ------------------------------------------------------------------ INV-12
class CanonicalCodec:
    """Canonical lowering of scalar/bytes/str elements; lifting re-checks the type.

    Wire form: 1-byte tag + payload. Tags: b bytes, s utf-8 str, i int64, f float64,
    j canonical JSON (dict/list/tuple of the above).
    """

    MAX = 1 << 20

    def lower(self, value: Any) -> bytes:
        if isinstance(value, bool):
            raise AdapterError("bool has no canonical lowering on this seam")
        if isinstance(value, bytes):
            out = b"b" + value
        elif isinstance(value, str):
            out = b"s" + value.encode("utf-8")
        elif isinstance(value, int):
            if not -(1 << 63) <= value < (1 << 63):
                raise AdapterError("int outside int64")
            out = b"i" + struct.pack(">q", value)
        elif isinstance(value, float):
            out = b"f" + struct.pack(">d", value)
        elif isinstance(value, (dict, list, tuple)):
            out = b"j" + json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        else:
            raise AdapterError("type has no canonical lowering", type=type(value).__name__)
        if len(out) > self.MAX:
            raise AdapterError("lowered element exceeds seam limit", size=len(out))
        return out

    def lift(self, data: bytes, expected: type) -> Any:
        if not isinstance(data, (bytes, bytearray)) or not data or len(data) > self.MAX:
            raise AdapterError("malformed lowered element")
        tag, body = data[:1], bytes(data[1:])
        try:
            value: Any
            if tag == b"b":
                value = body
            elif tag == b"s":
                value = body.decode("utf-8")
            elif tag == b"i" and len(body) == 8:
                value = struct.unpack(">q", body)[0]
            elif tag == b"f" and len(body) == 8:
                value = struct.unpack(">d", body)[0]
            elif tag == b"j":
                value = json.loads(body)
                if expected is tuple and isinstance(value, list):
                    value = tuple(value)
            else:
                raise AdapterError("unknown tag")
        except (UnicodeDecodeError, ValueError, struct.error):
            raise AdapterError("malformed lowered element") from None
        if not isinstance(value, expected):
            raise AdapterError("lifted type differs from stream type", expected=expected.__name__,
                               actual=type(value).__name__)
        return value


# ------------------------------------------------------------------ INV-18
class Completion:
    """Tiny one-shot cell used to model the INV-18 peer at the seam."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._set = False
        self.value: Any = None

    def resolve(self, value: Any) -> None:
        with self._lock:
            if self._set:
                raise AdapterError("completion already resolved (one-shot)")
            self._set, self.value = True, value

    @property
    def done(self) -> bool:
        return self._set


def drain_to_completion(s: Stream, trailer: Completion, fold: Callable[[Any, Any], Any], init: Any) -> Any:
    """Read a stream to EOF and resolve the one-shot trailer with the folded result.

    A dropped writer resolves the trailer with the error instead -- never a silent value.
    """
    acc = init
    while True:
        try:
            v = s.read()
        except EndDropped as exc:
            trailer.resolve(exc)
            raise
        if v is None:
            trailer.resolve(acc)
            return acc
        if v is NOT_READY:
            raise AdapterError("stream not ready; drive with a waitable set")
        acc = fold(acc, v)


# ------------------------------------------------------------------ INV-20
class HttpBody:
    """Request/response body as a ``Stream[bytes]`` with credit-sized chunking."""

    def __init__(self, s: Stream, chunk: int = 16384) -> None:
        if s.element_type is not bytes:
            raise AdapterError("HTTP bodies are byte streams")
        if chunk <= 0:
            raise ValueError("chunk must be positive")
        self.s, self.chunk = s, chunk
        self._received: list[bytes] = []  # survives a NOT_READY so no chunk is lost

    def send(self, data: bytes) -> int:
        """Write as many chunks as current credit allows; returns bytes accepted."""
        sent = 0
        while sent < len(data) and self.s.credit > 0:
            self.s.write(bytes(data[sent:sent + self.chunk]))
            sent += min(self.chunk, len(data) - sent)
        return sent

    def receive_all(self) -> bytes:
        """Return the whole body once the writer ended; partial reads are retained."""
        while True:
            v = self.s.read()
            if v is None:
                body, self._received = b"".join(self._received), []
                return body
            if v is NOT_READY:
                raise AdapterError("body incomplete; writer has not ended",
                                   received=sum(map(len, self._received)))
            self._received.append(bytes(v))  # type: ignore[call-overload]  # element type checked at write


# ------------------------------------------------------------------ INV-19
class OsReadinessBridge:
    """Maps an OS readiness report ("n units may be consumed") onto reader credit.

    Credit granted never exceeds the stream's remaining ceiling, so an OS reporting a
    huge readiness value cannot break INV-17's bounded-memory guarantee.
    """

    def __init__(self, s: Stream) -> None:
        self.s = s

    def on_ready(self, units: int) -> int:
        if isinstance(units, bool) or not isinstance(units, int) or units < 0:
            raise AdapterError("readiness must be a non-negative int")
        room = self.s.config.max_credit - self.s.credit
        n = min(units, room)
        if n > 0:
            self.s.grant(n)
        return n


def reciprocity(own: Iterable[tuple[str, str]], sibling_deps: dict[str, list[tuple[str, str]]]) -> list[dict]:
    """Compare INV-17's declared dependencies with each sibling's declaration of INV-17."""
    inverse = {"upstream": "downstream", "downstream": "upstream", "peer": "peer"}
    report = []
    for name, rel in own:
        sid = name.split()[0]
        theirs = [r for n, r in sibling_deps.get(sid, []) if n.startswith("INV-17")]
        report.append({"sibling": sid, "inv17_says": rel, "sibling_says": theirs[0] if theirs else None,
                       "consistent": bool(theirs) and theirs[0] == inverse[rel]})
    return report
