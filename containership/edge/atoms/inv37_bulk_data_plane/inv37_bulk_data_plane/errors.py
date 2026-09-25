"""Structured errors for the INV-37 bulk data plane."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(eq=False)
class BulkDataPlaneError(Exception):
    """Base error carrying a stable machine-readable code and details."""

    message: str
    code: str = "bulk_data_plane_error"
    details: Mapping[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __str__(self) -> str:
        return self.message

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "details": dict(self.details),
        }


class InvalidManifest(BulkDataPlaneError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, "invalid_manifest", details, False)


class DigestMismatch(BulkDataPlaneError, ValueError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, "digest_mismatch", details, False)


class TransferIncomplete(BulkDataPlaneError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, "transfer_incomplete", details, True)


class AdmissionRejected(BulkDataPlaneError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, "admission_rejected", details, True)


class TransferClosed(BulkDataPlaneError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, "transfer_closed", details, False)


class CodedError(BulkDataPlaneError):
    """Error with an explicit registry code (see ``outcomes.ERROR_CODES``)."""

    def __init__(self, code: str, message: str, *, retryable: bool | None = None, **details: Any) -> None:
        if retryable is None:
            from .outcomes import ERROR_CODES  # local import avoids a cycle

            spec = ERROR_CODES.get(code)
            retryable = bool(spec and spec.retryable)
        super().__init__(message, code, details, retryable)


class IllegalTransition(CodedError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__("illegal_transition", message, **details)


class SecurityRejected(CodedError):
    """Authentication/authorization/replay failures.  Details are deliberately sparse."""


class ConfigError(CodedError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__("invalid_config", message, **details)
