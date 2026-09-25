"""MC-042 - Backup / restore / migration tooling (GAP03-BACKUP/1).

backup(): snapshot every durable store under its own lock, copy snapshot +
WAL + archive into a tar with a per-file sha256 manifest and a store-level
chain head.  restore(): verify the manifest BEFORE unpacking into an empty
target, then open each store (which replays + verifies its hash chain) and
check invariants; reports RTO.  Never restores over a non-empty directory.
"""
from __future__ import annotations

from .canonical import readb

import hashlib
import io
import json
import os
import tarfile
import time

from .errors import SchedulerError


def backup(stores: dict, out_path: str, *, signer=None) -> dict:
    """Consistent multi-store backup.  Encryption at rest is NOT provided (stdlib has no approved cipher; see
    blocker BLK-CRYPTO); integrity + authenticity come from per-file sha256 and an Ed25519-signed manifest."""
    manifest = {"schema": "GAP03-BACKUP/1", "created": int(time.time()), "stores": {}}
    buf = {}
    for name, store in sorted(stores.items()):
        with store._lock:
            store.snapshot()
            files = {}
            for d, _, fs in os.walk(store.dir):
                for f in sorted(fs):
                    if f.endswith(".lock") or ".tmp-" in f:
                        continue
                    p = os.path.join(d, f)
                    rel = f"{name}/" + os.path.relpath(p, store.dir).replace(os.sep, "/")
                    data = readb(p)
                    buf[rel] = data
                    files[rel] = hashlib.sha256(data).hexdigest()
            manifest["stores"][name] = {"kind": store.KIND, "seq": store.seq, "head": store.head, "files": files}
    with tarfile.open(out_path, "w:gz") as tar:
        for rel, data in sorted(buf.items()):
            ti = tarfile.TarInfo(rel)
            ti.size, ti.mtime = len(data), 0
            tar.addfile(ti, io.BytesIO(data))
        if signer is not None:
            from .identity import sign_artifact
            manifest["signature"] = sign_artifact(signer, "backup_manifest", {k: v for k, v in manifest.items() if k != "signature"})
        m = json.dumps(manifest, sort_keys=True).encode()
        ti = tarfile.TarInfo("BACKUP_MANIFEST.json")
        ti.size = len(m)
        tar.addfile(ti, io.BytesIO(m))
    return manifest


def restore(archive: str, target: str, classes: dict, *, trust=None, dry_run: bool = False) -> dict:
    t0 = time.perf_counter()
    if not dry_run and os.path.exists(target) and os.listdir(target):
        raise SchedulerError("CONFLICT", "restore target is not empty")
    with tarfile.open(archive, "r:gz") as tar:
        members = {m.name: m for m in tar.getmembers()}
        if "BACKUP_MANIFEST.json" not in members:
            raise SchedulerError("INTEGRITY_FAILURE", "manifest missing")
        manifest = json.loads(tar.extractfile(members["BACKUP_MANIFEST.json"]).read())
        if manifest.get("schema") != "GAP03-BACKUP/1":
            raise SchedulerError("UNSUPPORTED_VERSION", "unknown backup schema")
        if trust is not None:
            from .identity import verify_artifact
            sig = manifest.get("signature")
            if not sig:
                raise SchedulerError("UNAUTHENTICATED", "backup manifest is unsigned")
            verify_artifact(trust, sig, {k: v for k, v in manifest.items() if k != "signature"}, kind="backup_manifest")
        for name, info in manifest["stores"].items():
            for rel, h in info["files"].items():
                if rel not in members or ".." in rel or rel.startswith("/"):
                    raise SchedulerError("INTEGRITY_FAILURE", f"missing/unsafe member {rel}")
                data = tar.extractfile(members[rel]).read()
                if hashlib.sha256(data).hexdigest() != h:
                    raise SchedulerError("INTEGRITY_FAILURE", f"digest mismatch {rel}")
        if dry_run:
            return {"dry_run": True, "verified": True, "stores": {n: {"kind": i["kind"], "seq": i["seq"], "files": len(i["files"])}
                                                                  for n, i in manifest["stores"].items()}, "manifest": manifest}
        for name, info in manifest["stores"].items():
            for rel in info["files"]:
                dst = os.path.join(target, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as fh:
                    fh.write(tar.extractfile(members[rel]).read())
    opened = {}
    for name, info in manifest["stores"].items():
        st = classes[name](os.path.join(target, name))
        if st.seq != info["seq"] or st.head != info["head"]:
            raise SchedulerError("INTEGRITY_FAILURE", f"{name}: restored head does not match backup")
        opened[name] = st
    return {"stores": opened, "rto_s": round(time.perf_counter() - t0, 4), "manifest": manifest}


RPO_RTO = {  # objectives per store (targets; achieved values are measured by restore rehearsals)
    "topology": {"class": "authoritative", "rpo_s": 0, "rto_s": 300},
    "ledger": {"class": "authoritative", "rpo_s": 0, "rto_s": 300},
    "txn": {"class": "authoritative", "rpo_s": 0, "rto_s": 300},
    "entitlement": {"class": "reconstructable (authority is upstream)", "rpo_s": 3600, "rto_s": 900},
    "config": {"class": "authoritative", "rpo_s": 0, "rto_s": 300},
    "controls": {"class": "authoritative", "rpo_s": 0, "rto_s": 120},
    "audit": {"class": "authoritative (security evidence)", "rpo_s": 0, "rto_s": 3600},
    "explain": {"class": "reconstructable/best-effort", "rpo_s": 86400, "rto_s": 86400},
    "lease": {"class": "ephemeral (re-elect)", "rpo_s": None, "rto_s": 30},
    "caches/latency": {"class": "ephemeral", "rpo_s": None, "rto_s": 0},
}
RESTORE_ORDER = ("controls", "config", "audit", "topology", "entitlement", "ledger", "txn", "explain")
