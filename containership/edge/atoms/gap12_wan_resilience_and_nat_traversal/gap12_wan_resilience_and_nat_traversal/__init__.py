"""GAP-12 - WAN resilience and NAT traversal (master-applied component).

v4.3.0: the package is importable without ``pk_core``.  The ``pk_core`` adapter
(``COMPONENT`` / ``WanResilienceAndNatTraversalComponent`` / contract helpers) is
resolved lazily so the stdlib runtime under :mod:`.wan` and the path state
machine can be used and tested on their own.
"""

__version__ = "4.3.0"
from .path import Partitioned, Path

_LAZY = {
    "COMPONENT": ("component", "COMPONENT"),
    "WanResilienceAndNatTraversalComponent": ("component", "WanResilienceAndNatTraversalComponent"),
    "ELEMENT_ID": ("contract", "ELEMENT_ID"),
    "ELEMENT_NAME": ("contract", "ELEMENT_NAME"),
    "build_contract": ("contract", "build"),
}


def __getattr__(name):
    if name in _LAZY:
        import importlib
        mod, attr = _LAZY[name]
        return getattr(importlib.import_module(f".{mod}", __name__), attr)
    raise AttributeError(name)


__all__ = ["__version__", "Partitioned", "Path", *_LAZY]
