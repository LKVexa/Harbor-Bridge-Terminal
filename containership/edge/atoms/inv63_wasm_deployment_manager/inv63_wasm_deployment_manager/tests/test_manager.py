"""Unit tests for the self-contained INV-63 reconciliation engine."""
import importlib
import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)
Manager = pkg.Manager
DesiredState = pkg.DesiredState


class ManagerTest(unittest.TestCase):
    def test_deterministic_spread_and_idempotent_reconcile(self):
        m = Manager({"h1": "z1", "h2": "z1", "h3": "z2", "h4": "z3"})
        m.set_desired("api", "v1", 3, spread=True)
        first = m.reconcile("api")
        self.assertEqual(first["start"], [
            ("api", "v1", "h1"),
            ("api", "v1", "h3"),
            ("api", "v1", "h4"),
        ])
        self.assertEqual({m.hosts[h] for _, _, h in m.actual}, {"z1", "z2", "z3"})
        second = m.reconcile("api")
        self.assertEqual(second, {"start": [], "stop": []})
        self.assertTrue(m.verify_audit_chain())

    def test_rollout_respects_bound_and_preserves_unrelated_workloads(self):
        m = Manager(
            {"h1": "z1", "h2": "z2", "h3": "z3", "h4": "z4"},
            [
                ("api", "v1", "h1"),
                ("api", "v1", "h2"),
                ("api", "v1", "h3"),
                ("worker", "v7", "h4"),
            ],
        )
        batches, worst = m.rollout("api", "v2", max_unavailable=2)
        self.assertEqual((batches, worst), (2, 2))
        self.assertEqual(sum(1 for c, v, _ in m.actual if c == "api" and v == "v2"), 3)
        self.assertIn(("worker", "v7", "h4"), m.actual)
        self.assertTrue(m.verify_audit_chain())

    def test_apply_is_transactional_on_invalid_stop(self):
        original = [("api", "v1", "h1")]
        m = Manager({"h1": "z1"}, original)
        with self.assertRaises(LookupError):
            m.apply({
                "stop": [("api", "v1", "h1"), ("api", "v1", "h1")],
                "start": [("api", "v2", "h1")],
            })
        self.assertEqual(m.actual, original)
        self.assertEqual(m.audit_events, [])

    def test_apply_rejects_unknown_start_host_without_mutation(self):
        m = Manager({"h1": "z1"}, [("api", "v1", "h1")])
        with self.assertRaises(LookupError):
            m.apply({"stop": [], "start": [("api", "v2", "ghost")]})
        self.assertEqual(m.actual, [("api", "v1", "h1")])

    def test_runtime_state_tampering_is_detected(self):
        m = Manager({"h1": "z1"})
        m.actual.append(("api", "v1", "ghost"))
        with self.assertRaises(LookupError):
            m.diff("api", "v1", 1)

    def test_validation_rejects_ambiguous_or_hostile_inputs(self):
        m = Manager({"h1": "z1"})
        bad_calls = [
            lambda: m.diff("api", "v1", -1),
            lambda: m.diff("api", "v1", True),
            lambda: m.diff("api", "v1", 1, spread="yes"),
            lambda: m.diff("", "v1", 1),
            lambda: m.diff("api\ninjected", "v1", 1),
            lambda: m.rollout("api", "v2", 0),
            lambda: m.rollout("api", "v2", True),
            lambda: m.apply({"start": []}),
            lambda: m.apply({"start": [], "stop": [], "extra": []}),
        ]
        for call in bad_calls:
            with self.subTest(call=call):
                with self.assertRaises((ValueError, LookupError)):
                    call()

    def test_nonzero_desired_requires_hosts(self):
        m = Manager({})
        with self.assertRaises(LookupError):
            m.set_desired("api", "v1", 1)
        self.assertEqual(m.diff("api", "v1", 0), {"start": [], "stop": []})


    def test_runtime_state_sequence_is_normalized_before_counter_use(self):
        m = Manager({"h1": "z1"}, [("api", "v1", "h1")])
        m.actual.append(["api", "v1", "h1"])
        m.apply({"stop": [("api", "v1", "h1")], "start": []})
        self.assertEqual(m.actual, [("api", "v1", "h1")])

    def test_direct_desired_state_tampering_is_rejected(self):
        m = Manager({"h1": "z1"})
        m.desired["api"] = {"version": "v1"}
        with self.assertRaises(ValueError):
            m.reconcile("api")

    def test_audit_chain_detects_record_tampering(self):
        from dataclasses import replace

        m = Manager({"h1": "z1"})
        m.set_desired("api", "v1", 1)
        m.reconcile("api")
        self.assertTrue(m.verify_audit_chain())
        m.audit_events[0] = replace(m.audit_events[0], kind="tampered")
        self.assertFalse(m.verify_audit_chain())

    def test_core_engine_survives_optimized_mode_without_pk_core(self):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from %s import Manager; "
            "m=Manager({'h':'z'}); "
            "m.set_desired('api','v1',1); "
            "m.reconcile('api'); "
            "(_ for _ in ()).throw(SystemExit(4)) if m.actual != [('api','v1','h')] else None; "
            "print(m.verify_audit_chain())"
        ) % (str(ROOT), PKG_DIR.name)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "True")


class PlacementEquivalenceTest(unittest.TestCase):
    """INV-63-C066: the heap optimisation must not change semantics."""

    @staticmethod
    def _reference(hosts, retained, count, spread):
        from collections import Counter
        zc = Counter(hosts[h] for h in retained); hc = Counter(retained); out = []
        while len(retained) + len(out) < count:
            if spread:
                h = min(sorted(hosts), key=lambda h: (zc[hosts[h]], hc[h], h))
            else:
                h = min(sorted(hosts), key=lambda h: (hc[h], h))
            zc[hosts[h]] += 1; hc[h] += 1; out.append(h)
        return out

    def test_heap_placement_matches_reference(self):
        import random
        rng = random.Random(66)
        for _ in range(300):
            hosts = {f"h{i}": f"z{rng.randrange(1, 5)}" for i in range(rng.randrange(1, 12))}
            existing = [("api", "v1", rng.choice(sorted(hosts))) for _ in range(rng.randrange(0, 6))]
            count = rng.randrange(0, 20)
            spread = rng.random() < 0.7
            m = Manager(hosts, existing)
            d = m.diff("api", "v1", count, spread)
            retained = [h for _, _, h in existing][:count]
            self.assertEqual([h for _, _, h in d["start"]], self._reference(hosts, retained, count, spread))


class PackageIntegrityTest(unittest.TestCase):
    def test_version_triplet(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")
        changelog = (PKG_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## 4.3.0", changelog)

    def test_checklist_shape(self):
        import json

        checklist = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        self.assertEqual(checklist["element"], "INV-63")
        self.assertEqual(checklist["item_count"], 100)
        self.assertEqual(len(checklist["items"]), 100)
        self.assertEqual(len({x["check_id"] for x in checklist["items"]}), 100)


if __name__ == "__main__":
    unittest.main()
