"""PLN-04 conformance and dependency-free runtime tests."""
from __future__ import annotations

import importlib
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

pkg = importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - expected in standalone archive
    pk_core = None

KNOWN_PARTIAL: list[str] = []


class PackageAndRuntimeTest(unittest.TestCase):
    def test_version_is_consistent(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")
        if not pkg.PK_CORE_AVAILABLE:
            with self.assertRaisesRegex(RuntimeError, "pk_core is required"):
                pkg.build_contract()

    def test_catalogue_validation_is_strict(self):
        with self.assertRaises(ValueError):
            pkg.Node({"container": True})
        with self.assertRaises(TypeError):
            pkg.Node({"process": "yes"})
        with self.assertRaises(ValueError):
            pkg.Node({"process": True}, max_instances=1, per_tenant_limit=2)
        node = pkg.Node({"process": True})
        with self.assertRaises(ValueError):
            node.restore_attestation("vm")
        with self.assertRaises(ValueError):
            node.fail_attestation("vm")

    def test_identifiers_reject_whitespace(self):
        node = pkg.Node({"process": True})
        for workload, tenant in [("", "t1"), ("   ", "t1"), ("w1", ""), ("w1", "\t"), ("x" * 257, "t1")]:
            with self.assertRaises(ValueError):
                pkg.admit(node, workload, tenant, "trusted")

    def test_admission_chooses_weakest_sufficient_attested_tier(self):
        node = pkg.Node({"process": True, "microvm": True})
        self.assertEqual(pkg.admit(node, "w1", "t1", "trusted"), "process")
        self.assertEqual(pkg.admit(node, "w2", "t1", "third-party"), "microvm")
        with self.assertRaises(pkg.NoSufficientTier):
            pkg.admit(node, "w3", "t1", "hostile")

    def test_cross_tenant_takeover_is_refused(self):
        node = pkg.Node({"process": True})
        pkg.admit(node, "w1", "tenant-a", "trusted")
        with self.assertRaises(PermissionError):
            pkg.admit(node, "w1", "tenant-b", "trusted")

    def test_readmission_never_silently_downgrades_or_migrates(self):
        node = pkg.Node({tier: True for tier in pkg.TIERS})
        self.assertEqual(pkg.admit(node, "hostile", "t1", "hostile"), "vm")
        self.assertEqual(pkg.admit(node, "hostile", "t1", "trusted"), "vm")
        self.assertEqual(node.instance("hostile").trust_class, "hostile")

        self.assertEqual(pkg.admit(node, "grow", "t1", "trusted"), "process")
        with self.assertRaises(pkg.AdmissionConflict):
            pkg.admit(node, "grow", "t1", "first-party")
        self.assertEqual(node.instance("grow").tier, "process")

    def test_attestation_loss_quarantines_residents_and_fails_closed(self):
        node = pkg.Node({"microvm": True})
        pkg.admit(node, "w1", "t1", "untrusted")
        self.assertEqual(node.fail_attestation("microvm"), ("w1",))
        self.assertEqual(node.instance("w1").state, "quarantined")
        with self.assertRaises(pkg.NoSufficientTier):
            pkg.admit(node, "w2", "t1", "untrusted")
        node.restore_attestation("microvm")
        with self.assertRaises(pkg.ResidentTierUnattested):
            pkg.admit(node, "w1", "t1", "untrusted")
        self.assertTrue(pkg.teardown(node, "w1", "t1"))
        self.assertEqual(pkg.admit(node, "w1", "t1", "untrusted"), "microvm")

    def test_teardown_enforces_tenant_or_explicit_privilege(self):
        node = pkg.Node({"process": True})
        pkg.admit(node, "w1", "tenant-a", "trusted")
        with self.assertRaises(PermissionError):
            pkg.teardown(node, "w1")
        with self.assertRaises(PermissionError):
            pkg.teardown(node, "w1", "tenant-b")
        with self.assertRaises(TypeError):
            pkg.teardown(node, "w1", privileged="yes")
        self.assertTrue(pkg.teardown(node, "w1", "tenant-a"))
        self.assertFalse(pkg.teardown(node, "missing", "tenant-a"))

        pkg.admit(node, "w2", "tenant-a", "trusted")
        self.assertTrue(pkg.teardown(node, "w2", privileged=True))

    def test_capacity_limits_are_enforced(self):
        node = pkg.Node({"process": True}, max_instances=2, per_tenant_limit=1)
        pkg.admit(node, "w1", "t1", "trusted")
        with self.assertRaises(pkg.CapacityExceeded):
            pkg.admit(node, "w2", "t1", "trusted")
        pkg.admit(node, "w3", "t2", "trusted")
        with self.assertRaises(pkg.CapacityExceeded):
            pkg.admit(node, "w4", "t3", "trusted")

    def test_audit_chain_covers_security_sensitive_transitions(self):
        ticks = iter(range(1, 100))
        node = pkg.Node({"process": True}, clock_ns=lambda: next(ticks))
        pkg.admit(node, "w1", "t1", "trusted")
        node.fail_attestation("process")
        node.restore_attestation("process")
        pkg.teardown(node, "w1", "t1")
        self.assertTrue(node.verify_audit_chain())
        self.assertEqual(
            [event.kind for event in node.audit_events()],
            ["workload_admitted", "attestation_failed", "attestation_restored", "workload_torn_down"],
        )

    def test_concurrent_same_workload_cannot_gain_duplicate_ownership(self):
        node = pkg.Node({"process": True})
        barrier = threading.Barrier(3)
        outcomes: list[str] = []
        lock = threading.Lock()

        def worker(tenant: str) -> None:
            barrier.wait()
            try:
                pkg.admit(node, "shared", tenant, "trusted")
            except PermissionError:
                result = "refused"
            else:
                result = "admitted"
            with lock:
                outcomes.append(result)

        threads = [threading.Thread(target=worker, args=(tenant,)) for tenant in ("a", "b")]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(sorted(outcomes), ["admitted", "refused"])
        self.assertEqual(len(node.instances), 1)


    def test_interface_schemas_parse_and_are_versioned(self):
        import json
        expected = {
            "PK_ADMISSION_1.schema.json": "PK_ADMISSION/1",
            "PK_TIER_CATALOGUE_1.schema.json": "PK_TIER_CATALOGUE/1",
            "PK_TIER_LIFECYCLE_1.schema.json": "PK_TIER_LIFECYCLE/1",
        }
        for filename, schema_name in expected.items():
            document = json.loads((PKG_DIR / "schemas" / filename).read_text(encoding="utf-8"))
            self.assertEqual(document["properties"]["schema"]["const"], schema_name)
            self.assertFalse(document.get("additionalProperties", True))

    def test_checks_survive_optimised_mode(self):
        code = (
            "import sys; sys.path.insert(0, %r); import %s as p; "
            "n=p.Node({'process': True}); print(p.admit(n,'w','t','trusted')); "
            "print(n.verify_audit_chain())"
        ) % (str(ROOT), pkg.__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=15,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.splitlines(), ["process", "True"])


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class FrameworkConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered(self):
        comp = pkg.COMPONENT()
        findings = [finding for group in comp.assess_all().values() for finding in group]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({finding.check_id for finding in findings}), 100)
        self.assertFalse([finding for finding in findings if finding.status.value == "blocked"])

    def test_framework_checks_survive_optimised_mode(self):
        code = (
            "import sys; sys.path.insert(0, %r); import %s as p; "
            "c=p.COMPONENT(); print(sum(len(v) for v in c.assess_all().values()))"
        ) % (str(ROOT), pkg.__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=30,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
