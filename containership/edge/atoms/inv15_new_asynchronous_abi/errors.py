"""Machine-readable error envelope for INV-15 (component 4, 12).

Every refusal or failure at the ABI boundary maps to exactly one stable
numeric code. Numeric values are permanent: a value, once assigned, is never
reused for a different meaning. Ranges:

* 0            OK (never raised)
* 1..63        core ABI codes (this module)
* 64..127      reserved for future core codes
* 128..191     reserved for adjacent layers (INV-16/17/18)
* 192..254     implementation-private, never on the wire
* 255          FORBIDDEN (sentinel poison value; never assigned)

Detail strings are diagnostic only. Callers MUST branch on ``code`` and never
parse ``detail``.
"""
from __future__ import annotations

from enum import IntEnum


class ErrorCode(IntEnum):
    OK = 0
    NOT_READY = 1
    FOREIGN_HANDLE = 2
    HANDLE_CONSUMED = 3
    BUDGET_EXHAUSTED = 4
    WAIT_TIMEOUT = 5
    CALL_TIMEOUT = 6
    DEADLINE_EXCEEDED = 7
    CANCELLED = 8
    TRAPPED = 9
    HOST_FAILURE = 10
    UNSUPPORTED_VERSION = 11
    WAIT_SET_TOO_LARGE = 12
    DRAINING = 13
    DISABLED = 14
    INVALIDATED = 15
    RNG_UNAVAILABLE = 16
    MALFORMED = 17
    MEMORY_EXHAUSTED = 18
    DUPLICATE_PUBLICATION = 19
    INVALID_ARGUMENT = 20
    HANDLE_SPACE_EXHAUSTED = 21
    REPLAYED = 22
    UNSUPPORTED_FEATURE = 23


FORBIDDEN_CODES = frozenset({255})
RESERVED_RANGES = ((64, 127), (128, 191), (192, 254))

RETRYABLE = frozenset({
    ErrorCode.NOT_READY, ErrorCode.BUDGET_EXHAUSTED, ErrorCode.WAIT_TIMEOUT,
    ErrorCode.MEMORY_EXHAUSTED, ErrorCode.DRAINING,
})


class AbiError(RuntimeError):
    """Base ABI error. ``code`` is authoritative; ``detail`` is diagnostic."""

    code: ErrorCode = ErrorCode.HOST_FAILURE

    def __init__(self, detail: str = "", *, code: ErrorCode | None = None):
        if code is not None:
            self.code = ErrorCode(code)
        self.detail = str(detail)[:256]
        super().__init__(f"{self.code.name}: {self.detail}")

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE

    def envelope(self) -> dict:
        return {"code": int(self.code), "name": self.code.name,
                "retryable": self.retryable, "detail": self.detail}


def _mk(name: str, code: ErrorCode):
    cls = type(name, (AbiError,), {"code": code, "__doc__": f"{code.name} ({int(code)})"})
    return cls


NotReady = _mk("NotReady", ErrorCode.NOT_READY)
ForeignHandleError = _mk("ForeignHandleError", ErrorCode.FOREIGN_HANDLE)
HandleConsumedError = _mk("HandleConsumedError", ErrorCode.HANDLE_CONSUMED)
BudgetExhaustedError = _mk("BudgetExhaustedError", ErrorCode.BUDGET_EXHAUSTED)
WaitTimeout = _mk("WaitTimeout", ErrorCode.WAIT_TIMEOUT)
CallTimeout = _mk("CallTimeout", ErrorCode.CALL_TIMEOUT)
DeadlineExceeded = _mk("DeadlineExceeded", ErrorCode.DEADLINE_EXCEEDED)
Cancelled = _mk("Cancelled", ErrorCode.CANCELLED)
CalleeTrapped = _mk("CalleeTrapped", ErrorCode.TRAPPED)
HostFailure = _mk("HostFailure", ErrorCode.HOST_FAILURE)
UnsupportedVersion = _mk("UnsupportedVersion", ErrorCode.UNSUPPORTED_VERSION)
WaitSetTooLargeError = _mk("WaitSetTooLargeError", ErrorCode.WAIT_SET_TOO_LARGE)
Draining = _mk("Draining", ErrorCode.DRAINING)
Disabled = _mk("Disabled", ErrorCode.DISABLED)
Invalidated = _mk("Invalidated", ErrorCode.INVALIDATED)
RngUnavailable = _mk("RngUnavailable", ErrorCode.RNG_UNAVAILABLE)
Malformed = _mk("Malformed", ErrorCode.MALFORMED)
MemoryExhausted = _mk("MemoryExhausted", ErrorCode.MEMORY_EXHAUSTED)
DuplicatePublication = _mk("DuplicatePublication", ErrorCode.DUPLICATE_PUBLICATION)
InvalidArgument = _mk("InvalidArgument", ErrorCode.INVALID_ARGUMENT)
HandleSpaceExhaustedError = _mk("HandleSpaceExhaustedError", ErrorCode.HANDLE_SPACE_EXHAUSTED)
Replayed = _mk("Replayed", ErrorCode.REPLAYED)
UnsupportedFeature = _mk("UnsupportedFeature", ErrorCode.UNSUPPORTED_FEATURE)

BY_CODE = {cls.code: cls for cls in AbiError.__subclasses__()}


def from_envelope(env: dict) -> AbiError:
    code = ErrorCode(int(env["code"]))
    return BY_CODE[code](env.get("detail", ""))


class CancelReason(IntEnum):
    """Bounded, stable cancellation cause taxonomy (component 12)."""

    UNSPECIFIED = 0
    CALLER_REQUESTED = 1
    CALLER_GONE = 2
    DEADLINE = 3
    CALL_TIMEOUT = 4
    PARENT_CANCELLED = 5
    DRAIN = 6
    TEARDOWN = 7
    HOST_SHUTDOWN = 8
    POLICY = 9
    EMERGENCY_DISABLE = 10
    OTHER = 254


class CancelAck(IntEnum):
    """Terminal cancellation acknowledgement (component 11).

    ``PROPAGATED`` means: recorded, the subtask is terminal CANCELLED in the host
    table, and the producer's publication is refused from this point on. It does
    NOT mean the callee's external side effects were stopped; the reference
    host has no way to stop them and does not claim to.
    """

    PROPAGATED = 1
    COMPLETED_BEFORE_CANCEL = 2
    ALREADY_TERMINAL = 3
    UNABLE_TO_CANCEL = 4
