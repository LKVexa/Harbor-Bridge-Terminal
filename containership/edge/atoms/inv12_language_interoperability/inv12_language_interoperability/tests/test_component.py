"""Conformance and hardening tests for INV-12 -- stdlib unittest, no network."""
import importlib
import importlib.util
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

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    pk_core = None

KNOWN_PARTIAL = []


def _load():
    pkg = importlib.import_module(
        PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)
    return pkg


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(_load().__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")

    def test_all_100_requirements_answered(self):
        comp = _load().COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        unexpected = sorted(
            f.check_id for f in findings
            if not f.status.passing and f.check_id not in KNOWN_PARTIAL and "not installed" not in f.note)
        self.assertEqual(unexpected, [])
        self.assertFalse([f for f in findings if f.status.value == "blocked"])

    def test_checks_survive_optimised_mode(self):
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([p for p in sys.path[:3]], _load().__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class BoundaryHardeningTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_nested_mutable_input_is_snapshotted(self):
        source = [{"v": [1, 2, 3]}]
        cv = self.m.lower(source, type_name="list", language="python", owner="producer")
        source[0]["v"][0] = 999
        out = self.m.lift(cv, language="go", new_owner="consumer")
        self.assertEqual(out["value"], [{"v": [1, 2, 3]}])
        out["value"][0]["v"][1] = 777
        self.assertTrue(cv.moved)

    def test_cyclic_container_refused(self):
        value = []
        value.append(value)
        with self.assertRaises(self.m.CanonicalizationError):
            self.m.lower(value, type_name="list", language="python", owner="a")

    def test_custom_object_refused_without_deepcopy_hooks(self):
        class HostObject:
            pass

        with self.assertRaises(self.m.CanonicalizationError):
            self.m.lower([HostObject()], type_name="list", language="python", owner="a")

    def test_invalid_unicode_refused(self):
        with self.assertRaises(self.m.CanonicalizationError):
            self.m.lower("\ud800", type_name="string", language="python", owner="a")

    def test_f32_silent_rounding_refused(self):
        with self.assertRaises(self.m.OutOfRange):
            self.m.lower(0.1, type_name="f32", language="python", owner="a")
        self.m.lower(1.5, type_name="f32", language="python", owner="a")

    def test_js_64_bit_integer_profile_is_exact(self):
        cv = self.m.lower(2**64 - 1, type_name="u64", language="javascript", owner="a")
        out = self.m.lift(cv, language="javascript", new_owner="b")
        self.assertEqual(out["value"], 2**64 - 1)

    def test_hostile_repr_and_container_subclasses_are_not_executed(self):
        class Hostile:
            def __repr__(self):
                raise AssertionError("hostile repr executed")

        class HostileList(list):
            def __iter__(self):
                raise AssertionError("hostile iterator executed")

        with self.assertRaises(self.m.OutOfRange):
            self.m.lower(Hostile(), type_name="u32", language="python", owner="a")
        with self.assertRaises(self.m.OutOfRange):
            self.m.lower(HostileList([1]), type_name="list", language="python", owner="a")

    def test_ownership_transfer_is_thread_safe(self):
        cv = self.m.lower(7, type_name="u32", language="rust", owner="a")
        results = []
        lock = threading.Lock()

        def worker(owner):
            try:
                self.m.lift(cv, language="go", new_owner=owner)
                result = "ok"
            except self.m.OwnershipError:
                result = "moved"
            with lock:
                results.append(result)

        threads = [threading.Thread(target=worker, args=(f"b{i}",)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(results, ["ok", "moved"])


if __name__ == "__main__":
    unittest.main()
