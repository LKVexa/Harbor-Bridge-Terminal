"""Components 15 + 24 - compatibility policy, N/N-1 interoperability and
protocol feature negotiation.

Policy (COMPAT_POLICY):
* Package versions are SemVer MAJOR.MINOR.PATCH.  A peer pair interoperates
  iff same MAJOR and |minor difference| <= 1 (N/N-1).  Patch is ignored.
* Each release declares the wire majors and optional features it speaks
  (RELEASES).  Negotiation = highest common wire major per interface +
  intersection of features; a feature marked required by either side and
  absent on the other fails with INV08.COMPAT.MISSING_FEATURE.
* Deprecation: announced in minor X, may be removed no earlier than X+2
  (two-minor window) and only if listed in DEPRECATIONS.
* Schema evolution (``schema_change_ok``): add optional property = minor;
  add required property, remove property, change type/const/enum narrowing,
  or tighten additionalProperties = breaking (needs new wire major).
* Upgrade sequencing: controller first, then nodes; at every step every
  node must be N/N-1 with the controller; rollback only to N-1 of the
  current controller.  ``check_rollout`` validates a proposed step list.
* Unknown/unsupported peers are rejected (fail closed) with
  INV08.COMPAT.UNSUPPORTED_PEER, never silently downgraded.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .errors_catalog import error

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

# release -> {"wire": {iface: (majors)}, "features": set, "required": set}
RELEASES: dict[str, dict] = {
    "4.0.0": {"wire": {"PK_DYN_LEASE": (1,), "PK_DYN_SCALE": (1,), "PK_DYN_COST": (1,)},
              "features": frozenset(), "required": frozenset()},
    "4.1.0": {"wire": {"PK_DYN_LEASE": (1,), "PK_DYN_SCALE": (1,), "PK_DYN_COST": (1,)},
              "features": frozenset({"lease.epoch"}), "required": frozenset()},
    "4.2.0": {"wire": {"PK_DYN_LEASE": (1,), "PK_DYN_SCALE": (1,), "PK_DYN_COST": (1,)},
              "features": frozenset({"lease.epoch", "scale.elapsed_hours", "cost.tenant"}),
              "required": frozenset()},
}
CURRENT = "4.2.0"
DEPRECATIONS = {
    # item: (announced_in, earliest_removal)
    "scale.one_tick_equals_one_hour": ("4.2.0", "4.4.0"),
}
COMPAT_POLICY = {"version": "PK_DYN_COMPAT/1", "window": "N/N-1 minor, same major",
                 "deprecation_minors": 2, "upgrade_order": ["controller", "nodes"]}


def parse(v: str) -> tuple[int, int, int]:
    m = _SEMVER.match(v or "")
    if not m:
        raise error("INV08.COMPAT.UNSUPPORTED_PEER", f"invalid version {v!r}")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def compatible(a: str, b: str) -> bool:
    (ma, na, _), (mb, nb, _) = parse(a), parse(b)
    return ma == mb and abs(na - nb) <= 1


def matrix(versions: list[str] | None = None) -> dict[str, dict[str, bool]]:
    vs = versions or sorted(RELEASES, key=parse)
    return {a: {b: compatible(a, b) for b in vs} for a in vs}


def _release(v: str) -> dict:
    parse(v)
    key = ".".join(map(str, parse(v)[:2])) + ".0"
    if key not in RELEASES:
        raise error("INV08.COMPAT.UNSUPPORTED_PEER", f"unknown release line {v}")
    return RELEASES[key]


@dataclass(frozen=True)
class Offer:
    version: str
    wire: dict
    features: frozenset
    required: frozenset = frozenset()

    @classmethod
    def for_release(cls, v: str) -> "Offer":
        r = _release(v)
        return cls(v, r["wire"], r["features"], r["required"])


def negotiate(local: Offer, peer: Offer) -> dict:
    if not compatible(local.version, peer.version):
        raise error("INV08.COMPAT.UNSUPPORTED_PEER",
                    f"{peer.version} is outside the N/N-1 window of {local.version}",
                    details={"local": local.version, "peer": peer.version})
    wire = {}
    for iface, majors in sorted(local.wire.items()):
        common = set(majors) & set(peer.wire.get(iface, ()))
        if not common:
            raise error("INV08.COMPAT.NO_COMMON_VERSION", iface)
        wire[iface] = f"{iface}/{max(common)}"
    missing = (local.required - peer.features) | (peer.required - local.features)
    if missing:
        raise error("INV08.COMPAT.MISSING_FEATURE", ",".join(sorted(missing)))
    return {"wire": wire, "features": sorted(local.features & peer.features),
            "versions": sorted([local.version, peer.version], key=parse)}


def deprecation_status(item: str, version: str) -> str:
    ann, rem = DEPRECATIONS[item]
    if parse(version) >= parse(rem):
        return "removable"
    if parse(version) >= parse(ann):
        return "deprecated"
    return "active"


def deprecation_windows_ok() -> list[str]:
    bad = []
    for item, (ann, rem) in DEPRECATIONS.items():
        a, r = parse(ann), parse(rem)
        if r[0] == a[0] and r[1] - a[1] < COMPAT_POLICY["deprecation_minors"]:
            bad.append(f"{item}: removal {rem} < announce {ann} + 2 minors")
    return bad


def schema_change_ok(old: dict, new: dict, path: str = "$") -> list[str]:
    """Return breaking differences between two schemas of the same wire major."""
    out = []
    for k in ("type", "const"):
        if old.get(k) != new.get(k):
            out.append(f"{path}: {k} changed")
    if "enum" in old and not set(old["enum"]) <= set(new.get("enum", old["enum"])):
        out.append(f"{path}: enum narrowed")
    for k in ("minimum", "minLength"):
        if k in new and new[k] > old.get(k, float("-inf")):
            out.append(f"{path}: {k} tightened")
    for k in ("maximum", "maxLength", "maxItems"):
        if k in new and new[k] < old.get(k, float("inf")):
            out.append(f"{path}: {k} tightened")
    if old.get("additionalProperties", True) and new.get("additionalProperties", True) is False:
        out.append(f"{path}: additionalProperties tightened")
    new_req = set(new.get("required", [])) - set(old.get("required", []))
    if new_req:
        out.append(f"{path}: new required {sorted(new_req)}")
    op, np_ = old.get("properties", {}), new.get("properties", {})
    for k in op:
        if k not in np_:
            out.append(f"{path}.{k}: removed")
        else:
            out += schema_change_ok(op[k], np_[k], f"{path}.{k}")
    if "items" in old:
        out += schema_change_ok(old["items"], new.get("items", {}), f"{path}[]")
    return out


def check_rollout(controller: str, nodes: dict[str, str], steps: list[tuple[str, str]]) -> list[dict]:
    """Simulate steps [(target, version)] where target is 'controller' or a node id.
    Every intermediate state must keep every node N/N-1 with the controller and
    negotiate successfully.  Returns the per-step negotiation log."""
    nodes = dict(nodes)
    log = []
    for i, (who, ver) in enumerate(steps):
        _release(ver)
        if who == "controller":
            if parse(ver) < parse(controller) and not compatible(ver, controller):
                raise error("INV08.COMPAT.BAD_SEQUENCE", f"step {i}: rollback beyond N-1")
            controller = ver
        elif who in nodes:
            if parse(ver) > parse(controller):
                raise error("INV08.COMPAT.BAD_SEQUENCE", f"step {i}: node {who} ahead of controller")
            nodes[who] = ver
        else:
            raise error("INV08.COMPAT.BAD_SEQUENCE", f"step {i}: unknown target {who}")
        for nid, nv in sorted(nodes.items()):
            if not compatible(controller, nv):
                raise error("INV08.COMPAT.BAD_SEQUENCE",
                            f"step {i}: {nid}@{nv} incompatible with controller@{controller}")
            negotiate(Offer.for_release(controller), Offer.for_release(nv))
        log.append({"step": i, "controller": controller, "nodes": dict(sorted(nodes.items()))})
    return log


def read_tolerant(msg: dict, supported_minor: int) -> dict:
    """N-1 reader: accept higher schema_minor of a supported major, dropping
    ``ext`` (the only place newer minors may add data)."""
    out = {k: v for k, v in msg.items() if k != "ext"}
    out["_downlevel"] = msg.get("schema_minor", 0) > supported_minor
    return out
