"""INV-53 - Message reliability.

The framework-independent reliability primitives are importable without
``pk_core``.  Framework integration objects are loaded lazily when requested.
"""
from __future__ import annotations

__version__ = "5.1.0"
ELEMENT_ID = "INV-53"
ELEMENT_NAME = "Message reliability"

from .reliability import (
    DeadLetter,
    DeduplicationCapacityError,
    Delivery,
    DuplicateMessageError,
    IdempotentConsumer,
    QueueCapacityError,
    ReliabilityError,
    ReliableQueue,
)


def __getattr__(name: str):
    if name in {"COMPONENT", "MessageReliabilityComponent"}:
        from .component import COMPONENT, MessageReliabilityComponent

        globals()["COMPONENT"] = COMPONENT
        globals()["MessageReliabilityComponent"] = MessageReliabilityComponent
        return globals()[name]
    if name == "build_contract":
        from .contract import build

        globals()["build_contract"] = build
        return build
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "COMPONENT",
    "MessageReliabilityComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "ReliableQueue",
    "Delivery",
    "DeadLetter",
    "IdempotentConsumer",
    "ReliabilityError",
    "DuplicateMessageError",
    "QueueCapacityError",
    "DeduplicationCapacityError",
]
