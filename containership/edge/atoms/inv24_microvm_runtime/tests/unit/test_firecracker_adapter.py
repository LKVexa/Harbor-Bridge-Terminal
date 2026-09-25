"""MC-001 / MC-003 / MC-018: adapter, supervisor and artifact gates against a stub VMM."""
import os
import pathlib
import unittest

from inv24_microvm_runtime.tests.helpers import FakeKvm, make_stub_vmm, pinned_manifest, tmpdir

from inv24_microvm_runtime import MicroVM
from inv24_microvm_runtime.adapters.firecracker import ApiCall, FirecrackerAdapter, _check_fields, build_plan
from inv24_microvm_runtime.devices import BlockSpec, NetSpec, OwnershipRegistry, SerialSpec, VsockSpec
from inv24_microvm_runtime.errors import Inv24Error
from inv24_microvm_runtime.security.artifacts import ArtifactManifest
from inv24_microvm_runtime.supervision.vmm_process import VmmProcess


def _proc_factory(mode):
    def factory(argv, **kw):
        p = VmmProcess(argv, ready_timeout_s=3.0, **kw)
        p.env["STUB_MODE"] = mode
        return p
    return factory


class Fixture:
    def __init__(self, mode="ok"):
        self.dir = tmpdir()
        self.fc = make_stub_vmm(self.dir)
        self.kernel = os.path.join(self.dir, "vmlinux")
        pathlib.Path(self.kernel).write_bytes(b"\x7fELF" + b"\0" * 508)
        self.rootfs = os.path.join(self.dir, "rootfs.ext4")
        pathlib.Path(self.rootfs).write_bytes(b"\0" * 4096)
        self.manifest = ArtifactManifest.load(pinned_manifest(self.dir, firecracker=self.fc,
                                                              guest_kernel=self.kernel, guest_rootfs=self.rootfs))
        self.registry = OwnershipRegistry()
        self.events = []
        self.adapter = FirecrackerAdapter(self.manifest, firecracker_path=self.fc, kernel_path=self.kernel,
                                          rootfs_path=self.rootfs, registry=self.registry,
                                          kvm=FakeKvm().preflight(), process_factory=_proc_factory(mode),
                                          run_dir=self.dir, call_timeout_s=0.5,
                                          on_event=lambda n, d: self.events.append(n))


class PlanTest(unittest.TestCase):
    def test_plan_is_ordered_and_whitelisted(self):
        f = Fixture()
        vm = MicroVM("vm1", "t1", vcpus=2, memory_mib=256, devices={"virtio-block", "virtio-net", "serial"})
        plan = build_plan(vm, [NetSpec("eth0", "tap0", "02:00:00:00:00:01"),
                               BlockSpec("rootfs", f.rootfs, is_root=True), SerialSpec()], kernel_path=f.kernel)
        self.assertEqual([c.path for c in plan], ["/machine-config", "/boot-source", "/drives/rootfs",
                                                  "/network-interfaces/eth0", "/actions"])
        self.assertEqual(plan[0].body, {"vcpu_count": 2, "mem_size_mib": 256, "smt": False})

    def test_undeclared_or_foreign_devices_rejected_before_launch(self):
        f = Fixture()
        vm = MicroVM("vm1", "t1", devices={"serial"})
        with self.assertRaises(Inv24Error) as cm:
            build_plan(vm, [BlockSpec("rootfs", f.rootfs)], kernel_path=f.kernel)
        self.assertEqual(cm.exception.code, "DEVICE_OUTSIDE_MODEL")

        class PciPassthrough:
            kind, device_id = "pci", "gpu0"
        with self.assertRaises(Inv24Error):
            build_plan(vm, [PciPassthrough()], kernel_path=f.kernel)

    def test_unsupported_api_fields_and_actions_rejected(self):
        for call in [ApiCall("PUT", "/machine-config", {"vcpu_count": 1, "cpu_template": "T2"}),
                     ApiCall("PUT", "/mmds", {}), ApiCall("PUT", "/actions", {"action_type": "FlushMetrics"})]:
            with self.subTest(call=call), self.assertRaises(Inv24Error) as cm:
                _check_fields(call)
            self.assertEqual(cm.exception.code, "UNSUPPORTED_FIELD")

    def test_boot_args_injection_rejected(self):
        f = Fixture()
        vm = MicroVM("vm1", "t1")
        for args in ["console=ttyS0 init=/bin/sh", "a\nb"]:
            with self.assertRaises(Inv24Error):
                build_plan(vm, [], kernel_path=f.kernel, boot_args=args)


class ArtifactGateTest(unittest.TestCase):
    def test_modified_binary_rejected_before_exec(self):
        f = Fixture()
        with open(f.fc, "a") as fh:
            fh.write("# tampered\n")
        vm = MicroVM("vm1", "t1")
        with self.assertRaises(Inv24Error) as cm:
            f.adapter.launch(vm, [])
        self.assertEqual(cm.exception.code, "ARTIFACT_DIGEST_MISMATCH")
        self.assertEqual(vm.state, "created")
        self.assertFalse(list(pathlib.Path(f.dir).glob("*.sock")))

    def test_shipped_manifest_is_unpinned_and_fails_closed(self):
        m = ArtifactManifest.load(pathlib.Path(__file__).resolve().parents[3] / "artifacts/firecracker/manifest.json")
        with self.assertRaises(Inv24Error) as cm:
            m.verify("firecracker", "/usr/bin/firecracker")
        self.assertEqual(cm.exception.code, "ARTIFACT_UNPINNED")

    def test_relative_symlink_and_unlisted_rejected(self):
        f = Fixture()
        link = os.path.join(f.dir, "fc-link")
        os.symlink(f.fc, link)
        for name, path, code in [("firecracker", "firecracker", "ARTIFACT_NOT_APPROVED"),
                                 ("firecracker", link, "ARTIFACT_NOT_APPROVED"),
                                 ("jailer", f.fc, "ARTIFACT_NOT_APPROVED")]:
            with self.subTest(path=path), self.assertRaises(Inv24Error) as cm:
                f.manifest.verify(name, path)
            self.assertEqual(cm.exception.code, code)

    def test_floating_versions_refused_in_manifest(self):
        d = tmpdir()
        p = os.path.join(d, "m.json")
        pathlib.Path(p).write_text('{"schema":"PK_MICROVM_ARTIFACTS/1","artifacts":[{"name":"firecracker","version":"latest","sha256":null}]}')
        with self.assertRaises(Inv24Error):
            ArtifactManifest.load(p)


class LaunchTest(unittest.TestCase):
    def test_launch_and_destroy_leaves_no_orphans(self):
        f = Fixture()
        vm = MicroVM("vm1", "t1", devices={"virtio-vsock", "serial"})
        res = f.adapter.launch(vm, [VsockSpec("vsock0", 3, os.path.join(f.dir, "v.sock")), SerialSpec()])
        self.assertEqual(vm.state, "running")
        self.assertEqual(res.api_calls, 4)
        self.assertTrue(res.host.usable)
        self.assertEqual(f.registry.owned_by("t1"), [("cid", "3"), ("uds", os.path.join(f.dir, "v.sock"))])
        proc = f.adapter.processes["vm1"]
        rec = f.adapter.destroy(vm)
        self.assertTrue(rec["destroyed"])
        self.assertFalse(proc.alive())
        self.assertEqual(f.registry.owned_by("t1"), [])
        self.assertFalse(os.path.exists(proc.socket_path))

    def test_failure_classes_are_distinct_and_cleaned(self):
        for mode, code in [("reject", "CONFIG_REJECTED"), ("bootfail", "GUEST_BOOT_FAILED"),
                           ("crash", "PROCESS_CRASHED"), ("hang", "TIMEOUT")]:
            with self.subTest(mode=mode):
                f = Fixture(mode)
                vm = MicroVM("vm1", "t1", devices={"serial"})
                with self.assertRaises(Inv24Error) as cm:
                    f.adapter.launch(vm, [SerialSpec()])
                self.assertEqual(cm.exception.code, code)
                self.assertEqual(f.adapter.processes, {})
                self.assertEqual(f.registry.owned_by("t1"), [])
                self.assertFalse(list(pathlib.Path(f.dir).glob("*.sock")))

    def test_kvm_absent_blocks_launch_before_spawn(self):
        f = Fixture()
        f.adapter.kvm = FakeKvm("absent").preflight()
        vm = MicroVM("vm1", "t1")
        with self.assertRaises(Inv24Error) as cm:
            f.adapter.launch(vm, [])
        self.assertEqual(cm.exception.code, "HOST_KVM_UNAVAILABLE")
        self.assertFalse(list(pathlib.Path(f.dir).glob("*.sock")))

    def test_supervisor_refuses_shell_style_and_relative_exec(self):
        with self.assertRaises(Inv24Error):
            VmmProcess(["firecracker"], socket_path="/tmp/x.sock", version="t")
        with self.assertRaises(Inv24Error):
            VmmProcess([], socket_path="/tmp/x.sock", version="t")

    def test_supervisor_bounds_output_capture(self):
        import sys
        d = tmpdir()
        p = VmmProcess([sys.executable, "-c", "import sys; sys.stdout.write('x'*200000)"],
                       socket_path=os.path.join(d, "s.sock"), version="t")
        p.start()
        p.proc.wait(5)
        p.cleanup()
        self.assertLessEqual(len(p.stdout.data), 64 * 1024)
        self.assertTrue(p.stdout.truncated)


if __name__ == "__main__":
    unittest.main()
