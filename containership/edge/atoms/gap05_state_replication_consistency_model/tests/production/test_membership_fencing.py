import json
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path

import _util
from gap05_state_replication_consistency_model.production import errors as E
from gap05_state_replication_consistency_model.production.anti_entropy import reconcile
from gap05_state_replication_consistency_model.production.identity import ReplicaKeys
from gap05_state_replication_consistency_model.production.membership import (
    CounterAllocator, CounterGuard, MembershipConfig, MembershipStore, ReplicaRecord)
from gap05_state_replication_consistency_model.production.protect import sign_write
from gap05_state_replication_consistency_model.production.schemas import make_write_doc
from gap05_state_replication_consistency_model.production.testkit import NOW, Cluster, E as ENV, T, replica_record


def rec(n):
    return ReplicaRecord(n, f"spiffe://t/replica/{n}", (n,))


class MembershipStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MembershipStore(Path(self.tmp.name), MembershipConfig(1, {"a": rec("a"), "b": rec("b")},
                                                                         None, "boot", "genesis"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_cas_and_chain(self):
        """items: MC14-001 MC14-002 MC14-004 MC14-012 MC32-001
        Epochs advance by one under CAS; a stale controller loses; history is a digest chain."""
        cfg = self.store.add_replica("c", "spiffe://t/replica/c", ("c",), author="ctl-1", expected_epoch=1)
        self.assertEqual(cfg.epoch, 2)
        with self.assertRaises(E.ConfigError) as cm:
            self.store.add_replica("d", "spiffe://t/replica/d", ("d",), author="ctl-2", expected_epoch=1)
        self.assertEqual(cm.exception.code, "CORR_CAS_CONFLICT")
        self.assertEqual(self.store.at(2).parent, self.store.at(1).digest)

    def test_concurrent_controllers_one_winner(self):
        """items: MC14-002 MC14-006 MC14-011 MC37-009
        Ten racing controllers with the same expected epoch: exactly one activation succeeds."""
        wins, errors = [], []

        def go(i):
            try:
                self.store.add_replica(f"n{i}", f"spiffe://t/replica/n{i}", (f"n{i}",), author=f"ctl{i}",
                                       expected_epoch=1)
                wins.append(i)
            except E.ConfigError:
                errors.append(i)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(10)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(wins), 1)
        self.assertEqual(self.store.epoch, 2)

    def test_corrupt_chain_detected_on_load(self):
        """items: MC14-010 MC14-011
        A tampered historical epoch breaks the chain and refuses to load."""
        self.store.add_replica("c", "spiffe://t/replica/c", ("c",), author="x", expected_epoch=1)
        p = Path(self.tmp.name) / "epoch-00000001.json"
        p.write_bytes(p.read_bytes().replace(b"genesis", b"genesiz"))
        with self.assertRaises(E.IntegrityError):
            MembershipStore(Path(self.tmp.name))

    def test_validation(self):
        """items: MC14-008
        Duplicate active identity mappings and empty active sets are refused."""
        dup = {"a": rec("a"), "b": ReplicaRecord("b", "spiffe://t/replica/a", ("b",))}
        with self.assertRaises(E.ConfigError):
            self.store.activate(1, dup, author="x", reason="dup")
        with self.assertRaises(E.ConfigError):
            MembershipConfig(2, {"a": ReplicaRecord("a", "w", ("a",), (), "retired", {}, 1, 2)}, "p", "x",
                             "y").validate()

    def test_rollback_keeps_retirements(self):
        """items: MC14-004 MC32-004
        Rollback is a forward activation; a replica retired since cannot be un-fenced by it."""
        self.store.remove_replica("b", high_water={"*": 5}, author="x", expected_epoch=1)
        cfg = self.store.rollback_to(1, expected_epoch=2, author="x", reason="bad deploy")
        self.assertEqual(cfg.epoch, 3)
        self.assertEqual(cfg.replicas["b"].status, "retired")

    def test_fencing_rules(self):
        """items: MC32-002 MC32-003 MC32-012 MC15-003 MC15-012 MC03-006
        Future epochs, pre-join epochs and retired-above-high-water authorship are refused."""
        self.store.remove_replica("b", high_water={"k": 3}, author="x", expected_epoch=1)
        self.store.check_authorship("b", 1, "k", 3)
        for args, code in ((("b", 1, "k", 4), "SEC_FENCED_RETIRED"), (("b", 2, "k", 1), "SEC_NOT_ACTIVE_IN_EPOCH"),
                           (("a", 9, "k", 1), "SEC_FUTURE_EPOCH")):
            with self.assertRaises(E.FencedError) as cm:
                self.store.check_authorship(*args)
            self.assertEqual(cm.exception.code, code)

    def test_reseed_creates_new_incarnation(self):
        """items: MC15-005 MC15-007 MC25-008 MC37-005
        Reseed retires the old name and adds name~2; a used name can never be re-added."""
        new, cfg = self.store.reseed_replica("b", "spiffe://t/replica/b~2", ("b2",), high_water={"*": 7},
                                             author="x", expected_epoch=1)
        self.assertEqual(new, "b~2")
        self.assertEqual(cfg.replicas["b"].status, "retired")
        with self.assertRaises(E.ConfigError):
            self.store.add_replica("b", "spiffe://t/replica/b", ("b",), author="x", expected_epoch=cfg.epoch)


class CounterTests(unittest.TestCase):
    def test_monotonic_across_restart_and_no_reuse(self):
        """items: MC03-001 MC03-002 MC03-003 MC03-004 MC03-012
        Block reservation persisted before issue: a restart skips the reserved block, never reuses."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            a = CounterAllocator(p, "a", block=4)
            got = [a.next("k") for _ in range(3)]
            b = CounterAllocator(p, "a", block=4)   # simulated crash + restart
            nxt = b.next("k")
            self.assertEqual(got, [1, 2, 3])
            self.assertGreater(nxt, 3)
            with self.assertRaises(E.IntegrityError):
                CounterAllocator(p, "other")

    def test_thread_contention_unique(self):
        """items: MC03-010
        Many threads allocating concurrently never receive the same counter."""
        with tempfile.TemporaryDirectory() as d:
            a = CounterAllocator(Path(d) / "c.json", "a", block=16)
            out = []
            lock = threading.Lock()

            def go():
                for _ in range(200):
                    v = a.next("k")
                    with lock:
                        out.append(v)
            ts = [threading.Thread(target=go) for _ in range(8)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(len(out), len(set(out)))

    def test_multiprocess_contention_documented_limit(self):
        """items: MC03-011 MC03-010
        Two processes allocating from one counter file concurrently never receive the same counter
        (exclusive flock + durable ceiling re-read)."""
        script = textwrap.dedent("""
            import sys, json
            sys.path.insert(0, {root!r})
            from pathlib import Path
            from gap05_state_replication_consistency_model.production.membership import CounterAllocator
            a = CounterAllocator(Path({p!r}), "a", block=1)
            print(json.dumps([a.next("k") for _ in range(50)]))
        """)
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "c.json")
            procs = [subprocess.Popen([sys.executable, "-c", script.format(root=str(_util.ROOT), p=p)],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(4)]
            outs = [pr.communicate() for pr in procs]
            for pr, (_o, err) in zip(procs, outs):
                self.assertEqual(pr.returncode, 0, err.decode()[-500:])
            vals = [v for o, _e in outs for v in json.loads(o)]
            self.assertEqual(len(vals), len(set(vals)), "cross-process counter collision")
            _util.record_observation("MC03-011", {"processes": 4, "allocations": len(vals), "collisions": 0})

    def test_guard_jump_rollback(self):
        """items: MC03-005 MC38-003
        Jumps beyond max_gap and counter reuse with different content are refused with evidence."""
        g = CounterGuard(max_gap=10)
        g.check("k", "a", {"a": 1}, "op1")
        g.record("k", "a", {"a": 1}, "op1")
        with self.assertRaises(E.CounterViolation) as cm:
            g.check("k", "a", {"a": 50}, "op2")
        self.assertEqual(cm.exception.code, "SEC_COUNTER_JUMP")
        with self.assertRaises(E.CounterViolation):
            g.check("k", "a", {"a": 1}, "opX")
        g2 = CounterGuard.restore(g.export())
        with self.assertRaises(E.CounterViolation):
            g2.check("k", "a", {"a": 1}, "opX")


class ChurnTests(unittest.TestCase):
    def test_removed_replica_cannot_write_after_fencing(self):
        """items: MC15-003 MC32-008 MC36-008 MC37-004 MC37-012 MC38-008
        After removal, a partitioned old replica's new writes are rejected everywhere; its
        pre-removal writes (<= high-water) still replicate."""
        c = Cluster(("a", "b", "c"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            old = b.write(T, ENV, "k", "before", principal="operator")
            hw = {"\x1f".join((T, ENV, "k")): 1}
            c.activate_everywhere(lambda s: s.remove_replica("b", high_water=hw, author="ctl", expected_epoch=1))
            self.assertEqual(a.submit(b.docs[old["op_id"]], principal=c.principal("b"), relay=True)["outcome"],
                             "converged")
            stale = sign_write(make_write_doc(tenant=T, environment=ENV, key="k", value="after", site="b",
                                              vector={"b": 2}, epoch=1), c.keys["b"].private_key)
            with self.assertRaises(E.FencedError):
                a.submit(stale, principal=c.principal("c"), relay=True)
            with self.assertRaises(E.FencedError):
                b.write(T, ENV, "k2", "x", principal="operator")
        finally:
            c.close()

    def test_join_during_writes_and_rejoin_via_sync(self):
        """items: MC15-002 MC37-001 MC37-002 MC37-003 MC15-008
        A replica added mid-stream converges via anti-entropy and can author only after activation."""
        c = Cluster(("a", "b"))
        try:
            a = c.nodes["a"]
            for i in range(5):
                a.write(T, ENV, f"k{i}", f"v{i}", principal="operator")
            newkeys = ReplicaKeys.provision(c.ca, "d", now=NOW)
            r = replica_record(newkeys)
            c.activate_everywhere(lambda s: s.add_replica("d", r.workload_id, r.key_fingerprints,
                                                          public_keys=r.public_keys, author="ctl",
                                                          expected_epoch=1))
            c.keys["d"] = newkeys
            c.memberships["d"] = MembershipStore(c.root / "d" / "membership",
                                                 MembershipConfig(1, dict(c.memberships["a"].at(1).replicas), None,
                                                                  "boot", "genesis"))
            # d's store must carry the same history: copy epoch files
            for f in (c.root / "a" / "membership").glob("epoch-*.json"):
                (c.root / "d" / "membership" / f.name).write_bytes(f.read_bytes())
            c.memberships["d"] = MembershipStore(c.root / "d" / "membership")
            c.policy = __import__("gap05_state_replication_consistency_model.production.testkit",
                                  fromlist=["full_policy"]).full_policy(
                ["operator"] + [k.credential.workload_id for k in c.keys.values()])
            d = c.open("d")
            c.nodes["d"] = d
            res = reconcile(a, d, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("d"))
            self.assertTrue(res["converged"])
            self.assertEqual(d.read(T, ENV, "k3", principal="operator")["value"], "v3")
            w = d.write(T, ENV, "k3", "from-d", principal="operator")
            self.assertEqual(w["outcome"], "converged")
            reconcile(a, d, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("d"))
            self.assertEqual(a.read(T, ENV, "k3", principal="operator")["value"], "from-d")
        finally:
            c.close()


class NamespaceTests(unittest.TestCase):
    def test_same_key_two_tenants_isolated(self):
        """items: MC06-001 MC06-003 MC06-012
        Identical logical keys in two tenants never share causal, dedupe or conflict state."""
        c = Cluster(("a", "b"), tenants=((T, ENV), ("tenant-b", ENV)))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            a.write(T, ENV, "k", "A", principal="operator")
            a.write("tenant-b", ENV, "k", "B", principal="operator")
            self.assertEqual(a.read(T, ENV, "k", principal="operator")["value"], "A")
            self.assertEqual(a.read("tenant-b", ENV, "k", principal="operator")["value"], "B")
            b.write(T, ENV, "k", "A2", principal="operator")
            reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            self.assertEqual(a.read(T, ENV, "k", principal="operator")["state"], "conflict")
            self.assertEqual(a.read("tenant-b", ENV, "k", principal="operator")["value"], "B")
        finally:
            c.close()

    def test_separator_injection_and_unauthorized_tenant(self):
        """items: MC06-002 MC06-004 MC06-005 MC06-010 MC06-011
        Separator/control chars cannot alias namespaces; writes to an ungranted tenant are denied and audited."""
        c = Cluster(("a",))
        try:
            a = c.nodes["a"]
            from gap05_state_replication_consistency_model.production.node import state_key
            with self.assertRaises(E.NamespaceError):
                state_key("t\x1fprod", "x", "k")
            with self.assertRaises(E.Gap05Error):
                a.write("t\x1fprod", ENV, "k", "v", principal="operator")
            with self.assertRaises(E.AuthorizationError):
                a.write("tenant-z", ENV, "k", "v", principal="operator")
            denied = [json.loads(l) for l in (a.dir / "audit").glob("audit-*.jsonl").__next__().read_text().splitlines()
                      if '"authz"' in l]
            self.assertTrue(any(not r["decision"]["allow"] and r["tenant"] == "tenant-z" for r in denied))
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
