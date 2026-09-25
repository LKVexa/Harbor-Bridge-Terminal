"""Startup/preflight compatibility checks (MC-01, MC-02, MC-05).

Reports the installed ``pk_core`` version/API level, how it was discovered,
adjacent-dependency pin status, baseline pin status and the crypto backend,
each with a machine-readable code.  ``strict=True`` (release mode) fails on
anything unpinned, absent or discovered through an untrusted path.
"""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import re
from typing import Mapping

from .errors import Inv22Error

PKG_DIR = pathlib.Path(__file__).resolve().parent
REQUIRED_PK_CORE_API = 1
_SHA = re.compile(r"^[0-9a-f]{40}$")
_DIG = re.compile(r"^sha256:[0-9a-f]{64}$")


def _resource(rel: str) -> dict:
    with open(PKG_DIR / rel, encoding="utf-8") as fh:
        return json.load(fh)


def pk_core_status(env: Mapping[str, str] | None = None) -> dict:
    source: Mapping[str, str] = os.environ if env is None else env
    dev_path = source.get("PK_CORE_PATH")
    out: dict = {"check": "pk_core", "dev_override": None}
    if dev_path:
        p = pathlib.Path(dev_path)
        if not p.is_absolute() or not p.is_dir():
            return {**out, "ok": False, "code": "INV22.DEPENDENCY.UNAVAILABLE",
                    "detail": "PK_CORE_PATH must be an existing absolute directory"}
        out["dev_override"] = str(p.resolve())
    try:
        mod = importlib.import_module("pk_core")
    except ModuleNotFoundError:
        return {**out, "ok": False, "code": "INV22.DEPENDENCY.UNAVAILABLE", "detail": "pk_core is not installed"}
    api = getattr(mod, "API_LEVEL", None)
    ver = getattr(mod, "__version__", None)
    if api != REQUIRED_PK_CORE_API:
        return {**out, "ok": False, "code": "INV22.DEPENDENCY.INCOMPATIBLE", "version": ver, "api_level": api,
                "detail": f"pk_core API level {api!r} != required {REQUIRED_PK_CORE_API}"}
    return {**out, "ok": True, "code": None, "version": ver, "api_level": api,
            "location": str(pathlib.Path(mod.__file__ or ".").resolve().parent)}


def adjacent_status() -> dict:
    doc = _resource("dependencies/adjacent.json")
    rows = []
    for d in doc["dependencies"]:
        pinned = bool(_SHA.match(d.get("commit") or "")) and bool(_DIG.match(d.get("schema_digest") or ""))
        rows.append({"element": d["element"], "role": d["role"], "pinned": pinned,
                     "failure_policy": d["failure_policy"],
                     "code": None if pinned else "INV22.DEPENDENCY.INCOMPATIBLE"})
    return {"check": "adjacent", "ok": all(r["pinned"] for r in rows), "dependencies": rows}


def baseline_status() -> dict:
    from .matrix import check_baselines
    rep = check_baselines(_resource("baselines/manifest.json"))
    return {"check": "baselines", "ok": rep["pinned"], "problems": rep["problems"],
            "code": None if rep["pinned"] else "INV22.DEPENDENCY.INCOMPATIBLE"}


def crypto_status() -> dict:
    from .cert import HAVE_CRYPTO
    return {"check": "crypto", "ok": HAVE_CRYPTO, "code": None if HAVE_CRYPTO else "INV22.DEPENDENCY.UNAVAILABLE"}


def run(strict: bool = False, env: Mapping[str, str] | None = None) -> dict:
    checks = [pk_core_status(env), adjacent_status(), baseline_status(), crypto_status()]
    if strict and checks[0].get("dev_override"):
        checks[0].update(ok=False, code="INV22.DEPENDENCY.INCOMPATIBLE",
                         detail="release mode forbids PK_CORE_PATH developer overrides")
    report = {"schema": "PK_BRANCH_PREFLIGHT/1", "strict": strict, "ok": all(c["ok"] for c in checks), "checks": checks}
    if strict and not report["ok"]:
        first = next(c for c in checks if not c["ok"])
        raise Inv22Error(first["code"] or "INV22.DEPENDENCY.UNAVAILABLE", f"preflight failed: {first['check']}",
                         {"check": first["check"]})
    return report
