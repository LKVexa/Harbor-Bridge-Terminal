"""Shared test support.  ``INV39_CERT_TARGET=1`` marks a claimed production target:
absent prerequisites then FAIL instead of skipping (no silent skips, MC-086/087)."""
from __future__ import annotations

import functools
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import importlib
pkg = importlib.import_module(PKG_DIR.name)
CERT = os.environ.get("INV39_CERT_TARGET") == "1"


def require(cond: bool, why: str):
    if cond:
        return lambda f: f
    if CERT:
        def fail(f):
            @functools.wraps(f)
            def w(self, *a, **k):
                self.fail(f"certification prerequisite missing: {why}")
            return w
        return fail
    return unittest.skip(why)


def linux_enforcement_available() -> bool:
    if sys.platform != "linux":
        return False
    try:
        from importlib import import_module
        b = import_module(PKG_DIR.name + ".backends")
        b.require()
        return True
    except Exception:  # noqa: BLE001
        return False


@functools.lru_cache(maxsize=1)
def probes_binary() -> str | None:
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        return None
    out = pathlib.Path(tempfile.mkdtemp(prefix="inv39-probes-")) / "escape_probes"
    rc = subprocess.run([cc, "-O2", "-o", str(out), str(PKG_DIR / "tools" / "escape_probes.c")],
                        capture_output=True).returncode
    return str(out) if rc == 0 else None


LINUX = linux_enforcement_available()
