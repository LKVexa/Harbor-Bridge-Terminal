"""The bill of lading: the ship's registry, rebuilt from disk, never appended."""

from __future__ import annotations

import datetime as _dt
from . import strictjson as json
import os
from typing import Any, Dict, List

from . import UC_RELEASE, NODE_IDS, NODE_CONTAINER, SLOTS
from . import ucmanifest as M
from . import engines as E
from . import safety as SAFE

SCHEMA = "UC/BILL_OF_LADING/1"


def registry_path() -> str:
    return os.path.join(E.ship_root(), "registry", "BILL_OF_LADING.json")


def scan() -> Dict[str, Any]:
    """Every berth on disk, from its own BERTH.json and seals."""
    bdir = os.path.join(E.ship_root(), "berths")
    berths: List[dict] = []
    if os.path.isdir(bdir):
        for name in sorted(os.listdir(bdir)):
            SAFE.validate_name(name)
            d = SAFE.contained_path(E.ship_root(), "berths/" + name)
            bj = os.path.join(d, "BERTH.json")
            if not os.path.isdir(d) or not os.path.isfile(bj):
                continue
            rec = json.load(open(bj, encoding="utf-8"))
            sums = os.path.join(d, "SHA256SUMS.txt")
            entry = {
                "berth": name, "kind": rec.get("kind"), "loaded_utc": rec.get("loaded_utc"),
                "source": {k: rec.get("source", {}).get(k) for k in ("kind", "path", "sha256", "tree_sha256", "bytes", "files")},
                "scripts": rec.get("scripts"), "bytes": rec.get("bytes"),
                "per_node": {n: {"count": rec["per_node"][n]["count"], "bytes": rec["per_node"][n]["bytes"],
                                 "tree_sha256": rec["per_node"][n]["tree_sha256"]} for n in NODE_IDS if n in rec.get("per_node", {})},
                "seals": rec.get("seals"), "reference_witnesses": rec.get("reference_witnesses"),
                "cargo_segments_of_84": rec.get("cargo_segments_of_84"),
                "studio_face": rec.get("studio_face"),
                "fabric": {"available": (rec.get("fabric") or {}).get("available"),
                           "containers": sorted((rec.get("fabric") or {}).get("containers") or {}),
                           "genesis_blob_sha256": {k: v.get("genesis_blob_sha256") for k, v in ((rec.get("fabric") or {}).get("containers") or {}).items()},
                           "hull_face_image": ((rec.get("fabric") or {}).get("hull_face") or {}).get("image")},
                "hull_cargo": [m.get("name") for m in (rec.get("hull_cargo") or []) if m.get("name")],
                "sums_sha256": M.sha256_file(sums) if os.path.isfile(sums) else None,
                "slots_present": [s for s in SLOTS if os.path.isdir(os.path.join(d, s))],
            }
            berths.append(entry)
    return {"schema": SCHEMA, "uc_release": UC_RELEASE, "berths": berths, "berth_count": len(berths),
            "totals": {"scripts": sum(b["scripts"] or 0 for b in berths), "bytes": sum(b["bytes"] or 0 for b in berths),
                       "per_node": {n: sum((b["per_node"].get(n) or {}).get("count", 0) for b in berths) for n in NODE_IDS}},
            "engines": {n: f"hold/{NODE_CONTAINER[n]}.zip" for n in NODE_IDS},
            "rule": "rebuilt from disk on every change, never appended to; it cannot describe a berth that is no longer there"}


def write() -> Dict[str, Any]:
    """Rebuild the bill of lading from disk. Idempotent: if the scan equals what is on disk
    (everything but `written_utc`), the files are left byte-identical -- so BUILD and VERIFY
    on a sealed ship never disturb its SHA256SUMS/MANIFEST; only a real change re-writes it."""
    reg = scan()
    p = registry_path()
    if os.path.isfile(p):
        try:
            old = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            old = None
        if old and compare(old, reg)["identical"] and os.path.isfile(os.path.join(os.path.dirname(p), "BILL_OF_LADING.md")):
            return old
    reg["written_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    SAFE.atomic_json(p, reg)
    SAFE.atomic_write(os.path.join(os.path.dirname(p), "BILL_OF_LADING.md"), as_md(reg))
    return reg


def as_md(reg: Dict[str, Any]) -> str:
    lines = [f"# Bill of lading -- {UC_RELEASE}", "",
             f"{reg['berth_count']} berth(s), {reg['totals']['scripts']} scripts, {reg['totals']['bytes']} bytes. "
             f"Per node: " + ", ".join(f"{n} {reg['totals']['per_node'][n]}" for n in NODE_IDS) + ".", "",
             "| berth | kind | scripts | bytes | N_SMALL | N_MEDIUM | N_LARGE | N_XLARGE | CARGO.pal witness | BERTH.pal witness (studio R2) | segments | .tif fabrics | hull cargo |",
             "|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---|"]
    for b in reg["berths"]:
        pn = b["per_node"]
        fab = b.get("fabric") or {}
        nfab = (len(fab.get("containers") or []) + (1 if fab.get("hull_face_image") else 0)) if fab.get("available") else 0
        lines.append(f"| `{b['berth']}` | {b['kind']} | {b['scripts']} | {b['bytes']} | {pn.get('N_SMALL', {}).get('count', 0)} | "
                     f"{pn.get('N_MEDIUM', {}).get('count', 0)} | {pn.get('N_LARGE', {}).get('count', 0)} | {pn.get('N_XLARGE', {}).get('count', 0)} | "
                     f"`{(b['reference_witnesses'] or {}).get('CARGO.pal')}` | `{(b['reference_witnesses'] or {}).get('BERTH.pal')}` | {b['cargo_segments_of_84']} | {nfab} | "
                     f"{', '.join(f'`{n}`' for n in (b.get('hull_cargo') or [])) or '-'} |")
    lines.append("")
    lines.append("`.tif fabrics` counts the containers with their own fabric image (the five DF containers + the hull face); "
                 "`hull cargo` names the studio containers a berth carries broken up (BUILD re-assembles and mounts them in the hull with their own pictures). "
                 "Rebuilt from disk on every change; `uc verify` compares this file with a fresh scan.")
    return "\n".join(lines) + "\n"


def compare(reg_on_disk: Dict[str, Any], fresh: Dict[str, Any]) -> Dict[str, Any]:
    strip = lambda r: {k: v for k, v in r.items() if k not in ("written_utc",)}
    a, b = strip(reg_on_disk), strip(fresh)
    return {"identical": json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
            "berths_on_disk": [x["berth"] for x in fresh["berths"]],
            "berths_registered": [x["berth"] for x in reg_on_disk.get("berths", [])]}
