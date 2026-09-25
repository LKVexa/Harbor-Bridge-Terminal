"""Single CI entry point: every suite, every generator, every gate, in order.

  python tools/run_ci.py            # PR tier
  python tools/run_ci.py --nightly  # longer fuzz/race/soak campaigns + mutation

Writes evidence/ci_run.json.  Exit 0 means the development gate passed; the
production verdict is the separate tools/release_gate.py (currently NO_GO).
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import subprocess
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
SUITES = ["test_primitives.py", "test_contracts.py", "test_properties.py", "test_races.py", "test_subsystems.py",
          "test_isolation.py", "test_governance.py", "test_component.py"]


def sh(args, cwd, env=None, timeout=1800):
    t = time.time()
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    return p, round(time.time() - t, 2)


def main() -> int:
    nightly = "--nightly" in sys.argv
    env = dict(os.environ, INV41_ITER="20000" if nightly else "300", INV41_RACE_ROUNDS="400" if nightly else "40",
               PYTHONDONTWRITEBYTECODE="1")
    out = {"schema": "INV41_CI_RUN/1", "tier": "nightly" if nightly else "pr", "python": platform.python_version(),
           "seed": env.get("INV41_SEED", "4130"), "suites": [], "tools": []}
    p, d = sh([sys.executable, "-m", "compileall", "-q", str(PKG)], PKG.parent)
    out["compileall"] = p.returncode == 0
    for s in SUITES:
        p, d = sh([sys.executable, "-B", s, "-v"], PKG / "tests", env)
        text = p.stderr
        ran = next((l for l in text.splitlines() if l.startswith("Ran ")), "Ran 0 tests")
        skipped = "skipped=" in text.splitlines()[-1] if text.strip() else False
        out["suites"].append({"name": s, "pass": p.returncode == 0, "ran": ran, "skipped": skipped,
                              "tail": text.strip().splitlines()[-1] if text.strip() else "", "seconds": d})
    for opt in ([], ["-O"]):
        p, d = sh([sys.executable, *opt, "-B", "-m", "inv41_capability_security.selfcheck"], PKG.parent, env)
        out["tools"].append({"name": "selfcheck" + ("".join(opt)), "pass": p.returncode == 0 and '"passing": true' in p.stdout})
    tools = [("preflight", ["-m", "inv41_capability_security.preflight"], PKG.parent),
             ("traceability", [str(PKG / "tools" / "traceability.py")], PKG),
             ("governance(dev)", [str(PKG / "tools" / "governance_check.py")], PKG),
             ("estate_gate(dev)", [str(PKG / "tools" / "estate_gate.py"), "--profile", "development"], PKG),
             ("bench", [str(PKG / "tools" / "bench.py")], PKG),
             ("scale_soak", [str(PKG / "tools" / "scale_soak.py"), "--tier", "nightly" if nightly else "pr"], PKG),
             ("compat", [str(PKG / "tools" / "compat.py")], PKG)]
    if nightly or "--mutation" in sys.argv:
        tools.append(("mutation", [str(PKG / "tools" / "mutation.py")], PKG))
    for name, args, cwd in tools:
        p, d = sh([sys.executable, "-B", *args], cwd, env)
        out["tools"].append({"name": name, "pass": p.returncode == 0, "seconds": d, "stdout_tail": p.stdout.strip()[-600:]})
    out["traceability_ok"] = next(t["pass"] for t in out["tools"] if t["name"] == "traceability")
    out["all_suites_pass"] = all(s["pass"] for s in out["suites"])
    out["pass"] = out["compileall"] and out["all_suites_pass"] and all(t["pass"] for t in out["tools"])
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "ci_run.json").write_text(json.dumps(out, indent=1))
    for s in out["suites"]:
        print(f"{'PASS' if s['pass'] else 'FAIL'}  {s['name']:22} {s['ran']:16} {s['tail']}")
    for t in out["tools"]:
        print(f"{'PASS' if t['pass'] else 'FAIL'}  {t['name']}")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
