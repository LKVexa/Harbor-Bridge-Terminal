"""Decision lifecycle state machine (MC-008).

States::

    proposed -> admitted -> delivering -> deployed -> rolled_back
            \\-> rejected          \\-> delivery_failed -> delivering
    admitted/delivering/deployed -> quarantined -> (admitted | rolled_back)

``rejected`` and ``rolled_back`` are terminal.  Every transition is journalled;
illegal transitions raise ``ILLEGAL_TRANSITION`` and are not recorded.
"""
from __future__ import annotations

TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset({"admitted", "rejected"}),
    "admitted": frozenset({"delivering", "quarantined", "rolled_back"}),
    "delivering": frozenset({"deployed", "delivery_failed", "quarantined"}),
    "delivery_failed": frozenset({"delivering", "quarantined", "rolled_back"}),
    "deployed": frozenset({"rolled_back", "quarantined"}),
    "quarantined": frozenset({"admitted", "rolled_back"}),
    "rejected": frozenset(),
    "rolled_back": frozenset(),
}
STATES = frozenset(TRANSITIONS)
TERMINAL = frozenset(s for s, t in TRANSITIONS.items() if not t)
OPERATOR_TRANSITIONS = frozenset({"quarantined", "rolled_back", "admitted"})


def legal(src: str, dst: str) -> bool:
    return dst in TRANSITIONS.get(src, frozenset())
