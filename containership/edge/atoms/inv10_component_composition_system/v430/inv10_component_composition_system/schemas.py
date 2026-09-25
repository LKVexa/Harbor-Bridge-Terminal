"""MC-03 / MC-04: machine-readable PK_COMPONENT/1 and PK_COMPOSITION/1 contracts.

The JSON Schema documents in ``schemas/`` are the portable artifacts for other
implementations. This module ships an equivalent dependency-free validator so
the package can enforce them without a third-party JSON Schema library.
Unknown-field policy: PK_COMPONENT/1 rejects unknown fields (closed input);
PK_COMPOSITION/1 permits additive fields (consumers must ignore unknowns).
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any

from .composition import COMPOSITION_SCHEMA, IDENTITY_PROFILE, Unit
from .errors import SchemaViolation

COMPONENT_SCHEMA = "PK_COMPONENT/1"
SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

COMPONENT_FIELDS = {"schema", "name", "imports", "exports", "metadata"}
COMPOSITION_REQUIRED = {
    "components": list, "order": list, "external_imports": list, "exports": list,
    "providers": dict, "bindings": list, "composition": str, "digest_algorithm": str,
    "identity_profile": str, "schema": str, "closed": bool,
}


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _str_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise SchemaViolation(f"{field} must be an array of non-empty strings", field=field)
    if len(set(value)) != len(value):
        raise SchemaViolation(f"{field} must not contain duplicates", field=field)
    return value


def validate_component(doc: Any) -> Unit:
    """Validate a PK_COMPONENT/1 document and return the Unit it declares."""
    if not isinstance(doc, dict):
        raise SchemaViolation("component document must be an object")
    unknown = set(doc) - COMPONENT_FIELDS
    if unknown:
        raise SchemaViolation("unknown fields in PK_COMPONENT/1", fields=sorted(unknown))
    if doc.get("schema") != COMPONENT_SCHEMA:
        raise SchemaViolation("schema must be PK_COMPONENT/1", field="schema", observed=doc.get("schema"))
    name = doc.get("name")
    if not isinstance(name, str) or not name:
        raise SchemaViolation("name must be a non-empty string", field="name")
    imports = _str_list(doc.get("imports", []), "imports")
    exports = _str_list(doc.get("exports", []), "exports")
    if "metadata" in doc and not isinstance(doc["metadata"], dict):
        raise SchemaViolation("metadata must be an object", field="metadata")
    return Unit(name, frozenset(imports), frozenset(exports))


def component_document(unit: Unit, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": COMPONENT_SCHEMA, "name": unit.name,
        "imports": sorted(unit.imports), "exports": sorted(unit.exports),
    }
    if metadata:
        doc["metadata"] = dict(metadata)
    return doc


def validate_composition(doc: Any) -> dict[str, Any]:
    """Validate a PK_COMPOSITION/1 result, tolerating additive fields."""
    if not isinstance(doc, dict):
        raise SchemaViolation("composition document must be an object")
    for field, typ in COMPOSITION_REQUIRED.items():
        if field not in doc:
            raise SchemaViolation(f"missing required field {field}", field=field)
        if not isinstance(doc[field], typ):
            raise SchemaViolation(f"{field} must be {typ.__name__}", field=field)
    if doc["schema"] != COMPOSITION_SCHEMA:
        raise SchemaViolation("schema must be PK_COMPOSITION/1", field="schema")
    if doc["identity_profile"] != IDENTITY_PROFILE:
        raise SchemaViolation("unsupported identity profile", field="identity_profile",
                              observed=doc["identity_profile"])
    if doc["digest_algorithm"] != "sha256" or not _HEX64.match(doc["composition"]):
        raise SchemaViolation("composition must be a 64-hex sha256 digest", field="composition")
    if doc["closed"] is not True:
        raise SchemaViolation("closed must be true", field="closed")
    comps = _str_list(doc["components"], "components")
    if sorted(doc["order"]) != sorted(comps):
        raise SchemaViolation("order must be a permutation of components", field="order")
    for b in doc["bindings"]:
        if not isinstance(b, dict) or not {"consumer", "interface"} <= set(b):
            raise SchemaViolation("binding must have consumer and interface", field="bindings")
        if ("provider" in b) == bool(b.get("external")):
            raise SchemaViolation("binding must have exactly one of provider/external", field="bindings")
    position = {n: i for i, n in enumerate(doc["order"])}
    for b in doc["bindings"]:
        if "provider" in b and position.get(b["provider"], -1) >= position.get(b["consumer"], -1):
            raise SchemaViolation("provider must precede consumer in order", field="order", binding=b)
    return doc
