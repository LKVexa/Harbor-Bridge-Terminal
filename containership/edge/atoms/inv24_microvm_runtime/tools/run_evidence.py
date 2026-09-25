"""MC-054: produce machine-readable evidence for the exact source bytes.

Outputs (under evidence/):
  test-results.json     every test id -> PASS | FAIL | NOT_TESTED (skips are never PASS)
  optimized-mode.json   the full suite under ``python -O``
  benchmarks.json       control-path latency distributions + regression verdicts
  sbom.json             every shipped file with SHA-256 (stdlib-only package)
  artifact-digests.json source tree digest + key file digests
  evidence-ledger.jsonl one hash-chained PK_MICROVM_EVIDENCE/1 record per component
Also regenerates traceability/TRACEABILITY.json and release/COMPONENT_STATUS.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import components  # noqa: E402

EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "evidence", ".pytest_cache"}
CHECKLIST = ROOT / "docs/checklist/INV24_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md"
GENERATED = {"traceability/TRACEABILITY.json", "release/COMPONENT_STATUS.json", "docs/CLOSURE_REPORT.md"}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def shipped_files() -> list[pathlib.Path]:
    out = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not EXCLUDE_DIRS & set(rel.parts) and not p.name.endswith((".pyc", ".tmp")):
            out.append(p)
    return out


def source_digest(exclude_generated: bool = True) -> str:
    h = hashlib.sha256()
    for p in shipped_files():
        rel = p.relative_to(ROOT).as_posix()
        if exclude_generated and rel in GENERATED:
            continue
        h.update(rel.encode() + b"\0" + sha_file(p).encode() + b"\n")
    return h.hexdigest()


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", ".", ":!evidence", ":!traceability", ":!release/COMPONENT_STATUS.json", ":!docs/CLOSURE_REPORT.md"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "") if out.returncode == 0 else "NO_GIT"
    except (OSError, subprocess.SubprocessError):
        return "NO_GIT"


class Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records: dict[str, dict] = {}
        self._t0: dict[str, float] = {}

    def startTest(self, test):
        self._t0[test.id()] = time.perf_counter()
        super().startTest(test)

    def _rec(self, test, result, detail=""):
        self.records[test.id()] = {"result": result, "detail": detail[:500],
                                   "ms": round((time.perf_counter() - self._t0.get(test.id(), time.perf_counter())) * 1000, 2)}

    def addSuccess(self, test):
        super().addSuccess(test)
        self._rec(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._rec(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._rec(test, "FAIL", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._rec(test, "NOT_TESTED", reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self._rec(test, "FAIL", self._exc_info_to_string(err, test))


def run_tests() -> dict:
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "inv24_microvm_runtime/tests"), top_level_dir=str(ROOT))
    with open(os.devnull, "w") as devnull:
        runner = unittest.TextTestRunner(stream=devnull, resultclass=Recorder, verbosity=0)
        started = now()
        res = runner.run(suite)
    for test, reason in res.skipped:  # class-level skips never call startTest
        res.records.setdefault(test.id(), {"result": "NOT_TESTED", "detail": reason, "ms": 0})
    counts = {k: sum(1 for r in res.records.values() if r["result"] == k) for k in ("PASS", "FAIL", "NOT_TESTED")}
    return {"started_at": started, "ended_at": now(), "counts": counts, "tests": dict(sorted(res.records.items()))}


def run_optimized() -> dict:
    cmd = [sys.executable, "-O", "-m", "unittest", "discover", "-s", "inv24_microvm_runtime/tests", "-t", "."]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    tail = p.stderr.strip().splitlines()[-3:]
    m = re.search(r"Ran (\d+) tests", p.stderr)
    return {"command": " ".join(cmd[1:]), "returncode": p.returncode, "ran": int(m.group(1)) if m else 0,
            "summary": tail, "result": "PASS" if p.returncode == 0 else "FAIL"}


def run_benchmarks(capture_baseline: bool) -> dict:
    from inv24_microvm_runtime import MicroVM
    from inv24_microvm_runtime.adapters.firecracker import build_plan
    from inv24_microvm_runtime.devices import SerialSpec, VsockSpec
    from inv24_microvm_runtime.perf import gate, host_profile, measure
    from inv24_microvm_runtime.security.identity import TokenAuthority
    from inv24_microvm_runtime.security.keys import Keyring, StaticKeyProvider
    from inv24_microvm_runtime.tests.unit.test_admission_resilience import Harness

    auth = TokenAuthority(Keyring(StaticKeyProvider({"b": b"k" * 32}), "b"))
    tokens = iter([auth.issue("s", "workload", {"microvm:create"}) for _ in range(3000)])
    vm = MicroVM("b", "t", devices={"serial", "virtio-vsock"})
    specs = [VsockSpec("v0", 3, "/run/v.sock"), SerialSpec()]
    cap = __import__("inv24_microvm_runtime.admission", fromlist=["Capacity"]).Capacity(10**6, 10**6, 10**9, 10**12, 10**4, 10**4)
    h = Harness(cap)
    counter = iter(range(10**7))
    results = {
        "microvm_create_validate": measure(lambda: MicroVM("vm", "t", vcpus=2, memory_mib=256, devices={"serial"})),
        "firecracker_plan_build": measure(lambda: build_plan(vm, specs, kernel_path="/k")),
        "token_verify": measure(lambda: auth.verify(next(tokens)), n=2000, warmup=50),
        "admission_decision": measure(lambda: h.ac.admit(h.req(f"op-bench{next(counter):07d}")), n=300, warmup=20),
    }
    base_path = ROOT / "benchmarks/baseline.json"
    baseline = json.loads(base_path.read_text())["results"] if base_path.exists() else None
    if capture_baseline or baseline is None:
        base_path.write_text(json.dumps({"captured_at": now(), "host": host_profile(), "results": results}, indent=2, sort_keys=True))
        baseline = results
    return {"host": host_profile(), "results": results, "verdicts": gate(results, baseline)}


def parse_checklist() -> dict[str, dict]:
    text = CHECKLIST.read_text()
    out = {}
    for m in re.finditer(r"## (MC-\d{3}) — (.+?)\n\n\*\*Priority:\*\* (P\d).*?\*\*Source checks:\*\* `([^`]*)`.*?\*\*Primary discipline:\*\* ([^\n]+?)\s*\n", text, re.S):
        body = text[m.end():].split("**Closure rule", 1)[0]
        out[m.group(1)] = {"title": m.group(2).strip(), "priority": m.group(3), "controls": [c.strip() for c in m.group(4).split(",")],
                           "discipline": m.group(5).strip(), "items": re.findall(rf"\*\*({m.group(1)}-[IQAE]\d\d)\*\*", body)}
    return out


def match_tests(prefixes: list[str], tests: dict) -> list[str]:
    return sorted(t for t in tests if any(t == p or t.startswith(p + ".") for p in prefixes))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture-baseline", action="store_true")
    args = ap.parse_args()
    ev = ROOT / "evidence"
    ev.mkdir(exist_ok=True)
    version = (ROOT / "inv24_microvm_runtime/VERSION").read_text().strip()
    commit = git_commit()
    tool_versions = {"python": sys.version.split()[0], "platform": platform.platform()}
    env_profile = {"kvm": os.path.exists("/dev/kvm"), "machine": platform.machine(),
                   "profile": "developer-sandbox (no KVM)" if not os.path.exists("/dev/kvm") else "kvm-host"}

    tests = run_tests()
    tests.update(release_version=version, source_commit=commit)
    (ev / "test-results.json").write_text(json.dumps(tests, indent=2, sort_keys=True))
    opt = run_optimized()
    (ev / "optimized-mode.json").write_text(json.dumps(opt, indent=2, sort_keys=True))
    bench = run_benchmarks(args.capture_baseline)
    (ev / "benchmarks.json").write_text(json.dumps(bench, indent=2, sort_keys=True))

    checklist = parse_checklist()
    status, trace = {}, {}
    for mc, meta in checklist.items():
        local, artifacts, prefixes, extra, notes = components.C[mc]
        matched = match_tests(prefixes, tests["tests"])
        results = [tests["tests"][t]["result"] for t in matched]
        local_result = ("NOT_TESTED" if not matched else "FAIL" if "FAIL" in results
                        else "PASS" if all(r == "PASS" for r in results) else "PARTIAL")
        missing = [a for a in artifacts if not (ROOT / a).exists()]
        blockers = [components.OWNER_BLOCKER, *extra] + ([f"missing artifacts: {missing}"] if missing else [])
        status[mc] = {"title": meta["title"], "priority": meta["priority"], "status": "BLOCKED",
                      "local_implementation": local, "local_verification": local_result,
                      "owner": None, "approver": None, "blocked_on": blockers, "notes": notes}
        trace[mc] = {"controls": meta["controls"], "items": meta["items"], "artifacts": artifacts,
                     "artifacts_resolved": not missing, "tests": matched, "evidence": ["evidence/test-results.json"]}
    (ROOT / "traceability").mkdir(exist_ok=True)
    (ROOT / "traceability/TRACEABILITY.json").write_text(json.dumps(
        {"schema": "PK_MICROVM_TRACE/1", "release": version, "components": trace}, indent=2, sort_keys=True))
    (ROOT / "release/COMPONENT_STATUS.json").write_text(json.dumps(
        {"schema": "PK_MICROVM_STATUS_REGISTRY/1", "release": version, "components": status}, indent=2, sort_keys=True))

    files = shipped_files()
    sbom = {"schema": "PK_MICROVM_SBOM/1", "bomFormat": "CycloneDX-like", "release": version,
            "component": {"name": "inv24-microvm-runtime", "version": version},
            "dependencies": [], "note": "stdlib only; Firecracker binaries not bundled",
            "files": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha_file(p), "bytes": p.stat().st_size} for p in files]}
    (ev / "sbom.json").write_text(json.dumps(sbom, indent=2, sort_keys=True))
    digests = {"release_version": version, "source_commit": commit, "source_tree_sha256": source_digest(),
               "checklist_sha256": sha_file(CHECKLIST),
               "firecracker_manifest_sha256": sha_file(ROOT / "artifacts/firecracker/manifest.json"),
               "config_base_sha256": sha_file(ROOT / "config/base.json"),
               "baseline_sha256": sha_file(ROOT / "benchmarks/baseline.json")}
    (ev / "artifact-digests.json").write_text(json.dumps(digests, indent=2, sort_keys=True))

    from inv24_microvm_runtime.schemas import validate
    tr_sha = sha_file(ev / "test-results.json")
    prev = "0" * 64
    lines = []
    for mc in sorted(status):
        rec = {"schema": "PK_MICROVM_EVIDENCE/1", "component_id": mc, "task_id": f"{mc}-LOCAL",
               "control_ids": trace[mc]["controls"], "release_version": version, "source_commit": commit,
               "artifact_digests": {"source_tree_sha256": digests["source_tree_sha256"]},
               "environment_profile": env_profile, "test_or_review_id": trace[mc]["tests"][:50] or None,
               "result": status[mc]["local_verification"] if status[mc]["local_verification"] in {"PASS", "FAIL", "NOT_TESTED"} else "NOT_TESTED",
               "started_at": tests["started_at"], "ended_at": tests["ended_at"], "tool_versions": tool_versions,
               "evidence_path": "evidence/test-results.json", "evidence_sha256": tr_sha,
               "owner": None, "approver": None, "waiver_id": None,
               "notes": f"status={status[mc]['status']}; local={status[mc]['local_implementation']}; prev={prev}"}
        validate(rec)
        line = json.dumps(rec, sort_keys=True)
        prev = hashlib.sha256(line.encode()).hexdigest()
        lines.append(line)
    (ev / "evidence-ledger.jsonl").write_text("\n".join(lines) + "\n")
    print(json.dumps({"tests": tests["counts"], "optimized": opt["result"], "source_tree_sha256": digests["source_tree_sha256"][:16],
                      "bench": {k: v["result"] for k, v in bench["verdicts"].items()}}, indent=1))
    return 0 if tests["counts"]["FAIL"] == 0 and opt["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
