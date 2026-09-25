"""Machine-readable production exit gate (MC-042).

1. Build the release (manifest, SBOM, reproducible zip).
2. Extract the archive into a clean temp dir, verify its manifest, and run every suite (normal and -O) *from the
   archive*, plus the working tree.
3. Run the performance gate.
4. Verify every closure-map evidence path exists; derive per-task and per-control status for all 969 tasks and
   100 controls (none silently omitted).
5. Decide: GO (everything closed, gates pass) / CONDITIONAL_GO (gates pass; remaining gaps covered by
   owner-APPROVED, unexpired waivers) / NO_GO (any gate fails, or any gap lacks an approved waiver).
Outputs bind to the archive sha256 and payload digest.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
import build_release  # noqa: E402
import run_checks  # noqa: E402

EXTERNAL = re.compile(r"\b(approv\w*|sign-?off|staff\w*|on-call|pager|production reference|fleet|power|"
                      r"hardware|external(ly)?|consensus|replicat\w*|KMS|HSM|legal|contact)\b", re.I)


def task_ledger(cmap: dict, residual: dict, gates_pass: bool) -> list[dict]:
    """Rule (documented, deterministic): a task inherits its component's status; in a PARTIAL component, tasks
    whose text needs people/approval/external systems are OPEN_EXTERNAL; generic final-acceptance tasks are
    EVIDENCED only when the automated gates passed."""
    out = []
    for mc, comp in residual.items():
        c = cmap[mc]
        for t in comp["tasks"]:
            if c["status"] == "CLOSED_LOCAL":
                status = "EVIDENCED"
            else:
                status = "OPEN_EXTERNAL" if EXTERNAL.search(t["text"]) else "EVIDENCED_PARTIAL"
            if t["category"] == "Acceptance" and not gates_pass:
                status = "OPEN"
            out.append({"task": t["id"], "component": mc, "category": t["category"], "status": status,
                        "evidence": c["evidence"], "tests": c["tests"], "waiver": c["waiver"]})
    return out


def main() -> int:
    dist = PKG.parent / "dist"
    build = build_release.build(dist)
    tmp = pathlib.Path(tempfile.mkdtemp())
    with zipfile.ZipFile(build["archive"]) as z:
        z.extractall(tmp)
    extracted = tmp / PKG.name
    manifest_problems = build_release.verify_tree(extracted)
    archive_tests = run_checks.run(extracted, write=False)
    tree_tests = run_checks.run(PKG, write=True)
    perf = subprocess.run([sys.executable, str(PKG / "tools" / "perf_gate.py")], capture_output=True, text=True)
    perf_doc = json.loads((PKG / "conformance" / "perf_gate_result.json").read_text())
    shutil.rmtree(tmp, ignore_errors=True)

    cmap = json.loads((PKG / "governance" / "closure_map.json").read_text())["components"]
    residual = json.loads((PKG / "governance" / "residual_tasks.json").read_text())
    waivers = {w["id"]: w for w in json.loads((PKG / "governance" / "WAIVERS.json").read_text())["items"]}
    trace = json.loads((PKG / "conformance" / "traceability.json").read_text())["controls"]
    missing = sorted({e for c in cmap.values() for e in c["evidence"]
                      if e not in build_release.GATE_OUTPUTS and not (PKG / e).exists()})
    gates = {"manifest": not manifest_problems, "archive_tests": archive_tests["status"] == "PASS",
             "tree_tests": tree_tests["status"] == "PASS", "perf": perf.returncode == 0, "evidence_present": not missing}
    gates_pass = all(gates.values())
    ledger = task_ledger(cmap, residual, gates_pass)
    today = dt.date.today().isoformat()

    def waiver_ok(wid):
        w = waivers.get(wid)
        return bool(w and w.get("approved_by") and w["expires"] >= today)
    controls = []
    for c in trace:
        if c["status"] in ("CLOSED_LOCAL", "SATISFIED_V420"):
            verdict = "PASS" if gates_pass else "FAIL"
        else:
            verdict = "WAIVER" if all(waiver_ok(w) for w in c["waivers"]) and c["waivers"] else "FAIL"
        controls.append({"control": c["control"], "verdict": verdict, "status": c["status"], "waivers": c["waivers"]})
    unapproved = sorted({c["waiver"] for c in cmap.values() if c["waiver"] and not waiver_ok(c["waiver"])})
    if not gates_pass or any(c["verdict"] == "FAIL" for c in controls):
        decision = "NO_GO"
    elif any(c["verdict"] == "WAIVER" for c in controls):
        decision = "CONDITIONAL_GO"
    else:
        decision = "GO"
    counts = {}
    for t in ledger:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    ctl_counts = {}
    for c in controls:
        ctl_counts[c["verdict"]] = ctl_counts.get(c["verdict"], 0) + 1
    gate = {"schema": "PLN01_EXIT_GATE/1", "component": "PLN-01", "version": build_release.version(),
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "generated_by": "tools/exit_gate.py", "decision": decision,
            "release": {"archive": pathlib.Path(build["archive"]).name, "archive_sha256": build["sha256"],
                        "payload_digest": build["payload_digest"], "files": build["files"]},
            "gates": gates, "manifest_problems": manifest_problems, "missing_evidence": missing,
            "tests": {"archive": archive_tests, "tree": tree_tests},
            "perf": {"status": perf_doc["status"], "baseline_approved": perf_doc["baseline_approved"]},
            "components": {k: {"status": v["status"], "waiver": v["waiver"]} for k, v in cmap.items()},
            "component_counts": {s: sum(1 for v in cmap.values() if v["status"] == s) for s in ("CLOSED_LOCAL", "PARTIAL")},
            "controls": controls, "control_counts": ctl_counts, "task_counts": counts, "tasks_total": len(ledger),
            "unapproved_waivers": unapproved,
            "note": "NO_GO while any gap depends on an unapproved waiver. Approving waivers in governance/WAIVERS.json "
                    "(approved_by + unexpired) and re-running this gate is the path to CONDITIONAL_GO."}
    (PKG / "conformance" / "EXIT_GATE.json").write_text(json.dumps(gate, indent=1))
    (PKG / "conformance" / "CLOSURE_LEDGER.json").write_text(json.dumps({"schema": "PLN01_LEDGER/1",
        "rule": task_ledger.__doc__, "archive_sha256": build["sha256"], "tasks": ledger}, indent=1))
    # Re-pack so the shipped archive carries its own gate record (gate outputs are outside the payload digest).
    final = build_release.build(dist)
    (dist / (pathlib.Path(final["archive"]).name + ".sha256")).write_text(f"{final['sha256']}  {pathlib.Path(final['archive']).name}\n")
    print(json.dumps({"decision": decision, "gates": gates, "control_counts": ctl_counts, "task_counts": counts,
                      "payload_digest": build["payload_digest"], "final_archive_sha256": final["sha256"],
                      "unapproved_waivers": unapproved}, indent=2))
    return 0 if decision != "NO_GO" else 2


if __name__ == "__main__":
    sys.exit(main())
