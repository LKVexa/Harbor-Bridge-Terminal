"""Policy precedence resolution (INV-37-C019).  Deterministic; the policy
document is versioned and its digest is part of decision records."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .errors import CodedError

_POLICY_PATH = Path(__file__).resolve().parent / "policy" / "precedence.json"
REJECT_CODE = {"security": "authorization_denied", "residency": "residency_violation", "integrity": "digest_mismatch",
               "safety_limit": "quota_exceeded"}


def load(path: Path = _POLICY_PATH) -> dict[str, Any]:
    p = json.loads(path.read_text(encoding="utf-8"))
    if p.get("schema") != "INV37_PRECEDENCE/1":
        raise CodedError("invalid_config", "unsupported precedence schema")
    p["digest"] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return p


def resolve(options: list[Mapping[str, Any]], policy: Mapping[str, Any] | None = None,
            override: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Choose among candidate plans.  Each option: {"name", "violates": [dimension...], "score": float}.
    An option violating a never-overridable dimension is removed; remaining
    options are ranked by the highest-precedence dimension they violate (later =
    better), then by score.  Returns a decision with explain data."""
    policy = policy or load()
    order = policy["order"]
    rank = {d: i for i, d in enumerate(order)}
    ov_dims = set(override.get("dimensions", [])) if override else set()
    if ov_dims - set(policy["emergency_override"]["allowed_for"]):
        raise CodedError("authorization_denied", "override not permitted for dimension", dims=sorted(ov_dims))
    if override and override.get("approver_role") not in policy["emergency_override"]["approver_roles"]:
        raise CodedError("authorization_denied", "override approver role not permitted")
    eligible, rejected = [], []
    for o in options:
        v = [d for d in o.get("violates", []) if d not in ov_dims]
        hard = [d for d in v if d in policy["never_overridable"] or d not in policy["auto_resolvable"]]
        if hard:
            worst = min(hard, key=rank.__getitem__)
            rejected.append({"name": o["name"], "reason_code": REJECT_CODE.get(worst, "policy_rejection"), "dimension": worst})
        else:
            eligible.append((max((rank[d] for d in v), default=len(order)), o.get("score", 0.0), o["name"], v))
    if not eligible:
        first = min(rejected, key=lambda r: rank[r["dimension"]]) if rejected else {"reason_code": "policy_rejection"}
        return {"decision": "reject", "reason_code": first["reason_code"], "rejected": rejected, "policy_digest": policy.get("digest")}
    eligible.sort(key=lambda e: (-e[0], -e[1]))
    best = eligible[0]
    return {"decision": "select", "selected": best[2], "accepted_tradeoffs": best[3], "rejected": rejected,
            "policy_version": policy["version"], "policy_digest": policy.get("digest"), "override": dict(override) if override else None}
