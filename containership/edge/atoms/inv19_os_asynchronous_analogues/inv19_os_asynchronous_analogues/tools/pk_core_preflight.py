"""MC-01 - pk_core dependency preflight (deterministic BLOCKED, never skip-green).

Reads ``deps/pk_core.lock.json``.  Exit codes:
  0 GO       pk_core importable, version == pinned, digest matches (if pinned)
  2 BLOCKED  pk_core absent, lock unresolved, wrong version, corrupt install
Always prints one JSON line so the evidence bundle can record the outcome.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata as md
import json
import os
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
LOCK = PKG / "deps" / "pk_core.lock.json"


def _tree_digest(root: pathlib.Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def preflight(env_path: str | None = None) -> dict:
    lock = json.loads(LOCK.read_text())
    out = {"check": "pk_core_preflight", "lock": lock, "result": "BLOCKED", "reasons": []}
    if lock.get("status") != "PINNED":
        out["reasons"].append("LOCK_UNRESOLVED: authoritative pk_core source/version not recorded")
    path = env_path if env_path is not None else os.environ.get("PK_CORE_PATH")
    if path:
        out["dev_override"] = "PK_CORE_PATH"  # documented development-only override
        sys.path.insert(0, path)
    try:
        mod = importlib.import_module("pk_core")
    except ModuleNotFoundError:
        out["reasons"].append("DEPENDENCY_UNAVAILABLE: pk_core not importable")
        return out
    except Exception as exc:  # corrupt / partial installation
        out["reasons"].append(f"DEPENDENCY_CORRUPT: {type(exc).__name__}")
        return out
    ver = getattr(mod, "__version__", None)
    try:
        ver = ver or md.version(lock.get("distribution", "pk_core"))
    except md.PackageNotFoundError:
        pass
    out["installed_version"] = ver
    for sub in ("pk_core.checklist", "pk_core.component", "pk_core.contract"):
        try:
            importlib.import_module(sub)
        except Exception as exc:
            out["reasons"].append(f"DEPENDENCY_CORRUPT: {sub} {type(exc).__name__}")
    if lock.get("version") and ver != lock["version"]:
        out["reasons"].append(f"VERSION_MISMATCH: installed {ver} != pinned {lock['version']}")
    if lock.get("tree_sha256") and getattr(mod, "__file__", None):
        dg = _tree_digest(pathlib.Path(mod.__file__).parent)
        out["installed_digest"] = dg
        if dg != lock["tree_sha256"]:
            out["reasons"].append("DIGEST_MISMATCH")
    if not out["reasons"]:
        out["result"] = "GO"
    return out


if __name__ == "__main__":
    r = preflight()
    print(json.dumps(r, sort_keys=True))
    sys.exit(0 if r["result"] == "GO" else 2)
