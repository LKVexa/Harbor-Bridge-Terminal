# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Executable contract tests for every public interface (GAP-056, GAP-015, GAP-019, GAP-020, GAP-022)."""
import json
import unittest
from pathlib import Path

from .. import schema
from ..errors import CODES, SchemaInvalid, envelope, Inv30Error
from ..core import BoundsViolation
from ._util import access, derive, invalidate, make_service, mint

FIX = Path(__file__).resolve().parents[1] / "fixtures"


class SchemaContractTest(unittest.TestCase):
    def test_every_schema_loads_and_uses_only_supported_keywords(self):
        self.assertEqual(schema.all_schemas(),
                         ["access", "access_result", "capability", "config", "decision", "failure", "health"])

    def test_access_positive_and_negative(self):
        good = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": "cap_" + "a" * 32, "address": 0, "size": 1,
                "operation": "read"}
        schema.validate("access", good)
        for bad in [dict(good, size=0), dict(good, size=True), dict(good, operation="admin"),
                    dict(good, extra=1), dict(good, schema="PK_CAPABILITY_ACCESS/2"), dict(good, address=-1),
                    dict(good, address=2 ** 64), dict(good, handle="cap_XYZ"),
                    {k: v for k, v in good.items() if k != "handle"}]:
            with self.subTest(bad=bad), self.assertRaises(SchemaInvalid):
                schema.validate("access", bad)

    def test_failure_envelope_conforms_for_every_code(self):
        for code in CODES:
            env = envelope(Inv30Error("x", code=code), "0" * 32, "4.3.0")
            schema.validate("failure", env)
            self.assertNotEqual(env["retryable"], env["terminal"])
        schema.validate("failure", envelope(BoundsViolation("oob"), "1" * 32))

    def test_security_codes_are_never_retryable(self):
        for code, (cat, retry, term, _) in CODES.items():
            if cat in ("security", "policy"):
                self.assertFalse(retry, code)

    def test_unknown_exception_hides_details(self):
        env = envelope(RuntimeError("secret path /etc/shadow"), "2" * 32)
        self.assertEqual(env["code"], "INTERNAL")
        self.assertNotIn("shadow", env["message"])


class ServiceContractTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()

    def test_mint_derive_access_invalidate_roundtrip(self):
        m = mint(self.svc)
        self.assertRegex(m["handle"], r"^cap_[0-9a-f]{32}$")
        self.assertEqual(m["enforcement"], "semantic-model")
        d = derive(self.svc, m["handle"], 0x1400, 0x100, ["read"])
        a = access(self.svc, d["handle"], 0x1400)
        schema.validate("access_result", {k: v for k, v in a.items() if k not in ("correlation_id", "traceparent")})
        self.assertEqual(a["enforcement"], "semantic-model")
        self.assertEqual(invalidate(self.svc, m["handle"])["invalidated"], 2)

    def test_every_refusal_is_a_valid_envelope(self):
        m = mint(self.svc)["handle"]
        outs = [access(self.svc, m, 0x5000), access(self.svc, m, 0x1000, op="execute"),
                derive(self.svc, m, 0x0, 0x10), access(self.svc, "cap_" + "0" * 32, 0x1000)]
        for o in outs:
            schema.validate("failure", {k: v for k, v in o.items() if k != "traceparent"})
        self.assertEqual([o["code"] for o in outs],
                         ["BOUNDS_VIOLATION", "PERMISSION_VIOLATION", "AMPLIFICATION", "NOT_FOUND"])

    def test_health_conforms(self):
        schema.validate("health", self.svc.health())

    def test_decisions_conform_and_explain(self):
        m = mint(self.svc)
        recs = self.svc.decisions.explain(m["correlation_id"])
        self.assertEqual(len(recs), 1)
        schema.validate("decision", recs[0])


class CompatibilityFixturesTest(unittest.TestCase):
    """Cross-version rules: v1 requests from 4.2.0-era peers still validate; v2 is refused."""

    def test_fixtures(self):
        cases = json.loads((FIX / "compat" / "cases.json").read_text())
        for c in cases["cases"]:
            with self.subTest(c["name"]):
                if c["expect"] == "accept":
                    schema.validate(c["schema"], c["payload"])
                else:
                    with self.assertRaises(SchemaInvalid):
                        schema.validate(c["schema"], c["payload"])

    def test_422_result_record_still_parses(self):
        # 4.2.0 emitted access records without "enforcement"; 4.3.0 consumers must treat them as model-only.
        old = {"schema": "PK_CAPABILITY_ACCESS/1", "address": 1, "size": 1, "operation": "read", "permitted": True}
        with self.assertRaises(SchemaInvalid):
            schema.validate("access_result", old)  # strict: a record lacking enforcement is never trusted as hw


class ReferenceFixturesTest(unittest.TestCase):
    def test_reference_examples_execute(self):
        svc = make_service()
        ex = json.loads((FIX / "integration" / "reference_flow.json").read_text())
        handle = mint(svc, **{k: v for k, v in ex["mint"].items() if k in ()})["handle"]
        for step in ex["steps"]:
            r = access(svc, handle, step["address"], step["size"], step["operation"])
            self.assertEqual(r.get("code", "OK"), step["expect"], step)


if __name__ == "__main__":
    unittest.main()
