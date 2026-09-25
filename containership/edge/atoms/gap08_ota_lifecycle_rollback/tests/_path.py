"""Make the package importable as ``gap08_ota_lifecycle_rollback`` from its parent directory."""
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))
PKG = PKG_DIR.name
