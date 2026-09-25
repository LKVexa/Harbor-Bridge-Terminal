"""Deterministic bootstrap (MC-030).

    python -m inv62_edge_topology.production.bootstrap \
        --config config.json [--overlay env.json ...] --secrets-dir DIR \
        --seed topology.json --tenant TENANT --state-dir DIR [--report out.json]

Steps (each fails closed and exits non-zero):
 1. compose config (defaults <- base <- overlays) and validate before activation
 2. start the service with a fresh or existing state directory (recovery runs)
 3. mint a short-lived bootstrap feed credential from the active key
 4. apply the seed graph atomically through PK_TOPO_GRAPH/1 (same path as production)
 5. verify readiness and that every seed node is present
 6. write a report with config digest, graph revision and snapshot digest
Running twice with the same inputs is idempotent: already-present nodes are skipped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from . import config as cfgmod, errors
from .client import Client
from .service import TopologyService


def run(config_doc: dict[str, Any], overlays: list[dict[str, Any]], secrets: cfgmod.SecretProvider,
        seed: dict[str, Any], tenant: str, state_dir: str | None) -> dict[str, Any]:
    effective = cfgmod.compose(config_doc, *overlays)
    svc = TopologyService(secrets, state_dir=state_dir)
    active = svc.config.active
    prov = svc.activate_config(effective, author="bootstrap", source="bootstrap",
                               expected_generation=active.provenance.generation if active else None)
    feed = Client(svc.handle, tenant, lambda: svc.authn.issue("bootstrap", "topology-feed", [tenant], lifetime_s=60))
    existing: set[str] = set()
    try:
        existing = set(feed.get()["result"]["nodes"])
    except errors.TopoError as exc:
        if exc.code != errors.UNKNOWN_NODE.code:
            raise
    graph = cfgmod.deep_merge({"nodes": {}, "links": []}, seed)
    order = {"cloud": 0, "region": 1, "site": 2, "device": 3}
    muts: list[dict[str, Any]] = []
    for name, meta in sorted(graph["nodes"].items(), key=lambda kv: (order.get(kv[1].get("tier"), 9), kv[0])):
        if name in existing:
            continue
        m = {"kind": "add_node", "node": name, "tier": meta["tier"], "caps": sorted(meta.get("caps", []))}
        for k in ("site", "parent", "residency"):
            if meta.get(k):
                m[k] = meta[k]
        muts.append(m)
    for link in graph["links"]:
        muts.append({"kind": "connect", "a": link["a"], "b": link["b"], "latency_ms": link["latency_ms"],
                     "up": link.get("up", True)})
    revision = None
    if muts:
        revision = feed.apply(muts)["revision"]
    health = svc.health()
    snap = feed.get()["result"]
    missing = sorted(set(graph["nodes"]) - set(snap["nodes"]))
    if not health["ready"] or missing:
        raise SystemExit(f"bootstrap verification failed: ready={health['ready']} missing={missing}")
    svc.checkpoint()
    return {"ok": True, "config_generation": prov.generation, "config_digest": prov.digest, "revision": revision,
            "nodes": len(snap["nodes"]), "links": len(snap["links"]),
            "snapshot_sha256": hashlib.sha256(json.dumps(snap, sort_keys=True).encode()).hexdigest(),
            "release": health["release"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv62-bootstrap")
    ap.add_argument("--config", required=True)
    ap.add_argument("--overlay", action="append", default=[])
    ap.add_argument("--secrets-dir", required=True)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--state-dir")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    load = lambda p: json.loads(Path(p).read_text())
    try:
        report = run(load(a.config), [load(p) for p in a.overlay], cfgmod.FileSecretProvider(a.secrets_dir),
                     load(a.seed), a.tenant, a.state_dir)
    except errors.TopoError as exc:
        print(json.dumps({"ok": False, "error": exc.to_wire()}), file=sys.stderr)
        return 2
    out = json.dumps(report, indent=2, sort_keys=True)
    if a.report:
        Path(a.report).write_text(out + "\n")
    print(out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
