"""Command line: python -m inv11_interface_contract_language.wit <command> ...

  check PATH                    parse + resolve, print diagnostics (exit 1 on error)
  export PATH                   PK_INTERFACE/1 JSON
  fingerprint PATH              package fingerprint (versioned and version-less)
  diff OLD NEW [--expanded] [--json]   classify two package releases
  semver OLD NEW                advisory version recommendation
  matrix                        supported-version matrix
Exit codes: 0 ok, 1 input/diagnostic error, 2 environment/blocked, 3 breaking (diff --fail-on-breaking).
"""
from __future__ import annotations

import argparse
import json
import sys

from .compat import BREAKING, classify_packages
from .lifecycle import recommend_version, render_diff
from .normalize import package_fingerprint
from .ops import matrix
from .parser import ParseConfig
from .resolve import Resolved, load_package
from .schema import export_interface


def _load(path: str, features: list[str]) -> Resolved:
    pr, res = load_package(path, ParseConfig(), frozenset(features))
    for d in res.diagnostics.sorted():
        print(d.render(), file=sys.stderr)
    if pr.fatal or not res.ok:
        raise SystemExit(1)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv11-wit")
    ap.add_argument("--feature", action="append", default=[], help="enable an @unstable feature")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("check", "export", "fingerprint"):
        sub.add_parser(c).add_argument("path")
    d = sub.add_parser("diff")
    d.add_argument("old")
    d.add_argument("new")
    d.add_argument("--json", action="store_true")
    d.add_argument("--expanded", action="store_true")
    d.add_argument("--fail-on-breaking", action="store_true")
    s = sub.add_parser("semver")
    s.add_argument("old")
    s.add_argument("new")
    sub.add_parser("matrix")
    a = ap.parse_args(argv)
    if a.cmd == "matrix":
        print(json.dumps(matrix(), indent=2, sort_keys=True))
        return 0
    if a.cmd == "check":
        res = _load(a.path, a.feature)
        print(f"ok: {len(res.interfaces)} interfaces, {len(res.worlds)} worlds, {len(res.types)} types")
        return 0
    if a.cmd == "export":
        print(json.dumps(export_interface(_load(a.path, a.feature)), indent=2, sort_keys=True))
        return 0
    if a.cmd == "fingerprint":
        res = _load(a.path, a.feature)
        print(json.dumps({"package": res.root_package, "fingerprint": package_fingerprint(res),
                          "structural_fingerprint": package_fingerprint(res, True)}, indent=2))
        return 0
    old, new = _load(a.old, a.feature), _load(a.new, a.feature)
    diff = classify_packages(old, new)
    if a.cmd == "semver":
        cur = (old.root_package or "").rsplit("@", 1)[-1]
        print(json.dumps(recommend_version(cur, diff), indent=2))
        return 0
    print(json.dumps(diff, indent=2) if a.json else render_diff(diff, a.expanded))
    return 3 if (a.fail_on_breaking and diff["class"] == BREAKING) else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
