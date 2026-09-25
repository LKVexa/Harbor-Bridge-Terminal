"""INV-18 - Completion primitive (master-applied component).

The primitive, runtime, adapters and release gate are stdlib-only.  The
``pk_core`` audit integration (``COMPONENT``, ``build_contract``) is loaded
lazily so a missing ``pk_core`` cannot break the primitive (C031, C090).
"""

__version__ = "4.3.0"
from .errors import ErrorRecord, FutureError, Rejected
from .future import Abandoned, AlreadyResolved, AlreadyTaken, Cancelled, Future

ELEMENT_ID = "INV-18"
ELEMENT_NAME = "Completion primitive"

_LAZY = {"COMPONENT": ("component", "COMPONENT"),
         "CompletionPrimitiveComponent": ("component", "CompletionPrimitiveComponent"),
         "build_contract": ("contract", "build"),
         "Runtime": ("runtime", "Runtime")}


def __getattr__(name):
    if name in _LAZY:
        import importlib
        mod, attr = _LAZY[name]
        return getattr(importlib.import_module(f".{mod}", __name__), attr)
    raise AttributeError(name)


__all__ = ["__version__", "COMPONENT", "CompletionPrimitiveComponent", "ELEMENT_ID", "ELEMENT_NAME",
           "build_contract", "Future", "AlreadyResolved", "AlreadyTaken", "Abandoned", "Cancelled",
           "FutureError", "Rejected", "ErrorRecord", "Runtime"]
