"""INV-42 - Capability descriptors (master-applied component)."""

__version__ = "4.3.0"

from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
from .descriptors import (
    CLOSE_SCHEMA,
    ComponentDisabled,
    KeyUnavailable,
    emergency_disable,
    emergency_enable,
    is_disabled,
    STATUS_SCHEMA,
    TABLE_LIMIT,
    WIRE_SCHEMA,
    Descriptor,
    DescriptorClosed,
    DescriptorError,
    DescriptorTable,
    ForeignDescriptor,
    ForkedTable,
    InvalidDescriptor,
    SessionExhausted,
    TableDestroyed,
    TableFull,
    TypeMismatch,
)

__all__ = [
    "__version__",
    "COMPONENT",
    "CapabilityDescriptorsComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "WIRE_SCHEMA",
    "CLOSE_SCHEMA",
    "STATUS_SCHEMA",
    "TABLE_LIMIT",
    "Descriptor",
    "DescriptorTable",
    "DescriptorError",
    "InvalidDescriptor",
    "ForeignDescriptor",
    "DescriptorClosed",
    "TypeMismatch",
    "TableDestroyed",
    "TableFull",
    "SessionExhausted",
    "ForkedTable",
    "ComponentDisabled",
    "KeyUnavailable",
    "emergency_disable",
    "emergency_enable",
    "is_disabled",
]


def __getattr__(name):
    # The certification adapter depends on pk_core; import it lazily so the
    # runtime, audit, telemetry and transport modules stay usable without it.
    if name in ("COMPONENT", "CapabilityDescriptorsComponent"):
        from . import component
        return getattr(component, name)
    raise AttributeError(name)
