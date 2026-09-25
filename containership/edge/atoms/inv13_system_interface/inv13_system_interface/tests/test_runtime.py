"""Dependency-free security tests for INV-13's reference runtime model."""
import importlib.util
import pathlib
import sys
import unittest

RUNTIME_PATH = pathlib.Path(__file__).resolve().parents[1] / "runtime.py"
SPEC = importlib.util.spec_from_file_location("inv13_runtime_under_test", RUNTIME_PATH)
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)

CapabilityDenied = runtime.CapabilityDenied
Instance = runtime.Instance
PathEscape = runtime.PathEscape
World = runtime.World


class RuntimeSecurityTest(unittest.TestCase):
    def test_world_snapshots_mutable_input(self):
        source = {"filesystem"}
        world = World("svc", source)
        source.add("sockets")
        self.assertEqual(world.capabilities, frozenset({"filesystem"}))

    def test_world_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            World("", frozenset())
        with self.assertRaises(TypeError):
            World("svc", frozenset({1}))
        with self.assertRaises(ValueError):
            World("svc", frozenset({"filesystem", "gpu-direct"}))

    def test_preopen_state_is_read_only_and_canonical(self):
        inst = Instance("api", World("svc", {"filesystem"}))
        inst.grant_preopen("/data", "/srv/data")
        with self.assertRaises(TypeError):
            inst.preopens["/escape"] = "/"
        for logical, host in [
            ("data", "/srv/data"),
            ("/data/", "/srv/data"),
            ("//data", "/srv/data"),
            ("/data", "/srv/../etc"),
            ("/data", "//srv/data"),
        ]:
            with self.subTest(logical=logical, host=host):
                with self.assertRaises(ValueError):
                    inst.grant_preopen(logical, host)

    def test_replacement_requires_explicit_intent(self):
        inst = Instance("api", World("svc", {"filesystem"}))
        inst.grant_preopen("/data", "/srv/a")
        with self.assertRaises(ValueError):
            inst.grant_preopen("/data", "/srv/b")
        inst.grant_preopen("/data", "/srv/b", replace=True)
        self.assertEqual(inst.preopens["/data"], "/srv/b")

    def test_capability_and_path_denials_fail_closed(self):
        inst = Instance("api", World("svc", {"filesystem"}))
        inst.grant_preopen("/data", "/srv/data")
        with self.assertRaises(CapabilityDenied):
            inst.use("sockets")
        with self.assertRaises(CapabilityDenied):
            inst.resolve("/missing", "x")
        for path in ("/etc/passwd", "../../etc/passwd", "reports/../../../root/key", "bad\0name"):
            with self.subTest(path=path):
                with self.assertRaises(PathEscape):
                    inst.resolve("/data", path)
        self.assertTrue(inst.resolve("/data", "reports/q3.csv")["inside_preopen"])

    def test_denial_and_audit_views_are_immutable(self):
        inst = Instance("api", World("svc", {"filesystem"}))
        inst.grant_preopen("/data", "/srv/data")
        with self.assertRaises(CapabilityDenied):
            inst.use("sockets")
        self.assertIsInstance(inst.denials, tuple)
        event = inst.audit_events[-1]
        with self.assertRaises(TypeError):
            event["outcome"] = "granted"
        with self.assertRaises(TypeError):
            event["detail"]["reason"] = "tampered"
        self.assertTrue(inst.verify_audit_chain())
        self.assertEqual(len(inst.audit_head), 64)

    def test_revoke_removes_authority(self):
        inst = Instance("api", World("svc", {"filesystem"}))
        inst.grant_preopen("/data", "/srv/data")
        inst.revoke_preopen("/data")
        with self.assertRaises(CapabilityDenied):
            inst.resolve("/data", "x")


if __name__ == "__main__":
    unittest.main()
