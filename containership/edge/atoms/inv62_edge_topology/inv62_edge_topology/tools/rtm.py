"""Requirements traceability (MC-011, MC-079).

Generates docs/SPEC.md and conformance/RTM.json from conformance/requirements.json,
conformance/mc_status.json and CHECKLIST.json, and verifies that every referenced
implementation symbol, test and evidence path exists.

    python inv62_edge_topology/tools/rtm.py            # regenerate
    python inv62_edge_topology/tools/rtm.py --check    # fail on drift or dangling references
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
GENERATED_PREFIXES = ("evidence/",)


def _symbol_exists(path: pathlib.Path, symbol: str) -> bool:
    text = path.read_text(encoding="utf-8")
    name = symbol.split(".")[-1]
    return re.search(rf"^\s*(def|class)\s+{re.escape(name)}\b|^\s*{re.escape(name)}\s*[:=]", text, re.M) is not None


def check_ref(ref: str) -> str | None:
    path, _, symbol = ref.partition("::")
    if path.startswith(GENERATED_PREFIXES):
        return None
    p = PKG / path
    if not p.exists():
        return f"missing path {path}"
    if symbol and p.is_file() and not _symbol_exists(p, symbol):
        return f"missing symbol {ref}"
    return None


def build() -> tuple[str, dict, list[str]]:
    reqdoc = json.loads((PKG / "conformance" / "requirements.json").read_text())
    reqs = reqdoc["requirements"]
    base = reqdoc.get("base_items", {})
    mcs = json.loads((PKG / "conformance" / "mc_status.json").read_text())["items"]
    checklist = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    problems: list[str] = []
    for r in reqs:
        for ref in r["implementation"] + r["verification"]:
            if (msg := check_ref(ref)):
                problems.append(f"{r['id']}: {msg}")
    for m in mcs:
        for ref in m["evidence"]:
            if (msg := check_ref(ref)):
                problems.append(f"{m['id']}: {msg}")
    for cid, refs in base.items():
        for ref in refs:
            if (msg := check_ref(ref)):
                problems.append(f"{cid}: {msg}")
    c_map: dict[str, dict[str, list[str]]] = {}
    for item in checklist:
        cid = item["check_id"].split("-")[-1]
        c_map[cid] = {"requirements": [], "mc": [], "base": base.get(cid, [])}
    for r in reqs:
        for c in r["checklist"]:
            c_map.setdefault(c, {"requirements": [], "mc": [], "base": []})["requirements"].append(r["id"])
    for m in mcs:
        for part in re.findall(r"C(\d{3})(?:-C(\d{3}))?", m["audit_mapping"]):
            lo = int(part[0])
            hi = int(part[1]) if part[1] else lo
            for n in range(lo, hi + 1):
                c_map.setdefault(f"C{n:03d}", {"requirements": [], "mc": [], "base": []})["mc"].append(m["id"])
    rtm = {
        "schema": "INV62_RTM/1",
        "version": (PKG / "VERSION").read_text().strip(),
        "requirements": {r["id"]: {"implementation": r["implementation"], "verification": r["verification"],
                                   "checklist": r["checklist"]} for r in reqs},
        "missing_components": {m["id"]: {"status": m["status"], "evidence": m["evidence"]} for m in mcs},
        "checklist_coverage": dict(sorted(c_map.items())),
        "uncovered_checklist_items": sorted(k for k, v in c_map.items() if not v["requirements"] and not v["mc"] and not v["base"]),
    }
    lines = ["# INV-62 production specification (generated — do not edit)", "",
             "Source: `conformance/requirements.json`; regenerate with `python inv62_edge_topology/tools/rtm.py`.",
             "Contexts: cloud, datacenter, near-edge, far-edge (`all` = every context). See NFR.md for the quality envelope.", "",
             "| ID | Context | Requirement (SHALL) | Implementation | Verification | Checklist |", "|---|---|---|---|---|---|"]
    for r in reqs:
        lines.append(f"| {r['id']} | {', '.join(r['contexts'])} | {r['statement']} | `{'`, `'.join(r['implementation'])}` | "
                     f"{'<br>'.join('`' + v + '`' for v in r['verification'])} | {', '.join(r['checklist'])} |")
    lines += ["", f"Checklist items with no requirement or MC mapping (covered by the base contract/README only): "
              f"{', '.join(rtm['uncovered_checklist_items']) or 'none'}.", ""]
    return "\n".join(lines), rtm, problems


def main(argv: list[str]) -> int:
    spec, rtm, problems = build()
    spec_path, rtm_path = PKG / "docs" / "SPEC.md", PKG / "conformance" / "RTM.json"
    rtm_text = json.dumps(rtm, indent=2, sort_keys=True) + "\n"
    if "--check" in argv:
        if not spec_path.exists() or spec_path.read_text() != spec:
            problems.append("docs/SPEC.md is stale")
        if not rtm_path.exists() or rtm_path.read_text() != rtm_text:
            problems.append("conformance/RTM.json is stale")
    else:
        spec_path.write_text(spec)
        rtm_path.write_text(rtm_text)
    for p in problems:
        print("RTM:", p)
    print(f"RTM: {len(rtm['requirements'])} requirements, {len(rtm['missing_components'])} MC items, "
          f"{len(rtm['uncovered_checklist_items'])} uncovered checklist items, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
