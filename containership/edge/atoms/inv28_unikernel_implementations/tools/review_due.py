"""Recurring review automation (MC-074): repository reviews (ops/REVIEWS.json) plus per-toolchain security
review freshness for a register snapshot.

    python -B -m inv28_unikernel_implementations.tools.review_due [--today YYYY-MM-DD] [--fail-on-overdue]
        [--snapshot rev-000042.json --registry-key-hex HEX]   # a production snapshot, verified before use
Without --snapshot the fixture world is used so the lane is always exercisable.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import warnings

from ._common import EVIDENCE, ROOT, ensure_path, read_json, write_json


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--fail-on-overdue", action="store_true")
    ap.add_argument("--snapshot")
    ap.add_argument("--registry-key-hex")
    a = ap.parse_args(argv)
    ensure_path()
    warnings.simplefilter("ignore", DeprecationWarning)
    from inv28_unikernel_implementations import fixtures as F
    from inv28_unikernel_implementations.registry import Registry
    from inv28_unikernel_implementations.service import Inv28Service
    from inv28_unikernel_implementations.trust import KeyRing
    today = dt.date.fromisoformat(a.today)
    now = dt.datetime.combine(today, dt.time(12), tzinfo=dt.timezone.utc)
    repo = []
    for rv in read_json(ROOT / "ops" / "REVIEWS.json")["reviews"]:
        due = (dt.date.fromisoformat(rv["last_done"]) + dt.timedelta(days=rv["interval_days"])) if rv["last_done"] else None
        repo.append({"id": rv["id"], "owner": rv["owner"], "due": due.isoformat() if due else None,
                     "overdue": due is None or due < today})
    if a.snapshot:
        ring = KeyRing()
        ring.add("registry", "operator", bytes.fromhex(a.registry_key_hex))
        reg = Registry(ring)
        reg.load(json.loads(open(a.snapshot, encoding="utf-8").read()))
        source = a.snapshot
    else:
        reg = F.world()["registry"]
        source = "fixture world"
    svc = Inv28Service(registry=reg, selector=type("S", (), {"policy": None, "metrics": None, "logger": None,
                                                              "audit": None, "certifications": None,
                                                              "advisories": None, "rollout": None})(),
                       clock=lambda: now)
    toolchains = svc.reviews_due(now)
    doc = {"schema": "PK_REVIEW_DUE/1", "today": a.today, "repository_reviews": repo, "toolchain_source": source,
           "toolchain_reviews_due": toolchains,
           "overdue": [r["id"] for r in repo if r["overdue"]] + [t["toolchain"] for t in toolchains if t["overdue"]]}
    write_json(EVIDENCE / "REVIEW_DUE.json", doc)
    for x in doc["overdue"]:
        print("OVERDUE", x)
    print("REVIEWS", "OVERDUE" if doc["overdue"] else "OK")
    return 1 if (a.fail_on_overdue and doc["overdue"]) else 0


if __name__ == "__main__":
    sys.exit(main())
