"""Backup, restore and reconstruction tooling (MC-063).

``backup(store_dir, dest)`` copies a *consistent* image of the store while
holding the store's writer lock (appends block for the copy's duration), then
writes ``BACKUP_MANIFEST.json`` with the SHA-256 of every file, the chain head
and the anchor count.  ``restore(backup_dir, store_dir)`` verifies the manifest,
copies into an empty target, drops the lease (the restored site must win a
fresh lease with a higher epoch) and verifies the hash chain and anchors.

Reconstruction: state is always derivable from the journal (snapshot +
records), so a restored store *is* a restored control plane once
``ControlPlaneService`` replays it.  Migration between store formats is done by
replaying records through the reducer into a new store (see RUNBOOKS.md §8).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil

from .store import JournalStore


def _files(root: pathlib.Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name not in (".lock", "lease.json", "BACKUP_MANIFEST.json") and ".tmp" not in p.name:
            yield p


def backup(store_dir: str | os.PathLike, dest: str | os.PathLike, anchor_key: bytes) -> dict:
    src, dst = pathlib.Path(store_dir), pathlib.Path(dest)
    dst.mkdir(parents=True, exist_ok=False)
    probe = JournalStore(src, "backup-probe", anchor_key=anchor_key, fsync=False)
    lk = probe._flock()
    try:
        probe._open()
        files = {}
        for p in _files(src):
            rel = p.relative_to(src)
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst / rel)
            files[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest = {"schema": "PK_ECP_BACKUP/1", "head_sequence": probe.head_seq, "head_hash": probe.head_hash,
                    "files": files}
    finally:
        probe._funlock(lk)
    (dst / "BACKUP_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def restore(backup_dir: str | os.PathLike, store_dir: str | os.PathLike, anchor_key: bytes) -> dict:
    src, dst = pathlib.Path(backup_dir), pathlib.Path(store_dir)
    manifest = json.loads((src / "BACKUP_MANIFEST.json").read_text())
    for rel, h in manifest["files"].items():
        if hashlib.sha256((src / rel).read_bytes()).hexdigest() != h:
            raise ValueError(f"backup file {rel} does not match manifest")
    if dst.exists() and any(dst.iterdir()):
        raise ValueError("restore target must be empty")
    for rel in manifest["files"]:
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, dst / rel)
    store = JournalStore(dst, "restore-verify", anchor_key=anchor_key, fsync=False)
    ok, detail = store.verify_all()
    aok, adetail = store.verify_anchors()
    if not ok or not aok or store.head_hash != manifest["head_hash"]:
        raise ValueError(f"restored store failed verification: {detail}; {adetail}")
    return {"head_sequence": store.head_seq, "verified": detail, "anchors": adetail}
