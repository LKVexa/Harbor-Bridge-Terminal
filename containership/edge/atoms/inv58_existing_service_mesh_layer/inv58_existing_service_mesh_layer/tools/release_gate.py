"""Production exit gate and machine-readable release acceptance record (MC-032, C090/C100).

    python -B tools/release_gate.py [--out release/ACCEPTANCE_RECORD.json] [--skip-perf]

Exit codes: 0 GO | 3 NO_GO (engineering passed, production blockers remain) | 1 engineering failure.
Never downgrades a blocker to a warning.  Signs the record with HMAC-SHA256 when
INV58_RELEASE_SIGNING_KEY is set; an unsigned record is itself a production blocker.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
EXCLUDE = {"release", "__pycache__", ".pytest_cache"}
EXPECTED_SKIP_MARKERS = ("pk_core",)  # framework absence: expected in this archive, still a production blocker
MAX_WAIVER_DAYS = 180


def manifest():
    files = {}
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not (set(rel.parts) & EXCLUDE) and rel.as_posix() != "perf/results.json" and p.suffix != ".pyc":
            files[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    tree = hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in files.items()).encode()).hexdigest()
    return files, "sha256:" + tree


def run_tests(optimized: bool):
    cmd = [sys.executable, "-B"] + (["-O"] if optimized else []) + [str(ROOT / "tools" / "run_tests.py")]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {"run": 0, "failures": ["<runner crashed>"], "errors": [r.stderr[-800:]], "skipped": []}


def tool(name, *args):
    r = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / name), *args], capture_output=True, text=True, cwd=ROOT)
    return r.returncode, (r.stdout + r.stderr).strip()[-2000:]


def check_waivers(reg: dict, today: dt.date):
    problems = []
    for w in reg.get("waivers", []):
        owner = str(w.get("owner", "")).strip()
        if not owner or owner.upper() == "UNASSIGNED":
            problems.append(f"waiver {w.get('id')}: no named owner")
        try:
            created = dt.date.fromisoformat(w["created"])
            exp = dt.date.fromisoformat(w["expires"])
        except Exception:  # noqa: BLE001
            problems.append(f"waiver {w.get('id')}: invalid created/expires")
            continue
        if exp < today:
            problems.append(f"waiver {w.get('id')}: expired {exp}")
        if (exp - created).days > MAX_WAIVER_DAYS:
            problems.append(f"waiver {w.get('id')}: longer than {MAX_WAIVER_DAYS} days")
        for f in ("rationale", "risk", "compensating_controls", "requirement"):
            if not w.get(f):
                problems.append(f"waiver {w.get('id')}: missing {f}")
    for t in reg.get("technical_debt", []) + reg.get("deprecations", []):
        if not t.get("owner_role"):
            problems.append(f"{t.get('id')}: missing owner_role")
    return problems


def verdict(engineering_failures: list, blockers: list) -> tuple[str, int]:
    if engineering_failures:
        return "ENGINEERING_FAIL", 1
    if blockers:
        return "NO_GO", 3
    return "GO", 0


def evaluate(skip_perf=False):
    eng, blockers, evidence = [], [], {}
    files, tree = manifest()
    version = (ROOT / "VERSION").read_text().strip()
    for label, opt in (("tests", False), ("tests_optimized", True)):
        t = run_tests(opt)
        evidence[label] = {k: t.get(k) for k in ("run", "failures", "errors", "skipped", "python", "optimized", "seconds")}
        if t["failures"] or t["errors"] or not t["run"]:
            eng.append(f"{label}: {len(t['failures'])} failures, {len(t['errors'])} errors")
        for s in t["skipped"]:
            if any(m in s["reason"] for m in EXPECTED_SKIP_MARKERS):
                blockers.append(f"{label}: skipped {s['test']} ({s['reason']}) - framework conformance not executed")
            else:
                eng.append(f"{label}: UNEXPECTED skip {s['test']} ({s['reason']})")
    for name, args in (("rtm.py", ["--check"]), ("gen_fixtures.py", ["--check"])):
        rc, out = tool(name, *args)
        evidence[name] = {"exit": rc, "output": out[-400:]}
        if rc:
            eng.append(f"{name} --check failed: {out[-200:]}")
    if not skip_perf:
        rc, out = tool("bench.py", "run", "--quick")
        rc2, out2 = tool("bench.py", "gate")
        evidence["performance_gate"] = json.loads(out2) if out2.startswith("{") else {"raw": out2[-400:]}
        if rc or rc2:
            eng.append("performance gate failed: " + "; ".join(evidence["performance_gate"].get("failures", ["?"])))
    else:
        blockers.append("performance gate not run (--skip-perf)")
    reg = json.loads((ROOT / "governance/waivers.json").read_text())
    wp = check_waivers(reg, dt.date.today())
    eng += wp
    rtm = json.loads((ROOT / "governance/RTM.json").read_text())
    evidence["rtm_counts"] = rtm["counts"]
    for row in rtm["rows"]:
        if row["status"] in ("BLOCKED", "PARTIAL"):
            blockers.append(f"{row['check_id']} {row['status']}: {row['blocker']}")
    own = json.loads((ROOT / "governance/OWNERSHIP.json").read_text())
    if own["accountable_owner"]["name"] == "UNASSIGNED":
        blockers.append("no accountable owner (governance/OWNERSHIP.json)")
    if "Status:** PROPOSED" in (ROOT / "docs/ADR-001-mesh-coexistence.md").read_text():
        blockers.append("ADR-001 not approved")
    bom = json.loads((ROOT / "governance/bom.json").read_text())
    if bom["framework"]["range"] == "UNPINNED":
        blockers.append("pk_core not pinned")
    if bom["mesh_implementation"]["approved_range"] == "UNSELECTED":
        blockers.append("Istio approved range not selected")
    if not (ROOT / "MASTER.md").exists():
        blockers.append("MASTER.md (authoritative source bundle) missing - MC-001")
    if not (ROOT / "LICENSE").exists():
        blockers.append("no LICENSE: licence choice belongs to the owner (NOTICE.md)")
    reviews = list((ROOT / "governance/reviews").glob("*-independent-release-review.json"))
    if not reviews:
        blockers.append("no independent release review record (reviewer must not be the implementer or this tool)")
    key = os.environ.get("INV58_RELEASE_SIGNING_KEY")
    if not key:
        blockers.append("acceptance record unsigned (INV58_RELEASE_SIGNING_KEY not provided)")
    status, code = verdict(eng, blockers)
    record = {
        "schema": "PK_MESH_ACCEPTANCE/1", "element": "INV-58", "version": version,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_tree_digest": tree, "file_count": len(files),
        "artifact_digests": {k: files[k] for k in ("VERSION", "governance/RTM.json", "governance/bom.json",
                                                   "governance/compatibility_matrix.json", "governance/waivers.json",
                                                   "schemas/PK_MESH_CONFIG-1.schema.json", "perf/baseline.json") if k in files},
        "environment": {"python": sys.version.split()[0], "platform": sys.platform},
        "engineering": {"pass": not eng, "failures": eng},
        "production": {"verdict": status, "blockers": blockers},
        "evidence": evidence, "reviewer": None,
    }
    body = json.dumps(record, sort_keys=True).encode()
    record["signature"] = ("hmac-sha256:" + hmac.new(key.encode(), body, hashlib.sha256).hexdigest()) if key else None
    return record, code


def main(argv):
    out = ROOT / "release" / "ACCEPTANCE_RECORD.json"
    if "--out" in argv:
        out = pathlib.Path(argv[argv.index("--out") + 1])
    record, code = evaluate(skip_perf="--skip-perf" in argv)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(f"engineering: {'PASS' if record['engineering']['pass'] else 'FAIL'}  production: {record['production']['verdict']}  "
          f"blockers: {len(record['production']['blockers'])}")
    for f in record["engineering"]["failures"]:
        print("  ENG:", f)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
