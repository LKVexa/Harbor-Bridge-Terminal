"""Standalone and pk_core conformance tests for INV-06 Traditional IaC."""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import subprocess
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

pkg = importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    pk_core = None

KNOWN_PARTIAL: list[str] = []


class CoreStateTest(unittest.TestCase):
    def test_version_and_checklist_integrity(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")
        checklist = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        self.assertEqual(checklist["item_count"], 100)
        self.assertEqual(len(checklist["items"]), 100)
        self.assertEqual(len({item["check_id"] for item in checklist["items"]}), 100)

    def test_plan_apply_and_detached_snapshots(self):
        s = pkg.IacState()
        desired = {"vm": {"size": "small", "tags": ["prod"]}}
        p = s.plan(desired)
        desired["vm"]["size"] = "mutated-after-plan"
        p_copy = json.loads(json.dumps(p))
        self.assertEqual(s.apply(p), 1)
        self.assertEqual(s.resources["vm"]["size"], "small")
        view = s.resources
        view["vm"]["size"] = "external-write"
        self.assertEqual(s.resources["vm"]["size"], "small")
        self.assertEqual(p, p_copy)

    def test_stale_plan_is_refused_atomically(self):
        s = pkg.IacState()
        s.apply(s.plan({"db": "large"}))
        a = s.plan({"db": "xlarge"})
        b = s.plan({"db": "small"})
        s.apply(a)
        before = s.snapshot()
        with self.assertRaises(pkg.StalePlan):
            s.apply(b)
        self.assertEqual(s.snapshot()["resources"], before["resources"])
        self.assertEqual(s.serial, before["serial"])

    def test_protection_is_read_only_and_invalidates_outstanding_plan(self):
        s = pkg.IacState({"db": "large"})
        p = s.plan({"db": "xlarge"})
        before_serial = s.serial
        s.protect("db")
        self.assertEqual(s.serial, before_serial + 1)
        self.assertIsInstance(s.protected, frozenset)
        with self.assertRaises(pkg.StalePlan):
            s.apply(p)
        with self.assertRaises(pkg.ProtectedResource):
            s.plan({})

    def test_tampered_or_malformed_plan_is_refused(self):
        s = pkg.IacState()
        p = s.plan({"a": 1})
        p["create"]["a"] = 2
        before = s.snapshot()
        with self.assertRaises(pkg.InvalidPlan) as cm:
            s.apply(p)
        self.assertEqual(cm.exception.code, "PK_IAC_INVALID_PLAN")
        self.assertEqual(s.snapshot()["resources"], before["resources"])
        bad = s.plan({"a": 1})
        bad["unexpected"] = True
        with self.assertRaises(pkg.InvalidPlan):
            s.apply(bad)

    def test_drift_distinguishes_missing_from_json_null(self):
        s = pkg.IacState({"present_null": None})
        d = s.drift({"other_null": None})
        self.assertEqual(set(d), {"present_null", "other_null"})
        self.assertTrue(d["present_null"]["state_present"])
        self.assertFalse(d["present_null"]["real_present"])
        self.assertFalse(d["other_null"]["state_present"])
        self.assertTrue(d["other_null"]["real_present"])

    def test_rejects_non_json_state(self):
        with self.assertRaises(pkg.InvalidState):
            pkg.IacState({"bad": {1, 2, 3}})
        with self.assertRaises(pkg.InvalidState):
            pkg.IacState({"bad": float("nan")})

    def test_structured_errors_metrics_and_audit_chain(self):
        s = pkg.IacState({"db": "large"})
        p1 = s.plan({"db": "xlarge"})
        p2 = s.plan({"db": "small"})
        s.apply(p1)
        with self.assertRaises(pkg.StalePlan) as cm:
            s.apply(p2)
        payload = cm.exception.as_dict()
        self.assertEqual(payload["code"], "PK_IAC_STALE_PLAN")
        self.assertIn("plan_serial", payload["details"])
        self.assertEqual(s.metrics()["stale_refusals"], 1)
        self.assertTrue(s.verify_audit_chain())
        exported = s.audit_events()
        exported[0]["action"] = "tampered-copy"
        self.assertTrue(s.verify_audit_chain())

    def test_concurrent_apply_allows_only_one_plan_for_a_serial(self):
        s = pkg.IacState({"counter": 0})
        a = s.plan({"counter": 1})
        b = s.plan({"counter": 2})
        barrier = threading.Barrier(3)
        outcomes: list[str] = []
        lock = threading.Lock()

        def worker(plan):
            barrier.wait()
            try:
                s.apply(plan)
                result = "applied"
            except pkg.StalePlan:
                result = "stale"
            with lock:
                outcomes.append(result)

        ta = threading.Thread(target=worker, args=(a,))
        tb = threading.Thread(target=worker, args=(b,))
        ta.start(); tb.start(); barrier.wait(); ta.join(); tb.join()
        self.assertEqual(sorted(outcomes), ["applied", "stale"])
        self.assertIn(s.resources["counter"], {1, 2})

    def test_json_schemas_and_reference_fixture(self):
        for path in sorted((PKG_DIR / "schemas").glob("*.json")):
            data = json.loads(path.read_text())
            self.assertEqual(data["$schema"], "https://json-schema.org/draft/2020-12/schema")
        fixture = json.loads((PKG_DIR / "fixtures" / "basic_plan.json").read_text())
        s = pkg.IacState()
        self.assertEqual(s.apply(fixture), 1)
        self.assertEqual(s.resources["vpc"]["cidr"], "10.0.0.0/16")

    def test_audit_retention_is_bounded_and_chain_remains_valid(self):
        s = pkg.IacState(audit_capacity=4)
        for i in range(6):
            s.drift({"x": i})
        self.assertLessEqual(len(s.audit_events()), 4)
        self.assertGreater(s.metrics()["audit_dropped"], 0)
        self.assertTrue(s.verify_audit_chain())

    def test_core_survives_optimized_mode(self):
        code = (
            "import sys; sys.path.insert(0, %r); import %s as m; "
            "s=m.IacState(); p=s.plan({'x': 1}); s.apply(p); "
            "print(s.serial, s.resources['x'], s.verify_audit_chain())"
        ) % (str(ROOT), pkg.__name__)
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "1 1 True")


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class PkCoreConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered(self):
        self.assertIsNotNone(pkg.COMPONENT)
        comp = pkg.COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        unexpected = sorted(
            f.check_id
            for f in findings
            if not f.status.passing and f.check_id not in KNOWN_PARTIAL and "not installed" not in f.note
        )
        self.assertEqual(unexpected, [])
        self.assertFalse([f for f in findings if f.status.value == "blocked"])

    def test_checks_survive_optimised_mode(self):
        code = (
            "import sys; sys.path.insert(0, %r); import %s as m; c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % (str(ROOT), pkg.__name__)
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main(verbosity=2)
