"""Versioned typed schemas and a stdlib validator for INV-26 (C022, C028, C029).

The schemas below are the single source of truth; ``schemas/*.schema.json``
are generated from them (``python -m inv26_microvm_snapshotting.schema write``)
and CI fails if the files drift (``tools/schemas_check.py``).

The validator implements the JSON-Schema (2020-12) subset the schemas use:
type, const, enum, pattern, minLength/maxLength, minimum/maximum,
required, properties, additionalProperties=false, items, minItems/maxItems,
uniqueItems. Unknown fields are rejected at every trust boundary. The
validator bounds its own work (depth, collection size, string length)
*before* walking, so a hostile document cannot make it allocate or recurse
without limit.

Canonical serialization (C022): signed/hashed structures use
:func:`canonical_bytes` — UTF-8 JSON, sorted keys, no whitespace,
``ensure_ascii=False``, integers only (floats are refused inside signed
records), so semantically equal records have exactly one encoding.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from .errors import SnapshotServiceError

ID_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,62}$"
HEX64 = r"^[0-9a-f]{64}$"
DEVICE_PATTERN = r"^[a-z0-9][a-z0-9._:-]{0,62}$"

MAX_DEPTH = 8
MAX_DOC_BYTES = 64 * 1024
MAX_DEVICES = 64
MAX_MEMORY_MIB = 1024 * 1024  # 1 TiB

_ident = {"type": "string", "pattern": ID_PATTERN, "maxLength": 63}
_security_context = {
    "tenant": _ident, "workload": _ident, "environment": _ident,
}
_devices = {"type": "array", "items": {"type": "string", "pattern": DEVICE_PATTERN, "maxLength": 63},
            "minItems": 1, "maxItems": MAX_DEVICES, "uniqueItems": True}

SCHEMAS: dict[str, dict] = {
    "PK_SNAPSHOT_CAPTURE_REQUEST/2": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "snapshot_id", "tenant", "workload", "environment", "devices",
                     "memory_mib", "vm_id", "idempotency_key"],
        "properties": {
            "schema": {"const": "PK_SNAPSHOT_CAPTURE_REQUEST/2"},
            "snapshot_id": _ident, **_security_context,
            "site": _ident,
            "devices": _devices,
            "memory_mib": {"type": "integer", "minimum": 1, "maximum": MAX_MEMORY_MIB},
            "vm_id": _ident,
            "idempotency_key": {"type": "string", "pattern": r"^[A-Za-z0-9_-]{8,64}$"},
            "deadline_ms": {"type": "integer", "minimum": 1, "maximum": 600_000},
            "traceparent": {"type": "string", "maxLength": 55},
        },
    },
    "PK_SNAPSHOT_RESTORE_REQUEST/2": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "snapshot_id", "tenant", "workload", "environment", "devices",
                     "target_vm_id", "grant", "idempotency_key"],
        "properties": {
            "schema": {"const": "PK_SNAPSHOT_RESTORE_REQUEST/2"},
            "snapshot_id": _ident, **_security_context,
            "site": _ident,
            "devices": _devices,
            "target_vm_id": _ident,
            "grant": {"type": "string", "maxLength": 4096},
            "idempotency_key": {"type": "string", "pattern": r"^[A-Za-z0-9_-]{8,64}$"},
            "deadline_ms": {"type": "integer", "minimum": 1, "maximum": 60_000},
            "traceparent": {"type": "string", "maxLength": 55},
        },
    },
    "PK_SNAPSHOT_MANIFEST/1": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "snapshot_id", "tenant", "workload", "environment", "site",
                     "fingerprint", "memory_mib", "runtime", "capture_schema", "generation",
                     "envelope", "created_at"],
        "properties": {
            "schema": {"const": "PK_SNAPSHOT_MANIFEST/1"},
            "snapshot_id": _ident, **_security_context, "site": _ident,
            "fingerprint": {"type": "string", "pattern": HEX64},
            "memory_mib": {"type": "integer", "minimum": 1, "maximum": MAX_MEMORY_MIB},
            "runtime": {"type": "object", "additionalProperties": False,
                        "required": ["adapter", "version", "arch"],
                        "properties": {"adapter": {"enum": ["firecracker", "cloud-hypervisor", "reference"]},
                                       "version": {"type": "string", "maxLength": 32},
                                       "arch": {"enum": ["x86_64", "aarch64"]}}},
            "capture_schema": {"const": "PK_SNAPSHOT/2"},
            "generation": {"type": "integer", "minimum": 1},
            "envelope": {"type": "object", "additionalProperties": False,
                         "required": ["alg", "key_id", "key_version", "wrapped_dek", "chunk_size",
                                      "chunks", "ciphertext_sha256", "plaintext_bytes", "aad_schema"],
                         "properties": {
                             "alg": {"const": "AES-256-GCM-CHUNKED/1"},
                             "key_id": _ident,
                             "key_version": {"type": "integer", "minimum": 1},
                             "wrapped_dek": {"type": "string", "maxLength": 512},
                             "chunk_size": {"type": "integer", "minimum": 4096, "maximum": 64 * 1024 * 1024},
                             "chunks": {"type": "integer", "minimum": 1, "maximum": 1 << 24},
                             "ciphertext_sha256": {"type": "string", "pattern": HEX64},
                             "plaintext_bytes": {"type": "integer", "minimum": 0},
                             "aad_schema": {"const": "PK_SNAPSHOT_AAD/1"}}},
            "created_at": {"type": "integer", "minimum": 0},
        },
    },
    "PK_SNAPSHOT_RESTORE/2": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "snapshot_id", "tenant", "workload", "environment", "operation_id",
                     "restore_ms", "budget_ms", "within_budget", "entropy_reseeded",
                     "entropy_proof_sha256", "state", "outcome"],
        "properties": {
            "schema": {"const": "PK_SNAPSHOT_RESTORE/2"},
            "snapshot_id": _ident, **_security_context,
            "operation_id": {"type": "string", "maxLength": 64},
            "restore_ms": {"type": "number", "minimum": 0},
            "budget_ms": {"type": "number", "minimum": 0},
            "within_budget": {"type": "boolean"},
            "entropy_reseeded": {"const": True},
            "entropy_proof_sha256": {"type": "string", "pattern": HEX64},
            "state": {"const": "READY"},
            "outcome": {"enum": ["success", "degraded_success"]},
            "replayed": {"type": "boolean"},
            "correlation_id": {"type": "string", "maxLength": 64},
        },
    },
    "PK_SNAPSHOT_ERROR/1": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "code", "number", "outcome", "retryable", "message", "correlation_id"],
        "properties": {
            "schema": {"const": "PK_SNAPSHOT_ERROR/1"},
            "code": {"type": "string", "pattern": r"^SNAP_[A-Z_]{2,40}$"},
            "number": {"type": "integer", "minimum": 1000, "maximum": 9999},
            "outcome": {"enum": ["retryable_failure", "terminal_failure", "policy_rejection",
                                 "integrity_rejection", "operator_aborted"]},
            "retryable": {"type": "boolean"},
            "message": {"type": "string", "maxLength": 200},
            "correlation_id": {"type": "string", "maxLength": 64},
            "retry_after_s": {"type": "number", "minimum": 0},
        },
    },
}


def _type_ok(value: Any, t: str) -> bool:
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if t == "boolean":
        return isinstance(value, bool)
    return False


def _walk(value: Any, schema: dict, path: str, errors: list[str], depth: int) -> None:
    if depth > MAX_DEPTH:
        errors.append(f"{path}: nesting too deep")
        return
    if len(errors) > 50:
        return
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        errors.append(f"{path}: must equal {schema['const']!r}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not an allowed value")
        return
    t = schema.get("type")
    if t and not _type_ok(value, t):
        errors.append(f"{path}: expected {t}")
        return
    if isinstance(value, str):
        if len(value) > schema.get("maxLength", 1 << 20):
            errors.append(f"{path}: too long")
            return
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: too short")
        if "pattern" in schema and not re.fullmatch(schema["pattern"].strip("^$"), value):
            errors.append(f"{path}: bad format")
    if _type_ok(value, "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(value, list):
        if len(value) > schema.get("maxItems", 10_000):
            errors.append(f"{path}: too many items")
            return
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        if schema.get("uniqueItems"):
            try:
                if len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
                    errors.append(f"{path}: duplicate items")
            except (TypeError, ValueError):
                errors.append(f"{path}: unhashable items")
        if "items" in schema:
            for i, v in enumerate(value):
                _walk(v, schema["items"], f"{path}[{i}]", errors, depth + 1)
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", ()):
            if k not in value:
                errors.append(f"{path}.{k}: required")
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    errors.append(f"{path}.{str(k)[:40]}: unknown field")
        for k, sub in props.items():
            if k in value:
                _walk(value[k], sub, f"{path}.{k}", errors, depth + 1)


def validate(doc: Any, schema_id: str) -> list[str]:
    """Return a list of field-path errors (empty when valid)."""
    if schema_id not in SCHEMAS:
        return [f"$: unknown schema {schema_id!r}"]
    errors: list[str] = []
    _walk(doc, SCHEMAS[schema_id], "$", errors, 0)
    return errors


def require(doc: Any, schema_id: str) -> dict:
    """Validate or raise ``SNAP_INVALID_REQUEST`` / ``SNAP_UNSUPPORTED_VERSION``."""
    if isinstance(doc, dict) and isinstance(doc.get("schema"), str) and doc["schema"] != schema_id:
        family = schema_id.rsplit("/", 1)[0]
        if doc["schema"].rsplit("/", 1)[0] == family:
            raise SnapshotServiceError("SNAP_UNSUPPORTED_VERSION", f"{doc['schema']} (supported: {schema_id})")
    errs = validate(doc, schema_id)
    if errs:
        raise SnapshotServiceError("SNAP_INVALID_REQUEST", "; ".join(errs[:10]), fields=errs[:10])
    return doc


def parse_json(raw: bytes | str, schema_id: str) -> dict:
    """Bounded parse + validate for untrusted bytes (C028)."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8", "surrogatepass")
    if len(raw) > MAX_DOC_BYTES:
        raise SnapshotServiceError("SNAP_LIMIT_EXCEEDED", f"document {len(raw)} bytes > {MAX_DOC_BYTES}")
    try:
        doc = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise SnapshotServiceError("SNAP_INVALID_REQUEST", f"unparseable: {type(exc).__name__}") from None
    return require(doc, schema_id)


def _reject_constant(name: str):
    raise ValueError(f"non-finite constant {name}")


def canonical_bytes(obj: Any) -> bytes:
    def check(v: Any, depth: int = 0) -> None:
        if depth > MAX_DEPTH + 4:
            raise ValueError("too deep")
        if isinstance(v, float):
            raise ValueError("floats are not permitted in canonical records")
        if isinstance(v, dict):
            for k, x in v.items():
                if not isinstance(k, str):
                    raise ValueError("non-string key")
                check(x, depth + 1)
        elif isinstance(v, list):
            for x in v:
                check(x, depth + 1)
    check(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def write_schema_files(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for sid, body in SCHEMAS.items():
        name = sid.replace("/", "_") + ".schema.json"
        doc = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"urn:pk:inv26:{sid}",
               "title": sid, **body}
        p = out_dir / name
        p.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        written.append(p)
    return written


if __name__ == "__main__":  # pragma: no cover
    if sys.argv[1:] == ["write"]:
        for p in write_schema_files(Path(__file__).resolve().parent / "schemas"):
            print(p)
