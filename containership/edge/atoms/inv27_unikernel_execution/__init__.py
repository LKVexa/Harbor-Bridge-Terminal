"""INV-27 - Unikernel execution (v4.3.0).

The admission/verification core (``admission``, ``image``, ``trust``, ``vmm``) is stdlib-only and
importable without ``pk_core``.  The pk_core contract/component are loaded lazily; ``_vendor/``
carries the owner's pk_core unchanged (see _vendor/PK_CORE_PROVENANCE.json).
"""
from __future__ import annotations

import os as _os
import sys as _sys

__version__ = "4.3.0"

ELEMENT_ID = "INV-27"
ELEMENT_NAME = "Unikernel execution"

_VENDOR = _os.path.join(_os.path.dirname(__file__), "_vendor")


def _ensure_pk_core() -> None:
    try:
        import pk_core  # noqa: F401
    except ModuleNotFoundError:
        if _VENDOR not in _sys.path:
            _sys.path.append(_VENDOR)


def build_contract():
    _ensure_pk_core()
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "UnikernelExecutionComponent"}:
        _ensure_pk_core()
        from . import component
        return getattr(component, name)
    raise AttributeError(name)


__all__ = ["__version__", "COMPONENT", "UnikernelExecutionComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
