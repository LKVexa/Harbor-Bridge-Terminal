"""MC-10/11/12/17/19/20/21/22/23/24/26/30 operational module tests."""
import random
import unittest

import _kit as k

from gap06_device_identity_and_attestation.mc import authz, clock, errors, ops, ratelimit, schemas
from gap06_device_identity_and_attestation.mc.errors import Gap06Error


def code(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except Gap06Error as e:
        return e.code
    return "NO_ERROR"


class ClockTest(unittest.TestCase):
    def test_unsynced_skew_stale_monotone(self):
        m = clock.FakeMonotonic()
        c = clock.TrustedClock(monotonic=m, skew_budget=1.0, max_unsynced=100)
        self.assertEqual(code(c.now), "E_TIME_UNTRUSTED")
        c.sync(1000.0)
        m.advance(10)
        self.assertEqual(c.now(), 1010.0)
        c.sync(1010.5)  # within budget
        m.advance(200)
        self.assertEqual(code(c.now), "E_TIME_UNTRUSTED")
        self.assertEqual(code(c.sync, 5000.0), "E_TIME_UNTRUSTED")
        self.assertEqual(code(c.now), "E_TIME_UNTRUSTED")  # poisoned
        c.reset_after_review()
        c.sync(2000.0)
        a = c.now()
        self.assertGreaterEqual(c.now(), a)


class AdmissionTest(unittest.TestCase):
    def test_per_principal_global_and_bounded(self):
        a = ratelimit.Admission(rate=1, burst=2, global_rate=0.001, global_burst=5, max_principals=3)
        a.admit("p", 0); a.admit("p", 0)
        self.assertEqual(code(a.admit, "p", 0), "E_RATE_LIMITED")
        a.admit("p", 1.0)
        a.admit("q", 1.0); a.admit("q", 1.0)
        self.assertEqual(code(a.admit, "r", 1.0), "E_OVERLOADED")
        for i in range(100):
            try:
                a.admit(f"h{i}", 10 + i)
            except Gap06Error:
                pass
        self.assertLessEqual(len(a._b), 3)

    def test_fairness(self):
        a = ratelimit.Admission(rate=10, burst=10, global_rate=1e6, global_burst=1e6)
        ok = {"noisy": 0, "quiet": 0}
        for i in range(1000):
            t = i / 100
            for p in ("noisy",) * 9 + ("quiet",):
                try:
                    a.admit(p, t); ok[p] += 1
                except Gap06Error:
                    pass
        self.assertGreater(ok["quiet"], 90)  # the quiet principal is not starved


class ErrorsSchemasTest(unittest.TestCase):
    def test_registry_and_redaction(self):
        e = errors.fail("E_REPLAY", "nonce " + "ab" * 32 + " -----BEGIN PRIVATE KEY-----x-----END PRIVATE KEY-----")
        d = e.to_dict()
        self.assertEqual((d["category"], d["http_status"], d["retryable"]), ("freshness", 409, False))
        self.assertNotIn("ab" * 32, d["safe_detail"])
        self.assertNotIn("BEGIN PRIVATE", d["safe_detail"])
        with self.assertRaises(ValueError):
            errors.Gap06Error("E_NOPE")

    def test_schemas(self):
        base = {"schema": "PK_ATTESTATION/1", "node": "n", "nonce": "ab", "attest": "00", "signature": "00",
                "pcrs": {"0": "00" * 32}, "idempotency_key": "k"}
        schemas.validate(base)
        for bad in [dict(base, extra=1), dict(base, schema="PK_ATTESTATION/2"), dict(base, nonce="AB"),
                    dict(base, pcrs={"24": "00" * 32}), {k_: v for k_, v in base.items() if k_ != "node"},
                    dict(base, node=1), "{not json", b"[]"]:
            self.assertEqual(code(schemas.validate, bad), "E_SCHEMA", bad)
        js = schemas.json_schema("PK_NODE_IDENTITY/1")
        self.assertFalse(js["additionalProperties"])

    def test_schema_fuzz_never_crashes(self):
        rng = random.Random(7)
        alphabet = '{}[]":,0123456789abcdefPK_ATESION/ \\'
        for _ in range(3000):
            s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
            try:
                schemas.validate(s)
            except Gap06Error as e:
                self.assertEqual(e.code, "E_SCHEMA")


class IsolationTest(unittest.TestCase):
    def test_scopes(self):
        z = authz.Authorizer("prod")
        p = authz.Principal("t1-reader", frozenset({"read"}), frozenset({"prod"}), sites=frozenset({"s1"}), tenants=frozenset({"t1"}))
        z.require(p, "read", site="s1", tenant="t1")
        self.assertEqual(code(z.require, p, "read", site="s2"), "E_TENANT_BOUNDARY")
        self.assertEqual(code(z.require, p, "read", tenant="t2"), "E_TENANT_BOUNDARY")
        self.assertEqual(code(authz.Authorizer("dev").require, p, "read"), "E_TENANT_BOUNDARY")
        self.assertEqual(code(z.require, p, "enroll"), "E_FORBIDDEN")
        self.assertEqual(code(z.require, None, "read"), "E_UNAUTHENTICATED")
        n = k.node_principal("n1")
        self.assertEqual(code(z.require, n, "attest", node="n2"), "E_FORBIDDEN")
        self.assertEqual(len(z.denials), 4)  # dev-authorizer and unauthenticated denials are not recorded on z


class OpsTest(unittest.TestCase):
    def test_quarantine_outbox_acks(self):
        w = k.World()
        flaky = {"n": 0}

        def sink(cmd):
            flaky["n"] += 1
            if flaky["n"] == 1:
                raise ConnectionError
            return True
        q = ops.QuarantineEnforcer(w.store, {"gap01": sink, "sch01": lambda c: True})
        q.quarantine("n1", "drift", 0)
        self.assertFalse(q.enforced("n1"))
        q.deliver("n1")
        self.assertTrue(q.enforced("n1"))
        self.assertEqual(code(q.release, "n1", fresh_verdict_ok=False, authorizer=w.authz, principal=k.operator()), "E_FORBIDDEN")
        self.assertEqual(code(q.release, "n1", fresh_verdict_ok=True, authorizer=w.authz, principal=k.node_principal("n1")), "E_FORBIDDEN")
        q.release("n1", fresh_verdict_ok=True, authorizer=w.authz, principal=k.operator())
        self.assertFalse(q.is_quarantined("n1"))

    def test_scheduler(self):
        s = ops.ReattestScheduler(ttl=100)
        dues = [s.next_due(0) for _ in range(500)]
        self.assertTrue(all(55 <= d < 95.0001 for d in dues))
        self.assertGreater(max(dues) - min(dues), 10)  # jitter spreads the herd
        self.assertLessEqual(s.backoff(20), 60)
        self.assertEqual(s.level(100, 100, "hardware"), "untrusted")

    def test_offline(self):
        o = ops.OfflineMode(max_offline_age=100)
        self.assertEqual(o.decide("n", "hardware", 0), "untrusted")
        o.cache(3, 0)
        self.assertEqual(o.decide("n", "hardware", 50), "software")
        self.assertEqual(o.decide("n", "software", 101), "untrusted")
        self.assertEqual(len(o.reconcile(4)), 1)

    def test_health(self):
        h = ops.Health({"store": lambda: (True, "ok"), "time": lambda: (True, ""), "metrics": lambda: 1 / 0},
                       critical={"store", "time"})
        r = h.report()
        self.assertEqual(r["status"], "degraded")
        h.checks["time"] = lambda: (False, "no sync")
        self.assertEqual(h.report()["status"], "unready")

    def test_telemetry(self):
        t = ops.Telemetry(max_series=3)
        with self.assertRaises(ValueError):
            t.inc("x", node="n1")  # node id label forbidden (cardinality)
        for c in "abcdef":
            t.inc("attest", code=c)
        self.assertEqual(len(t.counters), 3)
        self.assertEqual(t.dropped_series, 3)
        rec = t.log("reject", nonce="cd" * 32)
        self.assertNotIn("cd" * 32, str(rec))
        self.assertIn('attest{code="a"} 1', t.exposition())
        tp = ops.trace_context()
        self.assertEqual(ops.trace_context(tp).split("-")[1], tp.split("-")[1])

    def test_shards(self):
        r = ops.ShardRing(["s1", "s2", "s3", "s4"])
        counts = {}
        for i in range(8000):
            s = r.shard_for(f"node-{i}")
            counts[s] = counts.get(s, 0) + 1
        self.assertTrue(all(1400 < c < 2600 for c in counts.values()), counts)
        r2 = ops.ShardRing(["s1", "s2", "s3", "s4", "s5"])
        moved = sum(r.shard_for(f"node-{i}") != r2.shard_for(f"node-{i}") for i in range(8000))
        self.assertLess(moved, 8000 * 0.35)

    def test_config(self):
        c = ops.load_config({"challenge_ttl_s": 60}, signature_ok=True)
        self.assertEqual(c["challenge_ttl_s"], 60.0)
        self.assertEqual(code(ops.load_config, {}, signature_ok=False), "E_POLICY_UNSIGNED")
        self.assertEqual(code(ops.load_config, {"challenge_ttl_s": 1}, signature_ok=True), "E_SCHEMA")
        self.assertEqual(code(ops.load_config, {"bogus": 1}, signature_ok=True), "E_SCHEMA")
        self.assertEqual(code(ops.load_config, {"require_revocation_info": 1}, signature_ok=True), "E_SCHEMA")


if __name__ == "__main__":
    unittest.main()
