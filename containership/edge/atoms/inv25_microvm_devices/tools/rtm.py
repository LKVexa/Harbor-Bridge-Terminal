"""Requirements traceability matrix builder/validator (item 8, C020).

    python tools/rtm.py build     # regenerate governance/RTM.json + governance/RTM.md
    python tools/rtm.py check     # validate; exit 1 on any linkage defect
"""
from __future__ import annotations

import datetime, json, pathlib, re, sys
from collections import Counter

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
from rtm_source import ROWS, T  # noqa: E402

STATUSES = {"PASS", "BLOCKED", "EXTERNAL", "NOT_APPLICABLE", "FAIL"}


def build() -> dict:
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    rows = []
    for it in items:
        status, artifacts, tests, reason = ROWS[it["ordinal"]]
        rows.append({"check_id": it["check_id"], "dimension": it["dimension"], "requirement": it["requirement"],
                     "ownership": "external" if status == "EXTERNAL" else "INV-25", "status": status,
                     "artifacts": artifacts, "tests": [T[t] for t in tests], "reason": reason,
                     "exemption_approver": None if status in ("PASS",) else "PENDING - see governance/waivers.json"})
    return {"schema": "INV25_RTM/1", "element": "INV-25", "generated": datetime.date.today().isoformat(),
            "rows": rows}


def check(rtm: dict) -> list[str]:
    errs = []
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    want = [i["check_id"] for i in items]
    got = [r["check_id"] for r in rtm["rows"]]
    for cid, n in Counter(got).items():
        if n > 1:
            errs.append(f"duplicate {cid}")
    for cid in set(got) - set(want):
        errs.append(f"unknown {cid}")
    for cid in set(want) - set(got):
        errs.append(f"missing {cid}")
    for r in rtm["rows"]:
        if r["status"] not in STATUSES:
            errs.append(f"{r['check_id']}: bad status")
        if r["status"] != "PASS" and not r["reason"]:
            errs.append(f"{r['check_id']}: non-PASS without reason")
        if r["status"] == "PASS" and not r["artifacts"]:
            errs.append(f"{r['check_id']}: PASS without artifact")
        for a in r["artifacts"]:
            path = a.split("::")[0]
            if not (PKG / path).exists():
                errs.append(f"{r['check_id']}: artifact path missing {path}")
            elif "::" in a and path.endswith(".py"):
                sym = a.split("::")[1].split(".")[0]
                if not re.search(rf"(def|class)\s+{re.escape(sym)}\b|^{re.escape(sym)}\s*(:[^=\n]*)?=", (PKG / path).read_text(), re.M):
                    errs.append(f"{r['check_id']}: symbol {sym} not in {path}")
        for t in r["tests"]:
            f, cls = t.split("::")
            if not (PKG / f).exists() or f"class {cls}" not in (PKG / f).read_text():
                errs.append(f"{r['check_id']}: test not discoverable {t}")
    return errs


def to_md(rtm: dict) -> str:
    lines = ["# INV-25 Requirements Traceability Matrix", "",
             "Generated from `tools/rtm_source.py` by `python tools/rtm.py build`. Do not edit by hand.", "",
             "| Check | Status | Artifacts | Tests | Reason |", "|---|---|---|---|---|"]
    for r in rtm["rows"]:
        lines.append(f"| {r['check_id']} | {r['status']} | {'<br>'.join(r['artifacts'])} | "
                     f"{'<br>'.join(t.split('::')[1] for t in r['tests'])} | {r['reason']} |")
    c = Counter(r["status"] for r in rtm["rows"])
    lines += ["", "**Totals:** " + ", ".join(f"{k} {v}" for k, v in sorted(c.items()))]
    by = {}
    for r in rtm["rows"]:
        by.setdefault(r["dimension"], Counter())[r["status"]] += 1
    lines += ["", "| Dimension | " + " | ".join(sorted(STATUSES)) + " |", "|---" * (len(STATUSES) + 1) + "|"]
    for d, cc in by.items():
        lines.append(f"| {d} | " + " | ".join(str(cc.get(s, 0)) for s in sorted(STATUSES)) + " |")
    return "\n".join(lines) + "\n"


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "check"
    path = PKG / "governance" / "RTM.json"
    if cmd == "build":
        rtm = build()
        path.write_text(json.dumps(rtm, indent=1) + "\n")
        (PKG / "governance" / "RTM.md").write_text(to_md(rtm))
    rtm = json.loads(path.read_text())
    errs = check(rtm)
    print(json.dumps({"rtm_rows": len(rtm["rows"]), "errors": errs,
                      "status_counts": Counter(r["status"] for r in rtm["rows"])}, indent=1))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
