"""Standalone unit tests for the dependency-free INV-45 SFI core."""
from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
CORE_PATH = PKG_DIR / "sfi_core.py"
SPEC = importlib.util.spec_from_file_location("inv45_sfi_core_under_test", CORE_PATH)
core = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = core
SPEC.loader.exec_module(core)

Access = core.Access
BranchOutsideTargets = core.BranchOutsideTargets
ModuleNotVerified = core.ModuleNotVerified
SandboxRegion = core.SandboxRegion
SfiModule = core.SfiModule
UnmaskedAccess = core.UnmaskedAccess


class CoreSecurityTest(unittest.TestCase):
    def test_region_confines_arbitrary_integer_addresses(self):
        region = SandboxRegion(0x40000000, 0x10000)
        for address in (0, 1, -1, 0xFFFFFFFF, 0x7FFFFFFFFFFF, 1 << 130):
            self.assertTrue(region.contains(region.confine(address)))

    def test_region_rejects_invalid_shape(self):
        for args in ((-1, 0x1000), (0, 0), (0, 3), (True, 0x1000), (0, True)):
            with self.assertRaises((TypeError, ValueError), msg=args):
                SandboxRegion(*args)

    def test_access_record_validation(self):
        with self.assertRaises(ValueError):
            Access(-1, True)
        with self.assertRaises(TypeError):
            Access(0, 1)

    def test_mutable_caller_inputs_are_copied(self):
        accesses = [Access(0, True)]
        targets = {0}
        module = SfiModule("svc", SandboxRegion(0, 0x1000), accesses, targets)
        module.verify()
        accesses.append(Access(4, False))
        targets.add(999)
        self.assertTrue(module.verified)
        self.assertEqual(len(module.accesses), 1)
        with self.assertRaises(BranchOutsideTargets):
            module.branch(999)

    def test_security_state_replacement_invalidates_verification(self):
        module = SfiModule(
            "svc", SandboxRegion(0, 0x1000), (Access(0, True),), frozenset({0})
        )
        module.verify()
        self.assertTrue(module.verified)
        module.indirect_targets = frozenset({0, 999})
        self.assertFalse(module.verified)
        with self.assertRaises(ModuleNotVerified):
            module.branch(999)

        module.verify()
        module.region = SandboxRegion(0x2000, 0x1000)
        self.assertFalse(module.verified)
        with self.assertRaises(ModuleNotVerified):
            module.access(0)

    def test_failed_reverification_clears_old_seal(self):
        module = SfiModule(
            "svc", SandboxRegion(0, 0x1000), (Access(0, True),), frozenset({0})
        )
        module.verify()
        module.accesses = (Access(0, False),)
        with self.assertRaises(UnmaskedAccess):
            module.verify()
        self.assertFalse(module.verified)
        with self.assertRaises(ModuleNotVerified):
            module.access(0)

    def test_unverified_execution_and_bad_branch_fail_closed(self):
        module = SfiModule(
            "svc", SandboxRegion(0, 0x1000), (Access(0, True),), frozenset({0, 16})
        )
        with self.assertRaises(ModuleNotVerified):
            module.access(10)
        module.verify()
        self.assertEqual(module.branch(16), 16)
        for target in (17, -1, "16", [16]):
            with self.assertRaises(BranchOutsideTargets, msg=repr(target)):
                module.branch(target)

    def test_unmasked_error_is_machine_readable(self):
        module = SfiModule(
            "svc", SandboxRegion(0, 0x1000), (Access(8, False),), frozenset({0})
        )
        with self.assertRaises(UnmaskedAccess) as caught:
            module.verify()
        payload = caught.exception.as_dict()
        self.assertEqual(payload["code"], "SFI_UNMASKED_ACCESS")
        self.assertEqual(payload["details"]["unmasked_count"], 1)
        self.assertEqual(payload["details"]["sample_offsets"], [8])

    def test_overhead_metadata_must_be_finite_and_non_negative(self):
        for value in (-1, math.inf, math.nan, True, "1"):
            with self.assertRaises((TypeError, ValueError), msg=repr(value)):
                SfiModule(
                    "svc", SandboxRegion(0, 0x1000), (Access(0, True),), frozenset({0}), value
                )

    def test_report_shape_and_version(self):
        module = SfiModule(
            "svc", SandboxRegion(0x1000, 0x1000), (Access(0, True),), frozenset({0, 4}), 1.25
        )
        report = module.verify()
        self.assertEqual(report["schema"], "PK_SFI_MODULE/1")
        self.assertEqual(report["permitted_targets"], 2)
        self.assertEqual(report["overhead_percent"], 1.25)
        import re
        init_version = re.search(r'__version__ = "([^"]+)"', (PKG_DIR / "__init__.py").read_text()).group(1)
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), init_version)

    def test_schema_documents_are_valid_json_and_match_runtime_ids(self):
        module_schema = json.loads((PKG_DIR / "schemas" / "PK_SFI_MODULE_1.schema.json").read_text())
        mask_schema = json.loads((PKG_DIR / "schemas" / "PK_SFI_MASK_1.schema.json").read_text())
        self.assertEqual(module_schema["properties"]["schema"]["const"], core.MODULE_SCHEMA)
        self.assertEqual(mask_schema["properties"]["schema"]["const"], core.MASK_SCHEMA)


if __name__ == "__main__":
    unittest.main()
