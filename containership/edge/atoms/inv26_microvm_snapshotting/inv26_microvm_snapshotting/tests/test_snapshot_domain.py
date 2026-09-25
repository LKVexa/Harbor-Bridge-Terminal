"""Standalone unit tests for the INV-26 snapshot domain model (no pk_core required)."""
import importlib.util
import pathlib
import threading
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "snapshot.py"
spec = importlib.util.spec_from_file_location("inv26_snapshot_domain", MODULE)
snapshot = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = snapshot
spec.loader.exec_module(snapshot)


class SnapshotDomainTest(unittest.TestCase):
    def make_store(self, injector=None):
        return snapshot.SnapshotStore(**({"entropy_injector": injector} if injector else {}))

    def capture(self, store, name="s1"):
        return store.capture(name=name, tenant="t1", workload="w1", environment="prod",
                             devices={"virtio-net", "virtio-block"}, memory_mib=256)

    def restore(self, store, **overrides):
        args = dict(tenant="t1", workload="w1", environment="prod",
                    devices={"virtio-net", "virtio-block"}, elapsed_ms=4)
        args.update(overrides)
        return store.restore("s1", **args)

    def test_full_sha256_fingerprint_and_order_independence(self):
        a = snapshot.model_fingerprint(["virtio-net", "virtio-block"])
        b = snapshot.model_fingerprint(["virtio-block", "virtio-net"])
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_device_validation_rejects_string_and_duplicates(self):
        with self.assertRaises(TypeError):
            snapshot.model_fingerprint("virtio-net")
        with self.assertRaises(ValueError):
            snapshot.model_fingerprint(["virtio-net", "virtio-net"])

    def test_capture_rejects_overwrite(self):
        store = self.make_store(); self.capture(store)
        with self.assertRaises(snapshot.SnapshotExists):
            self.capture(store)

    def test_cross_tenant_workload_environment_and_model_restore_refused(self):
        store = self.make_store(); self.capture(store)
        cases = [
            ({"tenant": "t2"}, snapshot.CrossTenantRestore),
            ({"workload": "w2"}, snapshot.WorkloadMismatch),
            ({"environment": "dev"}, snapshot.EnvironmentMismatch),
            ({"devices": {"virtio-net"}}, snapshot.ModelMismatch),
        ]
        for kwargs, error in cases:
            with self.subTest(error=error.__name__), self.assertRaises(error):
                self.restore(store, **kwargs)
        self.assertEqual(store.reseeds, 0)

    def test_every_restore_injects_fresh_entropy_and_returns_only_proof(self):
        seen = []
        def inject(_snap, seed): seen.append(seed)
        store = self.make_store(inject); self.capture(store)
        one = self.restore(store); two = self.restore(store)
        self.assertEqual(len(seen), 2)
        self.assertEqual(len(seen[0]), snapshot.ENTROPY_BYTES)
        self.assertNotEqual(seen[0], seen[1])
        self.assertNotEqual(one["entropy_proof_sha256"], two["entropy_proof_sha256"])
        self.assertNotIn(seen[0].hex(), repr(one))

    def test_failed_entropy_injection_fails_closed(self):
        def fail(_snap, _seed): raise OSError("guest RNG unavailable")
        store = self.make_store(fail); self.capture(store)
        with self.assertRaises(snapshot.EntropyInjectionFailed):
            self.restore(store)
        self.assertEqual(store.reseeds, 0)

    def test_snapshot_view_is_read_only(self):
        store = self.make_store(); self.capture(store)
        with self.assertRaises(TypeError):
            store.snapshots["x"] = store.snapshots["s1"]

    def test_elapsed_validation(self):
        store = self.make_store(); self.capture(store)
        for value in (-1, float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.restore(store, elapsed_ms=value)
        with self.assertRaises(TypeError):
            self.restore(store, elapsed_ms=True)

    def test_concurrent_duplicate_capture_has_one_winner(self):
        store = self.make_store()
        outcomes = []
        barrier = threading.Barrier(8)
        def worker():
            barrier.wait()
            try:
                self.capture(store)
                outcomes.append("ok")
            except snapshot.SnapshotExists:
                outcomes.append("exists")
        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(outcomes.count("ok"), 1)
        self.assertEqual(outcomes.count("exists"), 7)

    def test_canonical_record_binds_security_context(self):
        store = self.make_store(); snap = self.capture(store)
        self.assertIn(b'"environment":"prod"', snap.canonical())
        self.assertIn(b'"tenant":"t1"', snap.canonical())
        self.assertIn(b'"schema":"PK_SNAPSHOT/2"', snap.canonical())


if __name__ == "__main__":
    unittest.main()
