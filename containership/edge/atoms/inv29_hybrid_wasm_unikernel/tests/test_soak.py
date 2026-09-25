"""Soak / burst test (MC037), scaled for CI.  Set INV29_SOAK_SECONDS for a real
soak; fleet-scale remains BLOCKED_EXTERNAL (needs an estate)."""
import os
import time
import tracemalloc
import unittest
from concurrent.futures import ThreadPoolExecutor

import _fixtures as F
from inv29_hybrid_wasm_unikernel import admission as adm

SECONDS = float(os.environ.get("INV29_SOAK_SECONDS", "1.5"))


class SoakTest(unittest.TestCase):
    def test_sustained_and_burst_admission_is_stable(self):
        kr = F.keyring()
        clock = F.Clock()
        a = F.admitter(kr, clock=clock, replay=adm.ReplayGuard(capacity=2_000_000))
        pool = [F.request(kr) for _ in range(64)]
        tracemalloc.start()
        deadline, n, errors = time.monotonic() + SECONDS, 0, 0
        snap0 = None
        while time.monotonic() < deadline:
            for req in pool:
                try:
                    a.admit(adm.AdmissionRequest(**{**req.__dict__, "nonce": adm.new_nonce()}))
                    n += 1
                except Exception:
                    errors += 1
            if snap0 is None and n > 2000:
                snap0 = tracemalloc.take_snapshot()
        # burst: 16 threads at once
        with ThreadPoolExecutor(16) as ex:
            burst = list(ex.map(lambda r: a.admit(adm.AdmissionRequest(**{**r.__dict__, "nonce": adm.new_nonce()})),
                                pool * 8))
        cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertEqual(errors, 0)
        self.assertEqual(len(burst), 512)
        self.assertGreater(n, 500)
        # the only growth allowed is the bounded replay cache (~ n entries); guard against leaks elsewhere
        self.assertLess(peak / max(n + 512, 1), 4096, "per-admission retained memory looks unbounded")


if __name__ == "__main__":
    unittest.main()
