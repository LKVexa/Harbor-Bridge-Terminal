"""Public-interface contract tests for serialized records (MC008, MC009, MC024,
MC057 secure parser, MC058 redaction)."""
import json
import unittest

import _fixtures as F
from inv29_hybrid_wasm_unikernel import records as R
from inv29_hybrid_wasm_unikernel.model import HostImage, WasmModule, compose, verify


class RecordContractTest(unittest.TestCase):
    def setUp(self):
        self.host = HostImage("host", frozenset({"clock", "net-send"}))
        self.mod = WasmModule("svc", frozenset({"clock"}))

    def roundtrip(self, rec, schema):
        wire = R.canonical(json.loads(json.dumps(rec, default=list)))
        return R.parse(wire, schema=schema)

    def test_verification_record_matches_schema(self):
        rec = verify(self.mod, self.host)
        self.roundtrip(rec, "PK_HYBRID_VERIFICATION/1")
        failing = verify(WasmModule("svc", frozenset({"x"}), hardened=False), self.host)
        self.roundtrip(failing, "PK_HYBRID_VERIFICATION/1")

    def test_composition_record_matches_schema(self):
        self.roundtrip(compose(self.mod, self.host), "PK_HYBRID_COMPOSITION/1")

    def test_admitted_record_matches_schema(self):
        kr = F.keyring()
        self.roundtrip(F.admitter(kr).admit(F.request(kr)), "PK_HYBRID_COMPOSITION/1")

    def test_schema_rejects_contract_violations(self):
        base = json.loads(json.dumps(compose(self.mod, self.host), default=list))
        mutations = {
            "single-layer": lambda r: r.update(layers=r["layers"][:1], layer_count=1),
            "no-defence-in-depth": lambda r: r.update(defence_in_depth=False),
            "wrong-schema": lambda r: r.update(schema="PK_HYBRID_COMPOSITION/2"),
            "unknown-field": lambda r: r.update(escape_hatch=True),
            "missing-field": lambda r: r.pop("imports"),
            "bool-as-int": lambda r: r.update(layer_count=True),
            "empty-name": lambda r: r.update(module=" "),
        }
        for name, mut in mutations.items():
            rec = json.loads(json.dumps(base))
            mut(rec)
            with self.subTest(name), self.assertRaises(R.RecordInvalid):
                R.validate(rec, "PK_HYBRID_COMPOSITION/1")

    def test_parser_hostile_inputs(self):
        hostile = [b"", b"[]", b"42", b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}',
                   b"\xff\xfe", b"[" * 5000 + b"]" * 5000, b'{"a":' * 40 + b"1" + b"}" * 40,
                   b"{" + b" " * (R.MAX_RECORD_BYTES + 1) + b"}", b'{"a":}']
        for h in hostile:
            with self.subTest(h=h[:20]), self.assertRaises(R.RecordInvalid):
                R.parse(h)

    def test_unknown_schema_refused(self):
        with self.assertRaises(R.RecordInvalid):
            R.validate({}, "PK_HYBRID_SOMETHING/1")

    def test_redaction(self):
        out = R.redact({"tenant": "acme", "api_key": "k", "nested": [{"client_secret": "s", "ok": 1}],
                        "Signing-Key": b"x", "token": "t"})
        self.assertEqual(out["tenant"], "acme")
        self.assertEqual(out["api_key"], R.REDACTED)
        self.assertEqual(out["nested"][0], {"client_secret": R.REDACTED, "ok": 1})
        self.assertEqual(out["Signing-Key"], R.REDACTED)
        self.assertEqual(out["token"], R.REDACTED)

    def test_canonical_is_deterministic(self):
        self.assertEqual(R.canonical({"b": 1, "a": [2, 1]}), b'{"a":[2,1],"b":1}')
        with self.assertRaises(ValueError):
            R.canonical({"x": float("nan")})


if __name__ == "__main__":
    unittest.main()
