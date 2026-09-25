"""M22: alert rules and dashboards reference metrics the runtime really emits,
and each alert has an on-call doc entry."""
import json, pathlib, re, unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.errors.mapping import ProviderFault

PKG = pathlib.Path(__file__).resolve().parents[2]


def emitted():
    w = World(); w.svc.start(); w.link(); w.call()
    try:
        w.call(tenant="globex")
    except ProviderFault:
        pass
    w.svc.metrics.inc("pk_isolation_violation", {"contract": "c"})
    return {m.split("{")[0].split(" ")[0] for m in w.svc.metrics.exposition().splitlines()}


class AlertRules(unittest.TestCase):
    def test_every_alert_references_emitted_metric(self):
        names = emitted()
        rules = json.loads((PKG / "alerts/provider-rules.json").read_text())["groups"][0]["rules"]
        doc = (PKG / "docs/oncall/provider-alerts.md").read_text()
        for r in rules:
            for m in r["metrics"]:
                self.assertIn(m, names, f"{r['alert']} uses {m}")
            for m in re.findall(r"\b(pk_[a-z_]+)", r["expr"]):
                self.assertIn(m, names, f"{r['alert']} expr uses {m}")
            self.assertIn(r["alert"], doc)

    def test_dashboard_queries_use_emitted_metrics(self):
        names = emitted()
        d = json.loads((PKG / "dashboards/provider-overview.json").read_text())
        for p in d["panels"]:
            for m in re.findall(r"\b(pk_[a-z_]+)", p["query"]):
                self.assertIn(m, names, p["title"])
