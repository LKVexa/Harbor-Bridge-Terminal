"""MC76 — migration framework.

Ordered, idempotent, forward-only migrations for persisted formats.  Downgrades are
refused explicitly: a binary that reads a newer schema than it understands fails
closed instead of silently dropping fields (rolling-upgrade safety, MC53).
"""
from __future__ import annotations

import json
from typing import Callable

from .registry import IntegrityError, MANIFEST_MEDIA_TYPE, digest


class SchemaTooNew(IntegrityError):
    code = "SCHEMA_TOO_NEW"


_STORE_STEPS: dict[int, Callable[[dict], dict]] = {}


def _step(frm: int):
    def deco(fn):
        _STORE_STEPS[frm] = fn
        return fn
    return deco


@_step(1)
def _v1_to_v2(meta: dict) -> dict:
    # v1 stored tags as {key: digest}; v2 stores versioned records for CAS updates.
    tags = {}
    for k, v in meta.get("tags", {}).items():
        tags[k] = v if isinstance(v, dict) else {"digest": v, "version": 1, "previous": None,
                                                 "actor": "migration", "at": 0}
    meta["tags"] = tags
    meta.setdefault("leases", {})
    meta.setdefault("quarantine", {})
    meta["schema"] = 2
    return meta


def migrate_store_meta(meta: dict, target: int) -> dict:
    if not isinstance(meta, dict):
        raise IntegrityError("metadata root must be an object")
    ver = meta.get("schema", 1)
    if not isinstance(ver, int) or ver < 1:
        raise IntegrityError("metadata schema version invalid")
    if ver > target:
        raise SchemaTooNew(f"metadata schema {ver} is newer than supported {target}; refusing to downgrade")
    while ver < target:
        step = _STORE_STEPS.get(ver)
        if step is None:
            raise IntegrityError(f"no migration from schema {ver}")
        meta = step(meta)
        ver = meta["schema"]
    return meta


def migrate_legacy_manifest(raw: bytes, layer_sizes: dict[str, int]) -> bytes:
    """Rewrite a v4.1.0 ``{"layers": ["sha256:..."]}`` manifest into the v4.2+ schema.
    Sizes must be supplied from verified blobs; unknown sizes fail closed."""
    doc = json.loads(raw)
    layers = doc.get("layers")
    if not isinstance(layers, list) or not all(isinstance(x, str) for x in layers):
        raise IntegrityError("not a legacy manifest")
    try:
        entries = [{"digest": d, "size": layer_sizes[d]} for d in layers]
    except KeyError as exc:
        raise IntegrityError(f"size unknown for {exc.args[0]}") from None
    return json.dumps({"schemaVersion": 1, "mediaType": MANIFEST_MEDIA_TYPE, "layers": entries},
                      sort_keys=True, separators=(",", ":")).encode()


__all__ = ["migrate_store_meta", "migrate_legacy_manifest", "SchemaTooNew", "digest"]
