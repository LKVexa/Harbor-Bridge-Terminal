"""Stable, machine-readable error contract for PLN-05 (``PK_ERROR/1``).

Every failure that crosses a public boundary is a :class:`PlaneError` carrying a
code from :data:`CODES`.  Codes are append-only: a released code is never reused
or given a different category/retryability (checked by ``tests/test_units.py::ErrorsTest``).
Messages never echo raw payload values; ``detail`` holds only field names,
bounded integers, and schema identifiers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

ERROR_SCHEMA = "PK_ERROR/1"

# code -> (category, retryable, severity)
CODES: dict[str, tuple[str, bool, str]] = {
    # boundary / schema
    "E_SCHEMA_MALFORMED": ("schema", False, "warning"),
    "E_SCHEMA_TOO_LARGE": ("schema", False, "warning"),
    "E_SCHEMA_TOO_DEEP": ("schema", False, "warning"),
    "E_SCHEMA_VERSION": ("schema", False, "warning"),
    "E_SCHEMA_FIELD": ("schema", False, "warning"),
    "E_SCHEMA_UNKNOWN_CRITICAL": ("schema", False, "warning"),
    "E_STALE_INPUT": ("freshness", False, "info"),
    "E_FUTURE_SKEW": ("freshness", False, "warning"),
    "E_OUT_OF_ORDER": ("ordering", False, "info"),
    "E_DUPLICATE": ("ordering", False, "info"),
    # identity / authority
    "E_AUTHN_FAILED": ("authn", False, "warning"),
    "E_AUTHN_EXPIRED": ("authn", False, "warning"),
    "E_AUTHN_REPLAY": ("authn", False, "critical"),
    "E_AUTHN_REVOKED": ("authn", False, "warning"),
    "E_AUTHZ_DENIED": ("authz", False, "warning"),
    "E_AUTHZ_SCOPE": ("authz", False, "critical"),
    "E_AUTHORITY_ESCALATION": ("authz", False, "critical"),
    "E_SECURITY_DEPENDENCY": ("security_dependency", True, "critical"),
    # control state
    "E_FROZEN": ("control", False, "info"),
    "E_QUARANTINED": ("control", False, "warning"),
    "E_DISABLED": ("control", False, "info"),
    "E_NOT_LEADER": ("coordination", True, "warning"),
    "E_FENCED": ("coordination", False, "critical"),
    # config / state
    "E_CONFIG_INVALID": ("config", False, "warning"),
    "E_CONFIG_SECRET": ("config", False, "critical"),
    "E_CONFIG_NO_ROLLBACK": ("config", False, "warning"),
    "E_STATE_CORRUPT": ("state", False, "critical"),
    "E_STATE_VERSION": ("state", False, "critical"),
    "E_STATE_UNAVAILABLE": ("state", True, "critical"),
    # reliability
    "E_OVERLOADED": ("overload", True, "warning"),
    "E_CIRCUIT_OPEN": ("dependency", True, "warning"),
    "E_DEADLINE": ("deadline", True, "warning"),
    "E_CANCELLED": ("deadline", False, "info"),
    "E_RETRY_BUDGET": ("dependency", False, "warning"),
    "E_AUDIT_UNAVAILABLE": ("audit", True, "critical"),
    # supply chain
    "E_ARTIFACT_UNTRUSTED": ("supply_chain", False, "critical"),
    "E_INTERNAL": ("internal", False, "critical"),
}

_SAFE_DETAIL = re.compile(r"^[A-Za-z0-9_./:\-\[\] ]{0,96}$")


@dataclass
class PlaneError(Exception):
    """A typed boundary error.  ``str()`` is safe to log."""

    code: str
    message: str
    detail: dict = field(default_factory=dict)
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if self.code not in CODES:
            self.detail = {"unknown_code": True}
            self.code = "E_INTERNAL"
        # Only allow short, character-restricted detail values: no payload echo.
        clean: dict = {}
        for k, v in list(self.detail.items())[:8]:
            if isinstance(v, bool) or isinstance(v, int):
                clean[str(k)[:32]] = v
            elif isinstance(v, str) and _SAFE_DETAIL.match(v):
                clean[str(k)[:32]] = v
            else:
                clean[str(k)[:32]] = "<redacted>"
        self.detail = clean
        super().__init__(f"{self.code}: {self.message}")

    @property
    def category(self) -> str:
        return CODES[self.code][0]

    @property
    def retryable(self) -> bool:
        return CODES[self.code][1]

    @property
    def severity(self) -> str:
        return CODES[self.code][2]

    def to_wire(self) -> dict:
        return {
            "schema": ERROR_SCHEMA,
            "code": self.code,
            "category": self.category,
            "retryable": self.retryable,
            "severity": self.severity,
            "message": self.message[:200],
            "detail": dict(self.detail),
            "correlation_id": self.correlation_id,
        }
