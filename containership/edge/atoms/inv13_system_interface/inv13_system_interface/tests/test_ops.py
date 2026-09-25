"""MC-014 atomic config, MC-015 durable audit, MC-016/029 telemetry+privacy, MC-017 quotas, MC-027 controls."""
import json, os, threading, unittest
import _fx
from inv13_system_interface.host.config import ConfigStore
from inv13_system_interface.host.audit_sink import AuditSink, verify_file
from inv13_system_interface.host.telemetry import Metrics, PrivacyFilter, StructuredLog, classify, parse_traceparent, child_traceparent
from inv13_system_interface.host.quotas import QuotaLedger, Admission
from inv13_system_interface.host.control import ControlPlane
from inv13_system_interface.host.descriptors import DescriptorTable
from inv13_system_interface.host.errors import ErrorCode, Inv13Error


def bundle(v, root="/srv/tenant-a"):
    return {"schema": "INV13_CONFIG/1", "version": v, "author": "ops", "policy": _fx.policy_doc(root)}


class Config(unittest.TestCase):
    def setUp(self):
        self.d = _fx.tmpdir()
        self.s = ConfigStore(self.d)

    def test_stage_activate_cas_rollback(self):
        d1, d2 = self.s.stage(bundle(1)), self.s.stage(bundle(2))
        self.s.activate(d1, expected_previous=None, actor="a", reason="init")
        with self.assertRaises(Inv13Error):
            self.s.activate(d2, expected_previous=None, actor="b", reason="racing writer")
        self.s.activate(d2, expected_previous=d1, actor="a", reason="upgrade")
        self.assertEqual(self.s.load()["version"], 2)
        self.assertEqual(self.s.rollback(actor="a", reason="bad release"), d1)
        self.assertEqual(self.s.load()["version"], 1)
        self.assertEqual([h["reason"] for h in self.s.history()][-1], "rollback: bad release")

    def test_invalid_bundle_never_staged(self):
        bad = bundle(1); bad["policy"]["tenants"]["tenant-a"]["rules"][0]["preopens"]["/data"]["host_root"] = "/etc"
        with self.assertRaises(Inv13Error):
            self.s.stage(bad)
        self.assertEqual(list((self.d / "staged").iterdir()), [])

    def test_crash_between_steps_leaves_old_config(self):
        d1 = self.s.stage(bundle(1))
        self.s.activate(d1, expected_previous=None, actor="a", reason="init")
        d2 = self.s.stage(bundle(2))
        for stage in ("before-pointer-swap", "before-active-replace"):
            def fault(s, stage=stage):
                if s == stage: raise RuntimeError("control plane crashed")
            st = ConfigStore(self.d, fault=fault)
            with self.assertRaises(RuntimeError):
                st.activate(d2, expected_previous=d1, actor="a", reason="x")
            self.assertEqual(ConfigStore(self.d).active(), d1)
        (self.d / ".ACTIVE.tmp-1-1").write_text("partial")
        self.assertEqual(self.s.recover(), 1)

    def test_corrupted_stage_detected(self):
        d1 = self.s.stage(bundle(1))
        p = self.d / "staged" / f"{d1}.json"
        p.write_text(p.read_text().replace("ops", "evil"))
        with self.assertRaises(Inv13Error):
            self.s.load(d1)


class Audit(unittest.TestCase):
    def setUp(self):
        self.path = str(_fx.tmpdir() / "audit.jsonl")

    def sink(self, **kw):
        return AuditSink(self.path, node="n1", release="4.3.0", checkpoint_key=_fx.CP_KEY, checkpoint_every=4, **kw)

    def test_durable_chain_and_reopen(self):
        s = self.sink()
        for i in range(10):
            s.append("api", "capability.use", "granted", {"capability": "stdio"})
        s.seal(); s.close()
        ok, info = verify_file(self.path, _fx.CP_KEY)
        self.assertTrue(ok, info)
        self.assertEqual((info["seq"], info["unsealed_tail"]), (10, 0))
        s2 = self.sink(); s2.append("api", "x", "y", {}); s2.close()        # continues the chain
        self.assertTrue(verify_file(self.path, _fx.CP_KEY)[0])
        rec = json.loads(open(self.path).readline())
        self.assertEqual((rec["node"], rec["release"], rec["workload"]), ("n1", "4.3.0", "api"))

    def test_tamper_detection(self):
        s = self.sink()
        for i in range(8):
            s.append("api", "a", "granted", {"count": i})
        s.close()
        lines = open(self.path).read().splitlines()
        variants = {
            "edit": [l.replace('"granted"', '"denied"', 1) if i == 2 else l for i, l in enumerate(lines)],
            "delete": lines[:2] + lines[3:],
            "reorder": [lines[1], lines[0]] + lines[2:],
            "truncate-mid": lines[:-1] + [lines[-1][:10]],
        }
        for name, v in variants.items():
            open(self.path, "w").write("\n".join(v) + "\n")
            self.assertFalse(verify_file(self.path, _fx.CP_KEY)[0], name)
        # full rewrite with recomputed digests but no checkpoint key is caught by checkpoint MAC
        forged = [json.loads(l) for l in lines]
        for r in forged:
            if r.get("t") == "cp": r["mac"] = "0" * 64
        open(self.path, "w").write("\n".join(json.dumps(r) for r in forged) + "\n")
        self.assertFalse(verify_file(self.path, _fx.CP_KEY)[0])
        with self.assertRaises(Inv13Error):
            self.sink()   # refuses to append to a corrupted log

    def test_privacy_filter_applied_before_write(self):
        s = self.sink(privacy=PrivacyFilter(b"region-eu-salt-01"))
        s.append("api", "path.resolve", "denied", {"path": "/srv/tenant-a/secret", "token": "abc", "code": "E1003"})
        s.close()
        raw = open(self.path).read()
        self.assertNotIn("/srv/tenant-a", raw)
        self.assertNotIn("abc", raw)
        self.assertIn("E1003", raw)


class Telemetry(unittest.TestCase):
    def test_cardinality_bounded(self):
        m = Metrics()
        for i in range(1000):
            m.inc("ops", capability=f"attacker-{i}", op="open", outcome="ok", user=str(i))
        self.assertEqual(m.series_count(), 1)
        self.assertIn('capability="other"', m.exposition())

    def test_outcome_classes_separated(self):
        self.assertEqual(classify(None), "ok")
        self.assertEqual(classify(Inv13Error(ErrorCode.PATH_ESCAPE)), "attack")
        self.assertEqual(classify(Inv13Error(ErrorCode.CAP_NOT_GRANTED)), "denial")
        self.assertEqual(classify(Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE)), "dependency")
        self.assertEqual(classify(Inv13Error(ErrorCode.QUOTA_EXCEEDED)), "overload")
        self.assertEqual(classify(ValueError()), "defect")

    def test_traceparent(self):
        tp = child_traceparent(None)
        p = parse_traceparent(tp)
        self.assertIsNotNone(p)
        self.assertEqual(parse_traceparent(child_traceparent(tp))[0], p[0])
        for bad in ("", "00-" + "0" * 32 + "-" + "1" * 16 + "-01", "zz", None, "01-" + "a" * 32 + "-" + "b" * 16 + "-01"):
            self.assertIsNone(parse_traceparent(bad))

    def test_structured_log_privacy_and_bound(self):
        log = StructuredLog(PrivacyFilter(b"salt-salt-salt-1"), limit=2)
        log.emit("warn", "deny", tenant="tenant-a", path="/srv/x", secret="s3", code="E1001")
        rec = json.loads(log.records[0])
        self.assertTrue(rec["tenant"].startswith("p:"))
        self.assertTrue(rec["path"].startswith("h:"))
        self.assertNotIn("secret", rec)
        log.emit("i", "a"); log.emit("i", "b")
        self.assertEqual(log.dropped, 1)


class Quotas(unittest.TestCase):
    def test_hierarchical_limits(self):
        q = QuotaLedger({"a": {"sockets": 3}}, workload_limits={"sockets": 2})
        q.acquire("a", "w1", "sockets", 2)
        with self.assertRaises(Inv13Error):
            q.acquire("a", "w1", "sockets")          # workload limit
        q.acquire("a", "w2", "sockets")
        with self.assertRaises(Inv13Error):
            q.acquire("a", "w3", "sockets")          # tenant limit
        with self.assertRaises(Inv13Error):
            q.acquire("unknown", "w", "sockets")
        q.release("a", "w1", "sockets", 2)
        with self.assertRaises(Inv13Error):
            q.release("a", "w1", "sockets")          # underflow detected

    def test_admission_fairness_and_shedding(self):
        ad = Admission(node_slots=10, fair_share=0.5)
        self.assertTrue(ad.try_admit("b"))
        admitted_a = sum(ad.try_admit("a") for _ in range(20))
        self.assertEqual(admitted_a, 5)
        self.assertTrue(ad.try_admit("b"))
        self.assertGreater(ad.shed, 0)


class Controls(unittest.TestCase):
    def setUp(self):
        self.audit = AuditSink(str(_fx.tmpdir() / "a.jsonl"), node="n", release="4.3.0", checkpoint_key=_fx.CP_KEY)
        self.dt = DescriptorTable()
        self.cfg = ConfigStore(_fx.tmpdir())
        self.cp = ControlPlane(identity=_fx.gate(), audit=self.audit, descriptors=self.dt, config=self.cfg)
        self.d = self.dt.mint(tenant="a", workload="api", capability="stdio", scope={}, rights={"invoke"},
                              provenance={"decision": "x", "actor": "y"})

    def op(self):
        return _fx.token(role="operator", workload=None)

    def test_quarantine_revokes_and_blocks(self):
        with self.assertRaises(Inv13Error):
            self.cp.quarantine(_fx.token(role="runtime"), "api", "suspicious")   # runtime cannot operate controls
        self.assertIn(self.d.id, self.cp.quarantine(self.op(), "api", "IOC match"))
        with self.assertRaises(Inv13Error) as cm:
            self.cp.guard("api")
        self.assertEqual(cm.exception.code, ErrorCode.QUARANTINED)
        with self.assertRaises(Inv13Error):
            self.dt.check(self.d.id)
        self.cp.release(self.op(), "api", "cleared")
        self.cp.guard("api")

    def test_emergency_disable_freeze_rollback_recorded(self):
        self.cp.emergency_disable(self.op(), "http-outgoing", "CVE")
        with self.assertRaises(Inv13Error):
            self.cp.guard("api", "http-outgoing")
        self.cp.freeze(self.op(), "incident")
        with self.assertRaises(Inv13Error) as cm:
            self.cp.guard("api", "stdio", mutation=True)
        self.assertEqual(cm.exception.code, ErrorCode.FROZEN)
        self.cp.guard("api", "stdio")                 # reads continue
        d1 = self.cfg.stage(bundle(1)); d2 = self.cfg.stage(bundle(2))
        self.cfg.activate(d1, expected_previous=None, actor="x", reason="i")
        self.cfg.activate(d2, expected_previous=d1, actor="x", reason="u")
        self.assertEqual(self.cp.rollback_config(self.op(), "regression"), d1)
        with self.assertRaises(Inv13Error):
            self.cp.freeze(self.op(), "")             # reason mandatory
        self.audit.close()
        ok, info = verify_file(self.audit.path, _fx.CP_KEY)
        self.assertTrue(ok)
        self.assertEqual(info["seq"], 3)   # disable, freeze, rollback; rejected op not recorded as applied


if __name__ == "__main__":
    unittest.main()
