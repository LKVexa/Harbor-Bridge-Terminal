"""GAP02-MC-17 — Structured error-code taxonomy.

Stable, machine-readable codes. Codes are append-only: a code's meaning never
changes once released; retired codes stay reserved (see ``RESERVED``).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

TAXONOMY_VERSION = "GAP02_ERRORS/1"


class Code(str, Enum):
    PROBE_UNAVAILABLE = "GAP02-E001"
    PRIVILEGE_DENIED = "GAP02-E002"
    UNSUPPORTED_PLATFORM = "GAP02-E003"
    TIMEOUT = "GAP02-E004"
    DRIVER_ERROR = "GAP02-E005"
    MALFORMED_RESPONSE = "GAP02-E006"
    STALE_DATA = "GAP02-E007"
    SIGNATURE_FAILURE = "GAP02-E008"
    DEPENDENCY_FAILURE = "GAP02-E009"
    RUNTIME_INCOMPATIBLE = "GAP02-E010"
    UNHEALTHY = "GAP02-E011"
    REPLAY_DETECTED = "GAP02-E012"
    CLOCK_UNTRUSTED = "GAP02-E013"
    CONFIG_INVALID = "GAP02-E014"
    POLICY_DENIED = "GAP02-E015"
    PROVENANCE_FAILURE = "GAP02-E016"
    QUARANTINED = "GAP02-E017"
    RESOURCE_EXHAUSTED = "GAP02-E018"
    CIRCUIT_OPEN = "GAP02-E019"
    SCHEMA_INCOMPATIBLE = "GAP02-E020"
    UNATTESTED = "GAP02-E021"
    INTERNAL = "GAP02-E999"


RESERVED: frozenset[str] = frozenset()  # retired codes go here, never reused

RUNBOOK = {c: f"RUNBOOKS.md#{c.value.lower()}" for c in Code}
RETRYABLE = frozenset({Code.TIMEOUT, Code.DEPENDENCY_FAILURE, Code.CIRCUIT_OPEN,
                       Code.RESOURCE_EXHAUSTED, Code.STALE_DATA})


@dataclass(frozen=True)
class Gap02Error(Exception):
    code: Code
    detail: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "detail", str(self.detail)[:512])

    def __str__(self) -> str:
        return f"{self.code.value} {self.code.name}: {self.detail}"

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "name": self.code.name, "detail": self.detail,
                "retryable": self.retryable, "runbook": RUNBOOK[self.code]}


def classify(exc: BaseException) -> Code:
    """Map an arbitrary exception to a code. Unknown → INTERNAL (fail closed)."""
    import subprocess
    if isinstance(exc, Gap02Error):
        return exc.code
    if isinstance(exc, PermissionError):
        return Code.PRIVILEGE_DENIED
    if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)):
        return Code.TIMEOUT
    if isinstance(exc, FileNotFoundError):
        return Code.PROBE_UNAVAILABLE
    if isinstance(exc, (ValueError, KeyError, UnicodeDecodeError)):
        return Code.MALFORMED_RESPONSE
    if isinstance(exc, NotImplementedError):
        return Code.UNSUPPORTED_PLATFORM
    if isinstance(exc, OSError):
        return Code.DRIVER_ERROR
    return Code.INTERNAL
