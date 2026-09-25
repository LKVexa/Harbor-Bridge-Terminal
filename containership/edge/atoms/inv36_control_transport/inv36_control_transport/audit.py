"""``python -m inv36_control_transport.audit`` - run the INV-36 gate (MC-01.007).

    python -m inv36_control_transport.audit                 # local mode; SKIPs allowed, never counted as PASS
    python -m inv36_control_transport.audit --certify       # production certification: SKIP/ERROR block
    python -m inv36_control_transport.audit --only G02-unit-tests --out /tmp/ev
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import gate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv36-audit")
    ap.add_argument("--certify", action="store_true", help="production-certification mode")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--only", action="append")
    ap.add_argument("--artifact-digest")
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return gate.EXIT_CONFIG
    known = {c.id for c in gate.CHECKS}
    if a.only and not set(a.only) <= known:
        print(json.dumps({"error": "unknown check id", "known": sorted(known)}))
        return gate.EXIT_CONFIG
    code, doc = gate.run("certify" if a.certify else "local", a.out, a.timeout, a.only, a.artifact_digest)
    if "results" in doc:
        for r in doc["results"]:
            print(f"{r['status']:5} {r['id']:28} {r['detail'][:110]}")
        print(json.dumps({"summary": doc["summary"], "exit_code": code, "source_digest": doc["source_digest"]}))
    else:
        print(json.dumps(doc))
    return code


if __name__ == "__main__":
    sys.exit(main())
