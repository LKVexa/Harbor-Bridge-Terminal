"""Wire schemas, golden vectors, compatibility locks, error model, conformance (MC-012, MC-013, MC-027, MC-047)."""
from __future__ import annotations

import json
import os
import unittest

from _util import PKG_DIR
from inv05_current_control_state_system import errors
from inv05_current_control_state_system.conformance import runner
from inv05_current_control_state_system.errors import ERROR_CATALOG, IncompatibleVersion, InvalidArgument, to_wire
from inv05_current_control_state_system.schema import (
    CAPABILITIES, MESSAGES, check_message, loads, negotiate, parse_compare, parse_op, schema_lock,
)
from inv05_current_control_state_system.store import Event

CONF = os.path.join(PKG_DIR, "conformance")


def load(name):
    with open(os.path.join(CONF, name), encoding="utf-8") as fh:
        return json.load(fh)


class GoldenTest(unittest.TestCase):
    def test_every_message_type_has_a_golden_vector_that_parses(self):
        g = load("golden_messages_v1.json")
        self.assertEqual(set(g["messages"]), set(MESSAGES))
        for kind, msg in g["messages"].items():
            with self.subTest(kind):
                check_message(kind, msg)
        t = g["messages"]["txn"]
        [parse_compare(c) for c in t["compare"]]
        [parse_op(o) for o in t["success"] + t["failure"]]

    def test_event_roundtrip(self):
        ev = load("golden_messages_v1.json")["responses"]["event"]
        self.assertEqual(Event.from_dict(ev).to_dict(), ev)

    def test_error_vector_codes_exist(self):
        g = load("golden_messages_v1.json")["responses"]
        self.assertIn(g["error"]["error"]["code"], ERROR_CATALOG)


class CompatibilityLockTest(unittest.TestCase):
    def test_schema_has_no_breaking_change_against_lock(self):
        from inv05_current_control_state_system.tools_check import schema_breaking_changes
        self.assertEqual(schema_breaking_changes(load("schema_lock.json"), schema_lock()), [])

    def test_breaking_change_detector_detects(self):
        from inv05_current_control_state_system.tools_check import schema_breaking_changes
        lock = load("schema_lock.json")
        cur = schema_lock()
        del cur["messages"]["txn"]["request_id"]
        cur["messages"]["range"]["limit"] = ["str"]
        cur["ops"]["put"].remove("lease")
        self.assertEqual(len(schema_breaking_changes(lock, cur)), 3)

    def test_error_catalog_is_append_only(self):
        lock = load("error_catalog_lock.json")
        for code, spec in lock.items():
            self.assertIn(code, ERROR_CATALOG)
            cur = ERROR_CATALOG[code]
            self.assertEqual((cur.category, cur.retryable, cur.http_status),
                             (spec["category"], spec["retryable"], spec["http_status"]))


class ErrorModelTest(unittest.TestCase):
    def test_categories_cover_required_classes(self):
        cats = {s.category for s in ERROR_CATALOG.values()}
        for c in ("input", "conflict", "compaction", "unavailable", "timeout", "cancellation", "quota",
                  "overload", "authn", "authz", "internal"):
            self.assertIn(c, cats)

    def test_wire_form_is_safe(self):
        e = errors.InternalError("stack: /secret/path token=abc", secret="s", revision=3)
        w = e.to_wire()
        self.assertNotIn("secret", json.dumps(w))
        self.assertEqual(w["details"], {"revision": 3})
        self.assertEqual(to_wire(KeyError("x"))["code"], "CSTATE_INTERNAL")
        rt = errors.from_wire(errors.QuotaExceeded("q", retry_after_s=1.5).to_wire())
        self.assertIsInstance(rt, errors.QuotaExceeded)
        self.assertEqual(rt.details["retry_after_s"], 1.5)


class NegotiationTest(unittest.TestCase):
    def test_negotiation(self):
        r = negotiate({"schema": "cstate.hello/1.0", "protocol": "PK_CSTATE", "versions": ["1.0"],
                       "capabilities": ["watch.stream", "unknown.cap"]})
        self.assertEqual(r["version"], "1.0")
        self.assertEqual(r["capabilities"], ["watch.stream"])
        self.assertIn("lease.fencing", r["server_only_capabilities"])
        with self.assertRaises(IncompatibleVersion):
            negotiate({"schema": "cstate.hello/1.0", "protocol": "PK_CSTATE", "versions": ["0.9", "3.0"]})

    def test_strict_parsing(self):
        for bad in (b'{"a":1,"a":2}', b"NaN", b"[1,", b"\xff", b'{"x": Infinity}'):
            with self.assertRaises(InvalidArgument):
                loads(bad, 1000)
        for op in ({"put": {"key": "k"}}, {"put": {"key": "k", "value": 1}, "delete": {"key": "k"}},
                   {"frob": {"key": "k"}}, {"put": {"key": "k", "value": 1, "lease": "3"}},
                   {"delete": {"key": "k", "prefix": "yes"}}):
            with self.assertRaises(InvalidArgument):
                parse_op(op)
        with self.assertRaises(InvalidArgument):
            check_message("range", {"schema": "cstate.range/1.1", "key": "k", "limit": True})


class ConformanceRunnerTest(unittest.TestCase):
    def test_all_vectors_pass(self):
        for path in sorted(os.listdir(CONF)):
            if path.startswith("vectors_v"):
                rep = runner.run_file(os.path.join(CONF, path))
                self.assertEqual(rep["failed"], 0, [r for r in rep["results"] if not r["ok"]])

    def test_subset_matcher(self):
        self.assertEqual(runner.subset({"a": [1, {"b": 2}]}, {"a": [1, {"b": 2, "c": 3}], "z": 0}), [])
        self.assertTrue(runner.subset({"a": 1}, {"a": 2}))


if __name__ == "__main__":
    unittest.main()
