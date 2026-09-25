"""C030 / C083 / C060 / C089 / C077 / C078 end-to-end tests through Sandbox.handle.

Adjacent layers are exercised at their real seams: the caller (INV-69 role) via
signed tokens and PK_FASTBOX_RUN/1+2, host capabilities via the process pipe, the
observability consumer (GAP-09 role) via metrics exposition/logs/audit, and the
control plane via config activation.  Faults are injected at each seam.
"""
import importlib
import io
import os
import time
import unittest

import _path
svc = importlib.import_module(_path.PKG + ".service")
sec = importlib.import_module(_path.PKG + ".security")
res = importlib.import_module(_path.PKG + ".resilience")

K = b"c" * 32
ADD = [("push", 2), ("push", 3), ("add",), ("halt",)]


def boom(_):
    raise RuntimeError("password=hunter2")


class Base(unittest.TestCase):
    env = "prod"

    @classmethod
    def setUpClass(cls):
        cls.ts = sec.TrustStore()
        cls.ts.add("c1", K, "caller")
        cls.audit_sink = io.StringIO()
        cls.sb = svc.Sandbox(environment=cls.env, trust=cls.ts, audit_key=b"a" * 32, audit_sink=cls.audit_sink)
        cls.sb.register_capability("double", lambda x: 2 * x)
        cls.sb.register_capability("slow", lambda x: time.sleep(3))
        cls.sb.register_capability("boom", boom)

    @classmethod
    def tearDownClass(cls):
        cls.sb.close()

    def tok(self, caps=("double", "slow", "boom"), tenant="t1"):
        return sec.issue_token(self.ts, "c1", subject="caller", tenant=tenant, capabilities=caps, audience="inv70",
                               ttl_s=60, now=time.time(), token_id=os.urandom(8).hex())

    def run_(self, program=ADD, v=2, **kw):
        req = {"token": kw.pop("token", None) or self.tok(), "versions": [v], "program": program}
        req.update(kw)
        return self.sb.handle(req)


class ProdPath(Base):
    def test_ok_v2_and_v1(self):
        r = self.run_()
        self.assertEqual((r["status"], r["value"], r["reason_code"], r["state"]), ("ok", 5, "FB-OK", "succeeded"))
        self.assertEqual(self.run_(v=1), {"ok": 5, "fuel": 4})

    def test_capability_requires_token_grant(self):
        prog = [("push", 3), ("call", "double"), ("halt",)]
        self.assertEqual(self.run_(prog, caps=["double"])["value"], 6)
        r = self.run_(prog, caps=["double"], token=self.tok(caps=()))
        self.assertEqual((r["reason_code"], r["state"]), ("FB-S001", "trapped"))
        self.assertIn("security precedence", self.sb.explain(r["run_id"]))

    def test_guest_traps_map_to_stable_codes(self):
        self.assertEqual(self.run_([("jmp", 0)])["reason_code"], "FB-R001")
        self.assertEqual(self.run_([("add",), ("halt",)])["reason_code"], "FB-R004")
        self.assertEqual(self.run_([("bogus",)])["reason_code"], "FB-R010")

    def test_unauthenticated_rejected_before_execution(self):
        r = self.run_(token="x.y")
        self.assertEqual((r["reason_code"], r["state"], r["fuel"]), ("FB-S010", "rejected", 0))

    def test_unsupported_version(self):
        self.assertEqual(self.run_(v=9)["reason_code"], "FB-V001")

    def test_caller_may_only_tighten_fuel(self):
        loop = [("jmp", 0)]
        self.assertEqual(self.run_(loop, fuel=10)["fuel"], 10)
        self.assertEqual(self.run_(loop, fuel=10**9)["fuel"], 1000)

    def test_idempotency(self):
        key = os.urandom(6).hex()
        a = self.run_(idempotency_key=key)
        b = self.run_(idempotency_key=key)
        self.assertTrue(b.get("replayed"))
        self.assertEqual(a["run_id"], b["run_id"])
        c = self.run_([("push", 1), ("halt",)], idempotency_key=key)
        self.assertEqual(c["reason_code"], "FB-D001")


class Faults(Base):
    """C060 / C089 fault injection with recovery assertions."""

    def test_host_timeout_and_error_redaction(self):
        r = self.run_([("push", 1), ("call", "slow"), ("halt",)], caps=["slow"])
        self.assertEqual(r["reason_code"], "FB-H003")
        r = self.run_([("push", 1), ("call", "boom"), ("halt",)], caps=["boom"])
        self.assertEqual(r["reason_code"], "FB-H001")
        self.assertNotIn("hunter2", str(r) + self.sb.explain(r["run_id"]) + str(list(self.sb.log.records)))
        self.assertEqual(self.run_()["status"], "ok")   # recovered

    def test_wall_clock_preemption(self):
        self.sb.config.activate({"_site": "t", "fuel": 10_000_000, "wall_clock_ms": 300,
                                 "host_call_timeout_ms": 100}, actor="test", reason="preempt")
        try:
            t = time.monotonic()
            r = self.run_([("jmp", 0)])
            self.assertEqual((r["reason_code"], r["state"]), ("FB-T001", "timed_out"))
            self.assertLess(time.monotonic() - t, 2.0)
        finally:
            self.sb.config.rollback(actor="test", reason="restore")
        self.assertEqual(self.run_()["status"], "ok")

    def test_trust_time_audit_outage_halts_then_recovers(self):
        for attr, obj in (("available", self.ts), ("healthy", self.sb.clock)):
            setattr(obj, attr, False)
            try:
                r = self.run_(token="x.y")
                self.assertEqual(r["reason_code"], "FB-C003")
                self.assertEqual(self.sb.health()["mode"], "halt")
            finally:
                setattr(obj, attr, True)
            self.assertEqual(self.run_()["status"], "ok")

    def test_control_plane_partition_freezes_config_but_serves(self):
        self.sb.control_plane_ok = False
        try:
            self.sb.config.frozen = self.sb.mode() == res.Mode.READ_ONLY_CONTROL
            self.assertEqual(self.run_()["status"], "ok")
            with self.assertRaises(Exception):
                self.sb.config.activate({"fuel": 5}, actor="x", reason="y")
        finally:
            self.sb.control_plane_ok = True
            self.sb.config.frozen = False

    def test_drain(self):
        self.sb.draining = True
        try:
            self.assertEqual(self.run_()["reason_code"], "FB-C004")
        finally:
            self.sb.draining = False

    def test_worker_crash_opens_breaker_then_recovers(self):
        ex = self.sb._executors["process"]
        real = ex.execute
        ex.execute = lambda *a, **k: {"trap": "worker crashed", "fuel": -1}
        try:
            codes = [self.run_()["reason_code"] for _ in range(6)]
            self.assertEqual(codes[:5], ["FB-I001"] * 5)
            self.assertEqual(codes[5], "FB-C002")
        finally:
            ex.execute = real
        self.sb.breaker.opened_at -= 100
        self.assertEqual(self.run_()["status"], "ok")
        self.assertEqual(self.sb.breaker.state, "closed")

    def test_overload_sheds_with_backpressure(self):
        adm = self.sb.admission
        old = adm.per_tenant
        adm.per_tenant = 0
        try:
            self.assertEqual(self.run_()["reason_code"], "FB-C001")
        finally:
            adm.per_tenant = old

    def test_audit_sink_failure_is_fail_closed(self):
        class Bad(io.StringIO):
            def write(self, s):
                raise OSError("disk")
        good = self.sb.audit.sink
        self.sb.audit.sink = Bad()
        try:
            r = self.run_()
            self.assertEqual(r["reason_code"], "FB-S022")
            self.assertEqual(self.run_()["reason_code"], "FB-C003")  # HALT until repaired
        finally:
            self.sb.audit.sink = good
            self.sb.audit.write_failures = 0


class Observability(Base):
    def test_metrics_logs_audit_explain_lineage(self):
        r = self.run_()
        self.assertIn("inv70_runs_total", self.sb.metrics.exposition())
        rec = [x for x in self.sb.log.records if x["run_id"] == r["run_id"]][0]
        self.assertEqual(rec["event"], "run.finished")
        ok, why = sec.AuditLog.verify(self.sb.audit.entries, b"a" * 32, self.sb.audit.sealed_head())
        self.assertTrue(ok, why)
        text = self.sb.explain(r["run_id"])
        for needle in ("path:", "received -> authenticated -> admitted -> validated -> running -> succeeded",
                       "config:  sha256:", "release: INV-70 4.3.0"):
            self.assertIn(needle, text)
        self.assertIn("no record", self.sb.explain("missing"))
        h = self.sb.health()
        self.assertEqual((h["mode"], h["lineage"]["version"]), ("normal", "4.3.0"))

    def test_trace_propagates(self):
        tp = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"
        r = self.sb.handle({"token": self.tok(), "versions": [2], "program": ADD}, traceparent=tp)
        self.assertIn("1" * 32, self.sb.explain(r["run_id"]))


class DevAndEdgeTiers(Base):
    """C083 tier coverage: dev (inline) and edge profiles resolve and execute."""
    env = "edge"

    def test_edge(self):
        self.assertEqual(self.run_()["value"], 5)
        self.assertEqual(self.sb.config.active["max_concurrent"], 8)


class DevTier(Base):
    env = "dev"

    def test_dev_inline(self):
        self.assertEqual(self.run_()["value"], 5)
        self.assertEqual(self.sb.config.active["isolation"], "inline-dev")


class WasmProfile(Base):
    """C031: selecting the wasm backend without the pinned engine fails closed."""

    def test_fail_closed(self):
        if self.sb.wasm.available:
            self.skipTest("engine present - covered by tests/wasm")
        self.sb.config.activate({"_site": "w", "backend": "wasm"}, actor="t", reason="wasm")
        try:
            blob = b"\0asm\1\0\0\0"
            r = self.sb.handle({"token": self.tok(), "versions": [2], "module": blob})
            self.assertEqual((r["reason_code"], r["state"]), ("FB-S030", "rejected"))   # C045 unsigned
            self.ts.add("art", b"r" * 32, "artifact")
            self.sb.artifact_policy.approved_versions["guest"] = {"1.0"}
            man = sec.make_manifest(self.ts, "art", name="guest", version="1.0", content=blob, builder="inv70-ci",
                                    source_revision="deadbeef", sbom=[{"name": "guest", "version": "1.0"}],
                                    now=time.time())
            r = self.sb.handle({"token": self.tok(), "versions": [2], "module": blob + b"x", "manifest": man})
            self.assertEqual(r["reason_code"], "FB-S032")                                # tampered module
            r = self.sb.handle({"token": self.tok(), "versions": [2], "module": blob, "manifest": man})
            self.assertEqual((r["reason_code"], r["state"]), ("FB-I002", "failed"))     # C031 fail closed
            self.assertIn("guest@1.0 sha256:", self.sb.explain(r["run_id"]))
        finally:
            self.sb.config.rollback(actor="t", reason="restore")


if __name__ == "__main__":
    unittest.main()
