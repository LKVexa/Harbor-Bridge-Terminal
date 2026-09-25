"""Long-running fuzz campaign (C085).  Scheduled nightly in CI; crashers land in tests/fuzz/corpus/.

    python tools/fuzz_campaign.py --seconds 3600 [--seed N]

Runs the same invariants as tests/fuzz/test_fuzz_parser.py with a long budget and a rotating seed.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    secs = float(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else 600
    seed = sys.argv[sys.argv.index("--seed") + 1] if "--seed" in sys.argv else str(int(time.time()))
    env = {**os.environ, "INV45_FUZZ_SECONDS": str(secs), "INV45_FUZZ_SEED": seed}
    r = subprocess.run([sys.executable, "-m", "unittest", f"{ROOT.name}.tests.fuzz.test_fuzz_parser"],
                       cwd=ROOT.parent, env=env)
    print(f"campaign seed={seed} seconds={secs} rc={r.returncode}")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
