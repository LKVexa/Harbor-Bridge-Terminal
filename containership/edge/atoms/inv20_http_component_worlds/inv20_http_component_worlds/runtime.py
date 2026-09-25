"""Dependency-free runtime primitives for INV-20 HTTP component worlds.

These primitives intentionally do not import ``pk_core`` so their security and
streaming behavior can be verified in isolation.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import ipaddress
import re
from typing import Any, Callable, Deque, FrozenSet, Generic, Mapping, Optional, TypeVar

from .errors import Inv20Error

_HOST_RE = re.compile(r"^(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*\.?$")
T = TypeVar("T")


class EgressDenied(Inv20Error, PermissionError):
    """Raised when a component calls a host its world did not grant."""

    code = "E_EGRESS_DENIED"


class NoOutgoingCapability(Inv20Error, PermissionError):
    """Raised when a world imports no outgoing HTTP at all."""

    code = "E_NO_OUTGOING"


class InvalidHost(Inv20Error, ValueError):
    """Raised when an egress target is not a canonical host literal/name."""

    code = "E_INVALID_HOST"


class BodyTooLarge(Inv20Error, RuntimeError):
    """Raised when a streamed body exceeds the workload's configured limit."""

    code = "E_BODY_TOO_LARGE"


class CompletionAlreadyResolved(Inv20Error, RuntimeError):
    """Raised when a completion is resolved more than once."""

    code = "E_ALREADY_RESOLVED"


def canonical_host(host: str) -> str:
    """Return a canonical hostname/IP literal, rejecting URLs and ambiguous input."""
    if not isinstance(host, str):
        raise TypeError("host must be a string")
    candidate = host.strip().lower()
    if not candidate or candidate != host.lower():
        raise InvalidHost("host must not contain surrounding whitespace")
    if any(token in candidate for token in ("://", "/", "@", "?", "#", "%", "\\")):
        raise InvalidHost("expected a host only, not a URL or authority")
    # Bracketed IPv6 is an authority representation, not a host literal here.
    if candidate.startswith("[") or candidate.endswith("]"):
        raise InvalidHost("IPv6 host literals must be unbracketed")
    try:
        return ipaddress.ip_address(candidate).compressed
    except ValueError:
        pass
    candidate = candidate.rstrip(".")
    if not _HOST_RE.fullmatch(candidate):
        raise InvalidHost(f"invalid host: {host!r}")
    return candidate


@dataclass
class BodyStream:
    """Bounded chunk stream with O(1) forwarding and defensive byte copies."""

    limit: int = 1 << 20
    chunks: Deque[bytes] = field(default_factory=deque)
    total: int = 0
    peak_buffered: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.limit, int) or isinstance(self.limit, bool) or self.limit < 0:
            raise ValueError("body limit must be a non-negative integer")

    def write(self, chunk: bytes | bytearray | memoryview) -> None:
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise TypeError(f"body chunks are bytes-like, got {type(chunk).__name__}")
        immutable = bytes(chunk)
        if self.total + len(immutable) > self.limit:
            raise BodyTooLarge(f"body would exceed {self.limit} bytes")
        self.total += len(immutable)
        self.chunks.append(immutable)
        self.peak_buffered = max(self.peak_buffered, len(self.chunks))

    def forward(self) -> bytes:
        """Return the next buffered chunk without copying the rest of the body."""
        return self.chunks.popleft() if self.chunks else b""

    @property
    def buffered_chunks(self) -> int:
        return len(self.chunks)


@dataclass
class Completion(Generic[T]):
    """Single-assignment completion used for response/request trailers."""

    _resolved: bool = False
    _value: Optional[T] = None

    def resolve(self, value: T) -> None:
        if self._resolved:
            raise CompletionAlreadyResolved("completion already resolved")
        self._value = value
        self._resolved = True

    @property
    def resolved(self) -> bool:
        return self._resolved

    def result(self) -> T:
        if not self._resolved:
            raise RuntimeError("completion is not resolved")
        return self._value  # type: ignore[return-value]


@dataclass
class HttpMessage:
    """Minimal HTTP message surface: streaming body plus trailer completion."""

    body: BodyStream = field(default_factory=BodyStream)
    trailers: Completion[Mapping[str, str]] = field(default_factory=Completion)


@dataclass
class HttpWorld:
    """One component's HTTP world: exported handler and explicit egress capability."""

    name: str
    handler: Optional[Callable[[Any], Any]] = None
    allowed_hosts: FrozenSet[str] = frozenset()
    outgoing_granted: bool = False
    egress_denials: int = 0
    handled: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("world name must be a non-empty string")
        canonical = frozenset(canonical_host(host) for host in self.allowed_hosts)
        if canonical and not self.outgoing_granted:
            raise ValueError("allowed_hosts requires outgoing_granted=True")
        self.allowed_hosts = canonical

    def export_handler(self, fn: Callable[[Any], Any]) -> None:
        if self.handler is not None:
            raise ValueError(f"world {self.name} already exports a handler")
        if not callable(fn):
            raise TypeError(f"world {self.name}: handler must be callable")
        self.handler = fn

    def handle(self, request: Any) -> Any:
        if self.handler is None:
            raise RuntimeError(f"world {self.name} exports no handler")
        self.handled += 1
        return self.handler(request)

    def fetch(self, host: str) -> tuple[str, str]:
        if not self.outgoing_granted:
            raise NoOutgoingCapability(f"world {self.name} imports no outgoing HTTP")
        canonical = canonical_host(host)
        if canonical not in self.allowed_hosts:
            self.egress_denials += 1
            raise EgressDenied(f"{canonical} is not in world {self.name}'s allow-list")
        return ("ok", canonical)
