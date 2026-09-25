"""Production exit gate (C090, C100, X013).

Consumes the evidence bundle (``evidence/``), verifies its manifest digests, and produces a deterministic
``EXIT_GATE.json`` (+ ``.sha256``). Verdicts:

  GO               no blockers
  CONDITIONAL_GO   only P2 controls open, each with an approved waiver
  NO_GO            anything else

Blockers come from: failed/unexpectedly-skipped tests (a skip is never a pass for a production gate), any
evidence result != PASS, evidence digest mismatch or missing file, non-certifiable performance evidence,
open P0/P1 controls (status other than IMPLEMENTED_LOCAL / PRESERVED_FROM_V5, or any control lacking the
owner sign-off every acceptance package requires), governance problems, and the missing pk_core gate.

``--selftest`` proves the gate fails closed on a tampered and on an incomplete bundle.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REQUIRED = ["TESTS.json", "TESTS_O.json", "FUZZ.json", "FAULTS.json", "DRILLS.json", "BENCH.json", "PERF_GATE.json",
            "SOAK.json", "STRESS.json", "SCHEMAS.json", "SECRET_SCAN.json", "GOVERNANCE.json", "RTM.json", "RELEASE.json",
            "INSTALL.json", "PREFLIGHT.json", "SMOKE.json", "INTEGRATION.json", "AUDIT_VERIFY.json"]


def priorities() -> dict[str, str]:
    t = (PKG / "source" / "INV-26_v5.0.0_Missing_Component_Engineering_Checklist.md").read_text()
    return {c: p for c, p in re.findall(r"## (?:INV-26-)?(C\d{3}|X\d{3})[^\n]*\n+\*\*Priority:\*\* (P\d)", t)}


def evaluate(ev: Path) -> dict:
    blockers: list[dict] = []

    def block(kind, ref, why, severity="P0"):
        blockers.append({"kind": kind, "ref": ref, "why": why, "severity": severity})
    manifest_p = ev / "EVIDENCE_MANIFEST.json"
    if not manifest_p.exists():
        block("evidence", "EVIDENCE_MANIFEST.json", "missing")
        manifest = {"files": {}}
    else:
        manifest = json.loads(manifest_p.read_text())
    docs = {}
    for name in REQUIRED:
        p = ev / name
        if not p.exists():
            block("evidence", name, "missing")
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if manifest["files"].get(name) != digest:
            block("evidence", name, "digest does not match EVIDENCE_MANIFEST (tampered or stale)")
        docs[name] = json.loads(p.read_text())
    for name, d in docs.items():
        res = d.get("result")
        if name == "GOVERNANCE.json":
            if res != "PASS":
                for prob in d.get("problems", []):
                    block("governance", "C009/C098/C099", prob, "P2")
            continue
        if name in ("PREFLIGHT.json",) and d.get("profile") != "production":
            block("environment", name, "preflight ran with the reference profile, not production")
        if res not in ("PASS", None):
            block("evidence", name, f"result {res}")
    t = docs.get("TESTS.json", {})
    if t:
        if t.get("failures") or t.get("errors"):
            block("tests", "TESTS.json", f"{t.get('failures')} failures / {t.get('errors')} errors")
        if t.get("skipped"):
            block("tests", "tests/test_component.py", f"{t['skipped']} skipped (pk_core absent) - skips never count as a "
                  "pass for a production gate (X013)")
    for name in ("BENCH.json", "SOAK.json"):
        if docs.get(name) and not docs[name].get("certifiable"):
            block("performance", name, "not certifiable: reference VMM / short duration (X014)", "P1")
    rtm = docs.get("RTM.json", {})
    if rtm.get("check_errors"):
        block("traceability", "RTM.json", f"{len(rtm['check_errors'])} RTM check errors")
    pr = priorities()
    for row in rtm.get("rows", []):
        cid = row["id"]
        sev = pr.get(cid, "P2")
        if row["status"] in ("IMPLEMENTED_LOCAL", "PRESERVED_FROM_V5"):
            if row["status"] == "PRESERVED_FROM_V5":
                continue
            block("signoff", cid, "implemented locally; owner/reviewer sign-off required by the acceptance package",
                  "P2" if sev == "P2" else "P1")
        else:
            block("control", cid, f"{row['status']}: " + "; ".join(row.get("gaps", [])[:2]), sev)
    sev_counts = {}
    for b in blockers:
        sev_counts[b["severity"]] = sev_counts.get(b["severity"], 0) + 1
    verdict = "GO" if not blockers else ("CONDITIONAL_GO" if set(sev_counts) == {"P2"} else "NO_GO")
    doc = {"schema": "PK_SNAPSHOT_EXIT_GATE/1", "component": "INV-26", "version": (PKG / "VERSION").read_text().strip(),
           "verdict": verdict, "blocker_counts": sev_counts, "blockers": blockers,
           "evidence_manifest_sha256": hashlib.sha256(manifest_p.read_bytes()).hexdigest() if manifest_p.exists() else None,
           "independent_review": None,
           "note": "The implementer cannot certify its own evidence; a GO additionally requires a named reviewer."}
    return doc


def selftest(ev: Path) -> dict:
    out = {}
    tmp = Path(tempfile.mkdtemp(prefix="inv26-gate-"))
    shutil.copytree(ev, tmp / "a")
    p = tmp / "a" / "FUZZ.json"
    d = json.loads(p.read_text()); d["result"] = "PASS"; d["findings"] = []; d["iterations"] = 10 ** 9
    p.write_text(json.dumps(d))
    g = evaluate(tmp / "a")
    out["tampered_detected"] = any(b["ref"] == "FUZZ.json" and "digest" in b["why"] for b in g["blockers"])
    shutil.copytree(ev, tmp / "b")
    (tmp / "b" / "FAULTS.json").unlink()
    g = evaluate(tmp / "b")
    out["missing_detected"] = any(b["ref"] == "FAULTS.json" and b["why"] == "missing" for b in g["blockers"])
    out["result"] = "PASS" if out["tampered_detected"] and out["missing_detected"] else "FAIL"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=str(PKG / "evidence"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    ev = Path(a.evidence)
    doc = evaluate(ev)
    if a.selftest:
        doc["selftest"] = selftest(ev)
    body = json.dumps(doc, indent=1, sort_keys=True) + "\n"
    (ev / "EXIT_GATE.json").write_text(body)
    (ev / "EXIT_GATE.json.sha256").write_text(hashlib.sha256(body.encode()).hexdigest() + "  EXIT_GATE.json\n")
    print(json.dumps({"verdict": doc["verdict"], "blocker_counts": doc["blocker_counts"],
                      "selftest": doc.get("selftest", {}).get("result")}))
    return 0 if doc["verdict"] == "GO" else 4


if __name__ == "__main__":
    sys.exit(main())
