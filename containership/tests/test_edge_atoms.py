"""UC-2.8.0 edge-atom integration: inventory, integrity, bindings, isolation and refusal paths."""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ship"))
from unikernel import Refusal  # noqa: E402
from unikernel import edge_atoms as X  # noqa: E402


def _synthetic_ship(d: Path, *, failing: bool = False) -> Path:
    """A minimal ship with one atom archive, extracted exactly as the installer does."""
    src = d / "edge" / "source"; src.mkdir(parents=True)
    (d / "pk").mkdir()
    body = "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(%s)\n" % ("False" if failing else "True")
    zp = src / "gap99_demo_v1.0.0.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("gap99_demo/__init__.py", "")
        z.writestr("gap99_demo/VERSION", "1.0.0\n")
        z.writestr("gap99_demo/tests/test_demo.py", body)
    atom_dir = d / "edge" / "atoms" / "gap99_demo"
    with zipfile.ZipFile(zp) as z:
        z.extractall(atom_dir)
    h = hashlib.sha256(zp.read_bytes()).hexdigest()
    m = {"schema": "UC/EDGE_ATOMS/1", "candidate": "UC-2.8.0", "requested_archives": 1, "stored_unique_archives": 1,
         "byte_identical_duplicates": 0, "elements": 1, "variants": 0,
         "archives": [{"archive": zp.name, "sha256": h, "element": "GAP-99", "stored_as": f"source/{zp.name}",
                       "role": "canonical", "installed_at": "atoms/gap99_demo"}],
         "atoms": [{"element": "GAP-99", "key": "gap99_demo", "path": "atoms/gap99_demo", "archive": zp.name,
                    "sha256": h, "package_root": "atoms/gap99_demo", "package_version": "1.0.0",
                    "tests": "atoms/gap99_demo/gap99_demo/tests"}]}
    (d / "edge" / "EDGE_MANIFEST.json").write_text(json.dumps(m))
    (d / "pk" / "PK_ATOM_BINDINGS.json").write_text(json.dumps({"bindings": {"GAP-99": {"pk_component": None}}}))
    return d


class ShippedInventory(unittest.TestCase):
    def test_manifest_counts(self):
        m = X.manifest(str(ROOT))
        self.assertEqual(m["requested_archives"], 99)
        self.assertEqual(m["stored_unique_archives"], 91)
        self.assertEqual(m["byte_identical_duplicates"], 8)
        self.assertEqual(m["elements"], 86)
        self.assertEqual(m["variants"], 4)
        self.assertEqual(len({a["element"] for a in m["atoms"]}), 86)

    def test_every_archive_has_one_role(self):
        roles = {r["role"] for r in X.manifest(str(ROOT))["archives"]}
        self.assertEqual(roles, {"canonical", "variant", "duplicate", "release-evidence"})

    def test_integrity_shallow_and_deep(self):
        self.assertTrue(X.check(str(ROOT))["pass"])
        r = X.check(str(ROOT), deep=True)
        self.assertTrue(r["pass"], r["problems"][:5])
        self.assertGreater(r["files_compared"], 10000)

    def test_bindings_resolve(self):
        b = X.bindings(str(ROOT))["bindings"]
        for el, v in b.items():
            self.assertTrue((ROOT / v["atom"]).is_dir(), el)
            if v["pk_component"]:
                self.assertTrue((ROOT / v["pk_component"] / "CHECKLIST.json").is_file(), el)
        self.assertEqual(sum(1 for v in b.values() if v["pk_component"]), 85)

    def test_status_never_claims_pass(self):
        s = X.status(str(ROOT))
        self.assertIn("not Production GO", s["boundaries"])
        self.assertNotIn("PASS", json.dumps(s["recorded_evidence"]["verdicts"]))

    def test_refusals(self):
        with self.assertRaises(Refusal):
            X.atom("../etc", str(ROOT))
        with self.assertRaises(Refusal):
            X.atom("INV-99", str(ROOT))


class SyntheticShip(unittest.TestCase):
    def test_tamper_detected(self):
        with tempfile.TemporaryDirectory() as t:
            d = _synthetic_ship(Path(t))
            self.assertTrue(X.check(str(d), deep=True)["pass"])
            (d / "edge/atoms/gap99_demo/gap99_demo/VERSION").write_text("9.9.9\n")
            r = X.check(str(d), deep=True)
            self.assertFalse(r["pass"]); self.assertTrue(any("modified" in p for p in r["problems"]))

    def test_extra_file_and_archive_detected(self):
        with tempfile.TemporaryDirectory() as t:
            d = _synthetic_ship(Path(t))
            (d / "edge/atoms/gap99_demo/gap99_demo/implant.py").write_text("x=1\n")
            (d / "edge/source/stray.zip").write_bytes(b"PK")
            probs = X.check(str(d), deep=True)["problems"]
            self.assertTrue(any("unrecorded file" in p for p in probs))
            self.assertTrue(any("unrecorded archive" in p for p in probs))

    def test_archive_corruption_detected(self):
        with tempfile.TemporaryDirectory() as t:
            d = _synthetic_ship(Path(t))
            p = d / "edge/source/gap99_demo_v1.0.0.zip"; p.write_bytes(p.read_bytes() + b"\0")
            self.assertTrue(any("sha256 mismatch" in x for x in X.check(str(d))["problems"]))

    def test_isolated_runner_green_and_red(self):
        for failing, verdict in ((False, "SUITE_GREEN"), (True, "SUITE_RED")):
            with tempfile.TemporaryDirectory() as t:
                d = _synthetic_ship(Path(t), failing=failing)
                a = X.manifest(str(d))["atoms"][0]
                r = X.run_atom(a, str(d), deadline_s=120, use_pytest=False)
                self.assertEqual(r["verdict"], verdict, r)
                self.assertEqual(r["passed"], 0 if failing else 1)

    def test_suite_writes_never_reach_sealed_atom(self):
        with tempfile.TemporaryDirectory() as t:
            d = _synthetic_ship(Path(t))
            tp = d / "edge/atoms/gap99_demo/gap99_demo/tests/test_demo.py"
            # rewrite the archive-matching file only inside the zip-derived tree via a fresh archive
            body = ("import os, unittest\nclass T(unittest.TestCase):\n    def test_write(self):\n"
                    "        p=os.path.join(os.path.dirname(__file__),'..','VERSION')\n"
                    "        open(p,'w').write('mutated')\n")
            zp = d / "edge/source/gap99_demo_v1.0.0.zip"
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("gap99_demo/__init__.py", ""); z.writestr("gap99_demo/VERSION", "1.0.0\n")
                z.writestr("gap99_demo/tests/test_demo.py", body)
            tp.write_text(body)
            m = json.loads((d / "edge/EDGE_MANIFEST.json").read_text())
            h = hashlib.sha256(zp.read_bytes()).hexdigest(); m["archives"][0]["sha256"] = h; m["atoms"][0]["sha256"] = h
            (d / "edge/EDGE_MANIFEST.json").write_text(json.dumps(m))
            self.assertEqual(X.run_atom(m["atoms"][0], str(d), deadline_s=120, use_pytest=False)["verdict"], "SUITE_GREEN")
            self.assertEqual((d / "edge/atoms/gap99_demo/gap99_demo/VERSION").read_text(), "1.0.0\n")
            self.assertTrue(X.check(str(d), deep=True)["pass"])
            self.assertEqual(list((d / "_runs/edge/work").iterdir()), [])

    def test_runner_does_not_leak_ship_path(self):
        with tempfile.TemporaryDirectory() as t:
            d = _synthetic_ship(Path(t))
            (d / "edge/atoms/gap99_demo/gap99_demo/tests/test_demo.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n    def test_no_ship(self):\n"
                "        import importlib.util\n        self.assertIsNone(importlib.util.find_spec('unikernel'))\n")
            a = X.manifest(str(d))["atoms"][0]
            self.assertEqual(X.run_atom(a, str(d), deadline_s=120, use_pytest=False)["verdict"], "SUITE_GREEN")


class Cli(unittest.TestCase):
    def _uc(self, *args):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        p = subprocess.run([sys.executable, "-B", str(ROOT / "uc.py"), *args], capture_output=True, text=True, env=env, timeout=300)
        return p.returncode, p.stdout

    def test_status_and_show(self):
        rc, out = self._uc("edge", "status")
        self.assertEqual(rc, 0); self.assertEqual(json.loads(out)["elements"], 86)
        rc, out = self._uc("edge", "show", "pln07")
        self.assertNotEqual(rc, 0)
        rc, out = self._uc("edge", "show", "PLN-07")
        self.assertEqual(rc, 0); self.assertEqual(json.loads(out)["atom"]["key"], "pln07_security_plane")

    def test_platform_status_reports_edge(self):
        rc, out = self._uc("platform", "status")
        self.assertEqual(rc, 0)
        v = json.loads(out)
        self.assertEqual(v["candidate"], "UC-2.8.0"); self.assertEqual(v["edge_atoms"]["elements"], 86)


if __name__ == "__main__":
    unittest.main()
