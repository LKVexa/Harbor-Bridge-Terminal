"""Adapter tests across real Unix-socket process boundaries (X001, X002, C030 partial, C083 partial).

These run the Firecracker / Cloud Hypervisor REST clients and the vsock entropy
injector against protocol fakes (tests/fakes.py) through the *full* service
path: capture -> encrypt -> store -> verify -> grant -> decrypt -> load(paused)
-> reseed over vsock with proof -> resume. They are not evidence of
compatibility with a real VMM (no /dev/kvm here)."""
import os
import unittest

from inv26_microvm_snapshotting.errors import SnapshotServiceError
from inv26_microvm_snapshotting.hypervisor import (CloudHypervisorAdapter, FirecrackerAdapter,
                                                   VsockAgentInjector)
from inv26_microvm_snapshotting.tests.fakes import FakeGuestAgent, FakeVMM
from inv26_microvm_snapshotting.tests.harness import Rig


class _NoBootRig(Rig):
    def capture(self, sid="s1", tenant="t1", vm="vm-1", **over):
        st, body = self.svc.handle("capture", self.token(tenant=tenant), self.capture_req(sid, tenant, vm, **over))
        assert st == 200, body
        return body


class FirecrackerEndToEnd(unittest.TestCase):
    def setUp(self):
        self.src, self.dst = FakeVMM("firecracker"), FakeVMM("firecracker")
        self.agent = FakeGuestAgent()
        self.killed = []
        self.hv = FirecrackerAdapter({"vm-1": self.src.path, "vm-2": self.dst.path}, killer=self.killed.append)
        self.inj = VsockAgentInjector({"vm-2": self.agent.path})
        self.r = _NoBootRig(hv=self.hv, entropy=self.inj)

    def tearDown(self):
        for x in (self.src, self.dst, self.agent):
            x.close()

    def test_full_path(self):
        snap = self.r.capture()
        self.assertEqual([c[1] for c in self.src.calls], ["/vm", "/snapshot/create"])
        self.assertEqual(self.src.calls[0][2], {"state": "Paused"})
        st, body = self.r.restore(snap, vm="vm-2")
        self.assertEqual(st, 200, body)
        self.assertEqual(self.dst.loaded[1], self.src.memory)  # byte-exact guest memory after AEAD round trip
        self.assertEqual(self.dst.load_file_modes, [0o600])
        load = [c for c in self.dst.calls if c[1] == "/snapshot/load"][0][2]
        self.assertIs(load["resume_vm"], False)  # loaded paused; resumed only after entropy ack
        self.assertEqual(self.dst.calls[-1], ("PATCH", "/vm", {"state": "Resumed"}))
        self.assertEqual(len(self.agent.seeds), 1)
        import hashlib
        self.assertEqual(hashlib.sha256(self.agent.seeds[0]).hexdigest(), body["entropy_proof_sha256"])
        # plaintext working files were wiped
        self.assertEqual([p for p in (self.r.root / "work").rglob("*") if p.is_file()], [])

    def test_lying_agent_fails_closed_and_guest_destroyed(self):
        self.agent.mode = "lie"
        snap = self.r.capture()
        st, body = self.r.restore(snap, vm="vm-2")
        self.assertEqual(body["code"], "SNAP_ENTROPY_FAILED")
        self.assertEqual(self.killed, ["vm-2"])
        self.assertNotIn(("PATCH", "/vm", {"state": "Resumed"}), self.dst.calls)

    def test_refusing_agent(self):
        self.agent.mode = "refuse"
        snap = self.r.capture()
        self.assertEqual(self.r.restore(snap, vm="vm-2")[1]["code"], "SNAP_ENTROPY_FAILED")

    def test_vmm_error_is_mapped(self):
        self.dst.fail_paths.add("/snapshot/load")
        snap = self.r.capture()
        st, body = self.r.restore(snap, vm="vm-2")
        self.assertEqual(body["code"], "SNAP_HYPERVISOR_FAILED")
        self.assertEqual(self.killed[-1], "vm-2")

    def test_missing_socket(self):
        hv = FirecrackerAdapter({"vm-x": "/nonexistent/sock"})
        with self.assertRaises(SnapshotServiceError) as cm:
            hv.pause("vm-x")
        self.assertEqual(cm.exception.code, "SNAP_HYPERVISOR_FAILED")
        with self.assertRaises(SnapshotServiceError):
            hv.pause("unregistered")


class CloudHypervisorEndToEnd(unittest.TestCase):
    def test_full_path(self):
        src, dst, agent = FakeVMM("cloud-hypervisor"), FakeVMM("cloud-hypervisor"), FakeGuestAgent()
        try:
            hv = CloudHypervisorAdapter({"vm-1": src.path, "vm-2": dst.path})
            r = _NoBootRig(hv=hv, entropy=VsockAgentInjector({"vm-2": agent.path}))
            snap = r.capture()
            st, body = r.restore(snap, vm="vm-2")
            self.assertEqual(st, 200, body)
            self.assertEqual(dst.loaded[1], src.memory)
            self.assertEqual([c[1] for c in dst.calls], ["/api/v1/vm.restore", "/api/v1/vm.resume"])
        finally:
            for x in (src, dst, agent):
                x.close()


class ConfigAdapterBinding(unittest.TestCase):
    def test_service_refuses_mismatched_adapter(self):
        from inv26_microvm_snapshotting.hypervisor import ReferenceHypervisor
        r = Rig()
        fc = FirecrackerAdapter({})
        with self.assertRaises(SnapshotServiceError):
            r.svc.__class__(meta=r.meta, config=r.cfgstore, blobs=r.blobs, kms=r.kms, hypervisor=fc,
                            entropy=r.entropy, authn=r.authn, audit=r.audit, node_id="n")


if __name__ == "__main__":
    unittest.main()
