"""P2 governance: C49 traceability stability, C54 waiver register, C55 production gate
(fail-closed with missing/failed/stale evidence), C56 master document consistency, C48 ADRs."""
import copy, datetime as dt, json, re, shutil, sys, tempfile, unittest
from pathlib import Path
from _util import T  # noqa: F401  (sets sys.path)
from gap04_disconnected_operation_controller.runtime import gate

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
import check_docs  # noqa: E402


class Traceability(unittest.TestCase):
    def test_T_C49_control_ids_stable_and_complete(self):
        src = (PKG / "tools" / "checklist_source.md").read_text()
        ids = re.findall(r"\*\*(GAP04-C\d\d-\d\d\d)\*\*", src)
        frozen = (Path(__file__).parent / "fixtures" / "control_ids.v1.txt").read_text().split()
        self.assertEqual(ids, frozen, "control IDs renumbered/deleted without migration")
        st = json.loads((PKG / "evidence" / "CHECKLIST_STATUS.json").read_text())
        self.assertEqual(sorted(st["controls"]), sorted(frozen))
        self.assertEqual(len(frozen), 1456)
        # component roll-ups must agree with the individual controls (guards the 4.3.0 slicing bug)
        for comp, meta in st["components"].items():
            ctl = [c["status"] for k, c in st["controls"].items() if k.split("-")[1] == "C" + comp]
            self.assertEqual(len(ctl), 26, comp)
            self.assertEqual(meta["counts"], {s: ctl.count(s) for s in "x~!- "}, comp)
            if meta["final_status"] == "Verified":
                self.assertTrue(all(s == "x" for s in ctl), comp)
        for cid, c in st["controls"].items():
            self.assertIn(c["status"], "x~!- ")
            if c["status"] == "x":
                self.assertTrue(c["evidence"], f"{cid} verified without evidence")
            else:
                self.assertTrue(c["note"], f"{cid} not verified but no reason recorded")
            for w in c["waivers"]:
                self.assertRegex(w, r"^W-\d{3}$")

    def test_T_C49_rtm_covers_original_100(self):
        rtm = json.loads((PKG / "evidence" / "RTM.json").read_text())["items"]
        ck = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
        self.assertEqual([r["check_id"] for r in rtm], [c["check_id"] for c in ck])
        for r in rtm:
            self.assertTrue(r["artifacts"]); self.assertTrue(r["components"])


class Waivers(unittest.TestCase):
    def test_T_C54_register_well_formed(self):
        w = json.loads((PKG / "evidence" / "waivers.json").read_text())["waivers"]
        ids = [x["id"] for x in w]
        self.assertEqual(len(ids), len(set(ids)))
        for x in w:
            for k in ("risk", "rationale", "compensating_controls", "created", "review_by", "expires"):
                self.assertTrue(x[k], (x["id"], k))
            self.assertLess(dt.date.fromisoformat(x["created"]), dt.date.fromisoformat(x["expires"]))


class Gate(unittest.TestCase):
    def _ev(self):
        d = Path(tempfile.mkdtemp())
        for f in ("CHECKLIST_STATUS.json", "waivers.json"):
            shutil.copy(PKG / "evidence" / f, d / f)
        (d / "test_results.json").write_text(json.dumps({"failed": 0, "errors": 0, "date": dt.date.today().isoformat(), "ci_run_id": "ci-1"}))
        return d

    def _make_pass(self, d):
        st = json.loads((d / "CHECKLIST_STATUS.json").read_text())
        for c in st["controls"].values():
            c["status"] = "x"; c["evidence"] = c["evidence"] or ["synthetic"]
        (d / "CHECKLIST_STATUS.json").write_text(json.dumps(st))
        w = json.loads((d / "waivers.json").read_text())
        for x in w["waivers"]:
            x.update(status="approved", approver="sec-lead", owner="owner")
        (d / "waivers.json").write_text(json.dumps(w))
        (d / "approvals.json").write_text(json.dumps({r: {"name": f"{r}-lead", "date": "2026-09-22"} for r in gate.REQUIRED_APPROVALS}))

    def test_T_C55_current_evidence_is_no_go(self):
        r = gate.evaluate(PKG / "evidence", archive_sha256="0" * 64)
        self.assertEqual(r["decision"], "NO_GO")
        self.assertTrue(any("P0 controls not verified" in x for x in r["reasons"]))
        self.assertTrue(any("missing named approval" in x for x in r["reasons"]))
        self.assertTrue(all(r["summary"][p] > 0 for p in ("P0", "P1", "P2")), r["summary"])

    def test_T_C55_pass_only_with_complete_evidence(self):
        d = self._ev(); self._make_pass(d)
        self.assertEqual(gate.evaluate(d, archive_sha256="a" * 64)["decision"], "PASS")
        self.assertEqual(gate.evaluate(d, archive_sha256=None)["decision"], "NO_GO")          # not bound to artifact

    def test_T_C55_fail_closed_on_each_defect(self):
        mutations = [
            lambda d: (d / "test_results.json").unlink(),
            lambda d: (d / "test_results.json").write_text(json.dumps({"failed": 1, "errors": 0, "date": dt.date.today().isoformat(), "ci_run_id": "c"})),
            lambda d: (d / "test_results.json").write_text(json.dumps({"failed": 0, "errors": 0, "date": "2020-01-01", "ci_run_id": "c"})),
            lambda d: (d / "test_results.json").write_text(json.dumps({"failed": 0, "errors": 0, "date": dt.date.today().isoformat()})),
            lambda d: (d / "approvals.json").unlink(),
        ]
        def one_control(d, st_, field):
            st = json.loads((d / "CHECKLIST_STATUS.json").read_text())
            k = next(iter(st["controls"]))
            st["controls"][k][field] = st_
            (d / "CHECKLIST_STATUS.json").write_text(json.dumps(st))
        mutations += [lambda d: one_control(d, "~", "status"), lambda d: one_control(d, [], "evidence")]
        def waiver(d, **kw):
            w = json.loads((d / "waivers.json").read_text()); w["waivers"][0].update(kw); (d / "waivers.json").write_text(json.dumps(w))
        mutations += [lambda d: waiver(d, expires="2020-01-01"), lambda d: waiver(d, status="proposed"), lambda d: waiver(d, owner=None)]
        for i, mut in enumerate(mutations):
            d = self._ev(); self._make_pass(d); mut(d)
            self.assertEqual(gate.evaluate(d, archive_sha256="a" * 64)["decision"], "NO_GO", f"mutation {i}")


class Docs(unittest.TestCase):
    def test_T_C56_master_and_docs_consistent(self):
        self.assertEqual(check_docs.check(), [])

    def test_T_C48_adrs_have_status_and_links(self):
        adrs = sorted((PKG / "docs" / "ADR").glob("ADR-*.md"))
        self.assertGreaterEqual(len(adrs), 8)
        for a in adrs:
            t = a.read_text()
            self.assertRegex(t, r"\*\*Status:\*\* (Proposed|Accepted|Superseded|Deprecated|Rejected)")
            for h in ("## Context", "## Decision", "## Alternatives considered", "## Consequences"):
                self.assertIn(h, t)


if __name__ == "__main__":
    unittest.main()
