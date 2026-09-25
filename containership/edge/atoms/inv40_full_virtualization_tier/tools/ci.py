"""Single CI entry point: tests (normal + -O), install check, fuzz, bench,
dependency lock, SBOM, manifest, traceability, gate -> machine-readable
evidence bound to the artifact digest (REPO-006, INV-40-C090).

Declared lanes: a skip whose reason starts with ``LANE:`` or which belongs to
the pk_core integration tests is reported NOT_RUN for that lane; any other
skip is a *mandatory skip* and fails the run.  Exit: 0 PASS, 1 FAIL,
3 INCOMPLETE (a declared lane did not run).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "tests"))
EV = PKG / "evidence"


class Rec(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.passed = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.append(test.id())


def lane_of(test, reason: str) -> str | None:
    if reason.startswith("LANE:"):
        return reason[5:].split()[0].strip(" -")
    if "pk_core" in reason or "pk_core" in test.id() or "test_component" in test.id():
        return "pk_core"
    return None


def run_tests() -> dict:
    suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), top_level_dir=str(PKG / "tests"))
    with open(os.devnull, "w") as dn:
        r = unittest.TextTestRunner(stream=dn, resultclass=Rec, verbosity=0).run(suite)
    lanes, mandatory = {}, []
    for t, reason in r.skipped:
        ln = lane_of(t, reason)
        if ln:
            lanes.setdefault(ln, []).append(t.id())
        else:
            mandatory.append({"test": t.id(), "reason": reason})
    return {"ran": r.testsRun, "passed": len(r.passed), "failed": len(r.failures) + len(r.errors),
            "failures": [t.id() for t, _ in r.failures + r.errors], "skipped_mandatory": mandatory,
            "lanes_not_run": {k: {"status": "NOT_RUN", "tests": v} for k, v in lanes.items()}}


def run_optimized() -> dict:
    p = subprocess.run([sys.executable, "-O", "-B", "-m", "unittest", "discover", "-s", "tests"], cwd=PKG,
                       capture_output=True, text=True, timeout=600)
    tail = p.stderr.strip().splitlines()[-1] if p.stderr.strip() else ""
    return {"returncode": p.returncode, "summary": tail}


def install_check() -> dict:
    """Build a wheel from declared metadata only, install it into a scratch
    target, and import the runtime + fvt layer from the installed copy."""
    py = os.environ.get("INV40_BUILD_PYTHON", sys.executable)
    for junk in ("build", "inv40_full_virtualization_tier.egg-info"):
        subprocess.run(["rm", "-rf", str(PKG / junk)], check=False)
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run([py, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
                            "-w", d, str(PKG)], capture_output=True, text=True, timeout=300)
        for junk in ("build", "inv40_full_virtualization_tier.egg-info"):  # setuptools writes into the source tree
            subprocess.run(["rm", "-rf", str(PKG / junk)], check=False)
        wheels = list(pathlib.Path(d).glob("*.whl"))
        if p.returncode != 0 or not wheels:
            return {"status": "FAIL", "build_python": py, "wheel": None, "detail": p.stderr.strip()[-600:]}
        tgt = pathlib.Path(d) / "site"
        q = subprocess.run([py, "-m", "pip", "install", "--no-deps", "--no-index", "-q", "--target", str(tgt),
                            str(wheels[0])], capture_output=True, text=True, timeout=300)
        probe = ("import inv40_full_virtualization_tier as m, inv40_full_virtualization_tier.fvt.service as s, "
                 "inv40_full_virtualization_tier.fvt.schema as sc; assert m.__version__=='4.3.0'; "
                 "sc.load('PK_FULL_VM_CONFIG.v1'); print(s.VERSION)")
        r = subprocess.run([py, "-I", "-c", f"import sys; sys.path.insert(0, {str(tgt)!r}); {probe}"],
                           capture_output=True, text=True, timeout=120, cwd=d)
        ok = q.returncode == 0 and r.returncode == 0 and r.stdout.strip() == "4.3.0"
        return {"status": "PASS" if ok else "FAIL", "build_python": py, "wheel": wheels[0].name,
                "wheel_sha256": hashlib.sha256(wheels[0].read_bytes()).hexdigest(),
                "import_from_installed": r.stdout.strip() or r.stderr.strip()[-400:]}


def write(name, doc):
    EV.mkdir(exist_ok=True)
    (EV / name).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(EV / "ci_run.json"))
    ap.add_argument("--lane", default="default")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--fuzz-iterations", type=int, default=40000)
    a = ap.parse_args(argv)
    sys.dont_write_bytecode = True

    import build_traceability  # noqa: E402  (tools/ on path below)
    counts = build_traceability.main()
    tests = run_tests()
    opt = run_optimized()
    import fuzz
    fz = fuzz.run(a.fuzz_iterations)
    write("fuzz.json", fz)
    import bench
    bn = bench.run(300)
    write("bench.json", bn)
    th = json.loads((PKG / "ci/bench_thresholds.json").read_text())
    regress = [f"{k}={bn[k]} > {v}" for k, v in th["max"].items() if bn.get(k) is not None and bn[k] > v]
    inst = install_check()
    lock = {"schema": "PK_FULL_VM_LOCK/1", "runtime_dependencies": [], "optional": {"pk_core": "UNPINNED"},
            "sha256_of_empty_set": hashlib.sha256(b"[]").hexdigest()}
    write("deps.lock.json", lock)
    from fvt import compat, gate, integrity
    write("sbom.cdx.json", {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
                            "metadata": {"component": {"type": "library", "name": "inv40-full-virtualization-tier",
                                                       "version": "4.3.0", "licenses": [{"license": {"name": "UNLICENSED (owner decision pending)"}}]}},
                            "components": [], "externalReferences": [{"type": "other", "comment": "host prerequisites: linux-kvm, qemu-system-x86_64 (not bundled)"}]})
    man = integrity.manifest(PKG)
    text = "".join(f"{h}  {p}\n" for h, p in man)
    (PKG / "MANIFEST.sha256").write_text(text)
    digest = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
    lanes = dict(tests["lanes_not_run"])
    pk = compat.check_pk_core()
    status = "FAIL" if (tests["failed"] or tests["skipped_mandatory"] or opt["returncode"] or fz["unclassified_crashes"]
                        or inst["status"] != "PASS") else ("INCOMPLETE" if lanes else "PASS")
    run = {"schema": "PK_FULL_VM_CI/1", "status": status, "artifact_digest": digest, "files_in_manifest": len(man),
           "python": platform.python_version(), "platform": platform.platform(), "lane": a.lane,
           "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
           "tests": {k: tests[k] for k in ("ran", "passed", "failed", "failures")},
           "failed": tests["failed"], "skipped_mandatory": tests["skipped_mandatory"], "lanes": lanes,
           "optimized_run": opt, "install_check": inst, "fuzz": {"iterations": fz["iterations"], "unclassified_crashes": fz["unclassified_crashes"]},
           "bench": {"p99_create_ms": bn["p99_create_ms"], "p99_boot_ms": bn["p99_boot_ms"],
                     "thresholds_status": th["status"], "regressions": regress},
           "pk_core": pk, "traceability": counts}
    pathlib.Path(a.out).write_text(json.dumps(run, indent=1, sort_keys=True) + "\n")
    g = gate.evaluate(digest, bench_path=EV / "bench.json", thresholds_path=PKG / "ci/bench_thresholds.json")
    write("gate.json", g)
    print(json.dumps({"status": status, "artifact_digest": digest, "tests": run["tests"], "lanes": list(lanes),
                      "gate": g["verdict"], "gate_reasons": len(g["reasons"]), "traceability": counts}, indent=1))
    if a.gate and g["verdict"] != "GO":
        return 1
    return {"PASS": 0, "FAIL": 1, "INCOMPLETE": 3}[status]


if __name__ == "__main__":
    sys.path.insert(0, str(PKG / "tools"))
    sys.exit(main())
