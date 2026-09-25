"""Decision records and the operator explain view (C076, C077, C078).

Every capture/restore/delete/quarantine decision produces a
``PK_SNAPSHOT_DECISION/1`` record: inputs (identifiers only, never secret or
guest material), the ordered checks evaluated with pass/fail, the rule that
decided (policy precedence id or error code), the effective configuration
revision and policy version, and caller-supplied release/topology lineage
(allowlisted keys, redacted, length-capped). :func:`render_text` turns a
record into an incident-note table.
"""
from __future__ import annotations

from typing import Any, Mapping

from .redaction import redact

DECISION_SCHEMA = "PK_SNAPSHOT_DECISION/1"
LINEAGE_KEYS = ("app_release", "release_id", "commit", "infrastructure_graph", "cluster", "site", "node",
                "topology", "change_ref", "pipeline_run")


def lineage(raw: Any) -> dict:
    if not isinstance(raw, Mapping):
        return {}
    return {k: str(redact(raw[k]))[:256] for k in LINEAGE_KEYS if k in raw}


class DecisionRecorder:
    def __init__(self, operation: str, operation_id: str, *, config_revision: int | None, policy_version: str,
                 correlation_id: str, lineage_in: Any = None):
        self.rec = {"schema": DECISION_SCHEMA, "operation": operation, "operation_id": operation_id,
                    "correlation_id": correlation_id, "config_revision": config_revision,
                    "policy_version": policy_version, "inputs": {}, "checks": [], "decided_by": None,
                    "result": None, "lineage": lineage(lineage_in)}

    def inputs(self, **kv: Any) -> None:
        self.rec["inputs"].update({k: str(redact(v))[:128] for k, v in kv.items()})

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        self.rec["checks"].append({"check": name, "passed": bool(passed), "detail": str(redact(detail))[:200]})

    def decide(self, result: str, rule: str) -> dict:
        self.rec["result"], self.rec["decided_by"] = result, rule
        return self.rec


def render_text(rec: Mapping[str, Any]) -> str:
    lines = [f"{rec['operation']} {rec['operation_id']}  result={rec['result']}  decided_by={rec['decided_by']}",
             f"config_revision={rec['config_revision']}  policy={rec['policy_version']}  "
             f"correlation={rec['correlation_id']}",
             "inputs: " + ", ".join(f"{k}={v}" for k, v in sorted(rec["inputs"].items()))]
    for c in rec["checks"]:
        lines.append(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['check']:<28} {c['detail']}")
    if rec.get("lineage"):
        lines.append("lineage: " + ", ".join(f"{k}={v}" for k, v in sorted(rec["lineage"].items())))
    return "\n".join(lines)
