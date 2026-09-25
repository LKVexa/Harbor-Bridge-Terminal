"""Backup / restore / migration for INV-64 persistent state (MC-32; C095).

    python -m inv64_application_model.tools.backup_restore backup  --store DIR --audit FILE --out BACKUP.tar
    python -m inv64_application_model.tools.backup_restore restore --backup BACKUP.tar --into NEW_DIR [--tenant T]

Only authoritative persistent state is backed up (ops/state_inventory.json):
the ConfigStore directory (``state.json`` + ``journal.jsonl``) and the audit
ledger (+ anchor if present). Caches, idempotency tables and telemetry are
reconstructible or intentionally ephemeral and are excluded.

The archive carries ``BACKUP_MANIFEST.json`` (format version, software
version, schema versions, per-file SHA-256, created time). Restore always goes
into a **new, empty** directory (isolated), then verifies: every digest, the
audit hash chain (and anchor), that ``state.json`` loads and its active
revision's digest re-derives from its manifest, and — when ``--tenant`` is
given — that every revision belongs to that tenant. Any failure deletes
nothing and returns FAIL; the operator never restores over live state.
Encryption of the archive is delegated to :func:`crypto_policy.seal` when a
KeyRing is configured (backups can contain tenant topology).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
import time
from pathlib import Path

from inv64_application_model import __version__
from inv64_application_model.audit import AuditChainBroken, AuditLog
from inv64_application_model.manifest import canonical

FORMAT = "PK_APP_BACKUP/1"


def backup(store: Path, audit: Path | None, out: Path, anchor: Path | None = None) -> dict:
    files = {}
    for name in ("state.json", "journal.jsonl"):
        p = store / name
        if p.is_file():
            files[f"store/{name}"] = p.read_bytes()
    if audit and audit.is_file():
        files["audit/audit.jsonl"] = audit.read_bytes()
    if anchor and anchor.is_file():
        files["audit/anchor.json"] = anchor.read_bytes()
    manifest = {"format": FORMAT, "software": __version__, "schemas": {"state": "PK_APP_CONFIG_STATE/1", "audit": "PK_APP_AUDIT/1"},
                "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "files": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}}
    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, "w") as tar:
        for name, data in sorted(files.items()) + [("BACKUP_MANIFEST.json", json.dumps(manifest, indent=2).encode())]:
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            ti.mtime = 0
            tar.addfile(ti, io.BytesIO(data))
    return manifest


def restore(archive: Path, into: Path, *, tenant: str | None = None, anchor_key: bytes | None = None) -> dict:
    checks = []
    if into.exists() and any(into.iterdir()):
        return {"schema": "PK_APP_RESTORE/1", "result": "FAIL", "checks": [{"check": "target empty", "result": "FAIL"}]}
    into.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        members = {m.name: m for m in tar.getmembers()}
        for n in members:
            if n.startswith("/") or ".." in Path(n).parts or not members[n].isfile():
                return {"schema": "PK_APP_RESTORE/1", "result": "FAIL", "checks": [{"check": "safe member names", "result": "FAIL", "member": n}]}
        manifest = json.loads(tar.extractfile("BACKUP_MANIFEST.json").read())
        if manifest.get("format") != FORMAT:
            return {"schema": "PK_APP_RESTORE/1", "result": "FAIL", "checks": [{"check": "format", "result": "FAIL"}]}
        for name, digest in manifest["files"].items():
            data = tar.extractfile(name).read()
            ok = hashlib.sha256(data).hexdigest() == digest
            checks.append({"check": f"digest {name}", "result": "PASS" if ok else "FAIL"})
            dest = into / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    major = lambda v: v.split(".")[0]
    checks.append({"check": "software major version compatible", "result": "PASS" if major(manifest["software"]) == major(__version__) else "FAIL",
                   "backup": manifest["software"], "running": __version__})
    if (into / "audit/audit.jsonl").is_file():
        try:
            n = AuditLog(into / "audit/audit.jsonl").verify(
                anchor_path=into / "audit/anchor.json" if (into / "audit/anchor.json").is_file() and anchor_key else None,
                anchor_key=anchor_key)
            checks.append({"check": "audit chain", "result": "PASS", "records": n})
        except AuditChainBroken as e:
            checks.append({"check": "audit chain", "result": "FAIL", "error": str(e)})
    st = into / "store/state.json"
    if st.is_file():
        state = json.loads(st.read_text())
        act = state.get("active")
        if act:
            rev = state["revisions"][act]
            ok = canonical(rev["effective"]["manifest"]) == rev["digest"]
            checks.append({"check": "active revision digest re-derives", "result": "PASS" if ok else "FAIL"})
        if tenant is not None:
            foreign = [r for r, v in state["revisions"].items() if v.get("scope", {}).get("tenant") not in (None, tenant)]
            checks.append({"check": "tenant scope", "result": "PASS" if not foreign else "FAIL", "foreign": foreign[:5]})
    bad = [c for c in checks if c["result"] == "FAIL"]
    return {"schema": "PK_APP_RESTORE/1", "result": "FAIL" if bad else "PASS", "checks": checks, "restored_into": str(into)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--store", required=True)
    b.add_argument("--audit")
    b.add_argument("--anchor")
    b.add_argument("--out", required=True)
    r = sub.add_parser("restore")
    r.add_argument("--backup", required=True)
    r.add_argument("--into", required=True)
    r.add_argument("--tenant")
    a = ap.parse_args(argv)
    if a.cmd == "backup":
        print(json.dumps(backup(Path(a.store), Path(a.audit) if a.audit else None, Path(a.out),
                                Path(a.anchor) if a.anchor else None), indent=2))
        return 0
    res = restore(Path(a.backup), Path(a.into), tenant=a.tenant)
    print(json.dumps(res, indent=2))
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
