"""INV-66 - Enterprise Wasm control plane (master-applied component).

The ``pk_core`` binding (:mod:`.component`, :mod:`.contract`) is imported lazily so
the production layer and the local decision engine import and run without
``pk_core`` (4.2.0 defect: ``import inv66_enterprise_wasm_control_plane`` raised
``ModuleNotFoundError: pk_core`` in any checkout that lacked it).
"""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "INV-66"
ELEMENT_NAME = "Enterprise Wasm control plane"

_LAZY = {"COMPONENT": "component", "EnterpriseWasmControlPlaneComponent": "component", "build_contract": "contract"}


def __getattr__(name):
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(f".{_LAZY[name]}", __name__)
        return getattr(mod, "build" if name == "build_contract" else name)
    raise AttributeError(name)


__all__ = ["__version__", "COMPONENT", "EnterpriseWasmControlPlaneComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
