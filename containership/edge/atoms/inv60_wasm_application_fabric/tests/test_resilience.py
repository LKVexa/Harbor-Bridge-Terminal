"""M13 M19 M42-M50 M71 M74 - partitions, retries, breakers, failover, durability, chaos, concurrency."""
import json, os, random, tempfile, threading, unittest
from _harness import World, Clock
from inv60_wasm_application_fabric.fabric import resilience as rs, membership as mb, placement as pl
from inv60_wasm_application_fabric.fabric.errors import FabricError
from inv60_wasm_application_fabric.fabric.store import StateStore
from inv60_wasm_application_fabric.fabric.ledger import AuditLedger


class Deadlines(unittest.TestCase):
    def test_expiry_at_each_hop(self):
        c = Clock(0.0)
        d = rs.Deadline.after(1.0, c)
        d.check("a"); c.advance(1.0)
        with self.assertRaises(FabricError) as cm:
            d.check("b")
        self.assertEqual(cm.exception.detail["hop"], "b")

    def test_fabric_call_deadline(self):
        w = World(); w.deploy()
        w.fabric.link(w.tok("deployer-a"), "api", "kv", lambda *a: w.mono.advance(2) or 1, tenant="tenant-a",
                      grantee=w.p["api"].id, operations=("get",))
        r = w.fabric.call(w.tok("api"), "api", "kv", "get", tenant="tenant-a", deadline=rs.Deadline.after(1.0, w.mono))
        self.assertEqual(r.code, "DEADLINE_EXCEEDED")
        r = w.fabric.call(w.tok("api"), "api", "kv", "get", tenant="tenant-a", deadline=rs.Deadline.after(0.0, w.mono))
        self.assertEqual(r.code, "DEADLINE_EXCEEDED")

    def test_cancellation_and_commit_race(self):
        t = rs.CancelToken(); self.assertTrue(t.cancel())
        with self.assertRaises(FabricError):
            t.check()
        t2 = rs.CancelToken(); t2.committed = True
        self.assertFalse(t2.cancel()); t2.check()


class Retries(unittest.TestCase):
    def test_retries_idempotent_until_success(self):
        n = {"i": 0}
        def f():
            n["i"] += 1
            if n["i"] < 3:
                raise FabricError("UNAVAILABLE")
            return "ok"
        p = rs.RetryPolicy(sleep=lambda s: None)
        self.assertEqual(p.run(f, op_class="stop"), "ok")

    def test_non_idempotent_not_retried(self):
        n = {"i": 0}
        def f():
            n["i"] += 1; raise FabricError("UNAVAILABLE")
        with self.assertRaises(FabricError):
            rs.RetryPolicy(sleep=lambda s: None).run(f, op_class="call")
        self.assertEqual(n["i"], 1)
        n["i"] = 0
        with self.assertRaises(FabricError):
            rs.RetryPolicy(sleep=lambda s: None).run(f, op_class="call", idempotency_key="k" * 8)
        self.assertEqual(n["i"], 4)

    def test_backoff_bounded_with_jitter(self):
        p = rs.RetryPolicy(base_s=0.1, cap_s=0.5)
        vals = [p.backoff(a) for a in range(1, 12)]
        self.assertTrue(all(0 <= v <= 0.5 for v in vals))
        self.assertGreater(len(set(vals)), 5)

    def test_retry_budget_prevents_storm(self):
        budget = rs.RetryBudget(ratio=0.1, min_retries=2)
        p = rs.RetryPolicy(budget=budget, sleep=lambda s: None)
        calls = {"n": 0}
        def f():
            calls["n"] += 1; raise FabricError("UNAVAILABLE")
        for _ in range(20):
            with self.assertRaises(FabricError):
                p.run(f, op_class="stop")
        self.assertLessEqual(budget.retries, max(2, 0.1 * 20) + 1)
        self.assertLess(calls["n"], 20 * 4)

    def test_backoff_respects_deadline(self):
        c = Clock(0.0)
        p = rs.RetryPolicy(base_s=10, cap_s=10, sleep=lambda s: None, rng=random.Random(1))
        def f(): raise FabricError("UNAVAILABLE", retry_after_s=5)
        with self.assertRaises(FabricError) as cm:
            p.run(f, op_class="stop", deadline=rs.Deadline.after(1.0, c))
        self.assertEqual(cm.exception.code, "DEADLINE_EXCEEDED")

    def test_idempotency_store_retention_and_mismatch(self):
        c = Clock(0.0); s = rs.IdempotencyStore(retention_s=10, clock=c)
        s.store("abcdefgh", {"a": 1}, "R")
        self.assertEqual(s.lookup("abcdefgh", {"a": 1}), "R")
        with self.assertRaises(FabricError):
            s.lookup("abcdefgh", {"a": 2})
        c.advance(11)
        self.assertIsNone(s.lookup("abcdefgh", {"a": 2}))
        with self.assertRaises(FabricError):
            s.lookup("short", {})


class Breaker(unittest.TestCase):
    def test_open_half_open_close(self):
        c = Clock(0.0); b = rs.CircuitBreaker(failure_threshold=2, cooldown_s=5, clock=c)
        b.failure(); b.before(); b.failure()
        with self.assertRaises(FabricError) as cm:
            b.before()
        self.assertEqual(cm.exception.code, "CIRCUIT_OPEN")
        c.advance(5); b.before(); self.assertEqual(b.state, "half_open")
        b.failure(); self.assertEqual(b.state, "open")
        c.advance(5); b.before(); b.success(); self.assertEqual(b.state, "closed")

    def test_fabric_provider_faults_open_circuit(self):
        w = World(); w.deploy()
        def bad(*a): raise RuntimeError("boom secret=Zq9-LEAKCANARY")
        w.fabric.link(w.tok("deployer-a"), "api", "kv", bad, tenant="tenant-a", grantee=w.p["api"].id, operations=("get",))
        codes = [w.fabric.call(w.tok("api"), "api", "kv", "get", tenant="tenant-a").code for _ in range(7)]
        self.assertEqual(codes[:5], ["PROVIDER_ERROR"] * 5)
        self.assertEqual(codes[5], "CIRCUIT_OPEN")
        self.assertNotIn("LEAKCANARY", json.dumps(list(w.fabric.log.buffer)) + json.dumps(w.fabric.ledger.records))


class Membership(unittest.TestCase):
    def test_detector_states(self):
        c = Clock(0.0); d = mb.FailureDetector(3, 8, 10, clock=c)
        d.heartbeat("h", 1)
        self.assertEqual(d.status("h"), "healthy")
        c.advance(3); self.assertEqual(d.status("h"), "suspect")
        c.advance(5); self.assertEqual(d.status("h"), "lost")
        d.heartbeat("h", 2); c.advance(2.9); self.assertEqual(d.status("h"), "healthy")

    def test_stall_detection(self):
        c = Clock(0.0); d = mb.FailureDetector(3, 8, 5, clock=c)
        d.heartbeat("h", 1)
        for _ in range(6):
            c.advance(1); d.heartbeat("h", 1)
        self.assertEqual(d.status("h"), "stalled")
        d.heartbeat("h", 2); self.assertEqual(d.status("h"), "healthy")

    def test_bad_thresholds(self):
        with self.assertRaises(FabricError):
            mb.FailureDetector(8, 3)

    def test_minority_partition_cannot_grant_authority(self):
        c = Clock(0.0); lm = mb.LeaseManager(["v1", "v2", "v3"], clock=c)
        with self.assertRaises(FabricError) as cm:
            lm.acquire("A", ["v1"])
        self.assertEqual(cm.exception.code, "PARTITIONED")
        a = lm.acquire("A", ["v1", "v2"])
        with self.assertRaises(FabricError) as cm:
            lm.acquire("B", ["v2", "v3"])
        self.assertEqual(cm.exception.code, "FENCED")
        c.advance(11)
        b = lm.acquire("B", ["v2", "v3"])
        self.assertGreater(b.epoch, a.epoch)
        with self.assertRaises(FabricError):
            lm.check_fence(a.epoch)              # stale writer fenced
        lm.check_fence(b.epoch)

    def test_isolated_serving_window(self):
        c = Clock(0.0); p = mb.PartitionState(isolated_serving_s=60, clock=c)
        p.isolate(); self.assertTrue(p.may_serve_existing())
        with self.assertRaises(FabricError):
            p.require_new_authority()
        c.advance(61); self.assertFalse(p.may_serve_existing())
        p.heal(); p.require_new_authority()

    def test_fabric_partition_blocks_mutation_serves_existing(self):
        w = World(); w.deploy()
        w.fabric.link(w.tok("deployer-a"), "api", "kv", lambda *a: 7, tenant="tenant-a", grantee=w.p["api"].id, operations=("get",))
        w.fabric.partition.isolate()
        self.assertEqual(w.fabric.call(w.tok("api"), "api", "kv", "get", tenant="tenant-a").code, "OK")
        self.assertEqual(w.fabric.stop(w.tok("deployer-a"), "api", tenant="tenant-a").code, "PARTITIONED")
        w.mono.advance(301)
        self.assertEqual(w.fabric.call(w.tok("api"), "api", "kv", "get", tenant="tenant-a").code, "PARTITIONED")
        self.assertEqual(w.fabric.status()["partition"], "isolated_expired")

    def test_failover_without_quorum_refused(self):
        w = World(); w.deploy()
        w.fabric.partition.isolate()
        w.mono.advance(9); w.fabric.heartbeat("h2"); w.fabric.heartbeat("h3")
        res = w.fabric.sweep()
        self.assertEqual(res[0].code, "PARTITIONED")
        self.assertEqual(w.fabric.lattice.instances["api"], "h1")   # no split-brain move


class Placement(unittest.TestCase):
    H = lambda self, i, **k: pl.HostInfo(i, **k)

    def test_precedence_and_tie_break(self):
        hosts = [self.H("b", latency_class=1, cost=2), self.H("a", latency_class=1, cost=2), self.H("c", latency_class=0, cost=9)]
        self.assertEqual(pl.resolve(hosts, pl.Request("x", "t"))["chosen"], "c")
        hosts[2].region = "us"
        self.assertEqual(pl.resolve(hosts, pl.Request("x", "t", regions=("default",)))["chosen"], "a")

    def test_hard_constraints_fail_closed(self):
        hosts = [self.H("a", attested=False), self.H("b", dedicated_tenant="other"), self.H("c", region="us"),
                 self.H("d", capacity=1, placed=[("t", "z", "q")]), self.H("e", placed=[("t", "app", "r")])]
        with self.assertRaises(FabricError) as cm:
            pl.resolve(hosts, pl.Request("x", "t", app="app", regions=("default",)))
        self.assertEqual(cm.exception.code, "NO_ELIGIBLE_TARGET")

    def test_only_capacity_relaxable_with_break_glass(self):
        hosts = [self.H("d", capacity=1, placed=[("t", "z", "q")])]
        with self.assertRaises(FabricError):
            pl.resolve(hosts, pl.Request("x", "t"), relax={"capacity"})
        self.assertEqual(pl.resolve(hosts, pl.Request("x", "t"), relax={"capacity"}, override_decision="bg-1")["chosen"], "d")
        with self.assertRaises(FabricError):
            pl.resolve(hosts, pl.Request("x", "t"), relax={"residency"}, override_decision="bg-1")

    def test_precedence_validation(self):
        pl.validate_precedence(pl.HARD + pl.SOFT)
        for bad in (pl.HARD, ("slo",) + pl.HARD + ("cost",), pl.HARD + pl.SOFT + ("slo",)):
            with self.assertRaises(FabricError):
                pl.validate_precedence(bad)

    def test_record_lists_every_rule(self):
        rec = pl.resolve([self.H("a"), self.H("b")], pl.Request("x", "t"))
        self.assertEqual({r["rule"] for r in rec["evaluated"][0]["rules"]}, set(pl.HARD))
        self.assertEqual(rec["policy"], pl.PRECEDENCE_VERSION)

    def test_residency_aware_failover(self):
        w = World(hosts=("h1", "h2", "h3"), regions={"h1": "eu", "h2": "us", "h3": "eu"})
        w.deploy(regions=("eu",))
        first = w.fabric.lattice.instances["api"]
        w.mono.advance(9)
        for h in ("h1", "h2", "h3"):
            if h != first:
                w.fabric.heartbeat(h)
        w.fabric.sweep()
        self.assertEqual(w.fabric.hosts[w.fabric.lattice.instances["api"]].region, "eu")

    def test_failover_with_no_residency_target_fails_component(self):
        w = World(hosts=("h1", "h2"), regions={"h1": "eu", "h2": "us"})
        w.deploy(regions=("eu",))
        w.mono.advance(9); w.fabric.heartbeat("h2")
        res = w.fabric.sweep()
        self.assertEqual(res[0].code, "NO_ELIGIBLE_TARGET")
        self.assertEqual(w.fabric.comp_sm["api"].state, "failed")


class Durability(unittest.TestCase):
    def test_wal_replay_and_torn_tail(self):
        with tempfile.TemporaryDirectory() as d:
            s = StateStore(d)
            s.apply("host.put", name="h1", record={"state": "active"})
            s.apply("component.put", name="c", record={"tenant": "t"})
            s.snapshot()
            s.apply("link.put", component="c", link="kv", record={})
            with open(s.wal, "a") as fh:
                fh.write('{"seq": 99, "op": "host.pu')     # crash mid-append
            s2 = StateStore(d)
            self.assertEqual(s2.torn_lines, 1)
            self.assertIn("c|kv", s2.state["links"])
            self.assertEqual(s2.seq, 3)

    def test_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            s = StateStore(d)
            for i in range(5):
                s.apply("config.generation", generation=i)
            a = StateStore(d).state; b = StateStore(d).state
            self.assertEqual(a, b)

    def test_fabric_restart_reconstructs_and_revokes_links(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(tmp=d); w.deploy()
            w.fabric.link(w.tok("deployer-a"), "api", "kv", print, tenant="tenant-a", grantee=w.p["api"].id)
            head = w.fabric.ledger.head
            from inv60_wasm_application_fabric.fabric.fabric import Fabric
            f2 = Fabric(trust=w.trust, policy=w.policy, state_dir=os.path.join(d, "state"),
                        ledger_path=os.path.join(d, "audit.jsonl"), clock=w.clock, mono=w.mono)
            self.assertEqual(f2.comp_sm["api"].state, "running")
            self.assertEqual(f2.link_sm[("api", "kv")].state, "revoked")   # fail closed after restart
            self.assertEqual(f2.ledger.verify(anchored_head=head), len(f2.ledger.records))


class Ledger(unittest.TestCase):
    def mk(self, d, key=None):
        L = AuditLedger(os.path.join(d, "l.jsonl"), mac_key=key)
        for i in range(5):
            L.append("k", "actor", {"i": i})
        return L

    def test_detects_modification_deletion_reorder_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            L = self.mk(d, b"k" * 32); head = L.head
            for mutate in (lambda r: r[2]["data"].update(i=99), lambda r: r.pop(2),
                           lambda r: r.insert(1, r.pop(3))):
                L2 = AuditLedger(None, mac_key=b"k" * 32); L2.records = json.loads(json.dumps(L.records))
                mutate(L2.records)
                with self.assertRaises(FabricError):
                    L2.verify()
            L3 = AuditLedger(None, mac_key=b"k" * 32); L3.records = json.loads(json.dumps(L.records))[:-1]
            L3.verify()                                   # the bare chain's blind spot...
            with self.assertRaises(FabricError):
                L3.verify(anchored_head=head)             # ...closed by the external anchor

    def test_mac_forgery(self):
        with tempfile.TemporaryDirectory() as d:
            self.mk(d, b"k" * 32)
            with self.assertRaises(FabricError):
                AuditLedger(os.path.join(d, "l.jsonl"), mac_key=b"x" * 32)

    def test_redacts_secrets(self):
        L = AuditLedger(None); r = L.append("k", "a", {"password": "p", "note": "token=abc123"})
        self.assertEqual(r["data"]["password"], "[REDACTED]")
        self.assertNotIn("abc123", r["data"]["note"])


class EmergencyControls(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.w.deploy()
        self.w.fabric.link(self.w.tok("deployer-a"), "api", "kv", lambda *a: 1, tenant="tenant-a",
                           grantee=self.w.p["api"].id, operations=("get",))

    def test_quarantine_component(self):
        self.assertEqual(self.w.fabric.quarantine(self.w.tok("ops"), "api", reason="ir-1").code, "OK")
        self.assertEqual(self.w.fabric.call(self.w.tok("api"), "api", "kv", "get", tenant="tenant-a").code, "QUARANTINED")
        self.assertEqual(self.w.fabric.comp_sm["api"].state, "quarantined")

    def test_quarantine_host_excluded_from_placement(self):
        self.w.fabric.quarantine(self.w.tok("ops"), "h2", reason="ir-2")
        self.w.fabric.quarantine(self.w.tok("ops"), "h3", reason="ir-2")
        self.assertEqual(self.w.deploy("b", name="tenant-a/b", data=b"b").value, "h1")

    def test_only_operator_can_quarantine(self):
        self.assertEqual(self.w.fabric.quarantine(self.w.tok("deployer-a"), "api", reason="x").code, "PERMISSION_DENIED")

    def test_freeze_and_read_only_modes(self):
        self.assertEqual(self.w.fabric.set_mode(self.w.tok("ops"), "frozen").code, "OK")
        self.assertEqual(self.w.fabric.stop(self.w.tok("deployer-a"), "api", tenant="tenant-a").code, "QUARANTINED")
        self.assertEqual(self.w.fabric.call(self.w.tok("api"), "api", "kv", "get", tenant="tenant-a").code, "OK")
        self.assertFalse(self.w.fabric.status()["ready"])
        self.w.fabric.set_mode(self.w.tok("ops"), "read_only")
        self.assertEqual(self.w.fabric.stop(self.w.tok("deployer-a"), "api", tenant="tenant-a").code, "UNAVAILABLE")
        self.assertEqual(self.w.fabric.set_mode(self.w.tok("ops"), "bogus").code, "INVALID_ARGUMENT")


class Concurrency(unittest.TestCase):
    def test_concurrent_calls_respect_inflight_and_ledger_intact(self):
        w = World(limits={"max_inflight_per_tenant": 4, "rate_per_tenant": 100000.0, "burst_per_tenant": 100000})
        w.deploy()
        gate = threading.Barrier(8)
        def prov(*a):
            return 1
        w.fabric.link(w.tok("deployer-a"), "api", "kv", prov, tenant="tenant-a", grantee=w.p["api"].id, operations=("get",))
        toks = [w.tok("api") for _ in range(80)]
        codes = []
        lock = threading.Lock()
        def worker(chunk):
            gate.wait()
            for t in chunk:
                c = w.fabric.call(t, "api", "kv", "get", tenant="tenant-a").code
                with lock:
                    codes.append(c)
        ths = [threading.Thread(target=worker, args=(toks[i::8],)) for i in range(8)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(len(codes), 80)
        self.assertTrue(set(codes) <= {"OK", "QUOTA_EXCEEDED"}, sorted(set(codes)) + [m for m in (r.get("event") for r in w.fabric.log.buffer)][:3])
        self.assertEqual(w.fabric.limiter.usage()["inflight_global"], 0)

    def test_concurrent_duplicate_start_only_one_wins(self):
        w = World()
        ref = w.fabric.push(w.tok("deployer-a"), "tenant-a/api", b"\x00asm-component-v1", w.artifact(), tenant="tenant-a").value
        toks = [w.tok("deployer-a") for _ in range(6)]
        codes = []
        lock = threading.Lock()
        def go(t):
            r = w.fabric.start(t, "api", ref, tenant="tenant-a")
            with lock:
                codes.append(r.code)
        ths = [threading.Thread(target=go, args=(t,)) for t in toks]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(codes.count("OK"), 1, codes)


class Chaos(unittest.TestCase):
    """M50/M74: seeded fault injection; invariants must hold after every step."""

    def test_seeded_chaos_invariants(self):
        for seed in range(12):
            rng = random.Random(seed)
            w = World(hosts=tuple(f"h{i}" for i in range(5)))
            for i in range(8):
                w.deploy(f"c{i}", name=f"tenant-a/c{i}", data=f"c{i}".encode())
            alive = set(w.fabric.hosts)
            for step in range(15):
                ev = rng.choice(["lose", "heal", "partition", "heartbeat"])
                if ev == "lose" and len(alive) > 1:
                    alive.discard(rng.choice(sorted(alive)))
                elif ev == "partition":
                    w.fabric.partition.isolate()
                elif ev == "heal":
                    w.fabric.partition.heal()
                w.mono.advance(rng.choice([1, 4, 9]))
                for h in alive:
                    w.fabric.heartbeat(h)
                w.fabric.sweep()
                # invariants
                for comp, host in w.fabric.lattice.instances.items():
                    self.assertIn(host, w.fabric.hosts)
                    self.assertNotEqual(w.fabric.host_sm[host].state, "lost", f"seed {seed}: {comp} on lost host")
                    self.assertEqual(w.fabric.comp_sm[comp].state, "running")
                w.fabric.ledger.verify()


if __name__ == "__main__":
    unittest.main()


class ConcurrencyRegressions(unittest.TestCase):
    """Defects found by the -O concurrency run of this build: unlocked nonce GC raised
    'dictionary changed size during iteration' (-> INTERNAL), and the replay
    check-then-record and ledger append were not atomic."""

    def test_same_token_accepted_once_under_race(self):
        from inv60_wasm_application_fabric.fabric.fabric import AUDIENCE
        w = World(hosts=("h1",))
        for _ in range(20):
            tok = w.tok("api"); ok = []; gate = threading.Barrier(8)
            def go():
                gate.wait()
                try:
                    w.trust.authenticate(tok, AUDIENCE); ok.append(1)
                except FabricError:
                    pass
            ths = [threading.Thread(target=go) for _ in range(8)]
            [t.start() for t in ths]; [t.join() for t in ths]
            self.assertEqual(len(ok), 1)

    def test_ledger_chain_intact_under_concurrent_append(self):
        L = AuditLedger(None); gate = threading.Barrier(8)
        def go():
            gate.wait()
            for i in range(200):
                L.append("k", "a", {"i": i})
        ths = [threading.Thread(target=go) for _ in range(8)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(L.verify(), 1600)
