"""Self-contained tests for the backend state machine (no pk_core required)."""
import pathlib, sys, threading, unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv19_os_asynchronous_analogues as inv


class BackendTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(inv.__version__, "5.0.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "5.0.0")

    def test_selection_is_stable_and_falls_back(self):
        self.assertEqual(inv.select(["epoll", "io_uring"]), "io_uring")
        self.assertEqual(inv.select(["kqueue", "epoll"]), "epoll")
        self.assertEqual(inv.select([]), inv.FALLBACK)
        with self.assertRaises(TypeError):
            inv.select("epoll")

    def test_completion_preserves_error_and_value(self):
        b = inv.AsyncBackend("io_uring")
        b.arm(3); b.post(3, None, "ECONNRESET")
        self.assertEqual(b.reap(3), ("error", "ECONNRESET"))
        b.arm(4); b.post(4, 17)
        self.assertEqual(b.reap(4), ("value", 17))

    def test_readiness_never_claims_completion(self):
        b = inv.AsyncBackend("epoll")
        b.arm(3); b.post(3, "payload", "EIO")
        self.assertEqual(b.reap(3), ("retry", None))

    def test_budget_duplicate_post_and_cancel(self):
        b = inv.AsyncBackend("portable", max_descriptors=1)
        self.assertEqual(b.fallback_engagements, 1)
        b.arm(1)
        with self.assertRaises(inv.DescriptorBudget): b.arm(2)
        b.post(1, None)
        with self.assertRaises(ValueError): b.post(1, None)
        self.assertTrue(b.cancel(1))
        self.assertFalse(b.cancel(1))
        self.assertEqual(b.snapshot()["cancelled"], 1)

    def test_descriptor_and_configuration_validation(self):
        for fd in (-1, True, 1.2, "1"):
            with self.assertRaises((inv.InvalidDescriptor, TypeError)):
                inv.AsyncBackend("epoll").arm(fd)
        for cap in (0, -1, True, 1.5):
            with self.assertRaises(ValueError): inv.AsyncBackend("epoll", cap)
        with self.assertRaises(inv.NoBackend): inv.AsyncBackend("invented")

    def test_concurrent_arming_respects_budget(self):
        b = inv.AsyncBackend("epoll", max_descriptors=8)
        barrier = threading.Barrier(17)
        outcomes = []
        lock = threading.Lock()
        def worker(fd):
            barrier.wait()
            try:
                b.arm(fd); value = "armed"
            except inv.DescriptorBudget:
                value = "bounded"
            with lock: outcomes.append(value)
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
        for t in ts: t.start()
        barrier.wait()
        for t in ts: t.join()
        self.assertEqual(outcomes.count("armed"), 8)
        self.assertEqual(b.armed_count, 8)


if __name__ == "__main__":
    unittest.main()
