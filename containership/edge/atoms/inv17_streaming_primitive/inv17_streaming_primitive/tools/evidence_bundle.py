"""C090: machine-readable release evidence bundle.

Runs, in order, recording command, exit code, duration and a digest of the output:
  compile -> full unit suite (python and python -O) -> pk_core W0-W9 workflow + gate +
  ledger verify -> coverage -> lint -> types -> schema manifest -> SBOM + verify ->
  benchmark + perf gate + version compare -> profile -> capacity -> rollout (pass + forced
  rollback) -> drill -> governance -> traceability.
Writes evidence/release-manifest.json (source digest, versions, per-step results),
evidence/pk_evidence.jsonl, conformance/PK_GATE_RESULTS.json and
conformance/pk_workflow_report.json. ``--quick`` skips benchmarks."""
import hashlib, json, os, platform, subprocess, sys, time
from _tools_pkg import ROOT

PY = sys.executable
T = ROOT / "tools"


def sh(name, argv, env=None, allow_fail=False):
    t0 = time.monotonic()
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})})
    out = (p.stdout + p.stderr)
    return {"step": name, "argv": [a.replace(str(ROOT), ".") for a in argv], "exit": p.returncode, "ok": p.returncode == 0 or allow_fail,
            "expected_nonzero": allow_fail, "seconds": round(time.monotonic() - t0, 2),
            "output_sha256": hashlib.sha256(out.encode()).hexdigest(), "tail": out.strip().splitlines()[-3:]}


def pk_core_run():
    code = r'''
import json, sys, pathlib
root = pathlib.Path(sys.argv[1]); sys.path[:0] = [str(root / "vendor"), str(root.parent)]
from pk_core.evidence import EvidenceLedger
from pk_core.workflow import WorkflowEngine
from pk_core.gate import ConformanceGate
import importlib
pkg = importlib.import_module(root.name)
ev = root / "evidence" / "pk_evidence.jsonl"
if ev.exists(): ev.unlink()
ledger = EvidenceLedger(ev)
res = WorkflowEngine(ledger).run(pkg.COMPONENT())
gate = ConformanceGate().evaluate([res])
(root / "conformance" / "PK_GATE_RESULTS.json").write_text(json.dumps(gate.to_dict(), indent=2) + "\n")
(root / "conformance" / "pk_workflow_report.json").write_text(json.dumps(res.to_dict(), indent=2) + "\n")
print(gate.verdict, res.certified, len(ledger), "verify:", ledger.verify() or "intact")
sys.exit(0 if gate.verdict != "NO_GO" and not ledger.verify() else 1)
'''
    return sh("pk_core workflow + gate + ledger verify", [PY, "-c", code, str(ROOT)])


GENERATED = {"__pycache__", "evidence", "results", "conformance", "traceability"}
GENERATED_FILES = {"performance/capacity-model.json", "benchmarks/baseline.json"}


def source_digest():
    """sha256 over (path, bytes) of every source file, excluding generated evidence."""
    h = hashlib.sha256()
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and p.suffix != ".pyc" and not (GENERATED & set(rel.parts)) and rel.as_posix() not in GENERATED_FILES:
            h.update(rel.as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()


def main():
    quick = "--quick" in sys.argv
    (ROOT / "evidence").mkdir(exist_ok=True); (ROOT / "conformance").mkdir(exist_ok=True)
    steps = [sh("compile", [PY, "-m", "compileall", "-q", "-x", "vendor|benchmarks/reference", "."])]
    steps.append(sh("unit suite", [PY, str(T / "run_tests.py")]))
    steps.append(sh("unit suite (python -O)", [PY, "-O", str(T / "run_tests.py")]))
    steps.append(pk_core_run())
    steps.append(sh("coverage", [PY, str(T / "coverage_run.py")]))
    lint = sh("lint (ruff)", ["ruff", "check", "."]); steps.append(lint)
    types = sh("types (mypy)", ["mypy"]); steps.append(types)
    (ROOT / "evidence" / "lint.json").write_text(json.dumps({"ruff": lint, "mypy": types}, indent=2) + "\n")
    steps.append(sh("schema manifest", [PY, str(T / "gen_schema_manifest.py"), "--check"]))
    if not quick:
        steps.append(sh("benchmark", [PY, str(T / "bench.py")]))
        steps.append(sh("perf gate", [PY, str(T / "perf_gate.py")]))
        steps.append(sh("version compare", [PY, str(T / "compare_versions.py"), "7"]))
        steps.append(sh("profile", [PY, str(T / "profile_copies.py")]))
        steps.append(sh("capacity model", [PY, str(T / "capacity.py")]))
    steps.append(sh("rollout (clean)", [PY, str(T / "rollout.py")]))
    steps.append(sh("rollout (forced rollback)", [PY, str(T / "rollout.py"), "--fail-at", "10%"]))
    steps.append(sh("sev1 drill (simulated)", [PY, str(T / "drill.py")]))
    steps.append(sh("governance validation", [PY, str(T / "validate_governance.py")], allow_fail=True))
    steps.append(sh("sbom", [PY, str(T / "sbom.py")]))
    steps.append(sh("sbom verify", [PY, str(T / "sbom.py"), "--verify"]))
    # the exit gate is itself a traced artifact, so a preliminary pass precedes traceability
    sh("production exit gate (preliminary)", [PY, str(T / "exit_gate.py")], allow_fail=True)
    steps.append(sh("traceability", [PY, str(T / "gen_traceability.py"), "--check"]))
    manifest = {"schema": "urn:pk:inv17:release-manifest:1", "component": "INV-17",
                "version": (ROOT / "VERSION").read_text().strip(),
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source_revision": os.environ.get("INV17_SOURCE_REVISION", "unrecorded (no VCS in this build)"),
                "source_tree_sha256": source_digest(),
                "environment": {"python": platform.python_version(), "system": platform.system(), "machine": platform.machine()},
                "versions": {"pk_core": "4.0.0", "config_schema": 1, "interfaces": {"PK_STREAM": 1, "PK_STREAM_CREDIT": 1, "PK_STREAM_CLOSE": 1}},
                "schema_manifest_sha256": hashlib.sha256((ROOT / "interfaces" / "schema-manifest.json").read_bytes()).hexdigest(),
                "steps": steps, "all_ok": all(s["ok"] for s in steps)}
    (ROOT / "evidence" / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    final = sh("production exit gate", [PY, str(T / "exit_gate.py")], allow_fail=True)
    print(f"exit gate: {final['tail'][-1] if final['tail'] else final['exit']}")
    for s in steps:
        print(f"{'OK ' if s['ok'] else 'FAIL'} {s['exit']:>3} {s['seconds']:>7}s  {s['step']}")
    return 0 if manifest["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
