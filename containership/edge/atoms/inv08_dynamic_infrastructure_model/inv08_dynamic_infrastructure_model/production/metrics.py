"""Component 51 - metrics exporter (Prometheus text exposition format 0.0.4).

Contract ``PK_DYN_METRICS/1``:
  * names match ``inv08_[a-z0-9_]+`` and end in a unit suffix (``_seconds``,
    ``_nodes``, ``_units``, ``_hours``, ``_bytes``, ``_timestamp_seconds``) or
    ``_total`` for counters, or ``_info``; names/units in ``CATALOG`` are stable:
    renaming = major version;
  * every metric declares an allow-list of label names and a per-metric series cap;
    unknown labels raise, series beyond the cap are dropped and counted in
    ``inv08_exporter_cardinality_rejections_total``;
  * ``Registry.scrape()`` never raises: failures are counted and a minimal
    self-health exposition is returned.
``wsgi_app`` is an in-process WSGI endpoint (no socket is bound in this overlay).
"""
from __future__ import annotations

import math
import re
from typing import Callable, Iterable

from .core import Inv08Error

SCHEMA = "PK_DYN_METRICS/1"
_NAME_RE = re.compile(r"^inv08_[a-z0-9_]+$")
_LABEL_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
UNIT_SUFFIXES = ("_seconds", "_nodes", "_units", "_hours", "_bytes", "_total", "_info", "_ratio", "_series")
LATENCY_BUCKETS = (0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 1.0)
LEASE_AGE_BUCKETS = (60, 300, 900, 1800, 3600, 7200, 14400, 43200, 86400)

# name: (type, help, labels, max_series, buckets)
CATALOG: dict[str, tuple] = {
    "inv08_pool_nodes": ("gauge", "Current leased nodes in the pool", (), 1, None),
    "inv08_pool_target_nodes": ("gauge", "Target node count chosen by the last decision", (), 1, None),
    "inv08_pool_demand_units": ("gauge", "Demand input of the last decision", (), 1, None),
    "inv08_pool_nodes_added_total": ("counter", "Nodes added by decisions", (), 1, None),
    "inv08_pool_nodes_reclaimed_total": ("counter", "Nodes reclaimed by decisions", (), 1, None),
    "inv08_pool_leases_renewed_total": ("counter", "Busy-node lease renewals", (), 1, None),
    "inv08_pool_node_hours_total": ("counter", "Accounted node hours", (), 1, None),
    "inv08_decision_latency_seconds": ("histogram", "Pool.tick wall latency", (), 1, LATENCY_BUCKETS),
    "inv08_lease_age_seconds": ("histogram", "Age of leases at reclaim", (), 1, LEASE_AGE_BUCKETS),
    "inv08_tick_errors_total": ("counter", "Rejected/failed decisions", ("reason",), 20, None),
    "inv08_policy_rejections_total": ("counter", "Security/policy rejections", ("check",), 30, None),
    "inv08_attestation_results_total": ("counter", "Attestation verdicts", ("action",), 4, None),
    "inv08_provider_errors_total": ("counter", "Provider errors", ("provider", "retryable"), 40, None),
    "inv08_provider_request_latency_seconds": ("histogram", "Provider call latency", ("provider",), 20, LATENCY_BUCKETS),
    "inv08_reconcile_drift_nodes": ("gauge", "Nodes differing between desired and observed", (), 1, None),
    "inv08_exporter_scrapes_total": ("counter", "Scrapes served", (), 1, None),
    "inv08_exporter_scrape_errors_total": ("counter", "Scrapes that failed to render", (), 1, None),
    "inv08_exporter_last_scrape_timestamp_seconds": ("gauge", "Clock value at last scrape", (), 1, None),
    "inv08_exporter_series": ("gauge", "Series currently held", (), 1, None),
    "inv08_exporter_cardinality_rejections_total": ("counter", "Series dropped by cardinality cap", ("metric",), 64, None),
}


def validate_catalog(catalog: dict = CATALOG) -> None:
    for name, (typ, _h, labels, cap, buckets) in catalog.items():
        if not _NAME_RE.match(name) or not name.endswith(UNIT_SUFFIXES):
            raise Inv08Error("INV08.METRICS.BAD_NAME", f"{name}: bad name/unit suffix")
        if typ == "counter" and not name.endswith("_total"):
            raise Inv08Error("INV08.METRICS.BAD_NAME", f"{name}: counters end in _total")
        if typ == "histogram" and (not buckets or list(buckets) != sorted(set(buckets))):
            raise Inv08Error("INV08.METRICS.BAD_BUCKETS", name)
        if any(not _LABEL_RE.match(l) or l == "le" for l in labels) or cap < 1:
            raise Inv08Error("INV08.METRICS.BAD_LABELS", name)


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _fmt(v: float) -> str:
    if v == math.inf:
        return "+Inf"
    return repr(float(v)) if not float(v).is_integer() else str(int(v)) if abs(v) < 1e15 else repr(float(v))


def _lbl(pairs: Iterable[tuple[str, str]]) -> str:
    p = list(pairs)
    return "{" + ",".join(f'{k}="{_esc(str(v))}"' for k, v in p) + "}" if p else ""


class Registry:
    def __init__(self, clock: Callable[[], float], catalog: dict = CATALOG) -> None:
        validate_catalog(catalog)
        self.catalog, self.clock = catalog, clock
        self._v: dict[str, dict[tuple, object]] = {n: {} for n in catalog}
        self.fail_next_render = False  # fault-injection hook for tests

    def _key(self, name: str, labels: dict) -> tuple | None:
        if name not in self.catalog:
            raise Inv08Error("INV08.METRICS.UNKNOWN_METRIC", name)
        allowed = self.catalog[name][2]
        if set(labels) != set(allowed):
            raise Inv08Error("INV08.METRICS.BAD_LABELS", f"{name} expects labels {allowed}")
        key = tuple((l, str(labels[l])[:128]) for l in allowed)
        series = self._v[name]
        if key not in series and len(series) >= self.catalog[name][3]:
            if name != "inv08_exporter_cardinality_rejections_total":
                self.inc("inv08_exporter_cardinality_rejections_total", metric=name)
            return None
        return key

    def inc(self, name: str, amount: float = 1.0, **labels) -> None:
        if self.catalog.get(name, ("",))[0] != "counter" or amount < 0 or not math.isfinite(amount):
            raise Inv08Error("INV08.METRICS.BAD_UPDATE", f"inc on {name} by {amount}")
        k = self._key(name, labels)
        if k is not None:
            self._v[name][k] = self._v[name].get(k, 0.0) + amount

    def set(self, name: str, value: float, **labels) -> None:
        if self.catalog.get(name, ("",))[0] != "gauge" or not math.isfinite(value):
            raise Inv08Error("INV08.METRICS.BAD_UPDATE", f"set on {name}")
        k = self._key(name, labels)
        if k is not None:
            self._v[name][k] = float(value)

    def observe(self, name: str, value: float, **labels) -> None:
        spec = self.catalog.get(name)
        if not spec or spec[0] != "histogram" or not math.isfinite(value):
            raise Inv08Error("INV08.METRICS.BAD_UPDATE", f"observe on {name}")
        k = self._key(name, labels)
        if k is None:
            return
        h = self._v[name].setdefault(k, {"b": [0] * len(spec[4]), "sum": 0.0, "count": 0})
        for i, ub in enumerate(spec[4]):
            if value <= ub:
                h["b"][i] += 1
        h["sum"] += value
        h["count"] += 1

    def value(self, name: str, **labels):
        return self._v[name].get(tuple((l, str(labels[l])) for l in self.catalog[name][2]))

    def series_count(self) -> int:
        return sum(len(s) for s in self._v.values())

    def render(self) -> str:
        if self.fail_next_render:
            self.fail_next_render = False
            raise RuntimeError("injected render failure")
        out = []
        for name in sorted(self.catalog):
            typ, hlp, _l, _c, buckets = self.catalog[name]
            out.append(f"# HELP {name} {hlp}")
            out.append(f"# TYPE {name} {typ}")
            for key in sorted(self._v[name]):
                val = self._v[name][key]
                if typ == "histogram":
                    for ub, c in zip(buckets, val["b"]):
                        out.append(f"{name}_bucket{_lbl(list(key) + [('le', _fmt(ub))])} {c}")
                    out.append(f"{name}_bucket{_lbl(list(key) + [('le', '+Inf')])} {val['count']}")
                    out.append(f"{name}_sum{_lbl(key)} {_fmt(val['sum'])}")
                    out.append(f"{name}_count{_lbl(key)} {val['count']}")
                else:
                    out.append(f"{name}{_lbl(key)} {_fmt(val)}")
        return "\n".join(out) + "\n"

    def scrape(self) -> str:
        self.inc("inv08_exporter_scrapes_total")
        self.set("inv08_exporter_last_scrape_timestamp_seconds", self.clock())
        self.set("inv08_exporter_series", self.series_count())
        try:
            return self.render()
        except Exception:
            self.inc("inv08_exporter_scrape_errors_total")
            e = self._v["inv08_exporter_scrape_errors_total"][()]
            return ("# TYPE inv08_exporter_scrape_errors_total counter\n"
                    f"inv08_exporter_scrape_errors_total {_fmt(e)}\n")


def wsgi_app(registry: Registry):
    def app(environ, start_response):
        if environ.get("PATH_INFO") != "/metrics" or environ.get("REQUEST_METHOD", "GET") != "GET":
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"not found\n"]
        body = registry.scrape().encode()
        start_response("200 OK", [("Content-Type", "text/plain; version=0.0.4; charset=utf-8")])
        return [body]
    return app


class InstrumentedPool:
    """Wraps ``model.Pool`` so every tick updates metrics.  Lease age is measured
    from the first tick a node was seen to the tick it was reclaimed; ``now`` is
    interpreted in hours (the model's node-hour accounting unit)."""

    def __init__(self, pool, registry: Registry, timer: Callable[[], float]) -> None:
        self.pool, self.reg, self.timer = pool, registry, timer
        self._born: dict[str, float] = {}
        self._nh = float(pool.node_hours)

    def tick(self, now, demand, **kw):
        t0 = self.timer()
        try:
            r = self.pool.tick(now, demand, **kw)
        except (ValueError, OverflowError) as exc:
            self.reg.inc("inv08_tick_errors_total", reason=type(exc).__name__)
            raise
        finally:
            self.reg.observe("inv08_decision_latency_seconds", max(0.0, self.timer() - t0))
        for n in r["reclaimed"]:
            if n in self._born:
                self.reg.observe("inv08_lease_age_seconds", max(0.0, (now - self._born.pop(n)) * 3600.0))
        for n in self.pool.nodes:
            self._born.setdefault(n, now)
        self.reg.set("inv08_pool_nodes", r["size"])
        self.reg.set("inv08_pool_target_nodes", r["target"])
        try:
            self.reg.set("inv08_pool_demand_units", float(r["demand"]))
        except OverflowError:  # arbitrarily large int demand
            self.reg.set("inv08_pool_demand_units", 1.7976931348623157e308)
        self.reg.inc("inv08_pool_node_hours_total", max(0.0, r["node_hours"] - self._nh))
        self._nh = r["node_hours"]
        self.reg.inc("inv08_pool_nodes_added_total", r["added"])
        self.reg.inc("inv08_pool_nodes_reclaimed_total", len(r["reclaimed"]))
        self.reg.inc("inv08_pool_leases_renewed_total", len(r["renewed"]))
        self.reg.set("inv08_reconcile_drift_nodes", abs(r["size"] - r["target"]))
        return r
