"""MC-14 adversarial suite: one or more tests per threat in security/threats.json.
Test names carry the threat id; tests/test_repo.py checks the mapping is complete."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from helpers import World  # noqa: E402

from pln05_elasticity_plane import supplychain, wire  # noqa: E402
from pln05_elasticity_plane.errors import PlaneError  # noqa: E402
from pln05_elasticity_plane.iam import Issuer  # noqa: E402
from pln05_elasticity_plane.keys import KeyRing, TransportPolicy  # noqa: E402
from pln05_elasticity_plane.reliability import CircuitBreaker, RetryBudget, RetryPolicy  # noqa: E402
from pln05_elasticity_plane.state import FencedSink  # noqa: E402


def code(fn):
    try:
        fn()
    except PlaneError as exc:
        return exc.code
    return "OK"


class Adversarial(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.declare(floor=1, ceiling=8)

    def test_T01_forged_and_spoofed_demand(self):
        w = self.w
        other = Issuer(KeyRing.ephemeral(w.clock()))  # attacker's own key
        forged = other.mint(sub="x", actor_class="demand_reporter", tenant="t1", source="r1", now=w.clock())
        self.assertEqual(code(lambda: w.observe(0.99, token=forged)), "E_AUTHN_FAILED")
        self.assertEqual(code(lambda: w.observe(0.99, token=w.token(source="r2"))), "E_AUTHZ_SCOPE")
        self.assertEqual(code(lambda: w.plane.submit_demand(w.demand(0.99), None)), "E_AUTHN_FAILED")
        self.assertEqual(list(w.sink.applied), [])

    def test_T02_ceiling_bypass(self):
        w = self.w
        self.assertEqual(code(lambda: w.plane.submit_limits(w.limits(revision=2, ceiling=1000), w.token())), "E_AUTHZ_DENIED")
        greedy = w.issuer.mint(sub="r", actor_class="demand_reporter", tenant="t1", source="r1",
                               caps=["demand.submit", "limits.update"], now=w.clock())
        self.assertEqual(code(lambda: w.plane.submit_limits(w.limits(revision=2, ceiling=1000), greedy)), "E_AUTHORITY_ESCALATION")
        self.assertEqual(code(lambda: w.plane.submit_limits(w.limits(revision=2, ceiling=10**7), w.token("intent_plane"))), "E_SCHEMA_FIELD")
        for _ in range(10):
            d = w.observe(9.9)
        self.assertLessEqual(d["target"], 8)

    def test_T03_floor_decrease_and_ceiling_raise(self):
        w = self.w
        for c in (0, 9):
            self.assertEqual(code(lambda c=c: w.plane.lower_ceiling(w.token("power_thermal"), tenant="t1", site="dub", workload="w1", ceiling=c)), "E_AUTHORITY_ESCALATION")
        self.assertEqual(code(lambda: w.plane.lower_ceiling(w.token("operator"), tenant="t1", site="dub", workload="w1", ceiling=2)), "E_AUTHZ_DENIED")
        for _ in range(6):
            d = w.observe(0.0)
        self.assertEqual(d["target"], 1)  # never below the declared floor

    def test_T04_replay(self):
        w = self.w
        raw = w.demand(0.99, message_id="replay-000001")
        w.plane.submit_demand(raw, w.token())
        self.assertEqual(code(lambda: w.plane.submit_demand(raw, w.token())), "E_DUPLICATE")
        limits = w.limits(revision=2, ceiling=6)
        tok = w.token("intent_plane")
        w.plane.submit_limits(limits, tok)
        self.assertIn(code(lambda: w.plane.submit_limits(limits, tok)), ("E_AUTHN_REPLAY", "E_OUT_OF_ORDER"))
        self.assertEqual(code(lambda: w.plane.submit_limits(limits, w.token("intent_plane"))), "E_OUT_OF_ORDER")
        op = w.token("operator")
        w.plane.control(op, "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
        self.assertEqual(code(lambda: w.plane.control(op, "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")), "E_AUTHN_REPLAY")

    def test_T05_reorder_and_oscillation_induction(self):
        w = self.w
        w.observe(0.5, seq=100)
        self.assertEqual(code(lambda: w.observe(0.5, seq=99)), "E_OUT_OF_ORDER")
        # alternating high/low around thresholds: scale-down can never follow scale-up
        # without grace_samples consecutive lows, so direction changes are bounded
        w2 = World()
        w2.declare(floor=0, ceiling=64, grace=3)
        dirs = []
        for i in range(200):
            d = w2.observe(0.9 if i % 2 == 0 else 0.1)
            if d["outcome"] in ("scale-up", "scale-down"):
                dirs.append(d["outcome"])
        self.assertNotIn("scale-down", dirs)

    def test_T06_cross_tenant_and_site(self):
        w = self.w
        w.plane.submit_limits(w.limits(tenant="t2"), w.token("intent_plane", tenant="t2"))
        self.assertEqual(code(lambda: w.observe(0.9, tenant="t2")), "E_AUTHZ_SCOPE")
        self.assertEqual(code(lambda: w.observe(0.9, site="ams")), "E_AUTHZ_SCOPE")
        d = w.observe(0.9)
        self.assertEqual(code(lambda: w.plane.explain(w.token("operator", tenant="t2"), decision_id=d["decision_id"], tenant="t2", site="dub")), "E_AUTHZ_SCOPE")
        st = w.plane.status(w.token("operator", tenant="t2"), tenant="t2", site="dub")
        self.assertTrue(all(s["scope"].startswith("t2/") for s in st["scopes"]))

    def test_T07_parser_exhaustion(self):
        w = self.w
        tok = w.token()
        cases = [b"[" * 100000, b'{"a":' * 5000, b"9" * 20000, b'{"utilisation": 1e999}',
                 b'{"schema":"PK_DEMAND/1","seq":' + b"9" * 5000 + b"}", "\ud800".encode("utf-8", "surrogatepass"),
                 b"\x00" * 100, b'{"schema":"PK_DEMAND/1","observed_at":NaN}']
        for raw in cases:
            with self.subTest(raw[:20]):
                t0 = time.perf_counter()
                self.assertTrue(code(lambda raw=raw: w.plane.submit_demand(raw, tok)).startswith("E_SCHEMA"))
                self.assertLess(time.perf_counter() - t0, 0.5)

    def test_T08_injection_surfaces(self):
        w = self.w
        for ident in ("t1\nINFO forged", "t1;rm -rf /", "../../etc/passwd", "${jndi:ldap://x}", "T1", "t1‮"):
            self.assertEqual(code(lambda ident=ident: w.observe(0.5, tenant=ident)), "E_SCHEMA_FIELD")
        e = PlaneError("E_SCHEMA_FIELD", "x", {"field": "a\nb"})
        self.assertNotIn("\n", json.dumps(e.to_wire()["detail"]).replace("\\n", "N"))

    def test_T09_read_only_escalation(self):
        w = self.w
        ro = w.token("telemetry_collector")
        for fn in (lambda: w.plane.control(ro, "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t"),
                   lambda: w.plane.activate_config(ro, {"site": {"revision": 2}}),
                   lambda: w.plane.status(ro, tenant="t1", site="dub"),
                   lambda: w.plane.explain(ro, decision_id="x" * 32, tenant="t1", site="dub"),
                   lambda: w.plane.resume(ro, tenant="t1", site="dub", workload="w1", ticket="t")):
            self.assertEqual(code(fn), "E_AUTHZ_DENIED")

    def test_T10_expired_and_revoked(self):
        w = self.w
        tok = w.token(lifetime=10)
        w.clock.advance(11)
        self.assertEqual(code(lambda: w.observe(0.9, token=tok)), "E_AUTHN_EXPIRED")
        ring = KeyRing()
        ring.add("k1", b"k" * 32, w.clock() - 1, w.clock() + 1000)
        ww = World(ring=ring, clock=w.clock)
        ww.declare()
        t2 = ww.token()
        ring.revoke("k1")
        self.assertEqual(code(lambda: ww.observe(0.9, token=t2)), "E_AUTHN_REVOKED")

    def test_T11_transport_downgrade(self):
        pol = TransportPolicy(minimum="TLSv1.3")
        base = dict(cipher="TLS_AES_128_GCM_SHA256", peer_identity="spiffe://pk/gap09", expected_identity="spiffe://pk/gap09",
                    cert_not_after=2e9, revoked=False, now=1e9, mutual=True)
        self.assertEqual(code(lambda: pol.check_peer(protocol="TLSv1.2", **base)), "E_AUTHN_FAILED")
        self.assertEqual(code(lambda: pol.check_peer(protocol="SSLv3", **base)), "E_AUTHN_FAILED")
        self.assertEqual(code(lambda: pol.check_peer(protocol="TLSv1.3", **dict(base, peer_identity="spiffe://pk/other"))), "E_AUTHN_FAILED")
        self.assertEqual(code(lambda: pol.check_peer(protocol="TLSv1.3", **base)), "OK")

    def test_T12_tampered_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "pkg.zip"
            p.write_bytes(b"good")
            digest = supplychain.sha256_file(p)
            p.write_bytes(b"evil")
            self.assertEqual(code(lambda: supplychain.verify_artifact(p, expected_sha256=digest, name="pln05-elasticity-plane", version="4.2.0")), "E_ARTIFACT_UNTRUSTED")
            ww = World(d)
            ww.declare()
            ww.observe(0.9)
            f = next((pathlib.Path(d) / "state").glob("*.state.json"))
            doc = json.loads(f.read_bytes())
            doc["doc"]["limits"]["ceiling"] = 1000
            f.write_text(json.dumps(doc))
            w2 = World(d, ring=ww.ring, leases=ww.leases, sink=ww.sink, clock=ww.clock)
            self.assertEqual(code(lambda: w2.observe(0.9)), "E_STATE_CORRUPT")

    def test_T13_dependency_policy(self):
        pol = supplychain.approved()
        self.assertEqual(pol["runtime_third_party"], [])
        pk = [d for d in pol["dependencies"] if d["name"] == "pk_core"][0]
        self.assertTrue(pk["status"].startswith("UNRESOLVED"))
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "x"
            p.write_bytes(b"x")
            self.assertEqual(code(lambda: supplychain.verify_artifact(p, expected_sha256=supplychain.sha256_file(p), name="pk-core", version="4.0.0")), "E_ARTIFACT_UNTRUSTED")

    def test_T14_exhaustion(self):
        w = self.w
        tok = w.token()
        rejected = 0
        for i in range(2000):
            try:
                w.plane.enqueue_demand(w.demand(0.5), tok)
            except PlaneError as exc:
                self.assertEqual(exc.code, "E_OVERLOADED")
                rejected += 1
        self.assertGreater(rejected, 0)
        self.assertLessEqual(len(w.plane.admission), 1024)
        w.plane.admission.offer("control", "ctl")  # reserve still available to control traffic
        for i in range(500):
            w.plane.metrics.inc("x", {"reason_code": f"R_{i}"})
        self.assertLessEqual(w.plane.metrics.series(), 10000)

    def test_T15_retry_amplification(self):
        calls = []
        budget = RetryBudget(0.2)
        pol = RetryPolicy(4, 1, 5, 10_000, budget)
        t = [0.0]
        for _ in range(100):
            try:
                pol.run(lambda: calls.append(1) or (_ for _ in ()).throw(PlaneError("E_OVERLOADED", "x")),
                        idempotent=True, clock=lambda: t[0], sleep=lambda s: t.__setitem__(0, t[0] + s))
            except PlaneError:
                pass
        self.assertLessEqual(len(calls), 100 + 21)  # <= 20% amplification (+1 cold-start retry)
        br = CircuitBreaker("provider", 5, 10, 1)
        attempts = 0
        for _ in range(100):
            try:
                br.call(lambda: (_ for _ in ()).throw(PlaneError("E_OVERLOADED", "x")), 0.0)
            except PlaneError:
                attempts += 1
        self.assertEqual(br.state, "open")

    def test_T16_leakage(self):
        w = self.w
        w.plane.submit_limits(w.limits(tenant="secret-tenant-name"), w.token("intent_plane", tenant="secret-tenant-name"))
        w.observe(0.9, tenant="secret-tenant-name", token=w.token(tenant="secret-tenant-name"))
        self.assertNotIn("secret-tenant-name", w.plane.metrics.exposition())
        self.assertNotIn("secret-tenant-name", json.dumps(w.plane.status()))
        e = PlaneError("E_AUTHZ_SCOPE", "tenant outside credential scope")
        self.assertNotIn("secret", json.dumps(e.to_wire()))

    def test_T17_control_bypass(self):
        w = self.w
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
        w.declare(revision=2)  # intent plane cannot clear
        w.plane.activate_config(w.token("platform_operator", tenant="*"), {"site": {"revision": 2}})
        self.assertEqual(w.observe(0.99)["outcome"], "frozen")
        self.assertEqual(code(lambda: w.plane.resume(w.token("operator"), tenant="t1", site="dub", workload="w1", ticket="t")), "E_AUTHZ_DENIED")
        w.plane.resume(w.admin("a"), tenant="t1", site="dub", workload="w1", ticket="t")
        self.assertEqual(w.observe(0.99)["outcome"], "frozen")  # one admin alone cannot resume

    def test_T18_stale_controller(self):
        w = self.w
        w.observe(0.9)
        w.clock.advance(20)
        b = World(instance="ctl-b", ring=w.ring, leases=w.leases, sink=w.sink, clock=w.clock)
        b.plane.submit_limits(w.limits(floor=1, ceiling=8), w.token("intent_plane"))
        b.observe(0.9, source="r2", token=b.token(source="r2"))
        self.assertEqual(code(lambda: w.observe(0.9)), "E_NOT_LEADER")
        old = dict(w.sink.applied[0], decision_id="zombie-1")
        self.assertEqual(code(lambda: w.sink.apply(old)), "E_FENCED")

    def test_T19_security_outage_never_expands(self):
        w = self.w
        w.observe(0.5)
        before = w.plane.scopes["t1/dub/w1"].controller.current
        # audit sink down and buffer nearly full -> security-degraded: no scale-up
        w.plane.audit.set_sink(False)
        w.plane.audit.pending = [{}] * 200
        d = w.observe(0.99)
        self.assertEqual((d["outcome"], d["target"]), ("degraded", before))
        w.plane.audit.pending = [{}] * 256
        self.assertEqual(code(lambda: w.observe(0.99)), "E_AUDIT_UNAVAILABLE")
        w.plane.audit.pending = []
        w.plane.audit.set_sink(True)
        # trusted time lost: refuse to decide
        w.clock.advance(-10)
        self.assertEqual(code(lambda: w.observe(0.99, observed_at=w.clock())), "E_SECURITY_DEPENDENCY")
        self.assertFalse(w.plane.health()["ready"])

    def test_T20_scale_to_zero_suppression(self):
        w = self.w
        for _ in range(10):
            d = w.observe(0.0)
        self.assertEqual(d["target"], 1)  # floor=1 declared by intent plane: cannot be driven to zero by demand
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="protect", ticket="SEC-1")
        self.assertEqual(w.observe(0.0)["target"], 1)
        self.assertTrue(any(r["action"] == "limits.update" for r in w.plane.audit.records))


if __name__ == "__main__":
    unittest.main()
