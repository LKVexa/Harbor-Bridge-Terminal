"""Policy integration, constraint precedence and adjacent-layer adapters.

* MC-022 — ``PolicyGate`` calls a GAP-13 ``PolicyEngine`` before apply.  The
  decision is bound to the plan digest and the policy bundle version; a denial
  propagates reasons; engine errors, timeouts or malformed decisions fail
  closed.
* MC-009 — ``CONSTRAINT_PRECEDENCE`` and ``resolve_constraints`` give a single
  deterministic ordering (security > residency > consistency > availability >
  SLO > cost > operator override) so a lower class can never overrule a
  higher one.
* MC-023 — ``InventoryIngest`` (INV-01 → INV-06), ``GitOpsHandoff``
  (INV-06 → INV-07) and ``DynamicPoolHandoff`` (INV-06 → INV-08) define and
  validate the versioned handoff documents.  They are contracts plus
  validators; the neighbouring services themselves live outside this package.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .state import IacError, _canonical_bytes, _normalise_resource_map

DECISION_SCHEMA = "PK_POLICY_DECISION/1"
INVENTORY_SCHEMA = "PK_INV01_INVENTORY/1"
GITOPS_SCHEMA = "PK_INV07_CHANGESET/1"
POOL_SCHEMA = "PK_INV08_POOL_HANDOFF/1"


class PolicyDenied(IacError):
    code = "PK_IAC_POLICY_DENIED"


class PolicyUnavailable(IacError):
    code = "PK_IAC_POLICY_UNAVAILABLE"


class ConstraintConflict(IacError):
    code = "PK_IAC_CONSTRAINT_CONFLICT"


class HandoffInvalid(IacError):
    code = "PK_IAC_HANDOFF_INVALID"


class PolicyEngine(Protocol):
    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


@dataclass
class RulePolicyEngine:
    """Reference engine: callables ``rule(plan) -> list[str] reasons``.  Used in tests/air-gapped mode."""

    version: str
    rules: dict[str, Any] = field(default_factory=dict)

    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        reasons = []
        for name, rule in sorted(self.rules.items()):
            for r in rule(request["plan"]) or []:
                reasons.append({"rule": name, "reason": r})
        return {
            "schema": DECISION_SCHEMA,
            "allow": not reasons,
            "reasons": reasons,
            "policy_version": self.version,
            "plan_digest": request["plan"]["integrity"]["digest"],
        }


class PolicyGate:
    def __init__(self, engine: PolicyEngine, *, required_version: str | None = None) -> None:
        self.engine, self.required_version = engine, required_version

    def check(self, plan: Mapping[str, Any], *, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        request = {"schema": "PK_POLICY_REQUEST/1", "plan": plan, "context": dict(context or {})}
        try:
            decision = dict(self.engine.evaluate(request))
        except Exception as exc:  # noqa: BLE001 - any engine failure fails closed
            raise PolicyUnavailable("policy engine failed; refusing apply", details={"error": type(exc).__name__}) from exc
        if decision.get("schema") != DECISION_SCHEMA or not isinstance(decision.get("allow"), bool):
            raise PolicyUnavailable("malformed policy decision; refusing apply")
        if decision.get("plan_digest") != plan["integrity"]["digest"]:
            raise PolicyUnavailable("policy decision not bound to this plan")
        if self.required_version and decision.get("policy_version") != self.required_version:
            raise PolicyUnavailable("policy bundle version mismatch", details={"required": self.required_version, "actual": decision.get("policy_version")})
        if not decision["allow"]:
            raise PolicyDenied("policy denied plan", details={"reasons": decision.get("reasons", []), "policy_version": decision.get("policy_version")})
        return decision


def no_delete_in_prod(plan: Mapping[str, Any]) -> list[str]:
    return [f"delete of {r} requires change-window approval" for r in plan.get("delete", [])]


def forbid_public_ingress(plan: Mapping[str, Any]) -> list[str]:
    out = []
    for rid, v in {**plan.get("create", {}), **plan.get("update", {})}.items():
        if isinstance(v, Mapping) and "0.0.0.0/0" in str(v.get("ingress", "")):
            out.append(f"{rid} opens ingress to 0.0.0.0/0")
    return out


# --------------------------------------------------------------- precedence
CONSTRAINT_PRECEDENCE = ("security", "residency", "consistency", "availability", "slo", "cost", "operator_override")


def resolve_constraints(proposals: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Each proposal: ``{"class": <precedence class>, "key": str, "value": Any}``.

    For each key the highest-precedence class wins.  Two proposals of the
    *same* class with different values are an unresolvable conflict and fail.
    An ``operator_override`` can therefore only set keys no higher class set.
    """
    rank = {c: i for i, c in enumerate(CONSTRAINT_PRECEDENCE)}
    chosen: dict[str, tuple[int, Any, str]] = {}
    for p in proposals:
        cls = p.get("class")
        if cls not in rank:
            raise ConstraintConflict("unknown constraint class", details={"class": cls})
        k, v, r = p["key"], p["value"], rank[cls]
        if k in chosen:
            cr, cv, _ = chosen[k]
            if r == cr and cv != v:
                raise ConstraintConflict("same-precedence conflict", details={"key": k, "class": cls})
            if r >= cr:
                continue
        chosen[k] = (r, v, cls)
    return {k: {"value": v, "decided_by": c} for k, (_, v, c) in sorted(chosen.items())}


# ------------------------------------------------------------ INV adapters
_RID = re.compile(r"^[A-Za-z_][\w-]*\.[A-Za-z_][\w-]*$")


def _digest(obj: Any) -> str:
    return hashlib.sha256(_canonical_bytes(obj)).hexdigest()


class InventoryIngest:
    """INV-01 inventory → desired-resource map (codify inventoried hosts)."""

    @staticmethod
    def to_desired(doc: Mapping[str, Any]) -> dict[str, Any]:
        if doc.get("schema") != INVENTORY_SCHEMA or not isinstance(doc.get("hosts"), list):
            raise HandoffInvalid("unsupported INV-01 inventory document", details={"schema": doc.get("schema")})
        out: dict[str, Any] = {}
        for h in doc["hosts"]:
            if not isinstance(h, Mapping) or not re.fullmatch(r"[A-Za-z0-9_-]{1,63}", str(h.get("id", ""))):
                raise HandoffInvalid("inventory host lacks a valid id", details={"host": str(h)[:80]})
            rid = f"host.{h['id']}"
            if rid in out:
                raise HandoffInvalid("duplicate inventory host", details={"id": h["id"]})
            out[rid] = {k: v for k, v in h.items() if k != "id"}
        return _normalise_resource_map(out, label="inventory")


class GitOpsHandoff:
    """INV-06 applied plan → INV-07 git changeset document."""

    @staticmethod
    def build(plan: Mapping[str, Any], *, applied_serial: int, source_revision: str) -> dict[str, Any]:
        doc = {
            "schema": GITOPS_SCHEMA,
            "plan_digest": plan["integrity"]["digest"],
            "applied_serial": applied_serial,
            "source_revision": source_revision,
            "changes": {k: sorted(plan[k]) for k in ("create", "update", "delete")},
        }
        doc["digest"] = _digest(doc)
        return doc

    @staticmethod
    def verify(doc: Mapping[str, Any]) -> None:
        body = {k: v for k, v in doc.items() if k != "digest"}
        if doc.get("schema") != GITOPS_SCHEMA or _digest(body) != doc.get("digest"):
            raise HandoffInvalid("INV-07 changeset invalid or tampered")


class DynamicPoolHandoff:
    """INV-06 static resources → INV-08 elastic pool ownership transfer."""

    @staticmethod
    def build(state_snapshot: Mapping[str, Any], resources: list[str], pool: str) -> dict[str, Any]:
        missing = [r for r in resources if r not in state_snapshot["resources"]]
        if missing:
            raise HandoffInvalid("cannot hand off resources absent from state", details={"missing": missing})
        if not re.fullmatch(r"[a-z0-9-]{1,63}", pool):
            raise HandoffInvalid("invalid pool name")
        doc = {
            "schema": POOL_SCHEMA,
            "pool": pool,
            "from_serial": state_snapshot["serial"],
            "resources": {r: state_snapshot["resources"][r] for r in sorted(resources)},
        }
        doc["digest"] = _digest(doc)
        return doc
