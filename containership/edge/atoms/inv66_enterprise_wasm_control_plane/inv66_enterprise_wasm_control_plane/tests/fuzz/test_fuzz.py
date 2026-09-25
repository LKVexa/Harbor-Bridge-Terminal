"""Property/fuzz tests (MC-037). Deterministic seed; iteration count from INV66_FUZZ_ITERS (default 400)."""
from __future__ import annotations

import copy
import json
import os
import random
import unittest

from tests.support import EcpError, Estate
from inv66_enterprise_wasm_control_plane.production import schema

SEED = int(os.environ.get("INV66_FUZZ_SEED", "20260922"))
ITERS = int(os.environ.get("INV66_FUZZ_ITERS", "400"))
ATOMS = [None, True, 0, -1, 2 ** 63, 1.5, float("inf"), "", " ", "a" * 5000, "\x00", "é", "../", "registry.estate.local/x",
         [], {}, [1], {"k": "v"}]


def mutate(rng: random.Random, obj):
    obj = copy.deepcopy(obj)
    paths = []

    def walk(o, p):
        paths.append(p)
        if isinstance(o, dict):
            for k in o:
                walk(o[k], p + [k])
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, p + [i])
    walk(obj, [])
    p = rng.choice(paths[1:])
    parent = obj
    for k in p[:-1]:
        parent = parent[k]
    op = rng.random()
    if op < 0.6:
        parent[p[-1]] = rng.choice(ATOMS)
    elif op < 0.8 and isinstance(parent, dict):
        del parent[p[-1]]
    elif isinstance(parent, dict):
        parent[f"x{rng.randint(0, 9)}"] = rng.choice(ATOMS)
    else:
        parent.append(rng.choice(ATOMS))
    return obj


class FuzzTest(unittest.TestCase):
    def test_admission_never_crashes_never_admits_mutants(self):
        rng = random.Random(SEED)
        e = Estate(fsync=False)
        base = e.request("api", "web")
        tok = e.token("ops", ttl=3600)
        admitted_bad = 0
        for i in range(ITERS):
            m = mutate(rng, base)
            m["request_id"] = f"f{i}"
            try:
                d = e.service.admit(m, tok)
            except EcpError:
                continue
            except Exception as exc:  # noqa: BLE001
                self.fail(f"non-EcpError {type(exc).__name__} on {json.dumps(m, default=str)[:300]}")
            if d["admitted"]:
                # an admitted mutant must still be fully valid: re-verify independently
                comps = m["manifest"]["components"]
                ok = all(c.get("signature") == next((b["signature"] for b in base["manifest"]["components"]
                                                     if b["name"] == c.get("name") and b["image"] == c.get("image")), None)
                         for c in comps)
                if not ok:
                    admitted_bad += 1
        self.assertEqual(admitted_bad, 0)
        self.assertEqual(e.service.journal.verify()["result"], "INTACT")

    def test_schema_valid_semantic_fuzz(self):
        """Mutations that pass the schema, so they reach RBAC, provenance and policy."""
        rng = random.Random(SEED + 3)
        e = Estate(fsync=False)
        tok = e.token("ops", ttl=3600)
        pool = [e.component(n, registry=r) for n in ("api", "web", "debug-shell")
                for r in ("eu.registry.estate.local", "registry.estate.local", "ghcr.evil.example")]
        pool += [e.component("api", signer=e.other_signer), dict(e.component("api"), signer="nobody"),
                 dict(e.component("api"), signature=e.component("web")["signature"]),
                 dict(e.component("api"), image="eu.registry.estate.local/api:latest")]
        admitted = 0
        for i in range(ITERS):
            comps = [copy.deepcopy(rng.choice(pool)) for _ in range(rng.randint(1, 4))]
            r = {"protocol": "PK_ECP_ADMIT/1", "request_id": f"s{i}", "tenant": "payments",
                 "lattice": rng.choice(["prod", "staging"]), "manifest": {"components": comps}}
            d = e.service.admit(r, tok if r["lattice"] == "prod" else e.token("contractor", ttl=3600))
            if d["admitted"]:
                admitted += 1
                names = [c["name"] for c in comps]
                self.assertEqual(len(names), len(set(names)))
                for c in comps:
                    allowed = ("eu.registry.estate.local/",) if r["lattice"] == "prod" else \
                        ("eu.registry.estate.local/", "registry.estate.local/")
                    self.assertTrue(c["image"].startswith(allowed), c)
                    self.assertIn("@sha256:", c["image"])
                    self.assertEqual(c["signature"], e.component(c["name"])["signature"])
                    self.assertNotEqual(c["name"], "debug-shell")
        self.assertGreater(admitted, 0)
        self.assertEqual(e.service.journal.verify()["result"], "INTACT")

    def test_token_fuzz(self):
        rng = random.Random(SEED + 1)
        e = Estate(fsync=False)
        tok = e.token("ops", ttl=3600)
        for _ in range(ITERS):
            b = bytearray(tok.encode())
            for _ in range(rng.randint(1, 4)):
                b[rng.randrange(len(b))] = rng.randrange(33, 127)
            t = b.decode("ascii", "replace")
            if t == tok:
                continue
            try:
                p = e.auth.authenticate_token(t)
            except EcpError:
                continue
            # base64url padding slack can decode to identical bytes; anything accepted must equal the original claims
            self.assertEqual(p.subject, "ops")

    def test_schema_validator_total(self):
        rng = random.Random(SEED + 2)
        e = Estate(fsync=False)
        doc = e.config()
        for _ in range(ITERS // 2):
            m = mutate(rng, doc)
            try:
                schema.errors(m, schema.load("PK_ECP_CONFIG_1"))
            except Exception as exc:  # noqa: BLE001
                self.fail(f"validator crashed: {exc!r}")


if __name__ == "__main__":
    unittest.main()
