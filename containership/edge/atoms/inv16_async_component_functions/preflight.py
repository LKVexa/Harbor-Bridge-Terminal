"""Certification preflight (closure items #1, #35): report and fail closed.

    python -m inv16_async_component_functions.preflight [--require-pk-core] [--json]

Reports interpreter, platform, package version, resolved import locations and
the ``pk_core`` resolution.  With ``--require-pk-core`` a missing, shadowed or
incompatible ``pk_core`` is a hard failure (exit 2) - certification never
proceeds on an ambient or partial framework.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import pathlib
import platform
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parent
PK_CORE_REQUIRED = ">=1.0,<2.0"          # compatibility contract, see docs/COMPATIBILITY.md
PK_CORE_SURFACE = ("pk_core.contract", "pk_core.checklist", "pk_core.component", "pk_core.integration")
SUPPORTED_PY = ((3, 10), (3, 13))
# Closure #14: concurrency/re-entrancy limits are enforced per process.  The only
# supported topology is one authoritative owner process per logical instance.
SUPPORTED_TOPOLOGIES = frozenset({"single-owner"})


def _ver_ok(v: str) -> bool:
    try:
        major = int(str(v).split(".")[0])
    except ValueError:
        return False
    return major == 1


def run(require_pk_core: bool = False, pk_core_module: str = "pk_core", topology: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    topo = topology or os.environ.get("INV16_TOPOLOGY", "single-owner")
    if topo not in SUPPORTED_TOPOLOGIES:
        errors.append(f"topology {topo!r} unsupported: INV-16 limits are process-local; run exactly one owner "
                      f"process per logical instance (supported: {sorted(SUPPORTED_TOPOLOGIES)})")
    py = sys.version_info[:2]
    if not SUPPORTED_PY[0] <= py <= SUPPORTED_PY[1]:
        errors.append(f"python {py[0]}.{py[1]} outside supported range "
                      f"{SUPPORTED_PY[0][0]}.{SUPPORTED_PY[0][1]}-{SUPPORTED_PY[1][0]}.{SUPPORTED_PY[1][1]}")
    version = (PKG_DIR / "VERSION").read_text().strip()
    rep = {
        "ok": True, "package_version": version, "python": platform.python_version(),
        "implementation": platform.python_implementation(), "platform": platform.platform(),
        "optimize": sys.flags.optimize, "package_path": str(PKG_DIR), "pk_core": None, "topology": topo,
        "errors": errors, "warnings": warnings,
    }
    spec = importlib.util.find_spec(pk_core_module)
    if spec is None:
        (errors if require_pk_core else warnings).append(
            f"{pk_core_module} not resolvable: 100-item assessment/gate/verify cannot run (closure #1 BLOCKED)")
    else:
        origin = pathlib.Path(spec.origin or "").resolve()
        info = {"module": pk_core_module, "origin": str(origin), "version": None, "surface": {}}
        if PKG_DIR in origin.parents:
            errors.append(f"{pk_core_module} is shadowed by a module inside this package: {origin}")
        try:
            mod = importlib.import_module(pk_core_module)
            info["version"] = getattr(mod, "__version__", None)
            for sub in PK_CORE_SURFACE:
                name = sub.replace("pk_core", pk_core_module, 1)
                try:
                    info["surface"][sub] = str(importlib.import_module(name).__file__)
                except Exception as exc:  # noqa: BLE001
                    info["surface"][sub] = None
                    errors.append(f"{name} missing from {pk_core_module} ({type(exc).__name__}): partial install")
            if not _ver_ok(info["version"]):
                errors.append(f"{pk_core_module} version {info['version']!r} not in {PK_CORE_REQUIRED}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{pk_core_module} import failed: {type(exc).__name__}: {exc}")
        rep["pk_core"] = info
    rep["ok"] = not errors
    return rep


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    rep = run(require_pk_core="--require-pk-core" in argv)
    if "--json" in argv:
        print(json.dumps(rep, indent=2, sort_keys=True))
    else:
        for k in ("package_version", "python", "implementation", "platform", "optimize", "package_path"):
            print(f"{k:16} {rep[k]}")
        print(f"{'pk_core':16} {rep['pk_core'] or 'NOT RESOLVED'}")
        for w in rep["warnings"]:
            print("WARN ", w)
        for e in rep["errors"]:
            print("ERROR", e)
        print("PREFLIGHT", "OK" if rep["ok"] else "FAILED")
    return 0 if rep["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
