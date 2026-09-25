"""Shared fixtures for the INV-52 4.3.0 suites (stdlib only)."""
from __future__ import annotations

import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv52_messaging_abstraction as pkg  # noqa: E402,F401
from inv52_messaging_abstraction.security import TokenAuthority  # noqa: E402

KEY = b"k" * 48
KEYS = {"k1": KEY}


class FakeClock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def authority(clock=None, keys=None):
    clock = clock or FakeClock()
    return TokenAuthority(lambda: KEYS if keys is None else keys, "k1", clock=clock), clock


def env(source="a", etype="e", data=None, **kw):
    return pkg.envelope(source, etype, {"n": 1} if data is None else data, **kw)
