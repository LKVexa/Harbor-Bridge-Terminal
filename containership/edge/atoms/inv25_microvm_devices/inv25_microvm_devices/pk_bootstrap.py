"""pk_core resolution and startup validation (docs/pk_core.md).

Supported distribution source: an installed distribution named ``pk_core``
resolvable from the interpreter's normal import path (declared as the optional
``[pk]`` extra in pyproject.toml).  ``PK_CORE_PATH`` is DEVELOPMENT-ONLY and is
refused when ``INV25_RELEASE=1``.

    python -m inv25_microvm_devices.pk_bootstrap   # prints a JSON status record, exit 0/3
"""
from __future__ import annotations

import importlib
import json
import os
import sys

from .compat import CompatibilityMismatch, check_pk_core
from .errors import Inv25Error, to_error

REQUIRED_MODULES = ("pk_core.checklist", "pk_core.component", "pk_core.contract")
REQUIRED_SYMBOLS = {"pk_core.checklist": ("ChecklistItem", "Finding"),
                    "pk_core.component": ("Component",),
                    "pk_core.contract": ("Contract", "Dependency", "Slo")}


class PkCoreUnavailable(Inv25Error):
    code = "INV25_DEPENDENCY_UNAVAILABLE"


def require_pk_core() -> str:
    dev_path = os.environ.get("PK_CORE_PATH")
    if dev_path:
        if os.environ.get("INV25_RELEASE") == "1":
            raise PkCoreUnavailable("PK_CORE_PATH is development-only and refused in release mode",
                                    dependency="pk_core")
        if dev_path not in sys.path:
            sys.path.insert(0, dev_path)
    try:
        pk = importlib.import_module("pk_core")
        for mod in REQUIRED_MODULES:
            m = importlib.import_module(mod)
            for sym in REQUIRED_SYMBOLS[mod]:
                if not hasattr(m, sym):
                    raise CompatibilityMismatch(f"{mod}.{sym} missing", peer="pk_core")
    except ModuleNotFoundError as exc:
        raise PkCoreUnavailable("pk_core is not installed; install the [pk] extra from the declared source",
                                dependency="pk_core") from exc
    version = getattr(pk, "__version__", None)
    if version is None:
        try:
            from importlib.metadata import version as _v
            version = _v("pk_core")
        except Exception:
            version = None
    return check_pk_core(version)


def main() -> int:
    try:
        v = require_pk_core()
        print(json.dumps({"pk_core": "ok", "version": v}))
        return 0
    except Inv25Error as exc:
        print(json.dumps(to_error(exc, operation="pk_core.bootstrap")))
        return 3


if __name__ == "__main__":
    sys.exit(main())
