#!/usr/bin/env python3
"""MC-039 - report overdue recurring reviews and expiring waivers. Exit 9 if anything is overdue."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    today = dt.date.fromisoformat(ap.parse_args().as_of)
    rv = json.loads((PKG / "REVIEWS.json").read_text())
    overdue = []
    for kind, days in rv["cadence_days"].items():
        dates = [dt.date.fromisoformat(r["date"]) for r in rv["reviews"] if r["kind"] == kind]
        last = max(dates) if dates else None
        if last is None or (today - last).days > days:
            overdue.append({"kind": kind, "last": last.isoformat() if last else None, "cadence_days": days})
    for w in json.loads((PKG / "WAIVERS.json").read_text())["waivers"]:
        exp = dt.date.fromisoformat(w["expires"])
        if exp < today:
            overdue.append({"kind": "waiver-expired", "id": w["id"], "expired": w["expires"]})
        elif (exp - today).days <= 7:
            overdue.append({"kind": "waiver-expiring", "id": w["id"], "expires": w["expires"]})
    print(json.dumps({"as_of": today.isoformat(), "overdue": overdue}, indent=1))
    return 9 if overdue else 0


if __name__ == "__main__":
    sys.exit(main())
