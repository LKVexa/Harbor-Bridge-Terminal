"""MC-15 security, MC-17 redaction/keys, MC-18 audit, MC-22 observability."""
import json
import os
import tempfile
import unittest

from _helpers import pipe_nb

from inv19_os_asynchronous_analogues.hostio import audit as auditmod
from inv19_os_asynchronous_analogues.hostio import observability as obs
from inv19_os_asynchronous_analogues.hostio import security as sec
from inv19_os_asynchronous_analogues.hostio.driver import AsyncHost


class CapabilityTest(unittest.TestCase):
    def setUp(self):
        self.t = [0.0]
        self.keys = sec.KeyProvider(clock=lambda: self.t[0])
        self.keys.create("k1")
        self.auth = sec.Authority(self.keys, clock=lambda: self.t[0])

    def test_forged_expired_revoked_scope(self):
        c = self.auth.mint("t1", "w1", ["submit"], "fd:5", ttl=10)
        self.auth.check(c, "submit", fd=5)
        forged = sec.Capability(**{**c.__dict__, "tenant": "t2"})
        for cap, action, kw, reason in [
            (forged, "submit", {"fd": 5}, "FORGED_CAPABILITY"),
            (c, "cancel", {}, "ACTION_NOT_GRANTED:cancel"),
            (c, "submit", {"fd": 6}, "RESOURCE_OUT_OF_SCOPE"),
            (c, "submit", {"owner": ("t2", "w1")}, "CROSS_TENANT"),
            (c, "submit", {"owner": ("t1", "w9")}, "CROSS_WORKLOAD"),
            ("t1", "submit", {}, "NO_CAPABILITY"),
        ]:
            with self.assertRaises(sec.Unauthorized) as cm:
                self.auth.check(cap, action, **kw)
            self.assertEqual(cm.exception.reason, reason)
        self.t[0] = 11
        with self.assertRaises(sec.Unauthorized) as cm:
            self.auth.check(c, "submit", fd=5)
        self.assertEqual(cm.exception.reason, "EXPIRED")
        c2 = self.auth.mint("t1", "w1", ["submit"])
        self.auth.revoke(c2)
        with self.assertRaises(sec.Unauthorized) as cm:
            self.auth.check(c2, "submit")
        self.assertEqual(cm.exception.reason, "REVOKED")

    def test_key_rotation_revocation_outage(self):
        c1 = self.auth.mint("t", "w", ["submit"])
        self.keys.rotate("k2")
        c2 = self.auth.mint("t", "w", ["submit"])
        self.auth.check(c1, "submit")  # old key verifies after rotation
        self.keys.revoke("k1")
        with self.assertRaises(sec.Unauthorized):
            self.auth.check(c1, "submit")
        self.auth.check(c2, "submit")
        self.keys.available = False  # key service outage -> fail closed
        with self.assertRaises(sec.Unauthorized) as cm:
            self.auth.check(c2, "submit")
        self.assertTrue(cm.exception.reason.startswith("KEY_UNAVAILABLE"))
        self.keys.available = True
        k = sec.KeyProvider(clock=lambda: self.t[0]); k.create("e", ttl=1)
        self.t[0] += 2
        with self.assertRaises(sec.KeyUnavailable):
            k.key("e")

    def test_identity_spoof_rejected_at_mint(self):
        for bad in ("", "a" * 65, "t1\nadmin", "t1|w"):
            with self.assertRaises(ValueError):
                self.auth.mint(bad, "w", ["submit"])
        with self.assertRaises(ValueError):
            self.auth.mint("t", "w", ["root"])

    def test_repr_never_leaks_key(self):
        self.assertNotIn(self.keys._keys["k1"].hex(), repr(self.keys))


class CrossTenantDriverTest(unittest.TestCase):
    def test_denial_before_allocation_and_audited(self):
        h = AsyncHost(override="portable")
        a = h.mint("tA", "wA")
        b = h.mint("tB", "wB")
        r, w = pipe_nb()
        f = h.read(a, r, 4)
        used = h.accountant.used("inflight_ops")
        with self.assertRaises(sec.Unauthorized):
            h.cancel(b, f)                         # cross-tenant cancel
        with self.assertRaises(sec.Unauthorized):
            h.read("forged", r, 4)                 # no capability
        narrow = h.mint("tB", "wB", ["submit"], resource="fd:999")
        with self.assertRaises(sec.Unauthorized):
            h.read(narrow, w, 4)                   # out of scope
        self.assertEqual(h.accountant.used("inflight_ops"), used)  # nothing allocated
        denials = [x for x in h.audit.records if x.get("outcome") == "denied"]
        self.assertGreaterEqual(len(denials), 3)
        self.assertTrue(h.cancel(a, f))
        h.shutdown(); os.close(r); os.close(w)

    def test_audit_outage_fails_closed(self):
        h = AsyncHost(override="portable")
        h.audit.max_buffer = 0
        c = h.mint("t", "w")
        r, w = pipe_nb()
        with self.assertRaises(auditmod.AuditUnavailable):
            h.read(c, r, 4)
        self.assertEqual(h.accountant.used("inflight_ops"), 0)
        self.assertGreaterEqual(h.audit.lost, 1)
        h.shutdown(); os.close(r); os.close(w)


class RedactionTest(unittest.TestCase):
    def test_nested_and_value_patterns(self):
        doc = {"a": {"api_token": "abc", "list": [{"password": "p"}, "Bearer eyJhbGciOi.xyz"]},
               "key": b"raw", "ok": "fine", "hexsecret": "a" * 64, "buf": bytearray(b"x")}
        out = json.dumps(sec.redact(doc))
        for leak in ("abc", '"p"', "eyJhbGciOi", "a" * 64, "raw"):
            self.assertNotIn(leak, out)
        self.assertIn("fine", out)

    def test_log_injection_and_bounds(self):
        s = sec.redact("line1\nFAKE event=admin\x1b[31m" + "x" * 1000)
        self.assertNotIn("\n", s)
        self.assertNotIn("\x1b", s)
        self.assertLessEqual(len(s), 260)
        deep = {}
        cur = deep
        for _ in range(50):
            cur["n"] = {}
            cur = cur["n"]
        self.assertIn("[DEPTH]", json.dumps(sec.redact(deep)))

    def test_exceptions_are_traceback_free(self):
        try:
            raise ValueError("token=Bearer abc.def")
        except ValueError as e:
            d = sec.safe_exception(e)
        self.assertNotIn("Traceback", json.dumps(d))
        self.assertNotIn("abc.def", json.dumps(d))

    def test_snapshot_has_no_secrets(self):
        h = AsyncHost(override="portable")
        snap = json.dumps(h.snapshot())
        self.assertNotIn(h.keys._keys[h.keys.active].hex(), snap)
        h.shutdown()

    def test_outage_policy_covers_every_dependency(self):
        self.assertEqual(set(sec.OUTAGE_POLICY), {"identity_service", "key_service", "time_service",
                                                  "audit_sink", "telemetry_sink"})
        for v in sec.OUTAGE_POLICY.values():
            self.assertRegex(v, r"^fail-(open|closed)")


class AuditTest(unittest.TestCase):
    def _log(self, path=None, n=10):
        a = auditmod.AuditLog(path=path, checkpoint_every=4)
        for i in range(n):
            a.emit("submit", "allowed", actor="x", tenant="ps_t", workload="ps_w", resource=f"fd:{i}")
        return a

    def test_chain_and_signed_checkpoints_verify(self):
        a = self._log()
        ok, msg = auditmod.verify_records(a.records, a.head)
        self.assertTrue(ok, msg)
        self.assertTrue(any("checkpoint" in r for r in a.records))

    def test_modification_deletion_reordering_truncation_detected(self):
        a = self._log()
        recs = [r for r in a.records]
        mod = json.loads(json.dumps(recs)); mod[1]["outcome"] = "denied"
        dele = recs[:2] + recs[3:]
        reo = [recs[1], recs[0]] + recs[2:]
        trunc = recs[:-2]
        for bad in (mod, dele, reo):
            self.assertFalse(auditmod.verify_records(bad)[0])
        self.assertFalse(auditmod.verify_records(trunc, a.head)[0])

    def test_forged_checkpoint_signature_detected(self):
        a = self._log()
        recs = json.loads(json.dumps(a.records))
        cp = next(r for r in recs if "checkpoint" in r)
        cp["sig"] = "00" * 64
        self.assertFalse(auditmod.verify_records(recs)[0])

    def test_offline_file_verifier(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "audit.jsonl")
            a = self._log(p, 9)
            self.assertTrue(auditmod.verify_file(p, a.head)[0])
            with open(p) as fh:
                lines = fh.read().splitlines()
            lines[2] = lines[2].replace("fd:2", "fd:7")
            with open(p, "w") as fh:
                fh.write("\n".join(lines) + "\n")
            self.assertFalse(auditmod.verify_file(p)[0])

    def test_sink_outage_buffers_then_refuses(self):
        a = auditmod.AuditLog(max_buffer=3)
        a.sink_up = False
        for _ in range(3):
            a.emit("x", "ok", actor="a", tenant="t", workload="w")
        with self.assertRaises(auditmod.AuditUnavailable):
            a.emit("x", "ok", actor="a", tenant="t", workload="w")
        self.assertEqual((a.lost, a.buffered), (1, 3))
        self.assertGreaterEqual(a.export_failures, 3)
        a.sink_up = True
        a.flush()
        self.assertTrue(auditmod.verify_records(a.records, a.head)[0])


class ObservabilityTest(unittest.TestCase):
    def test_label_safety(self):
        m = obs.Metrics()
        with self.assertRaises(obs.CardinalityError):
            m.inc("inv19_submit_total", backend="epoll", op="read", fd="3")
        with self.assertRaises(obs.CardinalityError):
            m.inc("inv19_errors_total", backend="epoll", code="bad value!")
        with self.assertRaises(KeyError):
            m.inc("made_up_metric")
        for i in range(obs.MAX_SERIES_PER_METRIC):
            m.inc("inv19_retry_total", code=f"C{i}")
        with self.assertRaises(obs.CardinalityError):
            m.inc("inv19_retry_total", code="overflow")

    def test_exposition_and_histogram(self):
        m = obs.Metrics()
        m.observe("inv19_reap_latency_seconds", 0.0002, backend="epoll")
        txt = m.exposition()
        self.assertIn('inv19_reap_latency_seconds_bucket{backend="epoll",le="0.0005"} 1', txt)
        self.assertIn("# TYPE inv19_submit_total counter", txt)

    def test_trace_context(self):
        c = obs.TraceContext.new()
        self.assertEqual(obs.TraceContext.parse(c.header()).trace_id, c.trace_id)
        for bad in ("", "00-" + "0" * 32 + "-" + "1" * 16 + "-01", "zz"):
            self.assertIsNone(obs.TraceContext.parse(bad))
        self.assertEqual(c.child().trace_id, c.trace_id)

    def test_driver_explains_selection_and_propagates_trace(self):
        h = AsyncHost()
        self.assertIn("backend-selection", h.decisions.explain())
        cap = h.mint("t", "w")
        r, w = pipe_nb()
        ctx = obs.TraceContext.new()
        f = h.write(cap, w, b"x", traceparent=ctx.header())
        h.run_until(f)
        self.assertEqual(f.corr["trace_id"], ctx.trace_id)
        self.assertTrue(any(s["name"] == "inv19.resolve" and s["trace_id"] == ctx.trace_id for s in h.tracer.spans))
        exp = h.metrics.exposition()
        self.assertIn(f'inv19_backend_selected{{backend="{h.name}"', exp)
        self.assertNotIn('fd="', exp)
        logs = h.logger.dumps()
        self.assertIn("backend_selected", logs)
        h.shutdown(); os.close(r); os.close(w)

    def test_alert_rules_cover_required_signals(self):
        names = {a["alert"] for a in obs.ALERT_RULES}
        for need in ("INV19UnknownHostErrors", "INV19PersistentFallback", "INV19QueueSaturation",
                     "INV19ReapP99", "INV19BackendUnhealthy", "INV19AuditExportFailure"):
            self.assertIn(need, names)


if __name__ == "__main__":
    unittest.main()
