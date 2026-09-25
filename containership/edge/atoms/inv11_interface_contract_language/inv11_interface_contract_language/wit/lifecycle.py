"""P3 lifecycle controls (INV11-MC-33..37): semver recommendation, deprecation
lifecycle, waiver registry, adapter planning, human-readable diff rendering."""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Any

from .compat import ADDITIVE, BREAKING, COMPATIBLE, POLICY
from .resolve import Resolved, unversioned

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


# ---- MC-33 semantic-version recommendation ---------------------------------
def recommend_version(current: str, diff: dict[str, Any]) -> dict[str, Any]:
    """Recommend the next version from the *structural* class.  Advisory only:
    the recommendation never feeds back into compatibility (which is decided
    by structure).  0.x follows Cargo/WIT convention: breaking bumps minor."""
    m = _SEMVER.match(current or "")
    if not m:
        return {"current": current, "recommended": None, "status": "BLOCKED", "reason": "current version is not semver"}
    major, minor, patch = (int(x) for x in m.group(1, 2, 3))
    cls = diff["class"]
    if cls == BREAKING:
        nxt, bump = ((major + 1, 0, 0), "major") if major > 0 else ((0, minor + 1, 0), "minor (0.x breaking)")
    elif cls == ADDITIVE:
        nxt, bump = ((major, minor + 1, 0), "minor") if major > 0 else ((0, minor, patch + 1), "patch (0.x additive)")
    else:
        nxt, bump = (major, minor, patch + 1), "patch"
    declared = diff.get("to", "") or ""
    declared_v = declared.rsplit("@", 1)[1] if "@" in declared else None
    under = False
    dmatch = _SEMVER.match(declared_v) if declared_v else None
    if dmatch:
        dm = tuple(int(x) for x in dmatch.group(1, 2, 3))
        under = dm < nxt
    return {"current": current, "class": cls, "bump": bump, "recommended": "{}.{}.{}".format(*nxt),
            "declared": declared_v, "declared_under_bumped": under, "advisory_only": True}


# ---- MC-34 deprecation lifecycle -------------------------------------------
@dataclass
class Deprecation:
    path: str
    since: str  # version
    removal_not_before: str  # ISO date
    replacement: str = ""
    consumers: list[str] = field(default_factory=list)


class DeprecationManager:
    """Deprecations come from `@deprecated(version = …)` gates plus a registry
    carrying grace periods.  Removal is gated: a removal is refused before the
    grace deadline or while registered consumers remain."""

    def __init__(self, entries: list[Deprecation], min_grace_days: int = 90) -> None:
        self.entries = {unversioned(e.path): e for e in entries}
        self.min_grace = min_grace_days

    @staticmethod
    def from_gates(res: Resolved, deadline: str) -> list[Deprecation]:
        return [Deprecation(unversioned(k), g["value"], deadline)
                for k, gs in sorted(res.gates.items()) for g in gs if g["kind"] == "deprecated"]

    def validate(self, today: _dt.date) -> list[str]:
        errs = []
        for p, e in sorted(self.entries.items()):
            try:
                _dt.date.fromisoformat(e.removal_not_before)
            except ValueError:
                errs.append(f"{p}: removal date {e.removal_not_before!r} is not ISO-8601")
                continue
            if not _SEMVER.match(e.since):
                errs.append(f"{p}: since {e.since!r} is not semver")
        return errs

    def removal_gate(self, diff: dict[str, Any], today: _dt.date) -> dict[str, Any]:
        verdicts = []
        for c in diff["changes"]:
            if not c["code"].endswith("removed"):
                continue
            e = self.entries.get(c["path"])
            if e is None:
                verdicts.append({"path": c["path"], "verdict": "REFUSED", "reason": "removed without prior deprecation"})
            elif today < _dt.date.fromisoformat(e.removal_not_before):
                verdicts.append({"path": c["path"], "verdict": "REFUSED", "reason": f"grace period runs to {e.removal_not_before}"})
            elif e.consumers:
                verdicts.append({"path": c["path"], "verdict": "REFUSED", "reason": f"live consumers: {sorted(e.consumers)}"})
            else:
                verdicts.append({"path": c["path"], "verdict": "ALLOWED", "reason": "deprecated, grace elapsed, no consumers"})
        ok = all(v["verdict"] == "ALLOWED" for v in verdicts)
        return {"gate": "deprecation-removal", "pass": ok, "verdicts": verdicts}


def discover_consumers(path: str, worlds: dict[str, Resolved]) -> list[str]:
    """Consumer discovery: which known worlds import the interface owning `path`."""
    iface = unversioned(path).split("#")[0].split(".")[0]
    out = []
    for name, res in sorted(worlds.items()):
        for w in res.worlds.values():
            if any(unversioned(k) == iface for k in w["imports"]):
                out.append(f"{name}:{unversioned(w['id'])}")
    return out


# ---- MC-35 waiver registry -------------------------------------------------
WAIVER_FIELDS = ("id", "owner", "rationale", "scope", "codes", "expires", "approved_by", "audit_ref")


def _in_scope(path: str, scope: str) -> bool:
    """Exact symbol, or a descendant separated by one of # . : ( — never a
    sibling that merely shares a prefix (a:b/i must not cover a:b/ix)."""
    if not scope:
        return False
    return path == scope or (path.startswith(scope) and path[len(scope)] in "#.:(")


class WaiverRegistry:
    """A waiver may downgrade a BREAKING change's gate effect, never its class.
    Expired, unscoped, unapproved or self-approved waivers are ignored (fail closed)."""

    def __init__(self, waivers: list[dict[str, Any]]) -> None:
        self.waivers = waivers

    def problems(self, w: dict[str, Any], today: _dt.date) -> list[str]:
        p = [f"missing {f}" for f in WAIVER_FIELDS if not w.get(f)]
        if w.get("expires"):
            try:
                if _dt.date.fromisoformat(w["expires"]) < today:
                    p.append("expired")
            except ValueError:
                p.append("bad expiry date")
        if w.get("approved_by") and w.get("approved_by") == w.get("owner"):
            p.append("self-approved")
        if w.get("scope") in ("*", "", None):
            p.append("unscoped")
        return p

    def apply(self, diff: dict[str, Any], today: _dt.date) -> dict[str, Any]:
        rows = []
        for c in diff["changes"]:
            if c["class"] != BREAKING:
                continue
            match = None
            for w in self.waivers:
                if _in_scope(c["path"], w.get("scope") or "") and c["code"] in (w.get("codes") or []) and not self.problems(w, today):
                    match = w["id"]
                    break
            rows.append({"path": c["path"], "code": c["code"], "waiver": match})
        unwaived = [r for r in rows if r["waiver"] is None]
        return {"class": diff["class"], "breaking": len(rows), "waived": len(rows) - len(unwaived),
                "gate": "PASS" if not unwaived else "FAIL", "rows": rows,
                "note": "waivers never change the structural class"}


# ---- MC-36 adapter/shim planning -------------------------------------------
def adapter_plan(diff: dict[str, Any]) -> dict[str, Any]:
    """Plan an adapter only where semantics are mechanically preserved.

    Supported: additive-only diffs (the new producer is a strict superset, so
    an old-view adapter just hides the additions) and compatible alias
    retargets.  Everything else is refused with the blocking change listed."""
    supported = {"func-added", "type-added", "interface-added", "world-added", "resource-method-added",
                 "world-export-added", "alias-retargeted-equal", "gate-changed", "version-only", "world-import-removed"}
    blockers = [c for c in diff["changes"] if c["code"] not in supported]
    if blockers:
        return {"adapter": None, "status": "REFUSED", "blockers": blockers}
    hidden = [c["path"] for c in diff["changes"] if c["code"].endswith("added")]
    return {"adapter": "projection", "status": "GENERATED", "hide": hidden,
            "maps_from": diff["to"], "maps_to": diff["from"]}


def render_adapter_wit(diff: dict[str, Any], new: Resolved, iface_id: str) -> str:
    """Emit the old-view WIT interface for an additive diff (the projection)."""
    plan = adapter_plan(diff)
    if plan["status"] != "GENERATED":
        raise ValueError("adapter refused: " + "; ".join(c["code"] + " " + c["path"] for c in plan["blockers"]))
    hidden = set(plan["hide"])
    i = new.interfaces[iface_id]
    base = unversioned(iface_id)
    keep = [f for f in sorted(i["functions"]) if f"{base}.{f}" not in hidden]
    return "\n".join([f"// adapter projection of {iface_id} onto {diff['from']}", f"interface {i['name']} {{"] +
                     [f"  // forwards {f}" for f in keep] + ["}"])


# ---- MC-37 human-readable diff renderer ------------------------------------
def render_diff(diff: dict[str, Any], expanded: bool = False) -> str:
    groups: dict[str, list[dict]] = {}
    for c in diff["changes"]:
        head = re.split(r"[#.:(]", c["path"].split("/", 1)[-1], maxsplit=1)[0]
        groups.setdefault(head, []).append(c)
    sym = {BREAKING: "!!", ADDITIVE: "++", COMPATIBLE: "=="}
    lines = [f"{diff['subject']}  {diff['from']} -> {diff['to']}",
             f"class: {diff['class'].upper()}   linkable: {'yes' if diff['linkable'] else 'NO'}",
             f"changes: {len(diff['changes'])} ({sum(c['class'] == BREAKING for c in diff['changes'])} breaking)"]
    for g in sorted(groups):
        lines.append(f"\n[{g}]")
        for c in groups[g]:
            lines.append(f"  {sym[c['class']]} {c['path']}  {c['code']}")
            if expanded:
                if c["detail"]:
                    lines.append(f"       detail: {c['detail']}")
                lines.append(f"       why: {POLICY[c['code']][1]}")
    return "\n".join(lines)
