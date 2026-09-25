"""MC-015 ABI/version negotiation and MC-016 compatibility/evolution engine.

Negotiation
-----------
Each party sends an *offer*::

    {"canonical_abi": ["1"],
     "mapping_profile": ["inv12-mapping@2.0.0"],
     "interfaces": {"demo:shapes/api": ["1.2.0", "1.1.0"]},
     "bindings": {"rust": "1.0.0"}}            # informational, digest-bound

``negotiate(a, b, policy)`` picks, for each dimension, the highest value both
parties support.  Interface versions match by semver: same MAJOR, and the agreed
version is the highest one both offered.  Any dimension with no common value, or
a result below ``policy`` floors, fails closed with ``PK_INTEROP_VERSION``.
The agreement carries a transcript digest over both canonicalized offers, so a
man-in-the-middle downgrade (altering either offer) is detectable by comparing
digests out of band.

Evolution
---------
``compare(old, new)`` classifies every difference between two loaded
interfaces.  Classes: ``compatible`` (additive; MINOR bump), ``adapter`` (safe
only with an explicit adapter, e.g. a variant/enum/flags member appended — old
consumers would reject the new discriminant), ``breaking`` (MAJOR bump).
``required_bump`` and ``check_version_bump`` enforce that the declared version
change is at least as large as the evidence requires.
"""
from __future__ import annotations

import hashlib
import json
import re

from .errors import InteropError, VersionError
from .types import EnumT, FlagsT, Interface, RecordT, VariantT

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)\Z")


def parse_semver(v: str) -> tuple:
    m = _SEMVER.match(v) if type(v) is str else None
    if not m:
        raise VersionError(f"invalid semantic version {str(v)[:32]!r}")
    return tuple(int(x) for x in m.groups())


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _validate_offer(o):
    if type(o) is not dict or set(o) - {"canonical_abi", "mapping_profile", "interfaces", "bindings"}:
        raise VersionError("malformed offer")
    for k in ("canonical_abi", "mapping_profile"):
        if type(o.get(k)) is not list or not o[k] or not all(type(x) is str for x in o[k]):
            raise VersionError(f"offer.{k} must be a non-empty list of strings")
    if type(o.get("interfaces")) is not dict:
        raise VersionError("offer.interfaces must be a mapping")
    for name, vs in o["interfaces"].items():
        if type(vs) is not list or not vs:
            raise VersionError("interface versions must be a non-empty list", path=[name])
        for v in vs:
            parse_semver(v)


def negotiate(a: dict, b: dict, policy: dict | None = None) -> dict:
    _validate_offer(a)
    _validate_offer(b)
    policy = policy or {}
    abi = sorted(set(a["canonical_abi"]) & set(b["canonical_abi"]), key=lambda s: (len(s), s))
    if not abi:
        raise VersionError("no common canonical ABI version")
    prof = sorted(set(a["mapping_profile"]) & set(b["mapping_profile"]))
    if not prof:
        raise VersionError("no common mapping profile")
    agreed = {}
    for name in sorted(set(a["interfaces"]) & set(b["interfaces"])):
        common = set(a["interfaces"][name]) & set(b["interfaces"][name])
        if not common:
            raise VersionError("no common interface version", path=[name])
        best = max(common, key=parse_semver)
        floor = policy.get("min_interface", {}).get(name)
        if floor and parse_semver(best) < parse_semver(floor):
            raise VersionError("negotiated interface version is below policy floor", path=[name])
        agreed[name] = best
    missing = set(policy.get("required_interfaces", ())) - set(agreed)
    if missing:
        raise VersionError("required interface not offered by both parties",
                           path=[sorted(missing)[0]])
    min_abi = policy.get("min_canonical_abi")
    if min_abi and (len(abi[-1]), abi[-1]) < (len(min_abi), min_abi):
        raise VersionError("canonical ABI below policy floor")
    transcript = hashlib.sha256((_canon(a) + "\n" + _canon(b)).encode()).hexdigest()
    return {"canonical_abi": abi[-1], "mapping_profile": prof[-1], "interfaces": agreed,
            "transcript": "sha256:" + transcript}


# ------------------------------------------------------------------ evolution
def _members(t):
    if isinstance(t, RecordT):
        return [n for n, _ in t.fields]
    if isinstance(t, VariantT):
        return [n for n, _ in t.cases]
    if isinstance(t, EnumT):
        return list(t.cases)
    if isinstance(t, FlagsT):
        return list(t.names)
    return None


def compare(old: Interface, new: Interface) -> list:
    changes = []

    def add(cls, what, detail):
        changes.append({"class": cls, "item": what, "detail": detail})

    for n in sorted(set(old.types) | set(new.types)):
        if n not in new.types:
            add("breaking", f"type {n}", "removed")
            continue
        if n not in old.types:
            add("compatible", f"type {n}", "added")
            continue
        a, b = old.types[n], new.types[n]
        if a.canonical() == b.canonical():
            continue
        ma, mb = _members(a), _members(b)
        if (type(a) is type(b) and not isinstance(a, RecordT) and ma is not None
                and mb[:len(ma)] == ma and len(mb) > len(ma)
                and (not isinstance(a, VariantT) or b.cases[:len(a.cases)] == a.cases)):
            add("adapter", f"type {n}", f"{len(mb) - len(ma)} member(s) appended")
        else:
            add("breaking", f"type {n}", "structure changed")
    for r in sorted(old.resources - new.resources):
        add("breaking", f"resource {r}", "removed")
    for r in sorted(new.resources - old.resources):
        add("compatible", f"resource {r}", "added")
    for f in sorted(set(old.functions) | set(new.functions)):
        if f not in new.functions:
            add("breaking", f"func {f}", "removed")
        elif f not in old.functions:
            add("compatible", f"func {f}", "added")
        elif old.functions[f].canonical() != new.functions[f].canonical():
            add("breaking", f"func {f}", "signature changed")
    return changes


def required_bump(changes: list) -> str:
    classes = {c["class"] for c in changes}
    if "breaking" in classes or "adapter" in classes:
        return "major"
    if classes:
        return "minor"
    return "none"


def check_version_bump(old: Interface, new: Interface) -> dict:
    changes = compare(old, new)
    need = required_bump(changes)
    if old.version is None or new.version is None:
        raise VersionError("both interfaces must declare a version")
    o, n = parse_semver(old.version), parse_semver(new.version)
    have = ("major" if n[0] > o[0] else "minor" if n[:2] > o[:2] else
            "patch" if n > o else "none")
    order = ["none", "patch", "minor", "major"]
    if n < o:
        raise VersionError("new version is lower than old version")
    if order.index(have) < order.index(need):
        raise InteropError(f"changes require a {need} bump but version moved by {have}",
                           code="PK_INTEROP_INCOMPATIBLE")
    return {"required": need, "declared": have, "changes": changes}
