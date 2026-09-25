"""Lifecycle state machines for INV-72 (C015).

Two machines are exposed:

* ``REQUEST`` - one accelerator requirement from receipt to release.
* ``DEVICE`` - the operator-visible state of one device as INV-72 treats it (discovery owns existence;
  INV-72 owns only whether it will *select* the device).

Illegal transitions raise ``AccelError("ACCEL_ILLEGAL_TRANSITION")``; terminal states have no exits.
"""
from __future__ import annotations

from .errors import AccelError

REQUEST = {
    "received": {"validated", "rejected", "cancelled"},
    "validated": {"matched", "refused", "cancelled", "expired"},
    "matched": {"reserved", "cancelled", "expired"},      # reserve=False stops at matched
    "reserved": {"released", "revoked"},
    "refused": set(),
    "rejected": set(),
    "cancelled": set(),
    "expired": set(),
    "released": set(),
    "revoked": set(),                                      # operator quarantine or stale-fence recovery
}
REQUEST_TERMINAL = frozenset(k for k, v in REQUEST.items() if not v)

DEVICE = {
    "available": {"reserved", "quarantined", "draining", "absent"},
    "reserved": {"available", "quarantined", "draining", "absent"},
    "draining": {"available", "quarantined", "absent"},    # no new selections; existing kept
    "quarantined": {"available", "absent"},                # no selections; operator must release
    "absent": {"available"},                               # missing from latest discovery
}


def check(machine: dict, current: str, target: str) -> None:
    if current not in machine or target not in machine[current]:
        raise AccelError("ACCEL_ILLEGAL_TRANSITION", f"{current} -> {target} not permitted",
                         current=current, target=target)


def table(machine: dict) -> list[tuple[str, str]]:
    return sorted((a, b) for a, bs in machine.items() for b in bs)
