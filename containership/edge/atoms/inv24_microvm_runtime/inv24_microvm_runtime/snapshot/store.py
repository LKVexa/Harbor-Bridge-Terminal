"""INV-26 snapshot metadata, validation and crash-consistent storage (MC-004).

Crash-consistency protocol for ``commit``:

1. guest is paused by the caller (adapter ``PATCH /vm {"state":"Paused"}``);
2. memory + VM-state files are written by the VMM into ``<id>.partial/``;
3. every file is fsync'd and hashed;
4. metadata with ``complete: true`` is written to ``meta.json.tmp``, fsync'd,
   then the directory is atomically renamed ``<id>.partial -> <id>`` and the
   parent directory fsync'd;
5. the guest is resumed.

A crash at any point leaves either no ``<id>`` directory or a complete one;
``*.partial`` directories are never loadable and are garbage-collected.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import time
from typing import Final

from ..errors import Inv24Error
from ..schemas import validate
from ..security.artifacts import sha256_file

SUPPORTED_RUNTIME_MAJOR: Final[str] = "4"


def _fsync_dir(path: pathlib.Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class SnapshotStore:
    def __init__(self, root: str, *, runtime_version: str, firecracker_version: str,
                 supported_firecracker: frozenset[str], arch: str, cpu_features: frozenset[str]) -> None:
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.runtime_version, self.fc_version = runtime_version, firecracker_version
        self.supported_fc, self.arch, self.cpu_features = supported_firecracker, arch, cpu_features

    def begin(self, snapshot_id: str) -> pathlib.Path:
        if not snapshot_id.replace("-", "").isalnum() or len(snapshot_id) > 64:
            raise Inv24Error("SNAPSHOT_INVALID", "snapshot id must be alphanumeric/dash <= 64")
        if (self.root / snapshot_id).exists():
            raise Inv24Error("SNAPSHOT_INVALID", "snapshot id already committed")
        partial = self.root / f"{snapshot_id}.partial"
        shutil.rmtree(partial, ignore_errors=True)
        partial.mkdir()
        return partial

    def commit(self, snapshot_id: str, *, tenant: str, workload: str, devices: list[str],
               kernel_sha256: str, rootfs_sha256: str, ownership_epoch: int) -> dict:
        partial = self.root / f"{snapshot_id}.partial"
        mem, state = partial / "memory.bin", partial / "vmstate.bin"
        for f in (mem, state):
            if not f.is_file() or f.stat().st_size == 0:
                raise Inv24Error("SNAPSHOT_INVALID", f"{f.name} missing or empty")
            with open(f, "rb+") as fh:
                os.fsync(fh.fileno())
        meta = {"schema": "PK_MICROVM_SNAPSHOT/1", "snapshot_id": snapshot_id,
                "runtime_version": self.runtime_version, "firecracker_version": self.fc_version,
                "arch": self.arch, "cpu_features": sorted(self.cpu_features),
                "kernel_sha256": kernel_sha256, "rootfs_sha256": rootfs_sha256,
                "devices": sorted(devices), "tenant": tenant, "workload": workload,
                "memory_sha256": sha256_file(mem), "state_sha256": sha256_file(state),
                "ownership_epoch": ownership_epoch,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "complete": True}
        validate(meta)
        tmp = partial / "meta.json.tmp"
        with open(tmp, "w") as fh:
            json.dump(meta, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, partial / "meta.json")
        _fsync_dir(partial)
        os.replace(partial, self.root / snapshot_id)
        _fsync_dir(self.root)
        return meta

    def validate_for_restore(self, snapshot_id: str, *, tenant: str, workload: str,
                             current_epoch: int, device_model: frozenset[str]) -> dict:
        d = self.root / snapshot_id
        if not d.is_dir() or d.name.endswith(".partial"):
            raise Inv24Error("SNAPSHOT_INVALID", "snapshot not committed")
        try:
            meta = json.loads((d / "meta.json").read_text())
        except (OSError, ValueError):
            raise Inv24Error("SNAPSHOT_INVALID", "metadata missing or corrupt") from None
        validate(meta, "PK_MICROVM_SNAPSHOT/1")
        if meta["tenant"] != tenant or meta["workload"] != workload:
            raise Inv24Error("TENANT_MISMATCH", "snapshot belongs to another tenant/workload")
        if meta["ownership_epoch"] < current_epoch:
            raise Inv24Error("STALE_EPOCH", "snapshot taken under a superseded ownership epoch")
        if meta["runtime_version"].split(".")[0] != SUPPORTED_RUNTIME_MAJOR:
            raise Inv24Error("SNAPSHOT_INCOMPATIBLE", "runtime major version mismatch")
        if meta["firecracker_version"] not in self.supported_fc:
            raise Inv24Error("SNAPSHOT_INCOMPATIBLE", "Firecracker version not supported for restore")
        if meta["arch"] != self.arch or not set(meta["cpu_features"]) <= self.cpu_features:
            raise Inv24Error("SNAPSHOT_INCOMPATIBLE", "architecture/CPU feature mismatch")
        if not set(meta["devices"]) <= device_model:
            raise Inv24Error("SNAPSHOT_INCOMPATIBLE", "snapshot device model not permitted")
        for fname, key in (("memory.bin", "memory_sha256"), ("vmstate.bin", "state_sha256")):
            p = d / fname
            if not p.is_file() or sha256_file(p) != meta[key]:
                raise Inv24Error("SNAPSHOT_INVALID", f"{fname} missing, truncated or modified")
        return meta

    def gc_partials(self) -> list[str]:
        removed = []
        for p in self.root.glob("*.partial"):
            shutil.rmtree(p, ignore_errors=True)
            removed.append(p.name)
        return removed
