"""PLN-01 tests -- standard library only for the core graph.

Run from the directory containing this package.  The core tests do not require
``pk_core``.  Monorepo conformance tests activate automatically when
``pk_core`` is importable (or ``PK_CORE_PATH`` points to it).
"""
from __future__ import annotations

import importlib
from concurrent.futures import ThreadPoolExecutor
import os
import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

pkg = importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - expected in standalone package
    pk_core = None

KNOWN_PARTIAL: list[str] = []


class CoreGraphTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")

    def test_dependency_order_is_deterministic(self):
        graph = pkg.IntentGraph()
        a = graph.declare("t1", "prod", "a", {"v": 1})
        b = graph.declare("t1", "prod", "b", {"v": 1}, after=[a])
        c = graph.declare("t1", "prod", "c", {"v": 1}, after=[a])
        self.assertEqual(graph.order(), [a, b, c])

    def test_cross_tenant_and_environment_edges_are_refused(self):
        graph = pkg.IntentGraph()
        graph.declare("t1", "prod", "root", {})
        for dep in (("t2", "prod", "root"), ("t1", "stage", "root")):
            with self.subTest(dep=dep), self.assertRaises(pkg.AdmissionRejectedError):
                graph.declare("t1", "prod", "app", {}, after=[dep])

    def test_bad_dependency_shape_is_validation_error(self):
        graph = pkg.IntentGraph()
        with self.assertRaises(pkg.ValidationError):
            graph.declare("t1", "prod", "x", {}, after=[("t1", "prod")])

    def test_spec_is_defensively_copied(self):
        graph = pkg.IntentGraph()
        spec = {"nested": {"value": 1}}
        key = graph.declare("t1", "prod", "x", spec)
        spec["nested"]["value"] = 99
        self.assertEqual(graph.node_spec(key)["nested"]["value"], 1)
        returned = graph.node_spec(key)
        returned["nested"]["value"] = 77
        self.assertEqual(graph.node_spec(key)["nested"]["value"], 1)

    def test_idempotent_declaration_does_not_advance_version(self):
        graph = pkg.IntentGraph()
        graph.declare("t1", "prod", "x", {"v": 1})
        version = graph.version
        graph.declare("t1", "prod", "x", {"v": 1})
        self.assertEqual(graph.version, version)
        self.assertEqual(graph.audit_events[-1].outcome, "admitted_noop")

    def test_optimistic_concurrency_refuses_stale_writer(self):
        graph = pkg.IntentGraph()
        graph.declare("t1", "prod", "x", {})
        with self.assertRaises(pkg.VersionConflictError):
            graph.declare("t1", "prod", "y", {}, expected_version=0)

    def test_expected_version_is_atomic_across_threads(self):
        graph = pkg.IntentGraph()

        def attempt(index):
            try:
                graph.declare("t1", "prod", f"n{index}", {}, expected_version=0, actor=f"worker-{index}")
                return "ok"
            except pkg.VersionConflictError:
                return "stale"

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(8)))
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("stale"), 7)
        self.assertEqual(graph.version, 1)
        self.assertEqual(len(graph), 1)

    def test_replay_guard_refuses_duplicate_request(self):
        graph = pkg.IntentGraph()
        graph.declare("t1", "prod", "x", {}, request_id="req-1")
        with self.assertRaises(pkg.ReplayError):
            graph.declare("t1", "prod", "y", {}, request_id="req-1")

    def test_retract_refuses_orphaning_unless_cascaded(self):
        graph = pkg.IntentGraph()
        a = graph.declare("t1", "prod", "a", {})
        b = graph.declare("t1", "prod", "b", {}, after=[a])
        with self.assertRaises(pkg.DependencyInUseError):
            graph.retract(a)
        removed = graph.retract(a, cascade=True)
        self.assertEqual(set(removed), {a, b})
        self.assertEqual(len(graph), 0)

    def test_diff_and_rollback(self):
        graph = pkg.IntentGraph()
        key = graph.declare("t1", "prod", "app", {"image": "svc:1"})
        baseline = graph.version
        graph.declare("t1", "prod", "app", {"image": "svc:2"}, expected_version=baseline)
        delta = graph.diff(baseline)
        self.assertEqual(delta["changed"], [list(key)])
        graph.rollback(baseline, expected_version=graph.version)
        self.assertEqual(graph.node_spec(key)["image"], "svc:1")

    def test_plan_is_deterministic_and_fingerprinted(self):
        graph = pkg.IntentGraph()
        key = graph.declare("t1", "prod", "app", {"image": "svc:1"})
        one = pkg.plan(graph, {key: {"image": "svc:1"}})
        two = pkg.plan(graph, {key: {"image": "svc:1"}})
        self.assertEqual(one, two)
        self.assertEqual(one["steps"][0]["action"], "noop")
        self.assertEqual(len(one["plan_id"]), 64)

    def test_limits_fail_closed(self):
        graph = pkg.IntentGraph(max_nodes=1, max_spec_bytes=16)
        graph.declare("t1", "prod", "x", {})
        with self.assertRaises(pkg.AdmissionRejectedError):
            graph.declare("t1", "prod", "y", {})
        other = pkg.IntentGraph(max_spec_bytes=8)
        with self.assertRaises(pkg.ValidationError):
            other.declare("t1", "prod", "x", {"payload": "too large"})

    def test_audit_chain_verifies(self):
        graph = pkg.IntentGraph()
        graph.declare("t1", "prod", "x", {}, actor="alice")
        try:
            graph.declare("t1", "stage", "y", {}, after=[("t1", "prod", "x")], actor="alice")
        except pkg.AdmissionRejectedError:
            pass
        self.assertGreaterEqual(len(graph.audit_events), 2)
        self.assertTrue(graph.verify_audit_chain())


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class MonorepoConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered(self):
        comp = pkg.COMPONENT()
        findings = [finding for findings in comp.assess_all().values() for finding in findings]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({finding.check_id for finding in findings}), 100)
        unexpected = sorted(
            finding.check_id
            for finding in findings
            if not finding.status.passing
            and finding.check_id not in KNOWN_PARTIAL
            and "not installed" not in finding.note
        )
        self.assertEqual(unexpected, [])
        self.assertFalse([finding for finding in findings if finding.status.value == "blocked"])

    def test_checks_survive_optimised_mode(self):
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([p for p in sys.path[:3]], pkg.__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT), check=False
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
