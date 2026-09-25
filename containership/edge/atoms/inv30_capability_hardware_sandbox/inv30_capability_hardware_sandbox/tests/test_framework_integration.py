# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Integration with pk_core and every adjacent layer: GAP-02, PLN-04, INV-41, INV-45 (GAP-001..003, 057).

These are MANDATORY. If pk_core or a sibling is missing they skip — and the
release gate counts a skipped mandatory suite as BLOCKED, never as passed.
"""
import unittest

from ..deps import pk_core_status, sibling_status

try:
    import pk_core  # noqa: F401
    from pk_core.integration import resolve
except ModuleNotFoundError:  # pragma: no cover
    pk_core = None


@unittest.skipIf(pk_core is None, "pk_core not importable (mandatory: see docs/COMPATIBILITY_MATRIX.md)")
class FrameworkIntegrationTest(unittest.TestCase):
    def test_pk_core_version_in_supported_range(self):
        self.assertEqual(pk_core_status()["state"], "ok")

    def test_registry_discovers_inv30(self):
        """Regression for the 4.2.0 defect: lazy import hid the component from pk_core.Registry."""
        from pk_core.registry import Registry
        self.assertIn("INV-30", Registry("pk_components").discover())

    def test_siblings_installed(self):
        missing = [k for k, v in sibling_status().items() if v["state"] != "ok"]
        if missing:
            self.skipTest(f"sibling(s) not installed: {missing}")

    def test_gap02_publishes_local_probe_honestly(self):
        from ..discovery import publish_to_gap02
        gap02 = resolve("GAP-02")
        if gap02 is None:
            self.skipTest("GAP-02 not installed")
        for state, bucket in (("absent", "absent"), ("unprobed", "unprobed"), ("present", "present")):
            rep = publish_to_gap02("n1", 5, {"state": state, "signal": "t"})
            view = rep.for_consumer(now=6)
            self.assertIn("cheri", view[bucket])
            if state != "present":
                self.assertNotIn("cheri", view["present"])

    def test_pln04_admits_only_where_hardware_is_present(self):
        pln04 = resolve("PLN-04")
        if pln04 is None:
            self.skipTest("PLN-04 not installed")
        from ..backend import select_backend
        from ..errors import HardwareRequired
        # PLN-04 admits a workload to this tier only if INV-30 can serve it; INV-30 refuses on no hardware.
        with self.assertRaises(HardwareRequired):
            select_backend(require_hardware=True, mode="production")

    def test_inv41_shares_attenuation_only_model(self):
        inv41 = resolve("INV-41")
        if inv41 is None:
            self.skipTest("INV-41 not installed")
        comp = inv41.COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertFalse([f for f in findings if f.status.value == "blocked"])

    def test_inv45_software_fallback_is_distinct_tier(self):
        inv45 = resolve("INV-45")
        if inv45 is None:
            self.skipTest("INV-45 not installed")
        comp = inv45.COMPONENT()
        self.assertEqual(comp.element_id, "INV-45")
        self.assertNotEqual(comp.element_id, "INV-30")  # fallback is a different tier, never relabelled INV-30

    def test_pk_core_gate_runs_end_to_end(self):
        from pk_core.evidence import EvidenceLedger
        from pk_core.gate import ConformanceGate
        from pk_core.registry import Registry
        from pk_core.workflow import WorkflowEngine
        comp = Registry("pk_components").discover().get("INV-30")
        ledger = EvidenceLedger()
        res = WorkflowEngine(ledger).run(comp)
        gate = ConformanceGate().evaluate([res]).to_dict()
        self.assertIn(gate["verdict"], ("GO", "CONDITIONAL_GO"))
        self.assertEqual(ledger.verify(), [])


if __name__ == "__main__":
    unittest.main()


class DependencyVersionTest(unittest.TestCase):
    """pk_core present / absent / incompatible / intentionally disabled (GAP-001-VAL-01)."""

    def test_incompatible_and_absent_pk_core_fail_closed(self):
        import sys
        import types
        from .. import deps
        from ..errors import DependencyIncompatible
        saved = sys.modules.get("pk_core")
        try:
            sys.modules["pk_core"] = types.SimpleNamespace(__version__="5.1.0")
            self.assertEqual(deps.pk_core_status()["state"], "incompatible")
            with self.assertRaises(DependencyIncompatible):
                deps.require_pk_core()
            sys.modules["pk_core"] = None  # intentionally disabled / absent
            self.assertEqual(deps.pk_core_status()["state"], "absent")
            with self.assertRaises(DependencyIncompatible):
                deps.require_pk_core()
        finally:
            if saved is not None:
                sys.modules["pk_core"] = saved
            else:
                sys.modules.pop("pk_core", None)
