"""M70 - seeded fuzz/property tests for untrusted boundaries: no input may crash a
boundary with anything other than a structured FabricError (or a clean refusal)."""
import base64, json, random, unittest
from _harness import World
from inv60_wasm_application_fabric.fabric import wire, config as cf, telemetry as tm, negotiation as ng
from inv60_wasm_application_fabric.fabric.errors import FabricError, Result
from inv60_wasm_application_fabric.fabric.fabric import AUDIENCE

N = 400


def rand_json(rng, depth=0):
    k = rng.randrange(7 if depth < 3 else 4)
    if k == 0: return rng.choice([None, True, False])
    if k == 1: return rng.randint(-2**40, 2**40)
    if k == 2: return rng.random() * rng.choice([1, -1e9, 1e300])
    if k == 3: return "".join(chr(rng.randrange(0, 0x2FF)) for _ in range(rng.randrange(0, 40)))
    if k in (4, 5): return {rand_json(rng, 9) if False else f"k{rng.randrange(20)}": rand_json(rng, depth + 1) for _ in range(rng.randrange(6))}
    return [rand_json(rng, depth + 1) for _ in range(rng.randrange(6))]


class Fuzz(unittest.TestCase):
    def test_wire_decode(self):
        rng = random.Random(1)
        for s in ("PK_LATTICE_START", "PK_LATTICE_LINK", "PK_LATTICE_CALL"):
            for _ in range(N):
                raw = rng.choice([json.dumps(rand_json(rng)).encode(), bytes(rng.randrange(256) for _ in range(rng.randrange(64)))])
                try:
                    wire.decode(raw, s)
                except FabricError as e:
                    self.assertIn(e.code, ("INVALID_ARGUMENT", "PAYLOAD_TOO_LARGE"))

    def test_tokens(self):
        w = World(hosts=("h1",)); rng = random.Random(2)
        good = w.tok("api")
        for _ in range(N):
            t = list(good); i = rng.randrange(len(t)); t[i] = rng.choice("abcXYZ0123-_.=")
            cand = rng.choice(["".join(t), base64.b64encode(bytes(rng.randrange(256) for _ in range(40))).decode(), "", "." * rng.randrange(5)])
            if cand == good:
                continue
            with self.assertRaises(FabricError):
                w.trust.authenticate(cand, AUDIENCE)

    def test_envelopes(self):
        w = World(hosts=("h1",), limits={"burst_per_tenant": 100000}); rng = random.Random(3)
        for _ in range(N // 2):
            env = rand_json(rng)
            if rng.random() < 0.5:
                env = w.artifact(); env["payload"] = base64.b64encode(json.dumps(rand_json(rng)).encode()).decode()
            r = w.fabric.push(w.tok("deployer-a"), "tenant-a/api", b"x", env if isinstance(env, dict) else {"x": env}, tenant="tenant-a")
            self.assertEqual(r.code, "SIGNATURE_INVALID", r.to_wire())

    def test_config(self):
        rng = random.Random(4); keys = list(cf.SCHEMA)
        for _ in range(N):
            c = cf.defaults()
            for _ in range(rng.randrange(1, 4)):
                c[rng.choice(keys)] = rand_json(rng)
            try:
                out = cf.validate(c)
                self.assertTrue(out["transport.require_tls"])
            except FabricError as e:
                self.assertEqual(e.code, "INVALID_ARGUMENT")

    def test_traceparent_and_result_decode(self):
        rng = random.Random(5)
        for _ in range(N):
            s = "".join(rng.choice("0123456789abcdef-") for _ in range(rng.randrange(80)))
            self.assertRegex(tm.TraceContext.parse(s).trace_id, r"^[0-9a-f]{32}$")
            r = rand_json(rng)
            if isinstance(r, dict):
                try:
                    Result.from_wire(r)
                except (TypeError, ValueError):
                    pass

    def test_negotiation_offers(self):
        rng = random.Random(6); seed, pub = ng.ed25519.public_key, None
        from inv60_wasm_application_fabric.fabric.identity import new_keypair
        seed, pub = new_keypair()
        for _ in range(N // 4):
            body = rand_json(rng)
            o = {"body": body if isinstance(body, dict) else {"versions": body}}
            o["sig"] = ng.ed25519.sign(seed, ng.canonical(o["body"])).hex()
            try:
                ng.negotiate(o, pub)
            except FabricError as e:
                self.assertIn(e.code, ("INVALID_ARGUMENT", "UNSUPPORTED_VERSION", "UNAUTHENTICATED"))


if __name__ == "__main__":
    unittest.main()
