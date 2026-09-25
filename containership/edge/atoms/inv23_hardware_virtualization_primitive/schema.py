"""Normative schema loading and validation (MC-06).

JSON Schema (2020-12) files under ``schemas/`` are normative.  This module ships a
small stdlib validator covering exactly the keywords those schemas use, so runtime
validation has no third-party dependency; CI additionally cross-checks every fixture
with the reference ``jsonschema`` package.  Semantic invariants the schema language
cannot express live in ``semantic_*`` below.
"""

from __future__ import annotations

import json
import math
import re
from functools import cache
from pathlib import Path
from typing import Any, List

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
SCHEMA_FILES = {
    "PK_VIRT_PRIMITIVE/1": "PK_VIRT_PRIMITIVE-1.schema.json",
    "PK_VIRT_PRIMITIVE/2": "PK_VIRT_PRIMITIVE-2.schema.json",
    "PK_VIRT_CLAIM/1": "PK_VIRT_CLAIM-1.schema.json",
    "PK_VIRT_CLAIM/2": "PK_VIRT_CLAIM-2.schema.json",
    "PK_VIRT_OWNERSHIP/1": "PK_VIRT_OWNERSHIP-1.schema.json",
    "PK_GATE_RESULTS/1": "PK_GATE_RESULTS-1.schema.json",
}
CURRENT = {"probe": "PK_VIRT_PRIMITIVE/2", "claim": "PK_VIRT_CLAIM/2"}


class SchemaError(ValueError):
    def __init__(self, errors: List[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@cache
def load(schema_id: str) -> dict:
    if schema_id not in SCHEMA_FILES:
        raise SchemaError([f"unknown schema {schema_id!r}"])
    return json.loads((SCHEMA_DIR / SCHEMA_FILES[schema_id]).read_text(encoding="utf-8"))


def _type_ok(v: Any, t: str) -> bool:
    if t == "null":
        return v is None
    if t == "boolean":
        return type(v) is bool
    if t == "integer":
        return type(v) is int
    if t == "number":
        return type(v) in (int, float) and math.isfinite(v)
    if t == "string":
        return isinstance(v, str)
    if t == "object":
        return isinstance(v, dict)
    if t == "array":
        return isinstance(v, list)
    return False


def _validate(v: Any, s: dict, path: str, errs: List[str]) -> None:
    if "const" in s and not (v == s["const"] and type(v) is type(s["const"])):
        errs.append(f"{path}: expected const {s['const']!r}")
        return
    if "enum" in s and not any(v == e and type(v) is type(e) for e in s["enum"]):
        errs.append(f"{path}: {v!r} not in enum")
        return
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_type_ok(v, t) for t in ts):
            errs.append(f"{path}: expected {'/'.join(ts)}, got {type(v).__name__}")
            return
    if type(v) in (int, float):
        if "minimum" in s and v < s["minimum"]:
            errs.append(f"{path}: {v} < minimum {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            errs.append(f"{path}: {v} > maximum {s['maximum']}")
        if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
            errs.append(f"{path}: {v} <= exclusiveMinimum")
    if isinstance(v, str):
        if len(v) < s.get("minLength", 0):
            errs.append(f"{path}: shorter than {s['minLength']}")
        if "maxLength" in s and len(v) > s["maxLength"]:
            errs.append(f"{path}: longer than {s['maxLength']}")
        if "pattern" in s and not re.search(s["pattern"], v):
            errs.append(f"{path}: does not match pattern")
    if isinstance(v, list):
        if "maxItems" in s and len(v) > s["maxItems"]:
            errs.append(f"{path}: more than {s['maxItems']} items")
        if "items" in s:
            for i, x in enumerate(v):
                _validate(x, s["items"], f"{path}[{i}]", errs)
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                errs.append(f"{path}: missing required {k!r}")
        props = s.get("properties", {})
        for k, x in v.items():
            if k in props:
                _validate(x, props[k], f"{path}.{k}", errs)
            elif s.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property {k!r}")


def validate(doc: Any, schema_id: str | None = None) -> dict:
    if not isinstance(doc, dict):
        raise SchemaError(["document must be an object"])
    sid = schema_id or doc.get("schema")
    if not isinstance(sid, str) or sid not in SCHEMA_FILES:
        raise SchemaError([f"unknown or missing schema id {sid!r}"])
    if doc.get("schema") not in (None, sid) and "schema" in load(sid).get("required", []):
        raise SchemaError([f"schema version mismatch: {doc.get('schema')!r} != {sid!r}"])
    errs: List[str] = []
    _validate(doc, load(sid), "$", errs)
    errs += SEMANTIC.get(sid, lambda d: [])(doc) if not errs else []
    if errs:
        raise SchemaError(errs)
    return doc


def semantic_probe(d: dict) -> List[str]:
    e = []
    if d["state"] == "usable" and d["reason"] != "ok":
        e.append("usable requires reason 'ok' (positive evidence)")
    if d["state"] != "usable" and d["reason"] == "ok":
        e.append("non-usable state cannot carry reason 'ok'")
    if d["bare_metal"] and (d["nesting_depth"] != 0 or d["virtualized"] is not False):
        e.append("bare_metal requires nesting_depth 0 and virtualized false")
    if d["virtualized"] is True and d["nesting_depth"] == 0:
        e.append("virtualized host cannot report nesting_depth 0")
    return e


def semantic_depth(d: dict) -> List[str]:
    nd = d.get("nesting_depth")
    return ["nesting_depth > 0 implies bare_metal=false"] if nd and d.get("bare_metal") else []


def semantic_claim2(d: dict) -> List[str]:
    e = semantic_depth(d)
    if d["bare_metal"] and d["nesting_depth"] is None:
        e.append("unknown depth cannot be bare metal")
    if d["lease_expires_at"] < d["acquired_at"]:
        e.append("lease expires before acquisition")
    return e


SEMANTIC = {
    "PK_VIRT_PRIMITIVE/1": semantic_depth,
    "PK_VIRT_PRIMITIVE/2": semantic_probe,
    "PK_VIRT_CLAIM/1": semantic_depth,
    "PK_VIRT_CLAIM/2": semantic_claim2,
}


def validate_probe_report(d: dict) -> dict:
    return validate(d, CURRENT["probe"])


def validate_claim_response(d: dict) -> dict:
    return validate(d, CURRENT["claim"])
