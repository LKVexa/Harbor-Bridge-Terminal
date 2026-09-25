"""Self-contained formal production exit gate (C090, C100).

    python tools/production_gate.py [--run] [--config-digest sha256:...]

``--run`` regenerates repository-owned evidence first (certification tests,
conformance, benchmark + perf gate, governance).  Each criterion yields PASS,
BLOCKED, WAIVED or NOT_APPLICABLE.  Rules:
  * evidence must carry the *current* source digest, else BLOCKED (stale);
  * a missing tool or evidence file is BLOCKED, never skipped;
  * WAIVED only with an active, approved, unexpired waiver in governance/WAIVERS.json;
  * each domain also requires an approval from its accountable role in
    governance/APPROVALS.json bound to the current digest;
  * the report is HMAC-signed only when INV37_GATE_KEY_FILE is supplied,
    otherwise the gate is BLOCKED on "evidence_unsigned".
Overall PASS requires every criterion PASS/WAIVED/NOT_APPLICABLE.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
ART = HERE / "artifacts"
EXT = ART / "external"

# criterion id -> (domain, requirement ids, kind, source)
#  kind "repo": evaluated from repository-generated evidence
#  kind "external": must be supplied as artifacts/external/<id>.json with {"status":"PASS","source_digest":...}
CRITERIA = [
    ("unit_contract_security_tests", "testing", ["C081", "C082", "C086", "C087"], "repo", "certification/tests.json"),
    ("conformance_fixtures", "interfaces", ["C029", "C016", "C027"], "repo", "certification/conformance.json"),
    ("perf_regression_gate", "performance", ["C062", "C070"], "repo", "certification/perf_gate.json"),
    ("governance_metadata", "ownership", ["C009", "C098", "C099"], "repo", "certification/governance.json"),
    ("adr_approved", "architecture", ["C010", "C031"], "adr", "ADR-0001-zero-copy-transport.md"),
    ("host_guest_zero_copy", "architecture", ["C010", "C011", "C066"], "external", "host_guest_zero_copy"),
    ("vm_topology_integration", "testing", ["C030", "C083"], "external", "vm_topology_integration"),
    ("multi_arch_runtime_matrix", "testing", ["C084", "C093"], "external", "multi_arch_runtime_matrix"),
    ("mtls_or_workload_identity", "security", ["C023", "C044"], "external", "mtls_or_workload_identity"),
    ("encryption_provider_pinned", "security", ["C047"], "external", "encryption_provider_pinned"),
    ("independent_penetration_test", "security", ["C041", "C050", "C087"], "external", "independent_penetration_test"),
    ("soak_burst_fleet_scale", "performance", ["C063", "C088"], "external", "soak_burst_fleet_scale"),
    ("power_thermal_edge", "performance", ["C068"], "external", "power_thermal_edge"),
    ("partition_disaster_drill", "resilience", ["C055", "C060", "C089"], "external", "partition_disaster_drill"),
    ("restore_drill", "operations", ["C095"], "external", "restore_drill"),
    ("canary_rollback_drill", "operations", ["C038", "C092"], "external", "canary_rollback_drill"),
    ("dashboards_alerts_deployed", "observability", ["C080", "C074"], "external", "dashboards_alerts_deployed"),
    ("escalation_tabletop", "ownership", ["C009", "C097"], "external", "escalation_tabletop"),
    ("sbom_signed_artifact", "implementation", ["C031", "C045"], "external", "sbom_signed_artifact"),
]
DOMAIN_APPROVER = {"testing": "service_owner", "interfaces": "architecture_approver", "performance": "architecture_approver",
                   "ownership": "service_owner", "architecture": "architecture_approver", "security": "security_owner",
                   "resilience": "sre_owner", "operations": "sre_owner", "observability": "sre_owner",
                   "implementation": "service_owner"}


def _run(cmd, out: Path) -> int:
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, cwd=HERE, timeout=1800)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.stat().st_mtime < __import__("time").time() - 5:
        out.write_text(r.stdout if r.stdout.strip().startswith("{") else json.dumps({"status": "BLOCKED", "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]}))
    return r.returncode


def regenerate(digest: str) -> None:
    c = ART / "certification"
    _run(["tools/run_certification.py", "--out", str(c / "tests.json")], c / "tests.json")
    _run(["conformance/run.py", "--out", str(c / "conformance.json")], c / "conformance.json")
    _run(["benchmarks/bench.py", "--out", str(ART / "benchmarks" / "current.json")], ART / "benchmarks" / "current.json")
    r = subprocess.run([sys.executable, "tools/perf_gate.py", str(ART / "benchmarks" / "current.json")], capture_output=True, text=True, cwd=HERE)
    (c / "perf_gate.json").write_text(r.stdout)
    r = subprocess.run([sys.executable, "tools/check_governance.py"], capture_output=True, text=True, cwd=HERE)
    (c / "governance.json").write_text(r.stdout)
    for name in ("conformance.json", "perf_gate.json", "governance.json"):
        p = c / name
        try:
            d = json.loads(p.read_text())
        except json.JSONDecodeError:
            d = {"status": "BLOCKED", "reason": "unparseable tool output"}
        d["source_digest"] = digest  # generated in this run from this source tree
        p.write_text(json.dumps(d, indent=1))


def load(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def active_waiver(req_ids, today):
    w = load(HERE / "governance" / "WAIVERS.json") or {"waivers": []}
    for x in w.get("waivers", []):
        try:
            if x.get("requirement") in req_ids and x.get("approver") and dt.date.fromisoformat(x["expires"]) >= today:
                return x
        except (KeyError, ValueError):
            continue
    return None


def evaluate(config_digest: str | None) -> dict:
    pkg = __import__(HERE.name)
    lineage = pkg.telemetry.release_lineage()
    digest = lineage["source_digest"]
    today = dt.date.today()
    results = []
    for cid, domain, reqs, kind, src in CRITERIA:
        status, reason = "BLOCKED", ""
        if kind == "repo":
            ev = load(ART / src)
            if ev is None:
                reason = "evidence missing"
            else:
                ev_digest = ev.get("source_digest") or ev.get("artifact", {}).get("source_digest")
                if ev_digest != digest:
                    reason = "evidence stale (digest mismatch)"
                elif ev.get("status") == "PASS":
                    status, reason = "PASS", "repository evidence current"
                else:
                    reason = f"evidence status {ev.get('status')}"
        elif kind == "adr":
            text = (HERE / src).read_text()
            status, reason = ("PASS", "approved") if "**Status:** Approved" in text else ("BLOCKED", "ADR not approved")
        else:
            ev = load(EXT / f"{src}.json")
            if ev is None:
                reason = "external evidence not supplied"
            elif ev.get("source_digest") != digest:
                reason = "external evidence stale"
            elif ev.get("status") == "PASS":
                status, reason = "PASS", ev.get("summary", "")
            else:
                reason = f"external status {ev.get('status')}"
        if status == "BLOCKED":
            w = active_waiver(["INV-37-" + r for r in reqs], today)
            if w:
                status, reason = "WAIVED", f"waiver until {w['expires']} by {w['approver_role']}"
        results.append({"criterion": cid, "domain": domain, "requirements": ["INV-37-" + r for r in reqs],
                        "status": status, "reason": reason})
    approvals = (load(HERE / "governance" / "APPROVALS.json") or {}).get("approvals", [])
    missing_approvals = sorted({DOMAIN_APPROVER[d] for d in DOMAIN_APPROVER
                                if not any(a.get("role") == DOMAIN_APPROVER[d] and a.get("source_digest") == digest for a in approvals)})
    blockers = [r["criterion"] for r in results if r["status"] == "BLOCKED"]
    if missing_approvals:
        blockers.append("approvals_missing:" + ",".join(missing_approvals))
    if not config_digest:
        blockers.append("config_digest_not_bound")
    report = {"schema": "INV37_PRODUCTION_GATE/1", "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "artifact": lineage, "config_digest": config_digest, "criteria": results,
              "missing_approvals": missing_approvals, "blockers": blockers}
    key_file = os.environ.get("INV37_GATE_KEY_FILE")
    body = json.dumps(report, sort_keys=True).encode()
    if key_file and Path(key_file).is_file():
        report["signature"] = "hmac-sha256:" + hmac.new(Path(key_file).read_bytes().strip(), body, hashlib.sha256).hexdigest()
    else:
        report["signature"] = None
        report["blockers"].append("evidence_unsigned")
    report["decision"] = "PASS" if not report["blockers"] else "NO_GO"
    return report


def render_md(r: dict) -> str:
    lines = [f"# INV-37 production gate — {r['decision']}", "",
             f"- Artifact: `{r['artifact']['version']}` `{r['artifact']['source_digest']}`",
             f"- Config digest: `{r['config_digest']}`", f"- Generated: {r['generated_at']}", f"- Signature: `{r['signature']}`", "",
             "| Criterion | Domain | Requirements | Status | Reason |", "|---|---|---|---|---|"]
    for c in r["criteria"]:
        lines.append(f"| {c['criterion']} | {c['domain']} | {', '.join(x[7:] for x in c['requirements'])} | **{c['status']}** | {c['reason']} |")
    lines += ["", "## Blockers", ""] + [f"- {b}" for b in r["blockers"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--config-digest")
    a = ap.parse_args(argv)
    pkg = __import__(HERE.name)
    if a.run:
        regenerate(pkg.telemetry.release_lineage()["source_digest"])
    r = evaluate(a.config_digest)
    out = ART / "certification"
    out.mkdir(parents=True, exist_ok=True)
    (out / "production_gate.json").write_text(json.dumps(r, indent=1))
    (out / "PRODUCTION_GATE.md").write_text(render_md(r))
    print(json.dumps({"decision": r["decision"], "blockers": len(r["blockers"])}))
    return 0 if r["decision"] == "PASS" else 3


if __name__ == "__main__":
    sys.exit(main())
