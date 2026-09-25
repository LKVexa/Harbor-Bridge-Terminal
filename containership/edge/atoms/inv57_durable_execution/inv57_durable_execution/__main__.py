"""Operator CLI: ``python -m inv57_durable_execution <command>``.

Commands:
  status [--db PATH]        canonical status document (MC-47)
  gate [--out FILE]         run the production exit gate (MC-57); exit 0 only on GO
  errors                    print the error-model registry (MC-14)
  lifecycle                 print the lifecycle transition table (MC-05)
  config-validate FILE      validate a configuration document (MC-21)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from . import __version__


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv57")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--db")
    g = sub.add_parser("gate")
    g.add_argument("--out")
    sub.add_parser("errors")
    sub.add_parser("lifecycle")
    c = sub.add_parser("config-validate")
    c.add_argument("file")
    a = ap.parse_args(argv)
    root = os.path.dirname(os.path.abspath(__file__))

    if a.cmd == "errors":
        from .errors import registry
        print(json.dumps(registry(), indent=1))
        return 0
    if a.cmd == "lifecycle":
        from .lifecycle import table
        print(json.dumps(table(), indent=1))
        return 0
    if a.cmd == "config-validate":
        from .config import validate, digest
        from .errors import ConfigRejected
        try:
            cfg = validate(json.load(open(a.file)))
        except ConfigRejected as exc:
            print(json.dumps({"valid": False, "error": str(exc)}))
            return 2
        print(json.dumps({"valid": True, "digest": digest(cfg)}))
        return 0
    if a.cmd == "status":
        from .config import defaults, digest
        from .status import StatusSurface
        probes = {"config": lambda: (True, "ok"),
                  "time_source": lambda: (time.time() > 1.7e9, "ok")}
        if a.db:
            def _db():
                from .sqlite_store import SQLiteBackend
                b = SQLiteBackend(a.db)
                b.event_count()
                b.close()
                return True, "ok"
            probes["history_backend"] = _db
        cfg = defaults()
        doc = StatusSurface(version=__version__, config_digest=digest(cfg), config_generation=0,
                            environment=cfg["environment"], site=cfg["site"], probes=probes).document()
        print(json.dumps(doc, indent=1))
        return 0 if doc["ready"]["ready"] else 3
    if a.cmd == "gate":
        from .acceptance import evaluate
        m = evaluate(root)
        text = json.dumps(m, indent=1, sort_keys=True)
        if a.out:
            open(a.out, "w").write(text + "\n")
        print(json.dumps({k: m[k] for k in ("verdict", "c_items", "components", "blockers")}, indent=1))
        return 0 if m["verdict"] == "GO" else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
