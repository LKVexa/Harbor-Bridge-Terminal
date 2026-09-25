"""Version negotiation and mixed-version compatibility (C016, C027, C093).

Policy (ops/COMPATIBILITY_POLICY.md):
* Wire schemas are ``NAME/<major>``.  Within one major version, changes are additive and optional only;
  unknown *optional* fields from a newer minor peer are ignored on read, never on security fields.
* A peer is compatible when it shares a major version for every schema it uses; negotiation picks the
  highest common major.  No common major -> ``ACCEL_UNSUPPORTED_VERSION`` (fail closed, never guess).
* Component versions follow SemVer.  N-1 minor releases of the same major are supported for mixed-version
  rollout; deprecations announce one minor ahead and are removed only at a major.
"""
from __future__ import annotations

import re

from .errors import AccelError

COMPONENT_VERSION = "4.3.0"
SUPPORTED = {"PK_ACCEL_REQ": {1}, "PK_ACCEL_INVENTORY": {1}, "PK_ACCEL_MATCH": {1}, "PK_ACCEL_ERROR": {1},
             "PK_ACCEL_CONFIG": {1}, "PK_ACCEL_AUDIT_EVENT": {1}, "PK_ACCEL_STATUS": {1}}
# fields a reader may ignore if a newer minor peer sends them; everything else unknown is rejected
IGNORABLE_OPTIONAL = {"PK_ACCEL_REQ": {"hints", "labels", "priority"}}
SECURITY_FIELDS = {"PK_ACCEL_REQ": {"tenant", "isolation"}}
_V = re.compile(r"^([A-Z_]+)/(\d+)$")


def parse(tag: str) -> tuple[str, int]:
    m = _V.match(tag or "") if isinstance(tag, str) else None
    if not m:
        raise AccelError("ACCEL_UNSUPPORTED_VERSION", f"bad schema tag {tag!r}")
    return m.group(1), int(m.group(2))


def negotiate(peer_offers: dict[str, list[int]]) -> dict[str, int]:
    out = {}
    for name, majors in peer_offers.items():
        common = SUPPORTED.get(name, set()) & set(majors)
        if not common:
            raise AccelError("ACCEL_UNSUPPORTED_VERSION", f"no common major for {name}",
                             ours=sorted(SUPPORTED.get(name, ())), theirs=sorted(majors))
        out[name] = max(common)
    return out


def accept_request(payload: dict) -> dict:
    """Read a PK_ACCEL_REQ from a possibly newer minor peer: drop ignorable optional fields only."""
    tag = payload.get("schema", "PK_ACCEL_REQ/1")
    name, major = parse(tag)
    if name != "PK_ACCEL_REQ" or major not in SUPPORTED["PK_ACCEL_REQ"]:
        raise AccelError("ACCEL_UNSUPPORTED_VERSION", f"cannot read {tag}")
    return {k: v for k, v in payload.items() if k not in IGNORABLE_OPTIONAL["PK_ACCEL_REQ"]}


def semver(v: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v or "")
    if not m:
        raise ValueError(f"not semver: {v!r}")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def peer_supported(peer_version: str, ours: str = COMPONENT_VERSION) -> bool:
    a, b = semver(peer_version), semver(ours)
    return a[0] == b[0] and b[1] - 1 <= a[1] <= b[1] + 1
