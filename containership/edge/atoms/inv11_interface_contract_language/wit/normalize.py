"""Canonical structural normalization and deterministic fingerprints (INV11-MC-06/16).

Rules (NORMALIZATION_VERSION INV11-NORM/1):
  * spans, docs, comments, file names and load order are excluded;
  * semantically ordered sequences (params, record fields, variant/enum/flags
    cases, tuple items) keep source order; unordered maps (functions, types,
    world imports/exports, resource methods) are key-sorted;
  * JSON is emitted with sorted keys, no whitespace, UTF-8, no NaN;
  * `strip_versions=True` rewrites ids to version-less form so two releases of
    one package can be compared structurally.
Fingerprint = sha256("INV11-NORM/1\\n" + canonical_json(form)).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from . import NORMALIZATION_VERSION
from .resolve import Resolved, unversioned


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _strip(v: Any) -> Any:
    if isinstance(v, str):
        return unversioned(v) if (":" in v and "@" in v) else v
    if isinstance(v, list):
        return [_strip(x) for x in v]
    if isinstance(v, dict):
        return {(_strip(k) if isinstance(k, str) else k): _strip(x) for k, x in v.items()}
    return v


def type_closure(res: Resolved, roots: list[Any]) -> list[str]:
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            for k, x in v.items():
                if k in ("ref", "own", "borrow") and isinstance(x, str) and x in res.types and x not in seen:
                    seen.add(x)
                    stack.append(res.types[x])
                else:
                    stack.append(x)
        elif isinstance(v, list):
            stack.extend(v)
    return sorted(seen)


def interface_form(res: Resolved, iid: str, strip_versions: bool = False) -> dict[str, Any]:
    i = res.interfaces[iid]
    own = {k: res.types[v] for k, v in i["scope"].items() if v in res.types and v.startswith(iid + "#")}
    closure = type_closure(res, [i["functions"], list(own.values())])
    form = {"id": iid, "functions": i["functions"], "types": own,
            "closure": {k: res.types[k] for k in closure}}
    return _strip(form) if strip_versions else form


def package_form(res: Resolved, strip_versions: bool = False, include_deps: bool = False) -> dict[str, Any]:
    pkgs = {k: v for k, v in res.packages.items() if include_deps or not v["dependency"]}
    ifaces = {k: {"functions": v["functions"], "uses": v["uses"],
                  "types": {t: res.types[v["scope"][t]] for t in v["types"]}}
              for k, v in res.interfaces.items() if v["package"] in pkgs}
    worlds = {k: {"imports": v["imports"], "exports": v["exports"]} for k, v in res.worlds.items() if v["package"] in pkgs}
    form = {"normalization": NORMALIZATION_VERSION,
            "packages": sorted(pkgs), "interfaces": ifaces, "worlds": worlds,
            "types": {k: v for k, v in res.types.items() if any(k.startswith(p.split("@")[0]) for p in pkgs)}}
    return _strip(form) if strip_versions else form


def fingerprint(form: Any) -> str:
    return "sha256:" + hashlib.sha256((NORMALIZATION_VERSION + "\n" + canonical_json(form)).encode("utf-8")).hexdigest()


def interface_fingerprint(res: Resolved, iid: str, strip_versions: bool = True) -> str:
    key = f"i:{iid}:{strip_versions}"
    if key not in res.cache:  # a Resolved is immutable once resolution returns
        res.cache[key] = fingerprint(interface_form(res, iid, strip_versions))
    return res.cache[key]


def package_fingerprint(res: Resolved, strip_versions: bool = False) -> str:
    key = f"p:{strip_versions}"
    if key not in res.cache:
        res.cache[key] = fingerprint(package_form(res, strip_versions))
    return res.cache[key]
