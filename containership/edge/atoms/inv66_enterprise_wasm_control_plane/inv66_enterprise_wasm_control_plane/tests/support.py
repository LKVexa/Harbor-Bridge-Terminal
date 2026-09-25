"""Shared test bootstrap: make the package importable from a plain checkout."""
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))

from inv66_enterprise_wasm_control_plane.production.errors import EcpError  # noqa: E402,F401
from inv66_enterprise_wasm_control_plane.production.testing import Estate  # noqa: E402,F401

P = "inv66_enterprise_wasm_control_plane.production"


class FakeClock:
    def __init__(self, t: float = 1_790_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s
