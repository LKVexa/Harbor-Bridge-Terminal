"""Structured errors and outcome semantics (C014, C026, C027)."""
import json
import pathlib
import re
import unittest

from _util import m

errors = m("errors")
future = m("future")
wire = m("wire")


class TaxonomyTest(unittest.TestCase):
    def test_every_code_has_complete_spec(self):
        """REQ: C026 C014"""
        for code, s in errors.CODES.items():
            self.assertRegex(code, r"^[A-Z_]+$")
            self.assertIn(s.category, errors.OUTCOME_CATEGORIES)
            self.assertIn(s.severity, ("info", "warning", "error", "critical"))
            self.assertTrue(s.operator_action)
        required = ["FUTURE_ALREADY_RESOLVED", "FUTURE_ALREADY_TAKEN", "FUTURE_ABANDONED", "INVALID_ARGUMENT",
                    "UNAUTHENTICATED", "PERMISSION_DENIED", "INCOMPATIBLE_VERSION", "RESOURCE_EXHAUSTED",
                    "TIMEOUT", "DEPENDENCY_UNAVAILABLE", "INTERNAL_INVARIANT"]
        for r in required:
            self.assertIn(r, errors.CODES)

    def test_codes_are_stable(self):
        """REQ: C026 C016 — codes may be added, never removed or recategorised within a major"""
        snap = json.loads((pathlib.Path(errors.__file__).parent / "conformance/API_SNAPSHOT.json").read_text())
        for c in snap["error_codes"]:
            self.assertIn(c, errors.CODES)

    def test_roundtrip_serialization_and_schema(self):
        """REQ: C026 C022"""
        inner = errors.ErrorRecord("DEPENDENCY_UNAVAILABLE", "db down")
        rec = errors.ErrorRecord("TIMEOUT", "deadline", {"timeout_s": 1.5}, inner)
        d = rec.to_dict()
        self.assertEqual(wire.validate(d, "PK_FUTURE_ERROR/1"), [])
        back = errors.ErrorRecord.from_dict(json.loads(json.dumps(d)))
        self.assertEqual(back.code, "TIMEOUT")
        self.assertEqual(back.cause.code, "DEPENDENCY_UNAVAILABLE")
        self.assertTrue(back.retryable)

    def test_unknown_code_forward_compatible(self):
        """REQ: C026 C027 INV18-CMP-002"""
        d = {"schema": "PK_FUTURE_ERROR/1", "code": "QUANTUM_FLUX", "message": "new", "details": {}}
        r = errors.ErrorRecord.from_dict(d)
        self.assertEqual(r.code, "UNKNOWN")
        self.assertEqual(r.original_code, "QUANTUM_FLUX")
        self.assertFalse(r.retryable)
        self.assertEqual(r.to_dict()["original_code"], "QUANTUM_FLUX")

    def test_malformed_records_rejected(self):
        """REQ: C026 C085"""
        for bad in (None, [], {"schema": "X"}, {"schema": "PK_FUTURE_ERROR/1"},
                    {"schema": "PK_FUTURE_ERROR/1", "code": "TIMEOUT", "details": []}):
            with self.assertRaises(ValueError):
                errors.ErrorRecord.from_dict(bad)
        deep = {"schema": "PK_FUTURE_ERROR/1", "code": "TIMEOUT", "details": {}}
        cur = deep
        for _ in range(10):
            cur["cause"] = {"schema": "PK_FUTURE_ERROR/1", "code": "TIMEOUT", "details": {}}
            cur = cur["cause"]
        with self.assertRaises(ValueError):
            errors.ErrorRecord.from_dict(deep)

    def test_redaction(self):
        """REQ: C039 C075 INV18-SEC-004"""
        r = errors.ErrorRecord("INVALID_ARGUMENT", "token SENTINEL-SECRET-abc123 leaked",
                               {"password": "hunter2", "api_key": "x", "n": 3, "note": "sk-ABCDEFGHIJKL"})
        blob = json.dumps(r.to_dict())
        for s in ("SENTINEL-SECRET-abc123", "hunter2", "sk-ABCDEFGHIJKL"):
            self.assertNotIn(s, blob)
        self.assertIn("[REDACTED]", blob)
        big = errors.redact({f"k{i}": i for i in range(40)})
        self.assertTrue(big["_truncated"])

    def test_exception_mapping(self):
        """REQ: C026"""
        self.assertEqual(errors.from_exception(future.AlreadyTaken("x")).code, "FUTURE_ALREADY_TAKEN")
        self.assertEqual(errors.from_exception(TypeError("x")).code, "TYPE_MISMATCH")
        self.assertEqual(errors.from_exception(ValueError("x")).code, "INVALID_ARGUMENT")
        self.assertEqual(errors.from_exception(TimeoutError()).code, "TIMEOUT")
        self.assertEqual(errors.from_exception(KeyError("x")).code, "INTERNAL_INVARIANT")
        try:
            try:
                raise OSError("disk")
            except OSError as e:
                raise errors.Rejected("wrapped", code="DEPENDENCY_UNAVAILABLE") from e
        except errors.Rejected as e:
            rec = errors.from_exception(e)
        self.assertEqual(rec.cause.code, "INTERNAL_INVARIANT")

    def test_precedence_is_deterministic(self):
        """REQ: C014 C019 INV18-FR-009"""
        self.assertEqual(errors.precedence(["INVALID_ARGUMENT", "FUTURE_ALREADY_RESOLVED"]), "FUTURE_ALREADY_RESOLVED")
        self.assertEqual(errors.precedence(["RESOURCE_EXHAUSTED", "PERMISSION_DENIED"]), "PERMISSION_DENIED")
        self.assertEqual(errors.precedence(["UNAUTHENTICATED", "COMPONENT_DISABLED"]), "COMPONENT_DISABLED")
        self.assertEqual(errors.precedence(["INTERNAL_INVARIANT", "COMPONENT_DISABLED"]), "INTERNAL_INVARIANT")


class OutcomeMatrixTest(unittest.TestCase):
    """Exhaustive state x operation matrix (C014, C015)."""

    OPS = ("resolve", "resolve_error", "abandon", "cancel", "take")

    def _make(self, state, taken):
        f = future.Future(int)
        if state == "VALUE":
            f.resolve(1)
        elif state == "ERROR":
            f.resolve_error("e")
        elif state == "ABANDONED":
            f.abandon()
        elif state == "CANCELLED":
            f.cancel()
        if taken and state != "CANCELLED":
            try:
                f.take()
            except future.Abandoned:
                pass
        return f

    def _apply(self, f, op):
        try:
            if op == "resolve":
                f.resolve(2); return "ok"
            if op == "resolve_error":
                f.resolve_error("x"); return "ok"
            if op == "abandon":
                return "did" if f.abandon() else "noop"
            if op == "cancel":
                return "did" if f.cancel() else "noop"
            r = f.take()
            return "pending" if r is None else r[0]
        except errors.FutureError as exc:
            return exc.code

    EXPECT = {
        ("PENDING", False): {"resolve": "ok", "resolve_error": "ok", "abandon": "did", "cancel": "did", "take": "pending"},
        ("VALUE", False): {"resolve": "FUTURE_ALREADY_RESOLVED", "resolve_error": "FUTURE_ALREADY_RESOLVED", "abandon": "noop", "cancel": "noop", "take": "ok"},
        ("VALUE", True): {"resolve": "FUTURE_ALREADY_RESOLVED", "resolve_error": "FUTURE_ALREADY_RESOLVED", "abandon": "noop", "cancel": "noop", "take": "FUTURE_ALREADY_TAKEN"},
        ("ERROR", False): {"resolve": "FUTURE_ALREADY_RESOLVED", "resolve_error": "FUTURE_ALREADY_RESOLVED", "abandon": "noop", "cancel": "noop", "take": "error"},
        ("ERROR", True): {"resolve": "FUTURE_ALREADY_RESOLVED", "resolve_error": "FUTURE_ALREADY_RESOLVED", "abandon": "noop", "cancel": "noop", "take": "FUTURE_ALREADY_TAKEN"},
        ("ABANDONED", False): {"resolve": "FUTURE_ALREADY_RESOLVED", "resolve_error": "FUTURE_ALREADY_RESOLVED", "abandon": "noop", "cancel": "noop", "take": "FUTURE_ABANDONED"},
        ("ABANDONED", True): {"resolve": "FUTURE_ALREADY_RESOLVED", "resolve_error": "FUTURE_ALREADY_RESOLVED", "abandon": "noop", "cancel": "noop", "take": "FUTURE_ALREADY_TAKEN"},
        ("CANCELLED", False): {"resolve": "FUTURE_CANCELLED", "resolve_error": "FUTURE_CANCELLED", "abandon": "noop", "cancel": "noop", "take": "FUTURE_ALREADY_TAKEN"},
    }

    def test_every_state_operation_combination(self):
        """REQ: C014 C015 C081 INV18-FR-001 INV18-FR-002 INV18-FR-005 INV18-FR-006 INV18-FR-007 INV18-FR-008 INV18-FR-013"""
        for (state, taken), row in self.EXPECT.items():
            for op in self.OPS:
                with self.subTest(state=state, taken=taken, op=op):
                    f = self._make(state, taken)
                    self.assertEqual(self._apply(f, op), row[op])

    def test_every_outcome_maps_to_one_category(self):
        """REQ: C014"""
        for (state, taken), row in self.EXPECT.items():
            for v in row.values():
                if v in errors.CODES:
                    self.assertIn(errors.CODES[v].category, errors.OUTCOME_CATEGORIES)
        self.assertNotIn("PARTIAL_SUCCESS", errors.OUTCOME_CATEGORIES)

    def test_architecture_table_matches_codes(self):
        """REQ: C014 C013"""
        doc = (pathlib.Path(errors.__file__).parent / "docs/ARCHITECTURE.md").read_text()
        for cat in errors.OUTCOME_CATEGORIES:
            self.assertRegex(doc, rf"\| {cat} \|")
        retryable = {c for c, s in errors.CODES.items() if s.category == errors.RETRYABLE_FAILURE}
        self.assertEqual(retryable, {"RESOURCE_EXHAUSTED", "DEPENDENCY_UNAVAILABLE", "TIMEOUT"})
        consumes = {c for c, s in errors.CODES.items() if s.consumes_receiver}
        self.assertEqual(consumes, {"FUTURE_ABANDONED", "FUTURE_CANCELLED"})


if __name__ == "__main__":
    unittest.main()
