"""MC-01: pinned, fail-closed ``pk_core`` dependency gate.

The checklist adapter needs ``pk_core``. This module declares the supported
range, the exact API surface INV-10 consumes, and refuses to bind to a
partial/unexpected implementation (e.g. a stray module on ``PYTHONPATH``).
"""
from __future__ import annotations

import importlib
import re
import importlib.metadata
from typing import Any

from .errors import DependencyIncompatible, DependencyUnavailable

# Supported range. The real pk_core release line is not bundled with this
# archive; this range is a declared assumption and must be qualified against
# the actual pk_core distribution (see docs/COMPATIBILITY.json).
PK_CORE_MIN = (1, 0, 0)
PK_CORE_MAX_EXCLUSIVE = (2, 0, 0)

# Minimum API surface consumed by contract.py / component.py.
REQUIRED_SURFACE: dict[str, tuple[str, ...]] = {
    "pk_core.contract": ("Contract", "Dependency", "Slo"),
    "pk_core.checklist": ("ChecklistItem", "Finding"),
    "pk_core.component": ("Component",),
}


def _parse(version: str) -> tuple[int, int, int]:
    parts = []
    for piece in version.split(".")[:3]:
        m = re.match(r"\d+", piece)
        parts.append(int(m.group(0)) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)  # type: ignore[return-value]


def check(*, require_distribution: bool = True) -> dict[str, Any]:
    """Verify pk_core is installed, in range, and exposes the required surface."""
    version = None
    try:
        version = importlib.metadata.version("pk_core")
    except importlib.metadata.PackageNotFoundError:
        if require_distribution:
            raise DependencyUnavailable(
                "pk_core distribution is not installed (a bare module on PYTHONPATH is not accepted)",
                dependency="pk_core",
            ) from None
    if version is not None:
        parsed = _parse(version)
        if not (PK_CORE_MIN <= parsed < PK_CORE_MAX_EXCLUSIVE):
            raise DependencyIncompatible(
                f"pk_core {version} outside supported range",
                dependency="pk_core", observed=version,
                supported=f">={'.'.join(map(str, PK_CORE_MIN))},<{'.'.join(map(str, PK_CORE_MAX_EXCLUSIVE))}",
            )
    missing: list[str] = []
    for module_name, names in REQUIRED_SURFACE.items():
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
            continue
        missing.extend(f"{module_name}.{n}" for n in names if not hasattr(module, n))
    if missing:
        raise DependencyIncompatible(
            "pk_core is partially installed or missing required API",
            dependency="pk_core", missing=sorted(missing),
        )
    return {"dependency": "pk_core", "version": version, "surface": sorted(REQUIRED_SURFACE)}
