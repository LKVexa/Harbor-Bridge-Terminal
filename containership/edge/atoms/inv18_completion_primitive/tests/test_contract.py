"""Public-interface contract tests (C082), run against an installed copy, not the source tree."""
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from _util import m, PKG_DIR

pkg = m()


class PublicApiTest(unittest.TestCase):
    def test_package_root_exports(self):
        """REQ: C082 C016"""
        for name in ("Future", "AlreadyResolved", "AlreadyTaken", "Abandoned", "Cancelled", "FutureError",
                     "Rejected", "ErrorRecord", "Runtime", "ELEMENT_ID", "ELEMENT_NAME", "__version__"):
            self.assertIn(name, pkg.__all__)
        for name in ("Future", "Runtime", "ErrorRecord"):
            self.assertTrue(callable(getattr(pkg, name)))
        self.assertEqual(pkg.__version__, (PKG_DIR / "VERSION").read_text().strip())
        self.assertEqual(pkg.ELEMENT_ID, "INV-18")

    def test_signatures_match_snapshot(self):
        """REQ: C082 C016"""
        snap = json.loads((PKG_DIR / "conformance/API_SNAPSHOT.json").read_text())
        fut = m("future").Future
        self.assertEqual(sorted(n for n in vars(fut) if not n.startswith("_") or n == "__init__"),
                         snap["api"]["future.Future"])
        self.assertEqual(list(inspect.signature(fut.wait).parameters), ["self", "timeout"])
        self.assertEqual(list(inspect.signature(m("runtime").Runtime.create).parameters),
                         ["self", "value_type", "tenant", "trace"])

    def test_exception_hierarchy(self):
        """REQ: C082 C026"""
        errors = m("errors")
        for exc in (pkg.AlreadyResolved, pkg.AlreadyTaken, pkg.Abandoned, pkg.Cancelled, pkg.Rejected):
            self.assertTrue(issubclass(exc, errors.FutureError))
            self.assertTrue(issubclass(exc, RuntimeError))       # 4.2.0 callers catching RuntimeError still work

    def test_invalid_arguments(self):
        """REQ: C082 INV18-FR-009"""
        with self.assertRaises(TypeError):
            pkg.Future("int")
        with self.assertRaises(TypeError):
            pkg.Future(int).resolve(1.5)

    def test_pk_core_integration_is_lazy(self):
        """REQ: C082 C031 C090 — the primitive imports without pk_core; the audit component needs it"""
        import importlib.util
        if importlib.util.find_spec("pk_core") is None:
            with self.assertRaises(ModuleNotFoundError):
                pkg.COMPONENT
        with self.assertRaises(AttributeError):
            pkg.no_such_name


class InstalledCopyTest(unittest.TestCase):
    def test_contract_against_installed_copy(self):
        """REQ: C082 C040 — import from a site-packages-like location outside the source tree"""
        site = tempfile.mkdtemp()
        dst = os.path.join(site, PKG_DIR.name)
        shutil.copytree(PKG_DIR, dst, ignore=shutil.ignore_patterns("__pycache__", "evidence", "tests"))
        code = (
            "import sys; sys.path.insert(0, %r); import %s as p;"
            "assert p.__file__.startswith(%r), p.__file__;"
            "rt = p.Runtime({'environment': 'test'}); w, r = rt.create(int); rt.resolve(w, 4);"
            "assert rt.take(r) == ('ok', 4);"
            "f = p.Future(str); f.resolve_error('e'); assert f.take() == ('error', 'e'); print('OK')"
        ) % (site, PKG_DIR.name, site)
        out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=site)
        shutil.rmtree(site)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "OK")


if __name__ == "__main__":
    unittest.main()
