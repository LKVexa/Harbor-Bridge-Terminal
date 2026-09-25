"""Missing-component registry for the applied checklist (MC-001..MC-094, 1,883 checkboxes).

    python -B -m inv27_unikernel_execution.tools.mc_status [--check]

Validates ops/MC_STATUS_SOURCE.json (every MC present, refs resolve, ``verified_local`` needs >=1
implementation and >=1 test ref and no blockers; other statuses name a waiver from ops/WAIVERS.json),
then classifies every checkbox of the applied checklist and writes evidence/MC_STATUS.json + ops/MC_STATUS.md.

Checkbox rule (mechanical, stated so it can be audited):
  1. A checkbox whose text needs a human, an environment or an approval (EXTERNAL patterns) is
     ``blocked`` on the MC's first waiver, or W-APPROVALS when the MC has none.
  2. The per-MC "production-gate result showing MC-xxx PASS" checkbox is ``blocked`` on W-APPROVALS for
     every MC: the gate never reports PASS without independent review.
  3. Otherwise the checkbox inherits the MC status (verified_local -> done_local, partial -> partial,
     blocked -> blocked).
No checkbox is ever marked done by this tool beyond "done_local"; nothing here is independently reviewed.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter

from ._refs import ROOT, load, resolve

CHECKLIST = "docs/INV27_v4.2.0_Missing_Component_Implementation_Checklist.md"
EXTERNAL = re.compile(r"(?i)(review(ed)? by the accountable owner|reviewer\(s\)|\bapprov(ed|al)\b|sign-?off|"
                      r"owned, reviewed|security/architecture/operations review|^review |^re-review|name a single accountable|"
                      r"protected-branch|multi-party|deployed and exercised|non-production environment|reference hardware|"
                      r"real (unikernel|supported|hypervisor|vmm)|\bfleet\b|on-call|pager|drills?\b|"
                      r"merged with code/document review|hosted ci|hardware-backed|production (traffic|deployment|fleet)|"
                      r"per major release|periodic(ally)? review|power/thermal|iommu|\bkms\b|\bhsm\b|transparency log)")
GATE_PASS = re.compile(r"production-gate result showing `?MC-\d{3}`? PASS")
MAP = {"verified_local": "done_local", "partial": "partial", "blocked": "blocked"}


def parse_checklist() -> dict:
    text = (ROOT / CHECKLIST).read_text(encoding="utf-8")
    out = {}
    for block in re.split(r"\n(?=## MC-\d{3})", text)[1:]:
        mc = re.match(r"## (MC-\d{3})", block).group(1)
        rows, section = [], "header"
        for line in block.splitlines():
            if line.startswith("### "):
                section = line[4:].strip()
            m = re.match(r"^- \[ \] (.*)$", line)
            if m:
                rows.append((section, m.group(1).strip()))
        out[mc] = rows
    return out


def validate(src: dict, waivers: dict) -> list[str]:
    errs = []
    wids = {w["id"] for w in waivers["entries"]}
    comps = src["components"]
    want = {f"MC-{i:03d}" for i in range(1, 95)}
    if set(comps) != want:
        errs.append(f"MC set mismatch missing={sorted(want - set(comps))} extra={sorted(set(comps) - want)}")
    for k, c in comps.items():
        if c["status"] not in src["status_values"]:
            errs.append(f"{k}: unknown status")
        for r in c["implementation"] + c["tests"]:
            why = resolve(r)
            if why:
                errs.append(f"{k}: {why}")
        if c["status"] == "verified_local" and (not c["implementation"] or not c["tests"] or c["blockers"]):
            errs.append(f"{k}: verified_local needs implementation + tests and no blockers")
        if c["status"] != "verified_local" and not c["blockers"]:
            errs.append(f"{k}: {c['status']} names no waiver")
        for b in c["blockers"]:
            if b not in wids:
                errs.append(f"{k}: blocker {b} not in ops/WAIVERS.json")
    return errs


def classify(src: dict, boxes: dict) -> list[dict]:
    rows = []
    for mc, items in boxes.items():
        if mc == "_GLOBAL":
            continue
        c = src["components"][mc]
        for i, (section, text) in enumerate(items, 1):
            if GATE_PASS.search(text):
                st, why = "blocked", "W-APPROVALS"
            elif EXTERNAL.search(text):
                st, why = "blocked", (c["blockers"] or ["W-APPROVALS"])[0]
            else:
                st, why = MAP[c["status"]], (c["blockers"][0] if c["blockers"] and c["status"] != "verified_local" else None)
            rows.append({"id": f"{mc}.{i:02d}", "mc": mc, "section": section, "text": text, "status": st, "waiver": why})
    for i, (section, text) in enumerate(boxes.get("_GLOBAL", []), 1):
        rows.append({"id": f"GLOBAL.{i:02d}", "mc": None, "section": section, "text": text, "status": "blocked",
                     "waiver": "W-APPROVALS"})
    return rows


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    src, waivers = load("ops/MC_STATUS_SOURCE.json"), load("ops/WAIVERS.json")
    errs = validate(src, waivers)
    boxes = parse_checklist()
    text = (ROOT / CHECKLIST).read_text(encoding="utf-8")
    head = text.split("\n## MC-001")[0]
    tail = text.split("# Program-level closure sequence")[1]
    boxes["_GLOBAL"] = [("Global acceptance gates", t) for t in re.findall(r"^- \[ \] (.*)$", head, re.M)] + \
                       [("Release exit criteria", t) for t in re.findall(r"^- \[ \] (.*)$", tail, re.M)]
    rows = classify(src, boxes)
    comps = src["components"]
    summary = {"components": dict(Counter(c["status"] for c in comps.values())),
               "by_priority": {p: dict(Counter(c["status"] for c in comps.values() if c["priority"] == p)) for p in ("P0", "P1", "P2")},
               "checkboxes": dict(Counter(r["status"] for r in rows)), "checkbox_total": len(rows),
               "waivers_cited": dict(Counter(r["waiver"] for r in rows if r["waiver"]))}
    doc = {"schema": "PK_MC_STATUS/1", "component": "INV-27", "version": src["version"], "rule": __doc__.split("Checkbox rule")[1].strip(),
           "summary": summary, "components": comps, "checkboxes": rows}
    md = [f"# INV-27 missing-component status — v{src['version']} (generated by tools/mc_status.py)", "",
          f"Components: {summary['components']}  ", f"By priority: {summary['by_priority']}  ",
          f"Checkboxes ({len(rows)}): {summary['checkboxes']}", "",
          "| MC | P | title | status | waivers | note |", "|---|---|---|---|---|---|"]
    for k, c in comps.items():
        md.append(f"| {k} | {c['priority']} | {c['title']} | **{c['status']}** | {', '.join(c['blockers'])} | {c['note']} |")
    if "--check" not in argv:
        (ROOT / "evidence" / "MC_STATUS.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        (ROOT / "ops" / "MC_STATUS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for e in errs:
        print("FAIL", e)
    print("MC_STATUS", "PASS" if not errs else "FAIL", json.dumps(summary["components"]), json.dumps(summary["checkboxes"]))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
