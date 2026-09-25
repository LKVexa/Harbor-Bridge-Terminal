"""Property and fuzz testing (MC-074).  Deterministic seeds; scale with
INV62_FUZZ_ITERS (default 300; the release gate runs 3000)."""
from __future__ import annotations

import json
import math
import os
import random
import unittest

from support import TENANT, seeded

from inv62_edge_topology import Topology, TopologyError, UnknownNode
from inv62_edge_topology.production import wire

ITERS = int(os.environ.get("INV62_FUZZ_ITERS", "300"))


def random_topology(rng: random.Random) -> Topology:
    t = Topology()
    t.add("c", "cloud", caps=["x"] if rng.random() < 0.5 else [])
    regions = [f"r{i}" for i in range(rng.randint(1, 3))]
    for r in regions:
        t.add(r, "region", parent="c", caps=["x"] if rng.random() < 0.2 else [])
    names = ["c"] + regions
    for s in range(rng.randint(1, 3)):
        gw = f"s{s}-gw"
        t.add(gw, "site", f"s{s}", ["coordinator"] if rng.random() < 0.7 else [], parent=rng.choice(regions))
        names.append(gw)
        for d in range(rng.randint(0, 4)):
            n = f"s{s}-d{d}"
            t.add(n, "device", f"s{s}", ["x"] if rng.random() < 0.3 else [], parent=gw)
            names.append(n)
    for _ in range(rng.randint(0, len(names) * 2)):
        a, b = rng.sample(names, 2)
        t.connect(a, b, round(rng.uniform(0, 100), 3), rng.random() < 0.85)
    return t


def floyd(t: Topology) -> dict[tuple[str, str], float]:
    names = list(t.nodes)
    d = {(a, b): (0.0 if a == b else math.inf) for a in names for b in names}
    for pair, link in t.links.items():
        if link.up:
            a, b = tuple(pair)
            d[a, b] = d[b, a] = min(d[a, b], link.latency_ms)
    for k in names:
        for i in names:
            for j in names:
                if d[i, k] + d[k, j] < d[i, j]:
                    d[i, j] = d[i, k] + d[k, j]
    return d


class GraphPropertyTest(unittest.TestCase):
    def test_routing_matches_reference_and_never_uses_down_links(self):
        for seed in range(max(20, ITERS // 10)):
            rng = random.Random(seed)
            t = random_topology(rng)
            ref = floyd(t)
            for origin in t.nodes:
                dist = t.distances(origin)
                for target in t.nodes:
                    expect = ref[origin, target]
                    got = dist.get(target)
                    if math.isinf(expect):
                        self.assertIsNone(got, (seed, origin, target))
                        self.assertIsNone(t.distance(origin, target))
                    else:
                        self.assertAlmostEqual(got, expect, places=6)
                node, lat = t.nearest(origin, "x")
                capable = [(ref[origin, n], n) for n in t.nodes if "x" in t.nodes[n].caps and not math.isinf(ref[origin, n])]
                if capable:
                    best = min(capable)
                    self.assertAlmostEqual(lat, best[0], places=6)
                    self.assertAlmostEqual(ref[origin, node], best[0], places=6)
                else:
                    self.assertEqual((node, lat), (None, None))

    def test_random_mutation_sequences_preserve_invariants(self):
        rng = random.Random(1234)
        for _ in range(ITERS):
            t = random_topology(rng)
            names = list(t.nodes)
            for _ in range(20):
                op = rng.randrange(4)
                try:
                    if op == 0:
                        t.remove(rng.choice(names))
                    elif op == 1:
                        a, b = rng.sample(names, 2)
                        t.connect(a, b, rng.choice([1, -1, math.nan, 5.5, "x", True]))
                    elif op == 2:
                        a, b = rng.sample(names, 2)
                        t.set_link_state(a, b, rng.random() < 0.5)
                    else:
                        t.add(rng.choice(["q", "c", "s0-gw", "zz"]), rng.choice(["device", "site", "cloud"]),
                              rng.choice([None, "s0", "s9"]))
                except (TopologyError, UnknownNode, LookupError):
                    pass
            for n in t.nodes.values():
                if n.tier != "cloud":
                    self.assertIn(n.parent, t.nodes)
            for pair, link in t.links.items():
                self.assertTrue(pair <= set(t.nodes))
                self.assertTrue(math.isfinite(link.latency_ms) and link.latency_ms >= 0)
            adj_pairs = {frozenset((a, b)) for a, nb in t._adj.items() for b in nb}
            self.assertEqual(adj_pairs, set(t.links))
            self.assertEqual(Topology.from_snapshot(t.snapshot()).snapshot(), t.snapshot())


class WireFuzzTest(unittest.TestCase):
    def test_mutated_requests_never_cause_internal_errors(self):
        svc, feed = seeded()
        rng = random.Random(99)
        base = {"protocol": "PK_TOPO_NEAREST/1", "op": "resolve", "tenant": TENANT, "request_id": "req-fuzz0001",
                "credential": svc.authn.issue("s", "scheduler", [TENANT], lifetime_s=900),
                "body": {"origin": "s1-d1", "capability": "gpu", "constraints": {"residency": ["eu"]}}}
        raw = wire.encode(base)
        seen = set()
        for i in range(ITERS * 3):
            b = bytearray(raw)
            for _ in range(rng.randint(1, 6)):
                kind = rng.randrange(3)
                pos = rng.randrange(len(b))
                if kind == 0:
                    b[pos] = rng.randrange(256)
                elif kind == 1:
                    del b[pos]
                else:
                    b.insert(pos, rng.choice(b'{}[]",:0-9aeE\\\x00'))
            resp = json.loads(svc.handle(bytes(b)))
            wire.validate_response(resp)
            c = resp.get("error", {}).get("code")
            self.assertNotEqual(c, "TOPO.INTERNAL", bytes(b)[:200])
            seen.add(c)
        self.assertIn("TOPO.INVALID_REQUEST", seen)

    def test_structured_body_fuzz(self):
        svc, feed = seeded()
        rng = random.Random(7)
        values = [None, True, 0, -1, 1e308, "", "x" * 200, "s1-d1", [], {}, ["eu"] * 20, {"a": 1}, 3.5]
        keys = ["origin", "capability", "constraints", "explain", "mutations", "site", "candidate", "fencing_token",
                "residency", "max_latency_ms", "exclude", "zzz"]
        for i in range(ITERS):
            fam, op = rng.choice([("PK_TOPO_NEAREST/1", "resolve"), ("PK_TOPO_GRAPH/1", "apply"),
                                  ("PK_TOPO_PARTITION/1", "status"), ("PK_TOPO_PARTITION/1", "acquire")])
            body = {rng.choice(keys): rng.choice(values) for _ in range(rng.randint(0, 4))}
            role = {"resolve": "scheduler", "apply": "topology-feed", "status": "scheduler", "acquire": "node-agent"}[op]
            env = {"protocol": fam, "op": op, "tenant": TENANT, "request_id": f"req-{i:08d}",
                   "credential": svc.authn.issue("s", role, [TENANT], node="s1-gw"), "body": body}
            resp = json.loads(svc.handle(wire.encode(env)))
            self.assertNotEqual(resp.get("error", {}).get("code"), "TOPO.INTERNAL", env)


if __name__ == "__main__":
    unittest.main()
