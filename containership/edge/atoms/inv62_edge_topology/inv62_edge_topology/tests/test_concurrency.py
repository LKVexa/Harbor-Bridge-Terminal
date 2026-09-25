"""Concurrency/race tests (MC-075).  The service serialises mutations behind
one lock and commits whole candidate graphs, so readers never observe a
partially-applied batch."""
from __future__ import annotations

import threading
import unittest

from support import TENANT, client, seeded

from inv62_edge_topology.production import errors


class ConcurrencyTest(unittest.TestCase):
    def test_parallel_writers_and_readers(self):
        svc, feed = seeded()
        errs: list = []
        partial: list = []

        def writer(w):
            f = client(svc, "topology-feed")
            for i in range(40):
                name = f"s1-w{w}-{i}"
                try:
                    f.apply([{"kind": "add_node", "node": name, "tier": "device", "site": "s1", "parent": "s1-gw",
                              "caps": ["gpu"], "residency": "eu"},
                             {"kind": "connect", "a": "s1-gw", "b": name, "latency_ms": 0.1}])
                except Exception as exc:  # pragma: no cover - reported below
                    errs.append(exc)

        def reader():
            s = client(svc, "scheduler")
            for _ in range(80):
                try:
                    snap = client(svc, "topology-feed").get()["result"]
                    dev = {n for n, m in snap["nodes"].items() if "-w" in n}
                    linked = {l["b"] for l in snap["links"] if "-w" in l["b"]}
                    if dev != linked:
                        partial.append(dev ^ linked)
                    s.resolve("s1-d1", "gpu")
                except Exception as exc:  # pragma: no cover
                    errs.append(exc)

        threads = [threading.Thread(target=writer, args=(w,)) for w in range(4)] + \
                  [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errs, [])
        self.assertEqual(partial, [])
        topo = svc.tenants[TENANT].topo
        self.assertEqual(sum(1 for n in topo.nodes if "-w" in n), 160)
        self.assertEqual(topo.revision, 12 + 160 * 2)

    def test_compare_and_set_detects_lost_update(self):
        svc, feed = seeded()
        rev = feed.get()["revision"]
        feed.apply([{"kind": "remove_node", "node": "s1-d2"}], expected_revision=rev)
        with self.assertRaises(errors.TopoError) as cm:
            feed.apply([{"kind": "remove_node", "node": "s1-d1"}], expected_revision=rev)
        self.assertEqual(cm.exception.code, "TOPO.CONFLICT")

    def test_contended_lease_has_single_winner(self):
        svc, feed = seeded()
        feed.apply([{"kind": "set_link_state", "a": "s1-gw", "b": "s1-gw2", "up": True}])
        winners: list = []
        lock = threading.Lock()

        def campaign(node):
            c = client(svc, "node-agent", node=node)
            for _ in range(30):
                try:
                    r = c.acquire("s1", node)["result"]
                    with lock:
                        winners.append((r["holder"], r["term"]))
                except errors.TopoError:
                    pass

        ts = [threading.Thread(target=campaign, args=(n,)) for n in ("s1-gw", "s1-gw2") for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(set(winners), {("s1-gw", 1)})


if __name__ == "__main__":
    unittest.main()
