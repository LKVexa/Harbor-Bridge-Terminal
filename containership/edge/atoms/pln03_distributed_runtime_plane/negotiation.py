"""Mixed-version peer negotiation and compatibility policy enforcement (MC-007, MC-016).

Interfaces are versioned ``PK_<NAME>/<major>``.  A peer advertises the majors it
speaks per interface; the highest common major is selected.  No common major is a
terminal ``PK_VERSION_UNSUPPORTED``.  Deprecated majors still negotiate but are
flagged so telemetry and release gates can see them (see COMPATIBILITY.md).
"""
from __future__ import annotations

from dataclasses import dataclass

from .runtime import RuntimePlaneError

RUNTIME_VERSION = "4.3.0"
SUPPORTED: dict[str, tuple[int, ...]] = {
    "PK_STATE": (1,), "PK_MESSAGE": (1,), "PK_SECRET": (1,), "PK_INVOKE": (1,),
}
DEPRECATED: dict[str, tuple[int, ...]] = {}
# N-1 policy: a release supports its own major and the previous one for >= 2 minor releases.


class VersionUnsupported(RuntimePlaneError):
    code = "PK_VERSION_UNSUPPORTED"


@dataclass(frozen=True)
class Agreement:
    versions: dict[str, int]
    deprecated: tuple[str, ...]
    peer_runtime: str


def hello() -> dict:
    return {"schema": "pk.hello/1", "runtime": RUNTIME_VERSION,
            "interfaces": {k: list(v) for k, v in SUPPORTED.items()}}


def negotiate(peer_hello: dict, required: tuple[str, ...] = tuple(SUPPORTED)) -> Agreement:
    if not isinstance(peer_hello, dict) or peer_hello.get("schema") != "pk.hello/1":
        raise VersionUnsupported("peer hello missing or unsupported schema")
    offered = peer_hello.get("interfaces") or {}
    chosen, deprecated = {}, []
    for iface in required:
        ours = set(SUPPORTED.get(iface, ()))
        theirs = {int(v) for v in offered.get(iface, []) if isinstance(v, int) and not isinstance(v, bool)}
        common = ours & theirs
        if not common:
            raise VersionUnsupported(f"no common major for {iface}", interface=iface,
                                     ours=",".join(map(str, sorted(ours))),
                                     theirs=",".join(map(str, sorted(theirs))))
        chosen[iface] = max(common)
        if chosen[iface] in DEPRECATED.get(iface, ()):
            deprecated.append(f"{iface}/{chosen[iface]}")
    return Agreement(chosen, tuple(deprecated), str(peer_hello.get("runtime", "unknown")))
