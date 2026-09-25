"""Component 19 - structured error taxonomy for GAP-10.

Every code is stable, machine-readable and carries a fail-closed flag so
automation can tell whether a failure can ever relax a ceiling (it cannot).
"""
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    # telemetry / trust
    TELEMETRY_MALFORMED = "GAP10-E-TEL-001"
    TELEMETRY_STALE = "GAP10-E-TEL-002"
    TELEMETRY_FUTURE = "GAP10-E-TEL-003"
    TELEMETRY_REPLAYED = "GAP10-E-TEL-004"
    TELEMETRY_UNAUTHENTICATED = "GAP10-E-TEL-005"
    TELEMETRY_UNAUTHORIZED = "GAP10-E-TEL-006"
    TELEMETRY_BAD_SIGNATURE = "GAP10-E-TEL-007"
    TELEMETRY_UNSUPPORTED_VERSION = "GAP10-E-TEL-008"
    TELEMETRY_IMPLAUSIBLE = "GAP10-E-TEL-009"
    TELEMETRY_OVERSIZE = "GAP10-E-TEL-010"
    TELEMETRY_RATE_LIMITED = "GAP10-E-TEL-011"
    # policy
    POLICY_INVALID = "GAP10-E-POL-001"
    POLICY_UNSIGNED = "GAP10-E-POL-002"
    POLICY_UNAUTHORIZED = "GAP10-E-POL-003"
    POLICY_REVISION_CONFLICT = "GAP10-E-POL-004"
    POLICY_UNKNOWN_REVISION = "GAP10-E-POL-005"
    # state store
    STORE_UNAVAILABLE = "GAP10-E-STO-001"
    STORE_CORRUPT = "GAP10-E-STO-002"
    # ownership
    OWNERSHIP_CONFLICT = "GAP10-E-OWN-001"
    FENCING_TOKEN_STALE = "GAP10-E-OWN-002"
    # downstream
    DOWNSTREAM_REJECTED = "GAP10-E-DWN-001"
    DOWNSTREAM_DIVERGENCE = "GAP10-E-DWN-002"
    DOWNSTREAM_UNAVAILABLE = "GAP10-E-DWN-003"
    ADMISSION_DENIED = "GAP10-E-DWN-004"
    CEILING_REVISION_MISMATCH = "GAP10-E-DWN-005"
    # control / time / keys / dependencies
    CONTROL_UNAUTHORIZED = "GAP10-E-CTL-001"
    CONTROL_INVALID = "GAP10-E-CTL-002"
    CLOCK_UNTRUSTED = "GAP10-E-CLK-001"
    KEY_UNKNOWN = "GAP10-E-KEY-001"
    KEY_SCOPE_DENIED = "GAP10-E-KEY-002"
    KEY_REVOKED = "GAP10-E-KEY-003"
    CIRCUIT_OPEN = "GAP10-E-DEP-001"
    DEPENDENCY_TIMEOUT = "GAP10-E-DEP-002"
    PARTITIONED = "GAP10-E-DEP-003"
    CALIBRATION_MISSING = "GAP10-E-CAL-001"


# Every GAP-10 error is fail-closed: none of them may widen a ceiling.
FAIL_CLOSED: frozenset[ErrorCode] = frozenset(ErrorCode)

CATEGORY = {
    "TEL": "telemetry", "POL": "policy", "STO": "state-store", "OWN": "ownership",
    "DWN": "downstream", "CTL": "control", "CLK": "time", "KEY": "keys",
    "DEP": "dependency", "CAL": "calibration",
}


def category(code: ErrorCode) -> str:
    return CATEGORY[code.value.split("-")[2]]


class Gap10Error(Exception):
    """Exception carrying a stable code, correlation id and structured detail."""

    def __init__(self, code: ErrorCode, message: str = "", *, correlation_id: str | None = None, **detail):
        super().__init__(f"{code.value} {code.name}: {message}")
        self.code = code
        self.message = message
        self.correlation_id = correlation_id
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "name": self.code.name,
            "category": category(self.code),
            "fail_closed": self.code in FAIL_CLOSED,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "detail": {k: v for k, v in self.detail.items() if isinstance(v, (str, int, float, bool, type(None)))},
        }
