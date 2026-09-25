"""Make the package importable by name from a source checkout or an installed wheel."""

import importlib
import os
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
NAME = "inv23_hardware_virtualization_primitive"
if os.environ.get("INV23_FROM_INSTALLED") != "1" and str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))
pkg = importlib.import_module(NAME)


def mod(name):
    return importlib.import_module(f"{NAME}.{name}")
