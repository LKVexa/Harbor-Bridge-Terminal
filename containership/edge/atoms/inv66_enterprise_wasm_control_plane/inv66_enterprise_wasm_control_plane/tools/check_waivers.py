"""Waiver register lane (MC-067): schema, no indefinite waivers, expiry <= policy max, links to known controls.
PASS means the register is well-formed; approvals are evaluated by the exit gate, not here."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
reg = json.loads((ROOT / "release/waivers.json").read_text())
ids = {i["check_id"].split("-")[-1] for i in json.loads((ROOT / "CHECKLIST.json").read_text())["items"]}
bad = []
seen = set()
for w in reg["waivers"]:
    for k in ("id", "controls", "type", "rationale", "compensating_controls", "risk", "created", "expires", "state"):
        if not w.get(k):
            bad.append(f"{w.get('id')}: missing {k}")
    if w["id"] in seen:
        bad.append(f"duplicate {w['id']}")
    seen.add(w["id"])
    c, e = dt.date.fromisoformat(w["created"]), dt.date.fromisoformat(w["expires"])
    if (e - c).days > reg["policy"]["max_days"]:
        bad.append(f"{w['id']}: exceeds max duration")
    for ctl in w["controls"]:
        if ctl.startswith("C") and ctl not in ids:
            bad.append(f"{w['id']}: unknown control {ctl}")
today = dt.date.today()
expired = [w["id"] for w in reg["waivers"] if dt.date.fromisoformat(w["expires"]) < today]
soon = [w["id"] for w in reg["waivers"] if 0 <= (dt.date.fromisoformat(w["expires"]) - today).days <= reg["policy"]["notify_days_before_expiry"]]
print(json.dumps({"waivers": len(reg["waivers"]), "problems": bad, "expired": expired, "expiring_soon": soon,
                  "pending_approval": [w["id"] for w in reg["waivers"] if not w["approver"]]}))
sys.exit(1 if bad or expired else 0)
