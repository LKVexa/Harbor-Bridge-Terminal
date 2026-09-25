"""M39 - canary / staged-rollout controller (shadow comparison).

Before a new validator build or policy bundle is promoted, the candidate gate
runs in shadow against the incumbent on a sample corpus.  Promotion rule:

* any module the candidate ACCEPTS that the incumbent rejects/refuses is a
  *widening* - it blocks promotion unless its digest is pre-approved;
* narrowing (candidate rejects what incumbent accepted) is reported and
  requires explicit acknowledgement, because it can break tenants;
* any candidate ``error`` outcome blocks promotion.

Stages: shadow -> 1% -> 10% -> 50% -> 100%, each gated by this report plus
M30/M38 health; rollback = re-activate the previous signed bundle (M43).
"""
from __future__ import annotations

from typing import Iterable

STAGES = ("shadow", "1%", "10%", "50%", "100%")


def compare(incumbent, candidate, corpus: Iterable[tuple[str, bytes]], *, profile: str, engine: str,
            approved_widenings: frozenset[str] = frozenset(), acknowledged_narrowing: bool = False) -> dict:
    widen, narrow, errors, same = [], [], [], 0
    for name, m in corpus:
        a = incumbent.validate(m, profile=profile, engine=engine)
        b = candidate.validate(m, profile=profile, engine=engine)
        if b["outcome"] == "error":
            errors.append(name)
        if a["outcome"] == b["outcome"]:
            same += 1
        elif b["outcome"] == "accept":
            if b["module_digest"] not in approved_widenings:
                widen.append(name)
        elif a["outcome"] == "accept":
            narrow.append(name)
        else:
            same += 1  # reject <-> refuse reclassification is not a policy change
    blocked = bool(widen or errors or (narrow and not acknowledged_narrowing))
    return {"schema": "PK_CANARY_REPORT/1", "profile": profile, "agree": same,
            "widening": widen, "narrowing": narrow, "errors": errors,
            "decision": "HOLD" if blocked else "PROMOTE"}
