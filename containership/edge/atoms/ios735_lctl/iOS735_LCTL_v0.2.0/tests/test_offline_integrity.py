from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class OfflineIntegrityTests(unittest.TestCase):
    def run_py(self, *args):
        return subprocess.run(
            [PYTHON, "-B", *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    def test_canonical_round_trip_and_map(self):
        cp = self.run_py(ROOT / "tools/check_translation.py")
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertIn("735/735", cp.stdout)

    def test_falsifiers_are_all_caught(self):
        cp = self.run_py(ROOT / "tools/check_translation.py", "--falsify")
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(cp.stdout.count("falsifier CAUGHT:"), 9, cp.stdout)
        self.assertNotIn("falsifier MISSED:", cp.stdout)

    def test_translation_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory(prefix="ios735-translate-test-") as td:
            out = Path(td)
            cp = self.run_py(
                ROOT / "tools/translate.py",
                ROOT / "input/iOS735_Skeleton",
                "--out",
                out,
            )
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            expected_sources = sorted((ROOT / "source").glob("*.lctlc"))
            actual_sources = sorted((out / "source").glob("*.lctlc"))
            self.assertEqual([p.name for p in actual_sources], [p.name for p in expected_sources])
            for expected, actual in zip(expected_sources, actual_sources):
                self.assertEqual(actual.read_bytes(), expected.read_bytes(), expected.name)
            self.assertEqual(
                (out / "map/TRANSLATION_MAP.json").read_bytes(),
                (ROOT / "map/TRANSLATION_MAP.json").read_bytes(),
            )

    def test_release_manifest(self):
        cp = self.run_py(ROOT / "tools/manifest.py")
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertIn("MANIFEST.sha256 verified", cp.stdout)

    def test_repository_shape_and_historical_evidence(self):
        self.assertEqual(len(list((ROOT / "source").glob("*.lctlc"))), 44)
        self.assertEqual(len(list((ROOT / "canonical").glob("*.lctl"))), 44)
        for command in ("causal-dag", "parallel-plan", "provenance"):
            self.assertEqual(len(list((ROOT / "evidence/lctl160" / command).glob("*.txt"))), 44)
        data = json.loads((ROOT / "evidence/VERIFY.json").read_text(encoding="utf-8"))
        self.assertEqual(data.get("verdict"), "PASS")
        self.assertEqual(data.get("units"), 44)


if __name__ == "__main__":
    unittest.main()
