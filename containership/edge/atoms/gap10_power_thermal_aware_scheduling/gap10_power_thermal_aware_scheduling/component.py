"""GAP-10 - Power/thermal-aware scheduling integration with ``pk_core``."""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .model import CRITICAL, RECOVERY_MARGIN, PolicyError, PowerThermalPolicy, ThermalState


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class PowerThermalAwareSchedulingComponent(Component):
    """Master-applied component for GAP-10."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)

        # C033: declarative configuration with secure defaults.
        policy = PowerThermalPolicy()
        cold = ThermalState("n1", policy=policy)
        _verify(cold.ceiling(10)["ceiling"] == 2, "unobserved startup must be constrained")
        _verify(cold.update(temperature=40.0) == "nominal")
        _verify(cold.ceiling(10)["ceiling"] == 10)
        _verify(cold.update(temperature=80.0) == "elevated")
        _verify(cold.ceiling(10)["ceiling"] == 6)
        power = ThermalState("n2", policy=policy)
        _verify(power.update(temperature=40.0, power_draw_watts=190.0, power_budget_watts=200.0) == "critical")
        _verify(power.ceiling(20)["ceiling"] == 5)
        findings[2] = self.satisfied(
            items[2],
            "PowerThermalPolicy is declarative and immutable; its defaults start unobserved nodes constrained and enforce thermal, battery, and power ceilings.",
            *self._evidence("model.py::PowerThermalPolicy"), *self._evidence("model.py::ThermalState"),
        )

        # C034: validate configuration before activation / fail closed.
        try:
            PowerThermalPolicy(elevated_c=90.0, critical_c=80.0)
        except PolicyError:
            pass
        else:
            raise AssertionError("invalid threshold ordering was accepted")
        findings[3] = self.satisfied(
            items[3],
            "Policy construction rejects inconsistent thresholds, hysteresis, freshness limits, and non-zero emergency ceilings before activation.",
            *self._evidence("model.py::PowerThermalPolicy.__post_init__"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)

        # C048: safe behavior when trust/time inputs are unavailable.
        blind = ThermalState("n1")
        _verify(blind.update(temperature=None) == "critical")
        _verify(blind.ceiling(10)["ceiling"] == 2)
        stale = ThermalState("n2")
        _verify(stale.update(temperature=30.0, observed_at=0.0, now=31.0) == "critical")
        findings[7] = self.satisfied(
            items[7],
            "Missing, stale, future-dated, NaN, or infinite thermal evidence cannot be interpreted as cool; unusable evidence fails closed to a constrained band.",
            *self._evidence("model.py::ThermalState.update"),
        )

        # C044: authenticate nodes/peers before trust. GAP-10 delegates reporter
        # authentication to GAP-09 and must be honest when that sibling is absent.
        gap09 = sibling("GAP-09")
        if gap09 is None:
            findings[3] = self.partial(
                items[3],
                "Reporter authentication is delegated to GAP-09 and cannot be proven by this isolated package.",
                note="GAP-09 Unified observability is not installed here",
            )
        else:
            store = gap09.SignalStore()
            cool = gap09.Sample("temperature", 30.0, "t1", "dub", "n1", at=0)
            try:
                store.submit("rogue", [cool], attested_level="untrusted", signed=True, now=0)
            except gap09.ReporterUntrusted:
                pass
            else:
                raise AssertionError("an unattested reporter injected a cool reading")
            store.submit(
                "n1",
                [gap09.Sample("temperature", 96.0, "t1", "dub", "n1", at=0)],
                attested_level="hardware",
                signed=True,
                now=0,
            )
            reading = store.read(
                caller_tenant="t1", tenant="t1", site="dub", workload="n1", signal="temperature", now=1
            )
            state = ThermalState("n1")
            state.update(temperature=reading["value"], observed_at=0, now=1)
            _verify(state.ceiling(10)["excluded"])
            findings[3] = self.satisfied(
                items[3],
                "GAP-09 rejects an unattested reporter before GAP-10 trusts its thermal reading; an authenticated emergency reading then produces exclusion.",
                *self._evidence("model.py::ThermalState.update"),
                "GAP-09/SignalStore",
            )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)

        # Exercise hysteresis even though it is an implementation invariant rather
        # than a direct substitute for one of the resilience checklist requirements.
        t = ThermalState("n1")
        t.update(temperature=86.0)
        _verify(t.band == "critical")
        _verify(t.update(temperature=84.0) == "critical", "recovered before the hysteresis margin")
        _verify(t.update(temperature=CRITICAL - RECOVERY_MARGIN - 0.1) == "elevated")

        # C052: explicit sensor-stall/freshness threshold.
        stale = ThermalState("n2")
        _verify(stale.update(temperature=30.0, observed_at=0.0, now=31.0) == "critical")
        findings[1] = self.satisfied(
            items[1],
            "Telemetry age is bounded by policy; samples older than the health threshold or excessively future-dated are detected and fail closed.",
            *self._evidence("model.py::PowerThermalPolicy.max_sensor_age_seconds"), *self._evidence("model.py::ThermalState.update"),
        )

        # C054: local load shedding/admission ceiling.
        battery = ThermalState("n3")
        _verify(battery.update(temperature=30.0, battery=0.10) == "critical")
        _verify(battery.ceiling(20)["ceiling"] == 5)
        findings[3] = self.satisfied(
            items[3],
            "Low battery, high temperature, or high power pressure reduces the node's admission ceiling before downstream scheduling.",
            *self._evidence("model.py::ThermalState.ceiling"),
        )

        # C056: degraded operation on noncritical telemetry failure.
        degraded = ThermalState("n4")
        _verify(degraded.update(temperature=None) == "critical")
        _verify(not degraded.ceiling(20)["excluded"] and degraded.ceiling(20)["ceiling"] == 5)
        findings[5] = self.satisfied(
            items[5],
            "Loss of usable temperature evidence enters constrained degraded operation instead of crashing or assuming full capacity; emergency exclusion remains reserved for observed emergency conditions.",
            *self._evidence("model.py::ThermalState.update"), *self._evidence("model.py::ThermalState.ceiling"),
        )
        return findings


COMPONENT = PowerThermalAwareSchedulingComponent
