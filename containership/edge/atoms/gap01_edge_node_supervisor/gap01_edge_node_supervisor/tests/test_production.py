"""Unit tests for the v5.0.0 production components (no network, no pk_core)."""
import errno
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from helpers import KEYS, Harness  # noqa: F401  (sets sys.path)

from gap01_edge_node_supervisor.config import (SecretBoundary, SupervisorConfig, load_config,
                                               sign)
from gap01_edge_node_supervisor.errors import ERROR_CATALOG, SupervisorError, wrap
from gap01_edge_node_supervisor.health import HealthRegistry, SignalSpec
from gap01_edge_node_supervisor.observability import Metrics, Tracer, redact
from gap01_edge_node_supervisor.schemas import validate
from gap01_edge_node_supervisor.security import (AuthorizationPolicy, NodeIdentity, RateLimiter,
                                                 verify_artifacts)
from gap01_edge_node_supervisor.store import AuditLog, StateStore, migrate
from gap01_edge_node_supervisor.supervisor import IllegalTransition


class ErrorModelTest(unittest.TestCase):
    def test_catalog_codes_are_structured(self):
        for code in ERROR_CATALOG:
            d = SupervisorError(code, "x").to_dict()
            self.assertEqual(validate("error", d), [])
            self.assertNotIn("detail", d)

    def test_unknown_code_becomes_internal(self):
        self.assertEqual(SupervisorError("E_NOPE").code, "E_INTERNAL")

    def test_wrap_core_errors(self):
        self.assertEqual(wrap(IllegalTransition("a -> b is not a legal transition")).code,
                         "E_ILLEGAL_TRANSITION")
        self.assertEqual(wrap(KeyError("x")).code, "E_INTERNAL")


class ConfigTest(unittest.TestCase):
    def test_ranges_enforced(self):
        with self.assertRaises(SupervisorError):
            SupervisorConfig(max_workloads=0)
        with self.assertRaises(SupervisorError):
            SupervisorConfig(max_workloads=True)

    def test_hot_reload_rules(self):
        c = SupervisorConfig()
        self.assertEqual(c.hot_reload({"rate_burst": 5}).rate_burst, 5)
        with self.assertRaises(SupervisorError):
            c.hot_reload({"max_workloads": 5})  # cold knob
        with self.assertRaises(SupervisorError):
            c.hot_reload({"nope": 1})

    def test_signed_config(self):
        d = pathlib.Path(tempfile.mkdtemp())
        key = b"k" * 32
        body = {"max_workloads": 10}
        (d / "c.json").write_text(json.dumps({"config": body, "signature": sign(body, key)}))
        cfg = load_config(d / "c.json", key=key)
        self.assertEqual(cfg.max_workloads, 10)
        self.assertTrue(cfg.provenance["signed"])
        with self.assertRaises(SupervisorError) as cm:
            load_config(d / "c.json", key=b"x" * 32)
        self.assertEqual(cm.exception.code, "E_SIGNATURE")

    def test_secret_boundary(self):
        d = pathlib.Path(tempfile.mkdtemp())
        p = d / "s"
        p.write_bytes(b"s" * 32)
        os.chmod(p, 0o644)
        with self.assertRaises(SupervisorError):
            SecretBoundary.from_file(p)
        os.chmod(p, 0o600)
        s = SecretBoundary.from_file(p)
        self.assertNotIn("sss", repr(s))
        self.assertEqual(s.reveal(), b"s" * 32)
        s.close()
        with self.assertRaises(SupervisorError):
            s.reveal()


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())

    def test_checkpoint_roundtrip_and_generation(self):
        s = StateStore(self.d, fsync=False)
        s.checkpoint({"a": 1})
        g = s.checkpoint({"a": 2})
        s2 = StateStore(self.d, fsync=False)
        body, j = s2.load()
        self.assertEqual((body, j, s2.generation), ({"a": 2}, [], g))

    def test_corrupt_checkpoint_falls_back_to_prev(self):
        s = StateStore(self.d, fsync=False)
        s.checkpoint({"a": 1})
        s.checkpoint({"a": 2})
        (self.d / "state.json").write_text("{garbage")
        s2 = StateStore(self.d, fsync=False)
        body, _ = s2.load()
        self.assertEqual(body, {"a": 1})
        self.assertIn("fell back to previous checkpoint", s2.recovery_notes)

    def test_both_checkpoints_corrupt_fails_closed(self):
        s = StateStore(self.d, fsync=False)
        s.checkpoint({"a": 1})
        s.checkpoint({"a": 2})
        (self.d / "state.json").write_text("{}")
        (self.d / "state.json.prev").write_text("{}")
        with self.assertRaises(SupervisorError) as cm:
            StateStore(self.d, fsync=False).load()
        self.assertEqual(cm.exception.code, "E_STATE_CORRUPT")

    def test_torn_journal_tail_discarded_mid_corruption_fails(self):
        s = StateStore(self.d, fsync=False)
        s.append_journal({"op": "a"})
        s.append_journal({"op": "b"})
        with open(self.d / "journal.jsonl", "ab") as fh:
            fh.write(b'{"e":{"op":"c"},"sha')  # power loss mid-append
        _, j = StateStore(self.d, fsync=False).load()
        self.assertEqual([e["op"] for e in j], ["a", "b"])
        lines = (self.d / "journal.jsonl").read_bytes().split(b"\n")
        lines[0] = lines[0].replace(b'"a"', b'"z"')
        (self.d / "journal.jsonl").write_bytes(b"\n".join(lines))
        with self.assertRaises(SupervisorError):
            StateStore(self.d, fsync=False).load()

    def test_migration(self):
        self.assertIn("drain_intent", migrate({"state": "ready"}, 1))
        with self.assertRaises(SupervisorError):
            migrate({}, 99)

    def test_idempotency_window_bounded(self):
        s = StateStore(self.d, replay_window=16, fsync=False)
        for i in range(40):
            s.record_completion(f"k{i}", {"i": i})
        self.assertIsNone(s.completed("k0"))
        s2 = StateStore(self.d, replay_window=16, fsync=False)
        self.assertEqual(s2.completed("k39"), {"i": 39})
        self.assertIsNone(s2.completed("k1"))

    def test_backup_restore(self):
        s = StateStore(self.d, fsync=False)
        s.checkpoint({"a": 1})
        arc = s.backup(self.d.parent / f"{self.d.name}.tgz")
        tgt = pathlib.Path(tempfile.mkdtemp())
        StateStore.restore(arc, tgt)
        body, _ = StateStore(tgt, fsync=False).load()
        self.assertEqual(body, {"a": 1})

    def test_disk_full_is_structured(self):
        s = StateStore(self.d, fsync=False)
        with mock.patch("os.write", side_effect=OSError(errno.ENOSPC, "No space left on device")):
            with self.assertRaises(SupervisorError) as cm:
                s.checkpoint({"a": 1})
        self.assertEqual(cm.exception.code, "E_PERSISTENCE")
        self.assertEqual(s.generation, 0)

    def test_audit_chain_detects_tamper(self):
        a = AuditLog(self.d / "audit.jsonl", fsync=False)
        for i in range(5):
            a.append({"i": i})
        self.assertTrue(AuditLog.verify(self.d / "audit.jsonl")[0])
        lines = (self.d / "audit.jsonl").read_bytes().split(b"\n")
        lines[2] = lines[2].replace(b'"i":2', b'"i":9')
        (self.d / "audit.jsonl").write_bytes(b"\n".join(lines))
        self.assertFalse(AuditLog.verify(self.d / "audit.jsonl")[0])
        with self.assertRaises(SupervisorError):
            AuditLog(self.d / "audit.jsonl")


class SecurityTest(unittest.TestCase):
    def test_policy_deny_default_and_override_expiry(self):
        p = AuthorizationPolicy()
        with self.assertRaises(SupervisorError):
            p.check("nobody", "status")
        p.grant_override("nobody", "state.read", ttl_s=10, reason="incident 7", now=100)
        self.assertEqual(p.check("nobody", "status", now=105), "state.read")
        with self.assertRaises(SupervisorError):
            p.check("nobody", "status", now=111)
        with self.assertRaises(SupervisorError):
            p.grant_override("x", "state.read", ttl_s=10, reason=" ")

    def test_rate_limiter(self):
        rl = RateLimiter(rate=1, burst=2, max_in_flight=100)
        rl.acquire("a", 0); rl.release()
        rl.acquire("a", 0); rl.release()
        with self.assertRaises(SupervisorError):
            rl.acquire("a", 0)
        rl.acquire("a", 1.5); rl.release()
        rl.acquire("b", 0)  # per-caller isolation

    def test_attestation(self):
        ident = NodeIdentity("n1", b"k" * 32)
        att = ident.attest({"x": 1}, "nonce1")
        self.assertTrue(ident.verify(att))
        att["measurements"] = {"x": 2}
        self.assertFalse(ident.verify(att))
        self.assertFalse(NodeIdentity("n2", b"k" * 32).verify(ident.attest({}, "n")))

    def test_artifact_verification(self):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "a.py").write_text("x")
        import hashlib
        import hmac
        from gap01_edge_node_supervisor.config import canonical
        files = {"a.py": hashlib.sha256(b"x").hexdigest(), "../etc": "0" * 64}
        key = b"k" * 32
        (d / "m.json").write_text(json.dumps({"files": files, "signature":
                                  hmac.new(key, canonical(files), hashlib.sha256).hexdigest()}))
        probs = verify_artifacts(d, d / "m.json", key)
        self.assertEqual(probs, ["../etc: path escapes root"])
        (d / "a.py").write_text("y")
        self.assertIn("a.py: digest mismatch", verify_artifacts(d, d / "m.json", key))


class HealthTest(unittest.TestCase):
    def reg(self):
        r = HealthRegistry(max_signals=3)
        r.register(SignalSpec("runtime", True, 10, frozenset({"hr"})))
        r.register(SignalSpec("disk", False, 10))
        r.register(SignalSpec("net", False, 10))
        return r

    def test_required_optional_quorum(self):
        r = self.reg()
        self.assertFalse(r.evaluate(0)["healthy"])
        r.report("runtime", True, 0, "hr")
        self.assertFalse(r.evaluate(0)["healthy"])  # 0/2 optional < 50%
        r.report("disk", True, 0, "x")
        self.assertTrue(r.evaluate(5)["healthy"])
        self.assertFalse(r.evaluate(11)["healthy"])  # stale
        self.assertIn("stale:runtime", r.evaluate(11)["reasons"])

    def test_spoofing_and_limits(self):
        r = self.reg()
        with self.assertRaises(SupervisorError):
            r.report("runtime", True, 0, "intruder")
        with self.assertRaises(SupervisorError):
            r.report("unregistered", True, 0, "hr")
        with self.assertRaises(SupervisorError):
            r.register(SignalSpec("fourth"))
        r.report("runtime", True, 5, "hr")
        with self.assertRaises(SupervisorError):
            r.report("runtime", True, 4, "hr")

    def test_output_matches_schema(self):
        r = self.reg()
        r.report("runtime", False, 0, "hr")
        self.assertEqual(validate("health", r.evaluate(1)), [])


class ObservabilityTest(unittest.TestCase):
    def test_metrics_low_cardinality(self):
        m = Metrics()
        m.inc("requests", op="made-up-op", outcome="ok", code="none")
        self.assertIn('op="other"', m.render())
        m.observe("request_seconds", 0.003, op="status")
        self.assertIn("gap01_request_seconds_bucket", m.render())

    def test_redaction(self):
        r = redact({"sig": "abc", "args": {"api_key": "x", "n": 1}})
        self.assertEqual(r, {"sig": "<redacted>", "args": {"api_key": "<redacted>", "n": 1}})

    def test_trace_propagation(self):
        t = Tracer()
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        with t.span("outer", traceparent=tp) as o:
            with t.span("inner") as i:
                pass
        self.assertEqual(o["trace_id"], "a" * 32)
        self.assertEqual(i["parent_id"], o["span_id"])


if __name__ == "__main__":
    unittest.main()


class TelemetryContractTest(unittest.TestCase):
    """Telemetry names are part of the /1 contract (renames need a decision)."""
    REQUIRED = {"gap01_requests_total", "gap01_request_seconds_bucket", "gap01_state",
                "gap01_resident_workloads", "gap01_in_flight_requests", "gap01_build_info",
                "gap01_reconcile_orphans_terminated_total", "gap01_reconcile_lost_workloads_total",
                "gap01_under_pressure"}

    def test_metric_names_stable(self):
        h = Harness()
        h.make_ready()
        h.ctl.tick()
        names = {ln.split("{")[0].split(" ")[0] for ln in h.ctl.metrics.render().splitlines()}
        self.assertEqual(self.REQUIRED - names, set())

    def test_spans_nest_apply_and_persist(self):
        h = Harness()
        h.make_ready()
        names = [s["name"] for s in h.ctl.tracer.spans]
        self.assertIn("gap01.apply.transition", names)
        self.assertIn("gap01.persist.checkpoint", names)
        by_id = {s["span_id"]: s for s in h.ctl.tracer.spans}
        child = next(s for s in h.ctl.tracer.spans if s["name"] == "gap01.apply.transition")
        self.assertEqual(by_id[child["parent_id"]]["name"], "gap01.handle")

    def test_exporter_loss_does_not_affect_control(self):
        h = Harness()

        def broken(_span):
            raise ConnectionError("collector down")
        h.ctl.tracer.exporter = broken
        h.make_ready()
        self.assertEqual(h.ctl.sup.state, "ready")

    def test_inbound_traceparent_propagates(self):
        h = Harness()
        req = h.req("obs", "status")
        tp = "00-" + "c" * 32 + "-" + "d" * 16 + "-01"
        from gap01_edge_node_supervisor import make_request
        req = make_request("obs", KEYS["obs"], "status", ts=h.clock.wall())
        req["traceparent"] = tp  # not covered by signature by design (routing metadata)
        h.ctl.handle(req)
        self.assertEqual(h.ctl.tracer.spans[-1]["trace_id"], "c" * 32)

    def test_diagnostics_is_bounded_and_redacted(self):
        h = Harness()
        for i in range(50):
            h.call("hr", "report_health", {"signal": "runtime", "ok": True})
        d = h.call("obs", "status")
        self.assertTrue(d["ok"])
        diag = h.ctl.diagnostics()
        self.assertLessEqual(len(diag["recent_spans"]), 20)
        self.assertNotIn(KEYS["cp"].decode(), json.dumps(diag, default=str))
