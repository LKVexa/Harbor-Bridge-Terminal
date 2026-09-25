"""Release evidence generator (M14, M15, M29-M31, M45-M48 inputs to M52).

    python inv09_portable_compute_isa/tools/evidence.py tests|fuzz|bench|soak|static|sbom|buildmeta|all [args]

Each step writes evidence/<name>.json bound to the release digest (hash of all
source files), so M52 can refuse stale evidence.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.metadata as md
import json
import os
import pathlib
import platform
import subprocess
import sys
import time
import tracemalloc
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "tests"))

SOURCE_GLOBS = ("*.py", "prod/*.py", "tests/*.py", "tools/*.py", "schemas/*.json", "docs/**/*.md",
                "ops/*", "pyproject.toml", "requirements.lock", "VERSION", "OWNERS.yaml", "waivers/*.json")


def source_files() -> list[pathlib.Path]:
    out = set()
    for g in SOURCE_GLOBS:
        out.update(p for p in ROOT.glob(g) if p.is_file() and "__pycache__" not in p.parts)
    return sorted(out)


def release_digest() -> str:
    h = hashlib.sha256()
    for p in source_files():
        h.update(p.relative_to(ROOT).as_posix().encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()


def write(name: str, doc: dict) -> None:
    EV.mkdir(exist_ok=True)
    doc = {"release_digest": release_digest(), "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           **doc}
    (EV / f"{name}.json").write_text(json.dumps(doc, indent=1, sort_keys=True))
    print(f"wrote evidence/{name}.json")


def step_tests(optimized: bool = False) -> None:
    def run(opt):
        cmd = [sys.executable] + (["-O"] if opt else []) + ["-m", "unittest", "discover", "-s",
                                                              str(ROOT / "tests"), "-p", "test_*.py", "-v"]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT.parent), timeout=600)
        lines = r.stderr.splitlines()
        names = [ln for ln in lines if " ... " in ln]
        return {"mode": "optimized(-O)" if opt else "normal", "returncode": r.returncode,
                "summary": [ln for ln in lines if ln.startswith(("Ran ", "OK", "FAILED"))],
                "passed": sum(ln.endswith("ok") for ln in names),
                "skipped": [ln for ln in names if "skipped" in ln],
                "failed": [ln for ln in names if ln.endswith(("FAIL", "ERROR"))]}
    write("tests", {"schema": "PK_TEST_RESULTS/1", "runs": [run(False), run(True)]})


def step_fuzz(seeds: list[int], n: int) -> None:
    import wasmgen
    from inv09_portable_compute_isa.prod import differential, fuzz
    prev = json.loads((EV / "fuzz_campaign.json").read_text()) if (EV / "fuzz_campaign.json").exists() else None
    if prev and prev.get("release_digest") != release_digest():
        prev = None
    agg = prev or {"schema": "PK_FUZZ_CAMPAIGN/1", "runs": [], "executions": 0, "crashes": 0,
                   "nondeterministic": 0, "differential": {"total": 0, "agree": 0, "disagreements": {},
                                                           "critical": 0, "examples": []}}
    for seed in seeds:
        if any(r["seed"] == seed for r in agg["runs"]):
            continue
        buf = []
        rep = fuzz.run(seed, list(wasmgen.seeds().values()), n, on_input=lambda nm, m: buf.append((nm, m)))
        agg["runs"].append({k: v for k, v in rep.items() if k != "crashes"} | {"crash_count": len(rep["crashes"])})
        agg["executions"] += rep["executions"]
        agg["crashes"] += len(rep["crashes"])
        agg["nondeterministic"] += len(rep["nondeterministic"])
        if rep["crashes"]:
            (EV / "crashes").mkdir(exist_ok=True)
            for c in rep["crashes"]:
                (EV / "crashes" / f"{c['name']}.hex").write_text(c["hex"])
        if differential.node_available():
            d = differential.run(buf)
            D = agg["differential"]
            D["total"] += d["total"]
            D["agree"] += d["agree"]
            D["critical"] += d["critical"]
            for k, v in d["disagreements"].items():
                D["disagreements"][k] = D["disagreements"].get(k, 0) + v
            D["examples"] = (D["examples"] + d["examples"])[:40]
            D["reference"] = d["reference"]
    agg.pop("release_digest", None)
    agg.pop("generated_at", None)
    write("fuzz_campaign", agg)


def step_bench() -> None:
    from inv09_portable_compute_isa.prod import bench
    r = bench.run(reps=5)
    write("benchmark", r)
    write("perf_gate", bench.gate(r))


def step_soak(seconds: float) -> None:
    import wasmgen
    from inv09_portable_compute_isa.prod import admission, attest, fuzz
    s = attest.Signer("soak")
    g = admission.Gate(signer=s, verifier=attest.Verifier({"soak": s.public_raw()}))
    tracemalloc.start()
    t0 = time.time()
    n = 0
    samples = []
    seeds = list(wasmgen.seeds().values())
    it = fuzz.inputs(4242, seeds, 10**9)
    while time.time() - t0 < seconds:
        name, m = next(it)
        v = g.validate(m, profile="permissive", engine="reference-engine")
        if v["outcome"] == "accept":
            g.execute(g.admit(m, v["attestation"], profile="permissive", engine="reference-engine"), len)
        n += 1
        if n % 2000 == 0:
            samples.append(tracemalloc.get_traced_memory()[0])
    cur, peak = tracemalloc.get_traced_memory()
    growth = (samples[-1] - samples[len(samples) // 2]) if len(samples) > 4 else None
    write("soak", {"schema": "PK_SOAK/1", "seconds": seconds, "validations": n, "rate_per_s": round(n / seconds),
                   "traced_current_bytes": cur, "traced_peak_bytes": peak,
                   "second_half_growth_bytes": growth, "cache_entries": len(g.cache),
                   "audit_events": len(g.audit.events), "health": g.health()["status"],
                   "note": "single-process soak; fleet-scale (M31) soak not executed"})


DANGEROUS = {"eval", "exec", "compile", "__import__"}
DANGEROUS_MODS = {"pickle", "marshal", "shelve"}


def step_static() -> None:
    findings = []
    files = [p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts]
    for p in files:
        src = p.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            findings.append({"file": str(p.relative_to(ROOT)), "sev": "high", "msg": f"syntax: {e}"})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in DANGEROUS:
                findings.append({"file": str(p.relative_to(ROOT)), "line": node.lineno, "sev": "high",
                                 "msg": f"call to {node.func.id}"})
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for m in mods:
                    if m.split(".")[0] in DANGEROUS_MODS:
                        findings.append({"file": str(p.relative_to(ROOT)), "line": node.lineno, "sev": "high",
                                         "msg": f"unsafe deserialisation module {m}"})
            if isinstance(node, ast.keyword) and node.arg == "shell" and getattr(node.value, "value", False) is True:
                findings.append({"file": str(p.relative_to(ROOT)), "line": node.lineno, "sev": "high",
                                 "msg": "subprocess shell=True"})
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append({"file": str(p.relative_to(ROOT)), "line": node.lineno, "sev": "medium",
                                 "msg": "bare except"})
            if isinstance(node, ast.Assert) and "prod" in p.parts:
                findings.append({"file": str(p.relative_to(ROOT)), "line": node.lineno, "sev": "medium",
                                 "msg": "assert used for control flow in prod (stripped under -O)"})
    tools = {t: bool(subprocess.run(["which", t], capture_output=True).returncode == 0)
             for t in ("ruff", "mypy", "bandit", "pip-audit")}
    write("static_scan", {"schema": "PK_STATIC_SCAN/1", "files": len(files), "findings": findings,
                          "high": sum(f["sev"] == "high" for f in findings),
                          "external_tools_available": tools,
                          "note": "stdlib AST scan; ruff/mypy/bandit/pip-audit were not installable (no PyPI access)"})


def _dist(name: str) -> dict:
    try:
        d = md.distribution(name)
        lic = d.metadata.get("License-Expression") or d.metadata.get("License") or ""
        return {"type": "library", "name": name, "version": d.version,
                "licenses": [{"license": {"name": lic.splitlines()[0][:80] if lic else "UNKNOWN"}}],
                "purl": f"pkg:pypi/{name}@{d.version}"}
    except md.PackageNotFoundError:
        return {"type": "library", "name": name, "version": "NOT-INSTALLED"}


def step_sbom() -> None:
    comps = [_dist("cryptography"), _dist("cffi"), _dist("pycparser"), _dist("jsonschema")]
    node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    comps.append({"type": "application", "name": "node", "version": node or "absent",
                  "description": "test-only differential reference (V8 WebAssembly.validate); not shipped"})
    files = [{"type": "file", "name": p.relative_to(ROOT).as_posix(),
              "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]}
             for p in source_files() if p.suffix == ".py" and "tests" not in p.parts and "tools" not in p.parts]
    write("sbom.cdx", {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
                       "metadata": {"component": {"type": "library", "name": "inv09-portable-compute-isa",
                                                  "version": (ROOT / "VERSION").read_text().strip()}},
                       "components": comps + files})


def step_buildmeta() -> None:
    sums = []
    for p in source_files():
        sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}")
    (ROOT / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    write("build_metadata", {"schema": "PK_BUILD_METADATA/1", "version": (ROOT / "VERSION").read_text().strip(),
                             "python": sys.version, "implementation": platform.python_implementation(),
                             "platform": platform.platform(), "machine": platform.machine(),
                             "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
                             "file_count": len(sums),
                             "reproducibility": "pure-Python sources; release digest is order-independent "
                                                "over relative path + content hash. Wheel build not executed."})


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "tests":
        step_tests()
    elif cmd == "fuzz":
        step_fuzz([int(x) for x in sys.argv[2].split(",")], int(sys.argv[3]))
    elif cmd == "bench":
        step_bench()
    elif cmd == "soak":
        step_soak(float(sys.argv[2]))
    elif cmd == "static":
        step_static()
    elif cmd == "sbom":
        step_sbom()
    elif cmd == "buildmeta":
        step_buildmeta()
    elif cmd == "digest":
        print(release_digest())
