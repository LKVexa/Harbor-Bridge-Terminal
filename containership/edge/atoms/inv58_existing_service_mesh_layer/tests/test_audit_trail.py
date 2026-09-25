"""MC-015: tamper-evident, bounded, sealed audit trail."""
from __future__ import annotations

import os
import tempfile
import unittest

from _support import Clock, audit


def _log(n=5, **kw):
    lg = audit.AuditLog(b"K" * 32, clock=Clock(), **kw)
    for i in range(n):
        lg.emit("authz.decision", actor=f"a{i}", tenant="alpha", target="route", decision="ALLOW", reason="r")
    return lg


class AuditTrailTest(unittest.TestCase):
    def test_chain_verifies(self):
        self.assertEqual(_log().verify(), (True, "ok"))

    def test_edit_delete_insert_reorder_are_detected(self):
        recs = list(_log().records())
        edited = [dict(r) for r in recs]
        edited[2]["decision"] = "DENY"
        self.assertFalse(audit.verify_chain(edited, b"K" * 32)[0])
        self.assertFalse(audit.verify_chain(recs[:2] + recs[3:], b"K" * 32)[0])
        self.assertFalse(audit.verify_chain([recs[1], recs[0]] + recs[2:], b"K" * 32)[0])
        self.assertFalse(audit.verify_chain(recs[:2] + [recs[2]] + recs[2:], b"K" * 32)[0])

    def test_recomputed_hash_without_key_is_detected(self):
        import hashlib
        recs = [dict(r) for r in _log().records()]
        last = recs[-1]
        body = {k: v for k, v in last.items() if k not in ("hash", "mac")}
        body["decision"] = "DENY"
        last.update(body, hash=hashlib.sha256(audit._canon(body)).hexdigest())
        ok, why = audit.verify_chain(recs, b"K" * 32)
        self.assertFalse(ok)
        self.assertIn("seal", why)

    def test_wrong_key(self):
        self.assertFalse(audit.verify_chain(_log().records(), b"Z" * 32)[0])

    def test_retention_bound_keeps_verifiable_anchor(self):
        lg = _log(50, max_records=10)
        self.assertEqual(len(lg.records()), 10)
        self.assertEqual(lg.verify(), (True, "ok"))
        self.assertNotEqual(lg.anchor(), audit.GENESIS)

    def test_truncated_tail_is_caught_by_external_head(self):
        lg = _log(5)
        head = lg.head
        recs = lg.records()[:-1]
        self.assertTrue(audit.verify_chain(recs, b"K" * 32)[0])  # chain alone cannot see tail truncation
        self.assertNotEqual(recs[-1]["hash"], head)                # the externally recorded head does

    def test_unknown_event_type_and_short_key(self):
        with self.assertRaises(ValueError):
            _log(0).emit("made.up", actor=None, tenant=None, target=None, decision="x", reason="y")
        with self.assertRaises(ValueError):
            audit.AuditLog(b"short")

    def test_fields_are_bounded(self):
        lg = _log(0)
        r = lg.emit("authz.decision", actor="a" * 10_000, tenant=None, target=None, decision="d", reason="r",
                    attrs={f"k{i}": i for i in range(100)})
        self.assertLessEqual(len(r["actor"]), 512)
        self.assertLessEqual(len(r["attrs"]), 32)

    def test_durable_jsonl_sink_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "audit.jsonl")
            lg = _log(7, sink_path=path)
            self.assertEqual(audit.verify_chain(audit.load_jsonl(path), b"K" * 32), (True, "ok"))
            self.assertEqual(oct(os.stat(path).st_mode & 0o777), oct(0o600))
            self.assertEqual(audit.load_jsonl(path)[-1]["hash"], lg.head)


if __name__ == "__main__":
    unittest.main()
