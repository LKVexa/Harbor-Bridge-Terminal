"""Component 02 - static validation of ``pyproject.toml`` (contract PK_DYN_PYPROJECT/1).

No build or install is executed (no network, no isolated build env).  Instead the
declared metadata is checked against PEP 517/518/621 rules and against the files
actually on disk: build backend present, project identity valid, PEP 440 version,
requires-python lower bound, dependency declarations parse (and unpinned optional
dependencies are reported), package discovery matches real importable packages,
and every package-data glob matches at least one shipped file.
"""
from __future__ import annotations

import re
from pathlib import Path

from .pkcore_pin import parse_requirement, parse_version
from .core import Inv08Error

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
MIN_PYTHON = (3, 10)

try:  # Python >= 3.11
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - 3.10
    tomllib = None


def load(path: Path = PYPROJECT) -> dict:
    if tomllib is None:
        raise Inv08Error(code="INV08.PYPROJECT.NO_TOMLLIB", message="tomllib requires Python >= 3.11")
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def check(data: dict, root: Path = REPO_ROOT) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    bs = data.get("build-system", {})
    if bs.get("build-backend") != "setuptools.build_meta":
        errors.append("build-system.build-backend must be setuptools.build_meta")
    if not any(str(r).startswith("setuptools") for r in bs.get("requires", [])):
        errors.append("build-system.requires must list setuptools")
    proj = data.get("project", {})
    name = proj.get("name", "")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        errors.append(f"project.name {name!r} not normalized")
    try:
        v = parse_version(str(proj.get("version", "")))
        if v.local:
            errors.append("local version labels are not uploadable")
    except Inv08Error as exc:
        errors.append(exc.message)
    readme = proj.get("readme")
    rfile = readme.get("file") if isinstance(readme, dict) else readme
    if not rfile or not (root / rfile).is_file():
        errors.append(f"readme {rfile!r} missing")
    lic = proj.get("license")
    lic_text = lic.get("text") if isinstance(lic, dict) else lic
    if not lic_text:
        errors.append("license must be declared")
    elif str(lic_text).startswith("LicenseRef-UNASSIGNED"):
        warnings.append("license UNASSIGNED pending owner decision (component 05 BLOCKED)")
    rp = str(proj.get("requires-python", ""))
    m = re.fullmatch(r">=\s*(\d+)\.(\d+)", rp)
    if not m or (int(m[1]), int(m[2])) < MIN_PYTHON:
        errors.append(f"requires-python must be >={MIN_PYTHON[0]}.{MIN_PYTHON[1]}, got {rp!r}")
    else:
        lo = (int(m[1]), int(m[2]))
        cls = proj.get("classifiers", [])
        for c in cls:
            cm = re.fullmatch(r"Programming Language :: Python :: (\d+)\.(\d+)", c)
            if cm and (int(cm[1]), int(cm[2])) < lo:
                errors.append(f"classifier {c} below requires-python")
    if proj.get("dependencies"):
        errors.append("runtime dependencies must be empty (stdlib-only contract)")
    for extra, reqs in proj.get("optional-dependencies", {}).items():
        for r in reqs:
            try:
                req = parse_requirement(r)
                if not req.exact:
                    warnings.append(f"optional extra {extra!r}: {r} is not pinned")
            except Inv08Error as exc:
                errors.append(f"extra {extra}: {exc.message}")
    st = data.get("tool", {}).get("setuptools", {})
    find = st.get("packages", {}).get("find", {})
    includes = find.get("include", [])
    pkgs = sorted(str(p.parent.relative_to(root)).replace("/", ".")
                  for p in root.glob("**/__init__.py") if "__pycache__" not in p.parts)
    matched = [p for p in pkgs if any(re.fullmatch(i.replace(".", r"\.").replace("*", ".*"), p)
                                      for i in includes)]
    if "inv08_dynamic_infrastructure_model" not in matched:
        errors.append("package discovery does not include the top-level package")
    for pkg, globs in st.get("package-data", {}).items():
        base = root / pkg.replace(".", "/")
        if pkg not in pkgs:
            errors.append(f"package-data for unknown package {pkg}")
            continue
        for g in globs:
            if not list(base.glob(g)):
                warnings.append(f"package-data glob {pkg}:{g} matches no file")
    ver_file = root / "inv08_dynamic_infrastructure_model" / "VERSION"
    base_ver = ver_file.read_text(encoding="utf-8").strip() if ver_file.is_file() else None
    return {"ok": not errors, "errors": errors, "warnings": warnings, "packages": matched,
            "base_version": base_ver}
