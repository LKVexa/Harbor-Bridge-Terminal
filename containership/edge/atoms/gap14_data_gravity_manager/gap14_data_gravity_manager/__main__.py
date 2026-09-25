"""Operator CLI:  python -m gap14_data_gravity_manager <command>

  handshake                       pk_core compatibility handshake (exit 0 only if certifying)
  gate RESULTS.json [--approved-skips SKIPS.json]
                                  evaluate raw pk_core results; PASS impossible without certified runtime
  verify-audit AUDIT.jsonl --keys KEYS.json
                                  verify the tamper-evident audit chain
  validate SCHEMA FILE.json       validate a payload against a shipped schema (e.g. PK_GAP14_CONFIG/1)
  knobs                           print configuration knobs, defaults, safe ranges, reloadability
  reason-codes                    print the reason-code registry (category, disposition, action)

KEYS.json: {"<kid>": {"issuer": "...", "secret_hex": "..."}} -- supplied by the estate key service;
never commit real keys.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import compat
from .audit import read_records, verify_chain
from .config import knob_table
from .errors import G14Error, REGISTRY
from .schema_check import SchemaError, validate
from .trust import Key, KeyRing


def _keyring(path: str) -> KeyRing:
    raw = json.load(open(path, encoding="utf-8"))
    return KeyRing(Key(kid, v["issuer"], bytes.fromhex(v["secret_hex"])) for kid, v in raw.items())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gap14_data_gravity_manager")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("handshake")
    g = sub.add_parser("gate")
    g.add_argument("results")
    g.add_argument("--approved-skips")
    v = sub.add_parser("verify-audit")
    v.add_argument("path")
    v.add_argument("--keys", required=True)
    s = sub.add_parser("validate")
    s.add_argument("schema")
    s.add_argument("file")
    sub.add_parser("knobs")
    sub.add_parser("reason-codes")
    a = ap.parse_args(argv)

    if a.cmd == "handshake":
        hs = compat.handshake()
        print(json.dumps(hs.as_dict(), indent=2))
        return 0 if hs.certifying else 2
    if a.cmd == "gate":
        hs = compat.handshake()
        results = json.load(open(a.results, encoding="utf-8"))
        skips = json.load(open(a.approved_skips, encoding="utf-8")) if a.approved_skips else {}
        res = compat.evaluate_gate(hs, results, approved_skips=skips)
        print(json.dumps(res.as_dict(), indent=2))
        return 0 if res.verdict == "PASS" else 3
    if a.cmd == "verify-audit":
        try:
            print(json.dumps(verify_chain(read_records(a.path), _keyring(a.keys)), indent=2))
            return 0
        except G14Error as exc:
            print(json.dumps(exc.as_dict(), indent=2))
            return 4
    if a.cmd == "validate":
        try:
            validate(json.load(open(a.file, encoding="utf-8")), a.schema)
            print("valid")
            return 0
        except SchemaError as exc:
            print(f"invalid: {exc}")
            return 5
    if a.cmd == "knobs":
        print(knob_table())
        return 0
    if a.cmd == "reason-codes":
        for r in REGISTRY.values():
            print(f"{r.code}\t{r.category}\t{r.disposition}\t{r.operator_action}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
