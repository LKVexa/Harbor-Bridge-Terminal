"""INV-22 - Alternative WASI branch (master-applied component).

The remediation modules (matrix, shim, cert, store, auth, config, governance,
telemetry, preflight, evidence) import without ``pk_core``.  The pk_core-bound
``COMPONENT`` / contract are loaded lazily so a missing framework is reported
by ``preflight`` instead of breaking every import.
"""

__version__ = "4.3.0"

_LAZY = {"COMPONENT": ("component", "COMPONENT"),
         "AlternativeWasiBranchComponent": ("component", "AlternativeWasiBranchComponent"),
         "ELEMENT_ID": ("contract", "ELEMENT_ID"),
         "ELEMENT_NAME": ("contract", "ELEMENT_NAME"),
         "build_contract": ("contract", "build")}

__all__ = ["__version__", *_LAZY]


def __getattr__(name):
    if name in _LAZY:
        import importlib
        mod, attr = _LAZY[name]
        return getattr(importlib.import_module(f"{__name__}.{mod}"), attr)
    raise AttributeError(name)
