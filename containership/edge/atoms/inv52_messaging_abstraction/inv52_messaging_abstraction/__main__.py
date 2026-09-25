"""Command line: ``python -m inv52_messaging_abstraction <command>``.

Commands
  config-check CONFIG [OVERLAY ...]   validate layered config; exit 1 on any problem
  bootstrap CONFIG [OVERLAY ...]      bootstrap an ephemeral bus and print health
  gate [...]                          release certification gate (see gate.py)
  rtm                                 render governance/RTM.md and check it
  bench [...]                         performance harness (see bench.py)
"""
from __future__ import annotations

import json
import os
import pathlib
import sys


def _load(paths: list[str]) -> list[dict]:
    return [json.loads(pathlib.Path(p).read_text(encoding="utf-8")) for p in paths]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "config-check":
        from .config import digest, layered, validate

        if not rest:
            print(json.dumps({"valid": False, "problems": ["no config given"]}))
            return 1
        cfg = layered(*_load(rest))
        problems = validate(cfg)
        print(json.dumps({"valid": not problems, "problems": problems, "digest": digest(cfg)}, indent=2))
        return 0 if not problems else 1
    if cmd == "bootstrap":
        from .lifecycle import bootstrap

        try:
            managed, report = bootstrap(_load(rest), author=os.environ.get("USER", "cli"))
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"bootstrapped": False, "error": getattr(exc, "as_dict", lambda: str(exc))()}, indent=2))
            return 1
        out = {"report": report, "health": managed.health()}
        print(json.dumps(out, indent=2, default=str))
        return 0 if out["health"]["ready"] else 1
    if cmd == "gate":
        from .gate import main as gate_main

        return gate_main(rest)
    if cmd == "rtm":
        from .gate import ROOT, check_rtm, render_rtm

        (ROOT / "governance" / "RTM.md").write_text(render_rtm(), encoding="utf-8")
        res = check_rtm()
        print(json.dumps(res, indent=2))
        return 0 if res["result"] == "PASS" else 1
    if cmd == "bench":
        from .bench import main as bench_main

        return bench_main(rest)
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
