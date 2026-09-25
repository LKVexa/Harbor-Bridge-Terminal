"""Local operator CLI (works without network or a running plane).

    python -m pln05_elasticity_plane version
    python -m pln05_elasticity_plane schemas
    python -m pln05_elasticity_plane validate PK_DEMAND msg.json
    python -m pln05_elasticity_plane validate-config overlay.json [--layer site]
    python -m pln05_elasticity_plane inspect-state STATE_DIR
    python -m pln05_elasticity_plane verify-audit audit.jsonl
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import __version__, configuration, wire
from .errors import PlaneError


def _out(obj) -> None:
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pln05")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version")
    sub.add_parser("schemas")
    v = sub.add_parser("validate")
    v.add_argument("family", choices=sorted(wire.SCHEMAS))
    v.add_argument("file")
    c = sub.add_parser("validate-config")
    c.add_argument("file")
    c.add_argument("--layer", default="site", choices=configuration.LAYERS[1:])
    i = sub.add_parser("inspect-state")
    i.add_argument("directory")
    a = sub.add_parser("verify-audit")
    a.add_argument("file")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "version":
            _out({"package": "pln05-elasticity-plane", "version": __version__,
                  "schemas": {k: list(v) for k, v in wire.SUPPORTED.items()}})
        elif args.cmd == "schemas":
            _out(wire.schema_checksums())
        elif args.cmd == "validate":
            wire.decode(args.family, pathlib.Path(args.file).read_bytes())
            _out({"valid": True, "family": args.family})
        elif args.cmd == "validate-config":
            layer = json.loads(pathlib.Path(args.file).read_text(encoding="utf-8"))
            cand = configuration.compose({args.layer: layer})
            configuration.validate(cand)
            _out({"valid": True, "checksum": configuration.checksum(cand),
                  "diff": configuration.diff(configuration.DEFAULTS, cand)})
        elif args.cmd == "inspect-state":
            rows = []
            for f in sorted(pathlib.Path(args.directory).glob("*.state.json")):
                try:
                    doc = json.loads(f.read_bytes())["doc"]
                    rows.append({"file": f.name, "scope": doc.get("scope"), "schema": doc.get("schema"),
                                 "epoch": doc.get("epoch"), "current": doc.get("current"),
                                 "controls": sorted(doc.get("controls", {})),
                                 "integrity": "not verified offline (requires key ring)"})
                except (ValueError, KeyError):
                    rows.append({"file": f.name, "error": "unreadable"})
            _out(rows)
        elif args.cmd == "verify-audit":
            from .audit import GENESIS, _digest
            prev, n, problems = GENESIS, 0, []
            for line in pathlib.Path(args.file).read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                n += 1
                if rec.get("seq") != n or rec.get("prev") != prev or _digest(rec) != rec.get("hash"):
                    problems.append(f"break at record {n}")
                    break
                prev = rec["hash"]
            _out({"records": n, "chain_ok": not problems, "problems": problems,
                  "note": "tail truncation needs the signed anchor (AuditLog.verify)"})
            return 0 if not problems else 1
    except PlaneError as exc:
        _out(exc.to_wire())
        return 2
    return 0
