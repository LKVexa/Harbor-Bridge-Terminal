"""INV-34 CI pipeline (MC-072, MC-073). Stdlib only.

Lanes: compile · unit tests (normal and -O) · schema/JSON parse · AST lint policy ·
secret scan · SPDX presence · RTM · reproducible build + SBOM · perf regression ·
pk_core gate (expected fail-closed) · runbook smoke · checklist status · exit gate.
Exit 0 = all local lanes pass; the pk_core and exit gates are reported, never forced green.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid

from _common import PKG, ROOT, source_digest, source_files, write_json

PY = sys.executable
BANNED_CALLS = {"eval", "exec", "compile", "__import__"}


def run(args, **kw):
    return subprocess.run(args, cwd=kw.pop("cwd", ROOT), capture_output=True, text=True, timeout=900, **kw)


def lint() -> list[str]:
    problems = []
    for p in source_files():
        if p.suffix != ".py":
            continue
        rel = p.relative_to(PKG).as_posix()
        tree = ast.parse(p.read_text(), rel)
        prod = rel.startswith("production/") or rel in ("expansion.py", "contract.py", "component.py")
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in BANNED_CALLS:
                problems.append(f"{rel}:{n.lineno} banned call {n.func.id}")
            if isinstance(n, ast.keyword) and n.arg == "shell" and getattr(n.value, "value", False) is True:
                problems.append(f"{rel}:{n.lineno} shell=True")
            if prod and isinstance(n, ast.ExceptHandler) and n.type is None:
                problems.append(f"{rel}:{n.lineno} bare except")
            if prod and isinstance(n, ast.Assert):
                problems.append(f"{rel}:{n.lineno} assert in production logic")
            if prod and isinstance(n, ast.Call) and getattr(n.func, "attr", "") in ("system", "popen"):
                problems.append(f"{rel}:{n.lineno} os.system/popen")
        if prod and rel.startswith("production/") and "SPDX-License-Identifier" not in p.read_text()[:600]:
            problems.append(f"{rel}: missing SPDX header")
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if re.search(r"\b(TODO|FIXME|XXX)\b", line) and prod:
                problems.append(f"{rel}:{i} TODO marker")
    return problems


SECRET_RX = [re.compile(r"AKIA[0-9A-Z]{16}"), re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
             re.compile(r"(?i)(api[_-]?key|password)\s*=\s*['\"][^'\"]{12,}['\"]")]


def secrets() -> list[str]:
    hits = []
    for p in source_files():
        if p.suffix in (".py", ".json", ".md", ".toml", ".yml"):
            for rx in SECRET_RX:
                if rx.search(p.read_text(errors="ignore")):
                    hits.append(f"{p.relative_to(PKG)} matches {rx.pattern[:20]}")
    return hits


def main() -> int:
    run_id = f"ci-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:6]}"
    lanes, tools = {}, {}
    r = run([PY, "-B", "-m", "compileall", "-q", str(PKG)], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    lanes["compile"] = "PASS" if r.returncode == 0 else "FAIL"
    passed, failed = [], []
    for mode in ([], ["-O"]):
        r = run([PY, "-B", *mode, "-m", "unittest", "discover", "-v", "-s", str(PKG / "tests")])
        lanes["unittest" + ("_O" if mode else "")] = "PASS" if r.returncode == 0 else "FAIL"
        if not mode:
            pending = None   # verbose output puts a docstring line between the id and the verdict
            for line in r.stderr.splitlines():
                m = re.match(r"^(test\w+) \((test_\w+)\.(\w+)(?:\.\w+)?\)", line)
                if m:
                    pending = f"{m.group(2)}.{m.group(3)}.{m.group(1)}"
                v = re.search(r"\.\.\. (ok|FAIL|ERROR|skipped.*)$", line)
                if v and pending:
                    (passed if v.group(1) == "ok" else failed).append(pending)
                    pending = None
            lanes["unittest_summary"] = r.stderr.strip().splitlines()[-1]
    bad_json = []
    for p in source_files():
        if p.suffix == ".json":
            try:
                json.loads(p.read_text())
            except ValueError:
                bad_json.append(str(p.relative_to(PKG)))
    lanes["json_schemas"] = "PASS" if not bad_json else f"FAIL {bad_json}"
    lp = lint()
    lanes["lint_policy"] = "PASS" if not lp else "FAIL"
    sp = secrets()
    lanes["secret_scan"] = "PASS" if not sp else "FAIL"
    for tool, expect in (("tools/rtm.py", 0), ("tools/build.py", 0), ("tools/perf.py", 0), ("tools/pk_core_gate.py", 2)):
        r = run([PY, "-B", str(PKG / tool)], cwd=PKG / "tools")
        tools[tool] = ("PASS" if r.returncode == 0 else
                       "EXPECTED_FAIL_CLOSED" if r.returncode == expect else f"FAIL rc={r.returncode}: {r.stdout[-300:]}{r.stderr[-300:]}")
    with tempfile.TemporaryDirectory() as td:
        cfg = os.path.join(td, "c.json")
        json.dump({"schema": "INV34_CONFIG/1", "version": "ci", "environment": "test", "site": "s1",
                   "expansion_enabled": False, "adapter": "emulator", "max_vcpus_default": 8, "host_reserve_vcpus": 1,
                   "stall_after_s": 120, "observation_max_age_s": 30, "tenant_quotas": {"t1": 8}, "site_ceiling": 64,
                   "fleet_ceiling": 64, "precedence": ["security", "residency", "capacity", "slo", "cost"]}, open(cfg, "w"))
        r1 = run([PY, "-B", str(PKG / "tools/runbook.py"), "day0", "--root", td, "--config", cfg, "--author", "ci"], cwd=PKG / "tools")
        r2 = run([PY, "-B", str(PKG / "tools/runbook.py"), "day2", "--root", td], cwd=PKG / "tools")
        tools["tools/runbook.py"] = "PASS" if r1.returncode == 0 and r2.returncode == 0 else f"FAIL {r1.stderr[-200:]}{r2.stderr[-200:]}"
    local_ok = all(v == "PASS" for k, v in lanes.items() if k != "unittest_summary") and \
        all(v in ("PASS", "EXPECTED_FAIL_CLOSED") for v in tools.values())
    result = {"schema": "INV34_CI_RESULT/1", "run_id": run_id, "source_digest": source_digest(),
              "python": sys.version.split()[0], "lanes": lanes, "tools": tools, "lint_problems": lp,
              "secret_hits": sp, "tests_passed": sorted(passed), "tests_not_passed": sorted(failed),
              "local_verdict": "PASS" if local_ok else "FAIL",
              "certification_verdict": "NOT_CERTIFIED (pk_core gate fails closed; exit gate NO_GO)"}
    write_json("governance/CI_RESULT.json", result)
    r = run([PY, "-B", str(PKG / "tools/checklist_status.py")], cwd=PKG / "tools")
    result["tools"]["tools/checklist_status.py"] = "PASS" if r.returncode == 0 else f"FAIL {r.stderr[-300:]}"
    r = run([PY, "-B", str(PKG / "tools/exit_gate.py")], cwd=PKG / "tools")
    result["exit_gate"] = json.loads((PKG / "governance/EXIT_GATE_RESULT.json").read_text())["decision"] if r.returncode in (0, 3) else f"ERROR {r.stderr[-200:]}"
    write_json("governance/CI_RESULT.json", result)
    print(json.dumps({k: result[k] for k in ("run_id", "lanes", "tools", "local_verdict", "exit_gate")}, indent=1))
    return 0 if local_ok else 1


if __name__ == "__main__":
    sys.exit(main())
