"""Stable, machine-readable error taxonomy for INV-36 (MC-06.004, INV-36-C026/C027).

Every refusal the transport, handshake, policy, configuration, health or
quarantine layers can raise maps to exactly one :class:`ErrorCode`.  Codes are
part of the external contract (``schema/error.schema.json``): values are never
reused, and the numeric ranges are reserved per layer:

====== ===================================
Range  Layer
====== ===================================
1xx    frame / session (PK_CTRL_FRAME/2)
2xx    stream framing (PK_CTRL_STREAM/1)
3xx    handshake (PK_CTRL_HS/1)
4xx    keys / custody
5xx    authorization / tenant policy
6xx    configuration
7xx    health / overload / retry
8xx    quarantine
9xx    gate / evidence / infrastructure
0xF000-0xFFFF  reserved for private extensions (never emitted by this package)
====== ===================================

``retryable`` tells a caller whether the *same* operation may be retried
(possibly after re-establishment); ``terminal`` marks integrity/identity
failures after which the session must be torn down.
"""
from __future__ import annotations

import enum
import json
from dataclasses import dataclass
from typing import Any, Mapping

MAX_DETAIL_CHARS = 256
MAX_DETAIL_FIELDS = 8


class Disposition(str, enum.Enum):
    SUCCESS = "success"
    DEGRADED = "degraded"
    RETRYABLE = "retryable"
    DENIED = "denied"
    PROTOCOL_ERROR = "protocol_error"
    INTEGRITY_FAILURE = "integrity_failure"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class _Code:
    number: int
    disposition: Disposition
    retryable: bool
    terminal: bool


class ErrorCode(enum.Enum):
    # 1xx frame/session
    AUTH_FAILURE = _Code(101, Disposition.INTEGRITY_FAILURE, False, True)
    REPLAY = _Code(102, Disposition.INTEGRITY_FAILURE, False, False)
    OUT_OF_ORDER = _Code(103, Disposition.PROTOCOL_ERROR, False, True)
    FRAME_TOO_LARGE = _Code(104, Disposition.PROTOCOL_ERROR, False, True)
    FRAME_FORMAT = _Code(105, Disposition.PROTOCOL_ERROR, False, True)
    SEQUENCE_EXHAUSTED = _Code(106, Disposition.RETRYABLE, True, True)
    SESSION_CLOSED = _Code(107, Disposition.RETRYABLE, True, True)
    MESSAGE_FORMAT = _Code(108, Disposition.PROTOCOL_ERROR, False, True)
    UNKNOWN_MESSAGE_TYPE = _Code(109, Disposition.DENIED, False, False)
    # 2xx stream
    STREAM_EOF = _Code(201, Disposition.RETRYABLE, True, True)
    STREAM_TRUNCATED = _Code(202, Disposition.PROTOCOL_ERROR, True, True)
    STREAM_LENGTH_INVALID = _Code(203, Disposition.PROTOCOL_ERROR, False, True)
    STREAM_TIMEOUT = _Code(204, Disposition.RETRYABLE, True, True)
    STREAM_RESET = _Code(205, Disposition.RETRYABLE, True, True)
    STREAM_UNAVAILABLE = _Code(206, Disposition.RETRYABLE, True, True)
    STREAM_BUSY = _Code(207, Disposition.PROTOCOL_ERROR, False, False)
    # 3xx handshake
    HS_IDENTITY = _Code(301, Disposition.DENIED, False, True)
    HS_TRUST_CHAIN = _Code(302, Disposition.DENIED, False, True)
    HS_ATTESTATION = _Code(303, Disposition.DENIED, False, True)
    HS_EXPIRED = _Code(304, Disposition.DENIED, False, True)
    HS_REVOKED = _Code(305, Disposition.DENIED, False, True)
    HS_NEGOTIATION = _Code(306, Disposition.PROTOCOL_ERROR, False, True)
    HS_TIMEOUT = _Code(307, Disposition.RETRYABLE, True, True)
    HS_POLICY = _Code(308, Disposition.DENIED, False, True)
    HS_REPLAY = _Code(309, Disposition.INTEGRITY_FAILURE, False, True)
    HS_FORMAT = _Code(310, Disposition.PROTOCOL_ERROR, False, True)
    HS_TRANSCRIPT = _Code(311, Disposition.INTEGRITY_FAILURE, False, True)
    HS_DEPENDENCY = _Code(312, Disposition.RETRYABLE, True, True)
    # 4xx keys
    KEY_UNAVAILABLE = _Code(401, Disposition.RETRYABLE, True, True)
    KEY_PERMISSION = _Code(402, Disposition.DENIED, False, True)
    KEY_INTEGRITY = _Code(403, Disposition.INTEGRITY_FAILURE, False, True)
    KEY_EPOCH = _Code(404, Disposition.DENIED, False, True)
    KEY_REVOKED = _Code(405, Disposition.DENIED, False, True)
    KEY_THROTTLED = _Code(406, Disposition.RETRYABLE, True, False)
    # 5xx authorization
    AUTHZ_DENIED = _Code(501, Disposition.DENIED, False, False)
    AUTHZ_CROSS_TENANT = _Code(502, Disposition.DENIED, False, False)
    AUTHZ_POLICY_UNAVAILABLE = _Code(503, Disposition.RETRYABLE, True, False)
    AUTHZ_POLICY_ROLLBACK = _Code(504, Disposition.DENIED, False, False)
    AUTHZ_RATE_LIMITED = _Code(505, Disposition.RETRYABLE, True, False)
    # 6xx config
    CONFIG_INVALID = _Code(601, Disposition.DENIED, False, False)
    CONFIG_ROLLBACK_DENIED = _Code(602, Disposition.DENIED, False, False)
    CONFIG_CONFLICT = _Code(603, Disposition.RETRYABLE, True, False)
    CONFIG_UNAUTHORIZED = _Code(604, Disposition.DENIED, False, False)
    # 7xx health / overload
    OVERLOADED = _Code(701, Disposition.RETRYABLE, True, False)
    CIRCUIT_OPEN = _Code(702, Disposition.RETRYABLE, True, False)
    RETRY_EXHAUSTED = _Code(703, Disposition.TERMINAL, False, False)
    DEADLINE_EXCEEDED = _Code(704, Disposition.RETRYABLE, True, False)
    NOT_READY = _Code(705, Disposition.RETRYABLE, True, False)
    CONNECTION_LIMIT = _Code(706, Disposition.RETRYABLE, True, False)
    # 8xx quarantine
    QUARANTINED = _Code(801, Disposition.DENIED, False, True)
    DIRECTIVE_INVALID = _Code(802, Disposition.DENIED, False, False)
    DIRECTIVE_SCOPE = _Code(803, Disposition.DENIED, False, False)
    # 9xx gate / infra
    GATE_UNAVAILABLE = _Code(901, Disposition.TERMINAL, False, False)
    GATE_SCHEMA = _Code(902, Disposition.TERMINAL, False, False)
    GATE_TIMEOUT = _Code(903, Disposition.TERMINAL, False, False)
    EVIDENCE_INVALID = _Code(904, Disposition.TERMINAL, False, False)

    @property
    def number(self) -> int:
        return self.value.number

    @property
    def disposition(self) -> Disposition:
        return self.value.disposition

    @property
    def retryable(self) -> bool:
        return self.value.retryable

    @property
    def terminal(self) -> bool:
        return self.value.terminal


_BY_NUMBER = {c.number: c for c in ErrorCode}
if len(_BY_NUMBER) != len(ErrorCode):  # pragma: no cover - import-time registry guard
    raise RuntimeError("duplicate error code number")


def code_by_number(number: int) -> ErrorCode:
    return _BY_NUMBER[number]


def _clip(value: Any) -> str | int | bool | None:
    if value is None or isinstance(value, (bool, int)):
        return value
    text = str(value)
    # Control characters are escaped so attacker-controlled detail cannot forge
    # log lines (MC-18.016).
    text = text.encode("unicode_escape", "backslashreplace").decode("ascii")
    return text[:MAX_DETAIL_CHARS]


class Inv36Error(Exception):
    """Base class carrying a stable :class:`ErrorCode` and bounded, redacted detail."""

    code: ErrorCode = ErrorCode.FRAME_FORMAT

    def __init__(self, message: str = "", *, code: ErrorCode | None = None, detail: Mapping[str, Any] | None = None,
                 retry_after_s: float | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        items = list((detail or {}).items())[:MAX_DETAIL_FIELDS]
        self.detail = {str(k)[:64]: _clip(v) for k, v in items}
        self.retry_after_s = retry_after_s

    def to_dict(self) -> dict[str, Any]:
        """Serialize per ``schema/error.schema.json`` revision 1."""
        out: dict[str, Any] = {
            "schema": "inv36.error/1",
            "code": self.code.name,
            "number": self.code.number,
            "disposition": self.code.disposition.value,
            "retryable": self.code.retryable,
            "terminal": self.code.terminal,
            "message": _clip(str(self)),
            "detail": self.detail,
        }
        if self.retry_after_s is not None and self.code.retryable:
            out["retry_after_s"] = round(float(self.retry_after_s), 3)
        return out

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def error_dict(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, Inv36Error):
        return exc.to_dict()
    return {
        "schema": "inv36.error/1",
        "code": "INTERNAL",
        "number": 0,
        "disposition": Disposition.TERMINAL.value,
        "retryable": False,
        "terminal": True,
        "message": _clip(type(exc).__name__),
        "detail": {},
    }
