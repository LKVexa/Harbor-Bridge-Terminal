"""INV-62 CI runner (MC-092).  Every lane is fail-closed: a lane that cannot run
is NOT_RUN and the overall result is INCOMPLETE (exit 3), never PASS.

    python inv62_edge_topology/tools/ci.py [--lanes a,b,...] [--out evidence] [--full]
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG.parent
EXCLUDE_DIRS = {"evidence", "dist", "__pycache__", ".git", ".mypy_cache", ".ruff_cache"}


def tree_digest() -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS) and p.name != "RELEASE_MANIFEST.json":
            rel = p.relative_to(PKG).as_posix()
            h.update(rel.encode() + b"\0" + hashlib.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
            n += 1
    return h.hexdigest(), n


def run(cmd: list[str], log: pathlib.Path, env: dict | None = None, timeout: int = 900) -> tuple[int, str]:
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PKG), env={**os.environ, **(env or {})}, timeout=timeout)
        out, code = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        out, code = "TIMEOUT", 124
    log.write_text(f"$ {' '.join(cmd)}\n# exit {code} in {time.time() - t0:.1f}s\n{out}")
    return code, out


def suite(*patterns: str, env: dict | None = None, optimize: bool = False):
    def lane(logs: pathlib.Path, name: str):
        cmd = [sys.executable] + (["-O"] if optimize else []) + [str(PKG / "tests" / "run_suite.py"), *patterns]
        code, out = run(cmd, logs / f"{name}.log", env)
        m = re.search(r"^\{.*\}$", out, re.M)
        detail = json.loads(m.group(0)) if m else {"raw": out[-500:]}
        return ("PASS" if code == 0 else "FAIL"), detail
    return lane


def cmd_lane(cmd: list[str], needs: str | None = None, ok_codes=(0,)):
    def lane(logs: pathlib.Path, name: str):
        if needs and shutil.which(needs) is None and importlib.util.find_spec(needs) is None:
            return "NOT_RUN", {"reason": f"{needs} not installed"}
        code, out = run(cmd, logs / f"{name}.log")
        return ("PASS" if code in ok_codes else "FAIL"), {"exit": code, "tail": out.strip().splitlines()[-3:]}
    return lane


def docs_lane(logs: pathlib.Path, name: str):
    """Referenced repository paths in docs must exist; stale names are defects."""
    problems = []
    pat = re.compile(r"`((?:production|tests|tools|docs|schemas|fixtures|examples|perf|ops|governance|conformance)/[A-Za-z0-9_./-]+)`")
    for doc in [PKG / "README.md", *sorted((PKG / "docs").glob("*.md"))]:
        for ref in pat.findall(doc.read_text(encoding="utf-8")):
            path = ref.split("::")[0].rstrip("/")
            if not (PKG / path).exists() and not path.startswith("evidence"):
                problems.append(f"{doc.name}: {ref}")
    for stale in ("MASTER.md`", "4.2.0 is production"):
        for doc in [PKG / "README.md", *sorted((PKG / "docs").glob("*.md"))]:
            if stale in doc.read_text(encoding="utf-8") and doc.name != "MASTER_SOURCE.md":
                problems.append(f"{doc.name}: stale reference {stale}")
    (logs / f"{name}.log").write_text("\n".join(problems) or "ok")
    return ("PASS" if not problems else "FAIL"), {"problems": problems}


def secrets_lane(logs: pathlib.Path, name: str):
    """No private keys, PKT1 credentials or long base64/hex secrets committed."""
    pats = [re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), re.compile(r"PKT1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}"),
            re.compile(r"(?i)(password|secret|api_key)\s*[:=]\s*['\"][^'\"]{12,}['\"]")]
    hits = []
    for p in PKG.rglob("*"):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS) and p.suffix in {".py", ".json", ".md", ".toml", ".yml"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            for pat in pats:
                for m in pat.finditer(text):
                    hits.append(f"{p.relative_to(PKG)}: {m.group(0)[:40]}")
    (logs / f"{name}.log").write_text("\n".join(hits) or "ok")
    return ("PASS" if not hits else "FAIL"), {"hits": hits}


def pk_core_lane(logs: pathlib.Path, name: str):
    if importlib.util.find_spec("pk_core") is None and not os.environ.get("PK_CORE_PATH"):
        return "NOT_RUN", {"reason": "pk_core not available (external 100-item conformance gate)"}
    code, _out = run([sys.executable, str(PKG / "tests" / "test_component.py")], logs / f"{name}.log")
    return ("PASS" if code == 0 else "FAIL"), {"exit": code}


def license_lane(logs: pathlib.Path, name: str):
    if not (PKG / "LICENSE").exists():
        return "NOT_RUN", {"reason": "no licence selected by the owner (MC-090); see NOTICE.md"}
    return "PASS", {}


def perf_lane(full: bool):
    def lane(logs: pathlib.Path, name: str):
        out = logs.parent / "bench.json"
        code, _text = run([sys.executable, str(PKG / "tools" / "bench.py"), *([] if full else ["--quick"]), "--out", str(out), "--gate"],
                         logs / f"{name}.log", timeout=1800)
        gate = json.loads((logs.parent / "perf_gate.json").read_text()) if (logs.parent / "perf_gate.json").exists() else {}
        return ("PASS" if code == 0 else "FAIL"), {"gate": gate.get("status"), "failing": [c["check"] for c in gate.get("checks", []) if c.get("status") == "FAIL"]}
    return lane


def main(argv: list[str]) -> int:
    full = "--full" in argv
    out = pathlib.Path(argv[argv.index("--out") + 1]) if "--out" in argv else PKG / "evidence"
    out = out if out.is_absolute() else (pathlib.Path.cwd() / out)
    logs = out / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    fuzz_env = {"INV62_FUZZ_ITERS": "3000" if full else "300"}
    lanes = {
        "compile": cmd_lane([sys.executable, "-m", "compileall", "-q", "."]),
        "lint": cmd_lane(["ruff", "check", "."], needs="ruff"),
        "types": cmd_lane(["mypy"], needs="mypy"),
        "unit": suite("test_*.py"),
        "unit-optimized": suite("test_*.py", optimize=True),
        "contract": suite("test_contract.py"),
        "security": suite("test_security.py"),
        "fuzz": suite("test_fuzz.py", env=fuzz_env),
        "concurrency": suite("test_concurrency.py"),
        "faults": suite("test_faults.py", "test_persistence.py"),
        "integration": suite("test_integration.py", "test_bootstrap.py"),
        "schemas": cmd_lane([sys.executable, str(PKG / "tools" / "export_schemas.py"), "--check"]),
        "rtm": cmd_lane([sys.executable, str(PKG / "tools" / "rtm.py"), "--check"]),
        "docs": docs_lane,
        "secrets": secrets_lane,
        "perf": perf_lane(full),
        "pk-core": pk_core_lane,
        "license": license_lane,
    }
    if "--lanes" in argv:
        wanted = argv[argv.index("--lanes") + 1].split(",")
        lanes = {k: v for k, v in lanes.items() if k in wanted}
    digest, nfiles = tree_digest()
    results = {}
    for name, lane in lanes.items():
        t0 = time.time()
        status, detail = lane(logs, name)
        results[name] = {"status": status, "seconds": round(time.time() - t0, 2), "detail": detail}
        print(f"{name:16s} {status:8s} {results[name]['seconds']:7.2f}s", flush=True)
    statuses = {r["status"] for r in results.values()}
    overall = "FAIL" if "FAIL" in statuses else "INCOMPLETE" if "NOT_RUN" in statuses else "PASS"
    report = {"schema": "INV62_CI_REPORT/1", "version": (PKG / "VERSION").read_text().strip(), "overall": overall,
              "source_tree_sha256": digest, "files": nfiles, "full": full,
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "ruff": shutil.which("ruff") is not None, "mypy": shutil.which("mypy") is not None},
              "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "lanes": results}
    (out / "ci_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("overall:", overall)
    return {"PASS": 0, "FAIL": 1, "INCOMPLETE": 3}[overall]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
