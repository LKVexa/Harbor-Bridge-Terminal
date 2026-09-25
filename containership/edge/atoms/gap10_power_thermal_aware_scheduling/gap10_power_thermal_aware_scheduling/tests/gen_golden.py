"""Regenerate golden vectors (review diffs before committing): python gen_golden.py"""
import json
from harness import PKG_DIR
from gap10_power_thermal_aware_scheduling.model import PowerThermalPolicy, ThermalState
from gap10_power_thermal_aware_scheduling.production.calibration import HardwareProfile, UNKNOWN_PROFILE
from gap10_power_thermal_aware_scheduling.production.predictive import BatteryModel, CoolingDomainModel, RateOfRisePredictor
from gap10_power_thermal_aware_scheduling.production.telemetry import AggregationPolicy, SensorReading, aggregate


def compute():
    g = {"kernel": [], "calibration": [], "aggregation": [], "predictor": [], "battery": [], "cooling": []}
    for seq in ([40, 74.99, 75, 84.99, 85, 94.99, 95], [96, 91, 90, 89.9, 80, 79.9, 70], [None, 40], [float("nan"), 40, 1000]):
        st, out = ThermalState("g"), []
        for t in seq:
            out.append(st.update(temperature=t))
        g["kernel"].append({"temps": [None if (t is None or t != t) else t for t in seq], "nan": seq[0] != seq[0] if seq[0] is not None else False, "bands": out})
    for prof in (UNKNOWN_PROFILE, HardwareProfile("edge", 105, 115, 200, 250, "li-ion", 500, validated_by="lab"),
                 HardwareProfile("pi", 80, 90, 12, 15, "none", validated_by="lab")):
        p = prof.derive_policy()
        g["calibration"].append({"class": prof.hardware_class, "elevated": p.elevated_c, "critical": p.critical_c,
                                 "emergency": p.emergency_c, "reserve": p.battery_reserve})
    for sensors, pol in (([("cpu", 70), ("accelerator", 90)], {"offsets": {"accelerator": 10}}), ([("gpu", 50)], {"required_kinds": ["cpu"]})):
        r = aggregate([SensorReading(k + "0", k, float(t), True) for k, t in sensors],
                      AggregationPolicy(offsets=pol.get("offsets", {}), required_kinds=tuple(pol.get("required_kinds", ["cpu"]))))
        g["aggregation"].append({"sensors": sensors, "policy": pol, "temp": r.temperature_c, "complete": r.complete})
    for pts in ([60, 63, 66, 69], [70, 70, 70], [80, 78, 76]):
        pr = RateOfRisePredictor()
        for i, t in enumerate(pts):
            pr.observe("n", i * 10.0, float(t))
        g["predictor"].append({"points": pts, "predicted": pr.predict("n"), "band": pr.band("n", PowerThermalPolicy())[0]})
    for soc, load in ((0.9, 50.0), (0.3, 50.0), (0.2, 10.0)):
        m = BatteryModel(100, 1.0, required_runtime_s=3600)
        g["battery"].append({"soc": soc, "load": load, "runtime": m.runtime_s(soc, load), "band": m.band(soc, load, False)[0]})
    m = CoolingDomainModel(membership={"a": "r", "b": "r", "c": "r"})
    for bands in (("nominal", "nominal", "nominal"), ("critical", "critical", "nominal")):
        for n, b in zip("abc", bands):
            m.report(n, b)
        g["cooling"].append({"bands": bands, "c_band": m.band_for("c")[0]})
    return g


if __name__ == "__main__":
    (PKG_DIR / "fixtures" / "golden_vectors.json").write_text(json.dumps(compute(), indent=2))
