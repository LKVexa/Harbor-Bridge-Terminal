"""Schema-defined machine-readable contracts (INV11-MC-09).

PK_INTERFACE/1       a resolved WIT package export (interfaces, worlds, types)
PK_INTERFACE_DIFF/1  a classification report
Evolution rule: a schema id is immutable; additive optional properties bump
the minor revision in `$id` (…/1.1), anything else mints /2.  Unknown
properties are rejected (additionalProperties: false) so drift fails closed.
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import NORMALIZATION_VERSION, POLICY_VERSION, TOOL_VERSION
from .compat import POLICY
from .limits import DEFAULT_LIMITS, Limits
from .normalize import canonical_json, package_fingerprint
from .resolve import Resolved

FP = {"type": "string", "pattern": r"^sha256:[0-9a-f]{64}$"}
TYPE_FORM: dict[str, Any] = {"type": ["string", "object", "null"]}

PK_INTERFACE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:inv11:schema:PK_INTERFACE/1",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema", "tool_version", "normalization", "root_package", "packages", "interfaces", "worlds", "types", "fingerprint"],
    "properties": {
        "schema": {"const": "PK_INTERFACE/1"},
        "tool_version": {"type": "string"},
        "normalization": {"const": NORMALIZATION_VERSION},
        "root_package": {"type": ["string", "null"]},
        "packages": {"type": "object"},
        "interfaces": {"type": "object", "additionalProperties": {
            "type": "object", "required": ["id", "package", "name", "functions", "types", "uses"],
            "properties": {"id": {"type": "string"}, "package": {"type": "string"}, "name": {"type": "string"},
                           "functions": {"type": "object"}, "types": {"type": "array", "items": {"type": "string"}},
                           "uses": {"type": "array", "items": {"type": "string"}}}}},
        "worlds": {"type": "object"},
        "types": {"type": "object", "additionalProperties": {
            "type": "object", "required": ["kind"],
            "properties": {"kind": {"enum": ["alias", "record", "variant", "enum", "flags", "resource"]}}}},
        "gates": {"type": "object"},
        "fingerprint": FP,
    },
}

PK_INTERFACE_DIFF_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:inv11:schema:PK_INTERFACE_DIFF/1",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema", "policy", "subject", "from", "to", "class", "linkable", "changes", "reasons", "fingerprints"],
    "properties": {
        "schema": {"const": "PK_INTERFACE_DIFF/1"},
        "policy": {"const": POLICY_VERSION},
        "subject": {"type": "string"},
        "from": {"type": ["string", "null"]},
        "to": {"type": ["string", "null"]},
        "class": {"enum": ["additive", "compatible", "breaking"]},
        "linkable": {"type": "boolean"},
        "changes": {"type": "array", "minItems": 1, "items": {
            "type": "object", "additionalProperties": False, "required": ["path", "code", "class", "detail"],
            "properties": {"path": {"type": "string"}, "code": {"enum": sorted(POLICY)},
                           "class": {"enum": ["additive", "compatible", "breaking"]}, "detail": {"type": "string"}}}},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "fingerprints": {"type": "object", "additionalProperties": False, "required": ["from", "to"],
                         "properties": {"from": FP, "to": FP}},
    },
}

SCHEMAS = {"PK_INTERFACE/1": PK_INTERFACE_SCHEMA, "PK_INTERFACE_DIFF/1": PK_INTERFACE_DIFF_SCHEMA}

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "boolean":
        return isinstance(v, bool)
    return isinstance(v, _TYPES[t]) and not isinstance(v, bool)


def validate(doc: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Minimal draft-2020-12 subset validator (stdlib; no network, no $ref)."""
    errs: list[str] = []
    if "const" in schema and doc != schema["const"]:
        errs.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and doc not in schema["enum"]:
        errs.append(f"{path}: {doc!r} not in enum")
    if "type" in schema:
        ts = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is(doc, t) for t in ts):
            return errs + [f"{path}: expected {ts}, got {type(doc).__name__}"]
    if "pattern" in schema and isinstance(doc, str) and not re.search(schema["pattern"], doc):
        errs.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(doc, dict):
        for r in schema.get("required", []):
            if r not in doc:
                errs.append(f"{path}: missing required {r!r}")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for k in sorted(doc):
            if k in props:
                errs.extend(validate(doc[k], props[k], f"{path}.{k}"))
            elif extra is False:
                errs.append(f"{path}: unexpected property {k!r}")
            elif isinstance(extra, dict):
                errs.extend(validate(doc[k], extra, f"{path}.{k}"))
    if isinstance(doc, list):
        if len(doc) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, x in enumerate(doc):
                errs.extend(validate(x, schema["items"], f"{path}[{i}]"))
    return errs


def export_interface(res: Resolved) -> dict[str, Any]:
    if not res.ok:
        raise ValueError("refusing to export a package that failed resolution")
    doc = {"schema": "PK_INTERFACE/1", "tool_version": TOOL_VERSION, "normalization": NORMALIZATION_VERSION,
           "root_package": res.root_package, "packages": res.packages,
           "interfaces": {k: {kk: vv for kk, vv in v.items() if kk != "scope"} for k, v in res.interfaces.items()},
           "worlds": res.worlds, "types": res.types, "gates": res.gates,
           "fingerprint": package_fingerprint(res)}
    out: dict[str, Any] = json.loads(canonical_json(doc))
    return out


def load_document(text: str | bytes, schema_id: str, limits: Limits = DEFAULT_LIMITS) -> dict[str, Any]:
    """Parse and validate an untrusted contract document; fail closed."""
    raw = text.encode() if isinstance(text, str) else text
    limits.check("json_bytes", len(raw))

    def no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate JSON object key")
        return dict(pairs)

    def no_const(x: str) -> Any:
        raise ValueError(f"non-finite number {x}")

    doc: dict[str, Any] = json.loads(raw.decode("utf-8"), object_pairs_hook=no_dupes, parse_constant=no_const)
    errs = validate(doc, SCHEMAS[schema_id])
    if errs:
        raise ValueError(f"{schema_id} validation failed: {errs[:10]}")
    return doc
