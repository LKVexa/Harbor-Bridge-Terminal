"""Bounded fuzz run inside the unit suite (C085); the release gate runs tools/fuzz.py at scale.

Regressions found by this pass and pinned here:
  FZ-1 config.validate crashed (AttributeError) when a section was not an object.
  FZ-2 open_envelope raised KeyError on envelope metadata missing fields (unvalidated).
  FZ-3 config.validate raised KeyError when a nested section lacked a key (found by the evidence run).
"""
import unittest

from inv26_microvm_snapshotting import config as cfgmod, crypto
from inv26_microvm_snapshotting.errors import SnapshotServiceError
from inv26_microvm_snapshotting.tools import fuzz


class FuzzTests(unittest.TestCase):
    def test_bounded_run_has_no_findings(self):
        res = fuzz.run(450, seed=7)
        self.assertEqual(res["findings"], [])

    def test_regression_fz1_config_sections(self):
        for bad in (14, [], "x", None):
            doc = cfgmod.example()
            doc["quotas"] = bad
            self.assertTrue(cfgmod.validate(doc))

    def test_regression_fz3_config_nested_keys(self):
        doc = cfgmod.example()
        del doc["telemetry"]["log_level"]
        self.assertIn("telemetry.log_level: required", cfgmod.validate(doc))

    def test_regression_fz2_envelope_metadata(self):
        with self.assertRaises(SnapshotServiceError):
            crypto.open_envelope(b"x", env={"alg": crypto.ENVELOPE_ALG, "aad_schema": crypto.AAD_SCHEMA},
                                 ctx={}, kms=crypto.LocalKeyService())


if __name__ == "__main__":
    unittest.main()
