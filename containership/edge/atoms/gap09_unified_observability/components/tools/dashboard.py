"""Dashboards and operational views (59).

``DASHBOARDS`` is the declarative definition (panels -> metric sources);
``render(ingest, health)`` produces the text operational view from live
counters.  Every panel names the counter it reads, so an empty panel is
visibly "no data" rather than a zero."""
from __future__ import annotations

DASHBOARDS = {
    "GAP09 / Ingest trust": [
        ("accepted submissions", "ingest.accepted"), ("refused submissions", "ingest.refused"),
        ("rejections by code", "store.rejections"), ("replay cache entries", "store.replay_cache_entries"),
        ("quarantines active", "quarantine.active"), ("admission shed", "admission.shed"),
    ],
    "GAP09 / Capacity": [
        ("active signals", "store.active_signals"), ("tenant series usage", "quota.usage"),
        ("admission in-flight", "admission.inflight"), ("decisions recorded", "decisions.total"),
    ],
    "GAP09 / Health": [("readiness", "health.ready"), ("mode", "health.mode"), ("dependencies", "health.dependencies"),
                       ("config digest", "health.config_digest")],
}


def sources(ingest, health) -> dict:
    m = ingest.store.metrics()
    h = health.report() if health else {}
    return {"ingest.accepted": ingest.accepted, "ingest.refused": ingest.refused,
            "store.rejections": m.get("rejected_submissions"), "store.replay_cache_entries": m.get("replay_cache_entries"),
            "store.active_signals": m.get("active_signals"), "quarantine.active": len(ingest.quarantine.active()),
            "admission.shed": ingest.admission.shed, "admission.inflight": ingest.admission.inflight,
            "quota.usage": ingest.quota.usage(), "decisions.total": ingest.admission.decisions.total,
            "health.ready": h.get("ready"), "health.mode": h.get("mode"), "health.dependencies": h.get("dependencies"),
            "health.config_digest": (h.get("config_digest") or "")[:12] or None}


def render(ingest, health=None) -> str:
    src = sources(ingest, health)
    lines = []
    for board, panels in DASHBOARDS.items():
        lines.append(f"== {board} ==")
        for label, key in panels:
            v = src.get(key)
            lines.append(f"  {label:28s} {'no data' if v is None else v}")
    return "\n".join(lines)
