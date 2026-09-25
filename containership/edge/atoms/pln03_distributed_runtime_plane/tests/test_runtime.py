"""Standalone behavioural tests for the PLN-03 operational reference runtime."""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pln03_runtime", PKG_DIR / "runtime.py")
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class RuntimeBehaviorTest(unittest.TestCase):
    def test_state_namespace_delete_and_atomic_transaction(self):
        state = runtime.Adapter("state")
        rt = runtime.DistributedRuntime({"api:state": state})
        rt.state_set("api", "t1", "k", b"v1")
        self.assertEqual(rt.state_get("api", "t1", "k"), b"v1")
        self.assertIsNone(rt.state_get("api", "t2", "k"))
        rt.state_transact("api", "t1", [("set", "a", b"1"), ("set", "b", b"2"), ("delete", "k", None)])
        self.assertEqual(rt.state_get("api", "t1", "a"), b"1")
        self.assertEqual(rt.state_get("api", "t1", "b"), b"2")
        self.assertIsNone(rt.state_get("api", "t1", "k"))
        self.assertTrue(rt.state_delete("api", "t1", "a"))
        self.assertFalse(rt.state_delete("api", "t1", "a"))

    def test_transaction_validation_is_fail_before_write(self):
        state = runtime.Adapter("state")
        rt = runtime.DistributedRuntime({"api:state": state})
        rt.state_set("api", "t1", "stable", b"old")
        with self.assertRaises(runtime.InvalidRuntimeInput):
            rt.state_transact("api", "t1", [("set", "stable", b"new"), ("bogus", "x", None)])
        self.assertEqual(rt.state_get("api", "t1", "stable"), b"old")

    def test_publish_is_atomic_idempotent_and_subscribable(self):
        bus = runtime.Adapter("bus")
        rt = runtime.DistributedRuntime({"api:messaging": bus})
        self.assertTrue(rt.publish("api", "t1", "orders", b"first", "idem"))
        self.assertFalse(rt.publish("api", "t1", "orders", b"replacement", "idem"))
        self.assertEqual(rt.subscribe("api", "t1", "orders"), (b"first",))

    def test_failed_publish_does_not_consume_idempotency_key(self):
        bus = runtime.Adapter("bus", available=False)
        rt = runtime.DistributedRuntime({"api:messaging": bus})
        with self.assertRaises(runtime.AdapterUnavailable):
            rt.publish("api", "t1", "orders", b"p", "idem")
        bus.available = True
        self.assertTrue(rt.publish("api", "t1", "orders", b"p", "idem"))

    def test_accept_honours_availability(self):
        adapter = runtime.Adapter("down", available=False)
        with self.assertRaises(runtime.AdapterUnavailable):
            adapter.accept("x")

    def test_concurrent_duplicate_publish_accepts_once(self):
        bus = runtime.Adapter("bus")
        rt = runtime.DistributedRuntime({"api:messaging": bus})
        results: list[bool] = []
        lock = threading.Lock()

        def worker(n: int) -> None:
            accepted = rt.publish("api", "t1", "orders", f"p{n}".encode(), "same")
            with lock:
                results.append(accepted)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(32)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(rt.subscribe("api", "t1", "orders")), 1)

    def test_ambiguous_topic_and_idempotency_combinations_do_not_collide(self):
        bus = runtime.Adapter("bus")
        rt = runtime.DistributedRuntime({"api:messaging": bus})
        self.assertTrue(rt.publish("api", "t1", "a/b", b"x", "c"))
        self.assertTrue(rt.publish("api", "t1", "a", b"y", "b/c"))

    def test_secret_and_invocation_interfaces(self):
        secrets = runtime.Adapter("secrets")
        invoke = runtime.Adapter("invoke")
        secrets.set("t1/db-password", b"s3cr3t")
        invoke.register_target("t1:worker", lambda payload: payload.upper())
        rt = runtime.DistributedRuntime({"api:secrets": secrets, "api:invoke": invoke})
        self.assertEqual(rt.secret_fetch("api", "t1", "db-password"), b"s3cr3t")
        self.assertEqual(rt.invoke("api", "t1", "worker", b"ping"), b"PING")
        with self.assertRaises(runtime.SecretNotFound):
            rt.secret_fetch("api", "t1", "missing")

    def test_input_validation_and_inline_limit(self):
        bus = runtime.Adapter("bus")
        rt = runtime.DistributedRuntime({"api:messaging": bus})
        with self.assertRaises(runtime.InvalidRuntimeInput):
            rt.publish("api", "bad/tenant", "topic", b"x", "i")
        with self.assertRaises(runtime.InvalidRuntimeInput):
            rt.publish("api", "t1", "", b"x", "i")
        with self.assertRaises(runtime.PayloadTooLarge):
            rt.publish("api", "t1", "topic", b"x" * (runtime.MAX_INLINE_BYTES + 1), "i")

    def test_package_imports_without_pk_core(self):
        code = f"""
import sys
sys.path.insert(0, {str(PKG_DIR.parent)!r})
import pln03_distributed_runtime_plane as p
assert p.__version__ == {(PKG_DIR / 'VERSION').read_text().strip()!r}
assert p.DistributedRuntime is not None
assert p.PK_CORE_AVAILABLE is False
try:
    p.build_contract()
except ModuleNotFoundError:
    pass
else:
    raise AssertionError('build_contract must require pk_core')
print(p.PK_CORE_AVAILABLE)
"""
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


    def test_binding_and_transaction_shapes_fail_closed(self):
        adapter = runtime.Adapter("state")
        with self.assertRaises(runtime.InvalidRuntimeInput):
            runtime.DistributedRuntime({"badbinding": adapter})
        with self.assertRaises(runtime.InvalidRuntimeInput):
            runtime.DistributedRuntime({"api:unknown": adapter})
        rt = runtime.DistributedRuntime({"api:state": adapter})
        with self.assertRaises(runtime.InvalidRuntimeInput):
            rt.state_get("bad:workload", "t1", "k")
        with self.assertRaises(runtime.InvalidRuntimeInput):
            rt.state_transact("api", "t1", [("set", "only-two")])



if __name__ == "__main__":
    unittest.main()
