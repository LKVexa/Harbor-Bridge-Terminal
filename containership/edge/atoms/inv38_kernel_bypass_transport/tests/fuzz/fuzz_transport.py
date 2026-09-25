"""INV-38-C085 structure-aware fuzz + property tests over the transport model.

Runnable standalone: `python fuzz_transport.py --iterations N`. Bounded per-input;
any invariant break (device access outside a registered region, or a non-stable
error code) is a failure. Regression corpus lives in corpus/.
"""
from __future__ import annotations
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from inv38_kernel_bypass_transport.transport import BypassQueue, BypassError, OutOfBounds

STABLE_CODES = {"PK_BYPASS_OUT_OF_BOUNDS","PK_BYPASS_NOT_REGISTERED","PK_BYPASS_REGION_BUSY",
                "PK_BYPASS_RING_FULL","PK_BYPASS_COMPLETION_RING_FULL","PK_BYPASS_REGION_LIMIT"}

def one_iteration(rng: random.Random) -> None:
    q = BypassQueue(ring_size=rng.randint(1, 4), max_regions=rng.randint(1, 4))
    base = rng.randrange(0, 1 << 20); length = rng.randint(1, 1 << 16)
    try:
        k = q.register(base, length)
    except BypassError as e:
        assert e.code in STABLE_CODES; return
    addr = rng.randrange(0, 1 << 21); plen = rng.randint(0, length + 8)
    try:
        res = q.post(k, addr, max(1, plen), b"\x00" * min(plen, length))
        assert res in ("bypass", "kernel")
        # property: an accepted bypass descriptor is inside the region
        if res == "bypass":
            assert base <= addr and addr + max(1, plen) <= base + length
    except BypassError as e:
        assert e.code in STABLE_CODES, e.code

def property_containment_never_violated(rng: random.Random) -> None:
    q = BypassQueue(ring_size=8)
    k = q.register(1000, 100)
    for _ in range(50):
        a = rng.randint(900, 1200); l = rng.randint(1, 200)
        try:
            if q.post(k, a, l, b"x" * min(l, 100)) == "bypass":
                assert 1000 <= a and a + l <= 1100
        except OutOfBounds:
            pass

def main(iterations: int = 5000, seed: int = 1234) -> int:
    rng = random.Random(seed)
    for _ in range(iterations):
        one_iteration(rng)
    property_containment_never_violated(rng)
    print(f"fuzz OK: {iterations} iterations, seed={seed}")
    return 0

# harness entry points
def test_fuzz_smoke(): assert main(1000) == 0
def test_containment_property(): property_containment_never_violated(random.Random(7))

if __name__ == "__main__":
    it = 5000
    if "--iterations" in sys.argv:
        it = int(sys.argv[sys.argv.index("--iterations") + 1])
    raise SystemExit(main(it))
