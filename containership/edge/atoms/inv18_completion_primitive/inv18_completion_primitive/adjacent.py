"""Adjacent-layer test adapters for INV-12/15/16/17/20 (C030, C083).

These are *contract doubles*: each reproduces the interface the adjacent
element is declared (in ``contract.py``) to present to INV-18, so the
integration paths can be exercised in unit CI.  They are not the real
elements; a higher CI tier must run the same scenarios against the real
components (see ``conformance/INTEGRATION_MATRIX.json``, tier ``real``), and
the release gate refuses to count this tier as satisfying that one.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Callable, Iterable

from .errors import ErrorRecord, FutureError, Rejected, from_exception
from .runtime import ReceiverCap, ResolverCap, Runtime
from .telemetry import TraceContext

LAYER_CONTRACTS = {
    "INV-15": "upstream: future readiness is reported through waitable sets",
    "INV-12": "upstream: lowers and lifts the resolved value",
    "INV-17": "peer: the many-shot counterpart to this primitive",
    "INV-20": "downstream: trailers and status resolve as completions",
    "INV-16": "downstream: an async function's return is a completion",
}
SUPPORTED_ADJACENT_CONTRACT = {"INV-12": 1, "INV-15": 1, "INV-16": 1, "INV-17": 1, "INV-20": 1}


def check_layer_version(layer: str, offered: int) -> int:
    want = SUPPORTED_ADJACENT_CONTRACT.get(layer)
    if want is None:
        raise Rejected(f"unknown adjacent layer {layer}", code="INVALID_ARGUMENT")
    if offered != want:
        raise Rejected(f"{layer} contract v{offered} unsupported", code="INCOMPATIBLE_VERSION")
    return want


class WaitableSet:
    """INV-15 double: readiness polling over many receivers."""

    def __init__(self, rt: Runtime):
        self.rt = rt
        self._members: dict[str, ReceiverCap] = {}

    def join(self, cap: ReceiverCap) -> None:
        self.rt.inspect(cap)          # capability check
        self._members[cap.future_id] = cap

    def poll(self, timeout: float = 0.0) -> list[ReceiverCap]:
        ready = [c for c in self._members.values() if self.rt.wait(c, 0)]
        if not ready and timeout:
            first = next(iter(self._members.values()), None)
            if first is not None and self.rt.wait(first, timeout):
                ready = [first]
        for c in ready:
            self._members.pop(c.future_id, None)
        return ready


class Codec:
    """INV-12 double: lower a value to canonical bytes and lift it back."""

    version = 1

    @staticmethod
    def lower(value: Any) -> bytes:
        return json.dumps({"v": value}, sort_keys=True, separators=(",", ":")).encode()

    @staticmethod
    def lift(blob: bytes, value_type: type) -> Any:
        try:
            v = json.loads(blob)["v"]
        except Exception as exc:
            raise Rejected("cannot lift value", code="INVALID_ARGUMENT") from exc
        if value_type is float and isinstance(v, int):
            v = float(v)
        if not isinstance(v, value_type) or (isinstance(v, bool) and value_type is not bool):
            raise Rejected("lifted value has wrong type", code="TYPE_MISMATCH")
        return v


def async_call(rt: Runtime, fn: Callable[[], Any], value_type: type, *, tenant: str = "default",
               trace: TraceContext | None = None) -> tuple[ReceiverCap, threading.Thread]:
    """INV-16 double: an async function's return is a completion.

    Return -> resolve; raised exception -> structured error resolution;
    a producer that dies without either (``SystemExit`` in the worker) drops
    its resolver capability -> abandonment reaches the receiver.
    """
    rcap, qcap = rt.create(value_type, tenant=tenant, trace=trace)
    holder = [rcap]
    del rcap

    def run():
        cap = holder.pop()
        try:
            v = fn()
        except SystemExit:           # simulated producer crash: capability dropped unresolved
            del cap
            return
        except BaseException as exc:  # noqa: BLE001
            rec = from_exception(exc)
            rt.resolve_error(cap, f"{rec.code}: {rec.message or type(exc).__name__}")
            return
        rt.resolve(cap, v)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return qcap, t


class Stream:
    """INV-17 double: a many-valued stream."""

    def __init__(self, items: Iterable[Any]):
        self._it = iter(items)

    def next(self):
        return next(self._it)


def completion_from_stream(rt: Runtime, stream: Stream, value_type: type) -> ReceiverCap:
    """Peer boundary: a stream converts to a completion only if it carries exactly one value."""
    rcap, qcap = rt.create(value_type)
    try:
        first = stream.next()
    except StopIteration:
        rt.abandon(rcap)
        return qcap
    try:
        stream.next()
    except StopIteration:
        rt.resolve(rcap, first)
    else:
        rt.resolve_error(rcap, "INVALID_ARGUMENT: stream carried more than one value")
    return qcap


def http_trailers(rt: Runtime, response_chunks: Iterable[bytes | dict], *, trace: TraceContext | None = None
                  ) -> ReceiverCap:
    """INV-20 double: trailers/status resolve a completion.

    A final ``dict`` chunk is the trailer block ``{"status": int}``; a body that
    ends without trailers (connection drop) abandons the completion.
    """
    rcap, qcap = rt.create(int, trace=trace)
    trailers = None
    for chunk in response_chunks:
        if isinstance(chunk, dict):
            trailers = chunk
    if trailers is None:
        rt.abandon(rcap)
    elif isinstance(trailers.get("status"), int) and not isinstance(trailers.get("status"), bool):
        st = trailers["status"]
        if st >= 500:
            rt.resolve_error(rcap, f"DEPENDENCY_UNAVAILABLE: upstream status {st}")
        else:
            rt.resolve(rcap, st)
    else:
        rt.resolve_error(rcap, "INVALID_ARGUMENT: malformed trailers")
    return qcap
