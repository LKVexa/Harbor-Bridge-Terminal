"""C32 partition/reconnect fault injection, C33 concurrency/race, C34 property/fuzz,
C35 security/adversarial. Seeds are fixed for reproducibility; set GAP04_SEED /
GAP04_FUZZ_ITERS to widen a qualification run."""
import os, random, threading, unittest
from _util import T, Tmp, node, code, Gap04Error
from gap04_disconnected_operation_controller.runtime import canonical, crypto, trust as TR
from gap04_disconnected_operation_controller.runtime.adapters import ReferenceReplication, ReferenceSupervisor
from gap04_disconnected_operation_controller.runtime.errors import AdapterError, REGISTRY
from gap04_disconnected_operation_controller.controller import AutonomyController, ControllerError, PERMITTED, TIERS

SEED = int(os.environ.get("GAP04_SEED", "1337"))
ITERS = int(os.environ.get("GAP04_FUZZ_ITERS", "300"))


class FaultInjection(unittest.TestCase):
    def test_T_C32_flapping_link_never_renews_or_leaks_authority(self):
        rnd = random.Random(SEED)
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m)
            accepted = 0
            for step in range(400):
                m.t += rnd.choice([1, 1, 2, 30])
                hb = cp.heartbeat(n.adapters.reachability, n.clock.now()) if rnd.random() < 0.5 else None
                st = n.observe_reachability(hb, latency_ms=rnd.choice([10, 10, 5000]))
                if n.controller.partitioned_since is not None and rnd.random() < 0.5:
                    try:
                        n.decide("restart", f"ns/{step}", f"req-{step:08d}"); accepted += 1
                    except Gap04Error as e:
                        self.assertIn(e.code, REGISTRY)
                if n.adapters.reachability.reachable and n.controller.partitioned_since is not None and rnd.random() < 0.3:
                    try:
                        n.reconnect()
                    except Gap04Error as e:
                        self.assertIn(e.code, ("GAP04-E0600",))
                if st == "flapping":
                    self.assertFalse(n.adapters.reachability.reachable)
            self.assertGreater(accepted, 0)
            n.close()

    def test_T_C32_asymmetric_partition_heartbeats_ok_replication_down(self):
        with Tmp() as d:
            rep = ReferenceReplication(fail_times=10**6)
            n, cp, m = node(d, replication=rep)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            n.decide("restart", "ns/a", "req-00000001")
            T.come_back(n, cp, m)
            code(self, "GAP04-E0600", n.reconnect)
            self.assertTrue(n.health()["reconciliation"]["in_progress"])
            code(self, "GAP04-E0002", n.install_policy, cp.policy())  # still can't bypass reconciliation
            n.close()

    def test_T_C32_reordered_and_duplicated_batches(self):
        with Tmp() as d:
            from gap04_disconnected_operation_controller.runtime.config import default_config
            cfg = default_config(); cfg["reconcile"]["batch_size"] = 3
            class Dup(ReferenceReplication):
                def submit(s, b):
                    r1 = super().submit(b); r2 = super().submit(b)   # network duplicates delivery
                    assert r1 == r2
                    return r2
            rep = Dup()
            n, cp, m = node(d, config=cfg, replication=rep)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            for i in range(10):
                n.decide("restart", f"ns/{i}", f"req-{i:08d}")
            T.come_back(n, cp, m)
            r = n.reconnect()
            self.assertEqual(r["decision_count"], 10); self.assertEqual(len(rep.applied), 10)
            n.close()

    def test_T_C32_delayed_revocation_applied_after_reconnect(self):
        with Tmp() as d:
            n, cp, m = node(d)
            pol, lease = T.bring_up(n, cp, m); T.go_dark(n, m)
            n.decide("restart", "ns/a", "req-00000001")
            m.t += 3600
            T.come_back(n, cp, m)
            code(self, "GAP04-E0002", n.apply_revocations, 2, revoked_lease_ids=[lease["lease_id"]])
            n.reconnect()
            n.apply_revocations(2, revoked_lease_ids=[lease["lease_id"]])
            self.assertFalse(n.health()["ready"])
            n.close()

    def test_T_C32_long_partition_to_expiry(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m, ttl=7200 + 600); T.go_dark(n, m)
            tiers = []
            for _ in range(20):
                m.t += 450; tiers.append(n.health()["tier"])
            self.assertEqual(tiers[-1], "expired")
            self.assertEqual(tiers, sorted(tiers, key=TIERS.index))
            code(self, "GAP04-E0100", n.decide, "restart", "ns/a", "req-00000001")
            n.close()


class LatencyRegression(unittest.TestCase):
    def test_T_C38_decide_latency_does_not_grow_with_log(self):
        """Regression guard for the O(n) deep-copy found by the 4.3.0 benchmark."""
        import time
        with Tmp() as d:
            from gap04_disconnected_operation_controller.runtime.config import default_config
            cfg = default_config(); cfg["journal"]["max_bytes"] = 1 << 28
            n, cp, m = node(d, config=cfg); T.bring_up(n, cp, m); T.go_dark(n, m)
            lat = []
            for i in range(1500):
                t = time.perf_counter(); n.decide("restart", f"ns/{i}", f"req-{i:08d}"); lat.append(time.perf_counter() - t)
            head, tail = sorted(lat[:300])[150], sorted(lat[-300:])[150]
            self.assertLess(tail / head, 3.0, (head, tail))
            n.close()


class Concurrency(unittest.TestCase):
    def test_T_C33_parallel_decisions_unique_and_durable(self):
        with Tmp() as d:
            from gap04_disconnected_operation_controller.runtime.config import default_config
            cfg = default_config(); cfg["admission"]["max_concurrency"] = 64; cfg["admission"]["max_queue"] = 4096
            n, cp, m = node(d, config=cfg)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            errs = []
            def w(k):
                for i in range(25):
                    rid = f"req-{(i % 20):04d}-{k % 4:04d}"   # deliberate duplicate request ids across threads
                    try:
                        n.decide("restart", f"ns/{rid}", rid)
                    except Gap04Error as e:
                        errs.append(e.code)
            ts = [threading.Thread(target=w, args=(k,)) for k in range(16)]
            [t.start() for t in ts]; [t.join() for t in ts]
            ids = [x["decision_id"] for x in n.controller.decisions]
            self.assertEqual(len(ids), len(set(ids))); self.assertEqual(len(ids), 80)
            self.assertEqual(len(n.adapters.supervisor.executed), 80)
            self.assertEqual(errs, [])
            n.close()
            n2, _, _ = node(d, cp=cp, mono=m, config=cfg)
            self.assertEqual(sorted(x["decision_id"] for x in n2.controller.decisions), sorted(ids))
            n2.close()

    def test_T_C33_decide_vs_reconnect_race(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            for i in range(20):
                n.decide("restart", f"ns/{i}", f"req-{i:08d}")
            T.come_back(n, cp, m)
            out = {"rec": None, "late": []}
            def rec():
                out["rec"] = n.reconnect()
            def late():
                for i in range(20, 60):
                    try:
                        n.decide("restart", f"ns/{i}", f"req-{i:08d}"); out["late"].append(i)
                    except Gap04Error:
                        pass
            a, b = threading.Thread(target=rec), threading.Thread(target=late)
            a.start(); b.start(); a.join(); b.join()
            # every decision either made it into the record or was refused; none silently dropped
            self.assertEqual(out["rec"]["decision_count"], 20 + len([i for i in out["late"]
                             if any(dd["request_id"] == f"req-{i:08d}" for dd in out["rec"]["decisions"])]))
            self.assertEqual(n.controller.decisions, [])
            n.close()

    def test_T_C33_duplicate_controllers_fenced_across_processes(self):
        import subprocess, sys, textwrap
        with Tmp() as d:
            n, cp, m = node(d)
            script = textwrap.dedent(f"""
                import sys; sys.path.insert(0, {str(T.__file__.rsplit('/', 3)[0])!r}); sys.path.insert(0, {os.path.dirname(__file__)!r})
                from _util import node
                try:
                    node({str(d)!r}, owner='intruder'); print('ACQUIRED')
                except Exception as e:
                    print(getattr(e, 'code', repr(e)))
            """)
            out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True).stdout.strip().splitlines()[-1]
            self.assertEqual(out, "GAP04-E0501")
            n.close()


class PropertyFuzz(unittest.TestCase):
    def test_T_C34_random_lifecycle_invariants(self):
        """Invariants over random event sequences: never a decision above tier; never after expiry;
        never while connected; reconcile returns exactly the accepted set; epoch monotone."""
        rnd = random.Random(SEED)
        for it in range(ITERS // 10):
            ctl = AutonomyController("s", lease_ticks=rnd.randint(1, 400), max_policy_staleness_ticks=rnd.randint(1, 400))
            t, accepted, epoch = 0, [], 0
            for _ in range(60):
                t += rnd.choice([0, 1, 5, 40, 100])
                op = rnd.choice(["partition", "decide", "decide", "decide", "reconcile", "renew", "tier"])
                kind = rnd.choice(sorted(PERMITTED["full"]))
                try:
                    if op == "partition":
                        ctl.partition(t)
                    elif op == "decide":
                        tier = ctl.tier(t)
                        r = ctl.decide(kind, "x", t)
                        self.assertIn(kind, PERMITTED[tier]); self.assertNotEqual(tier, "expired")
                        self.assertIsNotNone(ctl.partitioned_since)
                        accepted.append(r)
                    elif op == "reconcile":
                        rec = ctl.reconcile(t)
                        self.assertEqual(rec["decisions"], accepted); accepted = []
                    elif op == "renew":
                        ctl.renew(t, control_plane_reachable=True)
                    self.assertGreaterEqual(ctl.partition_epoch, epoch); epoch = ctl.partition_epoch
                except (ControllerError, ValueError, PermissionError):
                    pass

    def test_T_C34_fuzz_lease_parser_never_accepts_mutations(self):
        rnd = random.Random(SEED)
        cp = T.ControlPlane(); pol = cp.policy(); now = 1_800_000_000
        raw = canonical.dumps(cp.lease(pol, now))
        ts = cp.trust()
        for _ in range(ITERS):
            b = bytearray(raw)
            for _ in range(rnd.randint(1, 4)):
                op = rnd.random()
                i = rnd.randrange(len(b))
                if op < 0.5:
                    b[i] = rnd.randrange(256)
                elif op < 0.75:
                    del b[i]
                else:
                    b.insert(i, rnd.randrange(256))
            if bytes(b) == raw:
                continue
            try:
                TR.verify_lease(bytes(b), trust=ts, expected_scope=T.SCOPE, now=now + 1, min_authority_epoch=1,
                                expected_policy_digest=TR.policy_digest(pol))
                self.fail("mutated envelope accepted")
            except Gap04Error as e:
                self.assertIn(e.code, REGISTRY)

    def test_T_C34_fuzz_schema_payloads_and_boundaries(self):
        from gap04_disconnected_operation_controller.runtime.config import default_config, validate_config
        rnd = random.Random(SEED)
        vals = [None, True, -1, 0, 1, 2**53, "", "x" * 10000, [], {}, "é", 1.5]
        for _ in range(ITERS):
            c = default_config()
            sect = rnd.choice(list(c))
            if isinstance(c[sect], dict) and c[sect]:
                k = rnd.choice(list(c[sect])); c[sect][k] = rnd.choice(vals)
            else:
                c[sect] = rnd.choice(vals)
            try:
                validate_config(c)
            except Gap04Error as e:
                self.assertEqual(e.code, "GAP04-E0800")
        for v in (-1, True, 1.0, "1", None):
            with self.assertRaises((TypeError, ValueError)):
                AutonomyController("s", lease_ticks=v)

    def test_T_C34_canonical_roundtrip_property(self):
        rnd = random.Random(SEED)
        def gen(depth=0):
            r = rnd.random()
            if depth > 3 or r < 0.3:
                return rnd.choice([None, True, False, rnd.randint(-10**9, 10**9), "".join(rnd.choice("aéß中") for _ in range(rnd.randint(0, 5)))])
            if r < 0.6:
                return [gen(depth + 1) for _ in range(rnd.randint(0, 4))]
            return {f"k{rnd.randint(0, 9)}": gen(depth + 1) for _ in range(rnd.randint(0, 4))}
        for _ in range(ITERS):
            v = gen()
            try:
                b = canonical.dumps(v)
            except canonical.CanonicalError:
                continue
            self.assertEqual(canonical.loads(b), v); self.assertEqual(canonical.dumps(canonical.loads(b)), b)


class Adversarial(unittest.TestCase):
    def test_T_C35_replay_of_old_lease_after_new(self):
        with Tmp() as d:
            n, cp, m = node(d)
            pol, l1 = T.bring_up(n, cp, m)
            l2 = cp.lease(pol, n.clock.now())
            n.install_lease(l2)
            code(self, "GAP04-E0210", n.install_lease, l1)
            n.install_lease(l2)   # idempotent redelivery of current
            n.close()

    def test_T_C35_spoofed_reachability_cannot_end_partition(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            evil_seed, _ = crypto.generate_signing_key()
            from gap04_disconnected_operation_controller.runtime.adapters import sign_heartbeat
            for _ in range(10):
                m.t += 1
                n.observe_reachability(sign_heartbeat("site-a", n.adapters.reachability.challenge(), 1, "cp-1", "cp-1-k1", evil_seed))
            self.assertFalse(n.adapters.reachability.reachable)
            code(self, "GAP04-E0100", n.install_lease, cp.lease(cp.policy(), n.clock.now()))
            n.close()

    def test_T_C35_journal_tampering_detected_on_open(self):
        with Tmp() as d:
            n, cp, m = node(d, encrypt_journal=False)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            n.decide("restart", "ns/a", "req-00000001")
            n.close()
            p = d / "journal" / "journal.wal"
            lines = p.read_bytes().splitlines(keepends=True)
            p.write_bytes(b"".join(lines[:-3] + lines[-2:]))   # drop an inconvenient frame
            with self.assertRaises(Gap04Error) as cm:
                node(d, cp=cp, mono=m, encrypt_journal=False)
            self.assertIn(cm.exception.code, ("GAP04-E0401", "GAP04-E0402"))

    def test_T_C35_privilege_escalation_blocked(self):
        with Tmp() as d:
            n, cp, m = node(d)
            pol, _ = T.bring_up(n, cp, m)
            l = cp.lease(pol, n.clock.now(), caps=["restart"])
            n.install_lease(l); T.go_dark(n, m)
            code(self, "GAP04-E0101", n.decide, "admit-new", "ns/a", "req-00000001")
            code(self, "GAP04-E0004", n.request_override, "tier_cap", value="full", reason="escalate me please", ttl_s=60, requester=T.OPERATOR)
            n.close()

    def test_T_C35_exhaustion_bounded(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            code(self, "GAP04-E0004", n.decide, "restart", "x" * 10_000, "req-00000001")
            code(self, "GAP04-E0004", n.decide, "restart", "ns/a", "r" * 1000)
            with self.assertRaises(Exception):
                TR.verify_lease(b"{" * 100_000, trust=cp.trust(), expected_scope=T.SCOPE, now=1, min_authority_epoch=1, expected_policy_digest=None)
            n.close()

    def test_T_C35_signature_malleability_and_key_confusion(self):
        cp = T.ControlPlane(); pol = cp.policy(); now = 1_800_000_000
        env = cp.lease(pol, now)
        ts = cp.trust()
        sig = crypto.b64d(env["sig"])
        for bad in (env["sig"] + "=", env["sig"].upper(), crypto.b64e(sig[:63]), crypto.b64e(sig + b"\0")):
            code(self, "GAP04-E0201", TR.verify_lease, dict(env, sig=bad), trust=ts, expected_scope=T.SCOPE, now=now,
                 min_authority_epoch=1, expected_policy_digest=None)
        # a key authorized only for heartbeats must not sign leases
        doc = cp.trust_doc(); doc["keys"][0]["purposes"] = ["heartbeat"]
        code(self, "GAP04-E0202", TR.verify_lease, env, trust=TR.TrustStore.from_doc(doc), expected_scope=T.SCOPE,
             now=now, min_authority_epoch=1, expected_policy_digest=None)


if __name__ == "__main__":
    unittest.main()
