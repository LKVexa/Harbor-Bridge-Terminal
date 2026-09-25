"""INV-15 - New asynchronous ABI (master-applied component).

v4.3.0: ``abi.AsyncAbi`` is the frozen v4.2 reference model; ``host.AsyncHost`` is
the checklist-driven reference host (see COMPONENT_STATUS.md)."""
from __future__ import annotations

__version__ = "4.3.0"

from .abi import (
    AsyncAbi,
    AsyncAbiError,
    BudgetExhausted,
    ForeignHandle,
    HandleConsumed,
    HandleSpaceExhausted,
    Subtask,
    SubtaskHandle,
    SubtaskNotReady,
    SubtaskState,
    WaitSetTooLarge,
)

from .errors import AbiError, CancelAck, CancelReason, ErrorCode  # noqa: E402
from .host import AsyncHost, InstanceView, Limits  # noqa: E402
from .handles import Handle  # noqa: E402

_LAZY = {"COMPONENT", "NewAsynchronousAbiComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"}


def __getattr__(name: str):
    if name in {"COMPONENT", "NewAsynchronousAbiComponent"}:
        from .component import COMPONENT, NewAsynchronousAbiComponent
        return {"COMPONENT": COMPONENT, "NewAsynchronousAbiComponent": NewAsynchronousAbiComponent}[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "AsyncAbi",
    "AsyncAbiError",
    "BudgetExhausted",
    "ForeignHandle",
    "HandleConsumed",
    "HandleSpaceExhausted",
    "Subtask",
    "SubtaskHandle",
    "SubtaskNotReady",
    "SubtaskState",
    "WaitSetTooLarge",
    "AbiError", "CancelAck", "CancelReason", "ErrorCode", "AsyncHost", "InstanceView", "Limits", "Handle",
    "COMPONENT",
    "NewAsynchronousAbiComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
