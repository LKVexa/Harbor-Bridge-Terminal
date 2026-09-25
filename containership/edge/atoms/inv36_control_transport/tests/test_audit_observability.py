"""Tamper-evident audit log and observability."""
from __future__ import annotations

import io
import json
import pathlib
import tempfile
import unittest

import _util  # noqa: F401

from inv36_control_transport import audit_log as A
from inv36_control_transport import observability as O
from inv36_control_transport import schema_check
from inv36_control_transport.testing import World


class AuditLogTest(unittest.TestCase):
    """REQ: INV36-REQ-029 | KIND: security"""

    def setUp(self):
        self.w = World()
        self.path = pathlib.Path(tempfile.mkdtemp()) / "audit.jsonl"
        self.log = A.AuditLog.open(self.path, signer=self.w.audit_key, signer_key_id="audit#1", checkpoint_every=5,
                                   node="n1", component_version="5.1.0")
        for i in range(12):
            self.log.emit("authz.decision", {"i": i, "plaintext": "SECRET", "note": "line\nbreak"}, actor="a")
        self.keys = {"audit#1": self.w.audit_key.public_bytes()}

    def lines(self):
        return self.path.read_bytes().splitlines()

    def write(self, lines):
        self.path.write_bytes(b"\n".join(lines) + b"\n")

    def test_valid_chain_with_checkpoints_and_schema(self):
        r = A.verify_log(self.path, self.keys, require_checkpoint=True, expected_head=self.log.head)
        self.assertTrue(r.ok, r.to_dict())
        self.assertEqual(r.checkpoints, 2)
        schema = schema_check.load("audit-event.schema.json")
        first = json.loads(self.lines()[0])
        schema_check.validate(first, schema)
        self.assertEqual(first["data"]["plaintext"], "<redacted>")
        self.assertEqual(len(self.lines()), 14)

    def _expect(self, lines, error):
        self.write(lines)
        r = A.verify_log(self.path, self.keys, expected_head=self.log.head)
        self.assertFalse(r.ok)
        self.assertEqual(r.error, error, r.to_dict())
        return r

    def test_deletion(self):
        ls = self.lines()
        r = self._expect(ls[:3] + ls[4:], "chain_break")
        self.assertEqual(r.first_error_line, 4)

    def test_tail_truncation_detected_with_external_head(self):
        self._expect(self.lines()[:-2], "head_mismatch_truncation")

    def test_insertion_reorder_bitflip_duplicate(self):
        ls = self.lines()
        self._expect(ls[:2] + [ls[1]] + ls[2:], "chain_break")
        self._expect([ls[1], ls[0]] + ls[2:], "chain_break")
        flipped = bytearray(ls[2])
        flipped[40] ^= 1
        self._expect(ls[:2] + [bytes(flipped)] + ls[3:], "hash_mismatch")

    def test_forged_checkpoint_and_wrong_key(self):
        ls = self.lines()
        cp_idx = next(i for i, line in enumerate(ls) if b'"checkpoint"' in line)
        rec = json.loads(ls[cp_idx])
        rec["sig"] = "00" * 64
        rec.pop("hash")
        import hashlib
        rec["hash"] = hashlib.sha256(A._canon(rec)).hexdigest()
        forged = A._canon(rec)
        self.write(ls[:cp_idx] + [forged])
        r = A.verify_log(self.path, self.keys)
        self.assertEqual(r.error, "bad_checkpoint_signature")
        self.write(ls)
        other = World()
        r = A.verify_log(self.path, {"audit#1": other.audit_key.public_bytes()})
        self.assertEqual(r.error, "bad_checkpoint_signature")
        r = A.verify_log(self.path, {"other": other.audit_key.public_bytes()})
        self.assertEqual(r.error, "untrusted_checkpoint_key")

    def test_crash_torn_tail_recovery(self):
        with open(self.path, "ab") as fh:
            fh.write(b'{"kind":"event","event":"torn')
        self.assertEqual(A.verify_log(self.path, self.keys).error, "torn_tail")
        reopened = A.AuditLog.open(self.path, signer=self.w.audit_key, signer_key_id="audit#1")
        reopened.emit("config.activate", {"v": 2})
        self.assertTrue(A.verify_log(self.path, self.keys).ok)

    def test_sink_unavailable_buffers_or_fails_closed(self):
        self.log.sink_available = False
        self.log.emit("authz.decision", {"x": 1})  # buffered
        with self.assertRaises(A.AuditUnavailable):
            self.log.emit("key.revoke", {"epoch": 3})
        self.log.sink_available = True
        self.log.emit("authz.decision", {"x": 2})  # flushes buffer first
        self.assertTrue(A.verify_log(self.path, self.keys).ok)

    def test_bounded_buffer_and_oversized_fields(self):
        self.log.sink_available = False
        self.log.max_buffer = 5
        for i in range(20):
            self.log.emit("authz.decision", {"x": "y" * 10_000})
        self.assertEqual(len(self.log._buffer), 5)
        self.assertEqual(self.log.dropped, 15)
        rec = self.log._buffer[-1]
        self.assertLessEqual(len(rec["data"]["x"]), 256)

    def test_mandatory_events_cover_checklist(self):
        for e in ("handshake.failure", "key.rotate", "config.rollback", "quarantine.activate", "release.sign",
                  "integrity.failure", "replay.threshold", "admin.break_glass"):
            self.assertIn(e, A.MANDATORY_EVENTS)


class ObservabilityTest(unittest.TestCase):
    """REQ: INV36-REQ-030, INV36-REQ-031, INV36-REQ-032 | KIND: unit"""

    def test_metrics_catalog_cardinality_and_exposition(self):
        m = O.MetricsRegistry()
        with self.assertRaises(KeyError):
            m.inc("not_in_catalog")
        with self.assertRaises(KeyError):
            m.inc("inv36_frames_total", tenant="t1")  # raw tenant labels forbidden
        for i in range(500):
            m.inc("inv36_integrity_failures_total", reason=f"r{i}")
        text = m.exposition()
        self.assertIn('reason="other"', text)
        self.assertLessEqual(text.count("inv36_integrity_failures_total{"), O.MAX_LABEL_VALUES + 1)
        m.observe("inv36_latency_seconds", 0.0002, stage="seal")
        self.assertIn('inv36_latency_seconds_bucket{stage="seal",le="0.0005"} 1', m.exposition())
        m.sample_process()
        self.assertGreater(m.value("inv36_process_threads"), 0)

    def test_logger_schema_redaction_ratelimit_and_security_visibility(self):
        buf = io.StringIO()
        lg = O.StructuredLogger(stream=buf, level="error", rate_max=3, version="5.1.0", node="n1", build_digest="abc")
        lg.log("info", "noise")
        self.assertEqual(buf.getvalue(), "")
        lg.log("info", "auth_failure", reason="bad_tag", tenant="acme", shared_secret=b"k" * 32,
               payload="REVOKE lease", nested={"private_key": "x"})
        rec = json.loads(buf.getvalue().splitlines()[0])
        self.assertEqual(rec["fields"]["shared_secret"], "<redacted>")
        self.assertEqual(rec["fields"]["payload"], "<redacted>")
        self.assertEqual(rec["fields"]["nested"]["private_key"], "<redacted>")
        self.assertTrue(rec["tenant"].startswith("p_"))
        self.assertNotIn("acme", buf.getvalue())
        for k in ("ts", "mono", "severity", "component", "version", "node", "build", "event", "reason"):
            self.assertIn(k, rec)
        for _ in range(10):
            lg.log("error", "same", reason="x")
        self.assertEqual(lg.suppressed["error|same|x"], 7)

    def test_trace_context_sanitization(self):
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        self.assertEqual(O.accept_trace(tp, trusted_peer=True).trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertNotEqual(O.accept_trace(tp, trusted_peer=False).trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertIsNone(O.TraceContext.parse("00-" + "0" * 32 + "-" + "1" * 16 + "-01"))
        self.assertIsNone(O.TraceContext.parse("garbage"))
        tr = O.Tracer()
        with tr.span("seal", O.TraceContext.new(), payload=b"secret"):
            pass
        self.assertEqual(tr.spans[0]["attrs"]["payload"], "<redacted>")

    def test_exporter_never_blocks_and_bounds_memory(self):
        m = O.MetricsRegistry()

        def down(batch):
            raise ConnectionError("backend down")

        ex = O.BoundedExporter(capacity=100, send=down, metrics=m)
        for i in range(1000):
            ex.offer({"i": i})
        self.assertEqual(len(ex.queue), 100)
        self.assertEqual(ex.flush(), 0)
        self.assertEqual(len(ex.queue), 100)
        self.assertGreaterEqual(m.value("inv36_telemetry_dropped_total"), 900)
        sent = []
        ex.send = sent.extend
        self.assertEqual(ex.flush(), 100)

    def test_dashboards_and_alerts_reference_catalog_and_runbooks(self):
        pkg = pathlib.Path(__file__).resolve().parents[1]
        alerts = json.loads((pkg / "docs" / "observability" / "alerts.json").read_text())
        dash = json.loads((pkg / "docs" / "observability" / "dashboard.json").read_text())
        runbooks = (pkg / "docs" / "RUNBOOKS.md").read_text()
        classes = set()
        for a in alerts["alerts"]:
            self.assertTrue(any(metric in a["expr"] for metric in O.METRICS_CATALOG), a["name"])
            anchor = a["runbook"].split("#")[1]
            self.assertIn(f'<a id="{anchor}"></a>', runbooks, a["name"])
            self.assertIn(a["severity"], ("SEV1", "SEV2", "SEV3", "SEV4"))
            classes.add(a["class"])
        self.assertEqual(classes, {"load", "overload", "dependency_failure", "policy_rejection", "attack",
                                   "software_defect", "degradation"})
        for panel in dash["panels"]:
            self.assertTrue(any(metric in panel["expr"] for metric in O.METRICS_CATALOG), panel["title"])
        # synthetic alert test: evaluate simple threshold rules against a registry
        m = O.MetricsRegistry()
        m.inc("inv36_auth_failures_total", 50)
        fired = [a["name"] for a in alerts["alerts"] if a.get("synthetic_metric") == "inv36_auth_failures_total"
                 and m.value("inv36_auth_failures_total") > a["synthetic_threshold"]]
        self.assertIn("INV36AuthFailureSpike", fired)


if __name__ == "__main__":
    unittest.main()
