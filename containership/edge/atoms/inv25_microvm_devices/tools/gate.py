"""Standalone INV-25 evidence + production gate (work items 3 and 26).

    python tools/gate.py run    [--out-dir .]    # run all tests, emit evidence chain + gate result
    python tools/gate.py verify [--out-dir .]    # re-verify chain, file digests, source digest, signature

Evidence:  evidence/pk_evidence.jsonl   (one INV25_EVIDENCE_RECORD/1 per check, hash-chained)
Gate:      conformance/PK_GATE_RESULTS.json

This gate is honest about scope: it evaluates the 100 RTM rows using the repository's own tests and
artifacts.  Rows the RTM marks BLOCKED stay BLOCKED; EXTERNAL/NOT_APPLICABLE rows count only when an
*approved, unexpired* waiver covers them.  GO requires everything else PASS.  When pk_core becomes
available, its `pk_core gate` output is recorded alongside, never replaced by this file.
"""
from __future__ import annotations

import argparse, datetime, hashlib, hmac, io, json, os, pathlib, platform, subprocess, sys, unittest, uuid

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
SOURCE_GLOBS = ["*.py", "VERSION", "CHECKLIST.json", "schemas/*.json", "tools/*.py", "tests/*.py",
                "conformance/**/*.py", "conformance/**/*.json", "governance/*.json", "pyproject.toml"]
EXCLUDE = {"conformance/PK_GATE_RESULTS.json"}
GENESIS = "sha256:" + "0" * 64


def canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def source_files():
    seen = set()
    for g in SOURCE_GLOBS:
        for p in PKG.glob(g):
            rel = p.relative_to(PKG).as_posix()
            if p.is_file() and rel not in EXCLUDE and "__pycache__" not in rel:
                seen.add(rel)
    return sorted(seen)


def source_tree_digest():
    h = hashlib.sha256()
    for rel in source_files():
        h.update(rel.encode() + b"\0" + hashlib.sha256((PKG / rel).read_bytes()).digest())
    return "sha256:" + h.hexdigest()


def git_commit():
    try:
        return subprocess.run(["git", "-C", str(PKG), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return None


def run_tests():
    loader = unittest.TestLoader()
    sys.path.insert(0, str(PKG / "tests"))
    suite = loader.discover(str(PKG / "tests"), top_level_dir=str(PKG / "tests"))
    ran = []

    def walk(s):
        for t in s:
            if isinstance(t, unittest.TestSuite):
                walk(t)
            else:
                ran.append(t.id())
    walk(suite)
    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
    failed = {t.id() for t, _ in res.failures + res.errors}
    skipped = {t.id() for t, _ in res.skipped}
    by_class = {}
    for tid in ran:
        mod, cls, _ = tid.rsplit(".", 2)
        key = f"tests/{mod.split('.')[-1]}.py::{cls}"
        st = "failed" if tid in failed else ("skipped" if tid in skipped else "passed")
        agg = by_class.setdefault(key, {"passed": 0, "failed": 0, "skipped": 0})
        agg[st] += 1
    return by_class, buf.getvalue(), res.testsRun, len(failed), len(skipped)


def approved_waivers(today):
    reg = json.loads((PKG / "governance" / "waivers.json").read_text())
    ok = {}
    for w in reg["waivers"]:
        if w["status"] == "approved" and w["approvers"] and datetime.date.fromisoformat(w["expires"]) >= today:
            for c in w["checks"]:
                ok.setdefault(c, []).append(w["id"])
    return ok


def evaluate(out_dir: pathlib.Path):
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    rtm = json.loads((PKG / "governance" / "RTM.json").read_text())
    sys.path.insert(0, str(PKG / "tools"))
    import rtm as rtm_mod
    rtm_errors = rtm_mod.check(rtm)
    by_class, log, n_run, n_fail, n_skip = run_tests()
    waivers = approved_waivers(now.date())
    tree = source_tree_digest()
    build_id = os.environ.get("INV25_BUILD_ID") or ("local-" + uuid.uuid4().hex[:12])
    clean = os.environ.get("CI") == "true"
    version = (PKG / "VERSION").read_text().strip()
    ev_dir = out_dir / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "test-log.txt").write_text(log)
    prev, records, outcomes = GENESIS, [], {}
    for r in rtm["rows"]:
        tests_ok = all(by_class.get(t, {}).get("passed", 0) > 0 and by_class[t]["failed"] == 0 for t in r["tests"])
        status, reason = r["status"], r["reason"]
        if status == "PASS" and not tests_ok:
            status, reason = "FAIL", "linked test class failed, was skipped entirely, or did not run"
        if status == "PASS" and rtm_errors:
            status, reason = "FAIL", "RTM linkage errors present"
        evidence = []
        for a in r["artifacts"]:
            p = PKG / a.split("::")[0]
            if p.is_file():
                evidence.append({"path": a, "sha256": sha(p.read_bytes())})
            elif p.is_dir():
                evidence.append({"path": a, "sha256": sha(canon(sorted(
                    (x.relative_to(PKG).as_posix(), sha(x.read_bytes())) for x in p.rglob("*") if x.is_file()
                    and "__pycache__" not in x.parts)))})
        evidence.append({"path": "evidence/test-log.txt", "sha256": sha(log.encode())})
        rec = {"schema": "INV25_EVIDENCE_RECORD/1", "element": "INV-25", "check_id": r["check_id"],
               "status": status, "reason": reason, "evidence": evidence, "evaluator": "tools/gate.py",
               "tool_version": version, "timestamp": ts, "source_tree": tree, "build_id": build_id,
               "clean_environment": clean, "prev": prev}
        rec["digest"] = sha(canon(rec))
        prev = rec["digest"]
        records.append(rec)
        waived = waivers.get(r["check_id"], [])
        acceptable = status == "PASS" or (status in ("EXTERNAL", "NOT_APPLICABLE", "BLOCKED") and waived)
        outcomes[r["check_id"]] = {"status": status, "acceptable": bool(acceptable), "waivers": waived}
    (ev_dir / "pk_evidence.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in records))
    counts = {}
    for o in outcomes.values():
        counts[o["status"]] = counts.get(o["status"], 0) + 1
    hard_fail = any(o["status"] == "FAIL" for o in outcomes.values())
    all_ok = all(o["acceptable"] for o in outcomes.values())
    all_pass = all(o["status"] == "PASS" for o in outcomes.values())
    approvals = json.loads((PKG / "governance" / "approvals.json").read_text())["approvals"]
    roles = {a.get("role") for a in approvals}
    verdict = ("NO_GO" if hard_fail or n_fail else
               "GO" if all_pass and {"owner", "security", "release"} <= roles else
               "CONDITIONAL_GO" if all_ok and {"owner", "security", "release"} <= roles else "NO_GO")
    prev_gate = None
    gp = out_dir / "conformance" / "PK_GATE_RESULTS.json"
    if gp.exists():
        try:
            prev_gate = json.loads(gp.read_text()).get("gate_digest")
        except Exception:
            prev_gate = None
    gate = {"schema": "INV25_GATE_RESULT/1", "element": "INV-25", "version": version, "timestamp": ts,
            "verdict": verdict, "source_tree": tree, "git_commit": git_commit(), "build_id": build_id,
            "clean_environment": clean, "release_archive_digest": os.environ.get("INV25_ARCHIVE_DIGEST"),
            "python": platform.python_version(), "platform": f"{platform.system()}-{platform.machine()}",
            "pk_core": "not available (work item 1)", "checklist_digest": sha((PKG / "CHECKLIST.json").read_bytes()),
            "schemas": {"evidence": "INV25_EVIDENCE_RECORD/1", "gate": "INV25_GATE_RESULT/1"},
            "tests": {"run": n_run, "failed": n_fail, "skipped": n_skip},
            "rtm_errors": rtm_errors, "status_counts": counts, "evidence_head": prev,
            "evidence_file_digest": sha((ev_dir / "pk_evidence.jsonl").read_bytes()),
            "waivers_applied": sorted({w for o in outcomes.values() for w in o["waivers"]}),
            "approvals": approvals, "previous_gate": prev_gate, "outcomes": outcomes,
            "blocking": sorted(c for c, o in outcomes.items() if not o["acceptable"])}
    gate["gate_digest"] = sha(canon(gate))
    key = os.environ.get("INV25_GATE_KEY")
    gate["signature"] = ({"scheme": "hmac-sha256", "value": hmac.new(key.encode(), gate["gate_digest"].encode(),
                                                                       hashlib.sha256).hexdigest()}
                         if key else {"scheme": "none", "value": None,
                                      "note": "unsigned: no signing key in this environment (W-0005)"})
    gp.parent.mkdir(parents=True, exist_ok=True)
    gp.write_text(json.dumps(gate, indent=1, sort_keys=True) + "\n")
    return gate


def verify(out_dir: pathlib.Path) -> list[str]:
    errs = []
    gate = json.loads((out_dir / "conformance" / "PK_GATE_RESULTS.json").read_text())
    body = {k: v for k, v in gate.items() if k not in ("gate_digest", "signature")}
    if sha(canon(body)) != gate["gate_digest"]:
        errs.append("gate digest mismatch")
    if gate["source_tree"] != source_tree_digest():
        errs.append("stale gate: source tree changed since gate was produced")
    evp = out_dir / "evidence" / "pk_evidence.jsonl"
    if sha(evp.read_bytes()) != gate["evidence_file_digest"]:
        errs.append("evidence file digest mismatch")
    sys.path.insert(0, str(PKG))
    from schemavalidate import validate
    esch = json.loads((PKG / "schemas" / "PK_EVIDENCE_RECORD_1.schema.json").read_text())
    prev, seen = GENESIS, set()
    for line in evp.read_text().splitlines():
        rec = json.loads(line)
        errs += [f"{rec.get('check_id')}: {e}" for e in validate(rec, esch)]
        if rec["prev"] != prev or sha(canon({k: v for k, v in rec.items() if k != "digest"})) != rec["digest"]:
            errs.append(f"evidence chain broken at {rec['check_id']}")
        if rec["check_id"] in seen:
            errs.append(f"duplicate {rec['check_id']}")
        seen.add(rec["check_id"])
        prev = rec["digest"]
        for e in rec["evidence"]:
            p = PKG / e["path"].split("::")[0]
            if p.is_file() and e["path"] != "evidence/test-log.txt" and sha(p.read_bytes()) != e["sha256"]:
                errs.append(f"{rec['check_id']}: evidence file changed {e['path']}")
    want = {f"INV-25-C{i:03d}" for i in range(1, 101)}
    if seen != want:
        errs.append("evidence does not cover C001-C100 exactly once")
    if prev != gate["evidence_head"]:
        errs.append("evidence head mismatch")
    key = os.environ.get("INV25_GATE_KEY")
    sig = gate.get("signature", {})
    if key and sig.get("scheme") == "hmac-sha256":
        if not hmac.compare_digest(sig["value"], hmac.new(key.encode(), gate["gate_digest"].encode(),
                                                          hashlib.sha256).hexdigest()):
            errs.append("gate signature invalid")
    elif os.environ.get("INV25_RELEASE") == "1":
        errs.append("release mode requires a verifiable gate signature")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "verify"])
    ap.add_argument("--out-dir", default=str(PKG))
    ap.add_argument("--require-go", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out_dir)
    if a.cmd == "run":
        g = evaluate(out)
        print(json.dumps({k: g[k] for k in ("verdict", "status_counts", "tests", "blocking", "gate_digest")}, indent=1))
        return 0 if (g["verdict"] == "GO" or not a.require_go) and g["tests"]["failed"] == 0 else 1
    errs = verify(out)
    print(json.dumps({"verify_errors": errs}, indent=1))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
