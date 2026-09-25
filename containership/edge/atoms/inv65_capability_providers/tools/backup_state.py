"""Backup / restore / reconstruction tooling for durable link state (M35).

backup:  compacts, then writes a self-verifying archive
         {"format":"PK_INV65_BACKUP/1","seq","snapshot","sha256"}.
restore: verifies the archive, refuses to restore an older seq over newer
         state (unless --force-older), and ALWAYS re-applies the live store's
         tombstones so a restore can never resurrect a revoked link.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    __package__ = "inv65_capability_providers.tools"

from ..state.store import LinkStateStore, _ck  # noqa: E402


def backup(store: LinkStateStore, out: str) -> dict:
    store.compact()
    snap = store.snapshot_body()
    snap["checksum"] = _ck(snap)
    doc = {"format": "PK_INV65_BACKUP/1", "seq": snap["seq"], "snapshot": snap}
    doc["sha256"] = hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, out)
    return {"seq": doc["seq"], "sha256": doc["sha256"], "links": len(snap["links"])}


def load_backup(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    want = doc.pop("sha256", None)
    if doc.get("format") != "PK_INV65_BACKUP/1" or want != hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest():
        raise ValueError("backup integrity check failed")
    return doc


def restore(path: str, root: str, *, force_older: bool = False, keyring=None) -> dict:
    doc = load_backup(path)
    live_revoked: dict = {}
    live_seq = 0
    if os.path.exists(os.path.join(root, "snapshot.json")) or os.path.exists(os.path.join(root, "wal.jsonl")):
        live = LinkStateStore(root, keyring=keyring)
        live_revoked, live_seq = dict(live.revoked), live.seq
    snap = doc["snapshot"]
    if snap["seq"] < live_seq and not force_older:
        raise ValueError(f"backup seq {snap['seq']} older than live seq {live_seq}; use force_older")
    body = {k: v for k, v in snap.items() if k != "checksum"}
    resurrect = 0
    for k, ver in live_revoked.items():  # tombstones win over any older backup
        if k in body["links"]:
            body["links"].pop(k)
            resurrect += 1
        body["revoked"][k] = max(ver, body["revoked"].get(k, 0))
    body["seq"] = max(body["seq"], live_seq) + 1
    body["checksum"] = _ck(body)
    os.makedirs(root, exist_ok=True)
    tmp = os.path.join(root, "snapshot.json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(body, fh, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, os.path.join(root, "snapshot.json"))
    open(os.path.join(root, "wal.jsonl"), "wb").close()
    return {"restored_seq": body["seq"], "links": len(body["links"]), "blocked_resurrections": resurrect}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup"); b.add_argument("root"); b.add_argument("out")
    r = sub.add_parser("restore"); r.add_argument("archive"); r.add_argument("root"); r.add_argument("--force-older", action="store_true")
    v = sub.add_parser("verify"); v.add_argument("archive")
    a = ap.parse_args(argv)
    if a.cmd == "backup":
        print(json.dumps(backup(LinkStateStore(a.root), a.out)))
    elif a.cmd == "restore":
        print(json.dumps(restore(a.archive, a.root, force_older=a.force_older)))
    else:
        d = load_backup(a.archive); print(json.dumps({"ok": True, "seq": d["seq"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
