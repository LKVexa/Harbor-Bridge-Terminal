"""Site/environment overlays with deterministic merge and provenance (MC-12; C035-C036).

Overlay document ``PK_APP_OVERLAY/1``::

    {"format": "PK_APP_OVERLAY/1", "id": "prod-eu-replicas", "version": 3,
     "scope": {"tenant": "acme", "environment": "prod", "site": "eu-west-1"},   # site optional
     "base_digest": "<canonical sha256 of the base manifest>",
     "author": "alice@acme", "approval": {"approver": "bob@acme", "ref": "CHG-1234"},
     "set":   [{"path": "components[api].properties.replicas", "value": 6}],
     "unset": ["components[api].properties.debug"]}

Rules (all fail closed, before activation):

* only ``properties`` subtrees of declared components/providers and of traits
  (``traits[<type>@<component>]``) are writable; names, schema, links and the
  set of traits are immutable identity (``overlay.immutable``);
* scope must equal the target (tenant, environment[, site]) (``overlay.scope``);
* ``base_digest`` must equal the base being overlaid (``overlay.stale_parent``);
* precedence is structural: environment overlays (level 1) then site overlays
  (level 2); two overlays at the same level touching the same path conflict
  (``overlay.conflict``) — never resolved by list/file order;
* the effective manifest is re-validated in full (so a secret introduced by an
  overlay is refused) and identified by its canonical digest;
* author and approver must differ.

The same inputs always produce the same effective digest (tests replay this).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .errors import Inv64Error
from .manifest import canonical, validate_issues

OVERLAY_FORMAT = "PK_APP_OVERLAY/1"
MAX_OPS = 1_000
_SEG = re.compile(r"^(components|providers|traits)\[([A-Za-z0-9._@-]{1,260})\]\.properties((?:\.[A-Za-z0-9_-]{1,64}){1,16})$")


@dataclass(frozen=True)
class Scope:
    tenant: str
    environment: str
    site: str | None = None


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_path(path: str) -> tuple[str, str, tuple[str, ...]]:
    m = _SEG.fullmatch(path) if isinstance(path, str) else None
    if not m:
        raise Inv64Error("overlay.immutable", details={"path": str(path)[:200],
                                                        "reason": "only <section>[<name>].properties.* is writable"})
    return m.group(1), m.group(2), tuple(m.group(3).split(".")[1:])


def _locate(manifest: dict, section: str, name: str) -> dict:
    for item in manifest.get(section, []):
        if section == "traits":
            if f"{item.get('type')}@{item.get('component')}" == name:
                return item
        elif item.get("name") == name:
            return item
    raise Inv64Error("overlay.invalid", details={"reason": "target not declared in base", "target": f"{section}[{name}]"})


def check_overlay(doc: Any) -> dict:
    if not isinstance(doc, dict) or doc.get("format") != OVERLAY_FORMAT:
        raise Inv64Error("overlay.invalid", details={"reason": "format"})
    for k, t in (("id", str), ("version", int), ("scope", dict), ("base_digest", str), ("author", str),
                 ("approval", dict)):
        if not isinstance(doc.get(k), t) or (t is str and not doc[k]):
            raise Inv64Error("overlay.invalid", details={"field": k})
    sc = doc["scope"]
    if not isinstance(sc.get("tenant"), str) or not isinstance(sc.get("environment"), str):
        raise Inv64Error("overlay.invalid", details={"field": "scope"})
    appr = doc["approval"].get("approver")
    if not isinstance(appr, str) or not appr or appr == doc["author"]:
        raise Inv64Error("overlay.invalid", details={"field": "approval", "reason": "approver required and must differ from author"})
    if not isinstance(doc.get("set", []), list) or not isinstance(doc.get("unset", []), list):
        raise Inv64Error("overlay.invalid", details={"reason": "set/unset must be lists"})
    ops = list(doc.get("set", [])) + list(doc.get("unset", []))
    if len(ops) > MAX_OPS or not ops:
        raise Inv64Error("overlay.invalid", details={"reason": "1..1000 operations required"})
    for op in doc.get("set", []):
        if not isinstance(op, dict) or set(op) != {"path", "value"}:
            raise Inv64Error("overlay.invalid", details={"reason": "set entries are {path, value}"})
        parse_path(op["path"])
    for p in doc.get("unset", []):
        parse_path(p)
    return doc


def _level(doc: dict) -> int:
    return 2 if doc["scope"].get("site") else 1


def merge(base: dict, overlays: Iterable[dict], target: Scope, *,
          authorize: "Callable[[str, dict], bool] | None" = None) -> dict:
    """Return the effective-configuration record; raises on any rule violation.

    ``authorize(author, overlay)`` is the caller's hook into :class:`authz.Authorizer`
    (capability ``config.overlay.write`` on the overlay scope); an overlay whose
    author is not authorized is refused with ``authz.denied`` before merging.
    """
    issues = validate_issues(base)
    if issues:
        raise Inv64Error("manifest.invalid", details={"stage": "base", "issues": len(issues)})
    base_digest = canonical(base)
    docs = [check_overlay(o) for o in overlays]
    seen_ids = set()
    for d in docs:
        if d["id"] in seen_ids:
            raise Inv64Error("overlay.conflict", details={"reason": "duplicate overlay id", "id": d["id"]})
        seen_ids.add(d["id"])
        sc = d["scope"]
        if sc["tenant"] != target.tenant or sc["environment"] != target.environment or \
                (sc.get("site") is not None and sc.get("site") != target.site):
            raise Inv64Error("overlay.scope", details={"id": d["id"]})
        if d["base_digest"] != base_digest:
            raise Inv64Error("overlay.stale_parent", details={"id": d["id"]})
        if authorize is not None and not authorize(d["author"], d):
            raise Inv64Error("authz.denied", details={"id": d["id"], "capability": "config.overlay.write"})
    # conflict detection per level
    for level in (1, 2):
        touched: dict[str, str] = {}
        for d in (x for x in docs if _level(x) == level):
            paths = [op["path"] for op in d.get("set", [])] + list(d.get("unset", []))
            for p in paths:
                # a path conflicts with itself and with any ancestor/descendant
                for q, owner in touched.items():
                    if owner != d["id"] and (p == q or p.startswith(q + ".") or q.startswith(p + ".")):
                        raise Inv64Error("overlay.conflict", details={"path": p, "overlays": sorted([owner, d["id"]])})
                touched[p] = d["id"]
    eff = copy.deepcopy(base)
    applied = []
    for d in sorted(docs, key=lambda x: (_level(x), x["id"])):
        for op in d.get("set", []):
            section, name, keys = parse_path(op["path"])
            node = _locate(eff, section, name).setdefault("properties", {})
            if not isinstance(node, dict):
                raise Inv64Error("overlay.invalid", details={"path": op["path"]})
            for k in keys[:-1]:
                node = node.setdefault(k, {})
                if not isinstance(node, dict):
                    raise Inv64Error("overlay.invalid", details={"path": op["path"]})
            node[keys[-1]] = copy.deepcopy(op["value"])
        for p in d.get("unset", []):
            section, name, keys = parse_path(p)
            node = _locate(eff, section, name).get("properties", {})
            for k in keys[:-1]:
                node = node.get(k, {}) if isinstance(node, dict) else {}
            if isinstance(node, dict):
                node.pop(keys[-1], None)
        applied.append({"id": d["id"], "version": d["version"], "level": _level(d), "digest": _digest(d),
                        "author": d["author"], "approver": d["approval"]["approver"],
                        "approval_ref": d["approval"].get("ref")})
    issues = validate_issues(eff)
    if issues:
        raise Inv64Error("manifest.invalid", details={"stage": "effective",
                                                      "codes": sorted({i.code for i in issues})})
    return {
        "format": "PK_APP_EFFECTIVE_CONFIG/1",
        "scope": {"tenant": target.tenant, "environment": target.environment, "site": target.site},
        "base_digest": base_digest,
        "overlays": applied,
        "manifest": eff,
        "digest": canonical(eff),
    }


def diff(before: Any, after: Any, path: str = "") -> list[dict]:
    """Dry-run diff: list of {path, op, before, after} (values redacted by callers before export)."""
    out: list[dict] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for k in sorted(set(before) | set(after)):
            p = f"{path}.{k}" if path else k
            if k not in after:
                out.append({"path": p, "op": "remove", "before": before[k], "after": None})
            elif k not in before:
                out.append({"path": p, "op": "add", "before": None, "after": after[k]})
            else:
                out.extend(diff(before[k], after[k], p))
    elif isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        for i, (a, b) in enumerate(zip(before, after)):
            out.extend(diff(a, b, f"{path}[{i}]"))
    elif before != after:
        out.append({"path": path, "op": "replace", "before": before, "after": after})
    return out
