"""Formal instance lifecycle (MC-016; C016, C024).  docs/LIFECYCLE.md is generated from TRANSITIONS.

States:  pending -> verified -> starting -> running -> stopping -> stopped
                      |            |           |
                      v            v           v
                  rejected       failed    quarantined -> stopping
Terminal: rejected, stopped, failed(after cleanup).  Every transition is recorded with a reason
code; an illegal transition raises ``UK_ILLEGAL_TRANSITION`` and changes nothing.
"""
from __future__ import annotations

from .errors import UkError

TRANSITIONS: dict[str, frozenset] = {
    "pending": frozenset({"verified", "rejected"}),
    "verified": frozenset({"starting", "rejected"}),
    "starting": frozenset({"running", "failed"}),
    "running": frozenset({"stopping", "quarantined", "failed"}),
    "quarantined": frozenset({"stopping"}),
    "stopping": frozenset({"stopped"}),
    "failed": frozenset({"stopped"}),
    "rejected": frozenset(),
    "stopped": frozenset(),
}
TERMINAL = frozenset(s for s, nxt in TRANSITIONS.items() if not nxt)


def check(current: str, target: str) -> None:
    if current not in TRANSITIONS or target not in TRANSITIONS[current]:
        raise UkError("UK_ILLEGAL_TRANSITION", f"{current} -> {target} is not permitted", current=current, target=target)


def render_markdown() -> str:
    lines = ["# INV-27 instance lifecycle (generated from lifecycle.TRANSITIONS)", "",
             "| From | Allowed next states |", "|---|---|"]
    for s, nxt in TRANSITIONS.items():
        lines.append(f"| `{s}` | {', '.join(f'`{x}`' for x in sorted(nxt)) or '*(terminal)*'} |")
    lines += ["", "Any other transition raises `UK_ILLEGAL_TRANSITION` and leaves state unchanged."]
    return "\n".join(lines) + "\n"
