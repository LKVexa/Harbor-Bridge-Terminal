"""Backup / restore / migration tooling (GAP04-C41).

``backup`` produces an encrypted, integrity-checked archive of a node's durable
state (journal + keyring + generation) with a manifest of SHA-256 digests. The
archive key is derived from an operator passphrase with scrypt (n=2**15, r=8,
p=1) and the archive is sealed with AES-256-GCM. ``restore`` refuses a
non-empty target, verifies every digest, re-verifies the journal hash chain
with the restored audit key, and bumps the generation so a restored node
fences any still-running original (split-brain safety).

CLI:  python -m gap04_disconnected_operation_controller.runtime.backup backup <state_dir> <out.bak>
      python -m gap04_disconnected_operation_controller.runtime.backup restore <in.bak> <empty_dir>
      (passphrase from $GAP04_BACKUP_PASSPHRASE)
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tarfile
from pathlib import Path

from . import crypto
from .errors import Gap04Error
from .journal import Journal
from .storage import FileKeyProvider, Keyring, atomic_write

BACKUP_VERSION = "PK_GAP04_BACKUP/1"
FILES = ("journal/journal.wal", "keys.json", "generation.json")


def _kdf(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase) < 12:
        raise Gap04Error("backup passphrase must be >= 12 characters", code="GAP04-E0004")
    return hashlib.scrypt(passphrase.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


def backup(state_dir: Path, out: Path, passphrase: str) -> dict:
    state_dir = Path(state_dir)
    buf = io.BytesIO()
    manifest = {"version": BACKUP_VERSION, "files": {}}
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for rel in FILES:
            p = state_dir / rel
            if not p.exists():
                continue
            data = p.read_bytes()
            manifest["files"][rel] = hashlib.sha256(data).hexdigest()
            ti = tarfile.TarInfo(rel); ti.size = len(data); ti.mode = 0o600
            tar.addfile(ti, io.BytesIO(data))
        m = json.dumps(manifest, sort_keys=True).encode()
        ti = tarfile.TarInfo("MANIFEST.json"); ti.size = len(m)
        tar.addfile(ti, io.BytesIO(m))
    salt = os.urandom(16)
    blob = crypto.aead_encrypt(_kdf(passphrase, salt), buf.getvalue(), BACKUP_VERSION.encode())
    atomic_write(Path(out), BACKUP_VERSION.encode() + b"\n" + salt + blob)
    return manifest


def restore(archive: Path, target: Path, passphrase: str) -> dict:
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        raise Gap04Error("restore target must be empty", code="GAP04-E0004")
    raw = Path(archive).read_bytes()
    head, _, rest = raw.partition(b"\n")
    if head.decode() != BACKUP_VERSION:
        raise Gap04Error("unsupported backup version", code="GAP04-E0404")
    plain = crypto.aead_decrypt(_kdf(passphrase, rest[:16]), rest[16:], BACKUP_VERSION.encode())
    with tarfile.open(fileobj=io.BytesIO(plain)) as tar:
        members = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    manifest = json.loads(members.pop("MANIFEST.json"))
    for rel, digest in manifest["files"].items():
        if rel not in FILES or hashlib.sha256(members[rel]).hexdigest() != digest:
            raise Gap04Error("backup member digest mismatch", code="GAP04-E0403", details={"file": rel})
    (target / "journal").mkdir(parents=True, exist_ok=True)
    for rel, data in members.items():
        atomic_write(target / rel, data)
    kr = Keyring.open(FileKeyProvider(target / "keys.json"))
    j = Journal(target / "journal", kr, generation=lambda: 0, encrypt=True)  # verifies chain + MACs
    gen = json.loads((target / "generation.json").read_text())["generation"] if (target / "generation.json").exists() else 0
    atomic_write(target / "generation.json", json.dumps({"generation": gen + 1, "owner": "restore"}).encode())
    return {"restored_seq": j.seq, "head": j.head, "generation": gen + 1}


if __name__ == "__main__":  # pragma: no cover
    pw = os.environ.get("GAP04_BACKUP_PASSPHRASE", "")
    cmd, a, b = sys.argv[1:4]
    print(json.dumps(backup(Path(a), Path(b), pw) if cmd == "backup" else restore(Path(a), Path(b), pw), indent=2))
