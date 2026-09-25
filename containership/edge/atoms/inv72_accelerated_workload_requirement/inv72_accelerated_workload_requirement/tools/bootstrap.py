"""Deterministic day-0 bootstrap (C040).

    python -B -m inv72_accelerated_workload_requirement.tools.bootstrap --profile datacenter
        [--journal PATH] [--overlay FILE ...] [--inventory FILE --inventory-key-hex HEX]

From an empty environment: validate + activate the profile (generation 1) -> wire discovery -> refresh ->
recover or create the reservation journal -> print PK_ACCEL_STATUS/1.  Exit 0 only if ready.
Without --inventory a built-in two-device demo inventory signed with an in-process demo key is used and
the output says ``"demo": true`` - that path proves the bootstrap sequence, not a deployment.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

from .. import config, discovery, service, state, telemetry
from ..adapters import Gap02Publisher


def run(profile: str, journal: str | None = None, overlays: tuple = (), inventory: str | None = None,
        inventory_key: bytes | None = None) -> tuple[int, dict]:
    cs = config.ConfigStore()
    cfg = config.compose(profile, *[json.loads(Path(o).read_text()) for o in overlays])
    cs.activate(cfg, author=os.environ.get("USER", "bootstrap"), reason="day-0 bootstrap",
                sources=(f"config/profiles/{profile}.json",) + tuple(overlays))
    demo = inventory is None
    if demo:
        inventory_key = os.urandom(32)
        pub = Gap02Publisher("bootstrap-demo", inventory_key,
                             [{"dev_id": "demo0", "cls": "gpu-large", "mem_gb": 80, "node": "n0", "link_group": "l0"},
                              {"dev_id": "demo1", "cls": "gpu-large", "mem_gb": 80, "node": "n0", "link_group": "l0"}])
        src = discovery.Source("bootstrap-demo", pub.publish, inventory_key)
    else:
        snap = json.loads(Path(inventory).read_text())
        src = discovery.Source(snap["source"], lambda: snap, inventory_key)
    inv = discovery.InventoryCache([src], max_age_s=cfg["inventory_max_age_s"],
                                   offline_grace_s=cfg["offline_grace_s"], require_mac=cfg["require_inventory_mac"])
    inv.refresh()
    store = (state.ReservationStore.recover(Path(journal)) if journal and Path(journal).exists()
             else state.ReservationStore(journal_path=Path(journal) if journal else None))
    svc = service.AcceleratorService(cs, inv, store, auth=None, logger=telemetry.Logger(stream=io.StringIO()))
    st = svc.status()
    st["demo"] = demo
    st["note"] = ("authentication is wired by the host KeyProvider; bootstrap checks readiness only"
                  if cfg.get("require_authentication", True) else "far-edge anonymous mode")
    return (0 if st["ready"] else 1), st


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=config.TIERS)
    ap.add_argument("--journal")
    ap.add_argument("--overlay", action="append", default=[])
    ap.add_argument("--inventory")
    ap.add_argument("--inventory-key-hex")
    a = ap.parse_args(argv)
    code, st = run(a.profile, a.journal, tuple(a.overlay), a.inventory,
                   bytes.fromhex(a.inventory_key_hex) if a.inventory_key_hex else None)
    print(json.dumps(st, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
