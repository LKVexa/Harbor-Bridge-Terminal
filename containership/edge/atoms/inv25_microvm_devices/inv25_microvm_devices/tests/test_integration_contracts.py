"""Item 14 adjacent-layer contract scenarios against the version-pinned peer fixtures."""
import sys
import unittest

from _support import ALL, PKG_DIR, Clock, spec, store, token, verifier

sys.path.insert(0, str(PKG_DIR / "conformance" / "integration"))
import peer_contracts as pc  # noqa: E402


def setup(**kw):
    v = verifier(Clock())
    s = store.CatalogueStore("prod", v, mutation_burst=1000)
    for sp in (spec("virtio-net", regs=("queue_sel", "status")), spec("virtio-block", regs=("capacity",))):
        c = s.propose(token(v, "alice", ALL), "register", sp)
        s.approve(token(v, "bob", ["catalogue.approve"]), c["candidate"])
        s.activate(token(v, "alice", ALL), c["candidate"], expected_digest=c["base"])
    rt = pc.Runtime(s, kw.get("policy", pc.PolicyEngine()), kw.get("io", pc.IoBackend()), kw.get("tx"))
    return s, v, rt


class IntegrationContractTest(unittest.TestCase):
    def test_runtime_accepts_catalogued(self):
        s, v, rt = setup()
        vm = rt.boot("w1", ["virtio-net", "virtio-block"], "corr-1")
        self.assertEqual(vm["catalogue_digest"], s.active.digest)
        self.assertEqual(vm["correlation_id"], "corr-1")

    def test_runtime_rejects_uncatalogued_and_forbidden(self):
        s, v, rt = setup()
        for dev in ("virtio-gpu", "legacy-ide", "host-pci-0000:00:1f"):
            with self.subTest(dev), self.assertRaises(pc.PeerError) as cm:
                rt.boot("w", [dev], "c")
            self.assertEqual(cm.exception.code, "INV25_UNAUTHORIZED")

    def test_missing_backend_is_terminal_not_substituted(self):
        s, v, rt = setup(io=pc.IoBackend(backends=("virtio-net",)))
        with self.assertRaises(pc.PeerError) as cm:
            rt.boot("w", ["virtio-block"], "c")
        self.assertEqual(cm.exception.code, "INV25_DEPENDENCY_UNAVAILABLE")

    def test_policy_narrows_never_expands(self):
        s, v, rt = setup(policy=pc.PolicyEngine(deny={"virtio-block"}))
        with self.assertRaises(pc.PeerError):
            rt.boot("w", ["virtio-block"], "c")
        d = pc.PolicyEngine().decide("w", "prod", ["virtio-gpu"], s.active.digest, {"virtio-net"})
        self.assertEqual(d["allowed"], [])

    def test_policy_unavailable_fails_closed(self):
        s, v, rt = setup(policy=pc.PolicyEngine(available=False))
        with self.assertRaises(pc.PeerError) as cm:
            rt.boot("w", ["virtio-net"], "c")
        self.assertEqual(cm.exception.code, "INV25_DEPENDENCY_UNAVAILABLE")

    def test_emergency_disabled_device_not_bootable(self):
        s, v, rt = setup()
        s.emergency_disable(token(v, "op", ["catalogue.emergency_disable"], bg=True), "virtio-net",
                            reason="cve", incident_id="INC-9", expires="2026-12-01T00:00:00Z")
        with self.assertRaises(pc.PeerError):
            rt.boot("w", ["virtio-net"], "c")

    def test_snapshot_restore_rejects_surface_change(self):
        s, v, rt = setup()
        snapper = pc.Snapshotter()
        snap = snapper.save(rt.boot("w", ["virtio-net"], "c"))
        self.assertTrue(snapper.restore(snap, s))
        c = s.propose(token(v, "alice", ALL), "replace", spec("virtio-net", "1.1", ("queue_sel", "status", "mq")))
        s.approve(token(v, "bob", ["catalogue.approve"]), c["candidate"])
        s.activate(token(v, "alice", ALL), c["candidate"], expected_digest=c["base"])
        with self.assertRaises(pc.PeerError) as cm:
            snapper.restore(snap, s)
        self.assertEqual(cm.exception.code, "INV25_COMPATIBILITY_MISMATCH")

    def test_optional_transient_peer(self):
        s, v, rt = setup()
        self.assertEqual(rt.boot("w", ["virtio-net"], "c")["transient"]["status"], "not-evaluated")
        s, v, rt = setup(tx=pc.TransientDefense(sensitive={"virtio-net"}))
        self.assertEqual(rt.boot("w", ["virtio-net"], "c")["transient"]["speculation_sensitive"], ["virtio-net"])


if __name__ == "__main__":
    unittest.main()
