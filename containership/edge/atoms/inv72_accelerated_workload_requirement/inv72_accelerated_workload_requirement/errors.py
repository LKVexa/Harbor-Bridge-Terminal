"""Structured failure codes for INV-72 (C014, C026).

Every refusal and every error that crosses the PK_ACCEL_MATCH/1 boundary carries a
stable code from ``REGISTRY``.  Codes are append-only: a code is never renamed or
re-purposed, only deprecated (see ops/COMPATIBILITY_POLICY.md).

Outcome classes (C014):
  success          – selection returned and (if requested) reserved
  refused          – clean, explained non-match; retrying unchanged input is useless
  retryable        – transient (deadline, admission, stale discovery); retry with backoff
  degraded         – answered from a fallback path; answer is correct but flagged
  terminal         – malformed input or policy violation; never retry unchanged
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA = "PK_ACCEL_ERROR/1"

OUTCOMES = ("success", "refused", "retryable", "degraded", "terminal")


@dataclass(frozen=True)
class Code:
    code: str
    outcome: str
    http_like: int
    summary: str


_CODES = [
    # clean refusals (explained non-matches)
    Code("ACCEL_NO_CLASS", "refused", 409, "no device of the requested class exists"),
    Code("ACCEL_INSUFFICIENT_MEMORY", "refused", 409, "no device of the class has enough memory"),
    Code("ACCEL_PARTITION_DEDICATED", "refused", 409, "partition refused for dedicated isolation"),
    Code("ACCEL_PARTITION_FOREIGN_TENANT", "refused", 409, "partition already shared with another tenant"),
    Code("ACCEL_DEVICE_FOREIGN_TENANT", "refused", 409, "whole device assigned to another tenant"),
    Code("ACCEL_DEVICE_QUARANTINED", "refused", 409, "device quarantined or drained by an operator"),
    Code("ACCEL_NO_INTERCONNECT", "refused", 409, "not enough eligible devices share one interconnect"),
    Code("ACCEL_INSUFFICIENT_COUNT", "refused", 409, "fewer eligible devices than requested"),
    Code("ACCEL_QUOTA_EXCEEDED", "refused", 429, "tenant device quota would be exceeded"),
    # terminal
    Code("ACCEL_INVALID_REQUIREMENT", "terminal", 400, "requirement malformed or unsafe"),
    Code("ACCEL_INVALID_INVENTORY", "terminal", 400, "inventory malformed or ambiguous"),
    Code("ACCEL_LIMIT_EXCEEDED", "terminal", 413, "payload exceeds a documented bound"),
    Code("ACCEL_UNSUPPORTED_VERSION", "terminal", 400, "schema version not supported"),
    Code("ACCEL_UNAUTHENTICATED", "terminal", 401, "caller identity not established"),
    Code("ACCEL_FORBIDDEN", "terminal", 403, "caller lacks the capability or tenant scope"),
    Code("ACCEL_REPLAY", "terminal", 409, "request token already used"),
    Code("ACCEL_STALE_FENCE", "terminal", 409, "controller fencing token is stale"),
    Code("ACCEL_DISABLED", "terminal", 503, "component emergency-disabled by an operator"),
    Code("ACCEL_CONFIG_INVALID", "terminal", 400, "configuration failed validation"),
    Code("ACCEL_UNKNOWN_RESERVATION", "terminal", 404, "no such reservation"),
    Code("ACCEL_ILLEGAL_TRANSITION", "terminal", 409, "lifecycle transition not permitted"),
    Code("ACCEL_STATE_CORRUPT", "terminal", 500, "journal or snapshot failed integrity checks"),
    # retryable
    Code("ACCEL_DEADLINE_EXCEEDED", "retryable", 504, "deadline passed before a decision"),
    Code("ACCEL_CANCELLED", "retryable", 499, "caller cancelled"),
    Code("ACCEL_OVERLOADED", "retryable", 503, "admission control shed the request"),
    Code("ACCEL_CIRCUIT_OPEN", "retryable", 503, "dependency circuit open"),
    Code("ACCEL_INVENTORY_STALE", "retryable", 503, "inventory snapshot older than the freshness bound"),
    Code("ACCEL_DEPENDENCY_UNAVAILABLE", "retryable", 503, "a security-critical dependency is unavailable"),
]

REGISTRY: dict[str, Code] = {c.code: c for c in _CODES}


class AccelError(Exception):
    """An error carrying a registered code and machine-readable details."""

    def __init__(self, code: str, message: str = "", **details: Any) -> None:
        if code not in REGISTRY:
            raise KeyError(f"unregistered error code {code!r}")
        self.code = code
        self.message = message or REGISTRY[code].summary
        self.details = details
        super().__init__(f"{code}: {self.message}")

    @property
    def outcome(self) -> str:
        return REGISTRY[self.code].outcome

    @property
    def retryable(self) -> bool:
        return self.outcome == "retryable"

    def to_dict(self) -> dict:
        return {"schema": SCHEMA, "code": self.code, "outcome": self.outcome,
                "retryable": self.retryable, "message": self.message,
                "details": {k: v for k, v in self.details.items()}}


def describe(code: str) -> dict:
    c = REGISTRY[code]
    return {"code": c.code, "outcome": c.outcome, "http_like": c.http_like, "summary": c.summary}
