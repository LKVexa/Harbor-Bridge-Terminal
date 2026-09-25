"""Component 55 - dashboards and differentiated alerts (``PK_DYN_DASHBOARD/1``, ``PK_DYN_ALERT/1``).

Definitions live in ``fixtures/dashboards/*.json``.  Invariants checked by
``validate_all``:
  * every panel/alert metric exists in ``metrics.CATALOG`` (histogram series use
    the base name) and every label used is allowed for that metric;
  * every alert has severity ``page|ticket|info``, a runbook link
    ``docs/55_runbooks.md#<anchor>`` whose heading exists, and a route; routes are
    ``UNASSIGNED`` because no on-call rotation/owner exists (sub-part PARTIAL);
  * alert rules are executable in-process (``evaluate_alerts``) against a Registry.
"""
from __future__ import annotations

import json
import operator
import re
from pathlib import Path

from .core import Inv08Error
from .metrics import CATALOG, Registry

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "dashboards"
RUNBOOK = HERE / "docs" / "55_runbooks.md"
DASHBOARD_IDS = ("fleet_overview", "capacity_lease", "security_policy", "provider_degradation")
SEVERITIES = ("page", "ticket", "info")
_OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "==": operator.eq}


def _err(msg: str) -> Inv08Error:
    return Inv08Error("INV08.DASHBOARD.INVALID", msg)


def runbook_anchors(path: Path = RUNBOOK) -> set[str]:
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            slug = re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-")
            out.add(slug)
    return out


def _check_metric(metric: str, labels: dict, where: str) -> None:
    if metric not in CATALOG:
        raise _err(f"{where}: unknown metric {metric}")
    allowed = set(CATALOG[metric][2])
    if not set(labels) <= allowed:
        raise _err(f"{where}: labels {sorted(labels)} not allowed on {metric}")


def load_dashboards(folder: Path = FIXTURES) -> dict[str, dict]:
    out = {}
    for did in DASHBOARD_IDS:
        d = json.loads((folder / f"{did}.json").read_text())
        if d.get("schema") != "PK_DYN_DASHBOARD/1" or d.get("id") != did or not d.get("panels"):
            raise _err(f"dashboard {did} malformed")
        for p in d["panels"]:
            _check_metric(p["metric"], p.get("labels", {}), f"{did}/{p['title']}")
        out[did] = d
    return out


def load_alerts(folder: Path = FIXTURES, runbook: Path = RUNBOOK) -> list[dict]:
    doc = json.loads((folder / "alerts.json").read_text())
    if doc.get("schema") != "PK_DYN_ALERT/1":
        raise _err("alerts schema")
    anchors = runbook_anchors(runbook)
    names = set()
    for a in doc["alerts"]:
        if a["name"] in names:
            raise _err(f"duplicate alert {a['name']}")
        names.add(a["name"])
        if a["severity"] not in SEVERITIES:
            raise _err(f"{a['name']}: bad severity")
        if a["op"] not in _OPS:
            raise _err(f"{a['name']}: bad op")
        _check_metric(a["metric"], a.get("labels", {}), a["name"])
        doc_path, _, anchor = a["runbook"].partition("#")
        if doc_path != "docs/55_runbooks.md" or anchor not in anchors:
            raise _err(f"{a['name']}: runbook section {a['runbook']} missing")
        if not a.get("route"):
            raise _err(f"{a['name']}: no route")
    if {a["severity"] for a in doc["alerts"]} != set(SEVERITIES):
        raise _err("alerts must be differentiated across page/ticket/info")
    return doc["alerts"]


def validate_all() -> dict:
    return {"dashboards": sorted(load_dashboards()), "alerts": [a["name"] for a in load_alerts()]}


def _read(reg: Registry, metric: str, labels: dict, field: str):
    series = reg._v[metric]
    vals = []
    for key, v in series.items():
        if all(dict(key).get(k) == str(val) for k, val in labels.items()):
            vals.append(v)
    if not vals:
        return None
    if CATALOG[metric][0] == "histogram":
        if field == "count":
            return sum(v["count"] for v in vals)
        if field == "mean":
            c = sum(v["count"] for v in vals)
            return sum(v["sum"] for v in vals) / c if c else None
        raise _err(f"field {field} unsupported for histograms")
    return sum(vals)


def evaluate_alerts(reg: Registry, alerts: list[dict] | None = None) -> list[dict]:
    """Return firing alerts. Missing data does not fire (absent-data alerts are explicit rules)."""
    firing = []
    for a in alerts if alerts is not None else load_alerts():
        v = _read(reg, a["metric"], a.get("labels", {}), a.get("field", "value"))
        if a.get("absent"):
            if v is None:
                firing.append({"name": a["name"], "severity": a["severity"], "value": None,
                               "route": a["route"], "runbook": a["runbook"]})
        elif v is not None and _OPS[a["op"]](v, a["threshold"]):
            firing.append({"name": a["name"], "severity": a["severity"], "value": v, "route": a["route"],
                           "runbook": a["runbook"]})
    return firing
