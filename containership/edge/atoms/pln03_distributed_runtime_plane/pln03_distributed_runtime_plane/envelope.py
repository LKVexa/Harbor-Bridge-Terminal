"""Outcome model and serializable error envelope (MC-005, MC-015).

Every runtime failure maps to exactly one stable code, one outcome class, one
HTTP status and one gRPC status.  The envelope is language-neutral JSON and is
validated against ``schemas/error-envelope.v1.json``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

ENVELOPE_SCHEMA = "pk.error-envelope/1"


class Outcome(str, Enum):
    SUCCESS = "success"            # operation fully applied
    DEGRADED = "degraded"          # applied locally/buffered; will reconcile
    RETRYABLE = "retryable"        # nothing applied; safe to retry with same idempotency key
    TERMINAL = "terminal"          # nothing applied; retrying unchanged input will fail again


@dataclass(frozen=True)
class CodeSpec:
    outcome: Outcome
    http: int
    grpc: str


# Stable, append-only registry.  Removing or re-mapping a code is a breaking change (COMPATIBILITY.md).
CODES: dict[str, CodeSpec] = {
    "PK_OK": CodeSpec(Outcome.SUCCESS, 200, "OK"),
    "PK_DEGRADED_BUFFERED": CodeSpec(Outcome.DEGRADED, 202, "OK"),
    "PK_RUNTIME_ERROR": CodeSpec(Outcome.TERMINAL, 500, "INTERNAL"),
    "PK_CAPABILITY_DENIED": CodeSpec(Outcome.TERMINAL, 403, "PERMISSION_DENIED"),
    "PK_TOKEN_INVALID": CodeSpec(Outcome.TERMINAL, 401, "UNAUTHENTICATED"),
    "PK_TOKEN_EXPIRED": CodeSpec(Outcome.TERMINAL, 401, "UNAUTHENTICATED"),
    "PK_SECURITY_DEPENDENCY_UNAVAILABLE": CodeSpec(Outcome.RETRYABLE, 503, "UNAVAILABLE"),
    "PK_ADAPTER_UNAVAILABLE": CodeSpec(Outcome.RETRYABLE, 503, "UNAVAILABLE"),
    "PK_INVALID_ARGUMENT": CodeSpec(Outcome.TERMINAL, 400, "INVALID_ARGUMENT"),
    "PK_PAYLOAD_TOO_LARGE": CodeSpec(Outcome.TERMINAL, 413, "INVALID_ARGUMENT"),
    "PK_SECRET_NOT_FOUND": CodeSpec(Outcome.TERMINAL, 404, "NOT_FOUND"),
    "PK_INVOKE_TARGET_UNAVAILABLE": CodeSpec(Outcome.RETRYABLE, 503, "UNAVAILABLE"),
    "PK_DEADLINE_EXCEEDED": CodeSpec(Outcome.RETRYABLE, 504, "DEADLINE_EXCEEDED"),
    "PK_CANCELLED": CodeSpec(Outcome.TERMINAL, 499, "CANCELLED"),
    "PK_RATE_LIMITED": CodeSpec(Outcome.RETRYABLE, 429, "RESOURCE_EXHAUSTED"),
    "PK_QUOTA_EXCEEDED": CodeSpec(Outcome.RETRYABLE, 429, "RESOURCE_EXHAUSTED"),
    "PK_CIRCUIT_OPEN": CodeSpec(Outcome.RETRYABLE, 503, "UNAVAILABLE"),
    "PK_LIFECYCLE_REFUSED": CodeSpec(Outcome.RETRYABLE, 503, "UNAVAILABLE"),
    "PK_QUARANTINED": CodeSpec(Outcome.TERMINAL, 403, "FAILED_PRECONDITION"),
    "PK_FENCED": CodeSpec(Outcome.TERMINAL, 409, "ABORTED"),
    "PK_VERSION_UNSUPPORTED": CodeSpec(Outcome.TERMINAL, 505, "UNIMPLEMENTED"),
    "PK_CONFIG_INVALID": CodeSpec(Outcome.TERMINAL, 422, "FAILED_PRECONDITION"),
    "PK_READ_ONLY": CodeSpec(Outcome.RETRYABLE, 503, "UNAVAILABLE"),
    "PK_RESIDENCY_VIOLATION": CodeSpec(Outcome.TERMINAL, 451, "FAILED_PRECONDITION"),
}


def to_envelope(exc: BaseException, *, trace_id: str | None = None) -> dict:
    code = getattr(exc, "code", "PK_RUNTIME_ERROR")
    spec = CODES.get(code, CODES["PK_RUNTIME_ERROR"])
    details = getattr(exc, "details", {}) or {}
    # Details are structural only; values are coerced to str/int/bool and never contain payloads.
    safe = {str(k): (v if isinstance(v, (int, bool)) else str(v))[:256] if not isinstance(v, (int, bool)) else v
            for k, v in details.items()}
    return {
        "schema": ENVELOPE_SCHEMA,
        "code": code if code in CODES else "PK_RUNTIME_ERROR",
        "outcome": spec.outcome.value,
        "retryable": spec.outcome is Outcome.RETRYABLE,
        "http_status": spec.http,
        "grpc_status": spec.grpc,
        "message": str(exc.args[0] if exc.args else code)[:512],
        "details": safe,
        "trace_id": trace_id,
    }


def dumps(envelope: dict) -> str:
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def validate_envelope(env: dict) -> None:
    """Minimal structural validator mirroring schemas/error-envelope.v1.json (no third-party deps)."""
    required = {"schema", "code", "outcome", "retryable", "http_status", "grpc_status", "message", "details", "trace_id"}
    if set(env) != required:
        raise ValueError(f"envelope keys mismatch: {sorted(set(env) ^ required)}")
    if env["schema"] != ENVELOPE_SCHEMA or env["code"] not in CODES:
        raise ValueError("unknown schema or code")
    spec = CODES[env["code"]]
    if env["outcome"] != spec.outcome.value or env["http_status"] != spec.http or env["grpc_status"] != spec.grpc:
        raise ValueError("envelope inconsistent with code registry")
    if env["retryable"] != (spec.outcome is Outcome.RETRYABLE):
        raise ValueError("retryable flag inconsistent")
    if not isinstance(env["details"], dict):
        raise ValueError("details must be an object")
