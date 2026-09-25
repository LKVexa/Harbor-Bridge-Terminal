"""Shared helpers for INV-68 evidence producers."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
PARENT = PKG.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))


def machine() -> dict:
    info = {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count": os.cpu_count(),
    }
    try:
        info["loadavg"] = [round(x, 2) for x in os.getloadavg()]
    except (AttributeError, OSError):
        pass
    return info


def revision() -> str:
    try:
        return subprocess.run(["git", "-C", str(PKG), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown (not a git checkout)"


def source_digest() -> str:
    """SHA-256 over the runtime source files (``*.py`` at package root), sorted by name."""
    h = hashlib.sha256()
    for p in sorted(PKG.glob("*.py")):
        h.update(p.name.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def write(path: Path, doc: dict) -> dict:
    from inv68_resource_packing import __version__
    doc = dict(doc)
    doc.setdefault("component", "INV-68")
    doc.setdefault("version", __version__)
    doc.setdefault("source_digest", source_digest())
    doc.setdefault("generated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
