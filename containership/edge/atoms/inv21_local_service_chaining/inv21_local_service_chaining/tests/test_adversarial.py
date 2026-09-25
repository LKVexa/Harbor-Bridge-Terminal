"""GAP-027 threat-model-derived adversarial tests (see docs/THREAT_MODEL.md, T1..T12)."""
import json, threading, time, unittest
from dataclasses import replace
from _support import E, ChainEndpoint, LoopbackTransport, build, ctx, verifier
from inv21_local_service_chaining.context import IdentityVerifier


class AdversarialTest(unittest.TestCase):
    def setUp(self):
        self.ch, self.res, self.prov, self.v = build(grants=[("acme", "svc", "invoke"), ("acme", "a", "invoke")])
        self.ran = []
        self.res.place("svc", "acme", lambda hop, r: self.ran.append(r) or "ok", abi="hop")

    def test_T1_tenant_spoof_in_payload_or_path(self):
        self.ch.invoke("svc", {"tenant": "other", "__principal__": "root"}, ctx(self.v))
        with self.assertRaises(E.CrossTenantChain):
            self.ch.invoke("svc", {}, ctx(self.v, tenant="evil"))

    def test_T2_credential_replay_across_hosts_single_use(self):
        tok = self.v.issue("svc-a", "acme")
        self.v.verify(tok, single_use=True)
        with self.assertRaises(E.Unauthenticated):
            self.v.verify(tok, single_use=True)

    def test_T3_path_injection_cannot_reset_depth(self):
        b, rb, pb, v = build("host-b", grants=[("acme", "svc", "invoke")])
        rb.place("svc", "acme", lambda hop, r: hop.ctx.depth, abi="hop")
        ep = ChainEndpoint(b, v)
        tok = v.issue("svc-a", "acme")
        wire = {"schema": "PK_LOCAL_CHAIN/1", "callee": "svc", "payload": 0,
                "context": {"schema": "PK_CALL_CONTEXT/1", "trace_id": "t", "operation": "invoke",
                            "tenant": "acme", "subject": "svc-a", "path": ["x", "y", "z", "w"]}}
        _, out = ep.handle(json.dumps(wire).encode(), tok)
        self.assertEqual(json.loads(out)["error"]["code"], "PK_CHAIN_DEPTH_EXCEEDED")
        wire["context"]["path"] = ["svc"]
        _, out = ep.handle(json.dumps(wire).encode(), tok)
        self.assertEqual(json.loads(out)["error"]["code"], "PK_CHAIN_CYCLE")

    def test_T4_injection_strings_rejected_at_boundary(self):
        for bad in ("svc\n", "svc;rm -rf", "../../etc", "svc\x00", "<script>", "a" * 500, " svc2 "):
            with self.assertRaises((E.ValidationFailed, E.CapabilityRefused, E.TransportUnavailable, ValueError)):
                self.ch.invoke(bad, {}, ctx(self.v))
        self.assertEqual(self.ran, [])
        for bad in ("t\n1", "t 1", "x" * 100):
            with self.assertRaises(E.ValidationFailed):
                ctx(self.v, trace=bad)

    def test_T5_resource_exhaustion_bounded(self):
        # deep recursion attempt
        self.res.place("a", "acme", lambda hop, r: hop.call("a2", r), abi="hop")
        with self.assertRaises(E.ChainError):
            self.ch.invoke("a", {}, ctx(self.v))
        # oversized wire body
        b, rb, pb, v = build("host-b")
        _, out = ChainEndpoint(b, v).handle(b"x" * (2 << 20), v.issue("s", "acme"))
        self.assertEqual(json.loads(out)["error"]["code"], "PK_CHAIN_INVALID_REQUEST")
        # telemetry and audit memory bounded
        for i in range(3000):
            self.ch.invoke("svc", i, ctx(self.v))
        self.assertLessEqual(len(self.ch.decisions), 1024)
        self.assertLessEqual(len(self.ch.audit.records()), 4096)

    def test_T6_provider_compromise_returns_garbage(self):
        class Evil:
            authoritative = True
            def decide(self, r):
                return type("D", (), {"allow": 1, "schema": "PK_CAPABILITY/1"})()
        ch, res, _, v = build(provider=Evil())
        res.place("svc", "acme", lambda hop, r: "RAN", abi="hop")
        with self.assertRaises(E.ProviderUnavailable):
            ch.invoke("svc", {}, ctx(v))

    def test_T7_malicious_remote_peer_response(self):
        class Evil:
            def __init__(self, body): self.body = body
            def handle(self, body, cred): return 200, self.body
        v = verifier()
        for body, code in ((b"not json", "PK_CHAIN_REMOTE_PROTOCOL"),
                           (json.dumps({"schema": "PK_LOCAL_CHAIN/1", "ok": True, "route": "local", "extra": 1}).encode(),
                            "PK_CHAIN_REMOTE_PROTOCOL"),
                           (json.dumps({"schema": "PK_LOCAL_CHAIN/1", "ok": False, "route": "refused",
                                        "error": {"schema": "PK_CHAIN_ERROR/1", "code": "PK_CHAIN_ROOT",
                                                  "category": "internal", "retriable": False, "origin": "chain",
                                                  "message": "x"}}).encode(), "PK_CHAIN_REMOTE_PROTOCOL"),
                           (b"[" * 100000, "PK_CHAIN_REMOTE_PROTOCOL")):
            a, _, _, _ = build(grants=[("acme", "far", "invoke")], transport=LoopbackTransport(Evil(body)))
            with self.assertRaises(E.ChainError) as cm:
                a.invoke("far", {}, ctx(v))
            self.assertEqual(cm.exception.code, code)

    def test_T8_error_side_channel_does_not_reveal_foreign_placement_details(self):
        self.res.place("secret", "other", lambda hop, r: 1, abi="hop")
        with self.assertRaises(E.CrossTenantChain) as cm:
            self.ch.invoke("secret", {}, ctx(self.v))
        env = json.dumps(cm.exception.envelope())
        self.assertNotIn("handler", env.lower().replace("handler_failed", ""))

    def test_T9_stale_writer_cannot_hijack_placement(self):
        self.res.place("svc", "acme", lambda hop, r: "v2", abi="hop", epoch=5)
        with self.assertRaises(E.ResidencyStale):
            self.res.place("svc", "acme", lambda hop, r: "hijack", abi="hop", epoch=4)

    def test_T10_production_rejects_compat_and_unsigned_paths(self):
        with self.assertRaises(E.Unauthenticated):
            self.ch.call("svc", "acme", {})
        other_issuer = IdentityVerifier({"k1": b"k" * 32}, issuer="rogue")
        rogue = other_issuer.verify(other_issuer.issue("svc-a", "acme"))
        from inv21_local_service_chaining.context import CallContext
        with self.assertRaises(E.Unauthenticated):
            self.ch.invoke("svc", {}, CallContext(rogue, "t-1"))

    def test_T11_timing_uses_constant_time_compare(self):
        import inspect
        from inv21_local_service_chaining import context, audit
        self.assertIn("compare_digest", inspect.getsource(context.IdentityVerifier.verify))
        self.assertIn("compare_digest", inspect.getsource(audit.verify))

    def test_T12_audit_tamper_detected(self):
        from inv21_local_service_chaining.audit import verify
        self.ch.invoke("svc", {}, ctx(self.v))
        recs = [dict(r) for r in self.ch.audit.records()]
        recs[-1]["route"] = "local-but-edited"
        self.assertFalse(verify(recs, b"a" * 32)["ok"])


if __name__ == "__main__":
    unittest.main()
