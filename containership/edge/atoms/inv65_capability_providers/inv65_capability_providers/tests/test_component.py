"""Tests for INV-65 (inv65_capability_providers) -- stdlib unittest, no network.

The provider reference-model tests run standalone.  The 100-item conformance
checks additionally require the shared ``pk_core`` package and are skipped when
it is not importable.
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
for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - depends on outer repository
    pk_core = None

KNOWN_PARTIAL: list[str] = []


def _load_provider_module():
    """Load the pure provider model without importing package-level pk_core code."""
    name = "inv65_provider_standalone_test"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, PKG_DIR / "provider.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load provider.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load():
    pkg = importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)
    return pkg


class ProviderReferenceModelTest(unittest.TestCase):
    def setUp(self):
        self.m = _load_provider_module()

    def test_named_links_are_isolated(self):
        p = self.m.Provider("wasi:keyvalue")
        p.link("orders", {"bucket": "hot", "user": "orders-rw"}, link_name="primary")
        p.link("orders", {"bucket": "cold", "user": "orders-ro"}, link_name="archive")
        self.assertEqual(p.call("orders", "get", link_name="primary")["bucket"], "hot")
        self.assertEqual(p.call("orders", "get", link_name="archive")["bucket"], "cold")
        self.assertEqual(p.link_names("orders"), ("archive", "primary"))

    def test_legacy_default_link_api_remains_compatible(self):
        p = self.m.Provider("wasi:keyvalue")
        p.link("orders", {"bucket": "orders", "user": "rw"})
        self.assertEqual(p.call("orders", "get")["link"], "default")

    def test_unlink_is_durable_across_restart(self):
        p = self.m.Provider("wasi:keyvalue")
        p.link("orders", {"bucket": "orders", "user": "rw"})
        self.assertTrue(p.unlink("orders"))
        self.assertEqual(p.restart(), 0)
        with self.assertRaises(self.m.NoLink):
            p.call("orders", "get")

    def test_inline_secret_fields_are_rejected(self):
        p = self.m.Provider("wasi:keyvalue")
        with self.assertRaises(self.m.InvalidLink):
            p.link("orders", {"bucket": "orders", "user": "rw", "token": "plaintext"})
        with self.assertRaises(self.m.InvalidLink):
            p.link("orders", {"bucket": "orders", "user": "rw", "clientSecret": "plaintext"})
        p.link("orders", {"bucket": "orders", "user": "rw", "secret_ref": "secrets://orders"})
        self.assertEqual(p.link_count, 1)

    def test_invalid_identifiers_and_operations_fail_closed(self):
        with self.assertRaises(self.m.InvalidLink):
            self.m.Provider("  ")
        p = self.m.Provider("wasi:keyvalue")
        with self.assertRaises(self.m.InvalidLink):
            p.link("", {"bucket": "orders", "user": "rw"})
        p.link("orders", {"bucket": "orders", "user": "rw"})
        with self.assertRaises(self.m.InvalidLink):
            p.call("orders", "")

    def test_unhealthy_backend_refuses_calls(self):
        p = self.m.Provider("wasi:keyvalue")
        p.link("orders", {"bucket": "orders", "user": "rw"})
        p.backend_ok = False
        self.assertEqual(p.health(), "unhealthy")
        with self.assertRaises(self.m.ProviderUnavailable) as ctx:
            p.call("orders", "get")
        self.assertEqual(ctx.exception.code, "PK_PROVIDER_UNAVAILABLE")

    def test_input_config_is_copied_and_private(self):
        p = self.m.Provider("wasi:keyvalue")
        cfg = {"bucket": "orders", "user": "rw", "meta": {"region": "west"}}
        p.link("orders", cfg)
        cfg["bucket"] = "attacker-mutated"
        self.assertEqual(p.call("orders", "get")["bucket"], "orders")
        self.assertFalse(hasattr(p, "links"), "raw link configuration must not be publicly exposed")

    def test_parallel_link_updates_do_not_corrupt_state(self):
        p = self.m.Provider("wasi:keyvalue")
        errors: list[BaseException] = []

        def worker(i: int) -> None:
            try:
                p.link("worker", {"bucket": f"b{i}", "user": f"u{i}"}, link_name=f"l{i}")
                self.assertEqual(p.call("worker", "get", link_name=f"l{i}")["bucket"], f"b{i}")
            except BaseException as exc:  # capture thread assertion failures
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(32)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(p.link_count, 32)
        self.assertEqual(p.restart(), 32)


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
            f.check_id
            for f in findings
            if not f.status.passing and f.check_id not in KNOWN_PARTIAL and "not installed" not in f.note
        )
        self.assertEqual(unexpected, [])
        self.assertFalse([f for f in findings if f.status.value == "blocked"])

    def test_checks_survive_optimised_mode(self):
        """Behavioural checks must not depend on assert statements (python -O)."""
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([p for p in sys.path[:3]], _load().__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT), check=False
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
