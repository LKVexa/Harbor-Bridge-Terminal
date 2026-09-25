"""pk_core availability and compatibility probe (remediation item A01).

INV-31's runtime and boundary need only the standard library.  The 100-item
conformance gate needs the external ``pk_core`` framework, which is NOT bundled
and has no authoritative pin yet.  This probe makes absence or incompatibility
an intentional, documented failure (``INV31-E-PKCORE-UNAVAILABLE``) instead of
an uncontrolled ImportError at package import time.
"""
from __future__ import annotations

import importlib
from typing import Any

from .errors import FrameworkUnavailable

# Every pk_core symbol INV-31 consumes, and what INV-31 assumes about it.
REQUIRED_SYMBOLS: dict[str, tuple[str, ...]] = {
    "pk_core.contract": ("Contract", "Dependency", "Slo"),
    "pk_core.checklist": ("ChecklistItem", "Finding"),
    "pk_core.component": ("Component",),
}
REQUIRED_COMPONENT_METHODS = ("assess_implementation", "assess_security",
                              "assess_resilience", "satisfied", "_evidence")
# No authoritative pk_core release has been supplied, so no pin can be declared.
# Populate these from the release owner's coordinates; do not guess.
PINNED_VERSION: str | None = None
PINNED_DIGEST: str | None = None


def probe() -> dict[str, Any]:
    status: dict[str, Any] = {
        "available": False, "compatible": False, "version": None,
        "pinned_version": PINNED_VERSION, "pinned_digest": PINNED_DIGEST,
        "pin_satisfied": False, "missing": [], "error": None,
    }
    try:
        root = importlib.import_module("pk_core")
    except ModuleNotFoundError as exc:
        status["error"] = f"pk_core not installed ({exc.name})"
        return status
    except Exception as exc:  # noqa: BLE001 - a broken framework must not crash import
        status["error"] = f"pk_core import failed: {type(exc).__name__}"
        return status
    status["available"] = True
    status["version"] = getattr(root, "__version__", None)
    missing: list[str] = []
    for module_name, names in REQUIRED_SYMBOLS.items():
        try:
            module = importlib.import_module(module_name)
        except Exception:  # noqa: BLE001
            missing.append(module_name)
            continue
        for name in names:
            if not hasattr(module, name):
                missing.append(f"{module_name}.{name}")
    if not missing:
        component = importlib.import_module("pk_core.component").Component
        missing += [f"Component.{m}" for m in REQUIRED_COMPONENT_METHODS
                    if not hasattr(component, m)]
    status["missing"] = missing
    status["compatible"] = not missing
    status["pin_satisfied"] = bool(PINNED_VERSION) and status["version"] == PINNED_VERSION
    if missing:
        status["error"] = "pk_core is missing required symbols"
    return status


PK_CORE_STATUS: dict[str, Any] = probe()


def require_pk_core() -> None:
    """Raise the single actionable error when the conformance framework is unusable."""
    if not (PK_CORE_STATUS["available"] and PK_CORE_STATUS["compatible"]):
        raise FrameworkUnavailable(
            "pk_core conformance framework unavailable or incompatible: "
            f"{PK_CORE_STATUS['error']}. Install the release named in DEPENDENCIES.md "
            "or set PK_CORE_PATH; the 100-item gate cannot run without it.")
