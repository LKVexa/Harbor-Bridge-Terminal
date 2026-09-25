"""GAP-025 fuzz/property tests (stdlib, seeded, reproducible).

Seed via INV21_FUZZ_SEED; iterations via INV21_FUZZ_ITERS (default 400 -- the
release gate runs 5000). Properties: (P1) any input yields a value or a
ChainError/ValueError/TypeError, never another exception type; (P2) a refused
call never runs the handler; (P3) every public error envelope validates against
PK_CHAIN_ERROR/1; (P4) the wire parser never raises outside the taxonomy.
"""
import json, os, random, string, unittest
from _support import E, ChainEndpoint, build, ctx, verifier
from inv21_local_service_chaining.schema import load_schema, validate
from inv21_local_service_chaining.transport import parse_response

SEED = int(os.environ.get("INV21_FUZZ_SEED", "2109"))
ITERS = int(os.environ.get("INV21_FUZZ_ITERS", "400"))
ALPH = string.printable + "é☃\x00퟿"


def rstr(r, n=40):
    return "".join(r.choice(ALPH) for _ in range(r.randint(0, n)))


def rval(r, depth=0):
    k = r.randint(0, 7 if depth < 3 else 4)
    return [lambda: None, lambda: r.random() < .5, lambda: r.randint(-2**63, 2**63),
            lambda: r.random() * 1e308, lambda: rstr(r),
            lambda: [rval(r, depth + 1) for _ in range(r.randint(0, 4))],
            lambda: {rstr(r, 8): rval(r, depth + 1) for _ in range(r.randint(0, 4))},
            lambda: b"bytes"][k]()


class FuzzTest(unittest.TestCase):
    def test_P1_P2_P3_public_call_path(self):
        r = random.Random(SEED)
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        ran = []
        res.place("svc", "acme", lambda hop, q: ran.append(1) or q, abi="hop")
        schema = load_schema("error")
        for i in range(ITERS):
            callee = r.choice(["svc", rstr(r), "svc" + rstr(r, 3), r.randint(0, 9), None])
            before = len(ran)
            try:
                ch.invoke(callee, rval(r), ctx(v, trace=f"f-{i}"))
            except E.ChainError as e:
                self.assertEqual(validate(e.envelope(), schema), [], (SEED, i))
                self.assertEqual(len(ran), before, f"refused call ran handler (seed={SEED}, i={i})")
            except (ValueError, TypeError):
                self.assertEqual(len(ran), before)

    def test_P1_context_construction(self):
        r = random.Random(SEED + 1)
        v = verifier()
        for i in range(ITERS):
            try:
                ctx(v, tenant=rstr(r, 10) or "x", subject=rstr(r, 10) or "y", trace=rstr(r, 70) or "z",
                    caps=[rstr(r, 5) or "c" for _ in range(r.randint(0, 3))])
            except (E.ChainError, ValueError):
                pass

    def test_P4_wire_parsers(self):
        r = random.Random(SEED + 2)
        b, rb, pb, v = build("host-b", grants=[("acme", "svc", "invoke")])
        rb.place("svc", "acme", lambda hop, q: q, abi="hop")
        ep = ChainEndpoint(b, v)
        tok = v.issue("svc-a", "acme")
        good = {"schema": "PK_LOCAL_CHAIN/1", "callee": "svc", "payload": 1,
                "context": {"schema": "PK_CALL_CONTEXT/1", "trace_id": "t", "operation": "invoke",
                            "tenant": "acme", "subject": "svc-a", "path": []}}
        for i in range(ITERS):
            doc = json.loads(json.dumps(good))
            mode = r.randint(0, 4)
            if mode == 0:
                body = rstr(r, 200).encode("utf-8", "surrogatepass")
            elif mode == 1:
                doc["context"][r.choice(list(doc["context"]))] = rval(r); body = json.dumps(doc, default=str).encode()
            elif mode == 2:
                doc[rstr(r, 5) or "k"] = rval(r); body = json.dumps(doc, default=str).encode()
            elif mode == 3:
                body = json.dumps(rval(r), default=str).encode()
            else:
                body = json.dumps(doc).encode()
            status, out = ep.handle(body, r.choice([tok, rstr(r, 30), None]))
            resp = json.loads(out)
            self.assertEqual(validate(resp, load_schema("local_chain_response")), [], (SEED, i))
            try:
                parse_response(out)
            except E.ChainError:
                pass
        for i in range(ITERS):
            try:
                parse_response(json.dumps(rval(r), default=str).encode())
            except E.ChainError:
                pass


if __name__ == "__main__":
    unittest.main()
