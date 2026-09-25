"""pk_core pin + startup compatibility probe (component P0-01).

``deps/pk_core.lock.json`` is the single authoritative declaration of the
framework core.  Release/certification MUST refuse when it is UNRESOLVED.  This
archive ships it UNRESOLVED because the real ``pk_core`` was not supplied: the
build refuses to invent a version or digest.  Once the owner supplies the real
core, pin it with::

    python3 core_probe.py pin --path /path/to/pk_core --version X.Y.Z --source <index-or-repo>

which records the tree digest (sha256 over sorted relative path + file bytes,
excluding __pycache__) and the interpreter range.  ``probe()`` then verifies:
lock resolved -> importable -> version equal -> tree digest equal -> required
symbols present.  Each failure is a stable code; diagnostics never include local
filesystem paths.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
LOCK = HERE / "deps" / "pk_core.lock.json"
REQUIRED_SYMBOLS = {
    "pk_core.contract": ("Contract", "Dependency", "Slo"),
    "pk_core.checklist": ("ChecklistItem", "Finding"),
    "pk_core.component": ("Component",),
}
_BAD_VERSION = re.compile(r"(latest|\*|\^|~|>|<|,|\s|main|master|HEAD)", re.I)


def tree_digest(root: pathlib.Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            h.update(p.relative_to(root).as_posix().encode() + b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def load_lock(path: pathlib.Path = LOCK) -> dict:
    return json.loads(path.read_text())


def validate_lock(lock: dict) -> list:
    errs = []
    core = lock.get("pk_core", {})
    if lock.get("schema") != "PK_CORE_LOCK/1":
        errs.append("PK_CORE_LOCK_SCHEMA")
    if core.get("status") != "RESOLVED":
        errs.append("PK_CORE_UNPINNED")
        return errs
    v = core.get("version")
    if not isinstance(v, str) or not re.match(r"^\d+\.\d+\.\d+$", v) or _BAD_VERSION.search(v):
        errs.append("PK_CORE_FLOATING_VERSION")
    if not re.match(r"^[0-9a-f]{64}$", str(core.get("tree_sha256"))):
        errs.append("PK_CORE_NO_DIGEST")
    src = str(core.get("source", ""))
    if not src or src.startswith(("/", ".", "~")) or re.match(r"^[A-Za-z]:\\", src):
        errs.append("PK_CORE_MUTABLE_SOURCE")
    return errs


def _interp_ok(spec: str) -> bool:
    ver = sys.version_info[:2]
    for part in spec.split(","):
        m = re.match(r"^\s*(>=|<)\s*(\d+)\.(\d+)\s*$", part)
        if not m:
            return False
        tgt = (int(m.group(2)), int(m.group(3)))
        if m.group(1) == ">=" and ver < tgt or m.group(1) == "<" and ver >= tgt:
            return False
    return True


def probe(lock: dict | None = None) -> dict:
    """Return {'ok': bool, 'code': str, 'core': {...safe metadata...}}.  Never raises."""
    try:
        lock = lock if lock is not None else load_lock()
    except Exception:
        return {"ok": False, "code": "PK_CORE_LOCK_MISSING", "core": {}}
    errs = validate_lock(lock)
    core = lock.get("pk_core", {})
    safe = {"name": core.get("name"), "version": core.get("version"), "tree_sha256": core.get("tree_sha256"),
            "python": f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"}
    if errs:
        return {"ok": False, "code": errs[0], "core": safe, "all": errs}
    if not _interp_ok(lock.get("python_requires", "")):
        return {"ok": False, "code": "PK_CORE_INTERPRETER", "core": safe}
    spec = importlib.util.find_spec("pk_core")
    if spec is None or not spec.submodule_search_locations:
        return {"ok": False, "code": "PK_CORE_ABSENT", "core": safe}
    root = pathlib.Path(list(spec.submodule_search_locations)[0])
    try:
        mod = importlib.import_module("pk_core")
    except Exception:
        return {"ok": False, "code": "PK_CORE_IMPORT_FAILED", "core": safe}
    installed = getattr(mod, "__version__", None)
    if installed != core["version"]:
        return {"ok": False, "code": "PK_CORE_VERSION_MISMATCH", "core": dict(safe, installed_version=installed)}
    if tree_digest(root) != core["tree_sha256"]:
        return {"ok": False, "code": "PK_CORE_HASH_MISMATCH", "core": safe}
    for modname, syms in REQUIRED_SYMBOLS.items():
        try:
            m = importlib.import_module(modname)
        except Exception:
            return {"ok": False, "code": "PK_CORE_API_INCOMPATIBLE", "core": dict(safe, missing=modname)}
        missing = [s for s in syms if not hasattr(m, s)]
        if missing:
            return {"ok": False, "code": "PK_CORE_API_INCOMPATIBLE", "core": dict(safe, missing=f"{modname}:{missing[0]}")}
    return {"ok": True, "code": "PK_CORE_OK", "core": safe}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    pn = sub.add_parser("pin")
    pn.add_argument("--path", required=True)
    pn.add_argument("--version", required=True)
    pn.add_argument("--source", required=True)
    pn.add_argument("--python-requires", default=">=3.10,<3.14")
    a = ap.parse_args(argv)
    if a.cmd == "probe":
        r = probe()
        print(json.dumps(r, sort_keys=True))
        return 0 if r["ok"] else 2
    lock = {"schema": "PK_CORE_LOCK/1", "python_requires": a.python_requires,
            "pk_core": {"name": "pk_core", "status": "RESOLVED", "version": a.version, "source": a.source,
                        "tree_sha256": tree_digest(pathlib.Path(a.path))},
            "transitives": [], "upgrade_policy": load_lock().get("upgrade_policy")}
    errs = validate_lock(lock)
    if errs:
        print(json.dumps({"ok": False, "errors": errs}))
        return 2
    LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "tree_sha256": lock["pk_core"]["tree_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
