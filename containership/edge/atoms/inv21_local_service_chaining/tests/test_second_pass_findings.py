"""Regression tests for the independent second-pass audit findings (AUDIT_REPORT_4.3.0.md, SP-01..SP-10).
Each test reproduces the auditor's probe and asserts the corrected behaviour."""
import asyncio, threading, time, unittest
from dataclasses import replace
from _support import (AUDIT_KEY, E, AuditLog, ChainEndpoint, Chainer, GuardedProvider, Residency,
                      StaticPolicyProvider, build, ctx, prod_config, verifier)
from inv21_local_service_chaining.context import CallContext, Principal
from inv21_local_service_chaining.policy import CapabilityDecision
from inv21_local_service_chaining.schema import validate, check_keywords


class SecondPassFindings(unittest.TestCase):
    def test_SP01_hand_built_principal_refused_in_production(self):
        ch, res, prov, v = build(grants=[("globex", "secret", "invoke")])
        ran = []
        res.place("secret", "globex", lambda hop, r: ran.append(1) or "GLOBEX-DATA", abi="hop")
        forged = Principal("mallory", "globex", frozenset(), "pk-runtime", 0.0, time.time() + 999, "x")
        with self.assertRaises(E.Unauthenticated):
            ch.invoke("secret", "hi", CallContext(forged, "t-1"))
        real = ctx(v, tenant="acme")  # real credential, principal swapped for another tenant
        with self.assertRaises(E.Unauthenticated):
            ch.invoke("secret", "hi", replace(real, principal=replace(real.principal, tenant="globex")))
        self.assertEqual(ran, [])

    def test_SP02_caller_supplied_path_does_not_set_policy_caller(self):
        class ByCaller:
            authoritative = True
            def decide(self, r):
                return CapabilityDecision(r.caller == "billing", 1, "c", r.correlation_id)
        ch, res, _, v = build(provider=ByCaller())
        res.place("ledger", "acme", lambda hop, r: "LEDGER", abi="hop")
        res.place("billing", "acme", lambda hop, r: hop.call("ledger", r), abi="hop")
        with self.assertRaises(E.CapabilityRefused):
            ch.invoke("ledger", 1, ctx(v, path=("billing",)))
        # the genuine hop (billing -> ledger) still carries the caller; billing itself has no caller -> refused
        with self.assertRaises(E.CapabilityRefused):
            ch.invoke("billing", 1, ctx(v))

    def test_SP02b_genuine_nested_hop_carries_caller(self):
        seen = []
        class Rec:
            authoritative = True
            def decide(self, r):
                seen.append((r.callee, r.caller)); return CapabilityDecision(True, 1, "c", r.correlation_id)
        ch, res, _, v = build(provider=Rec())
        res.place("b", "acme", lambda hop, r: 1, abi="hop")
        res.place("a", "acme", lambda hop, r: hop.call("b", r), abi="hop")
        ch.invoke("a", 0, ctx(v, path=("spoof",)))
        self.assertEqual(seen, [("a", None), ("b", "a")])

    def test_SP03_fake_path_cannot_bypass_admission(self):
        ch, res, prov, v = build(grants=[("acme", "slow", "invoke"), ("acme", "x", "invoke")],
                                 cfg=prod_config(max_in_flight=1, max_in_flight_per_tenant=1))
        gate = threading.Event(); started = threading.Event()
        res.place("slow", "acme", lambda hop, r: (started.set(), gate.wait(2))[1], abi="hop")
        res.place("x", "acme", lambda hop, r: "inner", abi="hop")
        t = threading.Thread(target=lambda: ch.invoke("slow", 0, ctx(v))); t.start(); started.wait(2)
        try:
            with self.assertRaises(E.Overloaded):
                ch.invoke("x", 0, ctx(v, path=("zz",)))
        finally:
            gate.set(); t.join()
        self.assertEqual(ch.admission.snapshot()["in_flight"], 0)

    def test_SP04_apply_config_enforces_production_wiring(self):
        dev = Chainer(Residency("h"), capability_checker=lambda *a: True)
        with self.assertRaises(E.ValidationFailed):
            dev.apply_config(prod_config())
        self.assertFalse(dev.production)
        ch, res, prov, v = build(cfg=prod_config(mode="development"))
        ch.apply_config(prod_config(max_in_flight=7, max_in_flight_per_tenant=7))
        self.assertTrue(ch.production); self.assertEqual(ch.admission.max_in_flight, 7)

    def test_SP05_granted_decisions_are_audited(self):
        ch, res, prov, v = build(grants=[("acme", "s", "invoke")])
        res.place("s", "acme", lambda hop, r: "ok", abi="hop")
        ch.invoke("s", 0, ctx(v))
        kinds = [(r["kind"], r.get("route")) for r in ch.audit.records()]
        self.assertIn(("decision", "local"), kinds)

    def test_SP06_revocation_visible_through_cache(self):
        ch, res, prov, v = build(grants=[("acme", "s", "invoke")], cfg=prod_config(policy_cache_ttl_s=60))
        ch.policy.cache_ttl_s = 60
        res.place("s", "acme", lambda hop, r: "ok", abi="hop")
        self.assertEqual(ch.invoke("s", 0, ctx(v)), "ok")
        prov.revoke("acme", "s")
        with self.assertRaises(E.CapabilityRefused):
            ch.invoke("s", 0, ctx(v))

    def test_SP07_restored_placements_honour_leases(self):
        res = Residency("h", default_lease_s=0.05); h = lambda *a: 1
        res.place("a", "t", h, epoch=1)
        fresh = Residency("h", default_lease_s=0.05)
        fresh.restore(res.snapshot(), {"a": h}); fresh.reconcile([{"callee": "a", "tenant": "t", "epoch": 1}])
        self.assertIsNotNone(fresh.resolve("a"))
        time.sleep(0.07)
        self.assertIsNone(fresh.resolve("a"))

    def test_SP08_audit_window_and_empty(self):
        from inv21_local_service_chaining.audit import verify
        log = AuditLog(AUDIT_KEY, memory_max=4)
        for i in range(10):
            log.append("x", n=i)
        anchor, recs = log.window()
        self.assertTrue(verify(recs, AUDIT_KEY, anchor=anchor, expected_head=log.head())["ok"])
        self.assertFalse(verify(recs, AUDIT_KEY)["ok"])  # a window is not a full log
        self.assertEqual(verify([], AUDIT_KEY)["why"], "empty")
        recs[1] = dict(recs[1], n=99)
        self.assertFalse(verify(recs, AUDIT_KEY, anchor=anchor)["ok"])

    def test_SP09_schema_validator_soundness(self):
        self.assertTrue(validate({}, {"anyOf": [{"type": "object"}], "required": ["a"]}))
        self.assertTrue(validate({"z": 1}, {"type": "object", "additionalProperties": {"type": "string"}}))
        self.assertTrue(validate(True, {"enum": [1]}))
        self.assertTrue(validate(1, {"const": True}))
        with self.assertRaises(ValueError):
            check_keywords({"type": "object", "properties": {"a": {"format": "email"}}})
        with self.assertRaises(ValueError):  # follow-up audit: validate() itself must refuse
            validate({}, {"type": "object", "properties": {"a": {"bogus": 1}}})

    def test_SP10_peer_bounds_bearer_token_age(self):
        b, rb, pb, v = build("host-b", grants=[("acme", "s", "invoke")])
        rb.place("s", "acme", lambda hop, r: "ok", abi="hop")
        ep = ChainEndpoint(b, v, max_token_age_s=0.01)
        import json
        tok = v.issue("svc-a", "acme")
        wire = {"schema": "PK_LOCAL_CHAIN/1", "callee": "s", "payload": 0,
                "context": {"schema": "PK_CALL_CONTEXT/1", "trace_id": "t", "operation": "invoke",
                            "tenant": "acme", "subject": "svc-a", "path": []}}
        time.sleep(0.03)
        _, out = ep.handle(json.dumps(wire).encode(), tok)
        self.assertEqual(json.loads(out)["error"]["code"], "PK_CHAIN_UNAUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
