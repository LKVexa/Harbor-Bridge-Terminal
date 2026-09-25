"""Write the canonical JSON Schemas to schemas/ (MC-012).  ``--check`` exits 1 on drift."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from inv62_edge_topology.production import config, errors, wire  # noqa: E402


def documents() -> dict[str, dict]:
    docs = {f"{name.lower()}.request.schema.json": schema for name, schema in wire.REQUEST_SCHEMAS.items()}
    docs["pk_topo.response.schema.json"] = wire.RESPONSE_SCHEMA
    docs["config.schema.json"] = config.CONFIG_SCHEMA
    docs["error-codes.json"] = {
        "title": "INV-62 stable error code registry",
        "codes": {c: {"outcome": e.outcome.value, "http_status": e.http_status, "description": e.description}
                  for c, e in sorted(errors.registry().items())},
        "outcomes": [o.value for o in errors.Outcome],
        "limits": {"max_payload_bytes": wire.MAX_PAYLOAD_BYTES, "max_json_depth": wire.MAX_JSON_DEPTH,
                   "max_mutations_per_apply": wire.MAX_MUTATIONS_PER_APPLY, "max_candidates": wire.MAX_CANDIDATES,
                   "max_deadline_ms": wire.MAX_DEADLINE_MS, "default_deadline_ms": wire.DEFAULT_DEADLINE_MS},
        "versions": {k: list(v) for k, v in wire.SUPPORTED.items()},
        "features": {k: sorted(v) for k, v in wire.FEATURES.items()},
    }
    return docs


def main(argv: list[str]) -> int:
    out = ROOT / "schemas"
    out.mkdir(exist_ok=True)
    drift = []
    for name, doc in documents().items():
        text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
        path = out / name
        if "--check" in argv:
            if not path.exists() or path.read_text() != text:
                drift.append(name)
        else:
            path.write_text(text)
    if drift:
        print("schema drift:", ", ".join(drift))
        return 1
    print("schemas", "in sync" if "--check" in argv else "written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
