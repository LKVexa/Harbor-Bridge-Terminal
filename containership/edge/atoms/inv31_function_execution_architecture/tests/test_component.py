"""Conformance and standalone runtime tests for INV-31.

The runtime tests require only the Python standard library.  The framework
conformance tests additionally require ``pk_core`` and can be enabled with
``PK_CORE_PATH`` when that framework is stored outside the package tree.
"""
from __future__ import annotations

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
for path in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if path not in sys.path:
        sys.path.insert(0, path)

# Load runtime.py directly so safety tests still execute when pk_core is absent.
_runtime_spec = importlib.util.spec_from_file_location("inv31_runtime_standalone", PKG_DIR / "runtime.py")
if _runtime_spec is None or _runtime_spec.loader is None:  # pragma: no cover - interpreter failure
    raise RuntimeError("could not load runtime.py")
runtime = importlib.util.module_from_spec(_runtime_spec)
sys.modules[_runtime_spec.name] = runtime
_runtime_spec.loader.exec_module(runtime)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - expected in standalone archive
    pk_core = None

KNOWN_PARTIAL: list[str] = []


def _load_package():
    name = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
    return importlib.import_module(name)


class StandaloneRuntimeTest(unittest.TestCase):
    def test_version_file_and_source_agree(self):
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")
        source = (PKG_DIR / "__init__.py").read_text(encoding="utf-8")
        self.assertIn('__version__ = "4.3.0"', source)

    def test_cold_then_warm_reuse_and_state_clear(self):
        pool = runtime.FunctionPool()
        first = pool.invoke(tenant="t1", version="v1", now=0)
        second = pool.invoke(tenant="t1", version="v1", now=1)
        self.assertTrue(first["cold"])
        self.assertFalse(second["cold"])
        self.assertEqual(first["instance"], second["instance"])
        self.assertTrue(first["scratch_cleared"] and second["scratch_cleared"])
        self.assertEqual(second["decision_reason"], "reused_same_tenant_same_version_instance")

    def test_tenant_and_version_are_strict_reuse_boundaries(self):
        pool = runtime.FunctionPool()
        first = pool.invoke(tenant="t1", version="v1", now=0)
        other_tenant = pool.invoke(tenant="t2", version="v1", now=1)
        other_version = pool.invoke(tenant="t1", version="v2", now=2)
        self.assertNotEqual(first["instance"], other_tenant["instance"])
        self.assertNotEqual(first["instance"], other_version["instance"])
        self.assertTrue(other_tenant["cold"] and other_version["cold"])

    def test_per_invocation_scratch_isolation_under_concurrency(self):
        instance = runtime.Instance("fn-1", "t1", "v1", 0, concurrency_limit=2)
        scope_a = instance.enter(1)
        scope_b = instance.enter(1)
        instance.set_scratch(scope_a, "request", "A")
        instance.set_scratch(scope_b, "request", "B")
        instance.leave(scope_a)
        self.assertNotIn(scope_a, instance.scratch)
        self.assertEqual(instance.scope_snapshot(scope_b)["request"], "B")
        instance.leave(scope_b)
        self.assertEqual(instance.in_flight, 0)
        self.assertFalse(instance.scratch)

    def test_ambiguous_leave_is_rejected(self):
        instance = runtime.Instance("fn-1", "t1", "v1", 0, concurrency_limit=2)
        scope_a = instance.enter()
        scope_b = instance.enter()
        with self.assertRaises(RuntimeError):
            instance.leave()
        instance.leave(scope_a)
        instance.leave(scope_b)

    def test_concurrency_limit_is_thread_safe(self):
        instance = runtime.Instance("fn-1", "t1", "v1", 0, concurrency_limit=4)
        start = threading.Barrier(12)
        release = threading.Event()
        lock = threading.Lock()
        successes: list[str] = []
        rejected = 0

        def worker() -> None:
            nonlocal rejected
            start.wait()
            try:
                scope_id = instance.enter(1)
            except runtime.ConcurrencyExceeded:
                with lock:
                    rejected += 1
                return
            with lock:
                successes.append(scope_id)
            release.wait(timeout=2)
            instance.leave(scope_id)

        threads = [threading.Thread(target=worker) for _ in range(12)]
        for thread in threads:
            thread.start()
        # At least four workers must have entered before release; the lock makes
        # the bound deterministic even when all threads race at the check.
        for _ in range(2000):
            with lock:
                if len(successes) + rejected == 12:
                    break
            threading.Event().wait(0.001)
        with lock:
            self.assertEqual(len(successes), 4)
            self.assertEqual(rejected, 8)
        release.set()
        for thread in threads:
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
        self.assertEqual(instance.in_flight, 0)

    def test_direct_entry_rejects_stale_or_future_age(self):
        instance = runtime.Instance("fn-1", "t1", "v1", 10, max_age=5)
        with self.assertRaises(runtime.InstanceExpired):
            instance.enter(9)
        with self.assertRaises(runtime.InstanceExpired):
            instance.enter(16)

    def test_age_eviction_and_clock_rollback_are_fail_closed(self):
        pool = runtime.FunctionPool(max_age=10)
        first = pool.invoke(tenant="t1", version="v1", now=5)
        self.assertEqual(pool.evict_aged(16), [first["instance"]])
        second = pool.invoke(tenant="t1", version="v1", now=20)
        self.assertEqual(pool.evict_aged(19), [second["instance"]])
        self.assertEqual(pool.rollback_evictions, 1)

    def test_idle_capacity_eviction_is_reported(self):
        pool = runtime.FunctionPool(max_instances=1)
        first = pool.invoke(tenant="t1", version="v1", now=0)
        second = pool.invoke(tenant="t2", version="v1", now=1)
        self.assertEqual(second["evicted"], [first["instance"]])
        self.assertEqual(len(pool.instances), 1)
        self.assertEqual(pool.instances[0].name, second["instance"])

    def test_pool_capacity_is_bounded(self):
        pool = runtime.FunctionPool(max_instances=1)
        pool.invoke(tenant="t1", version="v1", now=0)
        held = pool.instances[0].enter(1)
        try:
            with self.assertRaises(runtime.PoolCapacityExceeded):
                pool.invoke(tenant="t2", version="v1", now=1)
        finally:
            pool.instances[0].leave(held)
        self.assertEqual(pool.capacity_rejections, 1)

    def test_identity_is_immutable(self):
        instance = runtime.Instance("fn-1", "t1", "v1", 0)
        with self.assertRaises(AttributeError):
            instance.tenant = "t2"
        with self.assertRaises(AttributeError):
            instance.version = "v2"

    def test_input_and_configuration_validation(self):
        with self.assertRaises(ValueError):
            runtime.FunctionPool(concurrency_limit=0)
        with self.assertRaises(ValueError):
            runtime.FunctionPool().invoke(tenant="   ", version="v1", now=0)
        with self.assertRaises(ValueError):
            runtime.FunctionPool().invoke(tenant="t1", version="v1", now=-1)
        with self.assertRaises(TypeError):
            runtime.FunctionPool().invoke(tenant="t1", version="v1", now=True)

    def test_pool_snapshot_excludes_scratch(self):
        pool = runtime.FunctionPool(concurrency_limit=2, max_age=20, max_instances=8)
        pool.invoke(tenant="t1", version="v1", now=0)
        snapshot = pool.pool_snapshot(1)
        self.assertEqual(snapshot["schema"], "PK_FUNCTION_POOL/1")
        self.assertEqual(snapshot["configuration"]["concurrency_limit"], 2)
        self.assertNotIn("scratch", snapshot["instances"][0])
        self.assertEqual(snapshot["stats"]["invocations"], 1)

    def test_destroy_idle_does_not_destroy_active_work(self):
        pool = runtime.FunctionPool()
        pool.invoke(tenant="t1", version="v1", now=0)
        instance = pool.instances[0]
        scope = instance.enter(1)
        self.assertEqual(pool.destroy_idle(tenant="t1"), [])
        instance.leave(scope)
        self.assertEqual(pool.destroy_idle(tenant="t1"), [instance.name])
        self.assertTrue(instance.destroyed)


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class FrameworkConformanceTest(unittest.TestCase):
    def test_package_version(self):
        self.assertEqual(_load_package().__version__, "4.3.0")

    def test_all_100_requirements_answered(self):
        comp = _load_package().COMPONENT()
        findings = [finding for band in comp.assess_all().values() for finding in band]
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
        ) % ([path for path in sys.path[:3]], _load_package().__name__)
        result = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
