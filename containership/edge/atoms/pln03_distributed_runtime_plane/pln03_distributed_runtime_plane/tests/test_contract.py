"""Wire-level contract, schema, conformance-fixture and fuzz tests (MC-012, MC-018, MC-035, MC-046)."""
from __future__ import annotations

import json
import pathlib
import random
import unittest

from _helpers import envelope, make_plane, negotiation
from pln03_distributed_runtime_plane import wire

PKG = pathlib.Path(__file__).resolve().parents[1]


def run_fixture(path):
    gp, _, issuer, *_ = make_plane()
    fx = json.loads(path.read_text())
    toks = {k: issuer.mint(v["workload"], v["tenant"], set(v["capabilities"])) for k, v in fx["tokens"].items()}
    results = []
    for step in fx["steps"]:
        req = dict(step["request"])
        if req.get("token") in toks:
            req["token"] = toks[req["token"]]
        resp = json.loads(wire.handle(gp, json.dumps(req)))
        results.append((step, resp))
    return results


class ContractTests(unittest.TestCase):
    def test_mc012_all_schemas_parse_and_are_closed(self):
        for p in (PKG / "schemas").glob("*.json"):
            s = json.loads(p.read_text())
            self.assertEqual(s["type"], "object", p.name)
            self.assertFalse(s.get("additionalProperties", True), p.name)

    def test_mc012_wit_declares_every_interface(self):
        wit = (PKG / "wit" / "pk-runtime.wit").read_text()
        for iface in ("interface state", "interface messaging", "interface secrets", "interface invoke"):
            self.assertIn(iface, wit)
        self.assertIn("package pk:runtime@1.0.0", wit)

    def test_mc018_conformance_fixtures(self):
        for path in sorted((PKG / "fixtures" / "conformance").glob("*.json")):
            for step, resp in run_fixture(path):
                exp = step["expect"]
                with self.subTest(step=step["name"]):
                    self.assertEqual(resp["ok"], exp["ok"], resp)
                    if exp["ok"]:
                        self.assertEqual(resp["result"], exp["result"])
                    else:
                        envelope.validate_envelope(resp["error"])
                        self.assertEqual(resp["error"]["code"], exp["code"])
                        if "trace_id" in exp:
                            self.assertEqual(resp["error"]["trace_id"], exp["trace_id"])

    def test_mc015_error_envelope_matches_packaged_schema(self):
        schema = wire.load_schema("error-envelope.v1")
        for code in envelope.CODES:
            exc = type("E", (Exception,), {"code": code})("m")
            wire.check(envelope.to_envelope(exc), schema)

    def test_mc016_hello_matches_schema(self):
        wire.check(negotiation.hello(), wire.load_schema("hello.v1"))

    def test_mc021_default_config_matches_schema(self):
        from pln03_distributed_runtime_plane import config
        wire.check(config.DEFAULT, wire.load_schema("config.v1"))

    def test_mc035_mc046_fuzz_wire_never_crashes_or_leaks(self):
        gp, tok, *_ = make_plane()
        gp.state_set("api", "t1", "secretish", b"FUZZ_SENTINEL_VALUE", token=tok)
        rng = random.Random(int(__import__("os").environ.get("PK_FUZZ_SEED", "20260923")))
        base = {"interface": "PK_STATE/1", "op": "get", "workload": "api", "tenant": "t1", "token": tok, "key": "k"}
        alphabet = ["", "\x00", "../", "/", ":", "A" * 5000, None, 1, True, [], {}, "t1/../t2", "\ud800",
                    "' OR 1=1 --", "${jndi:x}", tok[:-2] + "xx"]
        for i in range(3000):
            req = dict(base)
            for _ in range(rng.randint(1, 3)):
                field = rng.choice(list(base) + ["value", "operations", "extra"])
                req[field] = rng.choice(alphabet)
            raw = json.dumps(req) if rng.random() < 0.9 else json.dumps(req)[: rng.randint(0, 40)]
            resp = json.loads(wire.handle(gp, raw))
            if not resp["ok"]:
                envelope.validate_envelope(resp["error"])
                self.assertNotEqual(resp["error"]["code"], "PK_RUNTIME_ERROR", (req, resp))
            self.assertNotIn("FUZZ_SENTINEL_VALUE", json.dumps(resp))
        self.assertIn(json.loads(wire.handle(gp, b"[" * 100000))["error"]["code"], {"PK_INVALID_ARGUMENT"})

    def test_mc035_replay_of_publish_is_idempotent_across_wire(self):
        gp, tok, *_ = make_plane()
        req = json.dumps({"interface": "PK_MESSAGE/1", "op": "publish", "workload": "api", "tenant": "t1",
                          "token": tok, "topic": "x", "payload": "eA==", "idempotency_key": "k"})
        outs = [json.loads(wire.handle(gp, req))["result"]["accepted"] for _ in range(50)]
        self.assertEqual(outs.count(True), 1)

    def test_mc035_oversize_request_rejected_before_parse(self):
        gp, *_ = make_plane()
        resp = json.loads(wire.handle(gp, "x" * (wire.MAX_REQUEST_BYTES + 1)))
        self.assertEqual(resp["error"]["code"], "PK_INVALID_ARGUMENT")


if __name__ == "__main__":
    unittest.main()
