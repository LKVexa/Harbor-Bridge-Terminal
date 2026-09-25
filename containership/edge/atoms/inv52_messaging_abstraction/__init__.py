"""INV-52 - Messaging abstraction.

The broker-independent runtime API is importable without the optional ``pk_core``
audit framework.  Audit integration objects are loaded lazily on demand.
"""
from __future__ import annotations

__version__ = "4.3.0"

from .metadata import ELEMENT_ID, ELEMENT_NAME
from .runtime import (
    ACTIVE,
    DISABLED,
    FROZEN,
    QUARANTINED,
    InvalidTransition,
    Overloaded,
    TopicDisabled,
    TopicUnavailable,
    IncompleteEnvelope,
    InvalidArgument,
    InvalidSubscription,
    MessagingError,
    PubSub,
    ResourceLimitExceeded,
    TopicDenied,
    envelope,
    validate_envelope,
)


def __getattr__(name: str):
    if name in {"COMPONENT", "MessagingAbstractionComponent"}:
        from .component import COMPONENT, MessagingAbstractionComponent
        return {"COMPONENT": COMPONENT, "MessagingAbstractionComponent": MessagingAbstractionComponent}[name]
    if name == "build_contract":
        from .contract import build
        return build
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "MessagingError",
    "TopicDenied",
    "IncompleteEnvelope",
    "InvalidArgument",
    "InvalidSubscription",
    "ResourceLimitExceeded",
    "PubSub",
    "envelope",
    "validate_envelope",
    "TopicUnavailable",
    "TopicDisabled",
    "Overloaded",
    "InvalidTransition",
    "ACTIVE",
    "FROZEN",
    "QUARANTINED",
    "DISABLED",
    "COMPONENT",
    "MessagingAbstractionComponent",
    "build_contract",
]
