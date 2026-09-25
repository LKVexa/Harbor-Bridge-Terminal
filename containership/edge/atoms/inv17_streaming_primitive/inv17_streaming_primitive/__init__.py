"""INV-17 - Streaming primitive (master-applied component).

The runtime (``stream``, ``control``, ``security``, ``configuration``, ``observability``,
``adapters``) is stdlib-only. The ``pk_core`` certification adapter (``component``,
``contract``) is imported lazily so the runtime is usable without the framework.
"""

__version__ = "4.3.0"
from .stream import (BufferLimitExceeded, CancelToken, CreditExhausted, CreditLimitExceeded, ElementTypeMismatch,
                     EndDropped, NOT_READY, PROTOCOL_VERSIONS, Stream, StreamCancelled, StreamClosed, StreamConfig,
                     StreamError, StreamFrozen, StreamStats, StreamTimeout)

_LAZY = {"COMPONENT": "component", "StreamingPrimitiveComponent": "component", "ELEMENT_ID": "contract",
         "ELEMENT_NAME": "contract", "build_contract": "contract"}


def __getattr__(name):  # PEP 562: pk_core-dependent names resolve on first use
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(f".{_LAZY[name]}", __name__)
        return getattr(mod, "build" if name == "build_contract" else name)
    raise AttributeError(name)


__all__ = ["__version__", "COMPONENT", "StreamingPrimitiveComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract",
           "Stream", "StreamConfig", "StreamStats", "NOT_READY", "PROTOCOL_VERSIONS", "CancelToken", "StreamError",
           "CreditExhausted", "CreditLimitExceeded", "BufferLimitExceeded", "EndDropped", "StreamClosed",
           "ElementTypeMismatch", "StreamTimeout", "StreamCancelled", "StreamFrozen"]
