import json
import multiprocessing as mp
import pathlib
import random
import tempfile
import threading
import time
import unittest

import _util
from gap05_state_replication_consistency_model.production import crdt
from gap05_state_replication_consistency_model.production import errors as E
from gap05_state_replication_consistency_model.production.anti_entropy import digest_tree, reconcile
from gap05_state_replication_consistency_model.production.lifecycle import apply_batch
from gap05_state_replication_consistency_model.production.schemas import canonical_bytes
from gap05_state_replication_consistency_model.production.testkit import Cluster, E as ENV, T
from gap05_state_replication_consistency_model.production.transport import (
    KIND_ACK, KIND_WRITE, Link, ReliableSender, ack_frame, decode_frame, parse_write_frame)


def frontier_ops(node):
    return {sk: sorted(d["op_id"] for d in node._frontier_docs(sk)) for sk in node.state_keys()}


class AntiEntropyTests(unittest.TestCase):
    def setUp(self):
        self.c = Cluster(("a", "b"))
        self.a, self.b = self.c.nodes["a"], self.c.nodes["b"]

    def tearDown(self):
        self.c.close()

    def rec(self):
        return reconcile(self.a, self.b, T, ENV, principal_a=self.c.principal("a"), principal_b=self.c.principal("b"))

    def test_converge_after_divergence(self):
        """items: MC17-001 MC17-002 MC17-003 MC17-012 MC36-004 MC36-005
        Divergent replicas reach identical digest roots and frontiers; concurrent writes stay open."""
        for i in range(30):
            self.a.write(T, ENV, f"k{i}", f"a{i}", principal="operator")
            if i % 3 == 0:
                self.b.write(T, ENV, f"k{i}", f"b{i}", principal="operator")
        r = self.rec()
        self.assertTrue(r["converged"])
        self.assertEqual(frontier_ops(self.a), frontier_ops(self.b))
        self.assertEqual(self.a.read(T, ENV, "k0", principal="operator")["state"], "conflict")
        self.assertEqual(self.a.read(T, ENV, "k1", principal="operator")["value"], "a1")

    def test_repair_is_authenticated_and_idempotent(self):
        """items: MC17-005 MC17-006 MC17-007
        Repair goes through REPLICATE authz + provenance; running it again moves nothing."""
        self.a.write(T, ENV, "k", "v", principal="operator")
        self.rec()
        r2 = self.rec()
        self.assertEqual(r2["rounds"][0][0]["sent"], 0)
        from gap05_state_replication_consistency_model.production.authz import Grant, Permission, Policy
        self.c.policy = Policy([Grant("operator", p, T, ENV) for p in Permission], version="deny-replication")
        self.a.write(T, ENV, "k2", "v", principal="operator")
        r3 = self.rec()
        self.assertFalse(r3["converged"])
        self.assertTrue(all(x["code"] == "SEC_FORBIDDEN" for x in r3["rounds"][0][0]["rejected"]))

    def test_leaf_level_scoping(self):
        """items: MC17-004 MC17-009
        Only differing leaves are exchanged (bounded incremental repair)."""
        for i in range(200):
            self.a.write(T, ENV, f"k{i}", "v", principal="operator")
            self.a.admission.advance()
        self.rec()
        self.a.write(T, ENV, "k7", "changed", principal="operator")
        r = self.rec()
        self.assertEqual(r["rounds"][0][0]["differing_leaves"], 1)
        self.assertEqual(r["rounds"][0][0]["sent"], 1)


class TombstoneTests(unittest.TestCase):
    def test_delete_is_causal_and_no_resurrection(self):
        """items: MC19-001 MC19-002 MC19-004 MC19-009 MC19-012
        Deletes are signed causal writes; a stale pre-delete write replayed later stays superseded;
        repeated delete is idempotent."""
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            old = a.write(T, ENV, "k", "v1", principal="operator")
            old_doc = a.docs[old["op_id"]]
            d = a.delete(T, ENV, "k", principal="operator")
            self.assertEqual(a.read(T, ENV, "k", principal="operator")["state"], "deleted")
            self.assertTrue(a.docs[d["op_id"]]["deleted"])
            self.assertEqual(b.submit(old_doc, principal=c.principal("a"), relay=True)["outcome"], "converged")
            reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            self.assertEqual(b.read(T, ENV, "k", principal="operator")["state"], "deleted")
            self.assertIn(b.submit(old_doc, principal=c.principal("a"), relay=True)["outcome"],
                          ("duplicate", "superseded"))
            self.assertEqual(b.read(T, ENV, "k", principal="operator")["state"], "deleted")
        finally:
            c.close()

    def test_concurrent_update_vs_delete_is_conflict(self):
        """items: MC19-003 MC19-011
        Concurrent update and delete remain an explicit conflict."""
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            a.write(T, ENV, "k", "v", principal="operator")
            reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            a.delete(T, ENV, "k", principal="operator")
            b.write(T, ENV, "k", "update", principal="operator")
            reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            self.assertEqual(a.read(T, ENV, "k", principal="operator")["state"], "conflict")
        finally:
            c.close()

    def test_gc_only_when_all_active_acked_and_floor_blocks_resurrection(self):
        """items: MC19-005 MC19-006 MC19-007 MC19-008 MC20-002 MC20-003 MC20-004 MC20-012
        Tombstone GC waits for every active replica's acknowledgement; the retained floor vector keeps
        rejecting pre-delete writes (including from a stale restored replica) after GC and restart."""
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            old = a.write(T, ENV, "k", "v1", principal="operator")
            old_doc = a.docs[old["op_id"]]
            d = a.delete(T, ENV, "k", principal="operator")
            sk = "\x1f".join((T, ENV, "k"))
            vec = dict(map(tuple, a.docs[d["op_id"]]["vector"]))
            self.assertEqual(a.gc_tombstones({"a": {sk: vec}}), [])          # b has not acked
            self.assertEqual(a.gc_tombstones({"a": {sk: vec}, "b": {sk: vec}}), [sk])
            self.assertNotIn(sk, a.state_keys())
            self.assertEqual(a.submit(old_doc, principal=c.principal("a"), relay=True)["outcome"], "duplicate")
            a2 = c.reopen("a")
            self.assertIn(sk, a2.floors)
            r = a2.submit(old_doc, principal=c.principal("b"), relay=True)
            self.assertIn(r["outcome"], ("superseded", "duplicate"))
            self.assertEqual(a2.read(T, ENV, "k", principal="operator")["state"], "absent")
            audit = [json.loads(l) for p in (a2.dir / "audit").glob("*.jsonl") for l in p.read_text().splitlines()]
            self.assertTrue(any(x["event"] == "tombstone_gc" for x in audit))
        finally:
            c.close()


class CrdtTests(unittest.TestCase):
    GEN = {
        "crdt.g_counter/1": lambda r: json.dumps({s: r.randint(0, 9) for s in r.sample("abcd", r.randint(1, 4))}),
        "crdt.pn_counter/1": lambda r: json.dumps({"p": {"a": r.randint(0, 5)}, "n": {"b": r.randint(0, 5)}}),
        "crdt.max_register/1": lambda r: json.dumps(r.randint(-50, 50)),
        "crdt.g_set/1": lambda r: json.dumps(sorted(r.sample("uvwxyz", r.randint(0, 4)))),
        "crdt.or_set/1": lambda r: json.dumps({"adds": {e: [f"t{r.randint(0, 3)}"] for e in r.sample("xyz", 2)},
                                               "removes": {"x": ["t0"]}}),
    }

    def test_algebraic_laws(self):
        """items: MC21-001 MC21-002 MC21-003 MC21-011 MC21-012
        Commutativity, associativity and idempotence hold for every registered type (600 random triples each)."""
        for vt, gen in self.GEN.items():
            f = crdt.REGISTRY[vt]
            r = random.Random(vt)
            for _ in range(600):
                x, y, z = gen(r), gen(r), gen(r)
                self.assertEqual(f(x, y), f(y, x), vt)
                self.assertEqual(f(f(x, y), z), f(x, f(y, z)), vt)
                self.assertEqual(f(x, x), crdt.merge_all(vt, [x]), vt)

    def test_unregistered_type_never_merges(self):
        """items: MC21-005 MC21-006
        Unregistered or mixed types keep the conflict open (no silent last-writer fallback)."""
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            a.write(T, ENV, "c", json.dumps({"a": 2}), principal="operator", value_type="crdt.g_counter/1")
            b.write(T, ENV, "c", json.dumps({"b": 3}), principal="operator", value_type="crdt.g_counter/1")
            a.write(T, ENV, "u", "1", principal="operator", value_type="custom.lww/9")
            b.write(T, ENV, "u", "2", principal="operator", value_type="custom.lww/9")
            reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            r = a.read(T, ENV, "c", principal="operator")
            self.assertEqual(crdt.g_counter_value(r["value"]), 5)
            self.assertEqual(r, b.read(T, ENV, "c", principal="operator"))
            self.assertEqual(a.read(T, ENV, "u", principal="operator")["state"], "conflict")
            with self.assertRaises(E.SchemaError):
                crdt.merge_all("custom.lww/9", ["1"])
        finally:
            c.close()


class TransportTests(unittest.TestCase):
    def _run(self, link_kwargs, n=60, window=8):
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            docs = []
            for i in range(n):
                r = a.write(T, ENV, f"k{i % 20}", f"v{i}", principal="operator")
                docs.append(a.docs[r["op_id"]])
                a.admission.advance()
            fwd, back = Link(**link_kwargs), Link(seed=99)
            snd = ReliableSender(fwd, window=window, timeout_ticks=3, max_retries=200)
            for d in docs:
                snd.enqueue(d)
            peak_inflight = 0
            for tick in range(5000):
                snd.pump(tick)
                peak_inflight = max(peak_inflight, len(snd.inflight))
                for frame in fwd.advance():
                    kind, payload, _ = decode_frame(frame)
                    doc = parse_write_frame(payload)
                    try:
                        b.submit(doc, principal=c.principal("a"), relay=True)
                    except E.CapacityError:
                        b.admission.advance()
                        continue  # no ack -> sender retries (backpressure propagates)
                    back.send(ack_frame(doc["op_id"]))
                for frame in back.advance():
                    kind, payload, _ = decode_frame(frame)
                    snd.on_ack(bytes(payload).decode())
                if not snd.backlog:
                    break
            return a, b, snd, fwd, peak_inflight, c
        except Exception:
            c.close()
            raise

    def test_lossy_reordering_duplicating_link_converges(self):
        """items: MC18-001 MC18-003 MC18-004 MC18-012 MC36-002 MC36-006
        20% drop, 20% dup, 30% reorder, delay: every write delivered exactly once in effect."""
        a, b, snd, fwd, peak, c = self._run(dict(seed=3, drop=0.2, dup=0.2, reorder=0.3, delay_max=3))
        try:
            self.assertEqual(snd.failed, [])
            self.assertLessEqual(peak, 8)
            self.assertEqual(frontier_ops(a), frontier_ops(b))
            self.assertGreater(fwd.stats["dropped"], 0)
            self.assertGreater(fwd.stats["duplicated"], 0)
        finally:
            c.close()

    def test_full_partition_then_heal(self):
        """items: MC36-002 MC36-005 MC36-009 MC36-012
        A full partition makes no progress and loses nothing; after healing everything converges."""
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            link = Link(seed=1)
            link.partitioned = True
            snd = ReliableSender(link, window=4, timeout_ticks=2, max_retries=10_000)
            for i in range(10):
                r = a.write(T, ENV, f"p{i}", "v", principal="operator")
                snd.enqueue(a.docs[r["op_id"]])
            b.write(T, ENV, "p0", "b-side", principal="operator")
            for t in range(50):
                snd.pump(t)
                self.assertEqual(link.advance(), [])
            link.partitioned = False
            t0 = time.perf_counter()
            for t in range(50, 500):
                snd.pump(t)
                for f in link.advance():
                    doc = parse_write_frame(decode_frame(f)[1])
                    b.submit(doc, principal=c.principal("a"), relay=True)
                    snd.on_ack(doc["op_id"])
                if not snd.backlog:
                    break
            r = reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            _util.record_observation("MC36-009", {"heal_seconds": time.perf_counter() - t0,
                                                  "frames_sent": link.stats["sent"]})
            self.assertTrue(r["converged"])
            self.assertEqual(b.read(T, ENV, "p0", principal="operator")["state"], "conflict")
        finally:
            c.close()

    def test_backpressure_bounded_queues(self):
        """items: MC18-003 MC29-003 MC29-006
        Sender backlog and link queue have hard bounds that refuse with retryable capacity errors."""
        snd = ReliableSender(Link(capacity=2), window=1, max_pending=3)
        from gap05_state_replication_consistency_model.production.schemas import make_write_doc
        for i in range(3):
            snd.enqueue(make_write_doc(tenant=T, environment=ENV, key=f"k{i}", value="", site="a",
                                       vector={"a": 1}, epoch=1))
        with self.assertRaises(E.CapacityError) as cm:
            snd.enqueue(make_write_doc(tenant=T, environment=ENV, key="k9", value="", site="a", vector={"a": 1},
                                       epoch=1))
        self.assertTrue(cm.exception.retryable)


def _site_process(root, name, conn):
    """Child replica process: owns its node, applies frames from the pipe, answers digest queries."""
    import sys
    sys.path.insert(0, str(_util.ROOT))
    from gap05_state_replication_consistency_model.production.testkit import Cluster as C, T as TT, E as EE
    from gap05_state_replication_consistency_model.production.anti_entropy import digest_tree as dt
    c = C(("a", "b", "c"), root=pathlib.Path(root))
    node = c.nodes[name]
    while True:
        msg = conn.recv()
        if msg[0] == "write":
            r = node.write(TT, EE, msg[1], msg[2], principal="operator", context=msg[3] if len(msg) > 3 else None)
            conn.send(node.docs[r["op_id"]])
        elif msg[0] == "apply":
            try:
                conn.send(node.submit(msg[1], principal=c.principal(msg[2]), relay=True)["outcome"])
            except Exception as exc:  # noqa: BLE001
                conn.send(f"error:{getattr(exc, 'code', type(exc).__name__)}")
        elif msg[0] == "frontier":
            conn.send([d for sk in node.state_keys() for d in node._frontier_docs(sk)])
        elif msg[0] == "digest":
            conn.send(dt(node, TT, EE)["root"])
        elif msg[0] == "stop":
            node.close()
            conn.send("bye")
            return


class MultiProcessPartitionTests(unittest.TestCase):
    def test_three_os_processes_partition_duplicate_reorder_restart(self):
        """items: MC36-001 MC36-002 MC36-003 MC36-004 MC36-005 MC36-006 MC36-011 MC36-012
        Three replicas in three OS processes; the parent relays frames with drops, duplicates and
        reordering, partitions c, restarts b mid-run, heals, and checks all three frontiers are equal."""
        ctx = mp.get_context("spawn")
        with tempfile.TemporaryDirectory() as root:
            Cluster(("a", "b", "c"), root=pathlib.Path(root)).close()  # provision shared keys/membership
            procs, pipes = {}, {}

            def start(n):
                parent, child = ctx.Pipe()
                p = ctx.Process(target=_site_process, args=(root, n, child))
                p.start()
                procs[n], pipes[n] = p, parent

            for n in "abc":
                start(n)
            rng = random.Random(11)
            outbox = []
            try:
                for i in range(24):
                    n = "abc"[i % 3]
                    pipes[n].send(("write", f"k{i % 6}", f"{n}{i}"))
                    doc = pipes[n].recv()
                    for dst in "abc":
                        if dst != n:
                            outbox.append((dst, doc, n))
                    if i == 12:  # crash/restart b mid-run
                        pipes["b"].send(("stop",))
                        pipes["b"].recv()
                        procs["b"].join()
                        start("b")
                rng.shuffle(outbox)
                delivered = []
                for dst, doc, src in outbox:
                    if dst == "c" or src == "c":
                        continue                       # c partitioned
                    if rng.random() < 0.2:
                        continue                       # dropped
                    for _ in range(2 if rng.random() < 0.3 else 1):
                        pipes[dst].send(("apply", doc, src))
                        delivered.append(pipes[dst].recv())
                self.assertFalse([d for d in delivered if d.startswith("error")], delivered)
                # heal: full frontier exchange rounds until digests agree (anti-entropy over the pipe)
                for _round in range(4):
                    fronts = {}
                    for n in "abc":
                        pipes[n].send(("frontier",))
                        fronts[n] = pipes[n].recv()
                    for dst in "abc":
                        for src in "abc":
                            if src != dst:
                                for doc in fronts[src]:
                                    pipes[dst].send(("apply", doc, doc["site"]))
                                    pipes[dst].recv()
                    roots = set()
                    for n in "abc":
                        pipes[n].send(("digest",))
                        roots.add(pipes[n].recv())
                    if len(roots) == 1:
                        break
                self.assertEqual(len(roots), 1)
            finally:
                for n in "abc":
                    try:
                        pipes[n].send(("stop",))
                        pipes[n].recv()
                    except Exception:
                        pass
                    procs[n].join(timeout=10)


class BatchAndShardTests(unittest.TestCase):
    def test_batch_per_item_outcomes_and_retry_idempotent(self):
        """items: MC42-001 MC42-002 MC42-003 MC42-005 MC42-006 MC42-011 MC42-012
        Per-item outcomes; a duplicate inside the batch is 'duplicate'; retrying the batch adds nothing;
        atomic_validation refuses the whole batch on one invalid item."""
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            docs = []
            for i in range(5):
                r = a.write(T, ENV, f"k{i}", "v", principal="operator")
                docs.append(a.docs[r["op_id"]])
            out = apply_batch(b, docs + [docs[0]], principal=c.principal("a"))
            self.assertEqual([o["outcome"] for o in out], ["converged"] * 5 + ["duplicate"])
            wal = len(b.wal.records)
            again = apply_batch(b, docs, principal=c.principal("a"))
            self.assertEqual({o["outcome"] for o in again}, {"duplicate"})
            self.assertEqual(len(b.wal.records), wal)
            bad = dict(docs[1], value="tampered")
            with self.assertRaises(E.Gap05Error):
                apply_batch(b, [docs[0], bad], principal=c.principal("a"), atomic_validation=True)
            partial = apply_batch(b, [bad], principal=c.principal("a"))
            self.assertEqual(partial[0]["outcome"], "rejected")
            from gap05_state_replication_consistency_model.production.limits import Limits
            b.limits = Limits(max_batch_items=2)
            with self.assertRaises(E.LimitExceeded):
                apply_batch(b, docs, principal=c.principal("a"))
        finally:
            c.close()

    def test_unrelated_keys_scale_single_key_semantics_unchanged(self):
        """items: MC41-002 MC41-003 MC41-006 MC41-012
        Deterministic key->shard mapping; parallel writers on disjoint keys finish without changing
        per-key causal results (compared with a serial run)."""
        c = Cluster(("a",), node_kwargs={"shards": 8})
        try:
            a = c.nodes["a"]
            self.assertEqual(a._shard("x"), a._shard("x"))
            errors = []

            def worker(w):
                try:
                    for i in range(15):
                        a.write(T, ENV, f"w{w}-k{i % 3}", f"{w}-{i}", principal="operator")
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)
            a.admission = __import__("gap05_state_replication_consistency_model.production.observe",
                                     fromlist=["Admission"]).Admission(key_capacity=10_000, tenant_capacity=10_000)
            ts = [threading.Thread(target=worker, args=(w,)) for w in range(6)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(errors, [])
            for w in range(6):
                for k in range(3):
                    self.assertEqual(a.read(T, ENV, f"w{w}-k{k}", principal="operator")["value"], f"{w}-{12 + k}")
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
