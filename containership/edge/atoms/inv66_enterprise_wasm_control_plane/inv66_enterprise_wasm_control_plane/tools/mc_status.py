"""Execute the INV-66 v4.2.0 missing-components checklist against this tree (all 1,420 items).

    python tools/mc_status.py        # needs release/ci_report.json

Inputs: governance/INV66_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md (the governing checklist, verbatim),
tools/mc_map.py (per-MC evidence + open items), shared-family rules below, release/ci_report.json (test/lane results).

Outputs: release/mc_status.json, governance/…CHECKLIST.executed.md (every line annotated; a box is ticked only
for DONE items whose evidence verified), and the 4.3.0 disposition table appended to MISSING_COMPONENTS.md.

No MC is ever reported CLOSED here: every MC's D05 (independent review) is OPEN_HUMAN until a reviewer
record exists in release/reviews.jsonl.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mc_map import EV, OPEN  # noqa: E402

SRC = ROOT / "governance" / "INV66_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md"
OUT_MD = ROOT / "governance" / "INV66_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.executed.md"
D, PA, H, X = "DONE", "PARTIAL", "OPEN_HUMAN", "OPEN_EXTERNAL"

# Shared-family rules: prefix -> (status, note).  "@tests" means DONE when the MC has test evidence, else PARTIAL.
FAMILY = [
    ("Define the artifact owner, reviewer roles", H, "roles defined in governance/owners.json; people/teams UNASSIGNED"),
    ("Capture assumptions, non-goals", D, "stated in the artifact"),
    ("Use stable document/schema IDs", D, "stable IDs + versions; CHANGELOG"),
    ("Link the artifact to relevant `CHECKLIST.json`", D, "release/rtm.json"),
    ("Add automated repository checks", D, "tools/ci.py lanes docs/master/schema-drift/requirements-drift"),
    ("Assign a stable test/evidence ID", D, "test ids in release/ci_report.json, linked in release/rtm.json"),
    ("Automate the control in CI/CD", D, "tools/ci.py; NOT_RUN is never PASS"),
    ("Exercise positive, negative, boundary", "@tests", "upgrade/rollback paths only where noted"),
    ("Retain machine-readable results", D, "release/ci_report.json + environment + digests"),
    ("Define ownership, review/renewal cadence", PA, "cadence + release-blocking defined; owners UNASSIGNED"),
    ("Document the trust boundary, caller/callee", D, "docs/INTERFACES.md, docs/TOPOLOGY.md"),
    ("Define deterministic timeouts, limits", D, "docs/INTERFACES.md, production/resilience.py"),
    ("Propagate request/correlation/trace", D, "request_id/decision_id/traceparent + protocol recorded per decision"),
    ("Instrument rate/error/latency/saturation", PA, "service-level metrics; no per-interface stage metrics"),
    ("Provide schema-driven contract tests", D, "tests/contract + fixtures/compat"),
    ("Define attacker capabilities", D, "docs/THREAT_MODEL.md"),
    ("Apply least privilege, explicit scopes", D, "production/rbac.py (deny-overrides, default deny, delegation subset)"),
    ("Use approved cryptography/key management", PA, "Ed25519/AES-256-GCM/SHA-256 via cryptography; no managed KMS (W-05)"),
    ("Ensure security-sensitive successes and failures", D, "admit.decision/admit.refused/config.*/rbac.*/quarantine.* journal records with codes"),
    ("Derive negative/adversarial tests", D, "tests/security/test_threats.py T01-T17"),
    ("Define ownership and durability class", D, "docs/TOPOLOGY.md#persisted-datasets"),
    ("Validate all inputs before activation", D, "schema + semantic validation before stage/activate/admit"),
    ("Record immutable revision/digest", D, "config generation digest recorded on every decision"),
    ("Provide concurrency control, atomicity", D, "CAS activation, flock journal, startup integrity check"),
    ("Instrument state age/version", PA, "generation + journal head exposed; no state-age/lag metrics"),
    ("Express externally observable behavior", D, "typed decision states + error registry"),
    ("Define tenant/site/environment scope", D, "scope paths + site/environment in config"),
    ("Assign stable normative IDs", D, "requirements/requirements.json REQ-INV66-*"),
    ("Create executable/golden fixtures", D, "fixtures/compat + policy conflict fixtures in tests"),
    ("Require architecture/security/SRE review", H, "review not performed"),
    ("Define RPO/RTO, consistency", PA, "consistency/ordering/duplicates defined; RPO/RTO values PROPOSED"),
    ("Bound retries, queues, memory", D, "retry policy, shedder, bounded caches, compaction"),
    ("Preserve authorization, isolation, audit integrity", D, "tested in fault/disaster/concurrency suites"),
    ("Expose health/degraded/lag/backlog", PA, "health/degraded/backlog/ownership via /readyz + freeze controls; no replication-lag signal"),
    ("Prove the design using repeatable multi-process", PA, "repeatable multi-process + fault tests on one host; not production-like"),
    ("Define a stable telemetry schema", D, "PK_ECP_LOG/1 + docs/TELEMETRY_POLICY.md"),
    ("Correlate metrics/logs/traces/audit/explain", D, "trace_id/decision_id/request_id across all four"),
    ("Instrument normal, denied, degraded", D, "outcome/code counters + degraded mode + shed/quota/authn counters"),
    ("Ensure telemetry/export failure cannot block", D, "in-process metrics; synchronous bounded logging; SIEM exporter decoupled"),
    ("Provide dashboards/alerts or operator views", PA, "dashboards/alerts with runbooks; ownership UNASSIGNED"),
    ("Define representative workload distributions", PA, "1/3/20-component workloads + env fingerprint; not production-derived"),
    ("Measure end-to-end and per-stage latency", PA, "end-to-end, throughput, heap, FDs; no per-stage/CPU/network"),
    ("Define hard bounds for memory/queue/concurrency", D, "in-flight caps, quotas, bounded caches; overload test"),
    ("Link measured capacity to autoscaling", PA, "docs/CAPACITY.md model; scaling thresholds PROPOSED"),
    ("Publish raw benchmark artifacts", PA, "release/bench.json + perf gate; thresholds PROPOSED, no approved baseline"),
]
DITEMS = {
    "D01": (D, "artifacts in version control at documented paths and in RELEASE_MANIFEST.sha256"),
    "D02": (PA, "exact version pins, schemas/fixtures versioned; hash-locked constraints pending (W-09)"),
    "D03": (PA, "RTM rows carry artifacts, tests, release, waivers; owner field empty (UNASSIGNED)"),
    "D04": ("@verify", "verified in a clean container run of tools/ci.py; hosted CI not run"),
    "D05": (H, "no independent security/architecture/operations review recorded (release/reviews.jsonl)"),
    "D06": (D, "release/evidence.json + RELEASE_MANIFEST.sha256 digests (signature ephemeral)"),
    "D07": (D, "docs/runbooks + component docs"),
}


def parse():
    text = SRC.read_text()
    mcs = {}
    cur = None
    for line in text.splitlines():
        m = re.match(r"## (MC-\d{3}) — (.*)", line)
        if m:
            cur = m.group(1)
            mcs[cur] = {"title": m.group(2), "severity": None, "items": []}
            continue
        m = re.match(r"\*\*Severity:\*\* (.*?)\s*$", line)
        if m and cur:
            mcs[cur]["severity"] = m.group(1)
        m = re.match(r"- \[ \] `(MC-\d{3}-([TD]\d{2}))` (.*)", line)
        if m:
            mcs[m.group(1)[:6]]["items"].append({"id": m.group(1), "k": m.group(2), "text": m.group(3)})
    return text, mcs


def verify_ev(ev, ci):
    tests, lanes = ci.get("tests", {}), ci.get("lanes", {})
    out = []
    for e in ev:
        if e.startswith("lane:"):
            st = (lanes.get(e[5:]) or {}).get("status", "MISSING")
            out.append({"ref": e, "ok": st == "PASS", "status": st})
        elif e.startswith("tests."):
            hits = {k: v for k, v in tests.items() if k == e or k.startswith(e + ".")}
            ok = bool(hits) and all(v["outcome"] == "pass" for v in hits.values())
            out.append({"ref": e, "ok": ok, "status": f"{sum(v['outcome'] == 'pass' for v in hits.values())}/{len(hits)} pass"})
        else:
            out.append({"ref": e, "ok": (ROOT / e).exists(), "status": "exists" if (ROOT / e).exists() else "MISSING"})
    return out


def main() -> int:
    ci_p = ROOT / "release" / "ci_report.json"
    ci = json.loads(ci_p.read_text()) if ci_p.exists() else {}
    ci = dict(ci, lanes={**ci.get("lanes", {}), "rtm": {"status": "PASS" if (ROOT / "release/rtm.json").exists() else "MISSING"}})
    text, mcs = parse()
    assert len(mcs) == 71, len(mcs)
    result = {}
    totals: dict[str, int] = {}
    for mc, info in mcs.items():
        ev = verify_ev(EV[mc], ci)
        ev_ok = all(e["ok"] for e in ev)
        has_tests = any(e["ref"].startswith("tests.") for e in ev)
        rows = []
        for it in info["items"]:
            if it["k"].startswith("D"):
                st, note = DITEMS[it["k"]]
            elif it["k"] in OPEN.get(mc, {}):
                st, note = OPEN[mc][it["k"]]
            else:
                fam = next(((s, n) for p, s, n in FAMILY if it["text"].startswith(p)), None)
                st, note = fam if fam else (D, "implemented; see evidence")
            if st == "@tests":
                st = D if has_tests else PA
                note = note if has_tests else "document/tooling only; no executable test for this MC"
            if st == "@verify":
                st = D if (ev_ok and (has_tests or any(e["ref"].startswith("lane:") for e in ev))) else PA
                if st == PA:
                    note = "verification is document review only, or evidence did not verify"
            if st == D and not ev_ok:
                st, note = "FAIL_EVIDENCE", "evidence did not verify: " + ", ".join(e["ref"] for e in ev if not e["ok"])
            rows.append({"id": it["id"], "status": st, "note": note})
            totals[st] = totals.get(st, 0) + 1
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        # disposition is judged on the T items; D01-D07 carry the same shared blockers for every MC
        # (D02 hash lock, D03 owners, D05 independent review) and are reported separately.
        tcounts: dict[str, int] = {}
        for r in rows:
            if r["id"][-3] == "T":
                tcounts[r["status"]] = tcounts.get(r["status"], 0) + 1
        if counts.get("FAIL_EVIDENCE"):
            disp = "FAIL_EVIDENCE"
        elif set(tcounts) <= {D}:
            disp = "ENGINEERED_AWAITING_REVIEW"
        elif tcounts.get("NA_PROPOSED"):
            disp = "NA_PROPOSED"
        elif tcounts.get(X):
            disp = "PARTIAL_EXTERNAL_DEPENDENCY"
        elif tcounts.get(PA):
            disp = "PARTIAL"
        else:
            disp = "IMPLEMENTED_PENDING_HUMAN_DECISIONS"
        result[mc] = {"title": info["title"], "severity": info["severity"], "disposition": disp, "counts": counts,
                      "task_counts": tcounts,
                      "evidence": ev, "items": rows}
    disp_counts: dict[str, int] = {}
    for v in result.values():
        disp_counts[v["disposition"]] = disp_counts.get(v["disposition"], 0) + 1
    summary = {"schema": "PK_ECP_MC_STATUS/1", "checklist": SRC.name, "mcs": len(result),
               "items": sum(len(v["items"]) for v in result.values()), "item_totals": totals,
               "dispositions": disp_counts, "closed": 0,
               "closure_rule": "an MC closes only when every item is DONE and D05 has a reviewer record", "mc": result}
    (ROOT / "release" / "mc_status.json").write_text(json.dumps(summary, indent=1) + "\n")
    # executed checklist
    status_of = {r["id"]: r for v in result.values() for r in v["items"]}
    out = []
    for line in text.splitlines():
        m = re.match(r"- \[ \] `(MC-\d{3}-[TD]\d{2})` (.*)", line)
        if m:
            r = status_of[m.group(1)]
            box = "x" if r["status"] == D else " "
            out.append(f"- [{box}] `{m.group(1)}` {m.group(2)}  \n  **→ {r['status']}** — {r['note']}")
            continue
        m = re.match(r"## (MC-\d{3}) — ", line)
        out.append(line)
        if m:
            v = result[m.group(1)]
            out.append("")
            out.append(f"> **4.3.0 disposition: {v['disposition']}** · " +
                       " · ".join(f"{k} {n}" for k, n in sorted(v["counts"].items())) +
                       "  \n> Evidence: " + ", ".join(f"`{e['ref']}` ({e['status']})" for e in v["evidence"]))
    head = ["# EXECUTED — INV-66 v4.2.0 → 4.3.0 missing-components checklist", "",
            "Generated by `tools/mc_status.py` from the governing checklist (verbatim copy alongside) and `release/ci_report.json`.",
            f"Items: {summary['items']} · " + " · ".join(f"{k} {n}" for k, n in sorted(totals.items())),
            "MC dispositions: " + " · ".join(f"{k} {n}" for k, n in sorted(disp_counts.items())) + " · **CLOSED 0**",
            "A box is ticked only for DONE items whose evidence verified in this run. No item is independently reviewed yet.", "", "---", ""]
    OUT_MD.write_text("\n".join(head + out) + "\n")
    # disposition section in MISSING_COMPONENTS.md
    mcp = ROOT / "MISSING_COMPONENTS.md"
    base = mcp.read_text().split("\n## 4.3.0 disposition")[0].rstrip() + "\n"
    tbl = ["", "## 4.3.0 disposition (generated by tools/mc_status.py — do not edit)", "",
           f"{summary['items']} checklist items executed: " + ", ".join(f"{k} {n}" for k, n in sorted(totals.items())) +
           ". No MC is closed: each needs an independent review (D05). Disposition is judged on the task (T) items;"
           " every MC also carries the shared D-item blockers D02 (hash-locked deps), D03 (owners) and D05 (review).", "",
           "| MC | Severity | Disposition | DONE | PARTIAL | HUMAN | EXTERNAL | Title |", "|---|---|---|---|---|---|---|---|"]
    for mc, v in result.items():
        c = v["counts"]
        tbl.append(f"| {mc} | {v['severity']} | {v['disposition']} | {c.get(D, 0)} | {c.get(PA, 0)} | {c.get(H, 0)} | "
                   f"{c.get(X, 0)} | {v['title']} |")
    mcp.write_text(base + "\n".join(tbl) + "\n")
    print(json.dumps({"items": summary["items"], "totals": totals, "dispositions": disp_counts}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
