"""MC45 - Administrative tooling (read-only operator CLI).

``python -m gap05_state_replication_consistency_model.production.cli <command> ...``

Commands never mutate replica state; state changes (freeze, resolve, reconfigure) go
through the authorized, audited ``ReplicaNode`` API so every human action carries a
principal, a policy version and an audit record.

  inspect DATA_DIR            frontier/quarantine per key from snapshot + WAL (no keys needed)
  conflicts DATA_DIR          only keys with open conflicts or quarantine, JSON
  verify-wal DATA_DIR         framing/checksum scan, reports torn tail vs corruption
  verify-audit DIR... --pub HEX --head FILE
                              verify the audit chain against a signed head
  migrate SNAP_DIR --tenant T --environment E [--apply]
                              dry-run (default) or apply snapshot format migration
  modelcheck                  run the bounded invariant model checker
  bench [--quick]             run benchmarks + PROPOSED capacity gates
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..model import ReplicatedKey, Write
from .durable import SnapshotStore, WriteAheadLog
from .errors import Gap05Error


def _load_docs(data_dir: Path) -> tuple[list[dict], dict]:
    snap, rejected = SnapshotStore(data_dir / "snapshots").latest_valid()
    docs, seq = [], 0
    if snap:
        seq = snap["wal_seq"]
        docs = [s["doc"] for s in snap["state"]["frontier"]]
    # read-only WAL scan: copy to avoid truncating a live torn tail
    import shutil
    import tempfile
    wal_path = data_dir / "wal.log"
    info = {"snapshot_generation": snap["generation"] if snap else None, "snapshot_rejected": rejected}
    if wal_path.exists():
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "wal.log"
            shutil.copy2(wal_path, tmp)
            wal = WriteAheadLog(tmp)
            info["wal"] = wal.recovery_report
            docs += [r["body"]["doc"] for r in wal.records_after(seq) if r["kind"] == "apply"]
            wal.close()
    return docs, info


def inspect(data_dir: Path, only_open=False) -> dict:
    docs, info = _load_docs(Path(data_dir))
    keys: dict[str, ReplicatedKey] = {}
    sites = {s for d in docs for s, _ in d["vector"]}
    for d in docs:
        if "value" not in d:
            d = {**d, "value": "<encrypted>"}
        sk = f'{d["tenant"]}/{d["environment"]}/{d["key"]}'
        rk = keys.setdefault(sk, ReplicatedKey(sk, frozenset(sites) or frozenset({"_"}), max_siblings=8))
        try:
            rk.apply(Write(sk, d["value"], d["site"], tuple(tuple(e) for e in d["vector"])))
        except ValueError:
            pass
    out = {}
    for sk, rk in sorted(keys.items()):
        cs = rk.conflict_set()
        if only_open and not cs["open"]:
            continue
        out[sk] = {"open": cs["open"], "active": len(cs["siblings"]), "quarantined": len(cs["quarantined"]),
                   "sites": sorted({s["site"] for s in cs["siblings"] + cs["quarantined"]})}
    return {"info": info, "keys": out}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="gap05-admin")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("inspect", "conflicts", "verify-wal"):
        sp = sub.add_parser(name)
        sp.add_argument("data_dir", type=Path)
    va = sub.add_parser("verify-audit")
    va.add_argument("dirs", nargs="+", type=Path)
    va.add_argument("--pub", required=True)
    va.add_argument("--head", required=True, type=Path)
    mg = sub.add_parser("migrate")
    mg.add_argument("snap_dir", type=Path)
    mg.add_argument("--tenant", required=True)
    mg.add_argument("--environment", required=True)
    mg.add_argument("--apply", action="store_true")
    sub.add_parser("modelcheck")
    bn = sub.add_parser("bench")
    bn.add_argument("--quick", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.cmd in ("inspect", "conflicts"):
            res = inspect(a.data_dir, only_open=a.cmd == "conflicts")
        elif a.cmd == "verify-wal":
            res = _load_docs(a.data_dir)[1]
        elif a.cmd == "verify-audit":
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from .audit import AuditLedger
            res = AuditLedger.verify(a.dirs, Ed25519PublicKey.from_public_bytes(bytes.fromhex(a.pub)),
                                     json.loads(a.head.read_bytes()))
        elif a.cmd == "migrate":
            from .lifecycle import migrate_snapshot_dir
            res = migrate_snapshot_dir(a.snap_dir, dry_run=not a.apply, tenant=a.tenant, environment=a.environment)
        elif a.cmd == "modelcheck":
            from .modelcheck import run_all
            r = run_all()
            res = {k: ({kk: vv for kk, vv in v.items() if kk != "violations"} if isinstance(v, dict) else v)
                   for k, v in r.items()}
        else:
            from .bench import run_all as bench
            res = bench(a.quick)
    except Gap05Error as exc:
        print(json.dumps({"error": exc.as_record()}), file=sys.stderr)
        return 2
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
