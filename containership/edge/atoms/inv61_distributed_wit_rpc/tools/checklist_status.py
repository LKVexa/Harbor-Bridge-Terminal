"""Checklist status register for the M01-M32 completion checklist.

    python tools/checklist_status.py --build <checklist.md> <status.json>...   # (re)build the register
    python tools/checklist_status.py --check                                  # CI: consistency gate

--check fails when: any checklist item lacks a status; a status is not in the allowed
set; a LOCALLY_VERIFIED item cites no test id or cites one that no longer exists; or a
test id cited in docs/REQUIREMENTS.md no longer exists.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REG = ROOT / "CHECKLIST_STATUS.json"
MD = ROOT / "CHECKLIST_STATUS.md"
STATUSES = ("LOCALLY_VERIFIED", "DOCUMENTED", "PARTIAL", "OPEN", "BLOCKED")
TEST_ID = re.compile(r"\b(test_[a-z0-9_]+)\.([A-Z][A-Za-z0-9]+)\.(test_[a-z0-9_]+)\b")
BARE_TEST = re.compile(r"\b(test_[a-z0-9_]+)\b")


def parse_checklist(path: pathlib.Path) -> list[dict]:
    items, comp, title, sub, n = [], None, None, None, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## M"):
            comp, title = line[3:6], line[9:].strip()
            sub, n = None, 0
        elif line.startswith("### "):
            sub = line[4:].strip()
        elif line.startswith("- [ ] ") and comp:
            n += 1
            items.append({"id": f"{comp}-{n:03d}", "component": comp, "component_title": title,
                          "section": sub, "text": line[6:].strip()})
    return items


def known_tests() -> set[str]:
    sys.path.insert(0, str(ROOT))
    ids = set()

    def walk(s):
        for t in s:
            if isinstance(t, unittest.TestSuite):
                walk(t)
            else:
                ids.add(t.id())
    walk(unittest.defaultTestLoader.discover(str(ROOT / "tests")))
    return ids


def build(checklist: str, status_files: list[str]) -> None:
    items = parse_checklist(pathlib.Path(checklist))
    st = {}
    for f in status_files:
        for rec in json.loads(pathlib.Path(f).read_text()):
            st[rec["id"]] = rec
    missing = [i["id"] for i in items if i["id"] not in st]
    if missing:
        sys.exit(f"no status for {len(missing)} items, e.g. {missing[:5]}")
    for i in items:
        rec = st[i["id"]]
        i["status"], i["evidence"] = rec["status"], rec["evidence"]
        for k in ("assessed", "reassessed_after_fixes", "prior_status"):
            if k in rec:
                i[k] = rec[k]
    counts = collections.Counter(i["status"] for i in items)
    per = collections.defaultdict(collections.Counter)
    for i in items:
        per[i["component"]][i["status"]] += 1
    reg = {"schema": "INV61_CHECKLIST_STATUS/1", "package_version": (ROOT / "VERSION").read_text().strip(),
           "statuses": list(STATUSES), "totals": dict(counts),
           "per_component": {k: dict(v) for k, v in sorted(per.items())},
           "production_authorised": False, "items": items}
    REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_md(reg)
    print(f"{len(items)} items -> {REG.name}: {dict(counts)}")


def write_md(reg: dict) -> None:
    mark = {"LOCALLY_VERIFIED": "x", "DOCUMENTED": "~", "PARTIAL": "~", "OPEN": " ", "BLOCKED": "!"}
    out = ["# INV-61 v4.3.0 — completion checklist status", "",
           "`[x]` locally verified · `[~]` documented or partial · `[ ]` open · `[!]` blocked. "
           "A box is only `[x]` when code and an executed test in this build back it. "
           "Production use is **not** authorised.", "",
           "| Component | " + " | ".join(STATUSES) + " |", "|---|" + "---|" * len(STATUSES)]
    titles = {i["component"]: i["component_title"] for i in reg["items"]}
    for comp, c in reg["per_component"].items():
        out.append(f"| {comp} {titles[comp]} | " + " | ".join(str(c.get(s, 0)) for s in STATUSES) + " |")
    tot = reg["totals"]
    out.append("| **Total** | " + " | ".join(f"**{tot.get(s, 0)}**" for s in STATUSES) + " |")
    comp = sec = None
    for i in reg["items"]:
        if i["component"] != comp:
            comp, sec = i["component"], None
            out += ["", f"## {comp} — {i['component_title']}"]
        if i["section"] != sec:
            sec = i["section"]
            out += ["", f"### {sec}"]
        out.append(f"- [{mark[i['status']]}] **{i['id']}** {i['text']}  \n  _{i['status']}_ — {i['evidence']}")
    MD.write_text("\n".join(out) + "\n", encoding="utf-8")


def check() -> int:
    errors = []
    reg = json.loads(REG.read_text(encoding="utf-8"))
    tests = known_tests()
    short = {".".join(t.split(".")[-3:]) for t in tests}
    names = {t.rsplit(".", 1)[1] for t in tests}
    for i in reg["items"]:
        if i["status"] not in STATUSES:
            errors.append(f"{i['id']}: bad status {i['status']}")
        if i["status"] == "LOCALLY_VERIFIED":
            cited = [m.group(0) for m in TEST_ID.finditer(i["evidence"])]
            bare = [b for b in BARE_TEST.findall(i["evidence"]) if b in names]
            evidence_file = re.search(r"evidence/[a-z_.]+json", i["evidence"])
            if not cited and not bare and not evidence_file:
                errors.append(f"{i['id']}: LOCALLY_VERIFIED without a test id or evidence file")
            for c in cited:
                if c not in short:
                    errors.append(f"{i['id']}: cites missing test {c}")
    req = (ROOT / "docs" / "REQUIREMENTS.md").read_text(encoding="utf-8")
    for m in TEST_ID.finditer(req):
        if m.group(0) not in short:
            errors.append(f"REQUIREMENTS.md cites missing test {m.group(0)}")
    for e in errors:
        print("CHECK FAIL:", e)
    print(f"checked {len(reg['items'])} items, {len(tests)} tests: {'OK' if not errors else f'{len(errors)} error(s)'}")
    return 1 if errors else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", nargs="+", metavar=("CHECKLIST", "STATUS"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.build:
        build(a.build[0], a.build[1:])
    if a.check:
        sys.exit(check())
