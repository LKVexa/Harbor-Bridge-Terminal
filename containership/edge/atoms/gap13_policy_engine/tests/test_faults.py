"""G13-MC-034 fault injection: outages, corrupt cache, partial writes, restart, clock anomalies."""
import pathlib
import unittest

import testkit as k
from gap13_policy_engine import errors as E
from gap13_policy_engine.attributes import StaticContextProvider


class FaultTests(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(k.tmpdir())
        self.svc, self.c = k.service(self.dir, require_separation_of_duties=False)
        self.admin = k.principal("alice", clock=self.c)
        self.app = k.principal("svc-a", ("service",), kind="service", clock=self.c)
        self.svc.load(self.admin, k.envelope(1))

    def test_verifier_outage_keeps_current_policy(self):
        class Down:
            def trust_store(self):
                raise TimeoutError()
        self.svc.verifier.trust = Down()
        with self.assertRaises(E.DependencyUnavailable):
            self.svc.load(self.admin, k.envelope(2))
        self.assertEqual(self.svc.status()["active"]["generation"], 1)
        self.assertEqual(self.svc.status()["dependencies"]["verifier"], "unavailable")
        self.assertEqual(self.svc.evaluate(self.app, {"action": "read"})["effect"], "allow")

    def test_context_outage_fails_closed(self):
        self.svc.context = StaticContextProvider({}, available=False)
        with self.assertRaises(E.ContextUnavailable):
            self.svc.evaluate(self.app, {"action": "read"})

    def test_corrupt_cache_on_restart(self):
        (self.dir / "cache.json").write_text('{"kind":"PK_POLICY_CACHE/1","body":{"entries":[]},"sha256":"00"}')
        svc2, _ = k.service(self.dir, clock=self.c)
        self.assertFalse(svc2.restore_from_cache())
        with self.assertRaises(E.NoActivePolicy):
            svc2.evaluate(self.app, {"action": "read"})

    def test_truncated_cache_file(self):
        p = self.dir / "cache.json"
        p.write_bytes(p.read_bytes()[:40])
        svc2, _ = k.service(self.dir, clock=self.c)
        self.assertFalse(svc2.restore_from_cache())

    def test_restart_restores_lkg_and_reverifies(self):
        svc2, _ = k.service(self.dir, clock=self.c)
        self.assertTrue(svc2.restore_from_cache())
        self.assertEqual(svc2.evaluate(self.app, {"action": "read"})["effect"], "allow")
        # key revoked while down -> cached bundle no longer trusted
        svc3, _ = k.service(self.dir, clock=self.c, verifier=k.verifier(store=k.trust_store(revoked=True)))
        self.assertFalse(svc3.restore_from_cache())

    def test_restore_from_old_cache_cannot_downgrade(self):
        import shutil
        shutil.copy(self.dir / "cache.json", self.dir / "cache.gen1")
        self.svc.load(self.admin, k.envelope(2))
        shutil.copy(self.dir / "cache.gen1", self.dir / "cache.json")      # attacker restores old cache
        svc2, _ = k.service(self.dir, clock=self.c)
        self.assertTrue(svc2.restore_from_cache())                          # LKG rollback path...
        # ...but the durable floor still refuses gen-1 as a *new* activation
        with self.assertRaises(E.ReplayRejected):
            svc2.stage(self.admin, k.envelope(1))

    def test_partial_cache_write_leaves_previous_file(self):
        before = (self.dir / "cache.json").read_bytes()
        with self.assertRaises(OSError):
            self.svc.cache.record_activation(b"x", {"digest": "d", "generation": 9, "bundle_id": "b",
                                                    "activated_at_ms": 1}, fault="partial")
        self.assertEqual((self.dir / "cache.json").read_bytes(), before)
        self.assertEqual(list(p.name for p in self.dir.glob(".cache.json.*")), [])

    def test_clock_rollback_across_restart(self):
        self.c.t -= 200
        svc2, _ = k.service(self.dir, clock=self.c)
        svc2.restore_from_cache()
        self.assertGreater(svc2.clock_anomalies, 0)
        with self.assertRaises(E.StalePolicyRefused):
            svc2.evaluate(self.app, {"action": "read"})

    def test_audit_sink_outage_blocks_privileged_ops_when_buffer_full(self):
        self.svc.audit.sink_down = True
        self.svc.audit.buffer_limit = 0
        with self.assertRaises(E.AuditSinkUnavailable):
            self.svc.load(self.admin, k.envelope(2))
        self.assertIn("audit sink down (buffering)", self.svc.health()["not_ready_reasons"])

    def test_stale_controller_network_partition(self):
        from gap13_policy_engine.distribution import DistributionController

        class Partitioned:
            def fetch(self, *, timeout):
                raise E.DependencyUnavailable("partition")
        dc = DistributionController(self.svc, Partitioned(), self.admin)
        for _ in range(5):
            self.assertEqual(dc.poll_once(), "fetch-error")
        self.assertEqual(dc.failures, 5)
        self.c.advance(301)
        with self.assertRaises(E.StalePolicyRefused):
            self.svc.evaluate(self.app, {"action": "read"})


class LargeClockRollbackTests(unittest.TestCase):
    def test_large_rollback_before_issue_time_refuses_restore(self):
        d = pathlib.Path(k.tmpdir())
        svc, c = k.service(d, require_separation_of_duties=False)
        svc.load(k.principal("alice", clock=c), k.envelope(1))
        c.t -= 5000
        svc2, _ = k.service(d, clock=c)
        self.assertFalse(svc2.restore_from_cache())      # bundle now appears issued in the future
        with self.assertRaises(E.NoActivePolicy):
            svc2.evaluate(k.principal("svc-a", ("service",), kind="service", clock=c), {"action": "read"})


if __name__ == "__main__":
    unittest.main()
