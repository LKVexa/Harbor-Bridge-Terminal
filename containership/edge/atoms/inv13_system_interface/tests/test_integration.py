"""End-to-end: identity + policy + descriptors + fs + quotas + audit + telemetry + control."""
import os, unittest
import _fx
from inv13_system_interface.host.host import Host
from inv13_system_interface.host.policy import PolicyEngine
from inv13_system_interface.host.audit_sink import AuditSink, verify_file
from inv13_system_interface.host.quotas import QuotaLedger
from inv13_system_interface.host.telemetry import PrivacyFilter
from inv13_system_interface.host.errors import ErrorCode, Inv13Error


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.root = _fx.tmpdir()
        (self.root / "in.txt").write_text("payload")
        self.audit = AuditSink(str(_fx.tmpdir() / "audit.jsonl"), node="n1", release="4.3.0",
                               checkpoint_key=_fx.CP_KEY, privacy=PrivacyFilter(b"eu-west-salt-0001"))
        self.host = Host(policy=PolicyEngine(_fx.policy_doc(str(self.root))), identity=_fx.gate(),
                         audit=self.audit, quotas=QuotaLedger({"tenant-a": {"descriptors": 4}},
                                                               workload_limits={"descriptors": 4}))

    def inst(self, **kw):
        args = dict(tenant="tenant-a", workload="api", world="batch-file-worker",
                    preopens={"/data": (str(self.root), {"read", "write", "create"})})
        args.update(kw)
        return self.host.instantiate(_fx.token(workload=args["workload"]), **args)

    def test_happy_path_and_audit(self):
        i = self.inst()
        h = i.open("/data", "in.txt")
        self.assertEqual(i.read(h), b"payload")
        i.close(h)
        w = i.open("/data", "out.txt", os.O_WRONLY | os.O_CREAT)
        i.write(w, b"done"); i.close(w)
        self.assertEqual((self.root / "out.txt").read_text(), "done")
        self.assertGreater(i.monotonic(), 0)
        with self.assertRaises(Inv13Error) as cm:
            i.random(8)                       # world batch-file-worker has no random
        self.assertEqual(cm.exception.code, ErrorCode.CAP_NOT_GRANTED)
        self.assertEqual(i.shutdown(), 0)
        self.audit.close()
        ok, info = verify_file(self.audit.path, _fx.CP_KEY)
        self.assertTrue(ok)
        raw = open(self.audit.path).read()
        self.assertNotIn(str(self.root), raw)    # host paths never retained in clear
        self.assertEqual(self.host.metrics.get("ops", capability="random", op="random", outcome="denial"), 1)

    def test_denials_are_end_to_end(self):
        with self.assertRaises(Inv13Error):                     # policy: rng-* rule does not allow filesystem world
            self.inst(workload="rng-1")
        with self.assertRaises(Inv13Error):                     # token bound to another workload
            self.host.instantiate(_fx.token(workload="other"), tenant="tenant-a", workload="api",
                                  world="batch-file-worker")
        with self.assertRaises(Inv13Error):                     # preopen outside tenant root
            self.inst(preopens={"/data": ("/etc", {"read"})})
        i = self.inst()
        with self.assertRaises(Inv13Error) as cm:
            i.open("/data", "../../etc/passwd")
        self.assertEqual(cm.exception.code, ErrorCode.PATH_ESCAPE)
        os.symlink("/etc/passwd", self.root / "pw")
        with self.assertRaises(Inv13Error) as cm:
            i.open("/data", "pw")
        self.assertEqual(cm.exception.code, ErrorCode.SYMLINK_REFUSED)
        self.assertEqual(self.host.metrics.get("ops", capability="filesystem", op="open", outcome="attack"), 2)

    def test_quota_quarantine_revocation(self):
        i = self.inst()
        hs = [i.open("/data", "in.txt") for _ in range(4)]
        with self.assertRaises(Inv13Error) as cm:
            i.open("/data", "in.txt")
        self.assertEqual(cm.exception.code, ErrorCode.QUOTA_EXCEEDED)
        i.close(hs[0])
        hs[0] = i.open("/data", "in.txt")      # released descriptor quota is reusable
        self.host.control.quarantine(_fx.token(role="operator", workload=None), "api", "drill")
        with self.assertRaises(Inv13Error) as cm:
            i.read(hs[1])
        self.assertEqual(cm.exception.code, ErrorCode.QUARANTINED)
        self.host.control.release(_fx.token(role="operator", workload=None), "api", "drill over")
        with self.assertRaises(Inv13Error) as cm:        # descriptors stay revoked after release
            i.read(hs[1])
        self.assertEqual(cm.exception.code, ErrorCode.STALE_HANDLE)
        i.shutdown()


if __name__ == "__main__":
    unittest.main()
