"""INV-26 - MicroVM snapshotting.

The runtime (service, ports, adapters, crypto, metadata store, telemetry) is
importable without ``pk_core``. ``COMPONENT`` / ``build_contract`` (the
Post-Kubernetes conformance adapter) are resolved lazily and raise
``ModuleNotFoundError`` naming ``pk_core`` when it is absent — they never
silently degrade.
"""

__version__ = "6.0.0"

_LAZY = {
    "COMPONENT": ("component", "COMPONENT"),
    "MicrovmSnapshottingComponent": ("component", "MicrovmSnapshottingComponent"),
    "build_contract": ("contract", "build"),
}
ELEMENT_ID = "INV-26"
ELEMENT_NAME = "MicroVM snapshotting"


def __getattr__(name):
    if name in _LAZY:
        import importlib
        mod, attr = _LAZY[name]
        return getattr(importlib.import_module(f".{mod}", __name__), attr)
    raise AttributeError(name)


__all__ = ["__version__", "COMPONENT", "MicrovmSnapshottingComponent", "ELEMENT_ID", "ELEMENT_NAME",
           "build_contract"]
