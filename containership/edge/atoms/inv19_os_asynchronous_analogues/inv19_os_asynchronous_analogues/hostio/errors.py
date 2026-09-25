"""MC-12 - Structured error translation taxonomy (PK_ASYNC_ERROR/1).

Every native failure reaches callers as a :class:`CanonicalError` carrying a
stable machine code, the source backend, the raw native code, and structured
retry/transient/cancel/timeout classification.  Human messages are separate
from codes, host ``strerror`` text is never part of the contract, and unknown
codes become ``UNKNOWN_HOST_ERROR`` (counted, never success).
"""
from __future__ import annotations

import errno as _errno
import threading
from dataclasses import asdict, dataclass
from enum import Enum

SCHEMA = "PK_ASYNC_ERROR/1"


class Code(str, Enum):
    WOULD_BLOCK = "WOULD_BLOCK"
    INTERRUPTED = "INTERRUPTED"
    CONNECTION_RESET = "CONNECTION_RESET"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    CONNECTION_ABORTED = "CONNECTION_ABORTED"
    BROKEN_PIPE = "BROKEN_PIPE"
    NOT_CONNECTED = "NOT_CONNECTED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    BAD_DESCRIPTOR = "BAD_DESCRIPTOR"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    NO_MEMORY = "NO_MEMORY"
    IO_ERROR = "IO_ERROR"
    NOT_FOUND = "NOT_FOUND"
    HOST_UNREACHABLE = "HOST_UNREACHABLE"
    NETWORK_DOWN = "NETWORK_DOWN"
    ADDRESS_IN_USE = "ADDRESS_IN_USE"
    OVERLOADED = "OVERLOADED"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNKNOWN_HOST_ERROR = "UNKNOWN_HOST_ERROR"


# code -> (retryable, transient)
_CLASS: dict[Code, tuple[bool, bool]] = {
    Code.WOULD_BLOCK: (True, True), Code.INTERRUPTED: (True, True),
    Code.CONNECTION_RESET: (False, False), Code.CONNECTION_REFUSED: (True, True),
    Code.CONNECTION_ABORTED: (False, False), Code.BROKEN_PIPE: (False, False),
    Code.NOT_CONNECTED: (False, False), Code.TIMED_OUT: (True, True),
    Code.CANCELLED: (False, False), Code.BAD_DESCRIPTOR: (False, False),
    Code.INVALID_ARGUMENT: (False, False), Code.PERMISSION_DENIED: (False, False),
    Code.NOT_SUPPORTED: (False, False), Code.RESOURCE_EXHAUSTED: (True, True),
    Code.NO_MEMORY: (True, True), Code.IO_ERROR: (False, False),
    Code.NOT_FOUND: (False, False), Code.HOST_UNREACHABLE: (True, True),
    Code.NETWORK_DOWN: (True, True), Code.ADDRESS_IN_USE: (False, False),
    Code.OVERLOADED: (True, True), Code.UNAUTHORIZED: (False, False),
    Code.UNKNOWN_HOST_ERROR: (False, False),
}


def _e(name: str) -> int | None:
    return getattr(_errno, name, None)


# POSIX errno (Linux and BSD/macOS share symbolic names; numeric values differ,
# so the table is built from the running host's errno module, and a fixed
# per-OS golden table lives in schemas/fixtures/errno_golden.json).
_POSIX_NAMES: dict[str, Code] = {
    "EAGAIN": Code.WOULD_BLOCK, "EWOULDBLOCK": Code.WOULD_BLOCK, "EINPROGRESS": Code.WOULD_BLOCK,
    "EINTR": Code.INTERRUPTED, "ECONNRESET": Code.CONNECTION_RESET,
    "ECONNREFUSED": Code.CONNECTION_REFUSED, "ECONNABORTED": Code.CONNECTION_ABORTED,
    "EPIPE": Code.BROKEN_PIPE, "ENOTCONN": Code.NOT_CONNECTED, "ETIMEDOUT": Code.TIMED_OUT,
    "ETIME": Code.TIMED_OUT, "ECANCELED": Code.CANCELLED, "EBADF": Code.BAD_DESCRIPTOR,
    "EINVAL": Code.INVALID_ARGUMENT, "EFAULT": Code.INVALID_ARGUMENT,
    "EPERM": Code.PERMISSION_DENIED, "EACCES": Code.PERMISSION_DENIED,
    "ENOSYS": Code.NOT_SUPPORTED, "EOPNOTSUPP": Code.NOT_SUPPORTED, "ENOTSUP": Code.NOT_SUPPORTED,
    "EMFILE": Code.RESOURCE_EXHAUSTED, "ENFILE": Code.RESOURCE_EXHAUSTED,
    "ENOBUFS": Code.RESOURCE_EXHAUSTED, "EBUSY": Code.RESOURCE_EXHAUSTED,
    "ENOMEM": Code.NO_MEMORY, "EIO": Code.IO_ERROR, "ENOENT": Code.NOT_FOUND,
    "EHOSTUNREACH": Code.HOST_UNREACHABLE, "ENETUNREACH": Code.HOST_UNREACHABLE,
    "ENETDOWN": Code.NETWORK_DOWN, "EADDRINUSE": Code.ADDRESS_IN_USE,
}
POSIX_ERRNO: dict[int, Code] = {}
for _n, _c in _POSIX_NAMES.items():
    _v = _e(_n)
    if _v is not None:
        POSIX_ERRNO.setdefault(_v, _c)

# Win32 GetLastError values (stable, documented numeric constants).
WIN32: dict[int, Code] = {
    5: Code.PERMISSION_DENIED,      # ERROR_ACCESS_DENIED
    6: Code.BAD_DESCRIPTOR,         # ERROR_INVALID_HANDLE
    8: Code.NO_MEMORY,              # ERROR_NOT_ENOUGH_MEMORY
    2: Code.NOT_FOUND,              # ERROR_FILE_NOT_FOUND
    87: Code.INVALID_ARGUMENT,      # ERROR_INVALID_PARAMETER
    109: Code.BROKEN_PIPE,          # ERROR_BROKEN_PIPE
    121: Code.TIMED_OUT,            # ERROR_SEM_TIMEOUT
    258: Code.TIMED_OUT,            # WAIT_TIMEOUT
    995: Code.CANCELLED,            # ERROR_OPERATION_ABORTED
    996: Code.WOULD_BLOCK,          # ERROR_IO_INCOMPLETE
    997: Code.WOULD_BLOCK,          # ERROR_IO_PENDING (never terminal; see iocp)
    1167: Code.NOT_CONNECTED,       # ERROR_DEVICE_NOT_CONNECTED
    1225: Code.CONNECTION_REFUSED,  # ERROR_CONNECTION_REFUSED
    1236: Code.CONNECTION_ABORTED,  # ERROR_CONNECTION_ABORTED
    1450: Code.RESOURCE_EXHAUSTED,  # ERROR_NO_SYSTEM_RESOURCES
    50: Code.NOT_SUPPORTED,         # ERROR_NOT_SUPPORTED
    1168: Code.NOT_FOUND,           # ERROR_NOT_FOUND
}
# Winsock WSA* values.
WINSOCK: dict[int, Code] = {
    10004: Code.INTERRUPTED, 10009: Code.BAD_DESCRIPTOR, 10013: Code.PERMISSION_DENIED,
    10022: Code.INVALID_ARGUMENT, 10024: Code.RESOURCE_EXHAUSTED, 10035: Code.WOULD_BLOCK,
    10036: Code.WOULD_BLOCK, 10038: Code.BAD_DESCRIPTOR, 10045: Code.NOT_SUPPORTED,
    10048: Code.ADDRESS_IN_USE, 10050: Code.NETWORK_DOWN, 10051: Code.HOST_UNREACHABLE,
    10053: Code.CONNECTION_ABORTED, 10054: Code.CONNECTION_RESET, 10055: Code.RESOURCE_EXHAUSTED,
    10057: Code.NOT_CONNECTED, 10060: Code.TIMED_OUT, 10061: Code.CONNECTION_REFUSED,
    10065: Code.HOST_UNREACHABLE,
}
# NTSTATUS values surfaced in OVERLAPPED.Internal.
NTSTATUS: dict[int, Code] = {
    0xC0000120: Code.CANCELLED,          # STATUS_CANCELLED
    0xC0000008: Code.BAD_DESCRIPTOR,     # STATUS_INVALID_HANDLE
    0xC000020D: Code.CONNECTION_RESET,   # STATUS_CONNECTION_RESET
    0xC0000236: Code.CONNECTION_REFUSED, # STATUS_CONNECTION_REFUSED
    0xC0000241: Code.CONNECTION_ABORTED, # STATUS_CONNECTION_ABORTED
    0xC00000B5: Code.TIMED_OUT,          # STATUS_IO_TIMEOUT
    0xC0000017: Code.NO_MEMORY,          # STATUS_NO_MEMORY
    0xC0000022: Code.PERMISSION_DENIED,  # STATUS_ACCESS_DENIED
}

TABLES = {"posix": POSIX_ERRNO, "win32": WIN32, "winsock": WINSOCK, "ntstatus": NTSTATUS}
SOURCE_FOR_BACKEND = {"io_uring": "posix", "epoll": "posix", "kqueue": "posix",
                      "portable": "posix", "iocp": "win32"}


@dataclass(frozen=True)
class CanonicalError:
    code: str
    backend: str
    native_space: str
    native_code: int | None
    retryable: bool
    transient: bool
    cancelled: bool
    timeout: bool
    message: str
    schema: str = SCHEMA

    def to_dict(self) -> dict:
        return asdict(self)


class _Counter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.value = 0

    def inc(self) -> None:
        with self._lock:
            self.value += 1


untranslatable_errors = _Counter()

_MAX_SAFE = 2**32


def translate(backend: str, native_code: object, space: str | None = None) -> CanonicalError:
    """Translate a native code into the canonical taxonomy.

    ``io_uring`` CQE results are negative errno; pass them as-is.  A code that
    is not an int, or not in the table, yields ``UNKNOWN_HOST_ERROR`` and
    increments ``untranslatable_errors``.  Nothing ever translates to success.
    """
    space = space or SOURCE_FOR_BACKEND.get(backend, "posix")
    raw: int | None
    if isinstance(native_code, bool) or not isinstance(native_code, int):
        raw = None
    else:
        raw = native_code
        if backend == "io_uring" and space == "posix" and raw < 0:
            raw = -raw
    if raw is not None and not (-_MAX_SAFE < raw < _MAX_SAFE):
        raw = None
    table = TABLES.get(space, {})
    code = table.get(raw) if raw is not None else None
    if code is None:
        untranslatable_errors.inc()
        code = Code.UNKNOWN_HOST_ERROR
    retryable, transient = _CLASS[code]
    return CanonicalError(
        code=code.value, backend=backend, native_space=space, native_code=raw,
        retryable=retryable, transient=transient,
        cancelled=code is Code.CANCELLED, timeout=code is Code.TIMED_OUT,
        message=_MESSAGES.get(code, "host error"),
    )


def canonical(code: Code, backend: str = "inv19") -> CanonicalError:
    retryable, transient = _CLASS[code]
    return CanonicalError(code.value, backend, "canonical", None, retryable, transient,
                          code is Code.CANCELLED, code is Code.TIMED_OUT, _MESSAGES.get(code, code.value))


# Fixed, non-host messages: host strerror text never becomes a contract.
_MESSAGES = {c: c.value.replace("_", " ").lower() for c in Code}

# EOF is a non-error terminal condition: completion value 0 bytes on a stream.
EOF = ("value", 0)
