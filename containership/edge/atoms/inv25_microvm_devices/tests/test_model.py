"""Standalone domain-model tests; no pk_core dependency required."""
import importlib.util
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("inv25_model", PKG_DIR / "model.py")
model = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = model
spec.loader.exec_module(model)

DeviceCatalogue = model.DeviceCatalogue
DeviceRejected = model.DeviceRejected
DeviceSpec = model.DeviceSpec


def good(name="virtio-net", version="1.0", registers=frozenset({"status"})):
    return DeviceSpec(name, "paravirtual", version, registers, "required by guest", "sec-team")


class DeviceModelTest(unittest.TestCase):
    def test_register_export_and_surface(self):
        cat = DeviceCatalogue("prod")
        cat.register(good())
        self.assertEqual(cat.total_surface(), 1)
        self.assertEqual(cat.export()["schema"], "PK_DEVICE_CATALOGUE/1")
        self.assertEqual(cat.export()["devices"][0]["name"], "virtio-net")

    def test_forbidden_and_unknown_classes_are_closed_fail(self):
        for cls in ("legacy-emulation", "host-passthrough", "raw-mmio", "emulated-ide", "Host-Passthrough"):
            with self.subTest(cls=cls), self.assertRaises(DeviceRejected):
                DeviceCatalogue("prod").register(DeviceSpec("x", cls, "1.0", frozenset(), "r", "reviewer"))

    def test_rejects_malformed_entries(self):
        bad = [
            DeviceSpec("", "paravirtual", "1.0", frozenset(), "r", "reviewer"),
            DeviceSpec("../escape", "paravirtual", "1.0", frozenset(), "r", "reviewer"),
            DeviceSpec("virtio-net", "paravirtual", "latest", frozenset(), "r", "reviewer"),
            DeviceSpec("virtio-net", "paravirtual", "1.0", {"status"}, "r", "reviewer"),
            DeviceSpec("virtio-net", "paravirtual", "1.0", frozenset({"bad register"}), "r", "reviewer"),
            DeviceSpec("virtio-net", "paravirtual", "1.0", frozenset(), "", "reviewer"),
        ]
        for entry in bad:
            with self.subTest(entry=entry), self.assertRaises(DeviceRejected):
                DeviceCatalogue("prod").register(entry)

    def test_changed_reregistration_requires_replace(self):
        cat = DeviceCatalogue("prod")
        cat.register(good())
        with self.assertRaises(DeviceRejected):
            cat.register(good(version="1.1", registers=frozenset({"status", "feature"})))
        diff = cat.replace(good(version="1.1", registers=frozenset({"status", "feature"})))
        self.assertTrue(diff["widened"])
        self.assertEqual(diff["added"], ["feature"])
        self.assertEqual(cat.devices["virtio-net"].version, "1.1")

    def test_changed_entry_cannot_reuse_version(self):
        cat = DeviceCatalogue("prod")
        cat.register(good())
        with self.assertRaises(DeviceRejected):
            cat.replace(good(registers=frozenset({"status", "feature"})))

    def test_diff_rejects_different_devices(self):
        with self.assertRaises(ValueError):
            DeviceCatalogue.diff(good(), good(name="virtio-block"))


if __name__ == "__main__":
    unittest.main()
