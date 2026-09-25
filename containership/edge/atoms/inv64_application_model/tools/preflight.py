"""Environment preflight and pk_core dependency verification (MC-02, MC-27, MC-30).

    python -m inv64_application_model.tools.preflight [--certification] [--out FILE]

Reports (machine-readable, ``PK_APP_PREFLIGHT/1``): Python version and path,
platform/arch, package version, the pk_core import origin (after resolving
``PK_CORE_PATH`` through ``realpath``), its version attribute, and a content
digest over every ``*.py`` file under it. Checks against
``compatibility.json`` — the single compatibility source of truth:

* Python outside the supported range -> FAIL (deterministic diagnostic);
* platform/arch row ``unsupported`` -> FAIL; ``experimental`` -> WARN;
* pk_core missing -> FAIL in ``--certification`` (WARN otherwise);
* pk_core pin absent from compatibility.json -> BLOCKED (certification FAIL):
  no certification path may float;
* pk_core digest or version differs from the pin -> FAIL (tamper/drift);
* pk_core directory group/world-writable, or reached through a symlink that
  leaves its declared root -> FAIL in certification (untrusted location).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        h.update(p.relative_to(root).as_posix().encode() + b"\x00")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def _vt(v: str) -> tuple:
    return tuple(int(x) for x in v.split(".")[:3])


def run(certification: bool = False, compat_path: Path | None = None) -> dict:
    compat = json.loads((compat_path or ROOT / "compatibility.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    def add(name, result, **info):
        checks.append({"check": name, "result": result, **info})

    py = ".".join(map(str, sys.version_info[:3]))
    lo, hi = compat["python"]["min"], compat["python"]["max"]
    add("python.version", "PASS" if _vt(lo)[:2] <= _vt(py)[:2] <= _vt(hi)[:2] else "FAIL",
        have=py, supported=f"{lo}..{hi}", executable=sys.executable)
    plat = f"{platform.system().lower()}-{platform.machine().lower()}"
    row = compat["platforms"].get(plat, "unsupported")
    add("platform", {"required": "PASS", "supported": "PASS", "experimental": "WARN"}.get(row, "FAIL"),
        have=plat, tier=row)
    from inv64_application_model import __version__
    ver_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    add("package.version", "PASS" if ver_file == __version__ else "FAIL", version=__version__, VERSION=ver_file)

    pk = compat["pk_core"]
    env_path = os.environ.get("PK_CORE_PATH")
    if env_path:
        real = os.path.realpath(env_path)
        if real not in sys.path:
            sys.path.insert(0, real)
    try:
        mod = importlib.import_module("pk_core")
        origin = Path(os.path.realpath(mod.__file__)).parent
        info = {"origin": str(origin), "version": getattr(mod, "__version__", None), "digest": _tree_digest(origin)}
        add("pk_core.import", "PASS", **info)
        if pk.get("pin_version") is None or pk.get("pin_sha256") is None:
            add("pk_core.pin", "BLOCKED" if certification else "WARN",
                reason="no pk_core pin recorded in compatibility.json; certification may not float")
        else:
            ok = info["digest"] == pk["pin_sha256"] and str(info["version"]) == pk["pin_version"]
            add("pk_core.pin", "PASS" if ok else "FAIL", want_version=pk["pin_version"], want_sha256=pk["pin_sha256"])
        if os.name == "posix":
            mode = origin.stat().st_mode
            if mode & (stat.S_IWGRP | stat.S_IWOTH):
                add("pk_core.location", "FAIL" if certification else "WARN", reason="group/world-writable dependency directory")
            else:
                add("pk_core.location", "PASS")
        if env_path and not str(origin).startswith(os.path.realpath(env_path)):
            add("pk_core.path", "FAIL" if certification else "WARN", reason="PK_CORE_PATH resolved outside its root (symlink/junction)")
    except ModuleNotFoundError:
        add("pk_core.import", "FAIL" if certification else "WARN",
            reason="pk_core not importable; set PK_CORE_PATH or install the pinned distribution (DEPENDENCIES.md)")
        add("pk_core.pin", "BLOCKED" if certification else "WARN", reason="no pk_core pin recorded" if pk.get("pin_version") is None else "pin present but module absent")
    crypto = importlib.util.find_spec("cryptography") is not None
    add("optional.cryptography", "PASS" if crypto else "WARN",
        reason=None if crypto else "EdDSA tokens, Ed25519 signatures and at-rest encryption refuse without it")
    bad = [c for c in checks if c["result"] in ("FAIL", "BLOCKED")]
    return {"schema": "PK_APP_PREFLIGHT/1", "mode": "certification" if certification else "development",
            "result": "FAIL" if bad else "PASS", "checks": checks}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--certification", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run(a.certification)
    text = json.dumps(res, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if res["result"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
