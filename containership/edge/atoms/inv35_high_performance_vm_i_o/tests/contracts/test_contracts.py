"""INV-35-C022/C026/C029/C082: every public interface is checked against its committed schema."""
from __future__ import annotations

import json
import unittest

from _support import (PKG_DIR, Inv35Error, errors, lifecycle, one, rt, schema, schema_check, stack, wire,
                      MemoryRegion)

validate = schema_check.validate


class SchemaArtifactsTest(unittest.TestCase):
    def test_schemas_match_generator(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "gen_schemas.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_error_codes_are_append_only_and_unique(self):
        doc = schema("errors/error_codes.json")
        codes = [c["code"] for c in doc["codes"]]
        self.assertEqual(len(codes), len(set(codes)))
        frozen = json.loads((PKG_DIR / "schemas" / "errors" / "published_codes_4.3.0.json").read_text())
        for code, outcome in frozen.items():  # a published code must keep its outcome class forever
            self.assertEqual(errors.REGISTRY[code].outcome.value, outcome, code)

    def test_unregistered_code_cannot_be_raised(self):
        with self.assertRaises(ValueError):
            Inv35Error("INV35-E999")


class InterfaceContractTest(unittest.TestCase):
    def setUp(self):
        self.r, self.cp, self.dp, self.ctl, self.bulk = stack()

    def test_submit_and_complete_results_conform(self):
        res = self.dp.submit(self.bulk, tenant="t1", queue="q0", chain=one(), head=0, idempotency_key="k")
        validate(res, schema("submit/submit.result.schema.json"))
        replay = self.dp.submit(self.bulk, tenant="t1", queue="q0", chain=one(), head=0, idempotency_key="k")
        validate(replay, schema("submit/submit.result.schema.json"))
        done = self.dp.complete(self.bulk, tenant="t1", queue="q0", guest_wants_notification=True)
        validate(done, schema("complete/complete.result.schema.json"))

    def test_every_error_conforms(self):
        s = schema("errors/error.schema.json")
        for code in errors.REGISTRY:
            validate(Inv35Error(code, "x").to_dict(), s)

    def test_status_conforms(self):
        validate(self.cp.status(self.ctl, tenant="t1", queue="q0"), schema("status/status.schema.json"))

    def test_decisions_conform(self):
        with self.assertRaises(Inv35Error):
            self.dp.submit(self.bulk, tenant="t1", queue="q0", chain=one(addr=0), head=0)
        s = schema("status/decision.schema.json")
        for d in self.r.decisions:
            validate(d, s)

    def test_effective_config_conforms(self):
        validate(self.r.config.active.values, schema("config/config.schema.json"))

    def test_lifecycle_document_matches_code(self):
        self.assertEqual(schema("status/lifecycle.json"), lifecycle.state_machine_document())


class FixtureConformanceTest(unittest.TestCase):
    """Reusable conformance fixtures: any implementation must reproduce these codes."""

    def test_all_fixtures(self):
        files = sorted((PKG_DIR / "fixtures").rglob("*.json"))
        self.assertGreaterEqual(len(files), 15)
        for f in files:
            fx = json.loads(f.read_text())
            with self.subTest(fixture=f.name):
                r = rt.Runtime()
                cp, dp = rt.ControlPlane(r), rt.Datapath(r)
                ctl = r.authority.mint("c", "t1", {"q0"}, {"register_memory"})
                bulk = r.authority.mint("v", "t1", {"q0"}, {"submit", "complete"})
                cp.register_queue(ctl, tenant="t1", queue="q0",
                                  regions=tuple(MemoryRegion(b, l) for b, l in fx["setup"]["regions"]))
                try:
                    req = wire.decode_submit(fx["request"])
                    dp.submit(bulk, tenant=req["tenant"], queue=req["queue"], chain=req["chain"], head=req["head"],
                              idempotency_key=req["idempotency_key"], traceparent=req["traceparent"])
                    got = "INV35-E000"
                except Inv35Error as exc:
                    got = exc.code
                self.assertEqual(got, fx["expect"], f.name)
                if f.parent.name == "valid":
                    self.assertEqual(r.queues["q0"].vq.in_flight, 1)
                else:
                    self.assertEqual(r.queues["q0"].vq.in_flight_descriptors, 0, "refusal must not mutate")


if __name__ == "__main__":
    unittest.main()
