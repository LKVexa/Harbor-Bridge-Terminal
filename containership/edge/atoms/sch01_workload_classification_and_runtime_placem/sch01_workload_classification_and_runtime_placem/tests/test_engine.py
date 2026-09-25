"""Dependency-independent unit and safety tests for the SCH-01 scheduler engine."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sch01_workload_classification_and_runtime_placem as sch


class EngineTest(unittest.TestCase):
    def test_version_is_4_3_0(self):
        self.assertEqual(sch.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")

    def test_classification_matrix(self):
        expected = {
            "internal": ("trusted", "process"),
            "first-party": ("first-party", "wasm"),
            "partner": ("third-party", "unikernel"),
            "public": ("untrusted", "microvm"),
            "quarantined": ("hostile", "vm"),
        }
        for provenance, (trust, tier) in expected.items():
            with self.subTest(provenance=provenance):
                klass = sch.classify(sch.Workload("w", "t", provenance))
                self.assertEqual((klass["trust_class"], klass["required_tier"]), (trust, tier))

    def test_unknown_provenance_is_structured_refusal(self):
        with self.assertRaises(sch.Unplaceable) as raised:
            sch.classify(sch.Workload("w", "t", "mystery"))
        self.assertEqual(raised.exception.code, "UNKNOWN_PROVENANCE")
        self.assertEqual(raised.exception.as_dict()["schema"], "PK_SCHEDULER_ERROR/1")

    def test_input_validation_fails_closed(self):
        with self.assertRaises(ValueError):
            sch.Workload("", "t", "internal")
        with self.assertRaises(ValueError):
            sch.Workload("w", "", "internal")
        with self.assertRaises(ValueError):
            sch.Workload("w", "t", "internal", needs=frozenset({""}))
        with self.assertRaises(ValueError):
            sch.Workload("w", "t", "internal", needs="gpu")
        with self.assertRaises(ValueError):
            sch.NodeReport("n", "s", frozenset({"unknown"}))
        with self.assertRaises(ValueError):
            sch.NodeReport("n", "s", frozenset({"process"}), capabilities="gpu")
        with self.assertRaises(ValueError):
            sch.NodeReport("n", "s", frozenset({"process"}), free_slots=-1)
        with self.assertRaises(ValueError):
            sch.NodeReport("n", "s", frozenset({"process"}), reported_at=-1)

    def test_mutated_node_state_is_revalidated(self):
        node = sch.NodeReport("n", "s", frozenset({"process"}), free_slots=1)
        node.free_slots = -1
        with self.assertRaises(ValueError):
            sch.place(sch.Workload("w", "t", "internal"), [node])

        node = sch.NodeReport("n", "s", frozenset({"process"}), free_slots=1)
        node.tiers = frozenset({"bogus"})
        with self.assertRaises(ValueError):
            sch.place(sch.Workload("w", "t", "internal"), [node])

    def test_tampered_classification_is_rejected(self):
        workload = sch.Workload("w", "t", "public")
        tampered = sch.classify(workload)
        tampered["trust_class"] = "trusted"
        tampered["required_tier"] = "process"
        node = sch.NodeReport("n", "s", frozenset({"process"}))
        with self.assertRaises(ValueError):
            sch.candidates(workload, tampered, [node], now=0)

    def test_future_report_is_not_fresh(self):
        workload = sch.Workload("w", "t", "internal")
        klass = sch.classify(workload)
        node = sch.NodeReport("n", "s", frozenset({"process"}), reported_at=11)
        self.assertIn("REPORT_FROM_FUTURE", sch.rejection_reasons(workload, klass, node, now=10))
        with self.assertRaises(sch.Unplaceable) as raised:
            sch.place(workload, [node], now=10)
        self.assertIn("REPORT_FROM_FUTURE", raised.exception.details["rejection_counts"])

    def test_stale_thermal_site_hardware_tier_and_tenant_rejections(self):
        workload = sch.Workload("w", "t1", "public", needs=frozenset({"gpu"}), site_affinity="west")
        klass = sch.classify(workload)
        cases = [
            (sch.NodeReport("stale", "west", frozenset({"microvm"}), capabilities=frozenset({"gpu"}), reported_at=0), 31, "STALE_REPORT"),
            (sch.NodeReport("hot", "west", frozenset({"microvm"}), capabilities=frozenset({"gpu"}), thermally_excluded=True), 0, "THERMALLY_EXCLUDED"),
            (sch.NodeReport("site", "east", frozenset({"microvm"}), capabilities=frozenset({"gpu"})), 0, "SITE_MISMATCH"),
            (sch.NodeReport("hw", "west", frozenset({"microvm"})), 0, "MISSING_CAPABILITY"),
            (sch.NodeReport("tier", "west", frozenset({"process", "wasm"}), capabilities=frozenset({"gpu"})), 0, "INSUFFICIENT_TIER"),
            (sch.NodeReport("tenant", "west", frozenset({"microvm"}), capabilities=frozenset({"gpu"}), occupants={"other": "t2"}), 0, "TENANT_ISOLATION"),
        ]
        for node, now, reason in cases:
            with self.subTest(reason=reason):
                self.assertIn(reason, sch.rejection_reasons(workload, klass, node, now=now))

    def test_deterministic_tier_minimal_placement(self):
        nodes = [
            sch.NodeReport("b", "s", frozenset({"process", "wasm"}), free_slots=2),
            sch.NodeReport("a", "s", frozenset({"process", "wasm"}), free_slots=2),
            sch.NodeReport("c", "s", frozenset({"wasm", "microvm"}), free_slots=9),
        ]
        placement = sch.place(sch.Workload("w", "t", "internal"), nodes)
        self.assertEqual(placement["node"], "a")
        self.assertEqual(placement["tier"], "process")
        self.assertEqual(placement["decision"]["strategy"], "weakest-sufficient-tier/most-free-slots/name")

    def test_duplicate_node_identity_is_rejected(self):
        nodes = [
            sch.NodeReport("dup", "s", frozenset({"process"})),
            sch.NodeReport("dup", "s", frozenset({"process"})),
        ]
        with self.assertRaises(ValueError):
            sch.place(sch.Workload("w", "t", "internal"), nodes)

    def test_duplicate_workload_lease_is_rejected(self):
        nodes = [sch.NodeReport("n", "s", frozenset({"process"}), free_slots=2)]
        workload = sch.Workload("w", "t", "internal")
        sch.place(workload, nodes)
        with self.assertRaises(sch.Unplaceable) as raised:
            sch.place(workload, nodes)
        self.assertEqual(raised.exception.code, "DUPLICATE_LEASE")

    def test_concurrent_callers_cannot_oversubscribe_one_slot(self):
        node = sch.NodeReport("n", "s", frozenset({"process"}), free_slots=1)

        def attempt(name):
            try:
                return sch.place(sch.Workload(name, "t", "internal"), [node])["workload"]
            except sch.Unplaceable as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ["w1", "w2"]))
        self.assertEqual(sum(result in {"w1", "w2"} for result in results), 1)
        self.assertEqual(results.count("NO_CANDIDATE"), 1)
        self.assertEqual(node.free_slots, 0)
        self.assertEqual(len(node.occupants), 1)

    def test_no_candidate_error_uses_aggregate_diagnostics(self):
        workload = sch.Workload("w", "t", "public")
        nodes = [sch.NodeReport("n", "s", frozenset({"process"}))]
        with self.assertRaises(sch.Unplaceable) as raised:
            sch.place(workload, nodes)
        err = raised.exception.as_dict()
        self.assertEqual(err["code"], "NO_CANDIDATE")
        self.assertEqual(err["details"]["candidate_count"], 1)
        self.assertEqual(err["details"]["rejection_counts"], {"INSUFFICIENT_TIER": 1})
        self.assertNotIn("nodes", err["details"])
        self.assertNotIn("node_names", err["details"])

    def test_invalid_clock_and_lease_values_are_rejected(self):
        node = sch.NodeReport("n", "s", frozenset({"process"}))
        workload = sch.Workload("w", "t", "internal")
        for now in (-1, True, 1.5):
            with self.subTest(now=now), self.assertRaises(ValueError):
                sch.place(workload, [node], now=now)
        for ticks in (0, -1, True, 1.5):
            with self.subTest(ticks=ticks), self.assertRaises(ValueError):
                sch.place(workload, [node], lease_ticks=ticks)

    def test_engine_import_and_smoke_survive_optimized_mode(self):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "import sch01_workload_classification_and_runtime_placem as s; "
            "n=s.NodeReport('n','s',frozenset({'process'})); "
            "print(s.place(s.Workload('w','t','internal'),[n])['node'])"
        ) % str(ROOT)
        result = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "n")


if __name__ == "__main__":
    unittest.main()
