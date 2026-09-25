"""Long-running fuzzer (MC032).  Usage: python tools/fuzz.py [seconds] [seed]
Crashing inputs are written to fuzz/crashes/<target>-<sha>.bin."""
import hashlib
import pathlib
import random
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from inv29_hybrid_wasm_unikernel import fuzz_targets as T  # noqa: E402

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 60
r = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else int(time.time()))
out = PKG / "fuzz" / "crashes"
n = crashes = 0
end = time.monotonic() + secs
while time.monotonic() < end:
    name = r.choice(list(T.TARGETS))
    data = T.mutate(r, r.choice(T.SEEDS[name]))
    n += 1
    try:
        T.TARGETS[name](data)
    except T.ALLOWED:
        pass
    except Exception as exc:
        crashes += 1
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{name}-{hashlib.sha256(data).hexdigest()[:16]}.bin").write_bytes(data)
        print(f"FINDING {name}: {type(exc).__name__}: {exc}")
print(f"{n} executions, {crashes} findings")
sys.exit(1 if crashes else 0)
