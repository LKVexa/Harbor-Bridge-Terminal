"""pk_core dependency gate (checklist component 1).

``pk_core`` is a *release-gate and conformance* dependency: runtime primitives never import it;
``component.py``/``contract.py`` (the conformance adapter) and ``VERIFY.py`` require it.

The approved range is declared once here and mirrored in ``pyproject.toml``
(``[project.optional-dependencies].conformance``). Resolution is by normal installed-package
import only; ad-hoc ``sys.path`` injection is not performed, so a stray copy on PYTHONPATH or
in the working directory is detected (origin check) rather than silently used.
"""
from __future__ import annotations

import importlib
import importlib.util
import pathlib
from typing import Optional, Tuple

from .errors import Inv20Error

PK_CORE_MIN = (1, 0, 0)       # inclusive
PK_CORE_MAX = (2, 0, 0)       # exclusive
REQUIRED_API = ("pk_core.checklist", "pk_core.component", "pk_core.contract")


class PkCoreUnavailable(Inv20Error):
    code = "E_POLICY_UNAVAILABLE"   # dependency_unavailable category; maps to BLOCKED


def _parse(v: str) -> Tuple[int, ...]:
    parts = []
    for p in v.split(".")[:3]:
        num = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts + [0] * (3 - len(parts)))


def probe() -> dict:
    """Machine-readable dependency status for evidence/dependencies/pk_core.json."""
    spec = importlib.util.find_spec("pk_core")
    if spec is None:
        return {"name": "pk_core", "status": "BLOCKED", "reason": "not_installed",
                "required": f">={'.'.join(map(str, PK_CORE_MIN))},<{'.'.join(map(str, PK_CORE_MAX))}"}
    origin = pathlib.Path(spec.origin or "").resolve()
    here = pathlib.Path(__file__).resolve().parent
    if here.parent in origin.parents and "site-packages" not in str(origin):
        return {"name": "pk_core", "status": "BLOCKED", "reason": "shadowed_by_source_tree", "origin": str(origin)}
    mod = importlib.import_module("pk_core")
    ver: Optional[str] = getattr(mod, "__version__", None)
    if ver is None:
        return {"name": "pk_core", "status": "BLOCKED", "reason": "no_version", "origin": str(origin)}
    if not PK_CORE_MIN <= _parse(ver) < PK_CORE_MAX:
        return {"name": "pk_core", "status": "BLOCKED", "reason": "incompatible_version", "version": ver}
    for m in REQUIRED_API:
        if importlib.util.find_spec(m) is None:
            return {"name": "pk_core", "status": "BLOCKED", "reason": f"missing_api:{m}", "version": ver}
    return {"name": "pk_core", "status": "PASS", "version": ver, "origin": str(origin)}


def require_pk_core() -> str:
    st = probe()
    if st["status"] != "PASS":
        raise PkCoreUnavailable(f"pk_core {st['reason']}")
    return st["version"]
