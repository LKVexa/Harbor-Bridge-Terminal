import json, os, tempfile, unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.audit.emitter import AuditLog
from inv65_capability_providers.audit.verification import verify_chain, verify_file
from inv65_capability_providers.schemas import check


class AuditChain(unittest.TestCase):
    def test_every_sensitive_action_audited_and_chain_verifies(self):
        w = World(); w.svc.start(); w.link(); w.call(); w.unlink()
        try:
            w.call()
        except Exception:
            pass
        ev = w.svc.audit.events()
        self.assertEqual([e["action"] for e in ev], ["provider.start", "link.create", "link.revoke", "provider.call"])
        self.assertEqual(ev[-1]["outcome"], "deny")
        for e in ev:
            check(e, "audit_event")
        self.assertEqual(verify_chain(ev, expected_head=w.svc.audit.head), (True, "ok"))

    def test_tamper_reorder_truncate_detected(self):
        a = AuditLog()
        for i in range(5):
            a.emit("link.create", "allow", "p", f"s{i}")
        ev = a.events()
        bad = [dict(e) for e in ev]; bad[2]["subject"] = "x"
        self.assertFalse(verify_chain(bad)[0])
        self.assertFalse(verify_chain([ev[0], ev[2], ev[1], ev[3], ev[4]])[0])
        self.assertFalse(verify_chain(ev[:4], expected_head=a.head)[0])

    def test_file_mirror_reloads_and_refuses_tampered_file(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "audit.jsonl")
        a = AuditLog(p); a.emit("provider.start", "ok", "i", "s"); a.emit("link.create", "allow", "p", "s")
        self.assertEqual(len(AuditLog(p).events()), 2)
        lines = open(p).read().splitlines(); e = json.loads(lines[0]); e["actor"] = "evil"; lines[0] = json.dumps(e)
        open(p, "w").write("\n".join(lines) + "\n")
        self.assertFalse(verify_file(p)[0])
        with self.assertRaises(RuntimeError):
            AuditLog(p)
