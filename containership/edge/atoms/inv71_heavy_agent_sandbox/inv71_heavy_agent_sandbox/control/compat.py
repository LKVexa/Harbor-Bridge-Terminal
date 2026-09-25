"""Versioning, negotiation and mixed-version skew rules (C016, C027, C084, C093).

Each surface is versioned separately.  Support window is N and N-1 majors
(minor versions are additive).  Unknown *optional* fields are ignored by
readers; unknown *required* features must be refused, never silently
activated.  The version/compatibility matrix is data (``MATRIX``) so the gate
and node start-up can reject combinations that are not listed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .errors import ControlError

SURFACES: Mapping[str, tuple[int, int]] = {
    # surface: (current major, current minor)
    "control_api": (1, 0),
    "event_schema": (2, 0),      # PK_HEAVYBOX_EGRESS/2 adds resolved/selected; /1 still readable
    "policy_schema": (1, 0),
    "config_schema": (1, 0),
    "guest_image_abi": (1, 0),
    "snapshot_format": (1, 0),
    "evidence_schema": (1, 0),
}
FEATURES: Mapping[str, str] = {
    # feature: minimum control_api "major.minor" able to interpret it
    "dns_bound_egress": "1.0", "fencing_epochs": "1.0", "idempotency_keys": "1.0",
    "session_freeze": "1.0", "resumable_sessions": "9.9",  # not supported by any released version
}
DEPRECATIONS: Mapping[str, Mapping[str, str]] = {
    "PK_HEAVYBOX_EGRESS/1": {"notice": "2026-09-23", "enforce_after": "2027-03-23",
                             "migration": "emit /2 records; /1 readers ignore resolved/selected"},
}
MAX_SKEW = {"controller_vs_node": 1, "node_vs_image_abi": 0, "schema_major": 1}


def parse_v(v: str) -> tuple[int, int]:
    try:
        a, b = v.split(".")[:2]
        return int(a), int(b)
    except Exception:
        raise ControlError("COMPAT.UNSUPPORTED_VERSION", repr(v)) from None


def supported(surface: str, peer: str) -> bool:
    cur_major, _ = SURFACES[surface]
    pm, _ = parse_v(peer)
    return cur_major - 1 <= pm <= cur_major


@dataclass(frozen=True)
class Negotiated:
    versions: Mapping[str, str]
    features: frozenset[str]


def negotiate(peer_versions: Mapping[str, str], requested_features: Iterable[str],
              required_features: Iterable[str] = ()) -> Negotiated:
    for s, v in peer_versions.items():
        if s not in SURFACES:
            continue  # unknown optional surface: ignore
        if not supported(s, v):
            raise ControlError("COMPAT.UNSUPPORTED_VERSION", f"{s}={v}")
    api = parse_v(peer_versions.get("control_api", "0.0"))
    own = SURFACES["control_api"]
    eff = min(api, own)
    ok = frozenset(f for f in requested_features if f in FEATURES and parse_v(FEATURES[f]) <= eff)
    missing = [f for f in required_features if f not in ok]
    if missing:
        raise ControlError("COMPAT.UNSUPPORTED_VERSION", f"required features unavailable: {missing}")
    return Negotiated({s: f"{min(parse_v(peer_versions.get(s, '%d.%d' % SURFACES[s])), SURFACES[s])[0]}.x"
                       for s in SURFACES}, ok)


def check_skew(controller: str, node: str, node_image_abi: str, image_abi: str) -> None:
    if abs(parse_v(controller)[0] - parse_v(node)[0]) > MAX_SKEW["controller_vs_node"]:
        raise ControlError("COMPAT.UNSUPPORTED_VERSION", "controller/node skew")
    if parse_v(node_image_abi)[0] != parse_v(image_abi)[0]:
        raise ControlError("COMPAT.UNSUPPORTED_VERSION", "image ABI major mismatch")


# Compatibility matrix.  Statuses: supported | unsupported | upgrade-only |
# downgrade-incompatible | requires-snapshot-rebuild | untested.  Every real
# runtime row is ``untested`` because no hardware run exists in this repository.
MATRIX: tuple[Mapping[str, str], ...] = (
    {"arch": "x86_64", "cpu": "intel", "host_kernel": "6.1-lts", "firecracker": "UNPINNED", "guest_kernel": "UNPINNED", "status": "untested"},
    {"arch": "x86_64", "cpu": "amd", "host_kernel": "6.1-lts", "firecracker": "UNPINNED", "guest_kernel": "UNPINNED", "status": "untested"},
    {"arch": "aarch64", "cpu": "graviton", "host_kernel": "6.1-lts", "firecracker": "UNPINNED", "guest_kernel": "UNPINNED", "status": "untested"},
    {"arch": "x86_64", "cpu": "any", "host_kernel": "any", "firecracker": "any", "guest_kernel": "any", "nested_virt": "yes", "status": "unsupported"},
    {"arch": "x86_64->aarch64", "cpu": "cross-arch", "host_kernel": "any", "firecracker": "any", "guest_kernel": "any", "snapshot_migration": "yes", "status": "unsupported"},
)


def deployable(row_filter: Mapping[str, str]) -> bool:
    for row in MATRIX:
        if all(row.get(k) == v for k, v in row_filter.items()):
            return row["status"] == "supported"
    return False
