"""Standalone protocol tests for INV-61; intentionally independent of pk_core."""
import math
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR))

from rpc import Endpoint, MAX_ARGS, fingerprint, make_frame, validate_frame  # noqa: E402


class RpcProtocolTest(unittest.TestCase):
    def setUp(self):
        self.ep = Endpoint("kv", "2.0.0")
        self.ep.export("get", ["string"], ["u64"], lambda key: len(key))

    def test_happy_path_and_counters(self):
        result = self.ep.handle(make_frame("kv", "2.0.0", "get", ["string"], ["u64"], ["abc"], 10), 1)
        self.assertEqual(result, {"ok": 3})
        self.assertEqual(self.ep.stats.calls, 1)
        self.assertEqual(self.ep.stats.succeeded, 1)

    def test_version_mismatch_is_rejected_before_dispatch(self):
        called = []
        ep = Endpoint("kv", "2")
        ep.export("x", [], [], lambda: called.append(True))
        result = ep.handle(make_frame("kv", "1", "x", [], [], [], 10), 1)
        self.assertEqual(result["error"], "version-mismatch")
        self.assertEqual(called, [])

    def test_signature_mismatch_is_rejected_before_dispatch(self):
        frame = make_frame("kv", "2.0.0", "get", ["string"], ["string"], ["abc"], 10)
        self.assertEqual(self.ep.handle(frame, 1), {"error": "signature-mismatch"})
        self.assertEqual(self.ep.mismatches, 1)

    def test_deadline_is_exclusive(self):
        frame = make_frame("kv", "2.0.0", "get", ["string"], ["u64"], ["x"], 5)
        self.assertEqual(self.ep.handle(frame, 5), {"error": "deadline-exceeded"})

    def test_malformed_inputs_fail_closed(self):
        valid = make_frame("kv", "2.0.0", "get", ["string"], ["u64"], ["x"], 10)
        cases = [
            None,
            {},
            {**valid, "extra": 1},
            {**valid, "deadline": True},
            {**valid, "deadline": math.inf},
            {**valid, "fp": "xyz"},
            {**valid, "args": "x"},
            {**valid, "args": [None] * (MAX_ARGS + 1)},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(self.ep.handle(case, 0)["error"], "malformed-frame")

    def test_nonfinite_or_boolean_clock_fails_closed(self):
        valid = make_frame("kv", "2.0.0", "get", ["string"], ["u64"], ["x"], 10)
        for now in (True, math.nan, math.inf):
            with self.subTest(now=now):
                self.assertEqual(self.ep.handle(valid, now)["error"], "malformed-frame")

    def test_trap_is_typed_without_exception_detail_leak(self):
        ep = Endpoint("kv", "1")
        ep.export("boom", [], [], lambda: 1 / 0)
        self.assertEqual(ep.handle(make_frame("kv", "1", "boom", [], [], [], 10), 0), {"error": "callee-trap"})

    def test_export_validation(self):
        with self.assertRaises(ValueError):
            self.ep.export("", [], [], lambda: None)
        with self.assertRaises(TypeError):
            self.ep.export("bad", [], [], object())
        with self.assertRaises(ValueError):
            self.ep.export("get", [], [], lambda: None)

    def test_fingerprint_is_stable(self):
        self.assertEqual(fingerprint(["string"], ["u64"]), fingerprint(("string",), ("u64",)))
        self.assertRegex(fingerprint([], []), r"^[0-9a-f]{16}$")

    def test_frame_constructor_rejects_invalid_deadline(self):
        for deadline in (True, math.nan, math.inf):
            with self.subTest(deadline=deadline), self.assertRaises(ValueError):
                make_frame("kv", "2.0.0", "get", ["string"], ["u64"], [], deadline)

    def test_validate_frame_is_nonthrowing_for_hostile_types(self):
        for value in (object(), 1, [], "frame"):
            self.assertIsInstance(validate_frame(value), str)


if __name__ == "__main__":
    unittest.main()
