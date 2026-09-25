"""Coverage tags: each test declares exactly which checklist sub-check kinds it
evidences, e.g. ``@covers("G12-A001:spec1,unit,txn")``.

The evaluator only credits a kind for a component when at least one test
tagged with it ran and passed and no test tagged with it failed.  A skipped
test credits nothing.  Tags are claims about relevance that a reviewer can
audit line by line; the kind vocabulary is defined in
``evidence/kinds.py`` and unknown kinds are rejected at import time.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence"))
from kinds import KINDS  # noqa: E402


def covers(*specs: str):
    parsed = []
    for spec in specs:
        comp, _, kinds = spec.partition(":")
        if not comp.startswith("G12-") or len(comp) != 8:
            raise ValueError(f"bad component id {comp!r}")
        for k in kinds.split(","):
            k = k.strip()
            if k not in KINDS:
                raise ValueError(f"unknown kind {k!r} in {spec!r}")
            parsed.append((comp, k))

    def deco(fn):
        fn.__covers__ = getattr(fn, "__covers__", []) + parsed
        return fn
    return deco
