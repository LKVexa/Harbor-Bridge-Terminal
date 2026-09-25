"""Wire-level structured error envelope PK_PROVIDER_ERROR/1 (M13).

One catalog maps every provider error code to retryability and an HTTP status,
so Python, HTTP and WIT/RPC peers agree.  Messages are length-bounded and never
carry configuration or secret material (callers pass only safe text).
"""
from __future__ import annotations

import secrets as _rnd
from dataclasses import dataclass

from ..schemas import check


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    retryable: bool
    http_status: int
    meaning: str


CATALOG: dict[str, ErrorSpec] = {s.code: s for s in [
    ErrorSpec("PK_PROVIDER_ERROR", False, 500, "unclassified provider failure"),
    ErrorSpec("PK_PROVIDER_NO_LINK", False, 404, "no established, non-revoked named link"),
    ErrorSpec("PK_PROVIDER_INVALID_LINK", False, 400, "link/operation failed validation"),
    ErrorSpec("PK_PROVIDER_UNAVAILABLE", True, 503, "backing capability unhealthy"),
    ErrorSpec("PK_PROVIDER_UNAUTHENTICATED", False, 401, "caller identity not proven"),
    ErrorSpec("PK_PROVIDER_FORBIDDEN", False, 403, "authorization decision absent, denied, stale or mismatched"),
    ErrorSpec("PK_PROVIDER_DEADLINE_EXCEEDED", True, 504, "call deadline elapsed"),
    ErrorSpec("PK_PROVIDER_CANCELLED", False, 499, "caller cancelled"),
    ErrorSpec("PK_PROVIDER_OVERLOADED", True, 429, "admission control / quota / rate limit shed the call"),
    ErrorSpec("PK_PROVIDER_CIRCUIT_OPEN", True, 503, "circuit breaker open for the backend"),
    ErrorSpec("PK_PROVIDER_IDEMPOTENCY_CONFLICT", False, 409, "idempotency key reused with different request"),
    ErrorSpec("PK_PROVIDER_FENCED", False, 409, "stale lease epoch / not the owner"),
    ErrorSpec("PK_PROVIDER_RESIDENCY", False, 403, "residency/locality policy forbids placement"),
    ErrorSpec("PK_PROVIDER_SECRET_UNAVAILABLE", True, 503, "secret reference could not be resolved"),
    ErrorSpec("PK_PROVIDER_DISABLED", False, 503, "provider or link administratively disabled/draining"),
    ErrorSpec("PK_PROVIDER_INCOMPATIBLE", False, 426, "no mutually supported contract version"),
    ErrorSpec("PK_PROVIDER_UNTRUSTED_ARTIFACT", False, 403, "implementation digest not allowlisted"),
    ErrorSpec("PK_PROVIDER_STATE_CORRUPT", False, 500, "durable state failed integrity check"),
    ErrorSpec("PK_PROVIDER_KEY_UNAVAILABLE", True, 503, "encryption key unavailable"),
]}


class ProviderFault(RuntimeError):
    """Runtime-layer failure carrying a catalogued code."""

    def __init__(self, code: str, message: str, *, retry_after_ms: int | None = None, **details):
        if code not in CATALOG:
            raise ValueError(f"uncatalogued error code {code}")
        super().__init__(message)
        self.code = code
        self.retry_after_ms = retry_after_ms
        self.details = {k: v for k, v in details.items() if isinstance(v, (str, int, bool))}


def new_correlation_id() -> str:
    return _rnd.token_hex(8)


def to_envelope(exc: BaseException, correlation_id: str | None = None) -> dict:
    code = getattr(exc, "code", "PK_PROVIDER_ERROR")
    if code not in CATALOG:
        code = "PK_PROVIDER_ERROR"
    spec = CATALOG[code]
    msg = str(exc)[:512] if code != "PK_PROVIDER_ERROR" else "internal provider error"
    env = {"schema": "PK_PROVIDER_ERROR/1", "code": code, "message": msg,
           "retryable": spec.retryable, "correlation_id": correlation_id or new_correlation_id()}
    ra = getattr(exc, "retry_after_ms", None)
    if isinstance(ra, int) and ra >= 0:
        env["retry_after_ms"] = ra
    det = getattr(exc, "details", None)
    if det:
        env["details"] = dict(det)
    check(env, "pk_provider_error")
    return env


def from_envelope(env: dict) -> ProviderFault:
    """Decode a peer's envelope; unknown codes from newer peers degrade to PK_PROVIDER_ERROR."""
    check(env, "pk_provider_error")
    code = env["code"] if env["code"] in CATALOG else "PK_PROVIDER_ERROR"
    return ProviderFault(code, env["message"], retry_after_ms=env.get("retry_after_ms"))


def http_status(code: str) -> int:
    return CATALOG.get(code, CATALOG["PK_PROVIDER_ERROR"]).http_status
