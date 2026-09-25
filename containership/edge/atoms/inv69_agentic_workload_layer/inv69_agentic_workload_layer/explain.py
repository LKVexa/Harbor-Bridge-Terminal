"""Operator explain view (C077).

Deterministically renders machine-readable evidence (run events + decision
records) into chronological and decision-tree text.  It never invents
rationale: any input missing from the evidence is printed as ``<unavailable>``.
Access is tenant-scoped: a caller may only explain runs of tenants it holds.

CLI:  python -m inv69_agentic_workload_layer.explain EVIDENCE.json RUN_ID --tenant T
"""
from __future__ import annotations

from typing import Any, Mapping
import argparse
import json
import sys

from .errors import REGISTRY, AgentError
from .redaction import redact

U = "<unavailable>"


def _g(d: Mapping, k: str) -> Any:
    v = d.get(k)
    return U if v is None else v


def explain_run(events: list[Mapping[str, Any]], decisions: list[Mapping[str, Any]], run_id: str, *,
                caller_tenants: set[str]) -> dict[str, Any]:
    run_events = [e for e in events if e.get("run_id") == run_id]
    if not run_events:
        raise AgentError("AGT-VAL-001", "no evidence for run", details={"run_id": run_id})
    tenant = next((e.get("tenant") for e in run_events if e.get("tenant")), None)
    if tenant is None or tenant not in caller_tenants:
        raise AgentError("AGT-AUTHZ-002", "caller not authorized for this run's tenant")
    corr = {e.get("correlation_id") for e in run_events}
    decs = [d for d in decisions if d.get("run_id") == run_id or d.get("correlation_id") in corr]
    timeline = []
    for e in run_events:
        timeline.append({
            "seq": e["seq"], "event_hash": e["event_hash"], "kind": e["kind"], "at": e["at"],
            "tool": _g(e, "tool"), "outcome": _g(e, "outcome"), "code": e.get("code"),
            "code_meaning": REGISTRY[e["code"]].hint if e.get("code") in REGISTRY else None,
            "config": {"digest": _g(e, "config_digest"), "generation": _g(e, "config_generation")},
            "profile": _g(e, "profile"), "precedence_policy": _g(e, "precedence_policy"),
            "topology": {k: _g(e.get("lineage") or {}, k) for k in ("node", "site", "cluster", "topology_snapshot")},
            "trace_id": _g(e, "trace_id"), "correlation_id": _g(e, "correlation_id"),
        })
    tree = []
    for d in decs:
        node = {"decision_point": _g(d, "decision_point"), "policy_version": _g(d, "policy_version"),
                "chosen": d.get("chosen", d.get("decision", U)), "winning_constraint": d.get("winning_constraint"),
                "evaluated": [{"constraint": t["constraint"], "class": t["class"], "hard": t["hard"],
                               "satisfied": t["satisfied"], "candidate": t["candidate"]} for t in d.get("trace", [])],
                "rejected": d.get("rejected", []),
                "inputs": {k: d[k] for k in ("tool", "risk", "required_tier", "fast_available", "generated_code",
                                             "forced_heavy") if k in d}}
        tree.append(node)
    return redact({"schema": "PK_AGENT_EXPLAIN/1", "run_id": run_id, "tenant": tenant, "timeline": timeline,
                   "decisions": tree})


def render_text(x: Mapping[str, Any]) -> str:
    lines = [f"EXPLAIN run={x['run_id']} tenant={x['tenant']}", "", "Timeline:"]
    for t in x["timeline"]:
        lines.append(f"  #{t['seq']:>3} {t['kind']:<18} tool={t['tool']} outcome={t['outcome']} code={t['code'] or '-'}"
                     f" cfg={str(t['config']['digest'])[:12]}@g{t['config']['generation']} profile={t['profile']}"
                     f" node={t['topology']['node']} snap={t['topology']['topology_snapshot']} ev={t['event_hash'][:12]}")
        if t["code_meaning"]:
            lines.append(f"        -> {t['code_meaning']}")
    lines += ["", "Decisions:"]
    for d in x["decisions"]:
        lines.append(f"  [{d['decision_point']}] policy={d['policy_version']} chosen={d['chosen']}")
        for k, v in d["inputs"].items():
            lines.append(f"      input {k} = {v}")
        for ev in d["evaluated"]:
            mark = "ok " if ev["satisfied"] else "NO "
            lines.append(f"      {mark}{'HARD' if ev['hard'] else 'soft'} {ev['class']}: {ev['constraint']} on {ev['candidate']}")
        for r in d["rejected"]:
            lines.append(f"      rejected {r['candidate']} blocked_by {r['blocked_by']} ({r['class']})")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence")
    ap.add_argument("run_id")
    ap.add_argument("--tenant", action="append", required=True)
    a = ap.parse_args(argv)
    doc = json.load(open(a.evidence, encoding="utf-8"))
    try:
        x = explain_run(doc["events"], doc.get("decisions", []), a.run_id, caller_tenants=set(a.tenant))
    except AgentError as e:
        print(json.dumps(e.to_dict(), indent=2))
        return 2
    print(render_text(x))
    return 0


if __name__ == "__main__":
    sys.exit(main())
