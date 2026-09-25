# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Operator tooling: rollout/canary/rollback/emergency-disable, CLI, clean-env bootstrap (GAP-026, 062, 066)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .. import ops

PKG = Path(__file__).resolve().parents[1]


class OpsTest(unittest.TestCase):
    def test_rollout_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            green = {"error_rate_ok": True, "latency_ok": True, "invariant_violations_zero": True}
            self.assertEqual(ops.status(p)["percent"], 0)
            self.assertEqual(ops.promote(p, operator="o", health=green)["percent"], 1)
            self.assertEqual(ops.promote(p, operator="o", health=green)["percent"], 5)
            with self.assertRaises(SystemExit):
                ops.promote(p, operator="o", health=dict(green, invariant_violations_zero=False))
            self.assertEqual(ops.rollback(p, operator="o", reason="r")["percent"], 1)
            s = ops.disable(p, operator="o", reason="incident")
            self.assertEqual((s["percent"], s["disabled"]), (0, True))
            with self.assertRaises(SystemExit):
                ops.promote(p, operator="o", health=green)
            ops.enable(p, operator="o", reason="post-incident review done")
            self.assertTrue(ops.status(p)["audit_ok"])

    def _cli(self, *args, cwd=None, env=None):
        root = PKG.parent.parent
        mod = f"{PKG.parent.name}.{PKG.name}.ops" if PKG.parent.name == "pk_components" else f"{PKG.name}.ops"
        return subprocess.run([sys.executable, "-m", mod, *args], cwd=cwd or root, capture_output=True,
                              text=True, env=env, timeout=60)

    def test_cli_env_health_configcheck(self):
        for cmd in (["env"], ["health"], ["config-check", "--context", "far-edge"]):
            r = self._cli(*cmd)
            self.assertEqual(r.returncode, 0, r.stderr)
            json.loads(r.stdout)
        r = self._cli("config-check", "--mode", "production")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("minting_key", r.stderr)

    def test_clean_environment_bootstrap_without_pk_core(self):
        """Copy only this package to an empty dir; the model and ops must work with no framework present."""
        with tempfile.TemporaryDirectory() as d:
            import shutil
            shutil.copytree(PKG, Path(d) / PKG.name, ignore=shutil.ignore_patterns("__pycache__", "evidence"))
            env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PK_CORE_PATH")}
            env["PYTHONNOUSERSITE"] = "1"
            r = subprocess.run([sys.executable, "-S", "-c",
                                f"import sys; sys.path.insert(0, {d!r}); import {PKG.name} as m; "
                                "from importlib import import_module as im; d=im(m.__name__+'.deps'); "
                                "print(m.__version__, d.pk_core_status()['state'])"],
                               capture_output=True, text=True, env=env, cwd=d, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.split(), ["4.3.0", "absent"])


if __name__ == "__main__":
    unittest.main()


class ExitGatePolicyTest(unittest.TestCase):
    """The gate itself: skipped mandatory ⇒ blocked; invariant failure ⇒ NO_GO (unwaivable)."""

    def _suites(self, **over):
        from ..release import SUITES
        ok = {"ran": 5, "passed": 5, "failed": 0, "skipped": 0, "returncode": 0, "skip_reasons": []}
        hw = {"ran": 2, "passed": 0, "failed": 0, "skipped": 2, "returncode": 0, "skip_reasons": ["no CHERI"]}
        s = {n: {"normal": dict(ok), "optimized": dict(ok)} for n, *_ in SUITES}
        s["hardware-conformance"] = {"normal": dict(hw), "optimized": dict(hw)}
        for k, v in over.items():
            s[k.replace("_", "-")] = {"normal": v, "optimized": v}
        return s

    def _eval(self, suites, signed=True):
        from ..release import evaluate
        sig = {r: {"name": "x", "date": "2026-09-23"} for r in ("owner", "security_reviewer", "independent_verifier")}
        env = {"cheri": {"state": "absent", "signal": "test"}}
        return evaluate(suites, [], sig if signed else {}, env, [])

    def test_all_green_without_hardware_is_model_only(self):
        g = self._eval(self._suites())
        self.assertEqual((g["verdict"], g["hardware_tier_verdict"]), ("GO_MODEL_ONLY", "NO_GO"))

    def test_skipped_mandatory_suite_blocks(self):
        skipped = {"ran": 8, "passed": 0, "failed": 0, "skipped": 8, "returncode": 0, "skip_reasons": ["pk_core"]}
        g = self._eval(self._suites(framework_integration=skipped))
        self.assertEqual(g["verdict"], "NO_GO")

    def test_invariant_failure_is_unwaivable_no_go(self):
        bad = {"ran": 5, "passed": 4, "failed": 1, "skipped": 0, "returncode": 1, "skip_reasons": []}
        g = self._eval(self._suites(model_core=bad))
        self.assertEqual(g["verdict"], "NO_GO")
        self.assertTrue(g["zero_budget_invariant_failures"])
        self.assertFalse(g["waivable"]["zero_budget_invariant_failures"])

    def test_missing_signoffs_are_conditions_not_passes(self):
        g = self._eval(self._suites(), signed=False)
        self.assertEqual(g["verdict"], "CONDITIONAL_GO_MODEL_ONLY")
        self.assertEqual(len(g["conditions"]), 3)

    def test_hardware_green_allows_full_go(self):
        ok = {"ran": 2, "passed": 2, "failed": 0, "skipped": 0, "returncode": 0, "skip_reasons": []}
        g = self._eval(self._suites(hardware_conformance=ok))
        self.assertEqual((g["verdict"], g["hardware_tier_verdict"]), ("GO", "GO"))
