"""State schema migrations (M05/M35).  v1 (4.2.0 in-memory snapshot shape:
{"links": {"component|link": cfg}}) -> v2 (identity-scoped keys, tombstones)."""
from __future__ import annotations

import json

LEGACY_SCOPE = ["legacy", "default", "default", "default"]


def migrate_v1_to_v2(body: dict) -> dict:
    links = {}
    for k, cfg in body.get("links", {}).items():
        comp, _, name = k.partition("|")
        new_key = json.dumps(LEGACY_SCOPE + [comp, name or "default"], separators=(",", ":"))
        links[new_key] = {"config": cfg, "config_version": 1, "migrated_from": "v1"}
    return {"schema_version": 2, "seq": int(body.get("seq", 0)), "links": links, "revoked": {}}
