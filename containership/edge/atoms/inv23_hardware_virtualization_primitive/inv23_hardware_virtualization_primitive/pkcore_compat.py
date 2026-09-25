"""``pk_core`` dependency resolution and compatibility (MC-01).

Resolution precedence (first match wins, no silent fallthrough once one is chosen):
  1. ``PK_CORE_PATH`` -- an explicit directory that *contains* the ``pk_core`` package.
  2. An installed distribution named ``pk-core`` / ``pk_core`` (``pip install``).
  3. Vendored copy ``vendor/pk_core`` -- accepted only if every file matches the
     SHA-256 pins in ``vendor/VENDORED.json`` (owner's PK_Master_Applied_All_Batches build).
  4. Monorepo sibling: ``<repo parent>/pk_core`` or ``<repo parent>/pk/pk_core`` --
     honoured only in ``dev`` mode, never in ``release`` mode.
An import is accepted only if it exposes the required API contract below and a
compatible version.  ``INV23_CONFORMANCE=release`` turns every failure into a hard error.

Canonical identity: project ``pk_core`` 4.0.0, "Post-Kubernetes master-applied component
runtime", source ``PK_Master_Applied_All_Batches.zip`` (identical in UC270, DF_Fabric,
UC32, BOTTLE_ROCKET_110K).  Upper bound 4.x is the tested range.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

CANONICAL_NAME = "pk_core"
MIN_VERSION: Tuple[int, ...] = (4, 0, 0)
MAX_TESTED: Optional[Tuple[int, ...]] = (4, 99, 99)
REQUIRED_API = {
    "pk_core.checklist": ("ChecklistItem", "Finding"),
    "pk_core.component": ("Component",),
    "pk_core.contract": ("Contract", "Dependency", "Slo"),
}
STATUSES = ("passed", "failed", "skipped", "dependency_missing", "dependency_incompatible")


@dataclass
class Resolution:
    status: str  # "ok" | "dependency_missing" | "dependency_incompatible"
    source: Optional[str] = None  # env | installed | sibling
    location: Optional[str] = None
    version: Optional[str] = None
    distribution: Optional[str] = None
    diagnostics: List[str] = field(default_factory=list)

    def as_evidence(self) -> dict:
        return {
            "status": self.status,
            "source": self.source,
            "location": self.location,
            "version": self.version,
            "distribution": self.distribution,
            "expected_range": expected_range(),
            "diagnostics": self.diagnostics,
        }


def expected_range() -> str:
    lo = ".".join(map(str, MIN_VERSION))
    hi = ".".join(map(str, MAX_TESTED)) if MAX_TESTED else "*"
    return f">={lo},<={hi}"


def mode() -> str:
    m = os.environ.get("INV23_CONFORMANCE", "dev").strip().lower()
    return "release" if m == "release" else "dev"


def _parse(v: str) -> Optional[Tuple[int, ...]]:
    try:
        return tuple(int(p) for p in v.split("+")[0].split(".")[:3])
    except (ValueError, AttributeError):
        return None


def _candidates(repo_root: Path) -> List[Tuple[str, Optional[str]]]:
    out: List[Tuple[str, Optional[str]]] = []
    env = os.environ.get("PK_CORE_PATH")
    if env:
        out.append(("env", env))
        return out  # explicit wins; do not look elsewhere
    try:
        for dist_name in ("pk-core", "pk_core"):
            md.distribution(dist_name)
            out.append(("installed", None))
            return out
    except md.PackageNotFoundError:
        pass
    vend = repo_root / "vendor"
    if (vend / "pk_core" / "__init__.py").is_file():
        out.append(("vendored", str(vend)))
        return out
    if mode() == "dev":
        parent = repo_root.parent
        for p in (parent, parent / "pk", parent.parent):
            if (p / "pk_core" / "__init__.py").is_file():
                out.append(("sibling", str(p)))
                break
    return out


def resolve(repo_root: Optional[Path] = None) -> Resolution:
    repo_root = repo_root or Path(__file__).resolve().parent
    cands = _candidates(repo_root)
    if not cands:
        return Resolution(
            "dependency_missing",
            diagnostics=[
                f"pk_core not found: set PK_CORE_PATH to the directory containing pk_core/, or pip install "
                f"a pk_core distribution ({expected_range()})"
            ],
        )
    source, loc = cands[0]
    if source == "vendored":
        bad = verify_vendored(Path(str(loc)))
        if bad:
            return Resolution(
                "dependency_incompatible", source, loc, diagnostics=["vendored pk_core fails integrity pins: " + ", ".join(bad[:5])]
            )
    if loc:
        if not (Path(loc) / "pk_core" / "__init__.py").is_file():
            return Resolution("dependency_missing", source, loc, diagnostics=[f"{source}: {loc} has no pk_core/__init__.py"])
        if loc not in sys.path:
            sys.path.insert(0, loc)
    for mod in [m for m in list(sys.modules) if m == "pk_core" or m.startswith("pk_core.")]:
        if getattr(sys.modules[mod], "__file__", None) is None:
            del sys.modules[mod]  # drop shims so the real package is inspected
    try:
        pk = importlib.import_module("pk_core")
    except ImportError as exc:
        return Resolution("dependency_missing", source, loc, diagnostics=[f"import failed: {exc}"])
    location = str(Path(getattr(pk, "__file__", "") or "?").resolve().parent)
    if loc and not location.startswith(str(Path(loc).resolve())):
        return Resolution(
            "dependency_incompatible", source, location, diagnostics=[f"imported pk_core from {location}, not from {loc} (shadowed)"]
        )
    version = getattr(pk, "__version__", None)
    dist = None
    try:
        dist = md.version("pk-core")
    except md.PackageNotFoundError:
        pass
    version = version or dist
    res = Resolution("ok", source, location, version, dist)
    missing = []
    for m, names in REQUIRED_API.items():
        try:
            mm = importlib.import_module(m)
        except ImportError:
            missing.append(m)
            continue
        missing += [f"{m}.{n}" for n in names if not hasattr(mm, n)]
    if missing:
        res.status = "dependency_incompatible"
        res.diagnostics.append("pk_core lacks required API: " + ", ".join(missing))
    pv = _parse(version) if version else None
    if pv is None:
        res.diagnostics.append(f"pk_core version unknown (expected {expected_range()})")
        if mode() == "release":
            res.status = "dependency_incompatible"
    elif pv < MIN_VERSION or (MAX_TESTED and pv > MAX_TESTED):
        res.status = "dependency_incompatible"
        res.diagnostics.append(f"pk_core {version} outside {expected_range()}")
    return res


def verify_vendored(vendor_dir: Path) -> List[str]:
    """Return the list of files that do not match VENDORED.json (empty = intact)."""
    import hashlib
    import json

    try:
        pins = json.loads((vendor_dir / "VENDORED.json").read_text(encoding="utf-8"))["files"]
    except (OSError, ValueError, KeyError):
        return ["VENDORED.json missing or invalid"]
    bad = [f for f, h in pins.items() if not (vendor_dir / f).is_file() or hashlib.sha256((vendor_dir / f).read_bytes()).hexdigest() != h]
    extra = [
        str(p.relative_to(vendor_dir)).replace(os.sep, "/")
        for p in (vendor_dir / "pk_core").rglob("*.py")
        if str(p.relative_to(vendor_dir)).replace(os.sep, "/") not in pins
    ]
    return bad + [f"unpinned:{e}" for e in extra]
