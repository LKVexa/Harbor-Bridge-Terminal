"""Stable error taxonomy and public error envelope (PK_CHAIN_ERROR/1).

GAP-041. Every failure that crosses the INV-21 public call path -- whether it
was raised by the chainer itself, a local handler, the capability provider or
the remote transport -- is normalised to a :class:`ChainError` subclass with a
stable ``code``, a ``category``, a ``retriable`` flag and an ``origin`` layer.
Raw exception text, stack traces and details are kept in *protected*
diagnostics and are never placed in the public envelope.

Codes are append-only: a retired code is listed in ``RETIRED_CODES`` and must
never be reused with a different meaning.
"""
from __future__ import annotations

import traceback
from typing import Any, Mapping, Optional

ERROR_SCHEMA = "PK_CHAIN_ERROR/1"
MAX_MESSAGE_LEN = 256
MAX_DETAIL_KEYS = 16
MAX_DETAIL_VALUE_LEN = 128

# category -> default retriable
CATEGORIES = {
    "validation": False,
    "authentication": False,
    "authorization": False,
    "isolation": False,
    "residency": True,
    "bounds": False,
    "overload": True,
    "deadline": False,
    "cancelled": False,
    "handler": False,
    "provider": True,
    "transport": True,
    "protocol": False,
    "lifecycle": True,
    "internal": False,
}

RETIRED_CODES: frozenset[str] = frozenset()


class ChainError(RuntimeError):
    """Base class for stable, machine-readable local-chain failures."""

    code = "PK_CHAIN_ERROR"
    category = "internal"
    retriable: Optional[bool] = None
    origin = "chain"

    def __init__(self, message: str = "", **details: Any) -> None:
        super().__init__(message)
        self.details = details
        self.correlation_id: Optional[str] = details.get("trace_id")
        self._diagnostics: Optional[str] = None

    @property
    def is_retriable(self) -> bool:
        if self.retriable is not None:
            return self.retriable
        return CATEGORIES.get(self.category, False)

    def envelope(self) -> dict:
        """Sanitised public envelope, safe to cross a trust boundary."""
        return {
            "schema": ERROR_SCHEMA,
            "code": self.code,
            "category": self.category,
            "retriable": self.is_retriable,
            "origin": self.origin,
            "message": _clip(str(self.args[0]) if self.args else self.code, MAX_MESSAGE_LEN),
            "correlation_id": self.correlation_id,
            "details": _sanitize_details(self.details),
        }

    @property
    def diagnostics(self) -> Optional[str]:
        """Protected diagnostics (stack of the wrapped cause). Never public."""
        return self._diagnostics


def _clip(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


_PUBLIC_DETAIL_KEYS = {
    "callee", "depth", "max_depth", "tenant", "callee_tenant", "caller_tenant",
    "limit", "reason", "state", "epoch", "retry_after_ms", "attempts", "schema",
    "field", "existing_tenant", "requested_tenant", "trace_id",
}


def _sanitize_details(details: Mapping[str, Any]) -> dict:
    out = {}
    for key in sorted(details):
        if key not in _PUBLIC_DETAIL_KEYS or len(out) >= MAX_DETAIL_KEYS:
            continue
        value = details[key]
        if isinstance(value, (bool, int, float)) or value is None:
            out[key] = value
        else:
            out[key] = _clip(str(value), MAX_DETAIL_VALUE_LEN)
    return out


def _define(name: str, code: str, category: str, *, base=ChainError, retriable=None, origin="chain"):
    attrs = {"code": code, "category": category, "origin": origin}
    if retriable is not None:
        attrs["retriable"] = retriable
    return type(name, (base,), attrs)


class _PermissionChainError(PermissionError, ChainError):
    def __init__(self, message: str = "", **details: Any) -> None:
        ChainError.__init__(self, message, **details)


class _ValueChainError(ValueError, ChainError):
    def __init__(self, message: str = "", **details: Any) -> None:
        ChainError.__init__(self, message, **details)


ValidationFailed = _define("ValidationFailed", "PK_CHAIN_INVALID_REQUEST", "validation", base=_ValueChainError)
SchemaIncompatible = _define("SchemaIncompatible", "PK_CHAIN_SCHEMA_INCOMPATIBLE", "protocol")
Unauthenticated = _define("Unauthenticated", "PK_CHAIN_UNAUTHENTICATED", "authentication", base=_PermissionChainError)
CapabilityRefused = _define("CapabilityRefused", "PK_CHAIN_CAPABILITY_REFUSED", "authorization", base=_PermissionChainError)
CrossTenantChain = _define("CrossTenantChain", "PK_CHAIN_CROSS_TENANT", "isolation", base=_PermissionChainError)
ChainTooDeep = _define("ChainTooDeep", "PK_CHAIN_DEPTH_EXCEEDED", "bounds")
ChainCycle = _define("ChainCycle", "PK_CHAIN_CYCLE", "bounds")
ResidencyStale = _define("ResidencyStale", "PK_CHAIN_RESIDENCY_STALE", "residency")
Overloaded = _define("Overloaded", "PK_CHAIN_OVERLOADED", "overload")
CircuitOpen = _define("CircuitOpen", "PK_CHAIN_CIRCUIT_OPEN", "overload")
DeadlineExceeded = _define("DeadlineExceeded", "PK_CHAIN_DEADLINE_EXCEEDED", "deadline")
Cancelled = _define("Cancelled", "PK_CHAIN_CANCELLED", "cancelled")
HandlerFailed = _define("HandlerFailed", "PK_CHAIN_HANDLER_FAILED", "handler", origin="handler")
ProviderUnavailable = _define("ProviderUnavailable", "PK_CHAIN_PROVIDER_UNAVAILABLE", "provider", origin="policy")
TransportUnavailable = _define("TransportUnavailable", "PK_CHAIN_TRANSPORT_UNAVAILABLE", "transport", origin="transport")
RemoteProtocolError = _define("RemoteProtocolError", "PK_CHAIN_REMOTE_PROTOCOL", "protocol", origin="transport")
NotReady = _define("NotReady", "PK_CHAIN_NOT_READY", "lifecycle")
Quarantined = _define("Quarantined", "PK_CHAIN_QUARANTINED", "lifecycle", retriable=False)
InternalError = _define("InternalError", "PK_CHAIN_INTERNAL", "internal")

ALL_ERRORS = (
    ValidationFailed, SchemaIncompatible, Unauthenticated, CapabilityRefused, CrossTenantChain,
    ChainTooDeep, ChainCycle, ResidencyStale, Overloaded, CircuitOpen, DeadlineExceeded,
    Cancelled, HandlerFailed, ProviderUnavailable, TransportUnavailable, RemoteProtocolError,
    NotReady, Quarantined, InternalError,
)
CODE_TO_CLASS = {cls.code: cls for cls in ALL_ERRORS}
STABLE_CODES = tuple(sorted(CODE_TO_CLASS))


def normalize(exc: BaseException, *, origin: str = "handler", correlation_id: Optional[str] = None) -> ChainError:
    """Map any exception to a stable ChainError; raw text goes to diagnostics only."""
    if isinstance(exc, ChainError):
        if correlation_id and not exc.correlation_id:
            exc.correlation_id = correlation_id
        return exc
    import asyncio
    if isinstance(exc, (asyncio.CancelledError,)):
        err: ChainError = Cancelled("call cancelled")
    elif isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        err = DeadlineExceeded("deadline exceeded")
    elif origin == "transport":
        err = TransportUnavailable("remote transport failed")
    elif origin == "policy":
        err = ProviderUnavailable("capability provider failed")
    else:
        err = HandlerFailed("handler raised " + type(exc).__name__)
    err.correlation_id = correlation_id
    err._diagnostics = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-8192:]
    err.__cause__ = exc
    return err


def from_envelope(env: Mapping[str, Any]) -> ChainError:
    """Rebuild a ChainError from a public envelope (remote side). Unknown -> protocol error."""
    if not isinstance(env, Mapping) or env.get("schema") != ERROR_SCHEMA:
        return RemoteProtocolError("malformed remote error envelope")
    cls = CODE_TO_CLASS.get(env.get("code"))
    if cls is None:
        return RemoteProtocolError("unknown remote error code")
    details = env.get("details") if isinstance(env.get("details"), Mapping) else {}
    err = cls(_clip(str(env.get("message", "")), MAX_MESSAGE_LEN), **_sanitize_details(details))
    err.correlation_id = env.get("correlation_id") if isinstance(env.get("correlation_id"), str) else None
    return err
