"""INV-14 - Previous asynchronous model (master-applied component).

The legacy polling primitive is importable without ``pk_core``.  Framework-facing
objects are loaded lazily so behavioural/unit testing remains available even when
the larger post-Kubernetes framework has not been installed yet.
"""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "INV-14"
ELEMENT_NAME = "Previous asynchronous model"

from .polling import (
    ERROR_SCHEMA,
    MIGRATION_TARGET,
    POLL_SCHEMA,
    CancelToken,
    ForeignPollable,
    PollCancelled,
    PollSet,
    PollValidationError,
    Pollable,
)


def build_contract():
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "PreviousAsynchronousModelComponent"}:
        from .component import COMPONENT, PreviousAsynchronousModelComponent
        return {
            "COMPONENT": COMPONENT,
            "PreviousAsynchronousModelComponent": PreviousAsynchronousModelComponent,
        }[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "COMPONENT",
    "PreviousAsynchronousModelComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "Pollable",
    "PollSet",
    "PollValidationError",
    "ForeignPollable",
    "CancelToken",
    "PollCancelled",
    "POLL_SCHEMA",
    "ERROR_SCHEMA",
    "MIGRATION_TARGET",
]
