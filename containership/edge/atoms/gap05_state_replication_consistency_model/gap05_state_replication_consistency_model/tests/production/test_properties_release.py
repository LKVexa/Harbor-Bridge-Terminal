import json
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest

import _util
from gap05_state_replication_consistency_model import model as core
from gap05_state_replication_consistency_model.model import ReplicatedKey, Write, dominates
from gap05_state_replication_consistency_model.production import modelcheck

PKG = pathlib.Path(__file__).resolve().parents[2]


def random_history(rng, sites, n_writes):
    """Causally consistent random history: each new write's context is a random earlier write's
    vector (or empty) plus an increment of its author's own counter."""
    writes, own = [], {s: 0 for s in sites}
    for i in range(n_writes):
        s = rng.choice(sites)
        ctx = dict(rng.choice(writes).vector) if writes and rng.random() < 0.6 else {}
        own[s] = max(own[s], ctx.get(s, 0)) + 1
        ctx[s] = own[s]
        writes.append(Write("k", f"{s}{i}", s, tuple(sorted(ctx.items()))))
    return writes


class PropertyTests(unittest.TestCase):
    SEEDS = range(40)

    def test_convergence_maximality_replay(self):
        """items: MC34-001 MC34-002 MC34-003 MC34-004 MC34-005 MC34-007 MC34-011
        40 seeds x random histories (3-5 sites, up to 14 writes, bounds 1-4) x 12 shuffled delivery
        orders with duplicates: identical final partition, antichain frontier, nothing silently lost."""
        for seed in self.SEEDS:
            rng = random.Random(seed)
            sites = "abcde"[: rng.randint(3, 5)]
            hist = random_history(rng, sites, rng.randint(4, 14))
            bound = rng.randint(1, 4)
            finals = set()
            for _ in range(12):
                order = hist[:] + rng.sample(hist, k=min(3, len(hist)))
                rng.shuffle(order)
                rk = ReplicatedKey("k", frozenset(sites), max_siblings=bound)
                for w in order:
                    rk.apply(w)
                fr = rk.siblings + [e["write"] for e in rk.quarantine]
                for x in fr:
                    for y in fr:
                        self.assertFalse(x is not y and dominates(x.vector_map(), y.vector_map()), seed)
                for w in hist:
                    self.assertTrue(w in fr or any(dominates(f.vector_map(), w.vector_map()) for f in fr), seed)
                finals.add((tuple(w.identity() for w in rk.siblings),
                            tuple(e["write"].identity() for e in rk.quarantine)))
            self.assertEqual(len(finals), 1, f"seed {seed} diverged")

    def test_resolution_dominates_all(self):
        """items: MC34-008 MC48-003
        After resolve() the winner dominates every write in every random history."""
        for seed in self.SEEDS:
            rng = random.Random(1000 + seed)
            hist = random_history(rng, "abcd", 10)
            rk = ReplicatedKey("k", frozenset("abcd"), max_siblings=rng.randint(1, 3))
            for w in hist:
                rk.apply(w)
            win = rk.resolve("R", "a")
            for w in hist:
                self.assertTrue(dominates(win.vector_map(), w.vector_map()))

    def test_node_level_random_multi_replica(self):
        """items: MC34-009 MC34-001 MC36-004
        Node-level property: random interleavings of local writes, deletes, CRDT writes and pairwise
        anti-entropy across 3 replicas always end in identical frontiers."""
        from gap05_state_replication_consistency_model.production.anti_entropy import reconcile
        from gap05_state_replication_consistency_model.production.observe import Admission
        from gap05_state_replication_consistency_model.production.testkit import Cluster, E, T
        for seed in range(6):
            rng = random.Random(seed)
            c = Cluster(("a", "b", "c"))
            try:
                for n in c.nodes.values():
                    n.admission = Admission(key_capacity=10_000)
                for step in range(40):
                    n = c.nodes[rng.choice("abc")]
                    k = f"k{rng.randint(0, 4)}"
                    op = rng.random()
                    try:
                        if op < 0.6:
                            n.write(T, E, k, f"{n.name}{step}", principal="operator")
                        elif op < 0.75:
                            n.delete(T, E, k, principal="operator")
                        elif op < 0.9:
                            x, y = rng.sample("abc", 2)
                            reconcile(c.nodes[x], c.nodes[y], T, E, principal_a=c.principal(x),
                                      principal_b=c.principal(y))
                        else:
                            n.resolve(T, E, k, "R", principal="operator")
                    except Exception as exc:  # noqa: BLE001
                        if getattr(exc, "code", "") not in ("CORR_CONFLICT_OPEN", "CORR_NOTHING_TO_RESOLVE"):
                            raise
                for _ in range(2):
                    for x, y in (("a", "b"), ("b", "c"), ("a", "c")):
                        reconcile(c.nodes[x], c.nodes[y], T, E, principal_a=c.principal(x),
                                  principal_b=c.principal(y))
                fronts = [{sk: sorted(d["op_id"] for d in n._frontier_docs(sk)) for sk in n.state_keys()}
                          for n in c.nodes.values()]
                self.assertEqual(fronts[0], fronts[1], seed)
                self.assertEqual(fronts[1], fronts[2], seed)
            finally:
                c.close()


class ModelCheckTests(unittest.TestCase):
    def test_exhaustive_bounded_invariants(self):
        """items: MC48-001 MC48-002 MC48-003 MC48-004 MC48-006 MC48-007 MC34-012
        Every delivery order of the bounded scenarios satisfies INV-CONV/MAX/COVER/BOUND/DUP/RES/FENCE."""
        res = modelcheck.run_all()
        self.assertTrue(res["ok"], {k: v.get("violations", [])[:3] for k, v in res.items() if isinstance(v, dict)})
        self.assertEqual(res["3sites_depth2_bound2"]["orders"], 720)

    def test_checker_catches_injected_bug(self):
        """items: MC48-008 MC48-011
        Mutation check: reverting the v4.2.0 fix (arrival-order overflow) makes INV-CONV fail, proving
        the checker can detect the historical defect."""
        original = core._write_sort_key
        try:
            core._write_sort_key = lambda w: 0   # stable sort -> arrival order decides overflow
            res = modelcheck.check(modelcheck.scenario_writes(depth=1), "abc", 1)
            self.assertFalse(res["ok"])
            self.assertIn("INV-CONV", {v[0] for v in res["violations"]})
        finally:
            core._write_sort_key = original

    def test_tla_spec_shipped_not_claimed(self):
        """items: MC48-009 MC48-010
        The TLA+ spec ships beside the code and states plainly that TLC has not been run."""
        text = (PKG / "spec" / "GAP05.tla").read_text()
        self.assertIn("NOT_RUN", text)
        self.assertIn("Antichain", text)


class ReleaseTests(unittest.TestCase):
    def test_version_consistency(self):
        """items: MC49-001 MC49-009 MC40-011
        VERSION, __init__, pyproject, CHANGELOG head and compatibility matrix agree."""
        import gap05_state_replication_consistency_model as pkg
        v = (PKG / "VERSION").read_text().strip()
        self.assertEqual(pkg.__version__, v)
        self.assertIn(f'version = "{v}"', (PKG / "pyproject.toml").read_text())
        self.assertIn(f"## {v}", (PKG / "CHANGELOG.md").read_text().split("\n## ")[0] + "\n## " +
                      (PKG / "CHANGELOG.md").read_text().split("\n## ")[1])
        compat = json.loads((PKG / "COMPATIBILITY.json").read_text())
        self.assertEqual(compat["release"], v)

    def test_compat_matrix_runtime_check(self):
        """items: MC40-001 MC40-002 MC40-004 MC40-006 MC40-007
        The machine-readable matrix names this runtime's cell; its schema versions equal the code's."""
        from gap05_state_replication_consistency_model.production.schemas import SUPPORTED
        compat = json.loads((PKG / "COMPATIBILITY.json").read_text())
        cell = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.assertIn(cell, compat["python"])
        self.assertIn(compat["python"][cell], ("tested", "supported"))
        self.assertEqual({k: list(v) for k, v in SUPPORTED.items()}, compat["wire_schemas"])
        import cryptography
        self.assertIn(cryptography.__version__, compat["crypto_provider"]["cryptography"]["tested"])

    def test_sbom_and_checksums(self):
        """items: MC49-004 MC49-008 MC49-012
        SBOM lists the one runtime dependency; SHA256SUMS covers every shipped file and matches."""
        import hashlib
        sbom = json.loads((PKG / "sbom.cdx.json").read_text())
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual({c["name"] for c in sbom["components"]}, {"cryptography"})
        sums = dict(reversed(l.split("  ", 1)) for l in (PKG / "SHA256SUMS.txt").read_text().splitlines())
        for rel, h in sums.items():
            self.assertEqual(hashlib.sha256((PKG / rel).read_bytes()).hexdigest(), h, rel)
        for must in ("schemas/PK_REPLICATED_WRITE_v1.schema.json", "production/node.py", "spec/GAP05.tla",
                     "RUNBOOKS.md", "THIRD-PARTY-NOTICES.md"):
            self.assertIn(must, sums)

    def test_evidence_reference_check(self):
        """items: MC50-003 MC50-007 MC50-008 MC50-010 MC49-007
        CI check fails when docs reference an absent evidence artifact without a waiver; MASTER.md is
        recorded as an evidence gap and is NOT reconstructed."""
        self.assertFalse((PKG / "MASTER.md").exists())
        p = subprocess.run([sys.executable, str(PKG / "tools" / "check_evidence_refs.py"), str(PKG)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "README.md").write_text("See `GHOST.md` for the carried evidence.\n")
            p = subprocess.run([sys.executable, str(PKG / "tools" / "check_evidence_refs.py"), d],
                               capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)

    def test_cli_read_only_tools(self):
        """items: MC45-008 MC05-010 MC24-010 MC10-007
        The admin CLI inspects durable state offline without modifying it (bytes unchanged)."""
        from gap05_state_replication_consistency_model.production.testkit import Cluster, E, T
        from gap05_state_replication_consistency_model.production import cli
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            a.write(T, E, "k", "1", principal="operator")
            b.write(T, E, "k", "2", principal="operator")
            from gap05_state_replication_consistency_model.production.anti_entropy import reconcile
            reconcile(a, b, T, E, principal_a=c.principal("a"), principal_b=c.principal("b"))
            before = {p: p.read_bytes() for p in a.dir.rglob("*") if p.is_file()}
            res = cli.inspect(a.dir, only_open=True)
            self.assertEqual(list(res["keys"].values())[0]["active"], 2)
            head = pathlib.Path(c.root / "head.json")
            head.write_text(json.dumps(a.audit.signed_head()))
            from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
            pub = c.keys["a"].private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
            self.assertEqual(cli.main(["verify-audit", str(a.dir / "audit"), "--pub", pub, "--head", str(head)]), 0)
            after = {p: p.read_bytes() for p in a.dir.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
        finally:
            c.close()

    def test_bench_and_proposed_gates(self):
        """items: MC39-002 MC39-003 MC39-004 MC39-007 MC39-008 MC39-010 MC46-004 MC46-008 MC43-009
        Quick benchmark run records platform, latency percentiles, throughput, recovery rate, and
        evaluates PROPOSED gates without converting them into certified passes."""
        from gap05_state_replication_consistency_model.production import bench
        res = bench.run_all(quick=True)
        for k in ("platform", "core_apply_p99_ms", "node_write_p99_ms", "node_burst_writes_per_s",
                  "recovery_records_per_s", "soak_peak_mib", "quarantine_depth"):
            self.assertIn(k, res)
        self.assertTrue(all(g["status"] in ("met_under_proposed_target", "missed", "not_measured")
                            for g in res["gates"].values()))
        _util.record_observation("MC39-002", {k: v for k, v in res.items() if k != "gates"})


if __name__ == "__main__":
    unittest.main()
