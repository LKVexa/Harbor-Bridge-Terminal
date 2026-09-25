"""Operator CLI (MC-063, MC-089).

    python -m inv28_unikernel_implementations.cli demo                 # fixture world: select, refuse, explain, status
    python -m inv28_unikernel_implementations.cli validate SCHEMA FILE  # e.g. PK_TOOLCHAIN_SELECTION_REQUEST-1 req.json
    python -m inv28_unikernel_implementations.cli catalog              # validate catalog/catalog.json, list entries
    python -m inv28_unikernel_implementations.cli policy [FILE]         # validate a policy file, print its digest

A production host embeds ``service.Inv28Service`` with its own keys, clock and stores; this CLI works on
files and on the synthetic fixture world only, so it can never select against production data by accident.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import fixtures as F
from .errors import Inv28Error, RefusalError
from .model import ToolchainRecord
from .policy import SelectionPolicy
from .schema_check import validate_file

PKG = Path(__file__).resolve().parent


def cmd_demo(_a) -> int:
    w = F.world()
    res = w["selector"].select(F.request(), now=F.NOW)
    print(f"selected {res.ref} (decision {res.decision_id[:16]}, cert {res.certification_id})")
    try:
        w["selector"].select(F.request(language="rust"), now=F.NOW)
    except RefusalError as exc:
        print(f"refused rust/production: {exc.refusal.code}")
        print(w["service"].explain(exc.refusal.decision_id))
    print(w["service"].explain(res.decision_id))
    print(json.dumps(w["service"].status(), indent=1))
    return 0


def cmd_validate(a) -> int:
    errs = validate_file(a.schema, json.loads(Path(a.file).read_text(encoding="utf-8")))
    for e in errs:
        print("INVALID", e)
    print("VALID" if not errs else f"INVALID ({len(errs)})")
    return 0 if not errs else 1


def cmd_catalog(_a) -> int:
    cat = json.loads((PKG / "catalog" / "catalog.json").read_text(encoding="utf-8"))
    bad = 0
    for e in cat["entries"]:
        try:
            r = ToolchainRecord.from_dict(e)
            print(f"{r.ref:28} {r.maturity:12} {r.lifecycle:10} {r.catalog_status}")
        except Inv28Error as exc:
            bad += 1
            print("INVALID", e.get("name"), exc)
    return 0 if not bad else 1


def cmd_policy(a) -> int:
    p = SelectionPolicy.load(a.file or PKG / "config" / "policy.default.json")
    print(f"{p.policy_id} r{p.revision} digest {p.digest}")
    for env, rule in sorted(p.environments.items()):
        print(f"  {env:10} min_maturity={rule.min_maturity} production={rule.production} "
              f"certification={rule.require_certification}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="inv28")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo").set_defaults(fn=cmd_demo)
    v = sub.add_parser("validate")
    v.add_argument("schema")
    v.add_argument("file")
    v.set_defaults(fn=cmd_validate)
    sub.add_parser("catalog").set_defaults(fn=cmd_catalog)
    p = sub.add_parser("policy")
    p.add_argument("file", nargs="?")
    p.set_defaults(fn=cmd_policy)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
