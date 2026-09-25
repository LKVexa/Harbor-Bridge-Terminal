"""MC07 - Concrete wire schemas and validators; MC08 - schema/version negotiation.

Machine-readable definitions (JSON-Schema draft 2020-12 documents, emitted by
``json_schemas()``) plus hand-written strict validators, because the package is
stdlib-only.  Validation is strict: unknown fields, duplicate JSON object keys,
non-canonical types, lone surrogates and oversized fields are rejected.

Canonical encoding (used for hashing, signing and dedupe identity) is JSON with sorted
keys, no insignificant whitespace, UTF-8, ``ensure_ascii=False``.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .errors import IncompatibleVersion, SchemaError
from .limits import DEFAULT_LIMITS, Limits

WRITE_SCHEMA = "PK_REPLICATED_WRITE/1"
MERGE_SCHEMA = "PK_MERGE_RESULT/1"
CONFLICT_SCHEMA = "PK_CONFLICT_SET/1"

SUPPORTED = {
    "PK_REPLICATED_WRITE": (1,),
    "PK_MERGE_RESULT": (1,),
    "PK_CONFLICT_SET": (1,),
}
MERGE_OUTCOMES = ("converged", "conflict", "duplicate", "superseded", "quarantined", "rejected")

_WRITE_REQUIRED = {"schema", "tenant", "environment", "key", "value", "site", "vector", "epoch", "op_id"}
_WRITE_OPTIONAL = {"deleted", "value_type", "provenance", "trace_id"}
_PROV_FIELDS = {"alg", "key_id", "sig"}


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise SchemaError(f"duplicate field {k!r}", code="CORR_SCHEMA_DUPLICATE_FIELD")
        out[k] = v
    return out


def strict_loads(data: bytes | str, limits: Limits = DEFAULT_LIMITS) -> Any:
    if isinstance(data, bytes):
        if len(data) > limits.max_frame_bytes:
            raise SchemaError("document exceeds max_frame_bytes", code="CAP_FRAME_SIZE")
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SchemaError(f"invalid UTF-8: {exc}", code="CORR_SCHEMA_ENCODING") from exc
    try:
        obj = json.loads(data, object_pairs_hook=_no_dupes,
                         parse_constant=lambda c: (_ for _ in ()).throw(SchemaError(f"constant {c} not allowed")))
    except SchemaError:
        raise
    except (ValueError, RecursionError) as exc:
        raise SchemaError(f"malformed JSON: {exc}", code="CORR_SCHEMA_MALFORMED") from exc
    return obj


def _text(value, name: str, max_bytes: int, *, allow_empty=False) -> str:
    if not isinstance(value, str) or (not value and not allow_empty):
        raise SchemaError(f"{name} must be a {'string' if allow_empty else 'non-empty string'}")
    try:
        raw = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise SchemaError(f"{name} contains a lone surrogate", code="CORR_SCHEMA_ENCODING") from exc
    if len(raw) > max_bytes:
        raise SchemaError(f"{name} exceeds {max_bytes} bytes", code="CAP_FIELD_SIZE")
    if any(ord(ch) < 0x20 for ch in value) and name not in ("value",):
        raise SchemaError(f"{name} contains control characters")
    return value


def parse_schema_id(schema: Any) -> tuple[str, int]:
    if not isinstance(schema, str) or schema.count("/") != 1:
        raise SchemaError(f"bad schema identifier {schema!r}")
    family, _, version = schema.partition("/")
    if not version.isdigit() or version.startswith("0"):
        raise SchemaError(f"bad schema version in {schema!r}")
    return family, int(version)


def require_supported(schema: Any, expected_family: str) -> None:
    family, version = parse_schema_id(schema)
    if family != expected_family:
        raise SchemaError(f"expected {expected_family}, got {family}")
    if version not in SUPPORTED[family]:
        raise IncompatibleVersion(
            f"{family}/{version} unsupported; supported={SUPPORTED[family]}", code="CORR_INCOMPATIBLE_VERSION"
        )


def validate_write_doc(doc: Any, limits: Limits = DEFAULT_LIMITS) -> dict:
    if not isinstance(doc, dict):
        raise SchemaError("write must be an object")
    keys = set(doc)
    missing = _WRITE_REQUIRED - keys
    extra = keys - _WRITE_REQUIRED - _WRITE_OPTIONAL
    if missing:
        raise SchemaError(f"missing fields {sorted(missing)}", code="CORR_SCHEMA_MISSING")
    if extra:
        raise SchemaError(f"unknown fields {sorted(extra)}", code="CORR_SCHEMA_UNKNOWN")
    require_supported(doc["schema"], "PK_REPLICATED_WRITE")
    _text(doc["tenant"], "tenant", 128)
    _text(doc["environment"], "environment", 64)
    _text(doc["key"], "key", limits.max_key_bytes)
    _text(doc["value"], "value", limits.max_value_bytes, allow_empty=True)
    _text(doc["site"], "site", 128)
    epoch = doc["epoch"]
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 1:
        raise SchemaError("epoch must be a positive integer")
    vec = doc["vector"]
    if not isinstance(vec, list) or not vec:
        raise SchemaError("vector must be a non-empty array")
    if len(vec) > limits.max_vector_entries:
        raise SchemaError("vector too large", code="CAP_VECTOR_SIZE")
    seen = set()
    for entry in vec:
        if not isinstance(entry, list) or len(entry) != 2:
            raise SchemaError("vector entries must be [site, counter]")
        site, counter = entry
        _text(site, "vector site", 128)
        if isinstance(counter, bool) or not isinstance(counter, int) or not 0 < counter <= limits.max_counter:
            raise SchemaError("vector counter must be an integer in range")
        if site in seen:
            raise SchemaError("vector names a site twice")
        seen.add(site)
    if doc["site"] not in seen:
        raise SchemaError("author did not stamp its own counter")
    if [e[0] for e in vec] != sorted(seen):
        raise SchemaError("vector must be site-sorted (canonical form)", code="CORR_SCHEMA_NONCANONICAL")
    if "deleted" in doc and not isinstance(doc["deleted"], bool):
        raise SchemaError("deleted must be boolean")
    if "value_type" in doc:
        _text(doc["value_type"], "value_type", 64)
    if "trace_id" in doc:
        _text(doc["trace_id"], "trace_id", 64)
    if "provenance" in doc:
        prov = doc["provenance"]
        if not isinstance(prov, dict) or set(prov) != _PROV_FIELDS:
            raise SchemaError("provenance must have exactly alg, key_id, sig")
        for name in _PROV_FIELDS:
            _text(prov[name], f"provenance.{name}", 512)
    expected = op_id_for(doc)
    if doc["op_id"] != expected:
        raise SchemaError("op_id does not match content", code="CORR_SCHEMA_OPID")
    return doc


def signable_view(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("provenance", "op_id", "trace_id")}


def op_id_for(doc: dict) -> str:
    """Content-addressed durable dedupe identity (MC09)."""
    return digest(signable_view(doc))


def make_write_doc(*, tenant, environment, key, value, site, vector, epoch, deleted=False,
                   value_type=None) -> dict:
    doc = {
        "schema": WRITE_SCHEMA,
        "tenant": tenant,
        "environment": environment,
        "key": key,
        "value": value,
        "site": site,
        "vector": [[s, int(c)] for s, c in sorted(dict(vector).items())],
        "epoch": epoch,
    }
    if deleted:
        doc["deleted"] = True
    if value_type:
        doc["value_type"] = value_type
    doc["op_id"] = op_id_for(doc)
    return doc


def make_merge_result(*, tenant, environment, key, op_id, outcome, value=None, conflict=None, reason=None) -> dict:
    if outcome not in MERGE_OUTCOMES:
        raise SchemaError(f"unknown merge outcome {outcome!r}")
    doc = {"schema": MERGE_SCHEMA, "tenant": tenant, "environment": environment, "key": key,
           "op_id": op_id, "outcome": outcome}
    if value is not None:
        doc["value"] = value
    if conflict is not None:
        doc["conflict"] = conflict
    if reason is not None:
        doc["reason"] = reason
    return validate_merge_result(doc)


def validate_merge_result(doc: Any) -> dict:
    if not isinstance(doc, dict):
        raise SchemaError("merge result must be an object")
    allowed = {"schema", "tenant", "environment", "key", "op_id", "outcome", "value", "conflict", "reason"}
    if set(doc) - allowed:
        raise SchemaError(f"unknown fields {sorted(set(doc) - allowed)}")
    for name in ("schema", "tenant", "environment", "key", "op_id", "outcome"):
        if name not in doc:
            raise SchemaError(f"missing {name}")
    require_supported(doc["schema"], "PK_MERGE_RESULT")
    if doc["outcome"] not in MERGE_OUTCOMES:
        raise SchemaError("bad outcome")
    if "conflict" in doc:
        validate_conflict_set(doc["conflict"])
    return doc


def validate_conflict_set(doc: Any) -> dict:
    if not isinstance(doc, dict):
        raise SchemaError("conflict set must be an object")
    required = {"schema", "key", "siblings", "quarantined", "open", "total_unresolved"}
    if set(doc) != required:
        raise SchemaError(f"conflict set fields must be exactly {sorted(required)}")
    require_supported(doc["schema"], "PK_CONFLICT_SET")
    if not isinstance(doc["open"], bool):
        raise SchemaError("open must be boolean")
    for group in ("siblings", "quarantined"):
        if not isinstance(doc[group], list):
            raise SchemaError(f"{group} must be an array")
        for item in doc[group]:
            need = {"site", "value", "vector"} | ({"reason"} if group == "quarantined" else set())
            if not isinstance(item, dict) or set(item) != need:
                raise SchemaError(f"{group} entry has wrong fields")
    if doc["total_unresolved"] != len(doc["siblings"]) + len(doc["quarantined"]):
        raise SchemaError("total_unresolved inconsistent")
    if doc["open"] != (doc["total_unresolved"] > 1):
        raise SchemaError("open flag inconsistent with total_unresolved")
    return doc


def json_schemas() -> dict[str, dict]:
    vec = {"type": "array", "minItems": 1, "items": {"type": "array", "prefixItems": [
        {"type": "string", "minLength": 1}, {"type": "integer", "minimum": 1}], "minItems": 2, "maxItems": 2}}
    return {
        WRITE_SCHEMA: {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:pk:gap05:PK_REPLICATED_WRITE:1", "type": "object", "additionalProperties": False,
            "required": sorted(_WRITE_REQUIRED),
            "properties": {
                "schema": {"const": WRITE_SCHEMA}, "tenant": {"type": "string", "minLength": 1},
                "environment": {"type": "string", "minLength": 1}, "key": {"type": "string", "minLength": 1},
                "value": {"type": "string"}, "site": {"type": "string", "minLength": 1}, "vector": vec,
                "epoch": {"type": "integer", "minimum": 1}, "op_id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "deleted": {"type": "boolean"}, "value_type": {"type": "string"}, "trace_id": {"type": "string"},
                "provenance": {"type": "object", "additionalProperties": False, "required": ["alg", "key_id", "sig"],
                               "properties": {"alg": {"type": "string"}, "key_id": {"type": "string"},
                                              "sig": {"type": "string"}}},
            },
        },
        MERGE_SCHEMA: {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:pk:gap05:PK_MERGE_RESULT:1", "type": "object", "additionalProperties": False,
            "required": ["schema", "tenant", "environment", "key", "op_id", "outcome"],
            "properties": {"schema": {"const": MERGE_SCHEMA}, "tenant": {"type": "string"},
                           "environment": {"type": "string"}, "key": {"type": "string"},
                           "op_id": {"type": "string"}, "outcome": {"enum": list(MERGE_OUTCOMES)},
                           "value": {"type": "string"}, "reason": {"type": "string"},
                           "conflict": {"$ref": "urn:pk:gap05:PK_CONFLICT_SET:1"}},
        },
        CONFLICT_SCHEMA: {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:pk:gap05:PK_CONFLICT_SET:1", "type": "object", "additionalProperties": False,
            "required": ["schema", "key", "siblings", "quarantined", "open", "total_unresolved"],
            "properties": {"schema": {"const": CONFLICT_SCHEMA}, "key": {"type": "string"},
                           "siblings": {"type": "array"}, "quarantined": {"type": "array"},
                           "open": {"type": "boolean"}, "total_unresolved": {"type": "integer", "minimum": 0}},
        },
    }


# ---------------------------------------------------------------- negotiation (MC08)
def negotiate(local: dict[str, tuple[int, ...]], peer: dict[str, list[int]]) -> dict[str, int]:
    """Pick the highest commonly supported version per schema family.

    Every locally required family must have a common version; otherwise the peer is
    rejected with ``IncompatibleVersion`` (fail closed - no silent downgrade to an
    unsupported version, no guessing).
    """
    if not isinstance(peer, dict):
        raise SchemaError("peer capability advertisement must be an object")
    agreed = {}
    for family, versions in local.items():
        offered = peer.get(family)
        if not isinstance(offered, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in offered):
            raise IncompatibleVersion(f"peer did not advertise {family}", code="CORR_NEGOTIATION_MISSING")
        common = set(versions) & set(offered)
        if not common:
            raise IncompatibleVersion(
                f"no common {family} version (local={list(versions)}, peer={offered})",
                code="CORR_NEGOTIATION_NONE",
            )
        agreed[family] = max(common)
    return agreed
