"""Component 25: evidence disposition rules and gate behaviour (uses temp copies, never the live bundle)."""
import datetime as dt
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

try:
    from . import _path  # noqa: F401
except ImportError:
    import _path  # type: ignore # noqa: F401

from inv20_http_component_worlds import evidence_gate as eg

TODAY = dt.date(2026, 9, 23)
COMPS = [
    {"work_item": "WI-A", "status": "CLOSED_LOCAL", "maps_to": ["INV-20-C001"], "artifacts": ["a.py"], "tests": ["t.a"]},
    {"work_item": "WI-B", "status": "PARTIAL", "maps_to": ["INV-20-C002"], "artifacts": ["b.py"], "tests": ["t.b"]},
]


class DispositionTest(unittest.TestCase):
    def d(self, cid, groups, waivers=()):
        return eg.disposition(cid, COMPS, groups, list(waivers), TODAY, "BLOCKED")

    def test_pass_requires_closed_and_green(self):
        self.assertEqual(self.d("INV-20-C001", {"t.a": "pass"})["status"], "PASS")
        self.assertEqual(self.d("INV-20-C001", {"t.a": "fail"})["status"], "FAIL")
        self.assertEqual(self.d("INV-20-C001", {"t.a": "skip"})["status"], "BLOCKED")
        self.assertEqual(self.d("INV-20-C001", {})["status"], "BLOCKED")          # not run != pass

    def test_partial_blocks_and_unmapped_blocks(self):
        r = self.d("INV-20-C002", {"t.b": "pass"})
        self.assertEqual((r["status"], r["blocked_by"]), ("BLOCKED", ["WI-B"]))
        self.assertEqual(self.d("INV-20-C050", {})["blocked_by"], ["WI-INV20-01"])
        self.assertEqual(self.d("INV-20-C100", {})["status"], "BLOCKED")

    def test_waivers(self):
        good = {"id": "W1", "requirement": "INV-20-C002", "rationale": "r", "risk": "low", "compensating_control": "c",
                "owner": "sre", "approver": "cto", "created": "2026-09-01", "expires": "2026-12-01"}
        self.assertEqual(self.d("INV-20-C002", {"t.b": "pass"}, [good])["status"], "WAIVED")
        expired = dict(good, expires="2026-09-01")
        self.assertEqual(self.d("INV-20-C002", {"t.b": "pass"}, [expired])["status"], "BLOCKED")
        ownerless = dict(good, owner="UNASSIGNED")
        self.assertEqual(self.d("INV-20-C002", {"t.b": "pass"}, [ownerless])["status"], "BLOCKED")
        fail_waived = dict(good, requirement="INV-20-C001")
        self.assertEqual(self.d("INV-20-C001", {"t.a": "fail"}, [fail_waived])["status"], "FAIL")

    def test_group_status(self):
        o = {"tests.test_x.A.t1": "pass", "tests.test_x.A.t2": "skip:no", "tests.test_y.B.t": "error"}
        self.assertEqual(eg.group_status(o, "tests.test_x"), "skip")
        self.assertEqual(eg.group_status(o, "tests.test_y"), "fail")
        self.assertEqual(eg.group_status(o, "tests.test_z"), "missing")
        self.assertEqual(eg.group_status(o, "tests.test_x.A.t1"), "pass")


class GateTest(unittest.TestCase):
    def bundle(self, statuses=None, src="S"):
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        items = [{"check_id": f"INV-20-C{i:03d}", "status": (statuses or {}).get(i, "PASS")} for i in range(1, 101)]
        (d / "traceability.json").write_bytes(eg.canonical({"release": eg.__version__, "items": items}))
        rel = {"release": eg.__version__, "source_sha256": src, "evidence_files": {}, "signature": "sig",
               "traceability_sha256": eg._sha((d / "traceability.json").read_bytes()), "skipped_mandatory": []}
        (d / "release.json").write_text(json.dumps(rel))
        return d

    def run_gate(self, d, src="S", waivers=()):
        with mock.patch.object(eg, "source_digest", return_value=src), \
             mock.patch.object(eg, "_load_waivers", return_value=list(waivers)):
            return eg.gate(d)

    def test_go_only_when_all_green(self):
        self.assertEqual(self.run_gate(self.bundle())["verdict"], "GO")

    def test_blocked_and_fail(self):
        self.assertEqual(self.run_gate(self.bundle({5: "BLOCKED"}))["verdict"], "BLOCKED")
        self.assertEqual(self.run_gate(self.bundle({5: "FAIL"}))["verdict"], "NO_GO")

    def test_stale_tampered_missing(self):
        self.assertEqual(self.run_gate(self.bundle(), src="OTHER")["verdict"], "NO_GO")
        d = self.bundle()
        t = json.loads((d / "traceability.json").read_text()); t["items"][0]["status"] = "PASS"; t["x"] = 1
        (d / "traceability.json").write_text(json.dumps(t))
        self.assertEqual(self.run_gate(d)["verdict"], "NO_GO")
        d2 = self.bundle()
        t2 = json.loads((d2 / "traceability.json").read_text()); t2["items"].pop()
        (d2 / "traceability.json").write_bytes(eg.canonical(t2))
        rel = json.loads((d2 / "release.json").read_text()); rel["traceability_sha256"] = eg._sha((d2 / "traceability.json").read_bytes())
        (d2 / "release.json").write_text(json.dumps(rel))
        self.assertIn("requirement records missing or duplicated", self.run_gate(d2)["reasons"])
        self.assertEqual(self.run_gate(pathlib.Path(tempfile.gettempdir()) / "nope-inv20")["verdict"], "NO_GO")

    def test_expired_waiver_blocks(self):
        r = self.run_gate(self.bundle(), waivers=[{"id": "W", "expires": "2000-01-01"}])
        self.assertEqual(r["verdict"], "NO_GO")

    def test_unsigned_is_not_go(self):
        d = self.bundle()
        rel = json.loads((d / "release.json").read_text()); rel["signature"] = None
        (d / "release.json").write_text(json.dumps(rel))
        self.assertEqual(self.run_gate(d)["verdict"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
