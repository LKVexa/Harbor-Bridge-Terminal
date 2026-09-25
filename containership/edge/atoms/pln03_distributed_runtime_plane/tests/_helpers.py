"""Shared fixtures: import the package from the archive root without installation."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pln03_distributed_runtime_plane as pkg  # noqa: E402
from pln03_distributed_runtime_plane import (  # noqa: E402
    audit_log, config, durability, envelope, lifecycle, negotiation, plane, resilience, runtime, telemetry,
    tokens, artifacts, wire,
)

KEY = b"k" * 32


class FakeClock:
    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def make_plane(caps=("state", "messaging", "secrets", "invoke"), *, cfg=None, clock=None, adapters=None):
    clock = clock or FakeClock()
    ring = tokens.KeyRing()
    ring.add("k1", KEY)
    issuer = tokens.TokenIssuer(ring, clock)
    verifier = tokens.TokenVerifier(ring, clock)
    adapters = adapters or {c: runtime.Adapter(f"{c}-a") for c in caps}
    store = None
    if cfg is not None:
        store = config.ConfigStore(clock=clock)
        store.activate(cfg, author="test", source="test", reason="test")
    gp = plane.GovernedRuntime({f"api:{c}": adapters[c] for c in caps}, verifier=verifier, config=store,
                               owner="role:pln03-owner", sleep=lambda s: clock.advance(s), clock=clock)
    gp.start()
    tok = issuer.mint("api", "t1", set(caps))
    return gp, tok, issuer, clock, adapters


def cfg_with(**over):
    import copy
    c = copy.deepcopy(config.DEFAULT)
    for k, v in over.items():
        c[k] = v
    return c
