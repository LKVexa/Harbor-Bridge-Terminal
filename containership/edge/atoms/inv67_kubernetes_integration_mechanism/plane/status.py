"""Status writer and condition model (item 13).

Conditions follow the Kubernetes convention (type/status/reason/message/
lastTransitionTime/observedGeneration). ``lastTransitionTime`` only changes
when ``status`` flips, so a hot reconcile loop does not churn the object.
Messages are bounded and never contain secret material.
"""
from __future__ import annotations

import time

CONDITION_TYPES = ("Accepted", "Ready", "Degraded", "Progressing")
_MAX_MSG = 512


def set_condition(conds: list[dict], type_: str, status: bool | None, reason: str, message: str,
                  generation: int, now=None) -> list[dict]:
    if type_ not in CONDITION_TYPES:
        raise ValueError(f"unknown condition {type_}")
    st = {True: "True", False: "False", None: "Unknown"}[status]
    now = now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out, found = [], False
    for c in conds:
        if c["type"] == type_:
            found = True
            ltt = c["lastTransitionTime"] if c["status"] == st else now
            out.append({"type": type_, "status": st, "reason": reason, "message": message[:_MAX_MSG],
                        "lastTransitionTime": ltt, "observedGeneration": generation})
        else:
            out.append(c)
    if not found:
        out.append({"type": type_, "status": st, "reason": reason, "message": message[:_MAX_MSG],
                    "lastTransitionTime": now, "observedGeneration": generation})
    return out


def get_condition(conds: list[dict], type_: str) -> dict | None:
    return next((c for c in conds if c["type"] == type_), None)
