"""Validate security/waivers.json.  Exit 1 on malformed records; lists expired/unapproved.
A waiver counts toward a gate only when approval is a non-PENDING value and it is unexpired."""

import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQ = ("id", "check", "justification", "owner", "approval", "created", "expires", "risk")


def load(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    doc = json.loads((ROOT / "security" / "waivers.json").read_text())
    if doc.get("schema") != "INV23_WAIVERS/1":
        raise ValueError("bad waivers schema")
    out, seen = [], set()
    for w in doc["waivers"]:
        miss = [k for k in REQ if not isinstance(w.get(k), str) or not w[k].strip()]
        if miss or w["id"] in seen:
            raise ValueError(f"waiver {w.get('id')}: missing {miss} or duplicate")
        seen.add(w["id"])
        exp = dt.datetime.fromisoformat(w["expires"].replace("Z", "+00:00"))
        created = dt.datetime.fromisoformat(w["created"].replace("Z", "+00:00"))
        if exp <= created:
            raise ValueError(f"waiver {w['id']}: expires before created")
        w = dict(w, expired=exp <= now, approved=w["approval"].upper() != "PENDING")
        w["active"] = w["approved"] and not w["expired"]
        out.append(w)
    return out


if __name__ == "__main__":
    try:
        ws = load()
    except (ValueError, KeyError) as e:
        print(f"INVALID: {e}")
        sys.exit(1)
    for w in ws:
        print(f"{w['id']}  {'ACTIVE' if w['active'] else 'EXPIRED' if w['expired'] else 'UNAPPROVED'}  {w['check']}")
