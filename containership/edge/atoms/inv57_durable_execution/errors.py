"""Machine-readable error model for INV-57 (MC-14).

Every durable-execution exception maps to a stable code, a category, a
retryability class and a safe-to-expose flag.  ``describe`` never includes the
exception message when the entry is not safe to expose, because messages can
carry tenant identifiers.  The registry is versioned; codes are append-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from . import durable

ERROR_MODEL_SCHEMA = "INV57_ERROR_MODEL/1"


class StaleOwner(durable.DurableExecutionError):
    """A worker whose lease/fencing epoch is no longer current tried to mutate state."""


class OwnershipConflict(durable.DurableExecutionError):
    """Ownership could not be acquired because another live owner holds the lease."""


class ConcurrentAppend(durable.DurableExecutionError):
    """Conditional append lost a race: the expected sequence was no longer the tail."""


class HistoryQuarantined(durable.DurableExecutionError):
    """History failed integrity validation and is quarantined; no automatic continuation."""


class IllegalTransition(durable.DurableExecutionError):
    """A lifecycle control requested a transition the state machine forbids."""


class InvalidIdentity(durable.DurableExecutionError, ValueError):
    """A workflow identity field is malformed, oversized or not permitted."""


class Unauthorized(durable.DurableExecutionError):
    """The caller lacks the capability required for the requested operation."""


class ConfigRejected(durable.DurableExecutionError, ValueError):
    """A configuration document failed schema or policy validation."""


class Overloaded(durable.DurableExecutionError):
    """Admission control refused work (quota, queue bound, or open circuit)."""


class DeadlineExceeded(durable.DurableExecutionError):
    """An operation exceeded its deadline; the outcome may be ambiguous."""


class EffectUnresolved(durable.DurableExecutionError):
    """An external effect's outcome could not be established from its receipt."""


class Frozen(durable.DurableExecutionError):
    """The workflow, tenant or runtime is frozen/disabled by an operator control."""


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    category: str          # client | conflict | integrity | availability | safety | policy
    retryable: str         # never | after_backoff | after_reconcile | operator_only
    safe_message: bool     # may the exception text be shown to callers?
    http_status: int
    summary: str


_REGISTRY: dict[type, ErrorSpec] = {
    durable.NonDeterminism: ErrorSpec("INV57-E001", "integrity", "never", True, 409,
                                      "workflow code diverged from durable history"),
    durable.HistoryCorruption: ErrorSpec("INV57-E002", "integrity", "operator_only", False, 500,
                                         "history failed structural or digest validation"),
    durable.HistoryLimitExceeded: ErrorSpec("INV57-E003", "policy", "never", True, 413,
                                            "history bound would be exceeded"),
    durable.UnsupportedResult: ErrorSpec("INV57-E004", "client", "never", True, 422,
                                         "activity result is not deterministically encodable"),
    durable.ActivityInDoubt: ErrorSpec("INV57-E005", "safety", "after_reconcile", False, 409,
                                       "activity started without a durable outcome"),
    durable.RecordedActivityFailure: ErrorSpec("INV57-E006", "safety", "operator_only", True, 409,
                                               "activity previously failed; automatic re-run refused"),
    durable.ConcurrentRun: ErrorSpec("INV57-E007", "conflict", "after_backoff", True, 409,
                                     "worker already running a workflow"),
    StaleOwner: ErrorSpec("INV57-E010", "conflict", "never", True, 409,
                          "fencing epoch is stale; this worker must stop"),
    OwnershipConflict: ErrorSpec("INV57-E011", "conflict", "after_backoff", True, 409,
                                 "workflow is owned by another live worker"),
    ConcurrentAppend: ErrorSpec("INV57-E012", "conflict", "after_reconcile", True, 409,
                                "conditional append lost the tail race"),
    HistoryQuarantined: ErrorSpec("INV57-E013", "integrity", "operator_only", False, 423,
                                  "history quarantined pending operator review"),
    IllegalTransition: ErrorSpec("INV57-E014", "client", "never", True, 409,
                                 "lifecycle transition not permitted"),
    InvalidIdentity: ErrorSpec("INV57-E015", "client", "never", True, 400,
                               "workflow identity invalid"),
    Unauthorized: ErrorSpec("INV57-E016", "policy", "never", False, 403,
                            "capability not granted"),
    ConfigRejected: ErrorSpec("INV57-E017", "client", "never", True, 422,
                              "configuration rejected"),
    Overloaded: ErrorSpec("INV57-E018", "availability", "after_backoff", True, 429,
                          "admission refused"),
    DeadlineExceeded: ErrorSpec("INV57-E019", "availability", "after_reconcile", True, 504,
                                "deadline exceeded; outcome may be ambiguous"),
    EffectUnresolved: ErrorSpec("INV57-E020", "safety", "operator_only", False, 409,
                                "external effect outcome unresolved"),
    Frozen: ErrorSpec("INV57-E021", "policy", "operator_only", True, 423,
                      "operation frozen by operator control"),
}

_FALLBACK = ErrorSpec("INV57-E999", "availability", "operator_only", False, 500,
                      "unclassified durable-execution error")


def spec_for(exc: BaseException | type) -> ErrorSpec:
    cls = exc if isinstance(exc, type) else type(exc)
    for klass in cls.__mro__:
        if klass in _REGISTRY:
            return _REGISTRY[klass]
    return _FALLBACK


def describe(exc: BaseException) -> dict[str, Any]:
    """Return the canonical machine-readable error document for ``exc``."""
    spec = spec_for(exc)
    return {
        "schema": ERROR_MODEL_SCHEMA,
        "code": spec.code,
        "type": type(exc).__name__,
        "category": spec.category,
        "retryable": spec.retryable,
        "http_status": spec.http_status,
        "summary": spec.summary,
        "detail": str(exc) if spec.safe_message else None,
    }


def registry() -> list[Mapping[str, Any]]:
    rows = [{"type": k.__name__, **v.__dict__} for k, v in _REGISTRY.items()]
    return sorted(rows, key=lambda r: r["code"])
