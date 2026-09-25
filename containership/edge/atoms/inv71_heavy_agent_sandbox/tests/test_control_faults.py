"""Fault injection, conformance fixtures, fuzz regression, limit boundaries, pk_core probe."""
import hashlib
import json
import pathlib
import random
import shutil
import tempfile
import unittest

from _harness import FAKE_ARTIFACTS, Answer, build, token

from inv71_heavy_agent_sandbox.control import config as cfgmod
from inv71_heavy_agent_sandbox.control import controller as ctlmod
from inv71_heavy_agent_sandbox.control.errors import ControlError
from inv71_heavy_agent_sandbox.control.lifecycle import LeaseTable, State
from inv71_heavy_agent_sandbox.control.resilience import Shape
from inv71_heavy_agent_sandbox.control.runtime_plan import plan_session, reconcile
from inv71_heavy_agent_sandbox.sandbox import canonicalize_host

PKG = pathlib.Path(__file__).resolve().parents[1]


class FaultInjectionTest(unittest.TestCase):
    """[C060][C051][C057][C037][C089][C055] faults tied to governance/failure_matrix.json."""

    def test_matrix_rows_have_scenarios(self):
        m = json.loads((PKG / "governance" / "failure_matrix.json").read_text())
        ids = set()
        for r in m["rows"]:
            self.assertTrue(r["scenario"].startswith(("ref:", "BLOCKED:")), r["id"])
            if r["scenario"].startswith("ref:"):
                mod, cls, meth = r["scenario"][4:].split(".")
                src = (PKG / "tests" / f"{mod}.py").read_text()
                self.assertIn(f"class {cls}", src, r["id"])
                self.assertIn(f"def {meth}", src, r["id"])
            ids.add(r["id"])
        self.assertEqual(len(ids), len(m["rows"]))

    def test_create_phase_faults(self):
        """Inject a fault at every create phase; no phase may leak admission or leave a READY session."""
        for phase in ("plan", "guest", "lease"):
            c, ta, clock, *_ = build()
            orig_plan, orig_new, orig_check = ctlmod.plan_session, ctlmod.new_session, c.leases.check
            try:
                if phase == "plan":
                    ctlmod.plan_session = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("jailer exited 1"))
                elif phase == "guest":
                    ctlmod.new_session = lambda *a, **k: (_ for _ in ()).throw(OSError("kvm busy"))
                else:
                    c.leases.check = lambda *a, **k: (_ for _ in ()).throw(ControlError("LIFECYCLE.STALE_EPOCH"))
                with self.assertRaises(ControlError):
                    c.create(token(ta), sid="f1", tenant="t1", shape=Shape(1, 512), idempotency_key=phase)
            finally:
                ctlmod.plan_session, ctlmod.new_session, c.leases.check = orig_plan, orig_new, orig_check
            self.assertEqual(c.admission.usage("t1"), (0, 0, 0), phase)
            self.assertNotIn("f1", c.sessions, phase)
            # the retry with the same key after recovery succeeds (no poisoned idempotency entry)
            self.assertEqual(c.create(token(ta), sid="f1", tenant="t1", shape=Shape(1, 512), idempotency_key=phase)["state"], "READY")

    def test_node_crash_orphans(self):
        """After a node restart the controller's plans are gone; every observed heavybox resource is an orphan."""
        a = plan_session("a", cfgmod.merge({}), FAKE_ARTIFACTS)
        observed = set(a.owned)
        r = reconcile([], observed, closing=[])
        self.assertTrue(r.verified)  # nothing *closing* leaked...
        self.assertGreaterEqual(len(r.orphans), 6)  # ...but every hb- resource is flagged for reaping

    def test_partition_reconnect(self):
        """Controller A partitioned; B takes over (epoch 2). A's late teardown is fenced; B's succeeds."""
        leases = LeaseTable()
        c, ta, clock, *_ = build()
        c.leases = leases
        r = c.create(token(ta), sid="p1", tenant="t1", shape=Shape(1, 512), idempotency_key="p")
        leases.acquire("p1", "controller-b")
        with self.assertRaises(ControlError) as cm:
            c.teardown(token(ta), sid="p1", epoch=r["epoch"])
        self.assertEqual(cm.exception.code.code, "LIFECYCLE.STALE_EPOCH")
        c.owner = "controller-b"
        self.assertTrue(c.teardown(token(ta), sid="p1", epoch=leases.current("p1").epoch)["verified"])

    def test_resolver_flapping_never_serves_stale(self):
        c, ta, clock, res, *_ = build()
        c.create(token(ta), sid="r1", tenant="t1", shape=Shape(1, 512), idempotency_key="r")
        c.connect(token(ta), sid="r1", host="pypi.org", port=443)
        res.answers["pypi.org"] = Answer((), ("169.254.169.254",), 5)
        clock.advance(61)
        with self.assertRaises(ControlError):
            c.connect(token(ta), sid="r1", host="pypi.org", port=443)
        res.down = True
        clock.advance(10)
        with self.assertRaises(ControlError) as cm:
            c.connect(token(ta), sid="r1", host="pypi.org", port=443)
        self.assertEqual(cm.exception.code.code, "POLICY.DESTINATION_UNVERIFIED")


class BoundedStateTest(unittest.TestCase):
    """[C067][C088] control-plane state converges under churn; epochs never reissued."""

    def test_churn_converges(self):
        c, ta, clock, *_ = build()
        epochs = set()
        for i in range(200):
            r = c.create(token(ta), sid="same-sid", tenant="t1", shape=Shape(1, 512), idempotency_key=f"k{i}")
            epochs.add(r["epoch"])
            c.teardown(token(ta), sid="same-sid", epoch=r["epoch"])
            clock.advance(1)
            c.compact(retention_s=0)
        self.assertEqual(len(epochs), 200)          # sid reused, epoch never reused
        self.assertEqual(len(c.sessions), 0)
        self.assertEqual(len(c.leases), 0)
        self.assertLessEqual(len(c.explain.records), c.explain.limit)
        self.assertLessEqual(len(c.egress.decisions), c.egress.decision_limit)

    def test_stale_epoch_after_release_and_reuse(self):
        c, ta, clock, *_ = build()
        r1 = c.create(token(ta), sid="x", tenant="t1", shape=Shape(1, 512), idempotency_key="a")
        c.teardown(token(ta), sid="x", epoch=r1["epoch"])
        c.compact(retention_s=0)
        r2 = c.create(token(ta), sid="x", tenant="t1", shape=Shape(1, 512), idempotency_key="b")
        with self.assertRaises(ControlError):
            c.teardown(token(ta), sid="x", epoch=r1["epoch"])  # old epoch cannot touch the new session
        self.assertTrue(c.teardown(token(ta), sid="x", epoch=r2["epoch"])["verified"])


class ConformanceFixtureTest(unittest.TestCase):
    """[C029][C022][C082] fixture bundle is reproducible and schema-conformant."""

    def test_manifest_digests(self):
        m = json.loads((PKG / "fixtures" / "MANIFEST.json").read_text())
        for rel, d in m["files"].items():
            self.assertEqual(hashlib.sha256((PKG / "fixtures" / rel).read_bytes()).hexdigest(), d, rel)

    def test_regeneration_is_byte_identical(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("mf", PKG / "tools" / "make_fixtures.py")
        mf = importlib.util.module_from_spec(spec); spec.loader.exec_module(mf)
        out = pathlib.Path(tempfile.mkdtemp())
        mf.generate(out)
        self.assertEqual((out / "MANIFEST.json").read_bytes(), (PKG / "fixtures" / "MANIFEST.json").read_bytes())
        shutil.rmtree(out)

    def test_schemas_accept_valid_and_reject_invalid(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("NOT_RUN: jsonschema not installed")
        sch = lambda n: json.loads((PKG / "schemas" / f"PK_HEAVYBOX_{n}.schema.json").read_text())
        fx = lambda p: json.loads((PKG / "fixtures" / p).read_text())
        pairs = {"session_v2": "SESSION_v2", "teardown_v2": "TEARDOWN_v2", "egress_v2_allow": "EGRESS_v2",
                 "status_v1": "STATUS_v1", "config_v1": "CONFIG_v1"}
        for f, s in pairs.items():
            jsonschema.validate(fx(f"valid/{f}.json"), sch(s))
        for rec in fx("valid/errors_v1.json"):
            jsonschema.validate(rec, sch("ERROR_v1"))
        bad = {"session_v2_bad_state": "SESSION_v2", "session_v2_extra_field": "SESSION_v2", "session_v2_bad_sid": "SESSION_v2",
               "teardown_v2_unverified": "TEARDOWN_v2", "teardown_v2_leaked": "TEARDOWN_v2",
               "egress_v2_bad_decision": "EGRESS_v2", "error_v1_bad_code": "ERROR_v1", "status_v1_bad_state": "STATUS_v1"}
        for f, s in bad.items():
            with self.assertRaises(jsonschema.ValidationError, msg=f):
                jsonschema.validate(fx(f"invalid/{f}.json"), sch(s))

    def test_v1_readers_still_accept(self):
        """[C016] v1 egress readers: v2 records reduce to a v1 record without loss of the decision."""
        v2 = json.loads((PKG / "fixtures" / "valid" / "egress_v2_allow.json").read_text())
        v1 = {"sid": v2["sid"], "host": v2["canonical"], "decision": v2["decision"], "reason": v2["reason"]}
        try:
            import jsonschema
        except ImportError:
            self.skipTest("NOT_RUN: jsonschema not installed")
        jsonschema.validate(v1, json.loads((PKG / "schemas" / "PK_HEAVYBOX_EGRESS_v1.schema.json").read_text()))


class FuzzAndLimitsTest(unittest.TestCase):
    """[C085][C028][C050] fuzz regressions and N-1/N/N+1 limit boundaries."""

    def test_zone_id_regression(self):
        for s in ("fe80::1%eth0", "fe80::1%eth0:", "fe80::1%1"):
            with self.assertRaises(ValueError):
                canonicalize_host(s)

    def test_fuzz_smoke_no_findings(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("fz", PKG / "tools" / "fuzz.py")
        fz = importlib.util.module_from_spec(spec); spec.loader.exec_module(fz)
        self.assertEqual(fz.run(1500, 1234)["total_findings"], 0)

    def test_config_field_boundaries(self):
        for k, (typ, lo, hi, _) in cfgmod.FIELDS.items():
            if typ is not int or k in cfgmod.LOCKED:
                continue
            for v, ok in ((lo - 1, False), (lo, True), (hi, True), (hi + 1, False)):
                try:
                    cfgmod.validate_values({k: v}, partial=True)
                    self.assertTrue(ok, (k, v))
                except ControlError:
                    self.assertFalse(ok, (k, v))

    def test_structured_config_fuzz(self):
        rng = random.Random(5)
        for _ in range(3000):
            k = rng.choice(list(cfgmod.FIELDS))
            v = rng.choice([0, -1, 1, 2**63, 1.5, "x", True, None, [], {}, "deny", "allow", float("inf")])
            try:
                eff = cfgmod.merge({"environment": {k: v}})
                for lk, lv in cfgmod.LOCKED.items():
                    self.assertEqual(eff[lk], lv)
            except ControlError:
                pass

    def test_session_id_and_path_limits(self):
        from inv71_heavy_agent_sandbox.sandbox import MAX_PATH_BYTES, MAX_SESSION_ID_BYTES, normalize_path, validate_session_id
        validate_session_id("a" * MAX_SESSION_ID_BYTES)
        with self.assertRaises(ValueError):
            validate_session_id("a" * (MAX_SESSION_ID_BYTES + 1))
        normalize_path("/" + "a" * (MAX_PATH_BYTES - 1))
        with self.assertRaises(ValueError):
            normalize_path("/" + "a" * MAX_PATH_BYTES)


class PkCoreProbeTest(unittest.TestCase):
    """[INV71-X001] absent/unpinned/mismatched pk_core is never a pass."""

    def load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pp", PKG / "tools" / "pk_core_probe.py")
        pp = importlib.util.module_from_spec(spec); spec.loader.exec_module(pp)
        return pp

    def test_absent_is_not_run(self):
        pp = self.load()
        self.assertEqual(pp.probe(search=[tempfile.mkdtemp()])["status"], "NOT_RUN")

    def test_present_but_unpinned_is_not_run(self):
        pp = self.load()
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "pk_core").mkdir()
        (d / "pk_core" / "__init__.py").write_text("")
        self.assertEqual(pp.probe(search=[str(d)])["status"], "NOT_RUN")

    def test_pinned_mismatch_fails_and_match_verifies(self):
        pp = self.load()
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "pk_core").mkdir()
        (d / "pk_core" / "__init__.py").write_text("")
        (d / "pk_core" / "contract.py").write_text("class Contract: pass\nclass Dependency: pass\nclass Slo: pass\n")
        lock = json.loads((PKG / "deps" / "pk_core.lock.json").read_text())
        lock["dependencies"]["pk_core"].update(version_range=">=1,<2", sha256="0" * 64)
        lp = d / "lock.json"; lp.write_text(json.dumps(lock))
        self.assertEqual(pp.probe(lp, search=[str(d)])["status"], "FAILED")
        lock["dependencies"]["pk_core"]["sha256"] = pp.tree_digest(d / "pk_core")
        lp.write_text(json.dumps(lock))
        self.assertEqual(pp.probe(lp, search=[str(d)])["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
