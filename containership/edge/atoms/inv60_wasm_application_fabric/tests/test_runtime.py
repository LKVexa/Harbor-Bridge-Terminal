"""Dependency-free unit tests for the INV-60 lattice runtime."""
import importlib.util
import pathlib
import sys
import unittest

RUNTIME = pathlib.Path(__file__).resolve().parents[1] / "runtime.py"
spec = importlib.util.spec_from_file_location("inv60_runtime", RUNTIME)
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
assert spec.loader is not None
spec.loader.exec_module(runtime)


class LatticeRuntimeTest(unittest.TestCase):
    def test_digest_integrity_and_unknown_artifact_are_atomic(self):
        lat = runtime.Lattice(["h1"])
        ref = lat.push(bytearray(b"wasm"))
        self.assertIsInstance(lat.registry[ref], bytes)
        with self.assertRaises(runtime.UnknownArtifact):
            lat.start("missing", "sha256:" + "0" * 64)
        self.assertEqual(lat.instances, {})
        lat.registry[ref] = b"tampered"
        with self.assertRaises(runtime.DigestMismatch):
            lat.start("api", ref)
        self.assertEqual(lat.instances, {})

    def test_membership_failover_and_last_host_refusal_are_atomic(self):
        lat = runtime.Lattice(["h1", "h2"])
        ref = lat.push(b"wasm")
        lat.start("api", ref)
        victim = lat.instances["api"]
        moved = lat.lose_host(victim)
        self.assertEqual(moved, ["api"])
        self.assertNotEqual(lat.instances["api"], victim)
        self.assertEqual(lat.failovers, 1)
        before = (list(lat.hosts), dict(lat.instances), lat.failovers)
        with self.assertRaises(LookupError):
            lat.lose_host(lat.hosts[0])
        self.assertEqual((lat.hosts, lat.instances, lat.failovers), before)

    def test_lifecycle_revokes_links(self):
        lat = runtime.Lattice(["h1"])
        ref = lat.push(b"wasm")
        lat.start("api", ref)
        lat.link("api", "kv", lambda key: key.upper())
        self.assertEqual(lat.call("api", "kv", "a"), "A")
        with self.assertRaises(runtime.AlreadyRunning):
            lat.start("api", ref)
        lat.unlink("api", "kv")
        with self.assertRaises(runtime.NotLinked):
            lat.call("api", "kv", "a")
        lat.link("api", "kv", lambda key: key)
        lat.stop("api")
        self.assertNotIn(("api", "kv"), lat.links)
        with self.assertRaises(LookupError):
            lat.call("api", "kv", "a")

    def test_configuration_validation_and_host_add(self):
        with self.assertRaises(runtime.InvalidConfiguration):
            runtime.Lattice(["h1", "h1"])
        lat = runtime.Lattice([])
        lat.add_host("h1")
        with self.assertRaises(runtime.InvalidConfiguration):
            lat.add_host("h1")
        with self.assertRaises(TypeError):
            lat.push("not bytes")


if __name__ == "__main__":
    unittest.main()
