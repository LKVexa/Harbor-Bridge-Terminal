# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Explicit, fail-closed dependency detection (GAP-001, GAP-002, GAP-003).

Nothing here silently substitutes. Each probe returns a structured status; the
callers decide, and production policy refuses anything short of ``ok``.
"""
from __future__ import annotations

import importlib
import platform
import re
import sys

from .errors import DependencyIncompatible

#: Tested pk_core range: >=MIN, <MAX_EXCL (see docs/COMPATIBILITY_MATRIX.md).
PK_CORE_MIN = (4, 0, 0)
PK_CORE_MAX_EXCL = (5, 0, 0)
PYTHON_MIN = (3, 10)

SIBLINGS = {
    "GAP-02": ("upstream", "Hardware capability discovery", True),
    "PLN-04": ("downstream", "Execution plane", False),
    "INV-41": ("peer", "Capability security", False),
    "INV-45": ("peer", "SFI mechanisms (software fallback)", False),
}


def _parse(version: str) -> tuple[int, ...]:
    parts = []
    for piece in version.split(".")[:3]:
        m = re.match(r"\d+", piece)          # leading digits only: "0rc1" -> 0, not 1
        parts.append(int(m.group()) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def pk_core_status() -> dict:
    try:
        mod = importlib.import_module("pk_core")
    except ModuleNotFoundError:
        return {"name": "pk_core", "state": "absent", "version": None}
    version = getattr(mod, "__version__", "0")
    v = _parse(version)
    ok = PK_CORE_MIN <= v < PK_CORE_MAX_EXCL
    return {"name": "pk_core", "state": "ok" if ok else "incompatible", "version": version,
            "supported": f">={'.'.join(map(str, PK_CORE_MIN))},<{'.'.join(map(str, PK_CORE_MAX_EXCL))}"}


def require_pk_core() -> str:
    """Raise a stable diagnostic unless a supported pk_core is importable."""
    st = pk_core_status()
    if st["state"] != "ok":
        raise DependencyIncompatible(
            f"pk_core {st['state']} (found {st['version']!r}, supported {st.get('supported', '>=4.0.0,<5.0.0')})")
    return st["version"]


def sibling_status(package: str = "pk_components") -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        from pk_core.integration import resolve  # type: ignore
    except ModuleNotFoundError:
        resolve = None
    for element, (relation, name, required) in SIBLINGS.items():
        mod = resolve(element, package) if resolve else None
        out[element] = {"name": name, "relation": relation, "required_for_hardware_tier": required,
                        "state": "ok" if mod is not None else "absent"}
    return out


def python_status() -> dict:
    ok = sys.version_info[:2] >= PYTHON_MIN
    return {"name": "python", "version": platform.python_version(), "state": "ok" if ok else "incompatible"}
