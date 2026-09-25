"""M21 - protocol/interface version negotiation.

Peers exchange ``{"versions": [min, max], "features": [...], "nonce": str}``
signed by their identity key (authenticated negotiation). Selection: highest
common major.minor within both ranges and >= configured minimum; feature set is
the intersection. No overlap or below minimum -> UNSUPPORTED_VERSION (no silent
downgrade). Results are cached for a bounded lifetime and dropped on reconnect.
"""
from __future__ import annotations

import re
import time

from . import ed25519
from .errors import FabricError
from .identity import canonical

SUPPORTED = [(1, 0), (1, 1)]
MINIMUM = (1, 0)
FEATURES = ("batching", "deadline-propagation", "trace-context", "idempotency-keys")
CACHE_TTL_S = 600.0
_V = re.compile(r"^(\d{1,3})\.(\d{1,3})$")


def parse(v: str) -> tuple[int, int]:
    m = _V.match(v) if isinstance(v, str) else None
    if not m:
        raise FabricError("INVALID_ARGUMENT", f"malformed version {v!r}")
    return int(m.group(1)), int(m.group(2))


def offer(seed: bytes, *, lo="1.0", hi="1.1", features=FEATURES, nonce="") -> dict:
    body = {"versions": [lo, hi], "features": sorted(features), "nonce": nonce}
    return {"body": body, "sig": ed25519.sign(seed, canonical(body)).hex()}


def negotiate(peer_offer: dict, peer_public_key: bytes, *, minimum=MINIMUM, supported=SUPPORTED,
              local_features=FEATURES) -> dict:
    body = peer_offer.get("body") or {}
    try:
        sig = bytes.fromhex(peer_offer.get("sig", ""))
    except ValueError:
        sig = b""
    if not ed25519.verify(peer_public_key, canonical(body), sig):
        raise FabricError("UNAUTHENTICATED", "negotiation offer not signed by peer (downgrade protection)")
    vs = body.get("versions")
    if not (isinstance(vs, list) and len(vs) == 2):
        raise FabricError("INVALID_ARGUMENT", "versions must be [min, max]")
    lo, hi = parse(vs[0]), parse(vs[1])
    if lo > hi:
        raise FabricError("INVALID_ARGUMENT", "version range min > max")
    common = [v for v in supported if lo <= v <= hi and v >= minimum]
    if not common:
        raise FabricError("UNSUPPORTED_VERSION", "no mutually supported version at or above minimum",
                          detail={"peer": f"{vs[0]}..{vs[1]}", "minimum": "%d.%d" % minimum})
    feats = body.get("features") or []
    if not isinstance(feats, list) or any(not isinstance(f, str) for f in feats):
        raise FabricError("INVALID_ARGUMENT", "features must be a list of strings")
    v = max(common)
    return {"version": "%d.%d" % v, "features": sorted(set(feats) & set(local_features)),
            "expires_at": time.monotonic() + CACHE_TTL_S}


class NegotiationCache:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._d: dict = {}

    def get(self, peer: str):
        v = self._d.get(peer)
        if v and v["expires_at"] > self.clock():
            return v
        self._d.pop(peer, None)
        return None

    def put(self, peer: str, result: dict) -> None:
        self._d[peer] = result

    def on_reconnect(self, peer: str) -> None:
        self._d.pop(peer, None)
