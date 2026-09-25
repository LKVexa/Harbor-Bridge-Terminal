"""Requirements traceability matrix (MC-007) generated from requirements + CI results.

    python tools/rtm.py --ci release/ci_report.json [--check-only]

Writes ``release/rtm.json`` (machine), ``docs/COVERAGE.md`` (human, generated — never hand-edited)
and a per-release snapshot under ``release/rtm-history/``.  Exit 1 when any SHALL row lacks an
implementation reference or verification reference, references a missing file, references a test
that did not pass (skips are not passes), when a waiver has expired, or when the C001-C100 coverage
view is not exactly the 100 checklist IDs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip()
LANE_REFS = {"tools.perf_gate": "perf-gate", "tools.bench": "perf-gate", "tools.bench.soak": "perf-gate",
             "tools.rtm": "rtm", "tools.release": "release-build", "tools.release.package": "package",
             "tools.release.waivers": "waivers", "tools.release.gate": "exit-gate", "tools.review": "review",
             "tools.ci.observability": "observability", "tools.ci.docs": "docs"}


def sha_path(rel: str) -> str | None:
    p = ROOT / rel
    if p.is_file():
        return hashlib.sha256(p.read_bytes()).hexdigest()
    if p.is_dir():
        h = hashlib.sha256()
        for f in sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts):
            h.update(f.relative_to(ROOT).as_posix().encode() + b"\0" + f.read_bytes())
        return h.hexdigest()
    return None


def test_status(ref: str, tests: dict, lanes: dict) -> tuple[str, list[str]]:
    if ref.startswith("tools."):
        lane = LANE_REFS.get(ref)
        st = (lanes.get(lane) or {}).get("status") if lane else None
        return ("pass" if st == "PASS" else (st or "missing").lower()), [f"lane:{lane}"]
    hits = {k: v for k, v in tests.items() if k == ref or k.startswith(ref + ".")}
    if not hits:
        return "missing", []
    outs = {v["outcome"] for v in hits.values()}
    return ("pass" if outs == {"pass"} else "fail" if outs & {"fail", "error"} else "skip"), sorted(hits)[:50]


def build(ci: dict) -> tuple[dict, list[str]]:
    reqs = json.loads((ROOT / "requirements" / "requirements.json").read_text())["requirements"]
    waivers = json.loads((ROOT / "release" / "waivers.json").read_text())["waivers"]
    tests = ci.get("tests", {})
    lanes = ci.get("lanes", {})
    today = dt.date.today().isoformat()
    problems: list[str] = []
    rows = []
    for w in waivers:
        if w["expires"] < today:
            problems.append(f"{w['id']}: waiver expired {w['expires']}")
    for r in reqs:
        cid = r["source"].split("-")[-1] if r["source"].startswith("INV-66-") else None
        arts = r["acceptance"]["artifacts_exist"]
        art_rows = [{"path": a, "sha256": sha_path(a)} for a in arts]
        for a in art_rows:
            if a["sha256"] is None:
                problems.append(f"{r['id']}: missing artifact {a['path']}")
        tref = []
        for t in r["acceptance"]["tests_pass"]:
            st, ids = test_status(t, tests, lanes)
            tref.append({"ref": t, "status": st, "matched": len(ids)})
            if st != "pass" and not (st == "not_run" and r["engineering_status"] != "ENGINEERED"):
                problems.append(f"{r['id']}: verification {t} is {st}")
        if not arts:
            problems.append(f"{r['id']}: no implementation reference")
        if not tref and r["engineering_status"] == "ENGINEERED" and r["evidence_type"] == "automated":
            problems.append(f"{r['id']}: automated requirement without verification reference")
        wids = [w["id"] for w in waivers if cid and cid in w["controls"]]
        verified = all(t["status"] == "pass" for t in tref) and all(a["sha256"] for a in art_rows)
        rows.append({"requirement": r["id"], "control": cid, "statement": r["statement"], "owner_role": r["owner_role"],
                     "artifacts": art_rows, "verification": tref, "waivers": wids,
                     "engineering_status": r["engineering_status"], "gap": r["note"],
                     "evidence_status": "VERIFIED_LOCAL" if verified and tref else ("DOCUMENT_ONLY" if not tref else "NOT_VERIFIED"),
                     "independent_review": "MISSING", "release": VERSION,
                     "last_verified": ci.get("finished")})
    ids = [row["control"] for row in rows if row["control"]]
    expect = [f"C{i:03d}" for i in range(1, 101)]
    if sorted(ids) != expect:
        problems.append(f"control coverage mismatch: {sorted(set(expect) - set(ids))} missing / "
                        f"{sorted(set(ids) - set(expect))} unknown / duplicates={len(ids) - len(set(ids))}")
    mc_links = {}
    text = (ROOT / "MISSING_COMPONENTS.md").read_text()
    for m in re.finditer(r"\*\*(MC-\d{3}) — .*?\*\*.*?\*\((C[^)]*)\)\*", text):
        ctrl = []
        for part in m.group(2).split(","):
            part = part.strip()
            if "-" in part and part.startswith("C"):
                a, b = part.split("-")
                ctrl += [f"C{i:03d}" for i in range(int(a[1:]), int(b[1:]) + 1)]
            elif part.startswith("C"):
                ctrl.append(part)
        mc_links[m.group(1)] = ctrl
    rtm = {"schema": "PK_ECP_RTM/1", "release": VERSION, "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
           "ci_report_sha256": hashlib.sha256(json.dumps(ci, sort_keys=True).encode()).hexdigest(),
           "rows": rows, "mc_to_controls": mc_links, "problems": problems}
    return rtm, problems


def coverage_md(rtm: dict) -> str:
    rows = rtm["rows"]
    by = {}
    for r in rows:
        by[r["engineering_status"]] = by.get(r["engineering_status"], 0) + 1
    ev = {}
    for r in rows:
        ev[r["evidence_status"]] = ev.get(r["evidence_status"], 0) + 1
    out = [f"# Requirements coverage — INV-66 {rtm['release']}", "",
           "Generated by `tools/rtm.py` from `release/rtm.json`. Do not edit.", "",
           f"Engineering status: {', '.join(f'{k} {v}' for k, v in sorted(by.items()))}  ",
           f"Evidence: {', '.join(f'{k} {v}' for k, v in sorted(ev.items()))}  ",
           f"Independent review: **MISSING for all {len(rows)}** (no reviewer recorded)  ",
           f"RTM problems: {len(rtm['problems'])}", "",
           "| Req | Status | Evidence | Tests | Waivers | Gap |", "|---|---|---|---|---|---|"]
    for r in rows:
        t = ", ".join(f"{x['ref'].split('.')[-1]}={x['status']}" for x in r["verification"])[:120]
        out.append(f"| {r['requirement']} | {r['engineering_status']} | {r['evidence_status']} | {t} | "
                   f"{','.join(r['waivers'])} | {r['gap']} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", default=str(ROOT / "release" / "ci_report.json"))
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args(argv)
    ci = json.loads(Path(a.ci).read_text()) if Path(a.ci).exists() else {}
    rtm, problems = build(ci)
    if not a.check_only:
        (ROOT / "release" / "rtm.json").write_text(json.dumps(rtm, indent=1) + "\n")
        hist = ROOT / "release" / "rtm-history"
        hist.mkdir(exist_ok=True)
        (hist / f"rtm-{VERSION}.json").write_text(json.dumps(rtm, indent=1) + "\n")
        (ROOT / "docs" / "COVERAGE.md").write_text(coverage_md(rtm))
    print(f"rtm rows={len(rtm['rows'])} problems={len(problems)}")
    for p in problems[:30]:
        print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
