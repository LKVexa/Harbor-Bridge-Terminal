"""Release hygiene: preflight, versions, -O safety, CLI, traceability/evidence, secrets, lint, perf budgets
(MC-01, 02, 03, 22, 29, 36, 45, 51, 64)."""
import ast
import importlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from _support import PKG, PKG_DIR, ROOT

pkg = importlib.import_module(PKG)
preflight = importlib.import_module(f"{PKG}.preflight")
evidence = importlib.import_module(f"{PKG}.evidence")
E = importlib.import_module(f"{PKG}.errors").Inv22Error

SOURCES = sorted(p for p in PKG_DIR.glob("*.py"))


class Versions(unittest.TestCase):
    def test_single_version_source(self):
        v = (PKG_DIR / "VERSION").read_text().strip()
        self.assertEqual(pkg.__version__, v)
        self.assertIn('version = { file = "VERSION" }', (PKG_DIR / "pyproject.toml").read_text())
        self.assertIn(f"## {v}", (PKG_DIR / "CHANGELOG.md").read_text().split("\n## ", 2)[0] + "\n## " + (PKG_DIR / "CHANGELOG.md").read_text().split("\n## ", 2)[1])
        self.assertEqual(json.loads((PKG_DIR / "data/remediation.json").read_text())["release"], v)


class OptimisedMode(unittest.TestCase):
    def test_no_assert_statements_in_runtime_code(self):
        for src in SOURCES:
            tree = ast.parse(src.read_text(encoding="utf-8"))
            with self.subTest(src.name):
                self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])

    def test_behaviour_under_python_O(self):
        code = f"""
import sys, json; sys.path.insert(0, {str(ROOT)!r})
from {PKG} import matrix, shim, canonical
m = matrix.parse(open({str(PKG_DIR / 'data/matrix.json')!r}).read())
s = shim.ShimService(m, shim.default_registry())
ok = s.translate(json.load(open({str(PKG_DIR / 'fixtures/shim/std_to_fork_ok.json')!r}))['document'])
bad = s.translate(json.load(open({str(PKG_DIR / 'fixtures/shim/divergent_refused.json')!r}))['document'])
print(ok['status'], bad['error']['code'])
"""
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.split(), ["ok", "INV22.TRANSLATE.DIVERGENT"])


class Preflight(unittest.TestCase):
    def test_reports_missing_framework_and_pins(self):
        rep = preflight.run(strict=False, env={})
        checks = {c["check"]: c for c in rep["checks"]}
        self.assertFalse(rep["ok"])
        self.assertEqual(checks["pk_core"]["code"], "INV22.DEPENDENCY.UNAVAILABLE")
        self.assertFalse(checks["adjacent"]["ok"])
        self.assertFalse(checks["baselines"]["ok"])
        self.assertTrue(checks["crypto"]["ok"])

    def test_strict_fails_closed(self):
        with self.assertRaises(E) as c:
            preflight.run(strict=True, env={})
        self.assertTrue(c.exception.code.startswith("INV22.DEPENDENCY"))

    def test_dev_override_validation(self):
        self.assertEqual(preflight.pk_core_status({"PK_CORE_PATH": "relative/path"})["code"], "INV22.DEPENDENCY.UNAVAILABLE")

    def test_incompatible_api_level(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "pk_core"))
            with open(os.path.join(d, "pk_core", "__init__.py"), "w") as fh:
                fh.write("__version__ = '9.9'\nAPI_LEVEL = 99\n")
            sys.path.insert(0, d)
            sys.modules.pop("pk_core", None)
            try:
                st = preflight.pk_core_status({})
            finally:
                sys.path.remove(d)
                sys.modules.pop("pk_core", None)
        self.assertEqual(st["code"], "INV22.DEPENDENCY.INCOMPATIBLE")

    def test_package_imports_without_pk_core(self):
        out = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(ROOT)!r}); import {PKG} as p; "
                              f"from {PKG} import cert, store, shim, matrix; print(p.__version__)"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        out = subprocess.run([sys.executable, "-m", f"{PKG}.cli", *args], capture_output=True, text=True, cwd=str(ROOT))
        return out.returncode, json.loads(out.stdout)

    def test_commands(self):
        rc, out = self.run_cli("matrix-validate", str(PKG_DIR / "data/matrix.json"))
        self.assertEqual((rc, out["entries"]), (0, 5))
        rc, out = self.run_cli("translate", str(PKG_DIR / "fixtures/shim/std_to_fork_ok.json"))
        self.assertEqual(rc, 1)                     # fixture wrapper is not a bare request → structured error
        with tempfile.TemporaryDirectory() as d:
            req = os.path.join(d, "r.json")
            with open(req, "w") as fh:
                json.dump(json.loads((PKG_DIR / "fixtures/shim/std_to_fork_ok.json").read_text())["document"], fh)
            rc, out = self.run_cli("translate", req)
            self.assertEqual((rc, out["payload"]), (0, {"oflags": 9, "rights_base": 64}))
        rc, out = self.run_cli("matrix-validate", str(PKG_DIR / "fixtures/matrix/tampered.json"))
        self.assertEqual(out["error"]["code"], "INV22.VERSION.UNSUPPORTED")   # fixture wrapper has no contract id
        self.assertNotEqual(rc, 0)
        rc, out = self.run_cli("preflight")
        self.assertEqual(rc, 1)


class Traceability(unittest.TestCase):
    def test_all_controls_and_packages_traced(self):
        t = evidence.traceability()
        self.assertEqual(t["controls"], 100)
        rem = json.loads((PKG_DIR / "data/remediation.json").read_text())["items"]
        self.assertEqual(sorted(rem), [f"MC-{i:02d}" for i in range(1, 65)])
        self.assertEqual(sorted(evidence.mc_to_controls()), sorted(rem))
        for mc, v in rem.items():
            with self.subTest(mc):
                self.assertIn(v["status"], ("implemented", "partial", "blocked_external", "owner_decision"))
                if v["status"] != "implemented":
                    self.assertTrue(v["gap"], "non-complete packages must name their gap")
                for f in v["implementation"]:
                    path = f.split("::")[0].rstrip("/")
                    self.assertTrue((PKG_DIR / path).exists(), f"{mc}: {path} missing")
                for f in v["tests"]:
                    self.assertTrue((PKG_DIR / f).exists(), f"{mc}: {f} missing")

    def test_bundle_integrity_and_gate(self):
        with tempfile.TemporaryDirectory() as d:
            res = evidence.build_bundle(d, with_tests=False)
            man = json.loads(pathlib.Path(d, "MANIFEST.json").read_text())
            for name, dig in man["files"].items():
                self.assertEqual(evidence.canonical.file_digest(pathlib.Path(d, name)), dig)
            gate = json.loads(pathlib.Path(d, "gate.json").read_text())
        self.assertEqual(res["verdict"], "NO_GO")
        self.assertTrue(any("preflight pk_core" in r for r in gate["reasons"]))


class Hygiene(unittest.TestCase):
    PATTERNS = [re.compile(p) for p in (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\bAKIA[0-9A-Z]{16}\b",
                                        r"(?i)\b(password|secret)\s*=\s*['\"][^'\"]{6,}['\"]", r"\bghp_[A-Za-z0-9]{30,}")]

    def test_no_secrets_in_repository(self):
        hits = []
        for p in PKG_DIR.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".json", ".md", ".toml", ".yml", ".lock", "") and "tests" not in p.parts:
                text = p.read_text(encoding="utf-8", errors="ignore")
                hits += [f"{p.name}:{rx.pattern}" for rx in self.PATTERNS if rx.search(text)]
        self.assertEqual(hits, [])

    def test_lint_gate(self):
        ruff = shutil.which("ruff")
        if ruff is None:
            self.skipTest("ruff not installed")
        out = subprocess.run([ruff, "check", "--no-cache", "--select", "E9,F", str(PKG_DIR)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout[-2000:])


class PerformanceBudgets(unittest.TestCase):
    """Smoke budgets (generous, CI-safe).  Real baselines/regression tracking: MC-36."""

    def budget(self, fn, n, per_op_ms):
        t = time.perf_counter()
        for _ in range(n):
            fn()
        per = (time.perf_counter() - t) * 1000 / n
        self.assertLess(per, per_op_ms, f"{per:.3f} ms/op exceeds {per_op_ms} ms")
        return per

    def test_budgets(self):
        matrix = importlib.import_module(f"{PKG}.matrix")
        shim = importlib.import_module(f"{PKG}.shim")
        doc = (PKG_DIR / "data/matrix.json").read_text()
        m = matrix.parse(doc)
        s = shim.ShimService(m, shim.default_registry())
        req = json.loads((PKG_DIR / "fixtures/shim/std_to_fork_ok.json").read_text())["document"]
        self.budget(lambda: matrix.parse(doc), 200, 5.0)
        self.budget(lambda: s.translate(req), 500, 2.0)
        self.budget(lambda: m.classification("wasi:sockets"), 5000, 0.05)


if __name__ == "__main__":
    unittest.main()
