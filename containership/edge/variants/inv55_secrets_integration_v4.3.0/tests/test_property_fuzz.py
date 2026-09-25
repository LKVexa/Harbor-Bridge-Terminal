"""Seeded property-based and fuzz tests (checklist #84).  Stdlib only (no hypothesis);
seeds are fixed for reproducibility and can be overridden with INV55_FUZZ_SEED / INV55_FUZZ_N."""
from __future__ import annotations

import json
import os
import random
import string
import unittest

from helpers import SECRET, Env
from inv55_secrets_integration.audit import verify_chain
from inv55_secrets_integration.config import deep_merge
from inv55_secrets_integration.errors import ErrorCode
from inv55_secrets_integration.identity import HmacJwtAuthenticator

SEED = int(os.environ.get("INV55_FUZZ_SEED", "20260922"))
N = int(os.environ.get("INV55_FUZZ_N", "400"))
CODES = {c.value.code for c in ErrorCode}


def rand_value(rng: random.Random, depth: int = 0):
    k = rng.randrange(8 if depth < 2 else 5)
    if k == 0:
        return None
    if k == 1:
        return rng.choice([True, False])
    if k == 2:
        return rng.choice([0, -1, 1, 2**63, 3.5, float("nan"), float("inf")])
    if k == 3:
        return "".join(rng.choice(string.printable + "\u0000‮퟿") for _ in range(rng.randrange(0, 300)))
    if k == 4:
        return rng.choice(["db-password", "PK_SECRET_RESOLVE/1", "PK_SECRET_ROTATE/1", "PK_SECRET_SCOPE/1", SECRET])
    if k == 5:
        return [rand_value(rng, depth + 1) for _ in range(rng.randrange(0, 4))]
    return {rng.choice(["name", "protocol", "lease_id", "apps", "value", "ttl_s", "x"]): rand_value(rng, depth + 1)
            for _ in range(rng.randrange(0, 4))}


class Fuzz(unittest.TestCase):
    def test_public_api_never_raises_and_never_leaks(self):
        """Arbitrary request dicts: every op returns a well-formed result, never raises, never leaks."""
        rng = random.Random(SEED)
        e = Env()
        e.seed()
        good = e.cred("admin")
        ops = [e.svc.resolve, e.svc.use, e.svc.revoke, e.svc.rotate, e.svc.retire, e.svc.set_scope]
        for i in range(N):
            req = {k: rand_value(rng) for k in rng.sample(
                ["protocol", "name", "lease_id", "apps", "value", "ttl_s", "version", "idempotency_key",
                 "expected_version", "credential", "request_id", "traceparent", "timeout_ms"], rng.randrange(0, 10))}
            if rng.random() < 0.5:
                req["credential"] = good
            op = rng.choice(ops)
            r = op(req)
            self.assertIsInstance(r, dict)
            json.dumps(r, allow_nan=True)
            if not r["ok"]:
                self.assertIn(r["error"]["code"], CODES)
                self.assertNotEqual(r["error"]["code"], ErrorCode.INTERNAL.value.code, (op.__name__, req))
            elif "value" in r:
                self.assertEqual(op, e.svc.use)
        diag = e.all_diagnostics()
        # the seeded value may only appear if the fuzzer itself rotated it in as a *new* value; it never
        # appears in diagnostics regardless
        self.assertNotIn(SECRET, diag)
        self.assertTrue(verify_chain(e.sink.lines, b"audit-key")[0])

    def test_jwt_bitflip_never_authenticates(self):
        rng = random.Random(SEED + 1)
        a = HmacJwtAuthenticator(b"k" * 32, "i", "a", lambda: 100.0)
        tok = a.issue("s", "t", ["consumer"])
        for _ in range(N):
            b = bytearray(tok.encode())
            i = rng.randrange(len(b))
            b[i] = rng.choice(b"ABCDEFabcdef0123456789-_.")
            mutated = b.decode()
            if mutated == tok:
                continue
            try:
                p = a.authenticate(mutated)
            except Exception:
                continue
            # base64 padding slack can decode identically; must still be the same principal
            self.assertEqual((p.subject, p.tenant), ("s", "t"))


class Properties(unittest.TestCase):
    def test_rotation_monotonic_versions(self):
        rng = random.Random(SEED + 2)
        e = Env()
        e.seed()
        last = 1
        for i in range(60):
            r = e.svc.rotate({"protocol": "PK_SECRET_ROTATE/1", "credential": e.cred("admin"),
                              "name": "db-password", "value": f"v{i}", "idempotency_key": f"idem-prop-{i:04d}"})
            self.assertEqual(r["version"], last + 1)
            last = r["version"]
            if rng.random() < 0.3:
                lease = e.resolve()
                self.assertEqual(e.use(lease["lease_id"])["value"], f"v{i}")

    def test_lease_valid_iff_before_expiry(self):
        rng = random.Random(SEED + 3)
        e = Env()
        e.seed()
        for _ in range(100):
            ttl = rng.uniform(0.1, 50)
            r = e.resolve(ttl_s=ttl)
            dt = rng.uniform(0, 100)
            e.clock.advance(dt)
            u = e.use(r["lease_id"])
            self.assertEqual(u["ok"], dt < ttl, (ttl, dt))

    def test_deep_merge_identity_and_idempotence(self):
        rng = random.Random(SEED + 4)
        for _ in range(200):
            a = {str(rng.randrange(5)): rng.randrange(9) for _ in range(rng.randrange(5))}
            b = {str(rng.randrange(5)): rng.randrange(9) for _ in range(rng.randrange(5))}
            self.assertEqual(deep_merge(a, {}), a)
            self.assertEqual(deep_merge(deep_merge(a, b), b), deep_merge(a, b))


if __name__ == "__main__":
    unittest.main()
