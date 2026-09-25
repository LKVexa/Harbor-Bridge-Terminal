"""MC-15: declarative PK_COMPOSITION_MANIFEST/1 loader/validator.

Bounded (size, depth), strict (unknown fields rejected), duplicate-key-safe
JSON ingestion with deterministic, path-addressed errors.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

from .composition import Unit
from .errors import SchemaViolation
from .governance import CompositionContext
from .schemas import validate_component

MANIFEST_SCHEMA = "PK_COMPOSITION_MANIFEST/1"
MAX_MANIFEST_BYTES = 8 << 20
MAX_DEPTH = 32
FIELDS = {"schema", "context", "external", "aliases", "provenance", "components"}


@dataclass
class CompositionManifest:
    units: list[Unit]
    external: frozenset[str]
    context: CompositionContext | None = None
    aliases: dict[str, dict[str, str]] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, dict[str, Any]] = field(default_factory=dict)


def _no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise SchemaViolation("duplicate JSON object key", keys=sorted({k for k in keys if keys.count(k) > 1}))
    return dict(pairs)


def _depth(obj: Any, d: int = 0) -> None:
    if d > MAX_DEPTH:
        raise SchemaViolation("manifest nesting too deep", limit=MAX_DEPTH)
    if isinstance(obj, dict):
        for v in obj.values():
            _depth(v, d + 1)
    elif isinstance(obj, list):
        for v in obj:
            _depth(v, d + 1)


def loads(text: str | bytes) -> CompositionManifest:
    raw = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise SchemaViolation("manifest exceeds size limit", limit=MAX_MANIFEST_BYTES)
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupes,
                         parse_constant=lambda c: (_ for _ in ()).throw(SchemaViolation(f"non-finite number {c}")))
    except UnicodeDecodeError:
        raise SchemaViolation("manifest must be UTF-8") from None
    except json.JSONDecodeError as exc:
        raise SchemaViolation("manifest is not valid JSON", line=exc.lineno, column=exc.colno) from None
    return from_document(doc)


def load(path: str | pathlib.Path) -> CompositionManifest:
    p = pathlib.Path(path)
    if p.stat().st_size > MAX_MANIFEST_BYTES:
        raise SchemaViolation("manifest exceeds size limit", limit=MAX_MANIFEST_BYTES)
    return loads(p.read_bytes())


def from_document(doc: Any) -> CompositionManifest:
    _depth(doc)
    if not isinstance(doc, dict):
        raise SchemaViolation("manifest must be an object", path="$")
    unknown = sorted(set(doc) - FIELDS)
    if unknown:
        raise SchemaViolation("unknown manifest fields", path="$", fields=unknown)
    if doc.get("schema") != MANIFEST_SCHEMA:
        raise SchemaViolation("schema must be PK_COMPOSITION_MANIFEST/1", path="$.schema")
    comps = doc.get("components")
    if not isinstance(comps, list):
        raise SchemaViolation("components must be an array", path="$.components")
    units, meta = [], {}
    for i, c in enumerate(comps):
        try:
            u = validate_component(c)
        except SchemaViolation as exc:
            raise SchemaViolation(str(exc), path=f"$.components[{i}]", **exc.details) from None
        units.append(u)
        if c.get("metadata"):
            meta[u.name] = dict(c["metadata"])
    ext = doc.get("external", [])
    if not isinstance(ext, list) or not all(isinstance(e, str) for e in ext) or len(set(ext)) != len(ext):
        raise SchemaViolation("external must be an array of unique strings", path="$.external")
    ctx = None
    if "context" in doc:
        c = doc["context"]
        if not isinstance(c, dict) or set(c) - {"tenant", "workload", "environment", "site"}:
            raise SchemaViolation("invalid context", path="$.context")
        try:
            ctx = CompositionContext(**c)
        except TypeError:
            raise SchemaViolation("context requires tenant, workload, environment", path="$.context") from None
    aliases = doc.get("aliases", {})
    if not isinstance(aliases, dict) or not all(
            isinstance(v, dict) and all(isinstance(a, str) and isinstance(b, str) for a, b in v.items())
            for v in aliases.values()):
        raise SchemaViolation("aliases must map consumer -> {import: interface}", path="$.aliases")
    prov = doc.get("provenance", {})
    if not isinstance(prov, dict):
        raise SchemaViolation("provenance must be an object", path="$.provenance")
    return CompositionManifest(units, frozenset(ext), ctx, aliases, prov, meta)
