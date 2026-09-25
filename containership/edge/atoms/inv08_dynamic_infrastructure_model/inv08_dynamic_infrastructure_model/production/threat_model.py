"""Component 34 - machine-readable STRIDE threat model for the INV-08 lease pool.

Contract ``PK_DYN_THREAT/1`` (see docs/34_threat_model.md):
  * assets, flows and trust boundaries have unique ids; every flow endpoint is a
    declared asset/actor and every boundary crossing is declared;
  * every threat has one STRIDE category, targets a declared asset or flow, and
    lists >=1 mitigation reference ``production/<module>.py::<Symbol>`` that must
    resolve to a real symbol in this overlay (``resolve_mitigations``);
  * residual risk acceptance is ``UNACCEPTED`` with owner ``UNASSIGNED`` until a
    human risk owner signs it - this module never marks a risk accepted;
  * attack trees are AND/OR trees whose leaves are threat ids.
Unsupported: any other schema version, unknown STRIDE letter, dangling ids.
"""
from __future__ import annotations

import importlib
from typing import Any

from .core import Inv08Error, digest

SCHEMA = "PK_DYN_THREAT/1"
STRIDE = {"S": "Spoofing", "T": "Tampering", "R": "Repudiation", "I": "Information disclosure",
          "D": "Denial of service", "E": "Elevation of privilege"}
RISK_LEVELS = ("low", "medium", "high", "critical")
ABUSE_KINDS = ("tenant", "compromised_node", "supply_chain", "replay", "spoofing", "operator", "provider")

_UNACC = {"acceptance": "UNACCEPTED", "owner": "UNASSIGNED"}


def _t(tid, cat, target, abuse, title, mitigations, residual):
    return {"id": tid, "stride": cat, "target": target, "abuse_case": abuse, "title": title,
            "mitigations": mitigations, "residual_risk": dict(_UNACC, level=residual)}


MODEL: dict[str, Any] = {
    "schema": SCHEMA,
    "system": "INV-08 dynamic infrastructure lease pool (model.Pool + production overlay)",
    "assets": [
        {"id": "A.pool_state", "kind": "data", "desc": "Pool.nodes lease table, _n counter, node_hours"},
        {"id": "A.policy_bundle", "kind": "data", "desc": "min/max/per_node/lease_ttl policy bundle"},
        {"id": "A.artifact", "kind": "data", "desc": "released package artifacts + provenance"},
        {"id": "A.audit_log", "kind": "data", "desc": "PK_DYN_AUDIT/1 hash-chained log"},
        {"id": "A.keys", "kind": "secret", "desc": "HMAC trust root, KEK/DEK hierarchy"},
        {"id": "A.tenant_state", "kind": "data", "desc": "per-tenant workload state"},
        {"id": "A.telemetry", "kind": "data", "desc": "metrics, logs, traces, decision journal"},
        {"id": "P.controller", "kind": "process", "desc": "control loop calling Pool.tick"},
        {"id": "P.node_agent", "kind": "process", "desc": "agent on a leased node (untrusted once compromised)"},
        {"id": "P.provider", "kind": "external", "desc": "cloud/edge provider API (PK_DYN_PROVIDER)"},
        {"id": "P.tenant", "kind": "external", "desc": "tenant workload submitting demand"},
        {"id": "P.operator", "kind": "external", "desc": "human operator / CI"},
    ],
    "boundaries": [
        {"id": "B.tenant", "desc": "tenant workload <-> control plane"},
        {"id": "B.node", "desc": "leased node <-> control plane"},
        {"id": "B.provider", "desc": "control plane <-> external provider"},
        {"id": "B.supply", "desc": "build/release pipeline <-> runtime"},
        {"id": "B.operator", "desc": "operator/CI <-> control plane"},
    ],
    "flows": [
        {"id": "F.demand", "src": "P.tenant", "dst": "P.controller", "data": "demand", "crosses": ["B.tenant"]},
        {"id": "F.heartbeat", "src": "P.node_agent", "dst": "P.controller", "data": "busy flag, attestation evidence", "crosses": ["B.node"]},
        {"id": "F.provision", "src": "P.controller", "dst": "P.provider", "data": "add/reclaim node", "crosses": ["B.provider"]},
        {"id": "F.release", "src": "P.operator", "dst": "P.controller", "data": "artifact + policy bundle", "crosses": ["B.supply", "B.operator"]},
        {"id": "F.audit", "src": "P.controller", "dst": "A.audit_log", "data": "audit events", "crosses": []},
        {"id": "F.telemetry", "src": "P.controller", "dst": "A.telemetry", "data": "metrics/logs/journal", "crosses": []},
        {"id": "F.state", "src": "P.tenant", "dst": "A.tenant_state", "data": "tenant data", "crosses": ["B.tenant"]},
    ],
    "threats": [
        _t("T01", "S", "F.heartbeat", "compromised_node", "Node agent forges attestation to rejoin pool",
           ["production/attestation.py::AttestationVerifier", "production/attestation.py::NonceIssuer"], "medium"),
        _t("T02", "S", "F.heartbeat", "replay", "Replay of an old valid attestation quote",
           ["production/attestation.py::NonceIssuer.consume"], "low"),
        _t("T03", "T", "A.artifact", "supply_chain", "Tampered artifact deployed to controller",
           ["production/artifact_verify.py::verify_digest", "production/artifact_verify.py::verify_provenance"], "medium"),
        _t("T04", "T", "A.policy_bundle", "supply_chain", "Unsigned/malformed policy bundle widens max_nodes",
           ["production/artifact_verify.py::validate_policy_bundle", "production/artifact_verify.py::ArtifactGate"], "medium"),
        _t("T05", "S", "F.release", "spoofing", "Signature by revoked or out-of-scope delegated key",
           ["production/artifact_verify.py::verify_chain"], "high"),
        _t("T06", "T", "A.audit_log", "operator", "Audit log edited, reordered or truncated",
           ["production/audit.py::verify_file", "production/audit.py::verify_against_checkpoint"], "low"),
        _t("T07", "R", "A.pool_state", "operator", "Scaling decision cannot be explained or attributed",
           ["production/explain.py::DecisionJournal", "production/audit.py::AuditLog"], "low"),
        _t("T08", "I", "A.tenant_state", "tenant", "Tenant reads another tenant's state",
           ["production/isolation.py::NamespacedState", "production/isolation.py::check_isolation"], "high"),
        _t("T09", "I", "A.telemetry", "tenant", "Secrets or PII leak through logs/errors",
           ["production/logging_trace.py::StructuredLogger", "production/telemetry_gov.py::minimize"], "medium"),
        _t("T10", "D", "F.demand", "tenant", "Huge/NaN demand exhausts controller or forces over-provisioning",
           ["production/capacity.py::QuotaModel", "production/metrics.py::Registry"], "low"),
        _t("T11", "D", "A.telemetry", "tenant", "Label cardinality explosion exhausts metrics backend",
           ["production/metrics.py::Registry", "production/telemetry_gov.py::detect_high_cardinality"], "low"),
        _t("T12", "E", "A.keys", "compromised_node", "Compromised KEK used to derive tenant DEKs",
           ["production/keys.py::KeyHierarchy.compromise", "production/keys.py::KeyHierarchy.revoke"], "high"),
        _t("T13", "E", "F.state", "tenant", "Tenant escapes namespace to write shared state",
           ["production/isolation.py::NamespacedState"], "high"),
        _t("T14", "S", "F.provision", "provider", "Spoofed provider response claims node provisioned",
           ["production/attestation.py::AttestationVerifier"], "medium"),
    ],
    "attack_trees": [
        {"goal": "Run unauthorised code on a pool node", "op": "OR", "children": [
            {"op": "AND", "children": ["T03", "T05"]},
            {"op": "AND", "children": ["T01", "T02"]},
            "T14"]},
        {"goal": "Access another tenant's data", "op": "OR", "children": [
            "T08", "T13", {"op": "AND", "children": ["T12", "T01"]}]},
        {"goal": "Hide malicious scaling decision", "op": "AND", "children": ["T06", "T07"]},
    ],
}


def _err(msg: str) -> Inv08Error:
    return Inv08Error("INV08.THREAT.INVALID_MODEL", msg, remediation="fix threat_model.MODEL")


def _tree_leaves(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if not isinstance(node, dict) or node.get("op") not in ("AND", "OR") or not node.get("children"):
        raise _err(f"bad attack-tree node {node!r}")
    return [leaf for c in node["children"] for leaf in _tree_leaves(c)]


def validate_model(model: dict | None = None) -> list[str]:
    """Raise Inv08Error on structural violation; return list of threat ids."""
    m = MODEL if model is None else model
    if m.get("schema") != SCHEMA:
        raise _err(f"unsupported schema {m.get('schema')!r}")
    ids: set[str] = set()
    for sect in ("assets", "boundaries", "flows", "threats"):
        for item in m.get(sect, []):
            if item["id"] in ids:
                raise _err(f"duplicate id {item['id']}")
            ids.add(item["id"])
    assets = {a["id"] for a in m["assets"]}
    bounds = {b["id"] for b in m["boundaries"]}
    flows = {f["id"] for f in m["flows"]}
    for f in m["flows"]:
        if f["src"] not in assets or f["dst"] not in assets:
            raise _err(f"flow {f['id']} endpoint undeclared")
        for b in f["crosses"]:
            if b not in bounds:
                raise _err(f"flow {f['id']} crosses undeclared boundary {b}")
    tids = []
    for t in m["threats"]:
        if t["stride"] not in STRIDE:
            raise _err(f"{t['id']}: unknown STRIDE category {t['stride']!r}")
        if t["target"] not in assets | flows:
            raise _err(f"{t['id']}: undeclared target {t['target']}")
        if t["abuse_case"] not in ABUSE_KINDS:
            raise _err(f"{t['id']}: unknown abuse case {t['abuse_case']}")
        if not t["mitigations"]:
            raise _err(f"{t['id']}: no mitigation")
        rr = t["residual_risk"]
        if rr.get("level") not in RISK_LEVELS:
            raise _err(f"{t['id']}: bad residual level")
        if rr.get("acceptance") == "ACCEPTED" and rr.get("owner") in (None, "", "UNASSIGNED"):
            raise _err(f"{t['id']}: risk accepted without a named owner")
        tids.append(t["id"])
    for tree in m["attack_trees"]:
        for leaf in _tree_leaves(tree):
            if leaf not in tids:
                raise _err(f"attack tree {tree['goal']!r} references unknown threat {leaf}")
    return tids


def resolve_ref(ref: str) -> Any:
    """Resolve ``production/<mod>.py::A.b`` to the live Python object."""
    try:
        path, sym = ref.split("::")
    except ValueError:
        raise _err(f"malformed mitigation ref {ref!r}")
    if not (path.startswith("production/") and path.endswith(".py")) or "/" in path[11:]:
        raise _err(f"mitigation ref outside overlay: {ref!r}")
    mod = importlib.import_module("." + path[11:-3], __package__)
    obj: Any = mod
    for part in sym.split("."):
        if not hasattr(obj, part):
            raise _err(f"unresolved mitigation {ref!r}")
        obj = getattr(obj, part)
    return obj


def resolve_mitigations(model: dict | None = None) -> dict[str, Any]:
    m = MODEL if model is None else model
    return {ref: resolve_ref(ref) for t in m["threats"] for ref in t["mitigations"]}


def tree_achievable(node, unmitigated: set[str]) -> bool:
    """Attack goal reachable given the set of threat ids whose mitigations failed."""
    if isinstance(node, str):
        return node in unmitigated
    vals = [tree_achievable(c, unmitigated) for c in node["children"]]
    return all(vals) if node["op"] == "AND" else any(vals)


def abuse_cases(kind: str, model: dict | None = None) -> list[dict]:
    if kind not in ABUSE_KINDS:
        raise _err(f"unknown abuse kind {kind}")
    return [t for t in (MODEL if model is None else model)["threats"] if t["abuse_case"] == kind]


def residual_risk_register(model: dict | None = None) -> list[dict]:
    m = MODEL if model is None else model
    return [{"threat": t["id"], **t["residual_risk"]} for t in m["threats"]]


def model_digest(model: dict | None = None) -> str:
    return digest(MODEL if model is None else model)
