"""INV-16 - Async component functions (master-applied component)."""

__version__ = "4.3.0"
from .runtime import (ALLOW, REFUSE, AlreadyTerminal, AsyncFunctions, CallCancelled, CallIdAllocator,
                      CallIdExhausted, CallNotStarted, CallState, CallTrapped, CancelCode, CancelReason,
                      ConcurrencyLimitReached, DoubleDelivery, HistoryExpired, Outcome,
                      ReentrancyMode, ReentrancyPolicy, ReentrancyQueueFull, ReentrancyRefused,
                      StaleGeneration, TerminalConflict, Tombstone, TraceContext, TRANSITIONS)

__all__ = [
    "__version__", "COMPONENT", "AsyncComponentFunctionsComponent", "ELEMENT_ID", "ELEMENT_NAME",
    "build_contract", "AsyncFunctions", "CallState", "ReentrancyRefused", "ReentrancyQueueFull",
    "ConcurrencyLimitReached", "DoubleDelivery", "CallCancelled", "CallTrapped", "AlreadyTerminal",
    "TerminalConflict", "HistoryExpired", "StaleGeneration", "CallNotStarted", "CallIdExhausted",
    "CallIdAllocator", "CancelCode", "CancelReason", "Outcome", "ReentrancyMode", "ReentrancyPolicy",
    "ALLOW", "REFUSE", "Tombstone", "TraceContext", "TRANSITIONS",
]

_PK_CORE_NAMES = {"COMPONENT", "AsyncComponentFunctionsComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"}


def __getattr__(name):
    """pk_core-dependent names load lazily so the runtime imports without pk_core."""
    if name in _PK_CORE_NAMES:
        from . import component, contract
        table = {"COMPONENT": component.COMPONENT,
                 "AsyncComponentFunctionsComponent": component.AsyncComponentFunctionsComponent,
                 "ELEMENT_ID": contract.ELEMENT_ID, "ELEMENT_NAME": contract.ELEMENT_NAME,
                 "build_contract": contract.build}
        return table[name]
    raise AttributeError(name)
