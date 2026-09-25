"""Local CI runner — the authoritative equivalent of .github/workflows/ci.yml (MC-33).

    python tools/ci.py [--release] [--out DIR]

Presubmit tier: every test tier (normal and -O where applicable), repository checks,
traceability, schema compatibility, benchmarks + performance gate, package build twice
(reproducibility), clean-venv install / reinstall / upgrade-from-4.1.1 / rollback drill,
item-level checklist status, then the evidence manifest.  Release tier additionally scales
fuzz/soak, evaluates the performance gate at release tier and treats any skipped mandatory
check as FAIL.  Writes evidence/<version>/ (or --out) and exits non-zero on any FAIL."""
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
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
VERSION = (ROOT / "VERSION").read_text().strip()


def run(cmd, env=None, cwd=None, timeout=1800):
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, **(env or {})},
                       cwd=cwd or ROOT.parent, timeout=timeout)
    return p.returncode, p.stdout + p.stderr, time.time() - t0


def parse_unittest(out: str) -> dict:
    ran = re.findall(r"^Ran (\d+) tests?", out, re.M)
    tail = re.findall(r"^(OK|FAILED)(?: \((.*)\))?$", out, re.M)
    res = {"tests": int(ran[-1]) if ran else 0, "failures": 0, "errors": 0, "skipped": 0}
    if tail:
        for part in (tail[-1][1] or "").split(","):
            if "=" in part:
                k, v = part.strip().split("=")
                res[{"failures": "failures", "errors": "errors", "skipped": "skipped"}.get(k, k)] = int(v)
    res["ok_line"] = tail[-1][0] if tail else "NONE"
    return res


class CI:
    def __init__(self, out: pathlib.Path, release: bool):
        self.out, self.release = out, release
        self.logs = out / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.results: dict = {}

    def record(self, name, rc, log, dur, **extra):
        (self.logs / f"{name}.log").write_text(log)
        r = {"result": "PASS" if rc == 0 else "FAIL", "exit_code": rc, "duration_s": round(dur, 2),
             "log": f"logs/{name}.log", **extra}
        self.results[name] = r
        print(f"[{r['result']}] {name} ({r['duration_s']}s)" + (f" {extra}" if extra else ""), flush=True)
        return r

    def tests(self, name, files, optimized=False, mandatory_skips=True, env=None):
        agg = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        logs, rc_all, t = [], 0, 0.0
        for f in files:
            cmd = [PY] + (["-O"] if optimized else []) + [str(ROOT / f)]
            rc, out, dur = run(cmd, env=env)
            p = parse_unittest(out)
            for k in agg:
                agg[k] += p[k]
            rc_all |= rc
            t += dur
            logs.append(f"$ {' '.join(cmd)}\n{out}")
        return self.record(name, rc_all, "\n".join(logs), t, mandatory=mandatory_skips, **agg)

    def tool(self, name, cmd, env=None, **extra):
        rc, out, dur = run(cmd, env=env)
        return self.record(name, rc, out, dur, **extra)


def clean_install(ci: CI, dist: pathlib.Path, prev_whl: pathlib.Path | None):
    with tempfile.TemporaryDirectory() as d:
        venv = pathlib.Path(d) / "v"
        log = []
        steps = [[PY, "-m", "venv", str(venv)]]
        vpy = str(venv / ("Scripts" if os.name == "nt" else "bin") / "python")
        whl = next(dist.glob("*.whl"))
        smoke = [vpy, "-c", "import pln05_elasticity_plane as p, json; from pln05_elasticity_plane.plane import ElasticityPlane;"
                 "print(json.dumps({'version': p.__version__, 'build': __import__('pln05_elasticity_plane.plane', fromlist=['x']).BUILD}))"]
        steps += [[vpy, "-m", "pip", "install", "--no-index", "--no-deps", str(whl)], smoke,
                  [vpy, "-m", "pln05_elasticity_plane", "version"],
                  [vpy, "-m", "pip", "uninstall", "-y", "pln05-elasticity-plane"],
                  [vpy, "-m", "pip", "install", "--no-index", "--no-deps", str(whl)], smoke]
        rc_all = 0
        for s in steps:
            rc, out, _ = run(s, cwd=d)
            log.append(f"$ {' '.join(s)}\n{out}")
            rc_all |= rc
        ci.record("clean_install", rc_all, "\n".join(log), 0)
        if prev_whl is None:
            ci.record("rollback_drill", 1, "previous wheel unavailable", 0, reason="no previous release artifact")
            return
        meta = [vpy, "-c", "import importlib.metadata as m; print(m.version('pln05-elasticity-plane'))"]
        log, rc_all, seen = [], 0, []
        for s in ([vpy, "-m", "pip", "install", "--no-index", "--no-deps", "--force-reinstall", str(prev_whl)], meta,
                  [vpy, "-m", "pip", "install", "--no-index", "--no-deps", "--upgrade", str(whl)], meta, smoke,
                  [vpy, "-m", "pip", "install", "--no-index", "--no-deps", "--force-reinstall", str(prev_whl)], meta):
            rc, out, _ = run(s, cwd=d)
            log.append(f"$ {' '.join(s)}\n{out}")
            rc_all |= rc
            if s is meta:
                seen.append(out.strip().splitlines()[-1] if out.strip() else "?")
        ok = seen == ["4.1.1", VERSION, "4.1.1"]
        ci.record("rollback_drill", 0 if (rc_all == 0 and ok) else 1, "\n".join(log), 0, versions_seen=seen)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "evidence" / VERSION))
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out).resolve()  # subprocesses run from the parent directory
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    ci = CI(out, a.release)
    tier = "release" if a.release else "presubmit"
    started = dt.datetime.now(dt.timezone.utc)
    rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    dirty = bool(subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", ".", ":!evidence"],
                                capture_output=True, text=True).stdout.strip())
    env_ev = {"PLN05_EVIDENCE_DIR": str(out)}

    ci.tool("repo_checks", [PY, str(ROOT / "tools" / "check_repo.py")])
    ci.tool("compile", [PY, "-m", "compileall", "-q", str(ROOT)])
    ci.tool("traceability", [PY, str(ROOT / "tools" / "traceability.py"), "--check"])
    ci.tool("schema_compat", [PY, str(ROOT / "tools" / "schema_compat.py")])
    unit = ["tests/test_controller.py", "tests/test_units.py", "tests/test_plane.py", "tests/test_ops.py", "tests/test_repo.py"]
    ci.tests("unit", unit)
    ci.tests("unit_optimized", unit, optimized=True)
    ci.tests("framework_conformance", ["tests/test_component.py"])
    ci.tests("contract", ["tests/contract/test_fixtures.py"])
    ci.tests("security", ["tests/security/test_adversarial.py"])
    ci.tests("security_optimized", ["tests/security/test_adversarial.py"], optimized=True)
    ci.tests("faults", ["tests/fault/test_faults.py"], env=env_ev)
    ci.tests("fuzz", ["tests/fuzz/test_fuzz.py", "tests/fuzz/test_multi_instance.py"],
             env={"PLN05_FUZZ_ITERS": "20000" if a.release else "2000", "PLN05_MULTI_SEEDS": "400" if a.release else "60"})
    ci.tests("concurrency", ["tests/concurrency/test_concurrency.py"])
    ci.tests("compatibility", ["tests/compatibility/test_compat.py"])
    ci.tests("soak", ["tests/scale/test_soak.py"], env={**env_ev, "PLN05_SOAK_DECISIONS": "200000" if a.release else "60000",
                                                         "PLN05_FLEET_SCOPES": "10000" if a.release else "5000"})
    ci.tool("bench", [PY, str(ROOT / "benchmarks" / "bench.py"), "--out", str(out / "bench.json")])
    ci.tool("perf_gate", [PY, str(ROOT / "ci" / "performance_gate.py"), str(out / "bench.json"),
                          "--tier", tier, "--out", str(out / "perf_gate.json")])
    dist = out / "dist"
    rc1, o1, d1 = run([PY, str(ROOT / "tools" / "build_release.py"), "--out", str(dist)])
    rc2, o2, d2 = run([PY, str(ROOT / "tools" / "build_release.py"), "--out", str(out / "dist_rebuild"), "--no-sign"])
    same = rc1 == rc2 == 0 and all(
        (dist / n).read_bytes() == (out / "dist_rebuild" / n).read_bytes()
        for n in ("SHA256SUMS",) if (dist / n).exists())
    ci.record("package_reproducible", 0 if same else 1, o1 + "\n---\n" + o2, d1 + d2)
    shutil.rmtree(out / "dist_rebuild", ignore_errors=True)
    prev = None
    with tempfile.TemporaryDirectory() as d:
        base = subprocess.run(["git", "-C", str(ROOT), "rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True).stdout.split()
        if base:
            tree = pathlib.Path(d) / "pln05_elasticity_plane"
            subprocess.run(["git", "clone", "-q", str(ROOT), str(tree)], check=True)
            subprocess.run(["git", "-C", str(tree), "checkout", "-q", base[0]], check=True)
            rc, o, _ = run([PY, str(ROOT / "tools" / "build_release.py"), "--root", str(tree), "--out",
                            str(out / "prev_dist"), "--version", "4.1.1", "--no-sign"])
            prev = next((out / "prev_dist").glob("*.whl"), None) if rc == 0 else None
        clean_install(ci, dist, prev)
    shutil.rmtree(out / "prev_dist", ignore_errors=True)
    ci.tool("mc_status", [PY, str(ROOT / "tools" / "mc_status.py"), "--out", str(out / "MC_STATUS.json"),
                          "--annotate", str(out / "CHECKLIST_EXECUTED.md")])
    shutil.copy(ROOT / "traceability" / "requirements.json", out / "TRACEABILITY_SNAPSHOT.json")

    if a.release:
        for r in ci.results.values():
            if r.get("skipped") and r.get("mandatory", True):
                r["result"] = "FAIL"
                r["reason"] = "mandatory checks skipped in release tier"
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json")
    digests = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    bundle = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(digests.items())).encode()).hexdigest()
    manifest = {
        "schema": "PLN05_EVIDENCE/1", "package": "pln05-elasticity-plane", "version": VERSION, "tier": tier,
        "source_revision": rev, "source_dirty": dirty, "build_id": f"{VERSION}+g{rev[:12]}",
        "started": started.isoformat(), "finished": dt.datetime.now(dt.timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                        "system": platform.system(), "machine": platform.machine(), "release": platform.release()},
        "results": ci.results, "files": digests, "bundle_sha256": bundle,
        "sbom": "dist/sbom.cdx.json", "provenance": "dist/provenance.intoto.json",
        "waivers": json.loads((ROOT / "governance" / "waivers.json").read_text())["waivers"],
        "approver_roles_required": ["pln05.release-approver", "pln05.service-owner"],
        "schemas": __import__("json").loads(run([PY, "-m", "pln05_elasticity_plane", "schemas"])[1]),
        "status_vocabulary": ["PASS", "FAIL"], "skips_are": "never PASS in the release tier",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    fails = [k for k, r in ci.results.items() if r["result"] != "PASS"]
    print(json.dumps({"tier": tier, "fail": fails, "bundle_sha256": bundle}, indent=1))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
