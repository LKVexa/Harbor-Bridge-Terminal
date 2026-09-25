"""Release evidence, SBOM, provenance, RTM, MC status, signed manifest and the production exit gate.

    python tools/release.py build [--signing-key-ref env:NAME]   # needs release/ci_report.json (tools/ci.py)
    python tools/release.py verify                               # recompute RELEASE_MANIFEST.sha256 + signature
    python tools/release.py gate                                 # exit 0 only on GO

MC-060 (evidence bundle), MC-061 (release metadata), MC-062 (SBOM), MC-068 (exit gate), MC-001-T06 (MASTER.md
in the release manifest).  Signing: without an organisation key reference the manifest is signed with an
**ephemeral** Ed25519 key and marked ``NONPRODUCTION-EPHEMERAL``; the gate refuses that for production.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "release"
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "tools"))
VERSION = (ROOT / "VERSION").read_text().strip()
MANIFEST_EXCLUDE = {"RELEASE_MANIFEST.sha256", "release/MANIFEST.sig.json"}
SKIP_DIRS = {"__pycache__", ".git", "build", "dist"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def files() -> list[Path]:
    out = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not set(rel.parts) & SKIP_DIRS and rel.as_posix() not in MANIFEST_EXCLUDE \
                and not rel.name.endswith(".egg-info"):
            out.append(p)
    return out


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sbom(ci: dict) -> dict:
    import cryptography
    pkg = json.loads((REL / "package.json").read_text()) if (REL / "package.json").exists() else {}
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": now(), "component": {
                "type": "application", "name": "inv66-enterprise-wasm-control-plane", "version": VERSION,
                "hashes": [{"alg": "SHA-256", "content": pkg.get("sha256", "")}] if pkg else [],
                "licenses": [{"license": {"name": "NOASSERTION (no license selected; LICENSE-STATUS.md)"}}]},
                "tools": [{"name": "tools/release.py", "version": VERSION}]},
            "components": [
                {"type": "library", "name": "cryptography", "version": cryptography.__version__, "scope": "required",
                 "purl": f"pkg:pypi/cryptography@{cryptography.__version__}",
                 "licenses": [{"expression": "Apache-2.0 OR BSD-3-Clause"}]},
                {"type": "library", "name": "jsonschema", "version": "4.26.0", "scope": "optional",
                 "purl": "pkg:pypi/jsonschema@4.26.0", "licenses": [{"license": {"id": "MIT"}}],
                 "properties": [{"name": "inv66:usage", "value": "test-only"}]},
                {"type": "platform", "name": "CPython", "version": platform.python_version(), "scope": "required"}],
            "properties": [{"name": "inv66:vendored_third_party", "value": "none"},
                           {"name": "inv66:vuln_scan", "value": ci.get("lanes", {}).get("vuln-scan", {}).get("status", "NOT_RUN")}]}


def provenance(ci: dict) -> dict:
    pkg = json.loads((REL / "package.json").read_text()) if (REL / "package.json").exists() else {}
    try:
        rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        rev = ""
    return {"_type": "https://in-toto.io/Statement/v1", "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [{"name": pkg.get("wheel", "unbuilt"), "digest": {"sha256": pkg.get("sha256", "")}}],
            "predicate": {"buildDefinition": {"buildType": "inv66/tools/check_package.py@4.3.0",
                                              "externalParameters": {"source_date_epoch": pkg.get("source_date_epoch"),
                                                                     "source_tree_sha256": ci.get("source_tree_sha256"),
                                                                     "git_revision": rev or None}},
                          "runDetails": {"builder": {"id": "local-unattested-builder"},
                                         "metadata": {"finishedOn": now(), "environment": ci.get("environment")}}},
            "note": "builder identity is not attested (no CI OIDC); provenance is informative until produced by the release workflow"}


def evidence(ci: dict) -> dict:
    from control_map import CONTROLS
    rtm = json.loads((REL / "rtm.json").read_text())
    waivers = {w["id"]: w for w in json.loads((REL / "waivers.json").read_text())["waivers"]}
    reviews = [json.loads(line) for line in (REL / "reviews.jsonl").read_text().splitlines() if line.strip()] \
        if (REL / "reviews.jsonl").exists() else []
    rows = []
    for r in rtm["rows"]:
        if not r["control"]:
            continue
        m = CONTROLS[r["control"]]
        auto = "PASS" if r["evidence_status"] == "VERIFIED_LOCAL" else ("NONE" if r["evidence_status"] == "DOCUMENT_ONLY" else "FAIL")
        reviewed = any(v.get("control") == r["control"] and v.get("decision") == "approve" for v in reviews)
        if auto == "FAIL":
            state, why = "FAIL", "automated verification failed or missing"
        elif m["status"] == "NA_PROPOSED":
            state, why = "BLOCKED", "NOT_APPLICABLE proposed; approval missing"
        elif r["waivers"] and not all(waivers[w]["approver"] for w in r["waivers"]):
            state, why = "BLOCKED", f"waiver(s) {','.join(r['waivers'])} pending approval"
        elif m["status"] in ("OPEN_HUMAN", "OPEN_EXTERNAL", "PARTIAL"):
            state, why = "BLOCKED", m.get("gap", m["status"])
        elif not reviewed:
            state, why = "BLOCKED", "independent review missing"
        else:
            state, why = "PASS", ""
        rows.append({"control": r["control"], "state": state, "blocker": why, "automated_evidence": auto,
                     "engineering_status": m["status"], "artifacts": r["artifacts"], "tests": r["verification"],
                     "waivers": r["waivers"], "owner": None, "reviewer": None, "environment": ci.get("environment"),
                     "timestamp": ci.get("finished")})
    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    return {"schema": "PK_ECP_ACCEPTANCE_EVIDENCE/1", "release": VERSION, "generated": now(),
            "ci_report_sha256": sha(REL / "ci_report.json"), "rtm_sha256": sha(REL / "rtm.json"),
            "ci_overall": ci.get("overall"), "test_totals": ci.get("test_totals"),
            "pk_core_conformance": ci.get("lanes", {}).get("pk-core-gate", {"status": "NOT_RUN"}),
            "state_counts": counts, "controls": rows}


def gate(ev: dict, ci: dict, sig_trust: str) -> dict:
    owners = json.loads((ROOT / "governance/owners.json").read_text())
    waivers = json.loads((REL / "waivers.json").read_text())["waivers"]
    perf = json.loads((REL / "perf_gate.json").read_text()) if (REL / "perf_gate.json").exists() else {"verdict": "NOT_RUN"}
    rtm = json.loads((REL / "rtm.json").read_text())
    lanes = ci.get("lanes", {})
    sections = {
        "architecture": {"adr_approved": False, "evidence": "docs/adr/ADR-0001-enterprise-wasm-control-plane.md (PROPOSED)"},
        "requirements": {"rtm_problems": len(rtm["problems"]), "controls_covered": len([r for r in rtm["rows"] if r["control"]])},
        "interfaces": {"contract_lane": lanes.get("contract", {}).get("status"), "schema_drift": lanes.get("schema-drift", {}).get("status")},
        "implementation": {"ci_overall": ci.get("overall"), "lanes_not_pass": sorted(k for k, v in lanes.items() if v["status"] != "PASS")},
        "security": {"security_lane": lanes.get("security", {}).get("status"), "fuzz_lane": lanes.get("fuzz", {}).get("status"),
                     "vuln_scan": lanes.get("vuln-scan", {}).get("status")},
        "resilience": {"fault": lanes.get("fault", {}).get("status"), "disaster": lanes.get("disaster", {}).get("status"),
                       "concurrency": lanes.get("concurrency", {}).get("status")},
        "performance": {"perf_gate": perf.get("verdict"), "thresholds": perf.get("thresholds_status")},
        "observability": {"lane": lanes.get("observability", {}).get("status")},
        "testing": {"totals": ci.get("test_totals"), "pk_core": lanes.get("pk-core-gate", {}).get("status")},
        "rollback": {"config_rollback_tested": True, "artifact_rollback": "deploy/rollout.json (no orchestrator)"},
        "operations": {"runbooks": sorted(p.name for p in (ROOT / "docs/runbooks").glob("*.md"))},
        "ownership": {"bound": not any("UNASSIGNED" in json.dumps(v) for v in owners["roles"].values())},
        "evidence": {"state_counts": ev["state_counts"]},
        "release_integrity": {"signature_trust": sig_trust},
    }
    reasons = []
    if not sections["architecture"]["adr_approved"]:
        reasons.append("ADR-0001 not approved")
    if ci.get("overall") != "PASS":
        reasons.append(f"CI overall {ci.get('overall')} (lanes not PASS: {', '.join(sections['implementation']['lanes_not_pass'])})")
    if rtm["problems"]:
        reasons.append(f"RTM has {len(rtm['problems'])} problems")
    if perf.get("verdict") != "PASS":
        reasons.append(f"perf gate {perf.get('verdict')}")
    if perf.get("thresholds_status") != "APPROVED":
        reasons.append("performance thresholds not approved")
    blocked = ev["state_counts"].get("BLOCKED", 0) + ev["state_counts"].get("FAIL", 0)
    if blocked:
        reasons.append(f"{blocked} of 100 controls not PASS (BLOCKED/FAIL) — no independent reviews recorded")
    pend = [w["id"] for w in waivers if not w["approver"]]
    if pend:
        reasons.append(f"{len(pend)} waivers pending approval")
    if not sections["ownership"]["bound"]:
        reasons.append("owners/approvers not bound (governance/owners.json)")
    if sig_trust != "ORGANISATION":
        reasons.append("release manifest not signed with the organisation's production key")
    if lanes.get("pk-core-gate", {}).get("status") != "PASS":
        reasons.append("pk_core 100-item gate not run")
    approvals = {"service_owner": None, "architecture": None, "security": None, "sre": None, "release_authority": None}
    return {"schema": "PK_ECP_EXIT_GATE/1", "release": VERSION, "generated": now(),
            "decision": "GO" if not reasons and all(approvals.values()) else "NO_GO",
            "reasons": reasons, "required_approvals": approvals, "sections": sections,
            "inputs": {"evidence_sha256": sha(REL / "evidence.json"), "rtm_sha256": sha(REL / "rtm.json"),
                       "ci_report_sha256": sha(REL / "ci_report.json"),
                       "compatibility_sha256": sha(REL / "compatibility.json"),
                       "package": json.loads((REL / "package.json").read_text()) if (REL / "package.json").exists() else None},
            "break_glass": "deploy/rollout.json#break_glass — any bypass of a NO_GO must be recorded in release/reviews.jsonl"}


def sign_manifest(key_ref: str | None) -> tuple[dict, str]:
    from inv66_enterprise_wasm_control_plane.production.keys import LocalSecretProvider, Signer
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    lines = [f"{sha(p)}  ./{p.relative_to(ROOT).as_posix()}" for p in files()]
    body = "\n".join(lines) + "\n"
    (ROOT / "RELEASE_MANIFEST.sha256").write_text(body)
    if key_ref:
        seed = bytes.fromhex(LocalSecretProvider().resolve(key_ref).decode())
        signer, trust = Signer("release-org", Ed25519PrivateKey.from_private_bytes(seed)), "ORGANISATION-KEY-UNVERIFIED"
    else:
        signer, trust = Signer("release-ephemeral"), "NONPRODUCTION-EPHEMERAL"
    sig = {"schema": "PK_ECP_MANIFEST_SIG/1", "manifest_sha256": hashlib.sha256(body.encode()).hexdigest(),
           "files": len(lines), "key_id": signer.key_id, "public_key": signer.public_b64(),
           "signature": signer.sign(body.encode()), "trust": trust, "signed": now()}
    (REL / "MANIFEST.sig.json").write_text(json.dumps(sig, indent=1) + "\n")
    return sig, trust


def cmd_build(a) -> int:
    ci_p = REL / "ci_report.json"
    if not ci_p.exists():
        print("release/ci_report.json missing: run tools/ci.py first")
        return 2
    ci = json.loads(ci_p.read_text())
    (REL / "sbom.cdx.json").write_text(json.dumps(sbom(ci), indent=1) + "\n")
    (REL / "provenance.intoto.json").write_text(json.dumps(provenance(ci), indent=1) + "\n")
    # lanes produced by this tool itself (they record that the artifact was generated, not that it is GO)
    ci_rtm = json.loads(json.dumps(ci))
    ci_rtm["lanes"]["release-build"] = {"status": "PASS", "note": "sbom/provenance/evidence generated"}
    ci_rtm["lanes"]["exit-gate"] = {"status": "PASS", "note": "gate evaluated and recorded (decision is separate)"}
    ci_rtm["lanes"]["rtm"] = {"status": "PASS", "note": "RTM generated (self-reference)"}
    tmp = REL / ".ci_for_rtm.json"
    tmp.write_text(json.dumps(ci_rtm))
    trust = "NONPRODUCTION-EPHEMERAL" if not a.signing_key_ref else "ORGANISATION-KEY-UNVERIFIED"
    # two passes: rtm/evidence/exit_gate reference each other as artifacts, so the second pass is the fixed point
    for _ in range(2):
        rc = subprocess.run([sys.executable, str(ROOT / "tools/rtm.py"), "--ci", str(tmp)]).returncode
        ev = evidence(ci)
        (REL / "evidence.json").write_text(json.dumps(ev, indent=1) + "\n")
        g = gate(ev, ci, trust)
        (REL / "exit_gate.json").write_text(json.dumps(g, indent=1) + "\n")
    tmp.unlink()
    subprocess.run([sys.executable, str(ROOT / "tools/mc_status.py")], check=True)
    sig, trust = sign_manifest(a.signing_key_ref)
    print(json.dumps({"rtm_exit": rc, "evidence": ev["state_counts"], "gate": g["decision"],
                      "gate_reasons": len(g["reasons"]), "manifest_files": sig["files"], "signature": trust}, indent=1))
    return 0


def cmd_verify(_a) -> int:
    from inv66_enterprise_wasm_control_plane.production.keys import verify_sig
    body = (ROOT / "RELEASE_MANIFEST.sha256").read_text()
    bad = []
    for line in body.splitlines():
        h, path = line.split("  ", 1)
        p = ROOT / path[2:]
        if not p.exists() or sha(p) != h:
            bad.append(path)
    sig = json.loads((REL / "MANIFEST.sig.json").read_text())
    ok_sig = verify_sig(sig["public_key"], sig["signature"], body.encode()) and \
        sig["manifest_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    listed = {line.split("  ", 1)[1][2:] for line in body.splitlines()}
    unlisted = [p.relative_to(ROOT).as_posix() for p in files() if p.relative_to(ROOT).as_posix() not in listed]
    print(json.dumps({"files": len(listed), "mismatched": bad, "unlisted": unlisted, "signature_valid": ok_sig,
                      "trust": sig["trust"]}, indent=1))
    return 0 if not bad and not unlisted and ok_sig else 1


def cmd_gate(_a) -> int:
    g = json.loads((REL / "exit_gate.json").read_text())
    print(g["decision"])
    for r in g["reasons"]:
        print(" -", r)
    return 0 if g["decision"] == "GO" else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--signing-key-ref")
    sub.add_parser("verify")
    sub.add_parser("gate")
    a = ap.parse_args(argv)
    return {"build": cmd_build, "verify": cmd_verify, "gate": cmd_gate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
