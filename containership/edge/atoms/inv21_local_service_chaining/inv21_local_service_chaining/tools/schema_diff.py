"""Classify schema changes between two snapshots: returns breaking-change list.

Breaking (needs a new /N identifier): schema removed, required field added,
property removed, type narrowed/changed, const changed, enum value removed,
maxLength/maxItems/maximum lowered, minLength/minItems/minimum raised.
Usage: python -m inv21_local_service_chaining.tools.schema_diff OLD.json
"""
from __future__ import annotations

import json
import sys


def _walk(old, new, path, out):
    if not isinstance(old, dict) or not isinstance(new, dict):
        return
    if old.get("type") != new.get("type") and "type" in old:
        out.append(f"{path}: type {old.get('type')} -> {new.get('type')}")
    if "const" in old and old.get("const") != new.get("const"):
        out.append(f"{path}: const changed")
    if "enum" in old and set(old["enum"]) - set(new.get("enum", old["enum"])):
        out.append(f"{path}: enum values removed")
    for k in ("maxLength", "maxItems", "maximum"):
        if k in new and (k not in old or new[k] < old[k]):
            out.append(f"{path}: {k} lowered")
    for k in ("minLength", "minItems", "minimum"):
        if k in new and new[k] > old.get(k, float("-inf")):
            out.append(f"{path}: {k} raised")
    added = set(new.get("required", [])) - set(old.get("required", []))
    if added:
        out.append(f"{path}: required added {sorted(added)}")
    for p, sub in old.get("properties", {}).items():
        if p not in new.get("properties", {}):
            out.append(f"{path}.{p}: property removed")
        else:
            _walk(sub, new["properties"][p], f"{path}.{p}", out)
    for d, sub in old.get("$defs", {}).items():
        _walk(sub, new.get("$defs", {}).get(d, {}), f"{path}#{d}", out)
    if "items" in old:
        _walk(old["items"], new.get("items", {}), f"{path}[]", out)


def breaking(old: dict, new: dict) -> list:
    out: list = []
    for name, s in old.items():
        if name not in new:
            out.append(f"{name}: schema removed")
        else:
            _walk(s, new[name], name, out)
    return out


def main(argv=None) -> int:
    from ..schema import load_schema, schema_names
    old = json.load(open((argv or sys.argv[1:])[0]))
    b = breaking(old, {n: load_schema(n) for n in schema_names()})
    print(json.dumps({"breaking": b}, indent=2))
    return 1 if b else 0


if __name__ == "__main__":
    raise SystemExit(main())
