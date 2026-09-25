"""Peer-version compatibility matrix and fail-closed negotiation (docs/compatibility.md)."""
from __future__ import annotations

import re
from typing import Iterable

from .errors import Inv25Error

# Schemas this build can produce/consume, newest first.
SUPPORTED_SCHEMAS = {
    "catalogue": ["PK_DEVICE_CATALOGUE/1"],
    "diff": ["PK_DEVICE_SURFACE_DIFF/1"],
    "error": ["PK_DEVICE_ERROR/1"],
    "audit": ["PK_DEVICE_AUDIT_EVENT/1"],
    "activation": ["PK_DEVICE_CONFIG_ACTIVATION/1"],
}
# Minimum security version per interface: offers below this are refused (anti-downgrade).
MINIMUM_SECURITY_VERSION = {k: 1 for k in SUPPORTED_SCHEMAS}

# Compatibility matrix. Only rows marked "supported" with executable evidence may be claimed.
# Peers are externally owned; cells stay "unverified" until integration evidence exists.
MATRIX = [
    {"peer": "pk_core", "range": ">=4.0,<5.0", "status": "unverified",
     "evidence": None, "note": "pk_core not distributed with this archive (checklist item 1)"},
    {"peer": "INV-24 MicroVM runtime", "range": "unpinned", "status": "unverified", "evidence": None,
     "note": "contract fixture only: conformance/integration"},
    {"peer": "INV-35 High-performance VM I/O", "range": "unpinned", "status": "unverified", "evidence": None,
     "note": "contract fixture only"},
    {"peer": "INV-26 MicroVM snapshotting", "range": "unpinned", "status": "unverified", "evidence": None,
     "note": "contract fixture only"},
    {"peer": "GAP-13 Policy engine", "range": "unpinned", "status": "unverified", "evidence": None,
     "note": "contract fixture only"},
    {"peer": "INV-43 Transient-execution defense", "range": "unpinned", "status": "optional-unverified",
     "evidence": None, "note": "optional peer; absence never implies protection"},
    {"peer": "OASIS virtio", "range": "1.2", "status": "declared",
     "evidence": "ADR/ADR-0001-virtio-net-block.md", "note": "normative review edition; see ADR-0001"},
    {"peer": "CPython", "range": ">=3.10,<3.14", "status": "supported",
     "evidence": ".github/workflows/ci.yml", "note": "standalone package"},
]


class CompatibilityMismatch(Inv25Error):
    code = "INV25_COMPATIBILITY_MISMATCH"


_SCHEMA_RE = re.compile(r"^(PK_[A-Z_]+)/([0-9]{1,4})$")


def negotiate(interface: str, offered: Iterable[str]) -> str:
    """Pick the highest mutually supported schema. Never downgrades below the security floor."""
    if interface not in SUPPORTED_SCHEMAS:
        raise CompatibilityMismatch(f"unknown interface {interface}")
    ours = SUPPORTED_SCHEMAS[interface]
    floor = MINIMUM_SECURITY_VERSION[interface]
    candidates = []
    for o in offered:
        m = _SCHEMA_RE.fullmatch(o) if isinstance(o, str) else None
        if not m:
            continue  # unknown/future-malformed offers are ignored, never guessed at
        if int(m.group(2)) < floor:
            continue
        if o in ours:
            candidates.append((int(m.group(2)), o))
    if not candidates:
        raise CompatibilityMismatch(f"no compatible {interface} schema offered")
    return max(candidates)[1]


def version_tuple(v: str) -> tuple[int, ...]:
    core = re.split(r"[-+]", v, maxsplit=1)[0]
    return tuple(int(x) for x in core.split("."))


def check_pk_core(version: str | None) -> str:
    """Startup validation: reject unsupported pk_core versions before any audit/gate."""
    if not version:
        raise CompatibilityMismatch("pk_core version unknown", peer="pk_core")
    try:
        t = version_tuple(version)
    except ValueError as exc:
        raise CompatibilityMismatch("pk_core version unparseable", peer="pk_core") from exc
    if not ((4,) <= t[:1] and t[:1] < (5,)):
        raise CompatibilityMismatch("pk_core version outside supported range >=4.0,<5.0",
                                    peer="pk_core", found=version)
    return version
