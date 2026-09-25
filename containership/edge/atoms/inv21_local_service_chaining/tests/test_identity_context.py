"""GAP-005 authentication/identity, GAP-040 structured context."""
import time, unittest
from dataclasses import replace
from _support import E, CallContext, Deadline, IdentityVerifier, build, ctx, verifier, KEY
from inv21_local_service_chaining.context import Principal


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.v = verifier()

    def test_round_trip_binds_tenant_subject_caps(self):
        p = self.v.verify(self.v.issue("svc-a", "acme", ["read", "write"]))
        self.assertEqual((p.subject, p.tenant, p.capabilities), ("svc-a", "acme", frozenset({"read", "write"})))

    def test_tampered_body_refused(self):
        tok = self.v.issue("svc-a", "acme")
        h, b, s = tok.split(".")
        other = self.v.issue("svc-a", "evil").split(".")[1]
        with self.assertRaises(E.Unauthenticated):
            self.v.verify(f"{h}.{other}.{s}")

    def test_wrong_key_expired_retired_replay(self):
        other = IdentityVerifier({"k1": b"z" * 32})
        with self.assertRaises(E.Unauthenticated):
            self.v.verify(other.issue("a", "acme"))
        tok = self.v.issue("a", "acme", ttl_s=0.01); time.sleep(0.02)
        v2 = IdentityVerifier({"k1": KEY}, skew_s=0)
        with self.assertRaises(E.Unauthenticated):
            v2.verify(tok)
        rot = IdentityVerifier({"k1": KEY, "k2": b"q" * 32}, active_kid="k2")
        old = IdentityVerifier({"k1": KEY}).issue("a", "acme")
        rot.verify(old); rot.retire("k1")
        with self.assertRaises(E.Unauthenticated):
            rot.verify(old)
        once = self.v.issue("a", "acme")
        self.v.verify(once, single_use=True)
        with self.assertRaises(E.Unauthenticated):
            self.v.verify(once, single_use=True)

    def test_malformed_and_oversized_tokens(self):
        for bad in ("", "a.b", "a.b.c", "x" * 5000 + ".a.b", None, 7, "..", "e30.e30.AAAA"):
            with self.assertRaises(E.Unauthenticated):
                self.v.verify(bad)

    def test_alg_confusion_refused(self):
        import base64, json
        tok = self.v.issue("a", "acme").split(".")
        head = base64.urlsafe_b64encode(json.dumps({"alg": "none", "kid": "k1"}).encode()).decode().rstrip("=")
        with self.assertRaises(E.Unauthenticated):
            self.v.verify(f"{head}.{tok[1]}.")


class ContextTest(unittest.TestCase):
    def test_context_requires_principal_and_valid_fields(self):
        v = verifier()
        with self.assertRaises(E.Unauthenticated):
            CallContext("acme", "t-1")
        p = v.verify(v.issue("a", "acme"))
        for kw in ({"trace_id": "bad trace"}, {"trace_id": "x" * 65}, {"trace_id": "t", "operation": "a b"},
                   {"trace_id": "t", "path": ("ok", "")}, {"trace_id": "t", "schema": "PK_CALL_CONTEXT/2"},
                   {"trace_id": "t", "path": tuple(f"p{i}" for i in range(65))}):
            with self.assertRaises(E.ValidationFailed):
                CallContext(p, **kw)

    def test_tenant_comes_from_credential_not_request(self):
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        seen = []
        res.place("svc", "acme", lambda hop, req: seen.append(hop.ctx.tenant) or "ok", abi="hop")
        c = ctx(v, tenant="acme")
        self.assertEqual(ch.invoke("svc", {"tenant": "other"}, c), "ok")
        self.assertEqual(seen, ["acme"])

    def test_forged_principal_refused_in_production(self):
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        res.place("svc", "acme", lambda hop, req: "ok", abi="hop")
        forged = Principal("svc-a", "acme", frozenset(), "attacker", 0, time.time() + 60, "x")
        with self.assertRaises(E.Unauthenticated):
            ch.invoke("svc", {}, CallContext(forged, "t-1"))
        compat = replace(forged, issuer="pk-runtime", provenance="caller-asserted")
        with self.assertRaises(E.Unauthenticated):
            ch.invoke("svc", {}, CallContext(compat, "t-1"))

    def test_compat_string_api_refused_in_production(self):
        ch, res, prov, v = build()
        with self.assertRaises(E.Unauthenticated):
            ch.call("svc", "acme", {})

    def test_principal_expiry_mid_chain(self):
        v = IdentityVerifier({"k1": KEY}, skew_s=0)
        ch, res, prov, _ = build(grants=[("acme", "a", "invoke"), ("acme", "b", "invoke")])
        res.place("b", "acme", lambda hop, req: "b", abi="hop")
        res.place("a", "acme", lambda hop, req: (time.sleep(0.06), hop.call("b", req))[1], abi="hop")
        tok = v.issue("s", "acme", ttl_s=0.05)
        c = CallContext(v.verify(tok), "t-1", credential=tok)
        with self.assertRaises(E.Unauthenticated):
            ch.invoke("a", {}, c)

    def test_wire_projection_is_schema_valid_and_credential_free(self):
        from inv21_local_service_chaining.schema import load_schema, validate
        v = verifier()
        c = ctx(v, deadline=Deadline.after(1), idempotency_key="idem-1")
        w = c.to_wire()
        self.assertEqual(validate(w, load_schema("call_context")), [])
        self.assertNotIn(c.credential, str(w))


if __name__ == "__main__":
    unittest.main()
