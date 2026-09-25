"""Resolve and verify the external ``pk_core`` dependency (INV71-X001).

Status is one of:
  NOT_RUN      pk_core absent or the lock is UNPINNED (the shipped state)
  FAILED       pk_core present but digest/version/API mismatch
  VERIFIED     pk_core present, lock pinned, digest and API match

Only VERIFIED lets the production gate count pk_core conformance.  Ambient
``sys.path``/PYTHONPATH discovery is never trusted: the resolved package tree
must hash to the pinned sha256.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
LOCK = PKG / "deps" / "pk_core.lock.json"


def tree_digest(root: pathlib.Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root).as_posix().encode()
        data = p.read_bytes()
        h.update(len(rel).to_bytes(8, "big")); h.update(rel)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return h.hexdigest()


def probe(lock_path: pathlib.Path = LOCK, search: list[str] | None = None) -> dict:
    lock = json.loads(lock_path.read_text())["dependencies"]["pk_core"]
    out = {"schema": "PK_HEAVYBOX_PK_CORE_PROBE/1", "lock": lock, "status": "NOT_RUN", "reason": ""}
    candidates = [pathlib.Path(p) for p in (search or [os.environ.get("PK_CORE_PATH", ""), str(PKG.parent)]) if p]
    root = next((c / "pk_core" for c in candidates if (c / "pk_core" / "__init__.py").is_file()), None)
    if root is None:
        out["reason"] = "pk_core not present in PK_CORE_PATH or beside the package"
        return out
    out["found"] = str(root)
    if lock["sha256"] == "UNPINNED" or lock["version_range"] == "UNPINNED":
        out["reason"] = "pk_core present but the lock is UNPINNED; conformance cannot count"
        return out
    d = tree_digest(root)
    out["sha256"] = d
    if d != lock["sha256"]:
        out["status"], out["reason"] = "FAILED", "digest mismatch"
        return out
    saved_path, saved_mods = list(sys.path), {k: v for k, v in sys.modules.items() if k.split(".")[0] == "pk_core"}
    try:
        for k in saved_mods:
            del sys.modules[k]
        sys.path.insert(0, str(root.parent))
        from importlib import import_module
        c = import_module("pk_core.contract")
        missing = [n for n in ("Contract", "Dependency", "Slo") if not hasattr(c, n)]
    except Exception as exc:
        out["status"], out["reason"] = "FAILED", f"import failed: {type(exc).__name__}"
        return out
    finally:  # never leave a probed pk_core importable by the rest of the process
        sys.path[:] = saved_path
        for k in [k for k in sys.modules if k.split(".")[0] == "pk_core"]:
            del sys.modules[k]
        sys.modules.update(saved_mods)
    if missing:
        out["status"], out["reason"] = "FAILED", f"API missing {missing}"
        return out
    out["status"] = "VERIFIED"
    return out


if __name__ == "__main__":
    r = probe()
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["status"] in ("VERIFIED", "NOT_RUN") else 1)
