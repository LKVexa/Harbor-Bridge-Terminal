"""INV-71 production exit gate (C090, C099, C100).

Offline, deterministic, fail closed.  Re-evaluates the evidence bundle and
prints GO or NO_GO with every blocking reason.  It never reads prose to decide
anything: only the release manifest, the traceability/execution records, the
approved artifact manifest, the pk_core probe, the benchmark gate, the waiver
register, the approval directory and the RACI.

Exit code 0 = GO, 2 = NO_GO, 3 = evidence integrity failure.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
EV = PKG / "evidence"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def evaluate(root: pathlib.Path = PKG, today: dt.date | None = None) -> dict:
    ev = root / "evidence"
    today = today or dt.date.today()
    blockers: list[str] = []
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            blockers.append(f"{name}: {detail}")

    # 1. integrity: every manifest entry matches bytes on disk; no unlisted files
    try:
        man = json.loads((ev / "release-manifest.json").read_text())
    except Exception as exc:
        return {"verdict": "EVIDENCE_INVALID", "blockers": [f"release manifest unreadable: {exc}"], "checks": []}
    bad = [rel for rel, d in man["files"].items() if not (root / rel).is_file() or sha(root / rel) != d]
    extra = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
             and "__pycache__" not in p.parts and p.suffix != ".pyc"
             and p.relative_to(root).as_posix() not in man["files"]
             and p.relative_to(root).as_posix() not in ("evidence/release-manifest.json", "evidence/gate-result.json")]
    if bad or extra:
        return {"verdict": "EVIDENCE_INVALID", "blockers": [f"digest mismatch: {bad[:5]}", f"unlisted files: {extra[:5]}"], "checks": []}
    checks.append({"check": "manifest_integrity", "status": "PASS", "detail": f"{len(man['files'])} files match"})
    # Presence only: verifying the signature needs the release public key, which does
    # not exist yet.  A production gate must verify it against a pinned trust root.
    check("release_signature", bool(man.get("signature")), man.get("signature_status", "unsigned"))

    # 2. tests
    tests = json.loads((ev / "tests.json").read_text())
    c = tests["counts"]
    check("tests_pass", c["FAIL"] == 0 and c["ERROR"] == 0, json.dumps(c))

    # 3. controls: all EVIDENCED or validly waived
    audit = json.loads((root / "AUDIT_AFTER.json").read_text())
    waivers = json.loads((root / "governance" / "waivers.json").read_text())["waivers"]
    valid_waiver = {}
    for w in waivers:
        try:
            exp = dt.date.fromisoformat(w["expires"])
        except Exception:
            continue
        approvers = set(w.get("approved_by", []))
        if w.get("owner") and len(approvers) >= 2 and w["owner"] not in approvers and exp >= today:
            for ctl in w.get("scope", []):
                valid_waiver[ctl] = w["id"]
    not_ev = [x["check_id"] for x in audit["controls"] if x["status"] != "EVIDENCED" and x["check_id"] not in valid_waiver]
    check("controls_evidenced", not not_ev, f"{len(not_ev)} of {len(audit['controls'])} controls not EVIDENCED and not waived")
    expired = [w.get("id") for w in waivers if w.get("expires", "0000-00-00") < today.isoformat()]
    check("no_expired_waivers", not expired, f"expired: {expired}")

    # 4. checklist execution: blocked items
    exe = json.loads((ev / "checklist_execution.json").read_text())
    blocked = [i["id"] for i in exe["items"] if i["status"] == "BLOCKED"]
    open_ = [i["id"] for i in exe["items"] if i["status"] in ("OPEN", "PARTIAL")]
    check("no_blocked_items", not blocked, f"{len(blocked)} BLOCKED items")
    check("no_open_or_partial_items", not open_, f"{len(open_)} OPEN/PARTIAL items")
    tr = json.loads((ev / "traceability.json").read_text())
    check("traceability_clean", not tr["problems"], f"{len(tr['problems'])} traceability problems")

    # 5. artifacts pinned + signed
    am = json.loads((root / "artifacts" / "approved-manifest.json").read_text())
    unpinned = [k for k, v in am["artifacts"].items() if v.get("sha256") == "UNPINNED" or v.get("version") == "UNPINNED"]
    check("artifacts_pinned", not unpinned, f"UNPINNED: {unpinned}")
    check("artifact_manifest_signed", am.get("signature") not in (None, "", "UNSIGNED"), str(am.get("signature")))

    # 6. external conformance
    probe = json.loads((ev / "pk_core_probe.json").read_text())
    check("pk_core_verified", probe["status"] == "VERIFIED", f"{probe['status']}: {probe.get('reason', '')}")

    # 7. performance
    bench = json.loads((ev / "performance" / "bench.json").read_text())
    check("performance_gate", bench["gate"]["verdict"] == "PASS", bench["gate"]["verdict"])

    # 8. fuzz
    fz = json.loads((ev / "security" / "fuzz.json").read_text())
    check("fuzz_clean", fz["total_findings"] == 0, f"{fz['total_findings']} findings")

    # 9. ownership + approvals + licence
    raci = json.loads((root / "governance" / "raci.json").read_text())
    unassigned = [r for r, v in raci["roles"].items() if v["primary"] == "UNASSIGNED"]
    check("owners_assigned", not unassigned, f"UNASSIGNED: {unassigned}")
    approvals = [json.loads(p.read_text()) for p in (root / "governance" / "approvals").glob("*.json")]
    need = {"service_owner", "network_security_owner", "sre_oncall_owner", "release_authority"}
    have = {a["role"] for a in approvals if a.get("subject") == "release" and a.get("subject_digest") == man.get("approval_subject_sha256")
            and a.get("decision") == "approve"}
    check("release_approvals", need <= have, f"missing approvals: {sorted(need - have)}")
    check("license_present", (root / "LICENSE").is_file(), "LICENSE file absent (see LICENSE_STATUS.md)")

    # 10. node qualification evidence for the production profile
    qual = json.loads((ev / "qualification.json").read_text())
    check("production_node_qualified", qual["verdict"] == "ADMIT",
          f"audit host verdict {qual['verdict']} (evidence must come from a qualified production-equivalent node)")

    verdict = "GO" if not blockers else "NO_GO"
    return {"schema": "PK_HEAVYBOX_GATE_RESULT/1", "verdict": verdict, "release_tree_sha256": man["tree_sha256"],
            "evaluated_on": today.isoformat(), "checks": checks, "blockers": blockers}


def main() -> int:
    r = evaluate()
    (EV / "gate-result.json").write_text(json.dumps(r, indent=1) + "\n")
    for b in r["blockers"]:
        print("BLOCKER", b)
    print(f"verdict: {r['verdict']} ({len(r['blockers'])} blockers)")
    return {"GO": 0, "NO_GO": 2}.get(r["verdict"], 3)


if __name__ == "__main__":
    sys.exit(main())
