"""Audit chain verification (M18)."""
from __future__ import annotations

import json

from .emitter import GENESIS, _digest


def verify_chain(events: list[dict], *, expected_head: str | None = None) -> tuple[bool, str]:
    prev = GENESIS
    for i, ev in enumerate(events):
        if ev.get("seq") != i:
            return False, f"sequence gap at {i}"
        if ev.get("prev") != prev:
            return False, f"broken link at seq {i}"
        if _digest(ev) != ev.get("digest"):
            return False, f"digest mismatch at seq {i}"
        prev = ev["digest"]
    if expected_head is not None and prev != expected_head:
        return False, "head mismatch (truncation or substitution)"
    return True, "ok"


def verify_file(path: str, expected_head: str | None = None):
    events = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    return False, [], "unparseable line"
    ok, err = verify_chain(events, expected_head=expected_head)
    return ok, events, err
