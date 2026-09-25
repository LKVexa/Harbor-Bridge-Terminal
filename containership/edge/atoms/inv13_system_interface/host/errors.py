"""MC-012 -- structured, stable, leak-free error taxonomy.

Every failure that crosses the guest boundary is an ``Inv13Error`` carrying a
stable machine code from ``ErrorCode``.  Host detail (paths, errno text,
secrets, stack traces) is kept in ``host_detail`` which is *never* serialised
by ``to_guest()``; only the code, category and a fixed public message leave.
"""
from __future__ import annotations

import errno as _errno
from enum import Enum
from typing import Any


class Category(str, Enum):
    DENIED = "capability-denied"
    INVALID = "invalid-input"
    UNAVAILABLE = "unavailable-dependency"
    QUOTA = "quota-exceeded"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    NOT_FOUND = "not-found"
    CONFLICT = "conflict"
    TERMINAL = "terminal"


class ErrorCode(str, Enum):
    # code value, category, retryable, public message
    CAP_NOT_GRANTED = "E1001"
    PREOPEN_NOT_FOUND = "E1002"
    PATH_ESCAPE = "E1003"
    SYMLINK_REFUSED = "E1004"
    POLICY_DENIED = "E1005"
    IDENTITY_REQUIRED = "E1006"
    ATTESTATION_FAILED = "E1007"
    DESTINATION_DENIED = "E1008"
    QUARANTINED = "E1009"
    INVALID_ARGUMENT = "E2001"
    INVALID_ENCODING = "E2002"
    TOO_LONG = "E2003"
    INVALID_HANDLE = "E2004"
    STALE_HANDLE = "E2005"
    WRONG_HANDLE_TYPE = "E2006"
    UNSUPPORTED_VERSION = "E2007"
    MALFORMED_MODULE = "E2008"
    PROVIDER_UNAVAILABLE = "E3001"
    ENTROPY_UNAVAILABLE = "E3002"
    CONFIG_STALE = "E3003"
    QUOTA_EXCEEDED = "E4001"
    BACKPRESSURE = "E4002"
    TIMED_OUT = "E5001"
    CANCELLED = "E5002"
    NOT_FOUND = "E6001"
    ALREADY_EXISTS = "E6002"
    NOT_A_DIRECTORY = "E6003"
    IS_A_DIRECTORY = "E6004"
    FROZEN = "E6005"
    INTERNAL = "E9001"


_META: dict[ErrorCode, tuple[Category, bool, str]] = {
    ErrorCode.CAP_NOT_GRANTED: (Category.DENIED, False, "capability not granted"),
    ErrorCode.PREOPEN_NOT_FOUND: (Category.DENIED, False, "no such preopen"),
    ErrorCode.PATH_ESCAPE: (Category.DENIED, False, "path escapes preopen"),
    ErrorCode.SYMLINK_REFUSED: (Category.DENIED, False, "symbolic link refused"),
    ErrorCode.POLICY_DENIED: (Category.DENIED, False, "denied by policy"),
    ErrorCode.IDENTITY_REQUIRED: (Category.DENIED, False, "authenticated identity required"),
    ErrorCode.ATTESTATION_FAILED: (Category.DENIED, False, "attestation failed"),
    ErrorCode.DESTINATION_DENIED: (Category.DENIED, False, "destination denied"),
    ErrorCode.QUARANTINED: (Category.DENIED, False, "workload quarantined"),
    ErrorCode.INVALID_ARGUMENT: (Category.INVALID, False, "invalid argument"),
    ErrorCode.INVALID_ENCODING: (Category.INVALID, False, "invalid encoding"),
    ErrorCode.TOO_LONG: (Category.INVALID, False, "value too long"),
    ErrorCode.INVALID_HANDLE: (Category.INVALID, False, "invalid handle"),
    ErrorCode.STALE_HANDLE: (Category.INVALID, False, "stale handle"),
    ErrorCode.WRONG_HANDLE_TYPE: (Category.INVALID, False, "wrong handle type"),
    ErrorCode.UNSUPPORTED_VERSION: (Category.INVALID, False, "unsupported interface version"),
    ErrorCode.MALFORMED_MODULE: (Category.INVALID, False, "malformed module"),
    ErrorCode.PROVIDER_UNAVAILABLE: (Category.UNAVAILABLE, True, "provider unavailable"),
    ErrorCode.ENTROPY_UNAVAILABLE: (Category.UNAVAILABLE, True, "entropy unavailable"),
    ErrorCode.CONFIG_STALE: (Category.UNAVAILABLE, True, "configuration stale"),
    ErrorCode.QUOTA_EXCEEDED: (Category.QUOTA, True, "quota exceeded"),
    ErrorCode.BACKPRESSURE: (Category.QUOTA, True, "backpressure"),
    ErrorCode.TIMED_OUT: (Category.TIMEOUT, True, "timed out"),
    ErrorCode.CANCELLED: (Category.CANCELLED, False, "cancelled"),
    ErrorCode.NOT_FOUND: (Category.NOT_FOUND, False, "not found"),
    ErrorCode.ALREADY_EXISTS: (Category.CONFLICT, False, "already exists"),
    ErrorCode.NOT_A_DIRECTORY: (Category.INVALID, False, "not a directory"),
    ErrorCode.IS_A_DIRECTORY: (Category.INVALID, False, "is a directory"),
    ErrorCode.FROZEN: (Category.CONFLICT, True, "mutations frozen"),
    ErrorCode.INTERNAL: (Category.TERMINAL, False, "internal error"),
}


class Inv13Error(Exception):
    """Boundary error. ``str()`` is the public message only."""

    def __init__(self, code: ErrorCode, host_detail: Any = None) -> None:
        self.code = code
        self.category, self.retryable, self.public_message = _META[code]
        self.host_detail = host_detail  # never serialised to a guest
        super().__init__(f"{code.value} {self.public_message}")

    def to_guest(self) -> dict[str, Any]:
        return {"code": self.code.value, "category": self.category.value,
                "retryable": self.retryable, "message": self.public_message}

    def __repr__(self) -> str:  # repr also omits host detail
        return f"Inv13Error({self.code.name})"


_ERRNO_MAP = {
    _errno.ENOENT: ErrorCode.NOT_FOUND,
    _errno.EEXIST: ErrorCode.ALREADY_EXISTS,
    _errno.ENOTDIR: ErrorCode.NOT_A_DIRECTORY,
    _errno.EISDIR: ErrorCode.IS_A_DIRECTORY,
    _errno.ELOOP: ErrorCode.SYMLINK_REFUSED,
    _errno.EXDEV: ErrorCode.PATH_ESCAPE,
    _errno.EACCES: ErrorCode.POLICY_DENIED,
    _errno.EPERM: ErrorCode.POLICY_DENIED,
    _errno.ENAMETOOLONG: ErrorCode.TOO_LONG,
    _errno.EMFILE: ErrorCode.QUOTA_EXCEEDED,
    _errno.ENFILE: ErrorCode.QUOTA_EXCEEDED,
    _errno.ENOSPC: ErrorCode.QUOTA_EXCEEDED,
    _errno.ETIMEDOUT: ErrorCode.TIMED_OUT,
    _errno.EAGAIN: ErrorCode.BACKPRESSURE,
    _errno.ECONNREFUSED: ErrorCode.PROVIDER_UNAVAILABLE,
    _errno.EHOSTUNREACH: ErrorCode.PROVIDER_UNAVAILABLE,
    _errno.ENETUNREACH: ErrorCode.PROVIDER_UNAVAILABLE,
}


def from_os_error(exc: OSError) -> Inv13Error:
    """Map a host OSError to a stable code; the errno text stays host-side."""
    code = _ERRNO_MAP.get(exc.errno or -1, ErrorCode.INTERNAL)
    return Inv13Error(code, host_detail=repr(exc))


def all_codes() -> list[dict[str, Any]]:
    return [{"code": c.value, "name": c.name, "category": _META[c][0].value,
             "retryable": _META[c][1], "message": _META[c][2]} for c in ErrorCode]
