"""Dependency and protocol compatibility (REPO-001, INV-40-C016, C027, C093).

pk_core: the exact API surface ``contract.py``/``component.py`` rely on is
declared here and checked at import time with a stable diagnostic.  The
supported version range is UNPINNED because no pk_core distribution was
supplied with this candidate; ``check_pk_core`` therefore reports BLOCKED
rather than guessing a range.

Protocols: every external document is ``NAME/major``.  This build speaks
exactly the majors in ``SUPPORTED``; a peer offering none of them receives
PK_FULL_VM_VERSION_UNSUPPORTED.  Minor evolution is additive-only (new
optional fields, new error codes) and never changes meaning of an existing
field - see docs/VERSIONING.md.
"""
from __future__ import annotations

import ast
import importlib
import pathlib

from .errors import OpError

PKG = pathlib.Path(__file__).resolve().parents[1]

PK_CORE_API = {
    "pk_core.contract": {"Contract", "Dependency", "Slo"},
    "pk_core.checklist": {"ChecklistItem", "Finding"},
    "pk_core.component": {"Component"},
}
PK_CORE_COMPONENT_METHODS = {"assess_implementation", "assess_architecture", "assess_security",
                             "assess_performance", "satisfied", "_evidence"}
PK_CORE_RANGE: str | None = None  # UNPINNED: no distribution supplied (blocker REPO-001)

SUPPORTED = {"PK_FULL_VM": [1], "PK_FULL_VM_BOOT": [1], "PK_FULL_VM_STATE": [1],
             "PK_FULL_VM_ERROR": [1], "PK_FULL_VM_CONFIG": [1], "PK_FULL_VM_AUDIT": [1]}


def imported_pk_core_symbols() -> dict[str, set[str]]:
    """Statically read which pk_core symbols the integration modules import."""
    out: dict[str, set[str]] = {}
    for f in ("contract.py", "component.py"):
        tree = ast.parse((PKG / f).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("pk_core"):
                out.setdefault(node.module, set()).update(a.name for a in node.names)
    return out


def check_pk_core() -> dict:
    try:
        pk = importlib.import_module("pk_core")
    except ImportError:
        return {"status": "ABSENT", "diagnostic": "PK_CORE_ABSENT: pk_core not importable; standalone runtime "
                "and fvt layer remain usable, integration component is unavailable", "range": PK_CORE_RANGE}
    missing = []
    for mod, names in PK_CORE_API.items():
        try:
            m = importlib.import_module(mod)
        except ImportError:
            missing.append(mod)
            continue
        missing += [f"{mod}.{n}" for n in names if not hasattr(m, n)]
    if not missing:
        comp = importlib.import_module("pk_core.component").Component
        missing += [f"Component.{n}" for n in PK_CORE_COMPONENT_METHODS if not hasattr(comp, n)]
    version = getattr(pk, "__version__", None)
    if missing:
        return {"status": "INCOMPATIBLE", "diagnostic": f"PK_CORE_INCOMPATIBLE: missing {sorted(missing)}",
                "version": version, "range": PK_CORE_RANGE}
    if PK_CORE_RANGE is None:
        return {"status": "BLOCKED", "diagnostic": "PK_CORE_UNPINNED: API surface present but no approved range",
                "version": version, "range": None}
    return {"status": "OK", "version": version, "range": PK_CORE_RANGE}


def negotiate(offered: dict[str, list[int]]) -> dict[str, int]:
    """Pick the highest common major per protocol the peer needs."""
    agreed = {}
    for name, majors in offered.items():
        common = set(majors) & set(SUPPORTED.get(name, []))
        if not common:
            raise OpError("PK_FULL_VM_VERSION_UNSUPPORTED", f"no common major for {name}",
                          offered=majors, supported=SUPPORTED.get(name, []))
        agreed[name] = max(common)
    return agreed
