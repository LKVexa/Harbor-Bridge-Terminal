"""GAP-041 error taxonomy, GAP-003 schemas and compatibility fixtures."""
import json, pathlib, unittest
from _support import E, build, ctx
from inv21_local_service_chaining.schema import load_schema, schema_names, validate

FIX = pathlib.Path(__file__).parent / "fixtures"


class ErrorTaxonomyTest(unittest.TestCase):
    def test_codes_unique_stable_and_enveloped(self):
        self.assertEqual(len(E.STABLE_CODES), len(E.ALL_ERRORS))
        golden = json.loads((FIX / "error_codes.v1.json").read_text())
        self.assertTrue(set(golden) <= set(E.STABLE_CODES), "a released code was removed/renamed")
        self.assertFalse(E.RETIRED_CODES & set(E.STABLE_CODES))
        for cls in E.ALL_ERRORS:
            env = cls("m", trace_id="t-1", secret="leak").envelope()
            self.assertEqual(validate(env, load_schema("error")), [], cls)
            self.assertNotIn("secret", env["details"])

    def test_arbitrary_handler_exception_is_sanitised(self):
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        def boom(hop, req):
            raise KeyError("/etc/shadow password=hunter2")
        res.place("svc", "acme", boom, abi="hop")
        with self.assertRaises(E.HandlerFailed) as cm:
            ch.invoke("svc", {}, ctx(v))
        env = cm.exception.envelope()
        self.assertEqual(env["code"], "PK_CHAIN_HANDLER_FAILED")
        self.assertNotIn("hunter2", json.dumps(env))
        self.assertIn("hunter2", cm.exception.diagnostics)  # protected diagnostics keep it

    def test_nested_chain_errors_pass_through_unwrapped(self):
        ch, res, prov, v = build(grants=[("acme", "a", "invoke")])
        res.place("a", "acme", lambda hop, req: hop.call("b", req), abi="hop")
        res.place("b", "other", lambda hop, req: 1, abi="hop")
        with self.assertRaises(E.CrossTenantChain):
            ch.invoke("a", {}, ctx(v))

    def test_from_envelope_unknown_and_malformed(self):
        self.assertIsInstance(E.from_envelope({"schema": "x"}), E.RemoteProtocolError)
        self.assertIsInstance(E.from_envelope({"schema": "PK_CHAIN_ERROR/1", "code": "PK_CHAIN_NOPE"}),
                              E.RemoteProtocolError)
        self.assertIsInstance(E.from_envelope(E.ChainCycle("x").envelope()), E.ChainCycle)
        long = E.from_envelope({**E.HandlerFailed("y").envelope(), "message": "z" * 10000})
        self.assertLessEqual(len(str(long)), 256)


class SchemaTest(unittest.TestCase):
    def test_all_schemas_load_and_use_supported_keywords(self):
        names = schema_names()
        for n in ("local_chain_request", "local_chain_response", "residency", "chain_depth",
                  "call_context", "error", "capability_decision", "chain_config"):
            self.assertIn(n, names)
        for n in names:
            validate({}, load_schema(n))  # raises on unsupported keywords

    def test_golden_valid_invalid_future_fixtures(self):
        cases = json.loads((FIX / "schema_cases.v1.json").read_text())
        self.assertGreaterEqual(len(cases), 20)
        for c in cases:
            errs = validate(c["instance"], load_schema(c["schema"]))
            self.assertEqual(not errs, c["valid"], f"{c['name']}: {errs}")

    def test_schema_ids_are_versioned(self):
        for n in schema_names():
            s = load_schema(n)
            self.assertRegex(s["x-version"], r"^PK_[A-Z_]+/\d+")

    def test_breaking_change_detector(self):
        from tools_path import schema_diff
        old = json.loads((FIX / "schema_snapshot.v1.json").read_text())
        self.assertEqual(schema_diff.breaking(old, {n: load_schema(n) for n in schema_names()}), [])
        mutated = json.loads(json.dumps(old))
        mutated["residency"]["required"] = mutated["residency"]["required"] + ["new_required"]
        self.assertTrue(schema_diff.breaking(old, mutated))


if __name__ == "__main__":
    unittest.main()
