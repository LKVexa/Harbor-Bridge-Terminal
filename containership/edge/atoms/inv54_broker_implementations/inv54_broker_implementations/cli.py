"""``python -m inv54_broker_implementations.cli`` — validate a config and print a health/explain view."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import apply_overlays, digest, redact, validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv54")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate-config", help="fail-closed validation of base + overlays")
    v.add_argument("base")
    v.add_argument("overlays", nargs="*")
    sub.add_parser("version")
    a = ap.parse_args(argv)
    if a.cmd == "version":
        print(__version__)
        return 0
    base = json.load(open(a.base))
    cfg = apply_overlays(base, *[json.load(open(o)) for o in a.overlays])
    problems = validate(cfg)
    print(json.dumps({"valid": not problems, "problems": problems, "digest": digest(cfg),
                      "effective": redact(cfg)}, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
