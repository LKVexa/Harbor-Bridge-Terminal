"""INV-57 - Durable execution.

The stdlib-only replay engine is importable without the optional ``pk_core``
conformance framework.  Framework-bound component objects are loaded lazily.
"""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "INV-57"
ELEMENT_NAME = "Durable execution"

from .durable import (  # noqa: E402
    HISTORY_EVENT_SCHEMA,
    ActivityInDoubt,
    ConcurrentRun,
    Crash,
    DurableExecutionError,
    HistoryCorruption,
    HistoryEvent,
    HistoryLimitExceeded,
    HistoryStore,
    InMemoryHistoryStore,
    NonDeterminism,
    RecordedActivityFailure,
    UnsupportedResult,
    Worker,
)
from .errors import (  # noqa: E402
    ConcurrentAppend,
    ConfigRejected,
    DeadlineExceeded,
    EffectUnresolved,
    Frozen,
    HistoryQuarantined,
    IllegalTransition,
    InvalidIdentity,
    Overloaded,
    OwnershipConflict,
    StaleOwner,
    Unauthorized,
)
from .identity import WorkflowIdentity  # noqa: E402


def __getattr__(name: str):
    if name in {"COMPONENT", "DurableExecutionComponent"}:
        from .component import COMPONENT, DurableExecutionComponent

        return {"COMPONENT": COMPONENT, "DurableExecutionComponent": DurableExecutionComponent}[name]
    if name == "build_contract":
        from .contract import build

        return build
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "HISTORY_EVENT_SCHEMA",
    "ActivityInDoubt",
    "ConcurrentRun",
    "Crash",
    "DurableExecutionError",
    "HistoryCorruption",
    "HistoryEvent",
    "HistoryLimitExceeded",
    "HistoryStore",
    "InMemoryHistoryStore",
    "NonDeterminism",
    "RecordedActivityFailure",
    "UnsupportedResult",
    "Worker",
    "WorkflowIdentity",
    "ConcurrentAppend",
    "ConfigRejected",
    "DeadlineExceeded",
    "EffectUnresolved",
    "Frozen",
    "HistoryQuarantined",
    "IllegalTransition",
    "InvalidIdentity",
    "Overloaded",
    "OwnershipConflict",
    "StaleOwner",
    "Unauthorized",
    "COMPONENT",
    "DurableExecutionComponent",
    "build_contract",
]
