"""MC-11 - Schema validation and compatibility checking (stdlib only).

Authoritative mechanism: JSON Schema 2020-12 documents under ``schemas/``.
This validator implements the keyword subset those schemas use (type, const,
enum, required, properties, additionalProperties, items, minimum, maximum,
maxLength, pattern, oneOf).  Unknown fields are accepted (additive evolution);
unknown enum values are rejected by v1 readers - a new enum member therefore
requires a minor version with negotiation (``negotiate``).

Compatibility rules enforced by ``breaking_changes`` against the frozen v1
copies in ``schemas/v1_frozen``: removing a property, adding a required field,
narrowing a type, removing an enum member, changing a const, or tightening a
bound are breaking and require a new major interface version.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1] / "schemas"
SUPPORTED = {"PK_ASYNC_BACKEND": (1, 0), "PK_ASYNC_ARM": (1, 0), "PK_ASYNC_REAP": (1, 0),
             "PK_ASYNC_ERROR": (1, 0)}
_T = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def load(name: str, frozen: bool = False) -> dict:
    d = ROOT / "v1_frozen" if frozen else ROOT
    return json.loads((d / f"{name}.schema.json").read_text())


def _is(t: str, v: Any) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _T[t])


def validate(doc: Any, schema: dict, path: str = "$") -> list[str]:
    errs: list[str] = []
    if "const" in schema and doc != schema["const"]:
        errs.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and doc not in schema["enum"]:
        errs.append(f"{path}: {doc!r} not in enum")
    if "type" in schema:
        ts = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is(t, doc) for t in ts):
            return errs + [f"{path}: expected {ts}"]
    if "oneOf" in schema:
        ok = [s for s in schema["oneOf"] if not validate(doc, s, path)]
        if len(ok) != 1:
            errs.append(f"{path}: oneOf matched {len(ok)}")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if "minimum" in schema and doc < schema["minimum"]:
            errs.append(f"{path}: {doc} < {schema['minimum']}")
        if "maximum" in schema and doc > schema["maximum"]:
            errs.append(f"{path}: {doc} > {schema['maximum']}")
    if isinstance(doc, str):
        if "maxLength" in schema and len(doc) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], doc):
            errs.append(f"{path}: pattern mismatch")
    if isinstance(doc, dict):
        for r in schema.get("required", []):
            if r not in doc:
                errs.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        for k, v in doc.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected {k}")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs += validate(v, schema["additionalProperties"], f"{path}.{k}")
    if isinstance(doc, list) and "items" in schema:
        for i, v in enumerate(doc[:10000]):
            errs += validate(v, schema["items"], f"{path}[{i}]")
    return errs


def breaking_changes(old: dict, new: dict, path: str = "$") -> list[str]:
    out = []
    if old.get("const") != new.get("const") and "const" in old:
        out.append(f"{path}: const changed")
    if "enum" in old:
        missing = [e for e in old["enum"] if e not in new.get("enum", old["enum"])]
        if missing:
            out.append(f"{path}: enum members removed {missing}")
    if "type" in old:
        o = set(old["type"] if isinstance(old["type"], list) else [old["type"]])
        n = set(new.get("type", list(o)) if isinstance(new.get("type"), list) else [new.get("type", next(iter(o)))])
        if not o <= n:
            out.append(f"{path}: type narrowed {sorted(o)} -> {sorted(n)}")
    for b, cmp in (("minimum", lambda a, b: b > a), ("maximum", lambda a, b: b < a),
                   ("maxLength", lambda a, b: b < a)):
        if b in old and b in new and cmp(old[b], new[b]):
            out.append(f"{path}: {b} tightened")
    added_req = set(new.get("required", [])) - set(old.get("required", []))
    if added_req:
        out.append(f"{path}: new required fields {sorted(added_req)}")
    for k, sub in old.get("properties", {}).items():
        if k not in new.get("properties", {}):
            out.append(f"{path}.{k}: property removed")
        else:
            out += breaking_changes(sub, new["properties"][k], f"{path}.{k}")
    if old.get("additionalProperties", True) is not False and new.get("additionalProperties", True) is False:
        out.append(f"{path}: additionalProperties closed")
    return out


def check_all_compat() -> dict[str, list[str]]:
    return {n: breaking_changes(load(n, True), load(n)) for n in
            ("PK_ASYNC_BACKEND_1", "PK_ASYNC_ARM_1", "PK_ASYNC_REAP_1", "PK_ASYNC_ERROR_1")}


def negotiate(interface: str, peer_versions: list[tuple[int, int]]) -> tuple[int, int] | None:
    """Pick the highest mutually supported version: same major, min(minor)."""
    mine = SUPPORTED.get(interface)
    if mine is None:
        return None
    same = [v for v in peer_versions if v[0] == mine[0]]
    if not same:
        return None
    return (mine[0], min(mine[1], max(v[1] for v in same)))


def to_wire(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def from_wire(b: bytes, schema_name: str, max_bytes: int = 1 << 20) -> dict:
    if len(b) > max_bytes:
        raise ValueError("payload too large")
    doc = json.loads(b.decode("utf-8"))
    errs = validate(doc, load(schema_name))
    if errs:
        raise ValueError("; ".join(errs[:5]))
    return doc
