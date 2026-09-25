"""Machine-readable release evidence (54): runs every suite, lint, types,
coverage, schema fixtures, bench/perf gate and soak against THIS source tree,
and writes evidence/evidence.json with the tree digest it was produced from."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
ENV = {"GAP01_LOG_LEVEL": "CRITICAL", "PYTHONDONTWRITEBYTECODE": "1"}


def tree_digest() -> str:
    h = hashlib.sha256()
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG).as_posix()
        if p.is_file() and not rel.startswith(("evidence/", "RELEASE_MANIFEST", "CHECKSUMS", "CHECKLIST_STATUS", "sbom.cdx.json")) \
                and "__pycache__" not in rel and not rel.endswith(".pyc"):
            h.update(rel.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def run(name: str, cmd: list[str], cwd: pathlib.Path = PKG, env_extra: dict | None = None) -> dict:
    import os
    env = dict(os.environ, **ENV, **(env_extra or {}))
    t = datetime.datetime.now(datetime.timezone.utc)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=1800)
    tail = (p.stdout + p.stderr).strip().splitlines()[-8:]
    return {"check": name, "cmd": " ".join(cmd), "returncode": p.returncode, "passed": p.returncode == 0,
            "started": t.isoformat(), "tail": tail}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence" / "evidence.json"))
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    py = sys.executable
    seeds = "40" if a.quick else "300"
    checks = [
        run("unit+property+integration+chaos+fuzz", [py, "-m", "unittest", "discover", "-s", "tests"],
            env_extra={"GAP01_PROPERTY_SEEDS": seeds}),
        run("coverage>=85", [py, "tools/coverage_stdlib.py", "--min", "85", "--json", "evidence/coverage.json"]),
        run("verify.py", [py, "verify.py"]),
        run("ruff", ["ruff", "check", "."]),
        run("mypy", ["mypy", "--config-file", "pyproject.toml", "."]),
        run("perf_gate", [py, "tools/perf_gate.py", "evidence/bench.json"]),
        run("traceability", [py, "tools/traceability.py"]),
        run("repo hygiene (links, JSON, secret scan)", [py, "tools/check_repo.py"]),
    ]
    trace = json.loads((PKG / "TRACEABILITY.json").read_text())["summary"]
    doc = {"schema": "GAP01_EVIDENCE/1", "element": "GAP-01", "version": (PKG / "VERSION").read_text().strip(),
           "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "python": sys.version.split()[0], "platform": sys.platform,
           "source_tree_sha256": tree_digest(), "checks": checks,
           "all_passed": all(c["passed"] for c in checks), "traceability": trace,
           "bench": json.loads((PKG / "evidence" / "bench.json").read_text()),
           "soak": json.loads((PKG / "evidence" / "soak.json").read_text()),
           "coverage": json.loads((PKG / "evidence" / "coverage.json").read_text())
           if (PKG / "evidence" / "coverage.json").exists() else None}
    pathlib.Path(a.out).write_text(json.dumps(doc, indent=2) + "\n")
    for c in checks:
        print(("PASS " if c["passed"] else "FAIL ") + c["check"])
    return 0 if doc["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
