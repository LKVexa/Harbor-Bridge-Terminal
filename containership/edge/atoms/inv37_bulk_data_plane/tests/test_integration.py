"""End-to-end service integration across adjacent layers available in-repo:
config -> security -> admission -> lifecycle -> checkpoint/shm -> telemetry
(C014, C018, C025, C027, C030, C046, C052, C056-C059, C071-C077, C083, C089)."""
from __future__ import annotations

import io
import json
import os
import time
import unittest

from _support import ALL_DATA, Env, S, pkg


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.dp = self.env.plane(audit_path=str(self.env.dir / "audit.jsonl"))
        self.tok = self.env.token()
        self.data = os.urandom(3 * 4096 + 17)
        self.m = pkg.manifest(self.data, 4096)

    def tearDown(self):
        for t in list(self.dp.transfers.values()):
            if t.region:
                t.zc = None
                t.region.close()
        self.env.close()

    def send(self, tid, idxs=None, dp=None, tok=None):
        dp = dp or self.dp
        for i in (range(self.m["chunk_count"]) if idxs is None else idxs):
            dp.accept_chunk(tok or self.tok, tid, i, self.data[i * 4096:(i + 1) * 4096])

    def test_copy_durable_end_to_end(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="tx1", transport="copy")
        self.send("tx1")
        self.assertEqual(self.dp.finalize(self.tok, "tx1"), self.data)
        self.assertEqual(self.dp.finalize(self.tok, "tx1"), self.data)  # idempotent
        self.dp.close(self.tok, "tx1")
        self.assertEqual(self.dp.admission.metrics()["active"], 0)

    def test_shm_end_to_end_zero_copy(self):
        if not self.env.caps["shared_memory"]:
            self.skipTest("REQUIRED-CAPABILITY: shared memory")
        d = self.dp.create_transfer(self.tok, self.m, transfer_id="tx2", transport="shm")
        self.assertIn("descriptor", d)
        buf = self.dp.region_view(self.tok, "tx2")
        buf[: len(self.data)] = self.data
        del buf
        for i in range(self.m["chunk_count"]):
            self.dp.accept_chunk(self.tok, "tx2", i)
        v = self.dp.finalize(self.tok, "tx2")
        self.assertEqual(bytes(v), self.data)
        v.release()
        self.assertEqual(self.dp.diagnostics(self.tok, "tx2")["copies"]["data_plane_copies"], 0)

    def test_restart_resume_from_durable_checkpoint(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="tx3", transport="copy")
        self.send("tx3", [0, 2])
        rt = self.dp.resume_token(self.tok, "tx3")
        dp2 = self.env.plane()           # simulated process restart
        self.assertEqual(dp2.recover(), ["tx3"])
        self.assertEqual(dp2.transfers["tx3"].sm.state, pkg.Lifecycle.DISCONNECTED)
        with self.assertRaises(pkg.CodedError) as cm:   # old owner fenced
            self.send("tx3", [1])
        self.assertEqual(cm.exception.code, "stale_owner")
        r = dp2.reconcile(self.tok, "tx3", rt)
        self.assertEqual(r["missing"], [1, 3])
        self.send("tx3", [1, 3], dp=dp2)
        self.assertEqual(dp2.finalize(self.tok, "tx3"), self.data)

    def test_reconcile_rejects_forged_foreign_and_legacy_mismatch(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="tx4", transport="copy")
        rt = self.dp.resume_token(self.tok, "tx4")
        forged = dict(rt, verified=[0, 1, 2, 3])
        self.assertRaises(pkg.SecurityRejected, self.dp.reconcile, self.tok, "tx4", forged)
        legacy_other = {"schema": "PK_BULK_RESUME/1", "manifest_object": "0" * 64, "last_verified": -1, "verified": []}
        with self.assertRaises(pkg.CodedError) as cm:
            self.dp.reconcile(self.tok, "tx4", legacy_other)
        self.assertEqual(cm.exception.code, "resume_conflict")
        legacy_ok = {"schema": "PK_BULK_RESUME/1", "manifest_object": self.m["object"], "last_verified": 5, "verified": [0, 1, 2, 3]}
        r = self.dp.reconcile(self.tok, "tx4", legacy_ok)
        self.assertEqual(r["peer_overclaimed"], [0, 1, 2, 3])  # local verified progress wins

    def test_authorization_on_every_call(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="tx5", transport="copy")
        other = self.env.token(tenant="globex")
        for fn, args in ((self.dp.accept_chunk, ("tx5", 0, self.data[:4096])), (self.dp.finalize, ("tx5",)),
                         (self.dp.resume_token, ("tx5",)), (self.dp.cancel, ("tx5",))):
            with self.assertRaises(pkg.SecurityRejected):
                fn(other, *args)
        scoped = self.env.token(scope="tx-other")
        self.assertRaises(pkg.SecurityRejected, self.dp.accept_chunk, scoped, "tx5", 0, self.data[:4096])
        ro = self.env.token(actions=["read-progress"])
        self.assertRaises(pkg.SecurityRejected, self.dp.accept_chunk, ro, "tx5", 0, self.data[:4096])
        self.assertRaises(pkg.SecurityRejected, self.dp.create_transfer, "bogus", self.m, transfer_id="tx6")

    def test_idempotent_create_and_conflict(self):
        a = self.dp.create_transfer(self.tok, self.m, transfer_id="tx7", transport="copy")
        b = self.dp.create_transfer(self.tok, self.m, transfer_id="tx7", transport="copy")
        self.assertEqual(a["transfer_id"], b["transfer_id"])
        m2 = pkg.manifest(b"x" * 10, 4096)
        with self.assertRaises(pkg.CodedError) as cm:
            self.dp.create_transfer(self.tok, m2, transfer_id="tx7")
        self.assertEqual(cm.exception.code, "resume_conflict")

    def test_cancel_releases_everything(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="tx8", transport="copy")
        self.send("tx8", [0])
        self.dp.cancel(self.tok, "tx8")
        self.dp.cancel(self.tok, "tx8")  # idempotent
        self.assertEqual(self.dp.admission.metrics()["active"], 0)
        self.assertNotIn("tx8", self.dp.store.list())
        self.assertRaises(pkg.IllegalTransition, self.dp.accept_chunk, self.tok, "tx8", 1, self.data[4096:8192])

    def test_corrupt_chunk_then_resend(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="tx9", transport="copy")
        bad = bytearray(self.data[:4096]); bad[0] ^= 1
        self.assertRaises(pkg.DigestMismatch, self.dp.accept_chunk, self.tok, "tx9", 0, bytes(bad))
        self.send("tx9")
        self.assertEqual(self.dp.finalize(self.tok, "tx9"), self.data)
        self.assertGreaterEqual(self.dp.metrics.get("digest_failures_total", level="chunk"), 1)

    def test_final_verification_failure_quarantines(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="txq", transport="copy")
        self.send("txq")
        p = self.dp.store.data_path("txq")
        b = bytearray(p.read_bytes()); b[1] ^= 1; p.write_bytes(bytes(b))
        with self.assertRaises(pkg.CodedError) as cm:
            self.dp.finalize(self.tok, "txq")
        self.assertEqual(cm.exception.code, "object_digest_mismatch")
        self.assertEqual(self.dp.transfers["txq"].sm.state, pkg.Lifecycle.QUARANTINED)
        self.assertEqual(self.dp.admission.metrics()["active"], 0)

    def test_operator_controls(self):
        adm = self.env.admin()
        self.dp.create_transfer(self.tok, self.m, transfer_id="txa", transport="copy")
        self.dp.quarantine(adm, "txa", "suspicious")
        self.assertRaises(pkg.IllegalTransition, self.dp.accept_chunk, self.tok, "txa", 0, self.data[:4096])
        self.dp.freeze(adm, True)
        with self.assertRaises(pkg.CodedError) as cm:
            self.dp.create_transfer(self.tok, self.m, transfer_id="txb")
        self.assertEqual(cm.exception.code, "admission_frozen")
        self.assertEqual(self.dp.health()["status"], "frozen")
        self.dp.freeze(adm, False)
        self.dp.quarantine_tenant(adm, "acme")
        with self.assertRaises(pkg.CodedError) as cm:
            self.dp.create_transfer(self.tok, self.m, transfer_id="txc")
        self.assertEqual(cm.exception.code, "quarantined")
        self.assertRaises(pkg.SecurityRejected, self.dp.freeze, self.tok, True)  # data token can't administer

    def test_stall_detection_and_total_timeout(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="txs", transport="copy")
        self.send("txs", [0])
        r = self.dp.sweep(now=time.monotonic() + self.dp.e["timeouts.idle_chunk"] + 1)
        self.assertEqual(r["stalled"], ["txs"])
        self.send("txs", [1])  # reconnect by traffic
        self.assertEqual(self.dp.transfers["txs"].sm.state, pkg.Lifecycle.RECEIVING)
        r = self.dp.sweep(now=time.monotonic() + self.dp.e["timeouts.total_transfer"] + 1)
        self.assertIn("txs", r["expired"])
        self.assertEqual(self.dp.transfers["txs"].sm.state, pkg.Lifecycle.FAILED_TERMINAL)

    def test_quota_through_service(self):
        toks = []
        for i in range(2):
            self.dp.create_transfer(self.tok, self.m, transfer_id=f"q{i}", transport="copy")
        with self.assertRaises(pkg.CodedError) as cm:
            self.dp.create_transfer(self.tok, self.m, transfer_id="q2", transport="copy")
        self.assertEqual(cm.exception.code, "quota_exceeded")
        self.dp.create_transfer(self.env.token(tenant="globex"), self.m, transfer_id="g0", transport="copy")
        self.assertIn("quota_exceeded", self.dp.explain(self.env.admin()))

    def test_observability_surfaces(self):
        stream = io.StringIO()
        dp = self.env.plane(log_stream=stream)
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        d = dp.create_transfer(self.tok, self.m, transfer_id="to", traceparent=tp, transport="copy")
        self.assertTrue(d["traceparent"].startswith("00-" + "a" * 32))
        self.send("to", dp=dp)
        dp.finalize(self.tok, "to")
        lines = [json.loads(l) for l in stream.getvalue().splitlines()]
        self.assertTrue(all(l["trace_id"] == "a" * 32 for l in lines if l["transfer_id"] == "to"))
        self.assertTrue(all(l["tenant"] is None or l["tenant"].startswith("t_") for l in lines))  # pseudonymised
        self.assertNotIn("acme", stream.getvalue())
        h = dp.health()
        for k in ("status", "ready", "version", "config_digest", "artifact_digest", "dependencies", "capabilities", "limits", "utilization"):
            self.assertIn(k, h)
        snap = dp.metrics.snapshot()
        self.assertIn("chunks_verified_total", snap["counters"])
        self.assertIn("chunk_accept_seconds", snap["histograms"])
        ex = dp.explain(self.env.admin(), "to")
        self.assertIn("admission -> admit", ex)
        self.assertIn("transport_select", ex)
        self.assertIn("config=sha256:", ex)
        diag = dp.diagnostics(self.tok, "to")
        self.assertTrue(diag["tenant"].startswith("t_"))
        self.assertEqual(dp.diagnostics(self.env.admin(), "to")["tenant"], "acme")

    def test_audit_chain_covers_service(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="tz", transport="copy")
        self.assertRaises(pkg.SecurityRejected, self.dp.finalize, self.env.token(tenant="evil"), "tz")
        ok, _, n = S.verify_audit(self.env.dir / "audit.jsonl", self.env.ring.signing()[1])
        self.assertTrue(ok)
        events = [json.loads(l)["event"] for l in (self.env.dir / "audit.jsonl").read_text().splitlines()]
        self.assertIn("transfer.create", events)
        self.assertIn("authz.denied", events)

    def test_residency_precedence(self):
        env = Env({"security": {"allowed_regions": ["eu-1"]}})
        try:
            dp = env.plane(region="eu-1")
            with self.assertRaises(pkg.CodedError) as cm:
                dp.create_transfer(env.token(), self.m, transfer_id="r1", dest_region="us-1")
            self.assertEqual(cm.exception.code, "residency_violation")
        finally:
            env.close()

    def test_degraded_telemetry_does_not_block(self):
        class Broken(io.StringIO):
            def write(self, s):
                raise OSError("disk full")
        dp = self.env.plane(log_stream=Broken())
        dp.create_transfer(self.tok, self.m, transfer_id="td", transport="copy")
        self.send("td", dp=dp)
        self.assertEqual(dp.finalize(self.tok, "td"), self.data)
        self.assertEqual(dp.health()["status"], "degraded")

    def test_checkpoint_io_failure_is_retryable(self):
        self.dp.create_transfer(self.tok, self.m, transfer_id="tio", transport="copy")
        orig = self.dp.store.write_chunk
        self.dp.store.write_chunk = lambda *a, **k: (_ for _ in ()).throw(OSError("EIO"))
        with self.assertRaises(pkg.CodedError) as cm:
            self.dp.accept_chunk(self.tok, "tio", 0, self.data[:4096])
        self.assertEqual(cm.exception.code, "timeout")
        self.assertEqual(self.dp.transfers["tio"].sm.state, pkg.Lifecycle.FAILED_RETRYABLE)
        self.dp.store.write_chunk = orig
        self.send("tio")
        self.assertEqual(self.dp.finalize(self.tok, "tio"), self.data)

    def test_zero_length_object(self):
        m0 = pkg.manifest(b"", 4096)
        self.dp.create_transfer(self.tok, m0, transfer_id="t0", transport="copy")
        self.assertEqual(self.dp.finalize(self.tok, "t0"), b"")


class NegotiationTest(unittest.TestCase):
    FULL = {"manifest": ["PK_BULK_MANIFEST/1"], "chunk": ["PK_BULK_CHUNK/1"], "resume": ["PK_BULK_RESUME/1", "PK_BULK_RESUME/2"],
            "transport": ["INV37_SHM_DESCRIPTOR/1", "INV37_COPY/1"], "auth": ["v1"]}

    def test_highest_mutual(self):
        self.assertEqual(pkg.negotiate(self.FULL)["resume"], "PK_BULK_RESUME/2")
        old = dict(self.FULL, resume=["PK_BULK_RESUME/1"], transport=["INV37_COPY/1"])
        r = pkg.negotiate(old)
        self.assertEqual((r["resume"], r["transport"]), ("PK_BULK_RESUME/1", "INV37_COPY/1"))

    def test_refusals(self):
        cases = [dict(self.FULL, manifest=["PK_BULK_MANIFEST/2"]), {k: v for k, v in self.FULL.items() if k != "auth"},
                 dict(self.FULL, mandatory=["quantum"]), dict(self.FULL, mandatory=["encryption"]),
                 {k: v for k, v in self.FULL.items() if k != "chunk"}]
        for offer in cases:
            with self.assertRaises(pkg.CodedError):
                pkg.negotiate(offer)

    def test_unknown_optional_surface_ignored(self):
        self.assertIn("manifest", pkg.negotiate(dict(self.FULL, telemetry=["x/1"])))


if __name__ == "__main__":
    unittest.main()


class FlapTest(unittest.TestCase):
    """Repeated disconnect/reconnect flaps and long outages keep verified
    progress and never duplicate bytes (C018, C089)."""

    def test_repeated_flaps(self):
        env = Env()
        try:
            dp = env.plane()
            tok = env.token()
            data = os.urandom(20 * 4096)
            m = pkg.manifest(data, 4096)
            dp.create_transfer(tok, m, transfer_id="flap", transport="copy")
            idle = dp.e["timeouts.idle_chunk"]
            for i in range(20):
                dp.accept_chunk(tok, "flap", i, data[i * 4096:(i + 1) * 4096])
                if i % 3 == 0:
                    self.assertIn("flap", dp.sweep(now=time.monotonic() + idle + 1)["stalled"])
                    dp.accept_chunk(tok, "flap", i, data[i * 4096:(i + 1) * 4096])  # duplicate after reconnect
            self.assertEqual(dp.finalize(tok, "flap"), data)
            self.assertGreaterEqual(dp.metrics.get("duplicate_chunks_total"), 6)
        finally:
            env.close()

    def test_long_outage_restart_then_stale_token(self):
        env = Env()
        try:
            dp = env.plane()
            tok = env.token()
            data = os.urandom(4 * 4096)
            m = pkg.manifest(data, 4096)
            dp.create_transfer(tok, m, transfer_id="lo", transport="copy")
            dp.accept_chunk(tok, "lo", 0, data[:4096])
            rt = dp.resume_token(tok, "lo")
            dp2 = env.plane(); dp2.recover()
            dp3 = env.plane(); dp3.recover()          # second takeover: epoch +2
            with self.assertRaises(pkg.CodedError) as cm:
                dp3.reconcile(tok, "lo", rt)
            self.assertEqual(cm.exception.code, "stale_owner")
            fresh = dp3.resume_token(tok, "lo")
            self.assertEqual(dp3.reconcile(tok, "lo", fresh)["missing"], [1, 2, 3])
            with self.assertRaises(pkg.CodedError) as cm:
                dp3.reconcile(tok, "lo", dict(fresh, issued_at=0), max_age=10)
        finally:
            env.close()
