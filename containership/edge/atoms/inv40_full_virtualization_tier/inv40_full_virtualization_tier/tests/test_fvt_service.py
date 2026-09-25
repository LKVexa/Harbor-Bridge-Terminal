"""Service-level contract, integration, fault-injection, concurrency and
security tests for FullVmService over the FakeProvider (non-production lane)."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest

from _support import DIGEST, keys, req, tok
from fvt import audit, errors, fencing, schema
from fvt.provider import FakeProvider
from fvt.service import FullVmService


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kp = keys()
        self.prov = FakeProvider()
        self.svc = self.make()

    def make(self, **kw):
        return FullVmService(provider=kw.pop("provider", self.prov), keys=self.kp, state_dir=self.tmp.name,
                             sleep=lambda s: None, **kw)

    def tearDown(self):
        self.tmp.cleanup()

    def t(self, **kw):
        return tok(self.kp, **kw)

    def new(self, **kw):
        return self.svc.create(self.t(), req(**kw))["instance_id"]


class ContractTest(Base):
    def test_lifecycle_documents_match_schemas(self):
        c = self.svc.create(self.t(), req())
        self.assertEqual(c["schema"], "PK_FULL_VM/1")
        b = self.svc.boot(self.t(), c["instance_id"])
        schema.validate(b, schema.load("PK_FULL_VM_BOOT.v1"))
        s = self.svc.stop(self.t(), c["instance_id"])
        schema.validate(s, schema.load("PK_FULL_VM_STATE.v1"))
        self.svc.boot(self.t(), c["instance_id"])   # restart from stopped
        d = self.svc.destroy(self.t(), c["instance_id"])
        schema.validate(d, schema.load("PK_FULL_VM_STATE.v1"))
        d2 = self.svc.destroy(self.t(), c["instance_id"])
        self.assertTrue(d2["idempotent"])

    def test_errors_are_machine_readable(self):
        with self.assertRaises(errors.OpError) as cm:
            self.svc.create(self.t(), "{not json")
        schema.validate(cm.exception.as_dict(), schema.load("PK_FULL_VM_ERROR.v1"))

    def test_idempotent_create(self):
        r = req(key="same")
        a = self.svc.create(self.t(), r)
        b = self.svc.create(self.t(), r)
        self.assertEqual(a["instance_id"], b["instance_id"])
        self.assertTrue(b["idempotent_replay"])
        with self.assertRaises(errors.OpError):
            self.svc.create(self.t(), dict(r, memory_mib=512))

    def test_degraded_boot_reported(self):
        self.prov.boot_ms = 9000
        b = self.svc.boot(self.t(), self.new())
        self.assertEqual(b["status"], "degraded")
        self.assertTrue(any(d["outcome"] == "degraded" for d in self.svc.decisions.all()))


class SecurityTest(Base):
    def test_cross_tenant_denied_and_audited(self):
        iid = self.new()
        with self.assertRaises(errors.OpError) as cm:
            self.svc.boot(self.t(tenants=("t2",)), iid)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_FORBIDDEN")
        recs = self.svc.audit.records()
        self.assertEqual(recs[-1]["outcome"], "deny")
        self.assertEqual(audit.AuditLog.verify(recs), (True, None))

    def test_read_only_token_cannot_mutate(self):
        with self.assertRaises(errors.OpError):
            self.svc.create(self.t(ops=("read",)), req())

    def test_no_software_fallback(self):
        self.prov.usable = False
        iid = self.new()
        with self.assertRaises(errors.OpError) as cm:
            self.svc.boot(self.t(), iid)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_PRIMITIVE_REQUIRED")
        self.assertEqual(self.prov.launches, 0)
        self.assertFalse(self.svc.health()["ready"])

    def test_footprint_breach_leaves_no_orphan(self):
        self.prov.resident_mib = 4096
        iid = self.new()
        with self.assertRaises(errors.OpError):
            self.svc.boot(self.t(), iid)
        self.assertEqual(self.prov.live, {})
        self.assertEqual(self.svc.registry.active_claim_count(), 0)

    def test_unapproved_image_and_gpu_policy(self):
        svc = self.make(config={"approved_image_digests": ["sha256:" + "b" * 64]})
        with self.assertRaises(errors.OpError) as cm:
            svc.create(self.t(), req())
        self.assertEqual(cm.exception.code, "PK_FULL_VM_INTEGRITY_FAILED")
        with self.assertRaises(errors.OpError):
            self.svc.create(self.t(), req(extra_devices=["gpu-passthrough"]))

    def test_prod_refuses_nonproduction_provider(self):
        import tempfile as tf
        with tf.TemporaryDirectory() as d, self.assertRaises(errors.OpError):
            FullVmService(provider=FakeProvider(), keys=self.kp, state_dir=d,
                          config={"environment": "prod", "approved_image_digests": [DIGEST]})

    def test_key_service_down_fails_closed(self):
        iid = self.new()
        tkn = self.t()
        self.kp.available = False
        with self.assertRaises(errors.OpError) as cm:
            self.svc.boot(tkn, iid)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_TRUST_UNAVAILABLE")
        self.assertEqual(self.prov.launches, 0)

    def test_replayed_token_refused(self):
        tkn = self.t()
        self.svc.create(tkn, req())
        with self.assertRaises(errors.OpError):
            self.svc.create(tkn, req())

    def test_quarantine(self):
        iid = self.new()
        self.svc.boot(self.t(), iid)
        self.svc.quarantine(self.t(), f"guest:{iid}", "suspected escape attempt")
        self.assertEqual(self.svc.guests[iid].state, "stopped")
        with self.assertRaises(errors.OpError) as cm:
            self.svc.boot(self.t(), iid)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_QUARANTINED")
        with self.assertRaises(errors.OpError):
            self.svc.quarantine(self.t(), "tier", "x")   # service token, no admin
        self.svc.quarantine(self.t(kind="human", ops=("admin",)), "tier", "incident SEV1")
        self.assertFalse(self.svc.health()["ready"])


class FaultInjectionTest(Base):
    def test_transient_provider_failure_retried(self):
        self.prov.faults = ["unavailable", "unavailable"]
        b = self.svc.boot(self.t(), self.new())
        self.assertEqual(b["state"], "running")
        self.assertEqual(self.svc.breaker.state, "closed")

    def test_breaker_opens_then_recovers(self):
        iid = self.new()
        for _ in range(self.svc.cfg["breaker_failure_threshold"]):
            self.prov.faults = ["fail"]
            with self.assertRaises(errors.OpError):
                self.svc.boot(self.t(), iid)
        with self.assertRaises(errors.OpError) as cm:
            self.svc.boot(self.t(), iid)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_CIRCUIT_OPEN")
        self.svc.breaker.reset_s = 0
        self.assertEqual(self.svc.boot(self.t(), iid)["state"], "running")

    def test_guest_os_start_failure_is_terminal(self):
        self.prov.faults = ["guest"]
        with self.assertRaises(errors.OpError) as cm:
            self.svc.boot(self.t(), self.new())
        self.assertFalse(cm.exception.retryable)

    def test_crash_restart_reconciles(self):
        a, b = self.new(), self.new(name="g2")
        self.svc.boot(self.t(), a)
        self.svc.destroy(self.t(), b)
        # process crash: new service on same state dir, provider handles gone
        svc2 = self.make(provider=FakeProvider())
        self.assertEqual(svc2.recovered["reconciled_to_stopped"], 1)
        self.assertEqual(svc2.guests[a].state, "stopped")
        self.assertNotIn(b, svc2.guests)
        self.assertEqual(svc2.boot(self.t(), a)["state"], "running")

    def test_telemetry_outage_is_degraded_not_fatal(self):
        def bad(_):
            raise OSError("collector down")
        svc = self.make(log_sink=bad)
        svc.boot(self.t(), svc.create(self.t(), req())["instance_id"])
        self.assertGreater(svc.health()["dependencies"]["telemetry_sink_failures"], 0)


class FencingServiceTest(Base):
    def test_split_brain_prevented(self):
        t = [0.0]
        lt = fencing.LeaseTable(ttl_s=5, clock=lambda: t[0])
        svc = self.make(leases=lt)
        e1 = lt.acquire("ctl-a")
        iid = svc.create(self.t(), req(), controller="ctl-a", epoch=e1)["instance_id"]
        t[0] = 6
        e2 = lt.acquire("ctl-b")
        with self.assertRaises(errors.OpError) as cm:
            svc.boot(self.t(), iid, controller="ctl-a", epoch=e1)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_STALE_OWNER")
        svc.boot(self.t(), iid, controller="ctl-b", epoch=e2)
        with self.assertRaises(errors.OpError):
            svc.boot(self.t(), iid)   # no token at all


class ConcurrencyTest(Base):
    def test_parallel_creates_respect_quota(self):
        svc = self.make(config={"tenant_guest_quota": 10})
        ok, fail = [], []

        def go(i):
            try:
                ok.append(svc.create(self.t(), req(name=f"g{i}")))
            except errors.OpError as e:
                fail.append(e.code)
        th = [threading.Thread(target=go, args=(i,)) for i in range(40)]
        [x.start() for x in th]
        [x.join() for x in th]
        self.assertEqual(len(ok), 10)
        self.assertEqual(set(fail), {"PK_FULL_VM_QUOTA_EXCEEDED"})

    def test_parallel_boots_one_winner_per_guest(self):
        iid = self.new()
        res = []

        def go():
            try:
                res.append(self.svc.boot(self.t(), iid)["state"])
            except errors.OpError as e:
                res.append(e.code)
        th = [threading.Thread(target=go) for _ in range(16)]
        [x.start() for x in th]
        [x.join() for x in th]
        self.assertEqual(res.count("running"), 1)
        self.assertEqual(len(self.prov.live), 1)


class ObservabilityTest(Base):
    def test_health_and_trace(self):
        tp = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        c = self.svc.create(self.t(), req(trace_parent=tp))
        self.assertEqual(c["trace_id"], "ab" * 16)
        h = self.svc.health()
        for k in ("version", "ready", "config", "capabilities", "dependencies", "audit_head", "primitive"):
            self.assertIn(k, h)
        logs = [json.loads(l) for l in self.svc.log.lines]
        self.assertTrue(all({"node", "component", "operation", "tenant"} <= set(l) for l in logs))
        self.assertTrue(any(l.get("trace_id") == "ab" * 16 for l in logs))


if __name__ == "__main__":
    unittest.main()
