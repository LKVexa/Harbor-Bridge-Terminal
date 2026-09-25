"""Shared test setup: make the package importable and provide deterministic helpers."""
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PKG = PKG_DIR.name
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64


class Clock:
    def __init__(self, t: int = 1_800_000_000) -> None:
        self.t = t

    def __call__(self) -> int:
        return self.t
