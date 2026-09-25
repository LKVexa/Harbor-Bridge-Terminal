"""Schema loading, hardened decoding and validation for external interfaces (WS 3).

A deliberately small JSON-Schema (2020-12 subset) validator, stdlib only, so the package has no
runtime dependency.  Supported keywords: type, const, enum, required, properties,
additionalProperties, minimum, maximum, minLength, maxLength, pattern, oneOf, $ref (local), items,
maxItems.  Integers exclude booleans.  ``decode_request`` enforces size, depth, duplicate-key,
Unicode and numeric-range limits *before* schema validation, and schema validation happens before
anything reaches mutation logic.
"""
from __future__ import annotations

from functools import cache
import json
from pathlib import Path
import re
from typing import Any

from . import errors as E

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
SCHEMA_FILES = {
    "request": "resource_adjustment_request.v2.schema.json",
    "result": "resource_adjustment_result.v2.schema.json",
    "audit_event": "resource_audit_event.v1.schema.json",
    "host": "host_resources.v1.schema.json",
    "error": "error.v1.schema.json",
}
MAX_REQUEST_BYTES = 4096
MAX_DEPTH = 4
SUPPORTED_MAJOR = {"PK_RESOURCE_ADJUSTMENT": {2}}  # v1 only accepted as a *revert record*, not a request
_INT_LIMIT = 2 ** 53 - 1


@cache
def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / SCHEMA_FILES[name]).read_text(encoding="utf-8"))


_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _resolve(root: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ValueError("only local $ref supported")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def iter_errors(value: Any, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    root = root or schema
    errs: list[str] = []
    if "$ref" in schema:
        return iter_errors(value, _resolve(root, schema["$ref"]), root, path)
    if "oneOf" in schema:
        matches = [s for s in schema["oneOf"] if not iter_errors(value, s, root, path)]
        if len(matches) != 1:
            # Report the variant error for the tagged union where the tag matches, for useful diagnostics.
            tag_hits = [s for s in schema["oneOf"] if isinstance(value, dict)
                        and s.get("properties", {}).get("op", {}).get("const") == value.get("op")]
            if tag_hits:
                return iter_errors(value, tag_hits[0], root, path)
            errs.append(f"{path}: matched {len(matches)} of oneOf variants")
        return errs
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](value) for x in types):
            return [f"{path}: expected {t}"]
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: not in enum")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append(f"{path}: too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append(f"{path}: too long")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path}: pattern mismatch")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}.{req}: required")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                errs.extend(iter_errors(v, props[k], root, f"{path}.{k}"))
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}.{k}: unknown field")
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path}: too many items")
        if "items" in schema:
            for i, item in enumerate(value):
                errs.extend(iter_errors(item, schema["items"], root, f"{path}[{i}]"))
    return errs


def validate(name: str, value: Any) -> None:
    errs = iter_errors(value, load_schema(name))
    if errs:
        raise E.ValidationFailed("schema validation failed", schema=name, errors="; ".join(errs[:8]))


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise E.ValidationFailed("duplicate field", field=k[:64])
        out[k] = v
    return out


def _depth(v: Any, d: int = 0) -> int:
    if isinstance(v, dict):
        return max([d + 1] + [_depth(x, d + 1) for x in v.values()])
    if isinstance(v, list):
        return max([d + 1] + [_depth(x, d + 1) for x in v])
    return d


def _reject_const(token: str) -> Any:
    raise E.ValidationFailed("non-finite number")


def _int_guard(s: str) -> int:
    if len(s) > 20:
        raise E.ValidationFailed("integer literal too long")
    v = int(s)
    if abs(v) > _INT_LIMIT:
        raise E.ValidationFailed("integer outside safe range")
    return v


def decode_request(raw: bytes | str) -> dict[str, Any]:
    """Decode an untrusted request.  Never raises anything but ValidationFailed / SchemaVersionUnsupported."""
    if isinstance(raw, str):
        try:
            raw = raw.encode("utf-8")
        except UnicodeEncodeError:  # lone surrogates
            raise E.ValidationFailed("invalid unicode") from None
    if not isinstance(raw, (bytes, bytearray)):
        raise E.ValidationFailed("request must be bytes")
    if len(raw) > MAX_REQUEST_BYTES:
        raise E.ValidationFailed("request too large", max_bytes=MAX_REQUEST_BYTES)
    try:
        text = bytes(raw).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise E.ValidationFailed("invalid utf-8") from None
    try:
        doc = json.loads(text, object_pairs_hook=_no_dupes, parse_constant=_reject_const, parse_int=_int_guard)
    except E.ValidationFailed:
        raise
    except (ValueError, RecursionError):
        raise E.ValidationFailed("malformed JSON") from None
    if not isinstance(doc, dict):
        raise E.ValidationFailed("request must be an object")
    if _depth(doc) > MAX_DEPTH:
        raise E.ValidationFailed("request nesting too deep")
    schema_id = doc.get("schema")
    if isinstance(schema_id, str) and "/" in schema_id:
        family, _, major = schema_id.rpartition("/")
        if family in SUPPORTED_MAJOR and major.isdigit() and int(major) not in SUPPORTED_MAJOR[family]:
            raise E.SchemaVersionUnsupported("unsupported schema major version", schema=schema_id[:64],
                                             supported=",".join(f"{family}/{m}" for m in sorted(SUPPORTED_MAJOR[family])))
    for key in ("host", "guest", "tenant", "operation_id", "reason"):
        v = doc.get(key)
        if isinstance(v, str) and any(ord(c) < 0x20 or ord(c) == 0x7F for c in v):
            raise E.ValidationFailed("control characters are not permitted", field=key)
    validate("request", doc)
    return doc
