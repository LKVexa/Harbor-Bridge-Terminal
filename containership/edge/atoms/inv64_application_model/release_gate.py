"""Local production exit gate with machine-readable acceptance evidence (MC-29; C090, C100).

    python -m inv64_application_model.release_gate [--evidence evidence/] [--pk-gate FILE]
           [--approval FILE] [--today YYYY-MM-DD] [--out evidence/EXIT_GATE.json]

Shape adapted from the owner's INV-44 v4.3.0 ``release_gate.py``; the INV-64
gate is stricter:

* inputs are only files: the evidence directory, ``ops/GATE_POLICY.json``,
  ``COMPONENTS_STATUS.json``, ``evidence/REQUIREMENTS_MATRIX.json``,
  ``ops/REGISTER.json`` and optional external pk_core/approval records;
* every referenced evidence file must exist, parse, carry the expected
  ``schema`` and ``result: PASS``; its SHA-256 is recorded;
* every Critical/High missing component must be COMPLETE; a Medium one may be
  covered only by an **active, unexpired, owned, approved** register waiver
  (-> CONDITIONAL_GO); expired waivers force NO_GO;
* every INV-64-C### control must be ``verified`` or ``not_applicable`` (or
  waived as above);
* pk_core gate output is required (``--pk-gate``) and must be for INV-64 with
  a PASS/GO verdict; a human approval record must name a non-service approver
  distinct from the policy administrator;
* the verdict is a pure function of (evidence bytes, policy, today) — running
  twice on the same inputs yields the same verdict and ``input_digest``;
  ``generated_at`` is informational and excluded from the digest.

Exit codes: 0 GO, 2 CONDITIONAL_GO, 3 NO_GO.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GATE_SCHEMA = "PK_APP_EXIT_GATE/1"
SERVICE_MARKERS = ("bot", "service", "claude", "ci", "automation", "pipeline", "github-actions")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _revision() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown (not a git checkout)"


def evaluate(*, policy: dict, components: dict, matrix: dict, register: dict, evidence_dir: Path,
             pk_gate: dict | None, approval: dict | None, today: dt.date) -> dict:
    blockers: list[str] = []
    conditions: list[str] = []
    results: list[dict] = []
    digests: dict[str, str] = {}
    waivers = {}
    for e in register["entries"]:
        if e["type"] in ("waiver", "exception"):
            valid = (e.get("status") == "active" and e.get("owner") and e.get("approvers") and
                     e.get("compensating_controls") and dt.date.fromisoformat(e["expires"]) >= today)
            for target in e.get("affected", []):
                waivers.setdefault(target, []).append((e["id"], bool(valid), e["severity"], e["expires"]))
    # 1. evidence files
    for ctl in policy["evidence"]:
        p = evidence_dir / ctl["file"]
        entry = {"control": ctl["id"], "file": ctl["file"], "severity": ctl["severity"]}
        if not p.is_file():
            entry.update(state="fail", reason="missing evidence")
        else:
            digests[ctl["file"]] = _sha(p)
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                doc = None
            if not isinstance(doc, dict) or doc.get("schema") != ctl["schema"]:
                entry.update(state="fail", reason="malformed or wrong-schema evidence")
            elif doc.get("result") != "PASS":
                entry.update(state="fail", reason=f"result={doc.get('result')}")
            elif ctl.get("no_skips") and doc.get("skipped", 0):
                entry.update(state="fail", reason=f"{doc.get('skipped')} unexpected skips")
            else:
                entry.update(state="pass")
        if entry["state"] != "pass":
            blockers.append(f"evidence {ctl['id']} ({ctl['file']}): {entry['reason']}")
        results.append(entry)
    # 2. missing components
    for c in components["components"]:
        if c["status"] == "COMPLETE":
            continue
        w = waivers.get(c["id"], [])
        if any(valid for _, valid, _, _ in w) and c["severity"] == "Medium":
            conditions.append(f"{c['id']} waived by {[i for i, v, _, _ in w if v]}")
        elif any(not valid and dt.date.fromisoformat(exp) < today for _, valid, _, exp in w):
            blockers.append(f"{c['id']} {c['severity']}: waiver expired")
        else:
            blockers.append(f"{c['id']} {c['severity']}: {c['status']}")
    # 3. checklist controls
    bad = [r["check_id"] for r in matrix["requirements"] if r["status"] not in ("verified", "not_applicable")]
    if bad:
        blockers.append(f"{len(bad)} of {len(matrix['requirements'])} INV-64-C### controls not verified (first: {bad[0]})")
    # 4. external evidence
    if not pk_gate:
        blockers.append("pk_core PK_GATE_RESULTS not supplied (MC-02)")
    elif pk_gate.get("element", "INV-64") != "INV-64" or str(pk_gate.get("verdict")).upper() not in ("PASS", "GO"):
        blockers.append("pk_core gate result is not a PASS for INV-64")
    approver = str((approval or {}).get("approver", ""))
    if not approval or approval.get("decision") != "APPROVE":
        blockers.append("no human release approval record")
    elif not approver or set(re.split(r"[^a-z0-9]+", approver.lower())) & set(SERVICE_MARKERS):
        blockers.append("release approval names a service identity or no approver")
    elif approver == approval.get("policy_administrator"):
        blockers.append("separation of duties: approver is the policy administrator")
    verdict = "NO_GO" if blockers else ("CONDITIONAL_GO" if conditions else "GO")
    input_digest = hashlib.sha256(json.dumps(
        {"digests": digests, "policy": policy, "components": components, "matrix": matrix, "register": register,
         "pk_gate": pk_gate, "approval": approval, "today": today.isoformat()}, sort_keys=True).encode()).hexdigest()
    return {"verdict": verdict, "blockers": blockers, "conditions": conditions, "controls": results,
            "evidence_digests": digests, "input_digest": input_digest}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=str(ROOT / "evidence"))
    ap.add_argument("--pk-gate")
    ap.add_argument("--approval")
    ap.add_argument("--today")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    load = lambda p: json.loads(Path(p).read_text(encoding="utf-8")) if p else None
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    policy = load(ROOT / "ops" / "GATE_POLICY.json")
    res = evaluate(policy=policy, components=load(ROOT / "COMPONENTS_STATUS.json"),
                   matrix=load(ROOT / "evidence" / "REQUIREMENTS_MATRIX.json"), register=load(ROOT / "ops" / "REGISTER.json"),
                   evidence_dir=Path(a.evidence), pk_gate=load(a.pk_gate), approval=load(a.approval), today=today)
    comp = load(ROOT / "COMPONENTS_STATUS.json")
    counts: dict[str, int] = {}
    for c in comp["components"]:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    from inv64_application_model import __version__
    from inv64_application_model.service import OAM_BASELINE, SPEC_VERSION, build_digest
    from inv64_application_model.tenancy import ISOLATION_PROFILE
    src = load(ROOT / "provenance" / "master-source.json")
    out = {"schema": GATE_SCHEMA, "element": "INV-64", "version": __version__, "gate_policy_version": policy["version"],
           "spec_version": SPEC_VERSION, "oam_baseline": OAM_BASELINE, "isolation_profile": ISOLATION_PROFILE,
           "build_digest": build_digest(), "source_corpus_sha256": [x["sha256"] for x in src["sources"]],
           "source_revision": _revision(), "python": sys.version.split()[0], "today": today.isoformat(),
           "component_status_counts": counts, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **res}
    dest = Path(a.out) if a.out else Path(a.evidence) / "EXIT_GATE.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    dest.write_text(text, encoding="utf-8")
    dest.with_suffix(".json.sha256").write_text(f"{hashlib.sha256(text.encode()).hexdigest()}  {dest.name}\n", encoding="utf-8")
    print(f"{res['verdict']}: {len(res['blockers'])} blockers, {len(res['conditions'])} conditions; input {res['input_digest'][:16]}")
    for b in res["blockers"][:60]:
        print("  -", b)
    return {"GO": 0, "CONDITIONAL_GO": 2}.get(res["verdict"], 3)


if __name__ == "__main__":
    sys.exit(main())
