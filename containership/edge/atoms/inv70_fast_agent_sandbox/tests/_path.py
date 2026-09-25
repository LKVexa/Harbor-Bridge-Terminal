"""Put the package's parent directory on sys.path so tests import the package by name."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))
PKG = ROOT.name
