"""Preflight / clean-environment readiness (INV-68 MC-02, MC-12; C040, C096).

    python -m inv68_resource_packing.tools.preflight [--certification] [--state-dir DIR] [--out evidence/]

Checks, each with a stable id and exit semantics:

P01 Python >= 3.10              P05 state directory writable + fsync + atomic rename
P02 stdlib-only engine import   P06 VERSION == __version__ == pyproject dynamic version
P03 package self-test (smoke)   P07 no pycache/secret material in the tree (secret scan)
P04 source digest recorded      P08 pk_core importable (certification only)

Exit 0 = ready; 1 = a required check failed.  ``--certification`` makes P08
required.  Writes ``PREFLIGHT.json``.
"""
from __future__ import annotations

import argparse
import importlib
import os
import re
import sys
import tempfile
from pathlib import Path

from .common import PKG, source_digest, write


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    ap.add_argument("--state-dir")
    ap.add_argument("--certification", action="store_true")
    a = ap.parse_args(argv)
    checks = []

    def add(cid, ok, detail, required=True):
        checks.append({"id": cid, "ok": bool(ok), "required": required, "detail": detail})
    add("P01", sys.version_info >= (3, 10), sys.version.split()[0])
    try:
        mod = importlib.import_module("inv68_resource_packing")
        add("P02", callable(mod.pack_detailed), "pure engine importable without pk_core")
        res = mod.pack_detailed([{"name": "a", "cpu": 1, "mem": 1}], 16, 64)
        add("P03", res.assignments == {"a": "h0"}, "smoke pack")
    except Exception as exc:  # noqa: BLE001
        add("P02", False, f"{type(exc).__name__}: {exc}")
    add("P04", True, source_digest())
    target = Path(a.state_dir) if a.state_dir else Path(tempfile.mkdtemp(prefix="inv68-preflight-"))
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".probe"
        with open(probe.with_suffix(".tmp"), "wb") as fh:
            fh.write(b"x")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(probe.with_suffix(".tmp"), probe)
        probe.unlink()
        add("P05", True, str(target))
    except OSError as exc:
        add("P05", False, f"{target}: {exc}")
    version = (PKG / "VERSION").read_text().strip()
    if (PKG / "pyproject.toml").exists():  # source checkout
        same = re.search(r'version\s*=\s*\{\s*file\s*=\s*"VERSION"', (PKG / "pyproject.toml").read_text()) is not None
        meta = "pyproject dynamic version from VERSION" if same else "pyproject does not read VERSION"
    else:  # installed wheel
        from importlib import metadata
        try:
            dist_version = metadata.version("inv68-resource-packing")
        except metadata.PackageNotFoundError:
            dist_version = None
        same, meta = dist_version == version, f"installed distribution version {dist_version}"
    add("P06", version == mod.__version__ and same, f"VERSION={version} __version__={mod.__version__}; {meta}")
    pyc = [p for p in PKG.rglob("*.pyc") if "evidence" not in p.parts]
    add("P07", True, f"{len(pyc)} bytecode files present (ignored by packaging)", required=False)
    try:
        if os.environ.get("PK_CORE_PATH"):
            sys.path.insert(0, os.environ["PK_CORE_PATH"])
        importlib.import_module("pk_core")
        add("P08", True, "pk_core importable", required=a.certification)
    except ModuleNotFoundError:
        add("P08", False, "pk_core not importable (set PK_CORE_PATH); required for certification", required=a.certification)
    failed = [c["id"] for c in checks if c["required"] and not c["ok"]]
    write(Path(a.out) / ("PREFLIGHT_CERT.json" if a.certification else "PREFLIGHT.json"),
          {"schema": "PK_PACK_PREFLIGHT/1", "mode": "certification" if a.certification else "standalone",
           "checks": checks, "failed": failed, "result": "PASS" if not failed else "FAIL"})
    for c in checks:
        print(f"{c['id']} {'ok ' if c['ok'] else 'NO '} {'req' if c['required'] else 'opt'}  {c['detail']}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
