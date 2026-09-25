"""M15 - C001-C100 x M01-M86 traceability (machine + human), from CHECKLIST.json,
tools/m_registry.py, release/TEST_RESULTS.json and release/CONFORMANCE.json.
Fails (exit 1) on orphan requirements, stale file refs, unknown test ids, duplicates."""
import json, pathlib, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools")); sys.dont_write_bytecode = True
import m_registry as R
rel = PKG / "release"
checklist = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
tests = json.loads((rel / "TEST_RESULTS.json").read_text()) if (rel / "TEST_RESULTS.json").exists() else {"tests": {}}
conf = json.loads((rel / "CONFORMANCE.json").read_text()) if (rel / "CONFORMANCE.json").exists() else {"findings": {}}
problems = []
DOWNSTREAM = {"release/TRACEABILITY.json", "release/TRACEABILITY.md", "release/ACCEPTANCE.json", "release/EXIT_GATE.json"}
classes = {}
for tid, outcome in tests["tests"].items():
    mod, cls, _ = tid.split(".", 2)
    classes.setdefault(f"{mod}.{cls}", []).append(outcome)
m_rows = {}
for mid, (status, arts, tcls, blocker, waiver) in R.M.items():
    for a in arts:
        if a in DOWNSTREAM:
            continue          # produced later in the same CI run
        if not (PKG / a).exists():
            problems.append(f"{mid}: missing artifact {a}")
    tstat = {}
    for c in tcls:
        if c not in classes:
            problems.append(f"{mid}: unknown/unrun test class {c}")
            tstat[c] = "not_run"
        else:
            o = classes[c]
            tstat[c] = "failed" if any(x in ("failure", "error") for x in o) else ("skipped" if all(x == "skipped" for x in o) else "passed")
    effective = status
    if status == "LOCALLY_VERIFIED" and (not tcls or any(v != "passed" for v in tstat.values())):
        effective = "PARTIAL"; problems.append(f"{mid}: claimed LOCALLY_VERIFIED but tests {tstat}")
    m_rows[mid] = {"declared": status, "effective": effective, "artifacts": arts, "tests": tstat, "blocker": blocker, "waiver": waiver,
                   "cites": R.CITES.get(mid, [])}
c_rows = {}
ids = [i["check_id"] for i in checklist]
if len(ids) != len(set(ids)):
    problems.append("duplicate check ids")
for it in checklist:
    cid = it["check_id"].split("-")[-1]
    ms = [m for m, r in m_rows.items() if cid in r["cites"]]
    f = conf["findings"].get(it["check_id"], {})
    c_rows[it["check_id"]] = {"dimension": it["dimension"], "requirement": it["requirement"], "m_items": ms,
                              "pk_core_status": f.get("status", "not_run"), "pk_core_artifacts": f.get("artifacts", []),
                              "production_status": ("BLOCKED" if any(m_rows[m]["effective"] == "BLOCKED" for m in ms) else
                                                    "PARTIAL" if any(m_rows[m]["effective"] == "PARTIAL" for m in ms) else
                                                    "LOCALLY_VERIFIED" if ms else "CONTRACT_ONLY")}
    if not ms and f.get("status") not in ("satisfied",):
        problems.append(f"{it['check_id']}: orphan (no M item and no satisfied pk_core finding)")
out = {"schema": "inv60.traceability/1", "m_items": m_rows, "requirements": c_rows, "problems": problems,
       "summary": {"m_effective": {s: sum(1 for r in m_rows.values() if r["effective"] == s) for s in ("LOCALLY_VERIFIED", "PARTIAL", "BLOCKED")},
                   "c_production": {s: sum(1 for r in c_rows.values() if r["production_status"] == s) for s in ("LOCALLY_VERIFIED", "PARTIAL", "BLOCKED", "CONTRACT_ONLY")},
                   "c_pk_core_satisfied": sum(1 for r in c_rows.values() if r["pk_core_status"] == "satisfied")}}
(rel / "TRACEABILITY.json").write_text(json.dumps(out, indent=1))
md = ["# Traceability (M15) — generated", "", f"Summary: {json.dumps(out['summary'])}", "",
      "## M-items", "| M | declared | effective | tests | blocker / waiver |", "|---|---|---|---|---|"]
for m, r in m_rows.items():
    md.append(f"| {m} | {r['declared']} | {r['effective']} | {', '.join(f'{k}:{v}' for k, v in r['tests'].items()) or '—'} | {r['blocker'] or ''} {('('+r['waiver']+')') if r['waiver'] else ''} |")
md += ["", "## C001–C100", "| check | dimension | pk_core | M-items | production status |", "|---|---|---|---|---|"]
for c, r in c_rows.items():
    md.append(f"| {c} | {r['dimension']} | {r['pk_core_status']} | {' '.join(r['m_items']) or '—'} | {r['production_status']} |")
md += ["", "## Problems", *(f"- {p}" for p in problems or ["none"])]
(rel / "TRACEABILITY.md").write_text("\n".join(md) + "\n")
print(json.dumps(out["summary"]), "problems:", len(problems))
sys.exit(1 if problems else 0)
