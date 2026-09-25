"""MC31 / MC41-MC48 / MC54 — audit ledger, resilience, deadlines, observability, config."""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from inv02_container_substrate import observability as ob
from inv02_container_substrate.audit import AuditLedger, AuditTampered, verify_ledger
from inv02_container_substrate.config import load_config
from inv02_container_substrate.registry import ValidationError
from inv02_container_substrate.resilience import (AdmissionController, CircuitBreaker, CircuitOpen, Overloaded,
                                                  QuotaManager, RateLimited, RetryPolicy, TokenBucket, retry)
from inv02_container_substrate.timeutil import Deadline, DeadlineExceeded, FakeClock

KEY = b"k" * 32


class AuditTests(unittest.TestCase):
    def test_chain_verifies_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.jsonl"
            led = AuditLedger(p, KEY, clock=FakeClock())
            for i in range(5):
                led.append("tag.set", {"i": i, "token": "Bearer abc.def"})
            head = led.head
            self.assertEqual(verify_ledger(p, KEY, expected_head=head), 5)
            self.assertNotIn("abc.def", p.read_text())
            led2 = AuditLedger(p, KEY)  # reopen continues the chain
            led2.append("x", {})
            self.assertEqual(verify_ledger(p, KEY), 6)
            lines = p.read_text().splitlines()
            mutations = {
                "edit": lines[:2] + [lines[2].replace('"i":2', '"i":9')] + lines[3:],
                "delete": lines[:2] + lines[3:],
                "reorder": [lines[1], lines[0]] + lines[2:],
            }
            for name, ls in mutations.items():
                with self.subTest(name):
                    p.write_text("\n".join(ls) + "\n")
                    with self.assertRaises(AuditTampered):
                        verify_ledger(p, KEY)
            p.write_text("\n".join(lines[:3]) + "\n")  # truncation
            with self.assertRaises(AuditTampered):
                verify_ledger(p, KEY, expected_head=head)
            p.write_text("\n".join(lines) + "\n")
            with self.assertRaises(AuditTampered):
                verify_ledger(p, b"x" * 32)


class ResilienceTests(unittest.TestCase):
    def test_token_bucket_and_quota(self):
        c = FakeClock()
        b = TokenBucket(2, 2, c)
        self.assertEqual(b.try_take(), 0)
        self.assertEqual(b.try_take(), 0)
        self.assertAlmostEqual(b.try_take(), 0.5)
        c.advance(0.5)
        self.assertEqual(b.try_take(), 0)
        q = QuotaManager(100, 100, 1000, c)
        q.admit("a", 600)
        with self.assertRaises(RateLimited):
            q.admit("a", 600)
        q.admit("b", 600)  # tenants isolated
        q.release_bytes("a", 600)
        q.admit("a", 600)

    def test_admission_sheds_load(self):
        ac = AdmissionController(1, 1)
        started, release = threading.Event(), threading.Event()

        def hold():
            with ac.slot():
                started.set()
                release.wait(5)

        t1 = threading.Thread(target=hold)
        t1.start()
        started.wait(5)
        t2 = threading.Thread(target=lambda: ac.slot().__enter__())
        t2.start()
        for _ in range(100):
            if ac.waiting == 1:
                break
            threading.Event().wait(0.01)
        with self.assertRaises(Overloaded):
            with ac.slot():
                pass
        self.assertEqual(ac.shed, 1)
        release.set()
        t1.join()
        t2.join(5)

    def test_retry_backoff_deadline_and_breaker(self):
        c = FakeClock()
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ConnectionError("x")
            return "ok"

        self.assertEqual(retry(flaky, RetryPolicy(base_delay_s=0.1), clock=c), "ok")
        with self.assertRaises(ValueError):
            retry(lambda: (_ for _ in ()).throw(ValueError()), RetryPolicy(), clock=c)
        with self.assertRaises(DeadlineExceeded):
            retry(lambda: (_ for _ in ()).throw(ConnectionError()), RetryPolicy(base_delay_s=100, max_delay_s=100,
                  max_attempts=10), clock=c, deadline=Deadline.after(0.001, c))
        br = CircuitBreaker(2, 10, c)
        for _ in range(2):
            with self.assertRaises(ConnectionError):
                br.call(lambda: (_ for _ in ()).throw(ConnectionError()))
        with self.assertRaises(CircuitOpen):
            br.call(lambda: "x")
        c.advance(11)
        self.assertEqual(br.call(lambda: "probe"), "probe")
        self.assertEqual(br.state, "closed")

    def test_deadline_children(self):
        c = FakeClock()
        d = Deadline.after(10, c)
        self.assertEqual(d.child(100).remaining(), 10)
        c.advance(11)
        with self.assertRaises(DeadlineExceeded):
            d.check()


class ObservabilityTests(unittest.TestCase):
    def test_metrics_render_and_cardinality(self):
        m = ob.Metrics(max_series_per_metric=2)
        inc = m.counter("inv02_pulls_total", "pulls", ["result"])
        h = m.histogram("inv02_pull_seconds", "latency", [], buckets=(0.1, 1))
        inc(result="ok")
        inc(result="ok")
        inc(result="err")
        h(0.05)
        text = m.render()
        self.assertIn('inv02_pulls_total{result="ok"} 2.0', text)
        self.assertIn('inv02_pull_seconds_bucket{le="+Inf"} 1', text)
        with self.assertRaises(ob.CardinalityExceeded):
            inc(result="third")
        with self.assertRaises(ValueError):
            inc(-1, result="ok")

    def test_redaction_logging_tracing(self):
        self.assertEqual(ob.redact({"password": "x", "n": {"api_key": 1}, "h": "Bearer abc"}),
                         {"password": "[REDACTED]", "n": {"api_key": "[REDACTED]"}, "h": "[REDACTED]"})
        tr = ob.Tracer()
        with tr.span("pull", traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01") as outer:
            with tr.span("blob", token="t") as inner:
                pass
        self.assertEqual(inner.trace_id, "a" * 32)
        self.assertEqual(inner.parent_id, outer.span_id)
        self.assertEqual(inner.attrs["token"], "[REDACTED]")
        import io, logging
        buf = io.StringIO()
        log = logging.getLogger("t-json")
        hdl = logging.StreamHandler(buf)
        hdl.setFormatter(ob.JsonFormatter())
        log.addHandler(hdl)
        log.warning("auth Bearer xyz", extra={"fields": {"secret": "s"}})
        rec = json.loads(buf.getvalue())
        self.assertNotIn("xyz", buf.getvalue())
        self.assertEqual(rec["fields"]["secret"], "[REDACTED]")

    def test_health_http(self):
        h, m = ob.Health(), ob.Metrics()
        state = {"ok": True}
        h.add("store", lambda: state["ok"])
        h.add("proc", lambda: True, readiness=False)
        srv = ob.serve_http(h, m)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            self.assertEqual(urllib.request.urlopen(base + "/readyz").status, 200)
            state["ok"] = False
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(base + "/readyz")
            self.assertEqual(cm.exception.code, 503)
            self.assertEqual(urllib.request.urlopen(base + "/healthz").status, 200)
            self.assertIn(b"text/plain", urllib.request.urlopen(base + "/metrics").headers["Content-Type"].encode())
        finally:
            srv.shutdown()
            srv.server_close()


class ConfigTests(unittest.TestCase):
    def test_precedence_validation_digest(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"offline": True, "max_inflight_pulls": 4}, fh)
        try:
            c = load_config(fh.name, env={"INV02_MAX_INFLIGHT_PULLS": "9", "INV02_PROTECTED_ENVIRONMENTS": "prod,live"})
            self.assertTrue(c.offline)
            self.assertEqual(c.max_inflight_pulls, 9)
            self.assertEqual(c.protected_environments, ("prod", "live"))
            self.assertEqual(c.digest(), load_config(fh.name, env={"INV02_MAX_INFLIGHT_PULLS": "9",
                                                                   "INV02_PROTECTED_ENVIRONMENTS": "prod,live"}).digest())
            for env in ({"INV02_TYPO": "1"}, {"INV02_OFFLINE": "maybe"}, {"INV02_MAX_BLOB_BYTES": "-1"},
                        {"INV02_STORE_ROOT": "relative"}, {"INV02_METRICS_LISTEN": "nope"}):
                with self.subTest(env), self.assertRaises(ValidationError):
                    load_config(fh.name, env=env)
            Path(fh.name).write_text(json.dumps({"unknwn": 1}))
            with self.assertRaises(ValidationError):
                load_config(fh.name, env={})
        finally:
            os.unlink(fh.name)


if __name__ == "__main__":
    unittest.main()
