"""Dependency-free RPC framing primitives for INV-61.

This module intentionally has no dependency on ``pk_core`` so protocol behavior
can be tested, fuzzed, and embedded independently of the inventory/gating layer.
It is an in-process reference codec/dispatcher, not a network transport.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
import threading
from typing import Any, Callable, Iterable

FRAME_FIELDS = frozenset({"interface", "version", "function", "fp", "args", "deadline"})
MAX_ARGS = 256
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{16}$")


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def fingerprint(params: Iterable[str], results: Iterable[str]) -> str:
    """Return a deterministic truncated SHA-256 signature fingerprint.

    Canonical JSON separators make the digest independent of incidental spacing.
    The 64-bit digest is a drift detector, not an authentication primitive.
    """
    payload = json.dumps(
        [list(params), list(results)],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def make_frame(
    interface: str,
    version: str,
    function: str,
    params: Iterable[str],
    results: Iterable[str],
    args: Iterable[Any],
    deadline: float,
) -> dict[str, Any]:
    """Build a validated reference frame."""
    arg_list = list(args)
    candidate = {
        "interface": interface,
        "version": version,
        "function": function,
        "fp": fingerprint(params, results),
        "args": arg_list,
        "deadline": deadline,
    }
    if validate_frame(candidate) is not None:
        raise ValueError("invalid frame fields")
    return candidate


def validate_frame(frame: object) -> str | None:
    """Return ``None`` for a structurally valid frame, else a stable reason code."""
    if not isinstance(frame, dict):
        return "not-object"
    if set(frame) != FRAME_FIELDS:
        return "field-set"
    if not all(_nonempty_string(frame[name]) for name in ("interface", "version", "function")):
        return "identifier"
    if not isinstance(frame["fp"], str) or _FINGERPRINT_RE.fullmatch(frame["fp"]) is None:
        return "fingerprint"
    if not isinstance(frame["args"], (list, tuple)):
        return "args-type"
    if len(frame["args"]) > MAX_ARGS:
        return "args-limit"
    if not _finite_number(frame["deadline"]):
        return "deadline"
    return None


@dataclass
class EndpointStats:
    calls: int = 0
    malformed: int = 0
    deadline_exceeded: int = 0
    unknown_function: int = 0
    version_mismatch: int = 0
    signature_mismatch: int = 0
    callee_trap: int = 0
    succeeded: int = 0


@dataclass
class Endpoint:
    """Reference receiver enforcing frame compatibility before dispatch."""

    interface: str
    version: str
    functions: dict[str, tuple[tuple[str, ...], tuple[str, ...], Callable[..., Any]]] = field(default_factory=dict)
    stats: EndpointStats = field(default_factory=EndpointStats)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def _count(self, name: str) -> None:
        # M25: counters are mutated under a lock so concurrent handle() calls never lose updates.
        with self._lock:
            setattr(self.stats, name, getattr(self.stats, name) + 1)

    @property
    def mismatches(self) -> int:
        """Backward-compatible aggregate signature mismatch counter."""
        return self.stats.signature_mismatch

    def export(
        self,
        name: str,
        params: Iterable[str],
        results: Iterable[str],
        impl: Callable[..., Any],
    ) -> None:
        if not _nonempty_string(name):
            raise ValueError("export name must be a non-empty string")
        if not callable(impl):
            raise TypeError("export implementation must be callable")
        with self._lock:
            if name in self.functions:
                raise ValueError(f"duplicate export: {name}")
            self.functions[name] = (tuple(params), tuple(results), impl)

    def handle(self, incoming: object, now: float) -> dict[str, Any]:
        self._count("calls")
        reason = validate_frame(incoming)
        if reason is not None or not _finite_number(now):
            self._count("malformed")
            return {"error": "malformed-frame", "code": reason or "clock"}

        # validate_frame() guarantees a dictionary at this point.
        frame = incoming

        if now >= frame["deadline"]:
            self._count("deadline_exceeded")
            return {"error": "deadline-exceeded"}
        if frame["interface"] != self.interface:
            self._count("unknown_function")
            return {"error": "unknown-interface"}
        if frame["version"] != self.version:
            self._count("version_mismatch")
            return {"error": "version-mismatch", "expected": self.version}

        fn = self.functions.get(frame["function"])
        if fn is None:
            self._count("unknown_function")
            return {"error": "unknown-function"}
        if frame["fp"] != fingerprint(fn[0], fn[1]):
            self._count("signature_mismatch")
            return {"error": "signature-mismatch"}

        try:
            result = fn[2](*frame["args"])
        except Exception:
            self._count("callee_trap")
            return {"error": "callee-trap"}

        self._count("succeeded")
        return {"ok": result}
