"""Checklists 13, 16, 17, 18: trust-class policy and adjacent-layer mappings.

A versioned policy document (``policy/default_policy.json``) is the single
source that derives a *required mitigation set* and *SMT rule* from:

* the workload trust classes on each side of the boundary (checklist 13),
* the execution-plane isolation tier chosen by PLN-04 (checklist 17),
* the node's CPU lineage as reported by GAP-02 capability discovery
  (checklists 16 and 18: INV-34 legacy CPUs get stricter handling).

The requirement for a *pair* of workloads is the union of both sides'
requirements (the stricter side always wins).  Unknown trust classes,
unknown tiers and policy documents whose digest does not match their
declared digest are refused.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass

from .defense import REQUIRED_FOR_COTENANCY, MitigationMissing, _require_identifier

POLICY_SCHEMA = "INV43_POLICY/1"
DEFAULT_POLICY_PATH = pathlib.Path(__file__).resolve().parent / "policy" / "default_policy.json"


class PolicyError(MitigationMissing):
    def __init__(self, message: str, code: str, **details):
        super().__init__(message, code=code, details=details)


def canonical_digest(doc: dict) -> str:
    body = {k: v for k, v in doc.items() if k != "digest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Requirement:
    mitigations: tuple[str, ...]
    forbid_smt_without_core_sched: bool
    cross_tenant_allowed: bool
    policy_version: str
    policy_digest: str
    derivation: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "mitigations": list(self.mitigations),
            "forbid_smt_without_core_sched": self.forbid_smt_without_core_sched,
            "cross_tenant_allowed": self.cross_tenant_allowed,
            "policy_version": self.policy_version,
            "policy_digest": self.policy_digest,
            "derivation": list(self.derivation),
        }


class Policy:
    def __init__(self, doc: dict) -> None:
        if not isinstance(doc, dict) or doc.get("schema") != POLICY_SCHEMA:
            raise PolicyError("not an INV43_POLICY/1 document", "policy_schema")
        declared = doc.get("digest")
        actual = canonical_digest(doc)
        if declared != actual:
            raise PolicyError("policy digest mismatch", "policy_digest_mismatch", declared=declared, actual=actual)
        self.doc = doc
        self.version = str(doc["version"])
        self.digest = actual
        base = doc.get("baseline", [])
        if not set(REQUIRED_FOR_COTENANCY) <= set(base):
            raise PolicyError("policy baseline weaker than the INV-43 floor", "policy_below_floor",
                              floor=list(REQUIRED_FOR_COTENANCY))
        self.baseline = tuple(base)
        self.classes: dict[str, dict] = doc["trust_classes"]
        self.tiers: dict[str, dict] = doc["isolation_tiers"]
        self.legacy: dict = doc.get("legacy_cpu", {})

    @classmethod
    def load(cls, path: str | pathlib.Path = DEFAULT_POLICY_PATH) -> "Policy":
        return cls(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))

    def requirement(self, class_a: str, class_b: str, *, tier: str, cpu_lineage: str | None = None,
                    same_tenant: bool = False) -> Requirement:
        _require_identifier(class_a, "trust class")
        _require_identifier(class_b, "trust class")
        _require_identifier(tier, "isolation tier")
        for c in (class_a, class_b):
            if c not in self.classes:
                raise PolicyError(f"unknown trust class {c!r}", "policy_unknown_trust_class", trust_class=c)
        if tier not in self.tiers:
            raise PolicyError(f"unknown isolation tier {tier!r}", "policy_unknown_tier", tier=tier)
        names: list[str] = list(self.baseline)
        why = [f"baseline:{','.join(self.baseline)}"]
        forbid_smt = True
        allowed = True
        for c in sorted({class_a, class_b}):
            extra = self.classes[c].get("extra_mitigations", [])
            names += extra
            if extra:
                why.append(f"class:{c}:+{','.join(extra)}")
            if self.classes[c].get("no_cotenancy"):
                allowed = False
                why.append(f"class:{c}:no_cotenancy")
        t = self.tiers[tier]
        names += t.get("extra_mitigations", [])
        if t.get("extra_mitigations"):
            why.append(f"tier:{tier}:+{','.join(t['extra_mitigations'])}")
        if t.get("hardware_boundary_dedicated"):
            # dedicated host: no sibling sharing at all, the node never mixes tenants
            allowed = False
            why.append(f"tier:{tier}:dedicated_host")
        if cpu_lineage is not None:
            lin = self.legacy.get("lineages", {}).get(cpu_lineage)
            if lin is None and self.legacy.get("unknown_lineage") == "deny":
                allowed = False
                why.append(f"inv34:unknown_lineage:{cpu_lineage}:deny")
            elif lin is not None:
                names += lin.get("extra_mitigations", [])
                if lin.get("no_cotenancy"):
                    allowed = False
                why.append(f"inv34:{cpu_lineage}:{lin.get('note', 'mapped')}")
        seen: list[str] = []
        for n in names:
            if n not in seen:
                seen.append(n)
        if same_tenant:
            allowed = True
            why.append("same_tenant:no_boundary")
        return Requirement(tuple(seen), forbid_smt, allowed, self.version, self.digest, tuple(why))


def gap02_contradictions(capabilities: dict, readback_statuses: dict[str, str]) -> list[dict]:
    """Checklist 16: compare GAP-02 capability discovery with node read-back.

    ``capabilities`` is the GAP-02 record: ``{"vendor":..., "family":...,
    "model":..., "microcode":..., "affected": [mitigation names the CPU is
    known to be affected by]}``.  A read-back of ``not_affected`` for a class
    GAP-02 lists as affected is a contradiction; the caller must treat the
    node as ``unknown`` for that class (fail closed) and raise an alert.
    """
    out = []
    for name in capabilities.get("affected", []):
        st = readback_statuses.get(name)
        if st == "not_affected":
            out.append({"mitigation": name, "code": "gap02_readback_contradiction",
                        "gap02": "affected", "readback": st})
    return out


def seal_policy(doc: dict) -> dict:
    d = dict(doc)
    d["digest"] = canonical_digest(d)
    return d
