"""INV-05 - Current control-state system (master-applied component).

The reference state model is importable without the external ``pk_core``
framework. Framework-bound exports are loaded lazily when requested.
"""
from __future__ import annotations

from .state import Compacted, ControlState, InvalidStateRequest

__version__ = "4.3.0"

__all__ = [
    "__version__",
    "Compacted",
    "ControlState",
    "InvalidStateRequest",
    "COMPONENT",
    "CurrentControlStateSystemComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]


def __getattr__(name: str):
    if name in {"COMPONENT", "CurrentControlStateSystemComponent"}:
        from .component import COMPONENT, CurrentControlStateSystemComponent
        return {"COMPONENT": COMPONENT, "CurrentControlStateSystemComponent": CurrentControlStateSystemComponent}[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    raise AttributeError(name)
