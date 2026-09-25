"""MC24 persistence migration framework, MC25 backup/restore/reseed workflow,
MC42 batch apply API, MC47 incident automation hooks.

Migration
---------
Snapshot state formats are versioned (``state_format``).  ``MIGRATIONS`` maps
``from_version -> (to_version, fn)``; ``migrate_snapshot_dir`` backs up every snapshot
before rewriting, applies the chain, re-validates, and refuses downgrades and unknown
versions.  Format 1 (v4.2.x reference shape: frontier keyed by bare key, no namespace,
no floors/guard) migrates to format 2 only when the caller names the tenant and
environment the legacy data belongs to - the migrator never guesses a namespace.

Backup / restore
----------------
``backup(node, dest)`` checkpoints, then copies snapshot + membership history + audit
(active and archived) with a manifest of sha256 digests and the signed audit head.
``restore(dest, into)`` verifies every digest and the audit chain before copying, and
the restored node starts in *recovery mode*: not ready and unable to author writes
until an anti-entropy reconcile with a live peer completes (stale-state fencing: its
counters may be behind what peers already hold).  If the restored replica was retired
meanwhile, membership fencing rejects its authorship and the operator must reseed.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .audit import AuditLedger
from .durable import SnapshotStore, atomic_write
from .errors import Gap05Error, IntegrityError, LimitExceeded
from .schemas import canonical_bytes, make_write_doc

LATEST_STATE_FORMAT = 2


def _v1_to_v2(state: dict, *, tenant: str, environment: str) -> dict:
    frontier = []
    for item in state["writes"]:
        frontier.append({"doc": make_write_doc(tenant=tenant, environment=environment, key=item["key"],
                                               value=item["value"], site=item["site"],
                                               vector=dict(item["vector"]), epoch=1)})
    return {"state_format": 2, "frontier": frontier, "floors": {}, "frozen": [],
            "guard": {"max_gap": 1024, "high": [], "seen": []}, "recent_ops": [],
            "discarded_counts": {}, "membership_epoch": 1, "migrated_from": 1}


MIGRATIONS = {1: (2, _v1_to_v2)}


def migrate_state(state: dict, **ctx) -> dict:
    version = state.get("state_format", 1)
    if version > LATEST_STATE_FORMAT:
        raise IntegrityError(f"state format {version} is newer than this build ({LATEST_STATE_FORMAT}); "
                             "downgrade is not supported", code="CORR_DOWNGRADE_REFUSED")
    while version < LATEST_STATE_FORMAT:
        if version not in MIGRATIONS:
            raise IntegrityError(f"no migration from state format {version}", code="CORR_NO_MIGRATION")
        nxt, fn = MIGRATIONS[version]
        state = fn(state, **ctx)
        if state.get("state_format") != nxt:
            raise IntegrityError("migration produced wrong format", code="CORR_MIGRATION_BAD")
        version = nxt
    return state


def migrate_snapshot_dir(snap_dir: Path, *, dry_run: bool = False, **ctx) -> list[dict]:
    store = SnapshotStore(snap_dir)
    report = []
    for gen, path in store._paths():
        body = store.validate(path)
        before = body["state"].get("state_format", 1)
        if before == LATEST_STATE_FORMAT:
            report.append({"generation": gen, "action": "none"})
            continue
        new_state = migrate_state(body["state"], **ctx)
        report.append({"generation": gen, "action": f"{before}->{new_state['state_format']}"})
        if not dry_run:
            backup = path.with_suffix(f".pre-migration-v{before}")
            shutil.copy2(path, backup)
            store.write(gen, body["wal_seq"], new_state)
            store.validate(path)
    return report


# ---------------------------------------------------------------- backup / restore
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def backup(node, dest: Path, *, membership_dir: Path) -> dict:
    dest = Path(dest)
    node.checkpoint()
    files = {}
    for src_root, name in ((node.dir / "snapshots", "snapshots"), (Path(membership_dir), "membership"),
                           (node.dir / "audit", "audit"), (node.dir, "root")):
        for p in sorted(src_root.iterdir()):
            if p.is_file() and (name != "root" or p.name in ("wal.log", "counters.json")):
                rel = f"{name}/{p.name}"
                (dest / name).mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest / rel)
                files[rel] = _sha(dest / rel)
    if node.audit.archive_dir and node.audit.archive_dir.exists():
        for p in sorted(node.audit.archive_dir.iterdir()):
            rel = f"audit_archive/{p.name}"
            (dest / "audit_archive").mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest / rel)
            files[rel] = _sha(dest / rel)
    manifest = {"format": "GAP05_BACKUP/1", "replica": node.name, "generation": node.generation,
                "membership_epoch": node.membership.epoch, "files": files, "audit_head": node.audit.signed_head()}
    atomic_write(dest / "MANIFEST.json", canonical_bytes(manifest))
    return manifest


def verify_backup(src: Path, audit_public_key) -> dict:
    src = Path(src)
    manifest = json.loads((src / "MANIFEST.json").read_bytes())
    for rel, digest in manifest["files"].items():
        p = src / rel
        if not p.exists() or _sha(p) != digest:
            raise IntegrityError(f"backup file {rel} missing or altered", code="CORR_BACKUP_DIGEST")
    dirs = [d for d in (src / "audit_archive", src / "audit") if d.exists()]
    AuditLedger.verify(dirs, audit_public_key, manifest["audit_head"])
    SnapshotStore(src / "snapshots").latest_valid()
    return manifest


def restore(src: Path, into: Path, *, audit_public_key) -> dict:
    manifest = verify_backup(src, audit_public_key)
    into = Path(into)
    if into.exists() and any(into.iterdir()):
        raise IntegrityError("restore target is not empty (refusing to overwrite live state)",
                             code="CORR_RESTORE_TARGET")
    for sub in ("snapshots", "audit"):
        if (Path(src) / sub).exists():
            shutil.copytree(Path(src) / sub, into / sub)
    for name in ("wal.log", "counters.json"):
        if (Path(src) / "root" / name).exists():
            shutil.copy2(Path(src) / "root" / name, into / name)
    atomic_write(into / "RESTORED", canonical_bytes({"from_generation": manifest["generation"],
                                                    "membership_epoch": manifest["membership_epoch"]}))
    return manifest


# ---------------------------------------------------------------- batch apply (MC42)
def apply_batch(node, docs: list[dict], *, principal: str, relay: bool = True, atomic_validation: bool = False,
                trace_id: str | None = None) -> list[dict]:
    """Apply a replication batch with per-item outcomes and bounded memory.

    Items are applied in the given order (the core model makes the final state
    order-independent).  With ``atomic_validation`` every item is schema/provenance
    checked first and the whole batch is refused if any item is invalid.
    """
    from .protect import verify_write
    from .schemas import validate_write_doc
    size = sum(len(canonical_bytes(d)) for d in docs)
    node.limits.check_batch(len(docs), size)
    if atomic_validation:
        for i, d in enumerate(docs):
            try:
                validate_write_doc(d, node.limits)
                verify_write(d, node.membership)
            except Gap05Error as exc:
                raise type(exc)(f"batch item {i} invalid: {exc}", code=exc.code) from exc
    out = []
    for i, d in enumerate(docs):
        try:
            r = node.submit(d, principal=principal, relay=relay, trace_id=trace_id)
            out.append({"index": i, "outcome": r["outcome"], "op_id": r["op_id"]})
        except Gap05Error as exc:
            out.append({"index": i, "outcome": "rejected", "code": exc.code,
                        "retryable": exc.retryable})
    return out


# ---------------------------------------------------------------- incident automation (MC47)
SEVERITY = {
    "CORR_FAIL_STOP": "SEV1", "CORR_WAL_CORRUPT": "SEV1", "CORR_AUDIT_TAMPER": "SEV1",
    "CORR_AUDIT_TRUNCATED": "SEV1", "SEC_COUNTER_EQUIVOCATION": "SEV1", "SEC_VECTOR_EQUIVOCATION": "SEV1",
    "SEC_FENCED_RETIRED": "SEV2", "SEC_BAD_SIGNATURE": "SEV2", "CAP_AUDIT_FULL": "SEV2",
    "CAP_FRONTIER_FULL": "SEV3", "CAP_HOT_KEY": "SEV3", "DEP_POLICY_UNAVAILABLE": "SEV3",
}


def triage(node) -> dict:
    """Map health + rejection metrics to paging severity and a containment action."""
    h = node.health()
    pages = []
    if not h["live"]:
        pages.append({"severity": "SEV1", "signal": "fail-stop", "action": "runbook RB-01 (restore from backup)"})
    if h["audit_pressure"] >= 0.9:
        pages.append({"severity": "SEV2", "signal": "audit pressure", "action": "runbook RB-05 (archive)"})
    if h["quarantine_pressure"] >= 0.5:
        pages.append({"severity": "SEV3", "signal": "quarantine pressure",
                      "action": "runbook RB-03 (drain quarantine via policy)"})
    for (name, labels), value in node.metrics.counters.items():
        code = dict(labels).get("code")
        if name == "apply_total" and code in SEVERITY and value > 0:
            pages.append({"severity": SEVERITY[code], "signal": code, "count": value,
                          "action": "see RUNBOOKS.md reason-code table"})
    return {"health": h, "pages": sorted(pages, key=lambda p: p["severity"])}


def contain(node, tenant, environment, keys, *, principal, reason) -> list[str]:
    """Emergency containment: freeze keys (writes refused, quarantine preserved)."""
    for k in keys:
        node.freeze(tenant, environment, k, principal=principal, reason=reason)
    return list(keys)
