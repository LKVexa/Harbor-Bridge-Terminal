"""Test helper: make the package importable from a source checkout without installing."""
import os
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
PKG = PKG_DIR.name
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))

import importlib  # noqa: E402

pkg = importlib.import_module(PKG)
rt = importlib.import_module(PKG + ".runtime")


def sub(name):
    return importlib.import_module(f"{PKG}.{name}")


def scale(n: int) -> int:
    """INV16_STRESS_SCALE multiplies stress iteration counts (CI default 1)."""
    return max(1, int(n * float(os.environ.get("INV16_STRESS_SCALE", "1"))))
