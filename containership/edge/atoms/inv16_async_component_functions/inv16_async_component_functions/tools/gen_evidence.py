"""Produce the machine-readable evidence bundle and local gate (closure #41).

    python tools/gen_evidence.py [--soak-minutes 3] [--bench-samples 200000]

Writes ``evidence/`` (+ ``evidence/release/``), then a hash-chained ledger
``evidence/inv16_local_evidence.jsonl`` whose every record binds an artifact
digest, and ``evidence/INV16_LOCAL_GATE.json``.  Verify with
``python tools/verify_evidence.py``.  This bundle is *local* evidence: it does
not replace pk_core's ``pk_evidence.jsonl`` / ``PK_GATE_RESULTS.json``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile

PKG = pathlib.Path(__file__).resolve().parents[1]
EV = PKG / "evidence"
sys.path.insert(0, str(PKG / "tools"))
import closure_status  # noqa: E402

INTERPRETERS = ["python3.10", "python3.11", "python3.12", "python3.13"]


def sh(cmd, cwd=PKG, env=None, timeout=3600):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def digest(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name: str, obj) -> pathlib.Path:
    p = EV / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")
    return p


def test_matrix() -> dict:
    rows = []
    logs = EV / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    for py in INTERPRETERS:
        if shutil.which(py) is None:
            rows.append({"python": py, "status": "UNAVAILABLE"})
            continue
        for opt in ("", "-O"):
            cmd = [py] + ([opt] if opt else []) + ["-m", "unittest", "discover", "-s", ".", "-t", ".", "-v"]
            code, out, err = sh(cmd, cwd=PKG / "tests")
            log = err + out
            name = f"tests_{py}{opt.replace('-', '_')}.log"
            (logs / name).write_text(log)
            m = re.search(r"Ran (\d+) tests", log)
            skipped = len(re.findall(r"\.\.\. skipped", log))
            passed_ids = re.findall(r"^(test\w+) \(([\w.]+)\)", log, re.M)
            rows.append({"python": py, "optimize": bool(opt), "exit": code, "ran": int(m.group(1)) if m else 0,
                         "skipped": skipped, "status": "PASS" if code == 0 else "FAIL", "log": f"logs/{name}",
                         "log_sha256": digest(logs / name),
                         "skipped_tests": re.findall(r"^(\w+) \([\w.]+\).*skipped '?(.*?)'?$", log, re.M)})
            rows[-1]["tests"] = sorted({f"{c}.{t}" for t, c in passed_ids})
    return {"schema": "inv16.test_matrix/1", "rows": rows,
            "all_pass": all(r["status"] in ("PASS", "UNAVAILABLE") for r in rows),
            "note": "skipped tests are the 3 pk_core conformance tests; they are NOT counted as PASS anywhere."}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--soak-minutes", type=float, default=3.0)
    ap.add_argument("--bench-samples", type=int, default=200_000)
    a = ap.parse_args(argv)
    if EV.exists():
        shutil.rmtree(EV)
    EV.mkdir()
    py = sys.executable
    results: dict[str, pathlib.Path] = {}

    env = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine(),
           "cpus": os.cpu_count(), "interpreters": {p: shutil.which(p) for p in INTERPRETERS},
           "package_version": (PKG / "VERSION").read_text().strip()}
    results["environment"] = write("environment.json", env)

    code, out, err = sh([py, "-m", "compileall", "-q", "-x", "evidence|dist", "."])
    results["compileall"] = write("compileall.json", {"exit": code, "stderr": err[-2000:], "pass": code == 0})
    results["test_matrix"] = write("test_matrix.json", test_matrix())
    code, out, _ = sh([py, "tools/lint.py", "--json"])
    results["lint"] = write("lint.json", json.loads(out))
    code, out, _ = sh([py, "tools/coverage_gate.py", "--out", str(EV / "coverage.json")])
    results["coverage"] = EV / "coverage.json"
    code, out, _ = sh([py, "-m", PKG.name + ".preflight", "--json"], cwd=PKG.parent)
    results["preflight"] = write("preflight.json", json.loads(out))
    code, out, _ = sh([py, "-m", PKG.name + ".preflight", "--json", "--require-pk-core"], cwd=PKG.parent)
    results["preflight_certification"] = write("preflight_certification.json", {"exit": code, **json.loads(out)})
    sh([py, "bench/bridge_bench.py", "--samples", str(a.bench_samples), "--out", str(EV / "bench" / "bridge.json")])
    results["bench_bridge"] = EV / "bench" / "bridge.json"
    results["bench_bridge_raw"] = EV / "bench" / "bridge.raw.json"
    sh([py, "bench/capacity_bench.py", "--out", str(EV / "bench" / "capacity.json")])
    results["bench_capacity"] = EV / "bench" / "capacity.json"
    sh([py, "bench/soak.py", "--minutes", str(a.soak_minutes), "--interval", "2",
        "--out", str(EV / "bench" / "soak.json")], timeout=int(a.soak_minutes * 60 + 600))
    results["soak"] = EV / "bench" / "soak.json"
    code, out, _ = sh([py, "tools/rollback.py"])
    results["rollback"] = write("rollback.json", json.loads(out))
    code, out, _ = sh([py, "tools/canary.py"])
    results["canary"] = write("canary.json", json.loads(out))

    rel = EV / "release"
    code, out, _ = sh([py, "tools/release.py", "build", "--out", str(rel)])
    code, out, _ = sh([py, "tools/release.py", "verify", "--out", str(rel)])
    results["release_verify"] = write("release/verify.json", json.loads(out))
    for f in sorted(rel.iterdir()):
        results[f"release:{f.name}"] = f
    with tempfile.TemporaryDirectory() as d:
        whl = next(rel.glob("*.whl"))
        c1, o1, e1 = sh([py, "-m", "pip", "install", "--no-deps", "--no-index", "--target", d, str(whl)])
        envp = dict(os.environ, PYTHONPATH=d)
        c2, o2, e2 = sh([py, "-m", PKG.name + ".preflight", "--json"], cwd=tempfile.gettempdir(), env=envp)
        c3, o3, e3 = sh([py, "-c", f"import {PKG.name} as m, {PKG.name}.bridge; print(m.__file__, m.__version__)"],
                        cwd=tempfile.gettempdir(), env=envp)
    results["clean_install"] = write("clean_install.json", {
        "pip_exit": c1, "preflight_exit": c2, "import": o3.strip(), "import_exit": c3,
        "installed_from": whl.name, "pass": c1 == c2 == c3 == 0 and d in o3})

    # 100 checklist items: represented, never claimed PASS without pk_core.
    checklist = json.loads((PKG / "CHECKLIST.json").read_text())
    items = [{"check_id": it["check_id"], "dimension": it["dimension"], "status": "NOT_ASSESSED",
              "reason": "pk_core absent: the 100-item assessment cannot execute (closure #1)",
              "related_local_evidence": ["test_matrix.json"]} for it in checklist["items"]]
    results["checklist_items"] = write("checklist_items.json",
                                       {"element": "INV-16", "count": len(items), "items": items})

    closure = [{"item": n, "title": t, "priority": p, "status": s, "evidence": e, "note": note,
                "owner": closure_status.OWNER, "target_version": closure_status.TARGET, "waiver": None}
               for n, t, p, s, e, note in closure_status.ITEMS]
    results["closure_status"] = write("closure_status.json", {"items": closure})

    # hash-chained ledger
    sums_digest = digest(rel / "SHA256SUMS")
    ledger = EV / "inv16_local_evidence.jsonl"
    prev = "0" * 64
    lines = []
    for seq, (kind, path) in enumerate(sorted(results.items()), 1):
        rec = {"seq": seq, "kind": kind, "path": str(path.relative_to(EV)), "sha256": digest(path),
               "release_sha256sums": sums_digest, "version": env["package_version"], "prev": prev}
        rec["hash"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
        prev = rec["hash"]
        lines.append(json.dumps(rec, sort_keys=True))
    ledger.write_text("\n".join(lines) + "\n")

    tm = json.loads(results["test_matrix"].read_text())
    bench = json.loads(results["bench_bridge"].read_text())
    soak = json.loads(results["soak"].read_text())
    p0_open = [c for c in closure if c["priority"] == "P0" and c["status"] != "PASS"]
    gate = {
        "schema": "inv16.local_gate/1", "element": "INV-16", "version": env["package_version"],
        "ledger_head": prev, "release_sha256sums": sums_digest,
        "checks": {
            "tests_all_interpreters": tm["all_pass"],
            "lint": json.loads(results["lint"].read_text())["pass"],
            "coverage": json.loads(results["coverage"].read_text())["pass"],
            "release_reproducible": json.loads(results["release_verify"].read_text())["reproducible"],
            "clean_install": json.loads(results["clean_install"].read_text())["pass"],
            "soak": soak["pass"],
            "bridge_slo_p99_lt_5us": bench["slo_pass"],
            "pk_core_certification_preflight": json.loads(results["preflight_certification"].read_text())["ok"],
        },
        "closure_counts": {s: sum(1 for c in closure if c["status"] == s)
                           for s in ("PASS", "PARTIAL", "BLOCKED", "OPEN")},
        "p0_not_pass": [f'{c["item"]}: {c["title"]} ({c["status"]})' for c in p0_open],
        "checklist_items_represented": len(items), "checklist_items_pass_claimed": 0,
    }
    local_ok = all(v for k, v in gate["checks"].items() if k not in ("bridge_slo_p99_lt_5us",
                                                                        "pk_core_certification_preflight"))
    gate["local_engineering_verdict"] = "GREEN" if local_ok else "RED"
    certifiable = not p0_open and gate["checks"]["pk_core_certification_preflight"]
    gate["production_certification_verdict"] = "CONDITIONAL_GO" if certifiable else "NO_GO"
    (EV / "INV16_LOCAL_GATE.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n")
    print(json.dumps(gate, indent=2, sort_keys=True))
    return 0 if local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
