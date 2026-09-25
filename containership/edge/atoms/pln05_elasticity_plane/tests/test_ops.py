"""MC-27 alert rules exercised against synthetic scenarios on a real plane."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import World  # noqa: E402

from pln05_elasticity_plane.errors import PlaneError  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("alerts", ROOT / "tools" / "alerts.py")
alerts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alerts)


def attempt(fn):
    try:
        fn()
    except PlaneError:
        pass


class AlertScenarios(unittest.TestCase):
    def run_windows(self, w, step, windows=4):
        snaps = [alerts.snapshot(w.plane)]
        for i in range(windows):
            step(i)
            snaps.append(alerts.snapshot(w.plane))
        return alerts.evaluate(snaps)

    def test_quiet_system_fires_nothing(self):
        w = World()
        w.declare()
        self.assertEqual(self.run_windows(w, lambda i: w.observe(0.5)), set())

    def test_not_ready_pages(self):
        w = World()
        w.declare()
        w.plane.drain()
        self.assertIn("PLN05NotReady", self.run_windows(w, lambda i: None))

    def test_attack_pattern(self):
        w = World()
        w.declare()
        bad = w.token(source="r9")
        fired = self.run_windows(w, lambda i: [attempt(lambda: w.observe(0.9, token=bad)) for _ in range(20)], 2)
        self.assertIn("PLN05AuthAttack", fired)
        self.assertNotIn("PLN05DecisionFailures", fired)  # attack is distinguished from defect

    def test_stale_demand(self):
        w = World()
        w.declare()
        w.observe(0.5)

        def step(i):
            w.clock.advance(40)
            w.plane.tick()
        self.assertIn("PLN05StaleDemand", self.run_windows(w, step))

    def test_lease_loss_and_audit_pressure(self):
        w = World()
        w.declare()
        w.observe(0.5)
        w.leases.available = False
        w.clock.advance(20)
        fired = self.run_windows(w, lambda i: [attempt(lambda: w.observe(0.5)) for _ in range(10)], 3)
        self.assertIn("PLN05LeaseLoss", fired)
        w2 = World()
        w2.declare()
        w2.plane.audit.set_sink(False)
        self.assertIn("PLN05AuditPressure", self.run_windows(w2, lambda i: None, 1))

    def test_persistent_ceiling(self):
        w = World()
        w.declare(ceiling=1)
        fired = self.run_windows(w, lambda i: [w.observe(0.99) for _ in range(120)], 6)
        self.assertIn("PLN05PersistentCeiling", fired)

    def test_rules_have_route_severity_runbook(self):
        for r in alerts.RULES:
            self.assertTrue(r["route"] and r["severity"] in ("page", "ticket"))
            anchor_file = r["runbook"].split("#")[0]
            self.assertTrue((ROOT / anchor_file).exists(), r["runbook"])
        self.assertIn("PLN05SLOBurn", alerts.prometheus())

    def test_dashboards_cover_required_views(self):
        d = json.loads((ROOT / "observability" / "dashboards.json").read_text())
        titles = " ".join(x["title"] for x in d["dashboards"]).lower()
        for need in ("decisions", "latency", "input quality", "constraints", "overload", "ownership", "controls", "security"):
            self.assertIn(need, titles)


if __name__ == "__main__":
    unittest.main()
