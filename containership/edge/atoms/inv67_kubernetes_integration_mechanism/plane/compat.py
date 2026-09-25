"""Resource and feature compatibility/certification adapter (item 16) and
startup compatibility checks against the supported matrix (item 5).

GAP-15 certifies which translated features the runtime supports; a workload
using an uncertified feature is refused before any side effect.
"""
from __future__ import annotations

from .lifecycle import PlaneError

SUPPORTED_MATRIX = {
    "kubernetes": ["1.29", "1.30", "1.31", "1.32"],
    "python": ["3.10", "3.11", "3.12", "3.13"],
    "crd": ["inv67.linearfinance.org/v1alpha1"],
    "placement_wire": ["PK_K8S_PLACE/1"],
    "translate_wire": ["PK_K8S_TRANSLATE/1"],
}


def features_of(request: dict) -> set[str]:
    f: set[str] = set()
    for u in request["units"]:
        for part in (u["requests"], u["limits"]):
            f.update(k for k in part)
    if request.get("labels"):
        f.add("labels")
    if request.get("annotations"):
        f.add("annotations")
    if len(request["units"]) > 1:
        f.add("multiContainer")
    return f


def certify(request: dict, certified: list[str]) -> None:
    missing = sorted(features_of(request) - set(certified))
    if missing:
        raise PlaneError("INV67_INCOMPATIBLE", f"features not certified by GAP-15: {missing}", features=missing)


def check_peer(kind: str, version: str) -> None:
    allowed = SUPPORTED_MATRIX.get(kind)
    if allowed is None:
        raise PlaneError("INV67_INCOMPATIBLE", f"unknown peer kind {kind}")
    if kind in ("kubernetes", "python"):
        mm = ".".join(str(version).lstrip("v").split(".")[:2])
        ok = mm in allowed
    else:
        ok = version in allowed
    if not ok:
        raise PlaneError("INV67_INCOMPATIBLE", f"{kind} {version} outside supported matrix", allowed=allowed)
