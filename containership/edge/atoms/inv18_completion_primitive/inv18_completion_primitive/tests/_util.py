"""Shared test helpers: make the package importable under its folder name."""
import importlib
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
NAME = PKG_DIR.name


def m(sub=None):
    return importlib.import_module(NAME + ("." + sub if sub else ""))


def rt(**cfg):
    config = m("config")
    return m("runtime").Runtime(config.ConfigStore({"environment": "test", **cfg}))
