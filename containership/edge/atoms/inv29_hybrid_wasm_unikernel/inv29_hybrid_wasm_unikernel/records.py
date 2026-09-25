"""Secure serialization, schema validation and redaction (MC008/009/024/057/058).

* ``canonical()``  - deterministic JSON bytes used for digests and signatures.
* ``parse()``      - strict, bounded JSON parser: size cap, depth cap, duplicate
                     keys, NaN/Infinity and non-object roots are all refused.
* ``validate()``   - validates a record against the bundled JSON Schemas in
                     ``schemas/`` using a small, dependency-free subset of
                     JSON Schema 2020-12 (type, required, properties,
                     additionalProperties, enum, const, pattern, min/max,
                     items, minItems/maxItems, maxLength, $ref to $defs).
* ``redact()``     - removes secret-bearing fields before logging/export.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from typing import Any

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
MAX_RECORD_BYTES = 1 << 20  # 1 MiB
MAX_DEPTH = 32
SCHEMA_FILES = {
    "PK_HYBRID_COMPOSITION/1": "pk_hybrid_composition_1.schema.json",
    "PK_HYBRID_VERIFICATION/1": "pk_hybrid_verification_1.schema.json",
}
SECRET_KEYS = re.compile(r"(secret|token|password|passwd|private|credential|api[-_]?key|signing[-_]?key|mac_key)", re.I)
REDACTED = "[REDACTED]"


class RecordInvalid(ValueError):
    """A serialized record failed parsing or schema validation."""


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise RecordInvalid(f"duplicate key {k!r}")
        out[k] = v
    return out


def _reject_const(token):
    raise RecordInvalid(f"non-finite number {token} refused")


def _depth(obj: Any, level: int = 0) -> None:
    if level > MAX_DEPTH:
        raise RecordInvalid(f"nesting deeper than {MAX_DEPTH}")
    if isinstance(obj, dict):
        for v in obj.values():
            _depth(v, level + 1)
    elif isinstance(obj, list):
        for v in obj:
            _depth(v, level + 1)


def parse(data: bytes | str, *, schema: str | None = None) -> dict:
    """Parse an untrusted serialized record; optionally validate against ``schema``."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not isinstance(data, (bytes, bytearray)):
        raise RecordInvalid("record must be bytes or str")
    if len(data) > MAX_RECORD_BYTES:
        raise RecordInvalid(f"record exceeds {MAX_RECORD_BYTES} bytes")
    try:
        text = bytes(data).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RecordInvalid("record is not valid UTF-8") from exc
    # cheap pre-check so a hostile '[[[[...' cannot blow the C recursion limit
    depth = cur = 0
    for ch in text:
        if ch in "[{":
            cur += 1
            depth = max(depth, cur)
            if depth > MAX_DEPTH + 1:
                raise RecordInvalid(f"nesting deeper than {MAX_DEPTH}")
        elif ch in "]}":
            cur -= 1
    try:
        obj = json.loads(text, object_pairs_hook=_no_dupes, parse_constant=_reject_const)
    except RecordInvalid:
        raise
    except (ValueError, RecursionError) as exc:
        raise RecordInvalid(f"malformed JSON: {exc.__class__.__name__}") from exc
    if not isinstance(obj, dict):
        raise RecordInvalid("record root must be an object")
    _depth(obj)
    if schema is not None:
        validate(obj, schema)
    return obj


_SCHEMA_CACHE: dict = {}


def load_schema(schema_id: str) -> dict:
    if schema_id not in SCHEMA_FILES:
        raise RecordInvalid(f"unknown schema {schema_id!r}")
    if schema_id not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[schema_id] = json.loads((SCHEMA_DIR / SCHEMA_FILES[schema_id]).read_text("utf-8"))
    return _SCHEMA_CACHE[schema_id]


_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v),
    "null": lambda v: v is None,
}


def _ecma(pattern: str) -> str:
    """JSON Schema patterns are ECMA-262: '$' never matches before a trailing newline.
    Python's '$' does, so a terminal '$' is rewritten to '\\Z'."""
    if pattern.endswith("$") and not pattern.endswith("\\$"):
        return pattern[:-1] + r"\Z"
    return pattern


def _check(value: Any, sch: dict, root: dict, path: str, errors: list) -> None:
    if "$ref" in sch:
        ref = sch["$ref"]
        if not ref.startswith("#/$defs/"):
            errors.append(f"{path}: unsupported $ref {ref}")
            return
        sch = root["$defs"][ref.split("/")[-1]]
    t = sch.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](value) for x in types):
            errors.append(f"{path}: expected {t}")
            return
    if "const" in sch and value != sch["const"]:
        errors.append(f"{path}: must equal {sch['const']!r}")
    if "enum" in sch and value not in sch["enum"]:
        errors.append(f"{path}: not in {sch['enum']}")
    if isinstance(value, str):
        if "maxLength" in sch and len(value) > sch["maxLength"]:
            errors.append(f"{path}: longer than {sch['maxLength']}")
        if "minLength" in sch and len(value) < sch["minLength"]:
            errors.append(f"{path}: shorter than {sch['minLength']}")
        if "pattern" in sch and not re.search(_ecma(sch["pattern"]), value):
            errors.append(f"{path}: does not match {sch['pattern']}")
    if _TYPES["number"](value):
        if "minimum" in sch and value < sch["minimum"]:
            errors.append(f"{path}: below {sch['minimum']}")
        if "maximum" in sch and value > sch["maximum"]:
            errors.append(f"{path}: above {sch['maximum']}")
    if isinstance(value, list):
        if "minItems" in sch and len(value) < sch["minItems"]:
            errors.append(f"{path}: fewer than {sch['minItems']} items")
        if "maxItems" in sch and len(value) > sch["maxItems"]:
            errors.append(f"{path}: more than {sch['maxItems']} items")
        if sch.get("uniqueItems") and len({canonical(v) for v in value}) != len(value):
            errors.append(f"{path}: items not unique")
        if "items" in sch:
            for i, v in enumerate(value):
                _check(v, sch["items"], root, f"{path}[{i}]", errors)
    if isinstance(value, dict):
        for k in sch.get("required", []):
            if k not in value:
                errors.append(f"{path}: missing {k!r}")
        props = sch.get("properties", {})
        for k, v in value.items():
            if k in props:
                _check(v, props[k], root, f"{path}.{k}", errors)
            elif sch.get("additionalProperties", True) is False:
                errors.append(f"{path}: unexpected property {k!r}")
            elif isinstance(sch.get("additionalProperties"), dict):
                _check(v, sch["additionalProperties"], root, f"{path}.{k}", errors)


def validate(record: Any, schema_id: str) -> None:
    root = load_schema(schema_id)
    errors: list = []
    _check(record, root, root, "$", errors)
    if errors:
        raise RecordInvalid(f"{schema_id}: " + "; ".join(errors[:20]))


def redact(obj: Any) -> Any:
    """Return a copy of ``obj`` with secret-looking keys replaced by ``[REDACTED]``."""
    if isinstance(obj, dict):
        return {k: (REDACTED if isinstance(k, str) and SECRET_KEYS.search(k) else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    if isinstance(obj, (frozenset, set)):
        return sorted(redact(v) for v in obj)
    return obj
