"""Protocol version negotiation and compatibility (components 7, 23).

Interfaces are identified ``NAME/MAJOR[.MINOR]``.  Majors are incompatible; within a major,
the peer with the lower minor governs (newer peers MUST down-level).  A major is supported
for at least one deprecation window after its successor ships (docs/VERSIONING.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import INVALID_ARGUMENT, VERSION_UNSUPPORTED, BrokerError

_V = re.compile(r"^(PK_BROKER_[A-Z]+)/(\d+)(?:\.(\d+))?$")

SUPPORTED: dict[str, list[tuple[int, int]]] = {
    "PK_BROKER_FANOUT": [(1, 1)],
    "PK_BROKER_LOG": [(1, 1)],
    "PK_BROKER_OFFSET": [(1, 0)],
    "PK_BROKER_ERROR": [(1, 0)],
}
DEPRECATED: dict[str, set[int]] = {}


@dataclass(frozen=True)
class Version:
    name: str
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.name}/{self.major}.{self.minor}"


def parse(s: str) -> Version:
    m = _V.fullmatch(s or "")
    if not m:
        raise BrokerError(INVALID_ARGUMENT, "malformed interface version", value=s)
    return Version(m[1], int(m[2]), int(m[3] or 0))


def negotiate(offered: list[str]) -> Version:
    """Pick the highest mutually supported version from a peer's offer list."""
    best: Version | None = None
    for o in offered:
        v = parse(o)
        for major, minor in SUPPORTED.get(v.name, []):
            if v.major == major:
                cand = Version(v.name, major, min(minor, v.minor))
                if best is None or (cand.major, cand.minor) > (best.major, best.minor):
                    best = cand
    if best is None:
        raise BrokerError(VERSION_UNSUPPORTED, offered=",".join(offered)[:200])
    return best


def is_deprecated(v: Version) -> bool:
    return v.major in DEPRECATED.get(v.name, set())
