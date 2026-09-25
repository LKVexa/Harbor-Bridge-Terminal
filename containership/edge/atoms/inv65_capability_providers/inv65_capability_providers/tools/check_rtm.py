"""RTM consistency check (M31): 100 rows, every cited file exists, every cited
test function exists, 'verified-local' rows cite >=1 test, blocked/partial rows
name a blocker."""
from __future__ import annotations

import json
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]


def check(rtm: dict) -> list[str]:
    errs = []
    rows = rtm["rows"]
    if len(rows) != 100 or len({r["check_id"] for r in rows}) != 100:
        errs.append("RTM must have 100 unique rows")
    for r in rows:
        cid = r["check_id"]
        if r["status"] not in ("verified-local", "documented", "partial", "blocked"):
            errs.append(f"{cid}: bad status")
        if r["status"] == "verified-local" and not r["tests"]:
            errs.append(f"{cid}: verified-local without a test")
        if r["status"] in ("partial", "blocked") and not r["blocker"]:
            errs.append(f"{cid}: {r['status']} without a named blocker")
        for f in r["implementation"]:
            if not (PKG / f).exists():
                errs.append(f"{cid}: missing file {f}")
        for t in r["tests"]:
            f, _, sym = t.partition("::")
            p = PKG / f
            if not p.exists():
                errs.append(f"{cid}: missing test file {f}")
                continue
            src = p.read_text()
            for part in sym.split("::") if sym else []:
                if not re.search(rf"(def|class) {re.escape(part)}\b", src):
                    errs.append(f"{cid}: missing test symbol {part} in {f}")
    return errs


if __name__ == "__main__":
    e = check(json.loads((PKG / "traceability/INV65_RTM.json").read_text()))
    print("\n".join(e) or "RTM OK")
    sys.exit(1 if e else 0)
