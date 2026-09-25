"""Item 61: produce a dated review-evidence record (waivers, baseline age, deps, open blockers).

Usage: python3 -B tools/recurring_review.py [--ledger audit.jsonl --seal-key-file K] [--baseline baseline.json]
Scheduling it (cron / CI schedule) and assigning a reviewer are owner decisions.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(PKG))
sys.dont_write_bytecode = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger")
    ap.add_argument("--seal-key-file")
    ap.add_argument("--baseline")
    a = ap.parse_args()
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    rec = {"schema": "INV03_REVIEW/1", "at": now, "reviewer": None, "sections": {}}
    with open(os.path.join(PKG, "CHECKLIST_STATUS.json")) as fh:
        st = json.load(fh)
    rec["sections"]["open_blockers"] = [{"n": i["n"], "status": i["status"]} for i in st["items"] if not i["complete"]]
    with open(os.path.join(PKG, "pyproject.toml")) as fh:
        rec["sections"]["declared_runtime_dependencies"] = [ln.strip() for ln in fh if ln.startswith("dependencies")]
    if a.ledger and a.seal_key_file:
        from inv03_container_hardening.hardening.core import AuditLedger
        with open(a.seal_key_file, "rb") as fh:
            led = AuditLedger(a.ledger, fh.read().strip())
        ok, msg = led.verify()
        rec["sections"]["audit_chain"] = {"ok": ok, "detail": msg, "head": led.head}
        waivers = {}
        for e in led.events():
            if e["kind"].startswith("exception."):
                waivers.setdefault(e["data"]["id"], []).append(e["kind"])
        rec["sections"]["waivers"] = waivers
    if a.baseline:
        with open(a.baseline) as fh:
            b = json.load(fh)
        rec["sections"]["baseline"] = {"epoch": b.get("epoch"), "history_len": len(b.get("history", []))}
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
