"""P1 core operational tests: components 09-18."""
import unittest

from harness import SCOPE, Stack
from gap10_power_thermal_aware_scheduling.model import PolicyError, PowerThermalPolicy
from gap10_power_thermal_aware_scheduling.production.calibration import (
    UNKNOWN_PROFILE, CalibrationInventory, HardwareProfile)
from gap10_power_thermal_aware_scheduling.production.errors import ErrorCode, Gap10Error
from gap10_power_thermal_aware_scheduling.production.predictive import (
    AcceleratorReport, BatteryModel, CoolingDomainModel, RateOfRisePredictor, accelerator_band)
from gap10_power_thermal_aware_scheduling.production.shedding import Constraint, SheddingPolicy, resolve
from gap10_power_thermal_aware_scheduling.production.telemetry import AggregationPolicy, SensorReading, aggregate
from gap10_power_thermal_aware_scheduling.production.schema_validate import load_schemas, validate
from harness import PKG_DIR


class C09Calibration(unittest.TestCase):
    def test_c09_policy_derived_below_vendor_throttle(self):
        hp = HardwareProfile("pi5", 80.0, 90.0, 12.0, 15.0, "none", 0, "passive", 60.0, ("cpu",), "r1", "lab")
        p = hp.derive_policy()
        self.assertLessEqual(p.emergency_c, 75.0)
        self.assertLess(p.critical_c, p.emergency_c)

    def test_c09_uncalibrated_node_gets_conservative_profile(self):
        inv = CalibrationInventory()
        prof, calibrated = inv.profile_for("mystery")
        self.assertFalse(calibrated)
        self.assertIs(prof, UNKNOWN_PROFILE)
        self.assertLess(prof.derive_policy().emergency_c, PowerThermalPolicy().emergency_c)

    def test_c09_invalid_or_unvalidated_calibration_rejected(self):
        with self.assertRaises(PolicyError):
            HardwareProfile("bad", 90.0, 80.0, 10, 20)
        inv = CalibrationInventory()
        with self.assertRaises(PolicyError):
            inv.register(HardwareProfile("x", 80.0, 90.0, 10, 20))  # no validator
        with self.assertRaises(PolicyError):
            inv.assign("n", "nope")

    def test_c09_battery_chemistry_raises_reserve(self):
        hp = HardwareProfile("ups", 90.0, 100.0, 10, 20, "lead-acid", 100, validated_by="lab")
        self.assertGreaterEqual(hp.derive_policy().battery_reserve, 0.5)


class C10Aggregation(unittest.TestCase):
    def test_c10_worst_case_with_offsets(self):
        s = [SensorReading("cpu0", "cpu", 70.0, True), SensorReading("hs", "accelerator", 90.0, True)]
        r = aggregate(s, AggregationPolicy(offsets={"accelerator": 10.0}))
        self.assertEqual(r.temperature_c, 80.0)
        self.assertEqual(r.limiting_sensor, "hs")

    def test_c10_weighted_cannot_hide_hotspot(self):
        s = [SensorReading("a", "cpu", 40.0, True), SensorReading("b", "cpu", 40.0, True), SensorReading("c", "vrm", 96.0, True)]
        r = aggregate(s, AggregationPolicy(mode="weighted-with-floor", weights={"cpu": 10.0}))
        self.assertEqual(r.temperature_c, 96.0)

    def test_c10_missing_required_marks_incomplete(self):
        r = aggregate([SensorReading("g", "gpu", 50.0, True)], AggregationPolicy(required_kinds=("cpu", "gpu")))
        self.assertFalse(r.complete)
        self.assertEqual(r.missing_required, ("cpu",))
        self.assertIsNone(aggregate([]).temperature_c)


class C11Predictor(unittest.TestCase):
    def test_c11_derates_before_threshold(self):
        p = RateOfRisePredictor(horizon_s=60)
        for i, t in enumerate((60, 63, 66, 69)):
            p.observe("n", i * 10.0, float(t))
        band, why = p.band("n", PowerThermalPolicy())
        self.assertEqual(band, "elevated")  # 69 + 0.3*60 = 87 >= critical 85
        self.assertIn("predicted", why)

    def test_c11_predictor_never_excludes_and_ignores_noise(self):
        p = RateOfRisePredictor(horizon_s=60)
        for i, t in enumerate((70, 80, 90)):
            p.observe("n", i * 10.0, float(t))
        self.assertEqual(p.band("n", PowerThermalPolicy())[0], "critical")
        q = RateOfRisePredictor()
        for i, t in enumerate((20, 30, 200)):
            q.observe("m", float(i), float(t))
        self.assertIsNone(q.slope("m"))

    def test_c11_integrated_in_controller(self):
        s = Stack()
        for t in (60, 64, 68, 72):
            s.send(temp=float(t))
            s.mc.advance(5)
        d = s.ctl.decide("edge-001")
        self.assertIn(d["band"], ("elevated", "critical"))


class C12Battery(unittest.TestCase):
    def test_c12_runtime_based_bands(self):
        m = BatteryModel(capacity_wh=100, required_runtime_s=3600)
        self.assertEqual(m.band(0.9, 50.0, on_mains=False)[0], "nominal")
        self.assertEqual(m.band(0.3, 50.0, on_mains=False)[0], "critical")
        self.assertEqual(m.band(0.9, 50.0, on_mains=True)[0], "nominal")
        self.assertEqual(m.band(0.9, None, on_mains=False)[0], "critical")

    def test_c12_health_degrades_runtime(self):
        good, worn = BatteryModel(100, 1.0), BatteryModel(100, 0.5)
        self.assertLess(worn.runtime_s(0.8, 50), good.runtime_s(0.8, 50))


class C13Cooling(unittest.TestCase):
    def test_c13_cool_node_in_failing_domain_is_raised(self):
        m = CoolingDomainModel(membership={"a": "rack1", "b": "rack1", "c": "rack1"}, parent={"rack1": "room1"},
                               inlet_limits_c={"room1": 35.0})
        for n, b in (("a", "critical"), ("b", "critical"), ("c", "nominal")):
            m.report(n, b)
        self.assertEqual(m.band_for("c")[0], "elevated")
        m.report_inlet("room1", 38.0)
        self.assertEqual(m.band_for("c")[0], "critical")


class C14Accelerators(unittest.TestCase):
    def test_c14_hotspot_and_missing_telemetry(self):
        p = PowerThermalPolicy()
        ok = AcceleratorReport("gpu0", "gpu", 60.0, 90.0, 200.0)
        hot = AcceleratorReport("gpu1", "gpu", 91.0, 90.0, 300.0)
        blind = AcceleratorReport("npu0", "npu", None, 90.0, None)
        self.assertEqual(accelerator_band([ok], p)[0], "nominal")
        self.assertEqual(accelerator_band([ok, hot], p)[:2], ("emergency", 500.0))
        self.assertEqual(accelerator_band([blind], p)[0], "critical")

    def test_c14_controller_integrates_accelerator_band(self):
        s = Stack()
        s.ctl.nodes["edge-001"].accelerators = (AcceleratorReport("gpu0", "gpu", 85.0, 90.0, 250.0),)
        d = s.send(temp=40.0)
        self.assertEqual(d["band"], "critical")


class C15Shedding(unittest.TestCase):
    def test_c15_lowest_class_shed_first_and_no_bypass(self):
        sp = SheddingPolicy()
        a = sp.allocate(10, {"best-effort": 5, "batch": 5, "latency-critical": 5, "system": 2}, excluded=False)
        self.assertEqual(sum(a.values()), 10)
        self.assertEqual(a["system"], 2)
        self.assertEqual(a["latency-critical"], 5)
        self.assertEqual(a["best-effort"], 0)
        z = sp.allocate(10, {"system": 5}, excluded=True)
        self.assertEqual(z, {"system": 0})
        with self.assertRaises(ValueError):
            sp.allocate(10, {"vip": 1}, excluded=False)


class C16Precedence(unittest.TestCase):
    def test_c16_min_of_bounds_and_increase_ignored(self):
        eff, trail = resolve([Constraint("cost", 1.0, "cost wants more", wants_increase=True),
                              Constraint("thermal-safety", 0.25, "critical"),
                              Constraint("slo", 1.0, "slo pressure", wants_increase=True)])
        self.assertEqual(eff, 0.25)
        self.assertEqual(trail[0]["source"], "thermal-safety")
        self.assertTrue(any(t["ignored_increase"] for t in trail))
        with self.assertRaises(ValueError):
            resolve([Constraint("whatever", 1.0, "x")])


class C17Health(unittest.TestCase):
    def test_c17_health_reports_and_schema_valid(self):
        s = Stack()
        s.send(temp=40.0)
        h = s.ctl.health()
        self.assertTrue(h["safe_to_enforce"])
        self.assertIn(SCOPE, h["active_policy_revisions"])
        schema = load_schemas(PKG_DIR / "schemas")["PK_GAP10_HEALTH/1"]
        self.assertEqual(validate(h, schema), [])
        s.mc.advance(40)
        self.assertFalse(s.ctl.health()["checks"]["telemetry_fresh"])
        self.assertFalse(s.ctl.health()["safe_to_enforce"])


class C18Controls(unittest.TestCase):
    def sig(self, s, payload, cap="control.operate", target="edge-001"):
        return s.kr.sign("ops-k1", cap, target, payload)

    def test_c18_quarantine_freeze_disable(self):
        s = Stack()
        s.send(temp=40.0)
        now = s.clock.now()
        p = {"kind": "quarantine", "target": "edge-001", "reason": "fan failure", "control_id": "q1", "ticket": "INC-1"}
        s.ctl.controls.apply(key_id="ops-k1", signature=self.sig(s, p), kind="quarantine", target="edge-001",
                             reason="fan failure", control_id="q1", now=now, ticket="INC-1")
        s.mc.advance(1)
        self.assertEqual(s.send(temp=40.0)["ceiling"], 0)
        s.ctl.controls.release(key_id="ops-k1", signature=self.sig(s, {"release": "q1"}, "control.release"),
                               control_id="q1", now=s.clock.now())
        s.mc.advance(1)
        self.assertEqual(s.send(temp=40.0)["ceiling"], 100)
        p = {"kind": "emergency-disable", "target": "*", "reason": "bad release", "control_id": "d1", "ticket": "INC-2"}
        s.ctl.controls.apply(key_id="ops-k1", signature=s.kr.sign("ops-k1", "control.operate", "*", p),
                             kind="emergency-disable", target="*", reason="bad release", control_id="d1", now=s.clock.now(), ticket="INC-2")
        s.mc.advance(1)
        d = s.send(temp=40.0)
        self.assertTrue(d["automation_disabled"])
        self.assertLessEqual(d["ceiling_fraction"], 0.25)
        types = [e["type"] for e in s.audit.entries]
        self.assertIn("control.applied", types)
        self.assertIn("control.released", types)

    def test_c18_unauthorized_control_rejected_and_audited(self):
        s = Stack()
        with self.assertRaises(Gap10Error) as cm:
            s.ctl.controls.apply(key_id="gap09-k1", signature="0" * 64, kind="quarantine", target="edge-001",
                                 reason="x", control_id="q", now=s.clock.now())
        self.assertEqual(cm.exception.code, ErrorCode.CONTROL_UNAUTHORIZED)
        self.assertIn("control.rejected", [e["type"] for e in s.audit.entries])

    def test_c18_freeze_caps_at_current(self):
        s = Stack()
        s.send(temp=80.0)
        p = {"kind": "freeze", "target": "edge-001", "reason": "investigate", "control_id": "f1", "ticket": "INC-3"}
        s.ctl.controls.apply(key_id="ops-k1", signature=self.sig(s, p), kind="freeze", target="edge-001",
                             reason="investigate", control_id="f1", now=s.clock.now(), ticket="INC-3", current_fraction=0.6)
        for _ in range(3):
            s.mc.advance(1)
            d = s.send(temp=30.0)
        self.assertLessEqual(d["ceiling_fraction"], 0.6)


class GoldenVectors(unittest.TestCase):
    """Golden vectors for the models (fixtures/golden_vectors.json); regenerate with tests/gen_golden.py."""

    @classmethod
    def setUpClass(cls):
        import json
        import gen_golden
        cls.golden = json.loads((PKG_DIR / "fixtures" / "golden_vectors.json").read_text())
        cls.now = gen_golden.compute()

    def _cmp(self, key):
        import json
        self.assertEqual(json.loads(json.dumps(self.now[key])), self.golden[key])

    def test_c09_golden_calibration(self):
        self._cmp("calibration")

    def test_c10_golden_aggregation(self):
        self._cmp("aggregation")

    def test_c11_golden_predictor_and_threshold_boundaries(self):
        self._cmp("predictor")
        self._cmp("kernel")  # exact-threshold and hysteresis-margin boundaries

    def test_c12_golden_battery(self):
        self._cmp("battery")

    def test_c13_golden_cooling(self):
        self._cmp("cooling")


class C18ControlSemantics(unittest.TestCase):
    def test_c18_ticket_required_and_idempotent_redelivery(self):
        s = Stack()
        p = {"kind": "quarantine", "target": "edge-001", "reason": "r", "control_id": "q9", "ticket": ""}
        with self.assertRaises(Gap10Error):
            s.ctl.controls.apply(key_id="ops-k1", signature=s.kr.sign("ops-k1", "control.operate", "edge-001", p),
                                 kind="quarantine", target="edge-001", reason="r", control_id="q9", now=1.0, ticket="")
        p["ticket"] = "INC-9"
        sig = s.kr.sign("ops-k1", "control.operate", "edge-001", p)
        a = s.ctl.controls.apply(key_id="ops-k1", signature=sig, kind="quarantine", target="edge-001", reason="r",
                                 control_id="q9", now=1.0, ticket="INC-9")
        b = s.ctl.controls.apply(key_id="ops-k1", signature=sig, kind="quarantine", target="edge-001", reason="r",
                                 control_id="q9", now=2.0, ticket="INC-9")
        self.assertIs(a, b)
        self.assertEqual(sum(1 for e in s.audit.entries if e["type"] == "control.applied"), 1)


class C05Shadow(unittest.TestCase):
    def test_c05_shadow_evaluation_does_not_apply(self):
        from gap10_power_thermal_aware_scheduling.production.policy_service import policy_to_dict, sign_bundle
        s = Stack()
        s.send(temp=72.0)
        rev = s.policies.submit(sign_bundle(s.kr, SCOPE, dict(policy_to_dict(PowerThermalPolicy()), elevated_c=70.0),
                                            s.policies.active[SCOPE], "author-k1"), now=1)
        before = dict(s.ctl.nodes["edge-001"].last_decision)
        sh = s.ctl.shadow("edge-001", rev.revision_id)
        self.assertEqual((sh["live_band"], sh["candidate_band"], sh["applied"]), ("nominal", "elevated", False))
        self.assertEqual(s.ctl.nodes["edge-001"].last_decision, before)
        self.assertNotEqual(s.policies.active[SCOPE], rev.revision_id)


if __name__ == "__main__":
    unittest.main()
