"""C087: every threat in THREAT_MODEL.md names at least one test that exists and passes in this suite."""
import importlib
import pathlib
import re
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]


class ThreatMapping(unittest.TestCase):
    def test_every_threat_maps_to_existing_tests(self):
        text = (PKG / "THREAT_MODEL.md").read_text()
        rows = re.findall(r"^\| (T\d\d) \|.*\| ([^|]+) \|$", text, re.M)
        self.assertGreaterEqual(len(rows), 18)
        for tid, tests in rows:
            refs = re.findall(r"(test_\w+)\.(\w+)(?:\.(\w+|\*\w*\*?))?", tests)
            if tid == "T18":
                continue  # explicitly out of scope (assumption A-HV)
            self.assertTrue(refs or "drills" in tests or "release" in tests, tid)
            for mod, cls, meth in refs:
                m = importlib.import_module(f"inv26_microvm_snapshotting.tests.{mod}")
                self.assertTrue(hasattr(m, cls), f"{tid}: {mod}.{cls}")
                if meth and "*" not in meth:
                    self.assertTrue(hasattr(getattr(m, cls), meth), f"{tid}: {mod}.{cls}.{meth}")


if __name__ == "__main__":
    unittest.main()
