"""Behavioural tests for the in-process primitive model (carried from 4.2.0)."""

import threading
import unittest

from tests._boot import mod

m = mod("model")
VirtPrimitive, PrimitiveUnavailable = m.VirtPrimitive, m.PrimitiveUnavailable
USABLE, CLAIMED, PRESENT_DISABLED, ABSENT = m.USABLE, m.CLAIMED, m.PRESENT_DISABLED, m.ABSENT


class PrimitiveBehaviourTest(unittest.TestCase):
    def test_state_matrix_and_bare_metal(self):
        self.assertEqual(VirtPrimitive("n0").state(), ABSENT)
        self.assertEqual(VirtPrimitive("n1", True, False, False).state(), PRESENT_DISABLED)
        p = VirtPrimitive("n2", True, True, True)
        self.assertEqual(p.state(), USABLE)
        self.assertTrue(p.report()["bare_metal"])
        p.claim("vmm")
        self.assertEqual(p.state(), CLAIMED)
        self.assertTrue(p.report()["bare_metal"])

    def test_validation_rejects_ambiguous_values(self):
        for host in ("", "   ", None):
            with self.assertRaises((ValueError, TypeError)):
                VirtPrimitive(host)
        with self.assertRaises(ValueError):
            VirtPrimitive("n", nesting_depth=True)
        with self.assertRaises(TypeError):
            VirtPrimitive("n", cpuid_present=1)
        p = VirtPrimitive("n", True, True, True)
        with self.assertRaises(ValueError):
            p.claim("   ")
        with self.assertRaises(ValueError):
            p.claim("vmm", max_nesting=True)

    def test_claim_is_exclusive_and_release_is_authenticated(self):
        p = VirtPrimitive("n", True, True, True)
        p.claim("owner")
        with self.assertRaises(PrimitiveUnavailable):
            p.claim("other")
        with self.assertRaises(PrimitiveUnavailable):
            p.release()
        with self.assertRaises(PrimitiveUnavailable):
            p.release("other")
        self.assertEqual(p.holder, "owner")
        p.release("owner")
        self.assertIsNone(p.holder)

    def test_nesting_policy(self):
        p = VirtPrimitive("nested", True, True, True, nesting_depth=2)
        self.assertFalse(p.report()["bare_metal"])
        with self.assertRaises(PrimitiveUnavailable):
            p.claim("vmm", max_nesting=1)

    def test_concurrent_claim_has_single_winner(self):
        p = VirtPrimitive("n", True, True, True)
        barrier = threading.Barrier(8)
        winners, failures, lock = [], [], threading.Lock()

        def worker(i):
            barrier.wait()
            try:
                p.claim(f"vmm-{i}")
                with lock:
                    winners.append(i)
            except PrimitiveUnavailable:
                with lock:
                    failures.append(i)

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual((len(winners), len(failures)), (1, 7))

    def test_from_probe_never_upgrades(self):
        b = mod("backends.base")
        r = b.ProbeResult(
            host="h",
            backend="x",
            backend_version="1",
            platform="linux",
            architecture="x86_64",
            state=b.INDETERMINATE,
            reason="probe_timeout",
            cpu_capable=True,
        )
        vp = VirtPrimitive.from_probe(r)
        self.assertNotEqual(vp.state(), USABLE)
        self.assertFalse(vp.report()["bare_metal"])  # unknown virtualization -> depth 1


if __name__ == "__main__":
    unittest.main()
