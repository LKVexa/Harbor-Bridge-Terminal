"""Operator CLI: verify / migrate / backup / restore-verify / export / preflight / diagnose (components 47, 48).

Usage (from the folder containing the package)::

    python -m gap15_runtime_compatibility_certification.production.cli verify  --db data/gap15.db
    python -m gap15_runtime_compatibility_certification.production.cli migrate --db data/gap15.db [--dry-run]
    python -m gap15_runtime_compatibility_certification.production.cli export  --db data/gap15.db --out ledger.jsonl
    python -m gap15_runtime_compatibility_certification.production.cli diagnose --alert GAP15AuditChainBroken

Backup/restore need a signing key provider; with the development provider
they run only in ``--development`` mode and say so in their output.
Exit codes: 0 ok, 2 integrity failure, 3 refused (unsafe/unsupported), 4 usage.
"""
from __future__ import annotations

import argparse
import json
import sys

from .ops import ALERTS
from .store import SCHEMA_VERSION, Store, StoreError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gap15")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("verify", "migrate", "export"):
        p = sub.add_parser(name)
        p.add_argument("--db", required=True)
        if name == "migrate":
            p.add_argument("--dry-run", action="store_true")
        if name == "export":
            p.add_argument("--out", required=True)
    d = sub.add_parser("diagnose")
    d.add_argument("--alert", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "diagnose":
            hit = [a for a in ALERTS if a[0] == args.alert]
            if not hit:
                print(json.dumps({"error": "unknown alert"}))
                return 4
            n, sev, expr, owner, rb, fa = hit[0]
            print(json.dumps({"alert": n, "severity": sev, "owner": owner, "runbook": f"docs/RUNBOOKS.md#{rb}",
                              "first_action": fa, "expr": expr}, indent=2))
            return 0
        if args.cmd == "migrate" and args.dry_run:
            s = Store.__new__(Store)
            import sqlite3, threading
            s.db = sqlite3.connect(args.db, isolation_level=None)
            s._lock = threading.RLock()
            s.fault_hook = lambda stage: None
            cur = s.schema_version()
            print(json.dumps({"current": cur, "target": SCHEMA_VERSION, "pending": s.migrate(dry_run=True)}))
            return 0
        s = Store(args.db)
        if args.cmd == "verify":
            rec = s.recover()
            print(json.dumps({"ok": True, "schema_version": s.schema_version(), **rec,
                              "ledger_head": s.head("ledger"), "audit_head": s.head("audit")}))
            return 0
        if args.cmd == "migrate":
            print(json.dumps({"ok": True, "schema_version": s.schema_version()}))
            return 0
        if args.cmd == "export":
            print(json.dumps(s.export_ledger(args.out)))
            return 0
    except StoreError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "detail": exc.detail}))
        return 3 if exc.code in ("E_SCHEMA_TOO_NEW",) else 2
    return 4


if __name__ == "__main__":
    sys.exit(main())
