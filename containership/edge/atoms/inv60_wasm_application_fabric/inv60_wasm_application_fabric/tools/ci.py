"""M05 - the single CI/release entry point (also used by .github/workflows/ci.yml).

Steps: compile -> generated-doc drift -> fixture determinism -> unit/contract/security/
resilience/fuzz tests (+ pk_core conformance incl. python -O) -> Node cross-language
fixtures -> secret scan -> pk_core workflow+gate -> benchmark regression -> SBOM ->
traceability -> acceptance evidence -> exit gate -> seal. A skipped release-critical
test is a failure under --strict; a missing prerequisite is never reported as a pass."""
import compileall, json, pathlib, subprocess, sys, time, unittest
PKG = pathlib.Path(__file__).resolve().parents[1]
REL = PKG / "release"; REL.mkdir(exist_ok=True)
sys.path.insert(0, str(PKG.parent)); sys.path.insert(0, str(PKG / "tests")); sys.dont_write_bytecode = True
STRICT = "--strict" in sys.argv
CRITICAL_SKIP_OK = {"test_security.Ed25519Vectors.test_cross_check_with_cryptography_when_present"}  # optional cross-check
steps = []


def step(name, ok, detail=""):
    steps.append({"step": name, "ok": bool(ok), "detail": detail}); print(("PASS " if ok else "FAIL ") + name, detail)


def py(*args):
    return subprocess.run([sys.executable, "-B", *map(str, args)], capture_output=True, text=True, cwd=PKG)


step("compile", compileall.compile_dir(str(PKG), quiet=1, legacy=False, force=True) and compileall.compile_dir(str(PKG.parent / "pk_core"), quiet=1, force=True))
for p in list(PKG.rglob("__pycache__")) + list((PKG.parent / "pk_core").rglob("__pycache__")):
    import shutil; shutil.rmtree(p, ignore_errors=True)
r = py(PKG / "tools/gen_docs.py", "--check"); step("generated_docs_current", r.returncode == 0, r.stdout.strip())
before = (PKG / "fixtures/INDEX.json").read_bytes()
r = py(PKG / "tools/gen_fixtures.py"); step("fixtures_deterministic", r.returncode == 0 and before == (PKG / "fixtures/INDEX.json").read_bytes())


class Collector(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.outcomes = {}
    def _id(self, t):
        return t.id().replace("__main__.", "")
    def addSuccess(self, t): super().addSuccess(t); self.outcomes[self._id(t)] = "passed"
    def addFailure(self, t, e): super().addFailure(t, e); self.outcomes[self._id(t)] = "failure"
    def addError(self, t, e): super().addError(t, e); self.outcomes[self._id(t)] = "error"
    def addSkip(self, t, r): super().addSkip(t, r); self.outcomes[self._id(t)] = "skipped"


t0 = time.time()
suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), pattern="test_*.py", top_level_dir=str(PKG / "tests"))
runner = unittest.TextTestRunner(resultclass=Collector, verbosity=0, stream=open("/dev/null" if sys.platform != "win32" else "NUL", "w"))
res = runner.run(suite)
oc = res.outcomes
crit = sorted(k for k, v in oc.items() if v == "skipped" and k not in CRITICAL_SKIP_OK)
summary = {"total": len(oc), "passed": sum(v == "passed" for v in oc.values()), "failed": sum(v == "failure" for v in oc.values()),
           "errors": sum(v == "error" for v in oc.values()), "skipped": sum(v == "skipped" for v in oc.values()),
           "critical_skipped": len(crit), "critical_skipped_ids": crit, "seconds": round(time.time() - t0, 1),
           "python": sys.version.split()[0]}
(REL / "TEST_RESULTS.json").write_text(json.dumps({"schema": "inv60.test-results/1", "summary": summary, "tests": oc,
    "failures": [str(t) + "\n" + tb for t, tb in res.failures + res.errors]}, indent=1))
step("tests", summary["failed"] == 0 and summary["errors"] == 0 and (not STRICT or not crit), json.dumps({k: summary[k] for k in ("total", "passed", "failed", "errors", "skipped", "critical_skipped")}))
ro = subprocess.run([sys.executable, "-B", "-O", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"], capture_output=True, text=True, cwd=PKG / "tests")
step("tests_optimized_mode", ro.returncode == 0, (ro.stderr.strip().splitlines() or [""])[-1])
node = subprocess.run(["node", str(PKG / "fixtures/validate.mjs")], capture_output=True, text=True) if __import__("shutil").which("node") else None
step("fixtures_node_consumer", bool(node and node.returncode == 0), node.stdout.strip() if node else "node missing (not a pass)")
from inv60_wasm_application_fabric.fabric.config import scan_text_for_secrets
hits = [str(p.relative_to(PKG)) for p in PKG.rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".md", ".yml", ".toml", ".txt")
        and "tests" not in p.parts and p.name != "config.py" and scan_text_for_secrets(p.read_text(errors="ignore"))]
step("secret_scan", not hits, str(hits))
r = py(PKG / "tools/run_conformance.py"); step("pk_core_workflow_gate", r.returncode == 0, r.stdout.strip())
r = py(PKG / "tools/bench.py", "--check"); step("benchmark_regression", r.returncode == 0, r.stdout.strip()[-200:])
r = py(PKG / "tools/gen_sbom.py"); step("sbom", r.returncode == 0, r.stdout.strip())
r = py(PKG / "tools/gen_traceability.py"); step("traceability", r.returncode == 0, (r.stdout + r.stderr).strip()[-300:])
r = py(PKG / "tools/build_evidence.py"); step("acceptance_evidence", r.returncode == 0, r.stdout.strip())
r = py(PKG / "tools/exit_gate.py"); gate = json.loads(r.stdout) if r.returncode == 0 else {}
steps.append({"step": "exit_gate", "ok": r.returncode == 0, "detail": gate, "note": "verdict reported, not asserted"})
print("INFO exit_gate", gate)
(REL / "CI_REPORT.json").write_text(json.dumps({"schema": "inv60.ci/1", "strict": STRICT, "steps": steps}, indent=1))
r = py(PKG / "tools/seal.py"); print(r.stdout.strip())
sys.exit(0 if all(s["ok"] for s in steps) else 1)
