"""Wire protocol, fixtures, schema drift, negotiation, config (components 12, 16-19, 22-26, 72)."""
from __future__ import annotations

import json
import random
import string
import unittest

from _support import PKG_DIR, TmpDirCase, make_broker, signed
from inv53_message_reliability import config as C
from inv53_message_reliability import protocol as W
from inv53_message_reliability.errors import CODES, Outcome, taxonomy


class ProtocolTest(unittest.TestCase):
    def test_conformance_fixtures(self):
        files = sorted((PKG_DIR / "fixtures" / "wire").glob("*.json"))
        self.assertGreaterEqual(len(files), 12)
        for f in files:
            fx = json.loads(f.read_text())
            try:
                W.validate_request(fx["request"])
                got = "OK"
            except W.ProtocolError as exc:
                got = exc.code
            self.assertEqual(got, fx["expect_validation"], f.name)

    def test_generated_schemas_have_not_drifted(self):
        for name, schema in W.json_schemas().items():
            on_disk = json.loads((PKG_DIR / "schemas" / name).read_text())
            self.assertEqual(on_disk, json.loads(json.dumps(schema)), name)
        self.assertEqual(json.loads((PKG_DIR / "schemas" / "errors.json").read_text()), taxonomy())

    def test_every_required_field_in_schema_matches_validator(self):
        req = W.json_schemas()["request.schema.json"]
        for clause in req["allOf"]:
            op = clause["if"]["properties"]["op"]["const"]
            for field in clause["then"]["required"]:
                self.assertIn(op, W.REQUEST_FIELDS[field][1])

    def test_negotiation(self):
        self.assertEqual(W.negotiate(["inv53.wire/1", "inv53.wire/7"]), "inv53.wire/1")
        for bad in (["inv53.wire/2"], [], "inv53.wire/1", None):
            with self.assertRaises(W.ProtocolError):
                W.negotiate(bad)

    def test_error_taxonomy_is_closed_and_consistent(self):
        with self.assertRaises(ValueError):
            Outcome("E_MADE_UP")
        for c in CODES.values():
            if c.kind.value == "terminal":
                self.assertFalse(c.retryable, c.code)
        self.assertTrue(Outcome("OK_DUPLICATE").ok)
        self.assertFalse(Outcome("E_SHED").ok)


class FuzzTest(TmpDirCase):
    """Random requests must always yield a well-formed response, never an exception (component 73)."""

    def _junk(self, rng, depth=0):
        kind = rng.randrange(8 if depth < 3 else 5)
        return [lambda: rng.choice([None, True, False]),
                lambda: rng.uniform(-1e308, 1e308),
                lambda: rng.randrange(-2**70, 2**70),
                lambda: "".join(rng.choice(string.printable + "\u0000‮/.") for _ in range(rng.randrange(0, 40))),
                lambda: float(rng.choice(["nan", "inf", "-inf"])),
                lambda: [self._junk(rng, depth + 1) for _ in range(rng.randrange(3))],
                lambda: {rng.choice(list(W.REQUEST_FIELDS) + ["x", "id"]): self._junk(rng, depth + 1)
                         for _ in range(rng.randrange(6))},
                lambda: {"id": self._junk(rng, depth + 1)}][kind]()

    def test_random_requests_never_escape(self):
        b, _ = make_broker(self.tmp)
        rng = random.Random(53)
        ops = list(W.OPS) + ["drop", ""]
        for i in range(3000):
            req = {f: self._junk(rng) for f in rng.sample(list(W.REQUEST_FIELDS), rng.randrange(0, 8))}
            if rng.random() < 0.7:
                req.update({"v": "inv53.wire/1", "op": rng.choice(ops), "tenant": "acme", "queue": "q"})
            if rng.random() < 0.5:
                req = signed({k: v for k, v in req.items() if k not in ("v", "auth")})
            resp = b.handle(req)
            self.assertIn(resp["outcome"]["code"], CODES)
            json.dumps(resp)   # always serialisable
            self.assertNotEqual(resp["outcome"]["code"], "E_INTERNAL", req)

    def test_structured_well_typed_fuzz_reaches_every_op(self):
        b, clock = make_broker(self.tmp / "s", config={"tenant_burst": 1_000_000, "tenant_rate_per_second": 1e6,
                                                       "max_ready": 50, "max_in_flight": 20, "max_attempts": 2})
        rng = random.Random(530)
        leases, seen = [], {}
        for i in range(4000):
            op = rng.choice(W.OPS)
            req = {"op": op, "tenant": "acme", "queue": rng.choice(["q", "r"])}
            mid = f"m{rng.randrange(30)}"
            now = rng.choice([rng.uniform(0, 500), 0.0, 1e12, -5.0])
            if op == "put":
                req["message"] = {"id": mid, "n": rng.randrange(3)}
            if op in ("ack", "nack", "extend", "redrive", "explain"):
                req["id"] = mid
            if op in ("ack", "nack", "extend"):
                if leases and rng.random() < 0.8:
                    req["id"], req["lease"] = rng.choice(leases[-5:])
                else:
                    req["lease"] = "f" * 32
            if op in ("receive", "ack", "nack", "extend", "redrive") and rng.random() < 0.3:
                req["now"] = now                     # deprecated and ignored: must not matter
            clock.t += rng.choice([0] * 12 + [1, 2, 5, 40, 400])  # the broker clock drives lease expiry
            if op == "extend":
                req["extension"] = rng.choice([0.5, 30, 299.0])
            if op == "nack" and rng.random() < 0.5:
                req["requeue"] = rng.random() < 0.5
            resp = b.handle(signed(req, ts=clock.t))
            c = resp["outcome"]["code"]
            seen[(op, c)] = seen.get((op, c), 0) + 1
            self.assertNotEqual(c, "E_INTERNAL", (req, resp))
            if "delivery" in resp:
                leases.append((resp["delivery"]["message"]["id"], resp["delivery"]["lease"]))
        ok_ops = {op for (op, c) in seen if c == "OK"}
        self.assertTrue({"put", "receive", "ack", "nack", "extend", "redrive", "explain", "health"} <= ok_ops, seen)
        for key, h in b.health()["queues"].items():
            self.assertLessEqual(h["ready"], 50)
            self.assertLessEqual(h["in_flight"], 20)


class ConfigTest(TmpDirCase):
    def test_secure_defaults(self):
        d = C.defaults()
        self.assertTrue(d["require_authentication"] and d["fsync"] and d["audit_required"])
        self.assertEqual(C.validate({}), d)

    def test_rejections(self):
        for bad in ({"typo_key": 1}, {"max_attempts": 0}, {"max_attempts": 1.5}, {"visibility_seconds": float("nan")},
                    {"fsync": 1}, {"max_attempts": True}, {"max_in_flight": 10, "max_ready": 5}):
            with self.assertRaises(C.ConfigError, msg=str(bad)):
                C.validate(bad)

    def test_layering_and_provenance(self):
        eff = C.layer(("base", {"max_attempts": 4}), ("env:prod", {"visibility_seconds": 60}),
                      ("site:edge-7", {"max_attempts": 8}))
        self.assertEqual(eff.values["max_attempts"], 8)
        self.assertEqual(eff.provenance["max_attempts"], "site:edge-7")
        self.assertEqual(eff.provenance["visibility_seconds"], "env:prod")
        self.assertEqual(eff.provenance["fsync"], "default")
        self.assertEqual(eff.digest, C.digest(eff.values))
        self.assertEqual(C.layer(("base", {"max_attempts": 4})).digest, C.layer(("x", {"max_attempts": 4})).digest)

    def test_atomic_update_cas_and_rollback(self):
        s = C.ConfigStore(self.tmp / "cfg.json")
        v, cur = s.current()
        self.assertEqual(v, 1)
        v2 = s.update({"max_attempts": 7}, expected_version=1)
        with self.assertRaises(C.ConfigConflict):
            s.update({"max_attempts": 9}, expected_version=1)
        before = (self.tmp / "cfg.json").read_bytes()
        with self.assertRaises(C.ConfigError):
            s.update({"max_attempts": -1}, expected_version=v2)
        self.assertEqual((self.tmp / "cfg.json").read_bytes(), before, "invalid update leaves file untouched")
        v3 = s.rollback()
        self.assertEqual(s.current(), (v3, C.defaults()))
        with self.assertRaises(C.ConfigError):
            s.rollback()
        self.assertFalse(list(self.tmp.glob(".cfg-*.tmp")), "no temp files left behind")


if __name__ == "__main__":
    unittest.main()
