"""MC-004 descriptors, MC-005 policy enforcement point, MC-006 identity/attestation."""
import secrets, time, unittest
import _fx
from inv13_system_interface.host.descriptors import DescriptorTable
from inv13_system_interface.host.policy import PolicyEngine
from inv13_system_interface.host.identity import IdentityGate, KeyRing
from inv13_system_interface.host.errors import ErrorCode, Inv13Error

PROV = {"decision": "d1", "actor": "cp"}


class Descriptors(unittest.TestCase):
    def setUp(self):
        self.t = DescriptorTable()
        self.root = self.t.mint(tenant="a", workload="api", capability="filesystem",
                                scope={"logical": "/data", "host_root": "/srv/a"}, rights={"read", "write"}, provenance=PROV)

    def test_stable_ids_and_provenance(self):
        self.assertTrue(self.root.id.startswith("cd-"))
        self.assertEqual(dict(self.root.provenance)["actor"], "cp")
        with self.assertRaises(Inv13Error):
            self.t.mint(tenant="a", workload="w", capability="x", scope={}, rights={"read"}, provenance={"actor": "x"})

    def test_attenuation_only(self):
        child = self.t.derive(self.root.id, scope={"logical": "/data/reports", "host_root": "/srv/a/reports"},
                              rights={"read"}, provenance=PROV)
        self.assertEqual(child.rights, {"read"})
        for kw in ({"rights": {"read", "delete"}}, {"scope": {"logical": "/data", "host_root": "/srv"}},
                   {"scope": {"logical": "/data", "host_root": "/srv/ab"}}):
            with self.assertRaises(Inv13Error) as cm:
                self.t.derive(self.root.id, provenance=PROV, **kw)
            self.assertEqual(cm.exception.code, ErrorCode.POLICY_DENIED)

    def test_cascading_revocation_and_tenant_scope(self):
        c = self.t.derive(self.root.id, rights={"read"}, provenance=PROV)
        g = self.t.derive(c.id, rights={"read"}, provenance=PROV)
        with self.assertRaises(Inv13Error):
            self.t.check(g.id, tenant="b")
        self.assertEqual(set(self.t.revoke(self.root.id)), {self.root.id, c.id, g.id})
        for d in (self.root, c, g):
            with self.assertRaises(Inv13Error) as cm:
                self.t.check(d.id)
            self.assertEqual(cm.exception.code, ErrorCode.STALE_HANDLE)
        with self.assertRaises(Inv13Error):
            self.t.derive(c.id, provenance=PROV)


class Policy(unittest.TestCase):
    def setUp(self):
        self.pe = PolicyEngine(_fx.policy_doc("/srv/tenant-a"))

    def test_allow_with_reason(self):
        d = self.pe.decide(tenant="tenant-a", workload="api-1", world="batch-file-worker",
                           capabilities={"filesystem", "stdio"}, preopens={"/data": "/srv/tenant-a/x"},
                           rights={"/data": {"read"}})
        self.assertTrue(d.allowed)
        self.assertEqual(d.rule_id, "a-files")
        self.assertEqual(len(d.policy_digest), 64)

    def test_deny_by_default_with_machine_reasons(self):
        cases = [
            (dict(tenant="nobody", workload="api", world="batch-file-worker", capabilities=set()), "unknown-tenant"),
            (dict(tenant="tenant-a", workload="api", world="net-client", capabilities={"sockets"}), "no-matching-rule"),
            (dict(tenant="tenant-a", workload="api", world="batch-file-worker", capabilities={"sockets"}),
             "capability-not-allowed:sockets"),
            (dict(tenant="tenant-a", workload="api", world="batch-file-worker", capabilities={"filesystem"},
                  preopens={"/data": "/srv/tenant-b"}), "preopen-not-allowed:/data"),
            (dict(tenant="tenant-a", workload="api", world="batch-file-worker", capabilities={"filesystem"},
                  preopens={"/data": "/srv/tenant-a"}, rights={"/data": {"delete"}}), "rights-exceed:/data"),
            (dict(tenant="tenant-b", workload="api", world="batch-file-worker", capabilities=set()), "no-matching-rule"),
        ]
        for kw, reason in cases:
            d = self.pe.decide(**kw)
            self.assertFalse(d.allowed, kw)
            self.assertIn(reason, d.reasons)

    def test_invalid_documents_rejected(self):
        doc = _fx.policy_doc("/srv/tenant-a", root_b="/srv/tenant-a/nested")   # overlapping tenant roots
        with self.assertRaises(Inv13Error):
            PolicyEngine(doc)
        doc = _fx.policy_doc("/srv/tenant-a")
        doc["tenants"]["tenant-a"]["rules"][0]["preopens"]["/data"]["host_root"] = "/etc"
        with self.assertRaises(Inv13Error):
            PolicyEngine(doc)
        with self.assertRaises(Inv13Error):
            PolicyEngine({"schema": "nope"})

    def test_engine_detached_from_caller_document(self):
        doc = _fx.policy_doc("/srv/tenant-a")
        pe = PolicyEngine(doc)
        doc["tenants"]["tenant-a"]["rules"][0]["capabilities"].append("sockets")
        self.assertFalse(pe.decide(tenant="tenant-a", workload="api", world="batch-file-worker",
                                   capabilities={"sockets"}).allowed)


class Identity(unittest.TestCase):
    def test_valid_and_bound(self):
        g = _fx.gate()
        self.assertEqual(g.verify(_fx.token(), role="runtime", workload="api")["role"], "runtime")

    def test_rejections(self):
        g = _fx.gate()
        tok = _fx.token()
        g.verify(tok, role="runtime")
        other = KeyRing({"k1": b"z" * 32}).sign("k1", {"role": "runtime", "aud": _fx.AUD, "exp": time.time() + 60,
                                                        "nonce": secrets.token_hex(12)})
        bad = [tok,                                   # replay
               _fx.token(ttl=-1), _fx.token(ttl=99999), other, "a.b", None, "x" * 9000,
               _fx.token(role="operator"),          # wrong role
               tok[:-2] + ("AA" if not tok.endswith("AA") else "BB")]
        for t in bad:
            with self.assertRaises(Inv13Error) as cm:
                g.verify(t, role="runtime")
            self.assertEqual(cm.exception.code, ErrorCode.IDENTITY_REQUIRED)
        with self.assertRaises(Inv13Error):
            g.verify(_fx.token(workload="other"), role="runtime", workload="api")
        with self.assertRaises(ValueError):
            KeyRing({"k": b"short"})

    def test_attestation_fails_closed(self):
        class V:
            def __init__(self, ok): self.ok = ok
            def verify(self, node, ev):
                if self.ok is None: raise RuntimeError("verifier down")
                return self.ok
        for att, ev in ((None, b"q"), (V(True), None), (V(False), b"q"), (V(None), b"q")):
            g = _fx.gate(attestation=att, require_attestation=True)
            with self.assertRaises(Inv13Error) as cm:
                g.verify(_fx.token(), role="runtime", attestation_evidence=ev)
            self.assertEqual(cm.exception.code, ErrorCode.ATTESTATION_FAILED)
        g = _fx.gate(attestation=V(True), require_attestation=True)
        g.verify(_fx.token(), role="runtime", attestation_evidence=b"quote")


if __name__ == "__main__":
    unittest.main()
