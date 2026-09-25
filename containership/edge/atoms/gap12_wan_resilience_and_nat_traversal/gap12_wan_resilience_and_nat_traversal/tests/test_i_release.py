"""Group I — packaging, deployment and operations mechanisms."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PKG))
from gap12_wan_resilience_and_nat_traversal.tests._covers import covers  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import rollout, security as sec  # noqa: E402

sys.path.insert(0, os.path.join(PKG, "ops"))
sys.path.insert(0, os.path.join(PKG, "evidence"))


class BuildTest(unittest.TestCase):
    @covers("G12-I102:unit,impl-doc,reproducible", "G12-I101:reproducible")
    def test_two_builds_are_byte_identical(self):
        r = subprocess.run([sys.executable, "-B", os.path.join(PKG, "ops", "build.py"), "--check"], capture_output=True,
                           text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        h = [l.split()[1] for l in r.stdout.splitlines()]
        self.assertEqual(h[0], h[1])

    @covers("G12-I103:unit,impl-doc", "G12-I101:runtime-matrix")
    def test_dependencies_pinned_and_matrix_declared_in_metadata(self):
        with open(os.path.join(PKG, "pyproject.toml"), "rb") as fh:
            meta = tomllib.load(fh)
        self.assertEqual(meta["project"]["dependencies"], [])
        for dep in meta["project"]["optional-dependencies"]["e2e"]:
            self.assertRegex(dep, r"^[a-z0-9_-]+==\d+(\.\d+)+$")               # exact pins only
        cells = meta["tool"]["gap12"]["support-matrix"]["cells"]
        self.assertTrue(any(c["status"] == "verified" for c in cells))
        import sbom
        found = sbom.imports()
        third = {m for m in found if m not in sys.stdlib_module_names and m not in ("__future__", "pk_core")}
        self.assertEqual(third, {"cryptography"})

    @covers("G12-I104:spec1,unit,impl-doc")
    def test_sbom_bound_to_artifact_digest(self):
        import build
        import sbom
        d = tempfile.mkdtemp()
        art = os.path.join(d, "a.zip")
        dig = build.build(art)
        doc = sbom.sbom(dig, "4.3.0")
        self.assertEqual(doc["metadata"]["component"]["hashes"][0]["content"], dig)
        self.assertEqual([c["name"] for c in doc["components"] if c["type"] == "library"], ["cryptography"])
        self.assertTrue(all(c.get("licenses") for c in doc["components"] if c["type"] == "library"))
        prov = sbom.provenance("a.zip", dig, "0" * 64, "4.3.0", None)
        self.assertIsNone(prov["signature"])                                      # honest: unsigned


class CiTest(unittest.TestCase):
    @covers("G12-I105:spec2,unit,impl-doc", "G12-H085:no-skip", "G12-I116:spec1")
    def test_skipped_mandatory_job_fails_the_gate(self):
        import ci_gate
        ok = ci_gate.decide([{"job": "unit", "mandatory": True, "status": "PASS"},
                             {"job": "lab", "mandatory": True, "status": "PASS"}])
        self.assertEqual(ok["decision"], "PASS")
        for bad in ("SKIP", "UNKNOWN", "NOT-RUN", None):
            r = ci_gate.decide([{"job": "unit", "mandatory": True, "status": "PASS"},
                                {"job": "lab", "mandatory": True, "status": bad}])
            self.assertEqual(r["decision"], "NOT-EVIDENCED" if bad != "FAIL" else "FAIL", bad)
        r = ci_gate.decide([{"job": "bench", "mandatory": False, "status": "SKIP"},
                            {"job": "unit", "mandatory": True, "status": "PASS"}])
        self.assertEqual(r["decision"], "PASS")

    @covers("G12-I105:spec1,unit")
    def test_ci_script_separates_fast_and_privileged_lanes_on_one_revision(self):
        with open(os.path.join(PKG, "ops", "ci.sh")) as fh:
            text = fh.read()
        for lane in ("LANE fast", "LANE privileged-lab", "LANE bench", "LANE release", "LANE gate"):
            self.assertIn(lane, text)
        self.assertIn("SOURCE_DIGEST", text)


class RolloutTest(unittest.TestCase):
    @covers("G12-I107:unit,impl-doc,staged", "G12-I101:staged")
    def test_canary_stages_hold_without_evidence_and_rollback_on_breach(self):
        r = rollout.Rollout("4.3.0", "4.2.0", soak_s=100)
        self.assertTrue(r.compatibility(lambda a, b: (True, "PK_PATH_STATE/1 unchanged")))
        r.start(0)
        good = {"samples": 500, "error_rate": 0.001, "p95_establish_s": 0.8, "relay_ratio": 0.1}
        self.assertEqual(r.evaluate({"samples": 3}, 500), "running")
        self.assertEqual(r.fraction(), 0.01)                                    # no evidence -> no promotion
        r.evaluate(good, 100)
        self.assertEqual(r.fraction(), 0.10)
        r.pause("oncall")
        self.assertEqual(r.evaluate(good, 1000), "paused")
        r.resume("oncall", 1000)
        r.evaluate({**good, "error_rate": 0.2}, 1050)
        self.assertEqual((r.state, r.fraction()), ("rolled_back", 0.0))
        blocked = rollout.Rollout("5.0.0", "4.3.0")
        self.assertFalse(blocked.compatibility(lambda a, b: (False, "PK_PATH_STATE/2 breaks consumers")))
        with self.assertRaises(RuntimeError):
            blocked.start(0)

    @covers("G12-I108:spec1,spec2,unit,impl-doc", "G12-A010:fallback-policy", "G12-A008:fallback-policy",
            "G12-A009:fallback-policy")
    def test_kill_switch_signed_scoped_versioned_audited_with_safe_default(self):
        clk = [1000.0]
        audit = sec.AuditLog()
        ks = rollout.KillSwitch(b"op-key", node_scope={"env": "prod", "site": "ams"}, audit=audit, clock=lambda: clk[0])
        self.assertFalse(ks.enabled("upnp"))                                   # never-configured node: safe default
        self.assertTrue(ks.enabled("relay"))
        ctl = lambda v, **k: rollout.sign_control(b"op-key", {"version": v, "expires": clk[0] + 60, **k})
        self.assertEqual(ks.apply(ctl(1, disable=["hole-punch"], scope={"env": "prod"}), actor="alice"), "OK")
        self.assertFalse(ks.enabled("hole-punch"))                             # active + new sessions consult this
        self.assertEqual(ks.apply(ctl(1, enable=["hole-punch"]), actor="mallory"), "AUTH_REPLAY")
        self.assertEqual(ks.apply(rollout.sign_control(b"wrong", {"version": 9, "expires": 2e9, "enable": ["hole-punch"]}),
                                  actor="mallory"), "AUTH_INTEGRITY")
        self.assertEqual(ks.apply(ctl(2, disable=["relay"], scope={"site": "fra"}), actor="alice"), "OK")
        self.assertTrue(ks.enabled("relay"))                                   # out of scope
        clk[0] += 61
        self.assertTrue(ks.enabled("hole-punch"))                              # expired disable reverts
        self.assertTrue(sec.AuditLog.verify(audit.entries)[0])
        self.assertEqual([e["event"] for e in audit.entries],
                         ["killswitch_applied", "killswitch_rejected", "killswitch_rejected", "killswitch_out_of_scope"])


class WaiverGateTest(unittest.TestCase):
    @covers("G12-I115:unit,impl-doc", "G12-I116:spec2,unit,impl-doc,gate")
    def test_waivers_need_signature_owner_expiry_and_expire_automatically(self):
        import waivers
        keys = {"approver-1": b"k1"}
        w = waivers.sign({"id": "W-1", "item": "G12-A015-01", "owner": "net-team", "scope": "QUIC",
                          "rationale": "no QUIC stack", "compensating_control": "TLS/TCP fallback",
                          "expires": 2000.0, "approver": "approver-1"}, b"k1")
        self.assertEqual(waivers.valid(w, keys, now=1000.0), (True, "OK"))
        self.assertEqual(waivers.valid(w, keys, now=2001.0), (False, "expired"))
        forged = dict(w, expires=9e9)
        self.assertEqual(waivers.valid(forged, keys, now=1000.0), (False, "bad signature"))
        incomplete = waivers.sign({"id": "W-2", "item": "x", "expires": 2000.0, "approver": "approver-1"}, b"k1")
        self.assertEqual(waivers.valid(incomplete, keys, now=1000.0)[1], "missing fields")
        self.assertEqual(waivers.valid(w, {}, now=1000.0), (False, "unknown approver"))
        with open(os.path.join(PKG, "ops", "waivers.json")) as fh:
            reg = json.load(fh)
        self.assertEqual(reg["waivers"], [])                                    # none granted: nobody to grant them


class EvaluatorFalsifierTest(unittest.TestCase):
    """The gate must refuse fabricated claims, and must still be able to open with
    real (here: synthetic, clearly labelled) approvals - a gate, not a wall."""

    def _run(self, tests_doc, waivers_doc=None):
        import shutil
        d = tempfile.mkdtemp(prefix="NOT_THE_DELIVERED_")
        with open(os.path.join(d, "test_results.json"), "w") as fh:
            json.dump(tests_doc, fh)
        args = [sys.executable, "-B", os.path.join(PKG, "evidence", "evaluate.py"), "--out", d]
        if waivers_doc is not None:
            wp = os.path.join(d, "NOT_THE_DELIVERED_waivers.json")
            with open(wp, "w") as fh:
                json.dump(waivers_doc, fh)
            args += ["--waivers", wp]
        r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        with open(os.path.join(d, "evaluation.json")) as fh:
            ev = json.load(fh)
        shutil.rmtree(d)
        return r.returncode, {c["component"]: c for c in ev["components"]}

    @covers("G12-I116:spec1,gate", "G12-H100:unit,impl-doc", "G12-H085:no-skip")
    def test_fabricated_and_skipped_claims_are_refused(self):
        build = {"source_digest": "x" * 64}
        fake = {"build": build, "tests": [
            {"id": "fake.skip", "status": "SKIP", "covers": [["G12-B020", "unit"]]},
            {"id": "fake.owner", "status": "PASS", "covers": [["G12-B020", "owners"]]}]}
        rc, comps = self._run(fake)
        self.assertEqual(rc, 0)
        items = {i["kind"]: i for i in comps["G12-B020"]["items"]}
        self.assertEqual(items["unit"]["status"], "NOT-EVIDENCED")          # a SKIP credits nothing
        self.assertEqual(items["owners"]["status"], "NOT-EVIDENCED")        # a test cannot appoint a human
        rc, _ = self._run({"build": build, "tests": [{"id": "t", "status": "PASS", "covers": [["G12-B020", "spec1"]]}]})
        self.assertEqual(rc, 2)                                            # tag for a kind B020 does not have
        unsigned = {"approver_registry": {"synthetic": "k"}, "waivers": [
            {"id": "W", "item": "G12-B020-10", "owner": "o", "scope": "s", "rationale": "r",
             "compensating_control": "c", "expires": time.time() + 3600, "approver": "synthetic", "sig": "0" * 64}]}
        _, comps = self._run(fake, unsigned)
        self.assertEqual({i["kind"]: i for i in comps["G12-B020"]["items"]}["owners"]["status"], "NOT-EVIDENCED")

    @covers("G12-I116:gate", "G12-I115:unit")
    def test_gate_opens_with_synthetic_approvals_proving_it_is_not_a_wall(self):
        import waivers
        real = {"build": {"source_digest": "y" * 64}, "tests": []}          # self-contained: no dependence on a prior run
        _, comps = self._run(real)
        open_items = [i["id"] for i in comps["G12-B020"]["items"] if i["status"] != "PASS" and i["kind"] != "exit"]
        self.assertEqual(comps["G12-B020"]["items"][-1]["status"], "NOT-EVIDENCED")
        key = b"SYNTHETIC-APPROVER-KEY-NOT-A-REAL-PERSON"
        ws = [waivers.sign({"id": f"SYN-{n}", "item": i, "owner": "synthetic-owner", "scope": "probe",
                            "rationale": "falsifier probe", "compensating_control": "none (probe)",
                            "expires": time.time() + 3600, "approver": "synthetic"}, key) for n, i in enumerate(open_items)]
        _, comps = self._run(real, {"approver_registry": {"synthetic": key.decode()}, "waivers": ws})
        self.assertEqual(comps["G12-B020"]["items"][-1]["status"], "PASS")      # gate opens only with approvals
        self.assertTrue(all(i["status"] in ("PASS", "WAIVED") for i in comps["G12-B020"]["items"]))


class DocsTest(unittest.TestCase):
    @covers("G12-I109:unit", "G12-I110:unit", "G12-I111:unit", "G12-I112:unit", "G12-I113:unit", "G12-I114:unit")
    def test_operations_documents_exist_with_required_sections(self):
        req = {"RUNBOOK_DAY0.md": ["Preconditions", "Diagnostics", "Decision points", "Rollback", "Evidence to retain"],
               "RUNBOOK_DAY1.md": ["Preconditions", "Diagnostics", "Decision points", "Rollback", "Evidence to retain"],
               "RUNBOOK_DAY2.md": ["Preconditions", "Diagnostics", "Decision points", "Rollback", "Evidence to retain"],
               "INCIDENT_MATRIX.md": ["SEV1", "SEV2", "SEV3", "Paging"],
               "BACKUP_RECONSTRUCTION.md": ["Durable", "Reconstructable", "Discarded"],
               "COMPATIBILITY_EOL.md": ["Compatibility", "End of life"]}
        for f, heads in req.items():
            with open(os.path.join(PKG, "docs", f)) as fh:
                t = fh.read()
            for h in heads:
                self.assertIn(h, t, f"{f}: {h}")


if __name__ == "__main__":
    unittest.main()
