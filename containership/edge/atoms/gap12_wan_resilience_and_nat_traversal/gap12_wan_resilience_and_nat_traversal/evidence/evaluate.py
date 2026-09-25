"""Evaluate all 2,420 GAP-12 checklist sub-checks (G12-H100, G12-I116).

Inputs (all produced by this build, all machine-readable):
  evidence/GAP12_CHECKLIST_v4.2.0.md   the checklist as delivered (parsed, never edited)
  evidence/out/test_results.json       per-test PASS/FAIL/ERROR/SKIP + coverage tags
  evidence/out/lab/lab_results.json    kernel-NAT lab scenarios (optional lane)
  evidence/out/bench.json              benchmarks vs declared budgets
  ops/waivers.json                     signed waivers (none exist)
  evidence/registry.py                 per-component code map / normative text

States are exactly PASS, FAIL, NOT-EVIDENCED, WAIVED.  SKIP, UNKNOWN or a
missing input is NOT-EVIDENCED, never PASS.  Rules per sub-check kind are in
RULES below; every verdict carries the evidence it rests on or the blocker
that prevents it.

    python3 -B evidence/evaluate.py [--out evidence/out]
Exit: 0 evaluated; 2 when a test carries a coverage tag for a kind that the
tagged component does not have (a tagging defect must be fixed, not ignored).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(PKG))
sys.dont_write_bytecode = True
from kinds import TEMPLATES  # noqa: E402
from registry import REG  # noqa: E402
import waivers as waiver_rules  # noqa: E402

TEST_KINDS = ({k for k, (_, c) in TEMPLATES.items() if c == "test"} | {"spec1", "spec2", "spec3", "spec4", "spec5"}) - {"integration", "unit"}
UNIT_COVERAGE_MIN = 0.80   # a component's "unit tests" item also needs its runtime module(s) >= 80 % line-covered
DOC_TEST_KINDS = {k for k, (_, c) in TEMPLATES.items() if c == "doc+test"}
LAB_KINDS = {"nat-matrix", "pcap", "transitions", "family-matrix"}

# which lab scenarios exercise which component with real kernel networking (integration evidence)
LAB_COMPONENTS = {
    "stun_eim_apdf": ["G12-A001"], "stun_apdm": ["G12-A001"], "stun_udp_blocked": ["G12-A001", "G12-H093"],
    "stun_lossy30": ["G12-A001"], "classify_eim_apdf": ["G12-A006"], "classify_apdm": ["G12-A006"],
    "classify_eim_eif": ["G12-A006"], "cgnat_double_nat": ["G12-A007"], "tcp_fallback_udp_blocked": ["G12-A005", "G12-H093"],
    "e2e_holepunch_eim": ["G12-A004", "G12-C028", "G12-D043", "G12-G079", "G12-G080", "G12-H088", "G12-H090"],
    "e2e_relay_symmetric": ["G12-A002", "G12-C040", "G12-C028", "G12-D043", "G12-H088"],
}

HUMAN_OWNER = ("No named engineering owner, security reviewer, operational owner or escalation path exists. "
               "Assigning people is an owner decision; this build does not invent names.")


def parse_checklist(path):
    text = open(path, encoding="utf-8").read()
    comps = {}
    for m in re.finditer(r"^### (\d+)\. (.*?) — (P\d)\s*\n\n\*\*Component ID:\*\* `(G12-[A-I]\d{3})`", text, re.M):
        comps[m.group(4)] = {"ordinal": int(m.group(1)), "title": m.group(2), "priority": m.group(3), "items": []}
    first_owner = {}
    for full, comp, n, body in re.findall(r"^- \[ \] \*\*(G12-([A-I]\d{3})-(\d+))\*\* (.*)$", text, re.M):
        cid = "G12-" + comp
        kind = next((k for k, (p, _) in TEMPLATES.items() if body.startswith(p)), None)
        spec_text = None
        if kind is None:
            spec_n = sum(1 for it in comps[cid]["items"] if it["kind"].startswith("spec")) + 1
            kind = f"spec{spec_n}"
            spec_text = body
            first_owner.setdefault(body, (cid, kind))
        comps[cid]["items"].append({"id": full, "n": int(n), "kind": kind, "text": body, "spec_text": spec_text})
    return comps, first_owner


def resolve_symbol(sym: str) -> bool:
    """wan.x.y / lab.x.Y / evidence.x / ops.x / docs.X / tests.x / pyproject.toml / path strings."""
    if sym.endswith((".toml", ".json")) or "/" in sym:
        return os.path.exists(os.path.join(PKG, sym))
    head = sym.split(".")[0]
    if head == "docs":
        return os.path.exists(os.path.join(PKG, "docs", sym.split(".", 1)[1] + ".md"))
    if head in ("lab", "evidence", "ops", "tests"):
        parts = sym.split(".")
        f = os.path.join(PKG, parts[0], parts[1] + ".py")
        if not os.path.exists(f):
            return parts[1] == "ci" and os.path.exists(os.path.join(PKG, "ops", "ci.sh"))
        if len(parts) == 2:
            return True
        src = open(f).read()
        return re.search(rf"^(class|def|[A-Z_]+ =) ?{re.escape(parts[2])}\b", src, re.M) is not None or parts[2] in src
    try:
        parts = sym.split(".")
        mod = importlib.import_module(f"gap12_wan_resilience_and_nat_traversal.{parts[0]}.{parts[1]}")
        obj = mod
        for p in parts[2:]:
            obj = getattr(obj, p)
        return True
    except Exception:
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--waivers", default=os.path.join(PKG, "ops", "waivers.json"))
    a = ap.parse_args(argv)
    comps, first_owner = parse_checklist(os.path.join(HERE, "GAP12_CHECKLIST_v4.2.0.md"))

    def load(p):
        try:
            with open(p) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None
    tests = load(os.path.join(a.out, "test_results.json")) or {"tests": [], "build": {}}
    lab = load(os.path.join(a.out, "lab", "lab_results.json"))
    bench = load(os.path.join(a.out, "bench.json"))
    wreg = load(a.waivers) or {"waivers": [], "approver_registry": {}}

    # --- index test evidence by (component, kind) --------------------------------------------------
    tag_pass, tag_fail, invalid = collections.defaultdict(list), collections.defaultdict(list), []
    comp_kinds = {c: {it["kind"] for it in v["items"]} for c, v in comps.items()}
    spec_text = {(c, it["kind"]): it["spec_text"] for c, v in comps.items() for it in v["items"] if it["spec_text"]}
    for t in tests["tests"]:
        for comp, kind in t["covers"]:
            if comp not in comps or kind not in comp_kinds[comp]:
                invalid.append({"test": t["id"], "component": comp, "kind": kind})
                continue
            keys = [(comp, kind)]                           # no cross-component credit, ever
            for key in keys:
                if t["status"] == "PASS":
                    tag_pass[key].append(t["id"])
                elif t["status"] in ("FAIL", "ERROR"):
                    tag_fail[key].append(t["id"])
    lab_pass = collections.defaultdict(list)
    lab_note = "lab lane not run"
    if lab and lab.get("available"):
        for r in lab["results"]:
            for c in LAB_COMPONENTS.get(r["scenario"], []):
                if r["passed"]:
                    lab_pass[c].append(r["scenario"])
        lab_note = f"{sum(r['passed'] for r in lab['results'])}/{len(lab['results'])} lab scenarios passed"
    bench_by = collections.defaultdict(list)
    for r in (bench or {}).get("results", []):
        bench_by[r["component"]].append(r)
    all_bench_ok = bool(bench) and all(r["within_budget"] for r in bench["results"])

    def glob_pass(comp, kind):
        return tag_pass.get((comp, kind), [])

    valid_waivers = {}
    for w in wreg.get("waivers", []):
        ok, why = waiver_rules.valid(w, {k: v.encode() for k, v in wreg.get("approver_registry", {}).items()}, now=time.time())
        if ok:
            valid_waivers[w["item"]] = w["id"]

    results = []
    for cid, comp in comps.items():
        reg = REG.get(cid)
        api_ok = bool(reg and reg["api"]) and all(resolve_symbol(s) for s in reg["api"])
        missing_api = [s for s in (reg["api"] if reg else []) if not resolve_symbol(s)]
        items_out = []
        for it in comp["items"]:
            k = it["kind"]
            ev, status, why = [], None, ""
            defect = None
            if it["spec_text"] and first_owner[it["spec_text"]][0] != cid and cid != "G12-H087":
                owner = first_owner[it["spec_text"]][0]
                defect = (f"checklist defect: this item's text is copied from {owner} ({comps[owner]['title']}); "
                          f"its evidence is reported under {owner}, not credited here")
            if it["id"] in valid_waivers:
                status, why = "WAIVED", f"waiver {valid_waivers[it['id']]}"
            elif defect:
                status, why = "NOT-EVIDENCED", defect
            elif cid == "G12-H087" and k.startswith("spec"):
                status, why = "NOT-EVIDENCED", ("requires interoperability runs against independent STUN/TURN implementations "
                                                 "(e.g. coturn); none is installable here (package indexes blocked). "
                                                 "This package's own servers are not independent.")
            elif k == "owners":
                status, why = "NOT-EVIDENCED", HUMAN_OWNER + f" Lifecycle recorded: {reg['lifecycle'] if reg else 'design'}."
            elif k == "exit":
                continue                                          # computed after the component's other items
            elif k in TEST_KINDS:
                p, f = tag_pass.get((cid, k), []), tag_fail.get((cid, k), [])
                if f:
                    status, ev, why = "FAIL", f, "a test evidencing this item failed"
                elif p:
                    status, ev = "PASS", p
                else:
                    status, why = "NOT-EVIDENCED", ("no executed test evidences this item" +
                                                    (f"; explicitly unsupported: {reg['unsupported']}" if reg and reg["unsupported"] else ""))
            elif k == "unit":
                p, f = tag_pass.get((cid, k), []), tag_fail.get((cid, k), [])
                mods = sorted({"wan/" + x.split(".")[1] + ".py" for x in (reg["api"] if reg else []) if x.startswith("wan.")}
                              | ({"path.py"} if cid in ("G12-H085",) else set()))
                cov = tests.get("coverage") or {}
                ratios = {m: cov.get(m, {}).get("ratio") for m in mods}
                if f:
                    status, ev = "FAIL", f
                elif not mods:
                    status, why = "NOT-EVIDENCED", "no runtime module to unit-test (document/process component)"
                elif not p:
                    status, why = "NOT-EVIDENCED", "no executed unit test is tagged for this component"
                elif any(r is None or r < UNIT_COVERAGE_MIN for r in ratios.values()):
                    status, why = "NOT-EVIDENCED", f"tests pass but module line coverage is below {UNIT_COVERAGE_MIN:.0%}: {ratios}"
                    ev = p
                else:
                    status, ev = "PASS", p + [f"coverage {m}={r:.0%}" for m, r in ratios.items()]
                    why = "line coverage is a floor, not proof that every transition/boundary is asserted"
            elif k == "integration":
                p, f = tag_pass.get((cid, k), []) + [f"lab:{s}" for s in lab_pass.get(cid, [])], tag_fail.get((cid, k), [])
                if f:
                    status, ev = "FAIL", f
                elif p:
                    status, ev = "PASS", p
                    why = ("counterparts are this package's own RFC implementations or the kernel's netfilter NAT; "
                           "interop with independent STUN/TURN implementations is G12-H087 and is not evidenced")
                else:
                    status, why = "NOT-EVIDENCED", f"no real-dependency or lab test covers this component ({lab_note})"
            elif k in DOC_TEST_KINDS:
                p, f = tag_pass.get((cid, k), []), tag_fail.get((cid, k), [])
                doc_ok = bool(reg) and ({"interfaces": api_ok, "deps": bool(reg["deps"]), "config": bool(reg["params"]),
                                          "ownership": api_ok, "concurrency-model": api_ok}[k])
                if k == "interfaces" and missing_api:
                    status, why = "FAIL", f"registry names symbols that do not exist: {missing_api}"
                elif f:
                    status, ev = "FAIL", f
                elif doc_ok and p:
                    status, ev = "PASS", p + [f"docs/components/{cid}.md"]
                else:
                    status, why = "NOT-EVIDENCED", ("definition present in docs/components but no test evidences it" if doc_ok
                                                    else "no definition recorded for this component")
            elif k == "normative":
                ok = bool(reg and reg["success"] and reg["success"] != "n/a")
                status = "PASS" if ok else "NOT-EVIDENCED"
                ev = [f"docs/components/{cid}.md#normative"] if ok else []
                why = "" if ok else "no implementation exists to state success/failure semantics against"
            elif k == "runbook":
                ok = bool(reg and reg["diag"] and reg["lifecycle"] != "design")
                status = "PASS" if ok else "NOT-EVIDENCED"
                ev = [f"docs/components/{cid}.md#operator-diagnostics"] if ok else []
                why = "" if ok else "no operator diagnostics exist for an unimplemented component"
            elif k == "protocol-map":
                ok = bool(reg and api_ok and reg["lifecycle"] != "design") and \
                    os.path.exists(os.path.join(PKG, "docs", "adr", f"ADR-{cid}.md"))
                status, ev = ("PASS", [f"docs/components/{cid}.md#protocol-map", f"docs/adr/ADR-{cid}.md"]) if ok else ("NOT-EVIDENCED", [])
                why = "" if ok else "no protocol implementation to map"
            elif k == "threat-model":
                path = os.path.join(PKG, "docs", "THREAT_MODEL.md")
                ok = os.path.exists(path) and f"## {cid}" in open(path).read()
                status, ev = ("PASS", [f"docs/THREAT_MODEL.md#{cid}"]) if ok else ("NOT-EVIDENCED", [])
                why = ("created, NOT independently reviewed" if ok else "no component threat model")
            elif k in LAB_KINDS:
                status = "NOT-EVIDENCED"
                why = {"nat-matrix": "lab covers EIM/APDF, APDM (symmetric), EIM/EIF, double NAT (CGNAT-like), UDP-blocked/TCP-only and 30% loss with real netfilter; IPv6-only, NAT64 and captive/walled networks are impossible on this kernel/lab, so the full matrix is not evidenced",
                       "pcap": "pcaps exist for success, timeout (UDP-blocked) and relay paths; refusal, authentication-failure, mapping-change and teardown captures were not produced",
                       "transitions": "suspend/resume, interface rename, DHCP renewal, IPv6 privacy rotation, VPN transitions and gateway replacement need a real host/OS event source; only simulated snapshots were tested",
                       "family-matrix": "IPv6, dual-stack and NAT64 runs are impossible on this kernel (no IPv6); IPv4 NAT variants, CGNAT-like, UDP-blocked and relay/direct were run in the lab"}[k]
                ev = [lab_note]
            elif k == "perf":
                rows = bench_by.get(cid, [])
                if not rows:
                    status, why = "NOT-EVIDENCED", "no benchmark measures this component"
                elif all(r["within_budget"] for r in rows):
                    status, ev = "PASS", [f"bench:{r['bench']}" for r in rows]
                    why = "budgets are proposed engineering targets, not approved SLOs"
                else:
                    status, ev = "FAIL", [f"bench:{r['bench']}" for r in rows if not r["within_budget"]]
            elif k == "acceptance":
                status, why = "NOT-EVIDENCED", ("per-component acceptance record generated (acceptance/" + cid +
                                                ".json) but it cannot be complete: no security review has been performed "
                                                "and no waiver approver exists")
            elif k == "results":
                ok = bool(tests.get("build", {}).get("source_digest")) and bool(tag_pass.get((cid, "unit")) or lab_pass.get(cid))
                status, ev = ("PASS", ["evidence/out/test_results.json"]) if ok else ("NOT-EVIDENCED", [])
                why = "" if ok else "no executed tests for this component to report"
            elif k == "no-skip":
                p = glob_pass("G12-H085", "no-skip")
                status, ev = ("PASS", p + ["evidence/ci_gate.py"]) if p else ("NOT-EVIDENCED", [])
            elif k == "gate":
                p = glob_pass("G12-I116", "gate")
                status, ev = ("PASS", p + ["evidence/evaluate.py"]) if p else ("NOT-EVIDENCED", [])
                why = "the gate mechanism exists; its verdict for this build is NOT a production approval"
            elif k == "runtime-matrix":
                p = glob_pass("G12-I101", "runtime-matrix")
                status, ev = ("PASS", p + ["pyproject.toml", "ops/ci.sh"]) if p else ("NOT-EVIDENCED", [])
                why = "only CPython 3.11 / Linux is a verified cell; other cells are declared"
            elif k == "staged":
                p = glob_pass("G12-I101", "staged")
                status, ev = ("PASS", p + ["wan/rollout.py"]) if p else ("NOT-EVIDENCED", [])
                why = "mechanism tested; never exercised against a real fleet"
            elif k == "reproducible":
                status, why = "NOT-EVIDENCED", ("builds are byte-reproducible and carry SBOM + provenance bound to the "
                                                 "artifact digest, but provenance is UNSIGNED and no signing policy/identity exists")
                ev = glob_pass("G12-I102", "reproducible")
            elif k == "runbooks":
                status, why = "NOT-EVIDENCED", "runbooks exist with roles, but escalation contacts are people and none are named"
                ev = ["docs/RUNBOOK_DAY0.md", "docs/RUNBOOK_DAY1.md", "docs/RUNBOOK_DAY2.md"]
            elif k == "vuln":
                status, why = "NOT-EVIDENCED", ("no vulnerability scanner is reachable from this build (package indexes blocked); "
                                                 "a remediation SLA and revocation policy require owner commitment")
            else:
                status, why = "NOT-EVIDENCED", f"no rule for kind {k}"
            rec = {"id": it["id"], "kind": k, "status": status, "evidence": ev, "reason": why, "text": it["text"][:160]}
            if defect:
                rec["checklist_defect"] = defect
            items_out.append(rec)
        others = [r["status"] for r in items_out]
        exit_item = next(it for it in comp["items"] if it["kind"] == "exit")
        if all(s in ("PASS", "WAIVED") for s in others):
            ex = ("PASS", "every mandatory sub-check is PASS or validly waived")
        elif "FAIL" in others:
            ex = ("FAIL", f"{others.count('FAIL')} sub-check(s) FAIL")
        else:
            ex = ("NOT-EVIDENCED", f"{others.count('NOT-EVIDENCED')} sub-check(s) NOT-EVIDENCED")
        items_out.append({"id": exit_item["id"], "kind": "exit", "status": ex[0], "evidence": [], "reason": ex[1],
                          "text": exit_item["text"][:160]})
        items_out.sort(key=lambda r: int(r["id"].rsplit("-", 1)[1]))
        results.append({"component": cid, "title": comp["title"], "priority": comp["priority"],
                        "lifecycle": reg["lifecycle"] if reg else "design", "api": reg["api"] if reg else [],
                        "missing_api": missing_api, "items": items_out,
                        "counts": dict(collections.Counter(r["status"] for r in items_out))})

    # --- summaries ---------------------------------------------------------------------------------
    allitems = [i for c in results for i in c["items"]]
    by_status = collections.Counter(i["status"] for i in allitems)
    by_prio = {p: {"components": sum(c["priority"] == p for c in results),
                   "exit_pass": sum(c["priority"] == p and c["items"][-1]["status"] == "PASS" for c in results),
                   "items": dict(collections.Counter(i["status"] for c in results if c["priority"] == p for i in c["items"]))}
               for p in ("P0", "P1", "P2")}
    by_group = {g: dict(collections.Counter(i["status"] for c in results if c["component"][4] == g for i in c["items"]))
                for g in "ABCDEFGHI"}
    by_kind = collections.defaultdict(collections.Counter)
    for i in allitems:
        by_kind[i["kind"]][i["status"]] += 1
    gdod = [
        ("G-DOD-01", "NOT-EVIDENCED", "no P0 component has passed its exit gate (owners and security review absent)"),
        ("G-DOD-02", "NOT-EVIDENCED", "mandatory IPv6/NAT64/independent-interop tests cannot run in this environment"),
        ("G-DOD-03", "PASS" if glob_pass("G12-C028", "spec1") and glob_pass("G12-H098", "unit") else "NOT-EVIDENCED",
         "hard deadlines (AttemptRunner) + bounded histories/limiters + retry budget, tested"),
        ("G-DOD-04", "NOT-EVIDENCED", "identity/E2E enforcement is tested for direct/punched/relayed; TCP/QUIC/translated paths are not covered"),
        ("G-DOD-05", "NOT-EVIDENCED", "IPv6, dual-stack, NAT64/464XLAT scenarios impossible here"),
        ("G-DOD-06", "PASS" if glob_pass("G12-G080", "unit") else "NOT-EVIDENCED", "explain() + registered reason codes, redacted"),
        ("G-DOD-07", "NOT-EVIDENCED", "reproducible + SBOM + canary + kill switch exist; provenance unsigned"),
    ]
    summary = {
        "schema": "G12-EVALUATION/1", "evaluated_at": time.time(), "build": tests.get("build", {}),
        "inputs": {"tests": tests.get("summary"), "lab": lab_note, "bench_all_within_budget": all_bench_ok,
                   "valid_waivers": len(valid_waivers)},
        "items_total": len(allitems), "components_total": len(results), "by_status": dict(by_status),
        "by_priority": by_prio, "by_group": by_group, "by_kind": {k: dict(v) for k, v in sorted(by_kind.items())},
        "global_definition_of_done": [{"id": i, "status": s, "reason": r} for i, s, r in gdod],
        "completion_summary": {
            "P0_completion": f"{by_prio['P0']['exit_pass']} / {by_prio['P0']['components']}",
            "P1_completion": f"{by_prio['P1']['exit_pass']} / {by_prio['P1']['components']}",
            "P2_completion": f"{by_prio['P2']['exit_pass']} / {by_prio['P2']['components']}",
            "open_waivers": len(valid_waivers), "latest_certification_digest": tests.get("build", {}).get("source_digest"),
            "production_gate_decision": "NO-GO", "approvers": [],
        },
        "checklist_defects": sorted({i["checklist_defect"].split(";")[0] + f" -> {i['id']}" for i in allitems if "checklist_defect" in i}),
        "invalid_tags": invalid,
    }
    os.makedirs(os.path.join(a.out, "acceptance"), exist_ok=True)
    for c in results:
        with open(os.path.join(a.out, "acceptance", f"{c['component']}.json"), "w") as fh:
            json.dump({"component": c["component"], "title": c["title"], "source_digest": tests.get("build", {}).get("source_digest"),
                       "config_digest": tests.get("build", {}).get("config_digest"), "tests": tests.get("summary"),
                       "security_findings": None, "security_review": "NOT PERFORMED", "waivers": [],
                       "exit_gate": c["items"][-1]["status"], "counts": c["counts"]}, fh, indent=1)
    with open(os.path.join(a.out, "evaluation.json"), "w") as fh:
        json.dump({"summary": summary, "components": results}, fh, indent=1)
    with open(os.path.join(a.out, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({"items": len(allitems), **dict(by_status), "P0_exit_pass": summary["completion_summary"]["P0_completion"],
                      "invalid_tags": len(invalid)}))
    if invalid:
        for i in invalid[:50]:
            print("INVALID TAG", i)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
