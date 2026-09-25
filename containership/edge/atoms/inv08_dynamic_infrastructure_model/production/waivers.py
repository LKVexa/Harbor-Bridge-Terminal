"""Component 65 - exception / waiver / debt registry and release-gate enforcement (PK_DYN_WAIVER/1).

Waiver record::

  {"id": "WVR-NNNN", "component": int, "check": int (1..36), "kind": exception|waiver|debt|deprecation,
   "owner": str, "approver": str, "created": ts, "expires": ts, "review_by": ts,
   "compensating_controls": [str, ...], "residual_risk": low|medium|high, "rationale": str}

Rules: owner and approver present, not UNASSIGNED, and distinct; expires >
created and at most 90 days later (30 for high residual risk); review_by <=
expires; at least one compensating control.  P0 components' implementation /
verification checks (05-19) are UNWAIVABLE.  At gate time an expired waiver is
BLOCKING (as if absent) and waivers expiring within ``alert_days`` raise alerts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DAY = 86400.0
MAX_DAYS = {"low": 90, "medium": 90, "high": 30}
KINDS = {"exception", "waiver", "debt", "deprecation"}
UNWAIVABLE_P0_CHECKS = set(range(5, 20))
REGISTRY = Path(__file__).resolve().parent / "waivers.json"


def _person(v) -> bool:
    return isinstance(v, str) and bool(v.strip()) and not v.startswith("UNASSIGNED")


def validate(w: dict, *, priorities: dict[int, str]) -> list[str]:
    p = []
    if not re.fullmatch(r"WVR-\d{4}", str(w.get("id"))):
        p.append("id must be WVR-NNNN")
    if w.get("kind") not in KINDS:
        p.append("bad kind")
    if not _person(w.get("owner")):
        p.append("named owner required")
    if not _person(w.get("approver")):
        p.append("named approver required")
    if w.get("owner") and w.get("owner") == w.get("approver"):
        p.append("owner and approver must differ")
    risk = w.get("residual_risk")
    if risk not in MAX_DAYS:
        p.append("residual_risk must be low|medium|high")
    c, e, r = w.get("created"), w.get("expires"), w.get("review_by")
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (c, e, r)):
        p.append("created/expires/review_by must be numbers")
    else:
        if e <= c:
            p.append("expires must be after created")
        elif risk in MAX_DAYS and (e - c) > MAX_DAYS[risk] * DAY:
            p.append(f"expiry exceeds {MAX_DAYS[risk]} days for {risk} risk")
        if r > e:
            p.append("review_by after expiry")
    if not w.get("compensating_controls"):
        p.append("compensating controls required")
    chk = w.get("check")
    if not isinstance(chk, int) or not 1 <= chk <= 36:
        p.append("check must be 1..36")
    elif priorities.get(w.get("component")) == "P0" and chk in UNWAIVABLE_P0_CHECKS:
        p.append(f"P0 implementation/verification check {chk:02d} is unwaivable")
    return p


def gate(open_items: list[tuple[int, int]], waivers: list[dict], *, now: float,
         priorities: dict[int, str], alert_days: float = 14) -> dict:
    """open_items: (component, check) pairs that are not complete."""
    blocking, waived, alerts, invalid = [], [], [], []
    by_item: dict = {}
    for w in waivers:
        errs = validate(w, priorities=priorities)
        if errs:
            invalid.append({"id": w.get("id"), "errors": errs})
            continue
        if w["expires"] <= now:
            invalid.append({"id": w["id"], "errors": ["expired"]})
            continue
        if w["expires"] - now <= alert_days * DAY or w["review_by"] <= now:
            alerts.append(w["id"])
        by_item.setdefault((w["component"], w["check"]), w)
    for item in open_items:
        if item in by_item:
            waived.append({"item": list(item), "waiver": by_item[item]["id"]})
        else:
            blocking.append(list(item))
    return {"pass": not blocking, "blocking": blocking, "waived": waived, "alerts": alerts, "invalid": invalid}


def load(path: Path = REGISTRY) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["waivers"]
