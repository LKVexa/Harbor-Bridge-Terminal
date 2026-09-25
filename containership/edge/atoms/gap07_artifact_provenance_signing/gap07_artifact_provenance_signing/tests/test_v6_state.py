import os
import tempfile
import threading
import unittest
from unittest import mock

from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing.core import AuditLedger
from gap07_artifact_provenance_signing.distribution import PropagationSLO, PropagationTracker, SiteTrustAgent, make_delta, make_snapshot
from gap07_artifact_provenance_signing.errors import GapError
from gap07_artifact_provenance_signing.store import FileTrustRepository, TrustState, sign_config
from gap07_artifact_provenance_signing.tests.fixtures import AUTH_PURPOSES, Env, NS, T0
from gap07_artifact_provenance_signing.timesrc import FixedClock, TimeAuthority, TimeBudget, TrustedClock
from gap07_artifact_provenance_signing.trust import Namespace


class Persistence(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.tmp = tempfile.TemporaryDirectory()
        self.audit = AuditLedger()
        self.repo = FileTrustRepository(self.tmp.name, NS, self.e.authorities, audit=self.audit)

    def tearDown(self):
        self.tmp.cleanup()

    def doc(self, gen, ns=NS):
        from gap07_artifact_provenance_signing.tests.fixtures import PKI
        t = self.e.pki.trust(generation=gen) if ns == NS else PKI(ns=ns).trust(generation=gen)
        return sign_config("trust-snapshot", t.to_dict(), kid="cfg-1", alg="ed25519", signer=self.e.auth_sign)

    def code(self, fn, *a, **kw):
        with self.assertRaises(GapError) as cm:
            fn(*a, **kw)
        return cm.exception.code

    def test_activate_load_and_rollback_protection(self):
        self.repo.activate(self.doc(1), actor="op", reason="init")
        self.repo.activate(self.doc(2), actor="op", reason="rotate")
        self.assertEqual(self.code(self.repo.activate, self.doc(1), actor="op", reason="replay"), "TRUST_ROLLBACK")
        fresh = FileTrustRepository(self.tmp.name, NS, self.e.authorities)
        self.assertEqual(fresh.load().generation, 2)
        self.assertTrue(self.audit.verify())
        self.assertIn("trust.commit", [e["event"] for e in self.audit.events])

    def test_unsigned_wrong_scope_and_unauthorised_signer(self):
        d = self.doc(1)
        d["body"]["generation"] = 5
        self.assertEqual(self.code(self.repo.stage, d, actor="op", reason="x"), "TRUST_CORRUPT")
        other = Namespace("acme", "site-b", "prod")
        self.assertIn(self.code(self.repo.stage, self.doc(1, other), actor="op", reason="x"), {"TRUST_SCOPE", "TRUST_CORRUPT"})
        rogue = algs.generate_private_key("ed25519")
        d = sign_config("trust-snapshot", self.e.pki.trust().to_dict(), kid="cfg-1", alg="ed25519", signer=algs.software_signer("ed25519", rogue))
        self.assertEqual(self.code(self.repo.stage, d, actor="op", reason="x"), "TRUST_CORRUPT")
        self.assertTrue(os.listdir(os.path.join(self.tmp.name, "quarantine")))

    def test_corruption_prevents_readiness(self):
        self.repo.activate(self.doc(1), actor="op", reason="init")
        path = os.path.join(self.tmp.name, "generations", "gen-0000000001.json")
        with open(path, "r+b") as fh:
            fh.seek(50)
            fh.write(b"#")
        self.assertEqual(self.code(FileTrustRepository(self.tmp.name, NS, self.e.authorities).load), "TRUST_CORRUPT")

    def test_crash_during_commit_keeps_prior_generation(self):
        self.repo.activate(self.doc(1), actor="op", reason="init")
        self.repo.stage(self.doc(2), actor="op", reason="next")
        real_replace = os.replace
        calls = {"n": 0}

        def crash(src, dst):
            calls["n"] += 1
            if dst.endswith("active.json"):
                raise OSError("power loss")
            return real_replace(src, dst)

        with mock.patch("os.replace", crash):
            with self.assertRaises(OSError):
                self.repo.commit(2, actor="op", reason="next")
        self.assertEqual(FileTrustRepository(self.tmp.name, NS, self.e.authorities).load().generation, 1)

    def test_disk_full_on_stage(self):
        self.repo.activate(self.doc(1), actor="op", reason="init")
        with mock.patch("os.fsync", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(OSError):
                self.repo.stage(self.doc(2), actor="op", reason="x")
        self.assertEqual(FileTrustRepository(self.tmp.name, NS, self.e.authorities).load().generation, 1)

    def test_backup_restore_and_stale_restore(self):
        self.repo.activate(self.doc(1), actor="op", reason="init")
        b = self.repo.backup("bk1")
        self.assertEqual(self.repo.verify_backup(b)["generation"], 1)
        self.repo.activate(self.doc(2), actor="op", reason="next")
        self.assertEqual(self.code(self.repo.restore, b, actor="op"), "TRUST_ROLLBACK")
        self.assertEqual(self.code(self.repo.restore, b, actor="op", recovery_approval={"approval_id": "r1", "approvers": ["a"], "reason": "x", "compromise_ruled_out": True}), "BREAK_GLASS_INVALID")
        g = self.repo.restore(b, actor="op", recovery_approval={"approval_id": "r1", "approvers": ["a", "b"], "reason": "dr drill", "compromise_ruled_out": True})
        self.assertEqual(g.generation, 1)
        with open(os.path.join(b, "floor.json"), "ab") as fh:
            fh.write(b" ")
        self.assertEqual(self.code(self.repo.verify_backup, b), "TRUST_CORRUPT")

    def test_export_is_byte_preserving(self):
        d = self.doc(1)
        self.repo.activate(d, actor="op", reason="init")
        from gap07_artifact_provenance_signing.canonical import canonical_bytes
        self.assertEqual(self.repo.export_active(), canonical_bytes(d))

    def test_concurrent_readers_see_single_generation(self):
        state = TrustState()
        state.swap(self.e.pki.trust(generation=1))
        seen, stop = set(), threading.Event()

        def reader():
            while not stop.is_set():
                g = state.current()
                seen.add((g.generation, g.digest == self.e.pki.trust(generation=g.generation).digest))

        ts = [threading.Thread(target=reader) for _ in range(4)]
        for t in ts:
            t.start()
        for gen in range(2, 30):
            state.swap(self.e.pki.trust(generation=gen))
        stop.set()
        for t in ts:
            t.join()
        self.assertTrue(all(ok for _, ok in seen))


class Distribution(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.clock = FixedClock(T0)
        self.clock.production = True  # agent treats it as a reading source only
        self.site = SiteTrustAgent(NS, self.e.authorities, self.clock)
        self.snap1 = make_snapshot(self.e.pki.trust(generation=1), expires=T0 + 3600, kid="cfg-1", alg="ed25519", signer=self.e.auth_sign)

    def delta(self, parent, ops, urgent=False, ns=NS):
        return make_delta(ns, parent, ops, issued_at=T0, expires=T0 + 3600, urgent=urgent, kid="cfg-1", alg="ed25519", signer=self.e.auth_sign)

    def code(self, doc):
        with self.assertRaises(GapError) as cm:
            self.site.offer(doc)
        return cm.exception.code

    def test_snapshot_then_delta_then_revocation(self):
        self.site.offer(self.snap1)
        ev = self.site.offer(self.delta(1, [{"op": "revoke_kid", "value": self.e.pki.refs["k1"].kid}], urgent=True))
        self.assertTrue(ev["urgent"])
        self.assertEqual(self.site.active_generation(), 2)
        with self.assertRaises(GapError) as cm:
            self.site.state.current().resolve_kid(self.e.pki.refs["k1"].kid, T0, purpose="sign:code")
        self.assertEqual(cm.exception.code, "CERT_REVOKED")

    def test_duplicate_reordered_missing_stale_scope_tamper(self):
        self.site.offer(self.snap1)
        d2 = self.delta(1, [])
        d3 = self.delta(2, [])
        self.assertEqual(self.code(d3), "TRUST_PARENT_MISMATCH")  # missing delta
        self.site.offer(d2)
        self.assertEqual(self.code(d2), "TRUST_ROLLBACK")  # duplicate
        self.assertEqual(self.code(self.snap1), "TRUST_ROLLBACK")  # stale snapshot via malicious relay
        self.assertEqual(self.code(self.delta(2, [], ns=Namespace("acme", "site-b", "prod"))), "TRUST_SCOPE")
        tampered = self.delta(2, [])
        tampered["body"]["ops"] = [{"op": "remove_signer", "value": "x"}]
        self.assertEqual(self.code(tampered), "TRUST_CORRUPT")
        self.clock.t = T0 + 7200
        self.assertEqual(self.code(self.delta(2, [])), "TRUST_STALE")

    def test_journal_replay_and_readiness(self):
        with tempfile.TemporaryDirectory() as d:
            a = SiteTrustAgent(NS, self.e.authorities, self.clock, journal_dir=d)
            a.offer(self.snap1)
            a.offer(self.delta(1, []))
            b = SiteTrustAgent(NS, self.e.authorities, self.clock, journal_dir=d)
            self.assertEqual(b.active_generation(), 2)
            self.assertEqual(b.readiness(), (True, "ok"))
            self.clock.t = T0 + 10**6
            self.assertFalse(b.readiness()[0])

    def test_reconcile_plan(self):
        self.site.offer(self.snap1)
        self.assertEqual(self.site.reconcile_plan(5, 1)["action"], "deltas")
        self.assertEqual(self.site.reconcile_plan(9, 7)["action"], "snapshot")
        self.assertEqual(self.site.reconcile_plan(1, 1)["action"], "none")

    def test_acks_and_propagation_slo(self):
        sk = algs.generate_private_key("ed25519")
        agent = SiteTrustAgent(NS, self.e.authorities, self.clock, site_signer=("site-a-k", "ed25519", algs.software_signer("ed25519", sk)))
        tracker = PropagationTracker({"site-a": ("site-a-k", "ed25519", algs.spki(sk.public_key())), "site-b": ("b", "ed25519", algs.spki(sk.public_key()))},
                                     PropagationSLO(normal_s=100, urgent_revocation_s=10))
        ev = agent.offer(self.snap1)
        tracker.published(1, T0 - 50, urgent=False, digest=ev["digest"])
        self.assertEqual(tracker.ack(agent.acknowledge(ev, "site-a")), 50)
        rep = tracker.report(T0 + 200)
        self.assertEqual(rep["generations"][0]["pending_sites"], ["site-b"])
        self.assertTrue(rep["generations"][0]["slo_breach"])
        forged = agent.acknowledge(ev, "site-a")
        forged["generation"] = 99
        with self.assertRaises(GapError):
            tracker.ack(forged)


class TrustedTime(unittest.TestCase):
    def setUp(self):
        self.k = algs.generate_private_key("ed25519")
        self.ta = TimeAuthority("ta", "ed25519", algs.software_signer("ed25519", self.k))
        self.mono = [100.0]
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "time.json")

    def tearDown(self):
        self.tmp.cleanup()

    def clock(self):
        return TrustedClock(site="s", device="d", authorities={"ta": ("ed25519", algs.spki(self.k.public_key()))}, state_path=self.path,
                            monotonic=lambda: self.mono[0], wall=lambda: 0)

    def code(self, fn, *a, **kw):
        with self.assertRaises(GapError) as cm:
            fn(*a, **kw)
        return cm.exception.code

    def test_attested_time_advances_monotonically(self):
        c = self.clock()
        self.assertEqual(self.code(c.now), "TIME_UNTRUSTED")
        c.ingest(self.ta.attest("s", "d", T0))
        self.mono[0] += 30
        r = c.now()
        self.assertEqual(r.value, T0 + 30)
        self.assertIn("attestation:ta", r.source)
        self.assertIn("wall_clock_behind", r.source)  # wall clock (0) far behind: diagnostic only

    def test_replay_rollback_jump_namespace(self):
        c = self.clock()
        a1 = self.ta.attest("s", "d", T0)
        c.ingest(a1)
        self.assertEqual(self.code(c.ingest, a1), "REPLAY")
        self.assertEqual(self.code(c.ingest, self.ta.attest("s", "d", T0 - 100)), "CLOCK_ROLLBACK")
        self.assertEqual(self.code(c.ingest, self.ta.attest("s", "d", T0 + 10**6)), "CLOCK_JUMP")
        self.assertEqual(self.code(c.ingest, self.ta.attest("other", "d", T0 + 1)), "TENANT_MISMATCH")
        forged = dict(self.ta.attest("s", "d", T0 + 5), time=T0 + 50)
        self.assertEqual(self.code(c.ingest, forged), "SIGNATURE_INVALID")

    def test_floor_survives_restart(self):
        c = self.clock()
        c.ingest(self.ta.attest("s", "d", T0))
        c2 = self.clock()  # restart; wall clock reset to epoch 0
        self.assertEqual(c2.floor, T0)
        self.assertEqual(self.code(c2.ingest, self.ta.attest("s", "d", T0 - 10)), "CLOCK_ROLLBACK")

    def test_staleness_and_uncertainty_budgets(self):
        c = self.clock()
        c.ingest(self.ta.attest("s", "d", T0))
        self.mono[0] += 100_000
        self.assertEqual(self.code(c.now, TimeBudget(max_uncertainty_s=1.0)), "TIME_UNTRUSTED")
        self.assertEqual(self.code(c.now, TimeBudget(max_uncertainty_s=100, max_offline_s=3600)), "TIME_STALE")

    def test_first_attestation_after_restart_jump_checked(self):
        c = self.clock()
        c.ingest(self.ta.attest("s", "d", T0))
        c2 = self.clock()
        self.assertEqual(self.code(c2.ingest, self.ta.attest("s", "d", T0 + 90 * 86400)), "CLOCK_JUMP")

    def test_corrupt_state_fails_closed(self):
        with open(self.path, "w") as fh:
            fh.write("{bad")
        self.assertEqual(self.code(self.clock), "TIME_UNTRUSTED")


if __name__ == "__main__":
    unittest.main()
