"""Local CI driver: the same lanes as .github/workflows/ci.yml (MC-090).

    python -B inv27_unikernel_execution/tools/ci.py [--write]

--write regenerates evidence (perf quick run excluded; run bench/perf_suite.py separately), RTM, MC status,
SBOM, pk_core gate and the manifest before verifying.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT.name


def run(args):
    p = subprocess.run([sys.executable, *args], cwd=str(ROOT.parent))
    return p.returncode


def main() -> int:
    steps = []
    if "--write" in sys.argv:
        steps += [["-B", "-m", f"{P}.tools.rtm"], ["-B", "-m", f"{P}.tools.mc_status"], ["-B", "-m", f"{P}.tools.sbom"],
                  ["-B", "-m", f"{P}.tools.pk_gate"], ["-B", "-m", f"{P}.tools.perf_gate"], ["-B", "-m", f"{P}.tools.manifest"]]
    steps += [["-B", f"{P}/tests/run_all.py"], ["-O", "-B", f"{P}/tests/run_all.py"], ["-B", "-m", f"{P}.tools.lint"],
              ["-B", "-m", f"{P}.tools.deps_check"], ["-B", "-m", f"{P}.tools.coverage_check", "--check"],
              ["-B", "-m", f"{P}.tools.rtm", "--check"], ["-B", "-m", f"{P}.tools.mc_status", "--check"],
              ["-B", "-m", f"{P}.tools.manifest", "--verify"]]
    bad = [s for s in steps if run(s)]
    print("CI", "PASS" if not bad else f"FAIL {len(bad)}/{len(steps)}: {bad}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
