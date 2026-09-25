"""MC-01 - pk_core preflight: absent, wrong version, corrupt -> BLOCKED; never GO."""
import json
import pathlib
import sys
import tempfile
import unittest

from _helpers import ROOT  # noqa: F401

from inv19_os_asynchronous_analogues.tools import pk_core_preflight as pf


def fake_pk(root: pathlib.Path, version: str, corrupt: bool = False) -> None:
    p = root / "pk_core"
    p.mkdir()
    (p / "__init__.py").write_text(f"__version__ = {version!r}\n")
    for m in ("checklist", "component", "contract"):
        (p / f"{m}.py").write_text("raise ImportError('half-installed')\n" if corrupt and m == "component" else "X = 1\n")


class PreflightTest(unittest.TestCase):
    def tearDown(self):
        for k in [m for m in sys.modules if m == "pk_core" or m.startswith("pk_core.")]:
            del sys.modules[k]

    def test_absent_is_blocked(self):
        r = pf.preflight(env_path="/nonexistent-pk")
        self.assertEqual(r["result"], "BLOCKED")
        self.assertTrue(any(x.startswith("DEPENDENCY_UNAVAILABLE") for x in r["reasons"]))

    def test_unresolved_lock_blocks_even_when_installed(self):
        with tempfile.TemporaryDirectory() as d:
            fake_pk(pathlib.Path(d), "9.9.9")
            r = pf.preflight(env_path=d)
        self.assertEqual(r["result"], "BLOCKED")
        self.assertIn("LOCK_UNRESOLVED", " ".join(r["reasons"]))
        self.assertEqual(r["dev_override"], "PK_CORE_PATH")

    def test_wrong_version_and_corrupt_install_block(self):
        lock = json.loads(pf.LOCK.read_text())
        pinned = dict(lock, status="PINNED", version="1.2.3")
        with tempfile.TemporaryDirectory() as d, tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as lf:
            json.dump(pinned, lf); lf.flush()
            old = pf.LOCK
            pf.LOCK = pathlib.Path(lf.name)
            try:
                fake_pk(pathlib.Path(d), "1.2.4")
                r = pf.preflight(env_path=d)
                self.assertIn("VERSION_MISMATCH", " ".join(r["reasons"]))
                self.tearDown()
                d2 = tempfile.mkdtemp()
                fake_pk(pathlib.Path(d2), "1.2.3", corrupt=True)
                r2 = pf.preflight(env_path=d2)
                self.assertIn("DEPENDENCY_CORRUPT", " ".join(r2["reasons"]))
                self.tearDown()
                d3 = tempfile.mkdtemp()
                fake_pk(pathlib.Path(d3), "1.2.3")
                r3 = pf.preflight(env_path=d3)
                self.assertEqual(r3["result"], "GO")   # the gate CAN pass once genuinely pinned
            finally:
                pf.LOCK = old
        self.assertEqual(r["result"], "BLOCKED")
        self.assertEqual(r2["result"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
