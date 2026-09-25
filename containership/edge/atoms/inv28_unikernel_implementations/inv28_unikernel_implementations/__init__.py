"""INV-28 - Unikernel implementations (master-applied component).

The register/selection engine (``model``, ``policy``, ``registry``, ``selection``, ``binding``,
``certification``, ``advisories``, ``rollout``, ``observability``, ``service``) is stdlib-only and
importable without ``pk_core``.  The pk_core conformance component is loaded lazily; if ``pk_core``
is not importable from the environment, the copy vendored under ``_vendor/`` (provenance in
``_vendor/PK_CORE_PROVENANCE.json``) is used.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

__version__ = "4.3.0"

from .errors import Inv28Error, Reason, RefusalError, ValidationError  # noqa: E402
from .model import ToolchainRecord  # noqa: E402
from .selection import Refusal, SelectionRequest, SelectionResult, Selector, SiteCapabilities  # noqa: E402

ELEMENT_ID = "INV-28"
ELEMENT_NAME = "Unikernel implementations"


def ensure_pk_core() -> None:
    """Make ``pk_core`` importable, preferring an installed copy over the vendored one."""
    try:
        import pk_core  # noqa: F401
    except ModuleNotFoundError:
        vendor = str(_Path(__file__).resolve().parent / "_vendor")
        if vendor not in _sys.path:
            _sys.path.insert(0, vendor)


def build_contract():
    ensure_pk_core()
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "UnikernelImplementationsComponent"}:
        ensure_pk_core()
        from . import component
        return getattr(component, name)
    raise AttributeError(name)


__all__ = ["__version__", "COMPONENT", "UnikernelImplementationsComponent", "ELEMENT_ID", "ELEMENT_NAME",
           "build_contract", "ensure_pk_core", "ToolchainRecord", "SelectionRequest", "SelectionResult", "Refusal",
           "SiteCapabilities", "Selector", "Inv28Error", "Reason", "RefusalError", "ValidationError"]
