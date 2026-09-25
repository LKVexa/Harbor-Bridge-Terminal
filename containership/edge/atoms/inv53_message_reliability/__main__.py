"""Operator CLI: ``python -m inv53_message_reliability <command>`` (components 48, 66, 83, 84).

Exit codes: 0 success, 1 check failed / refused, 2 usage error, 3 gate NO_GO.
Offline store commands take the store's OS lock, so they refuse to run against a
store that a live broker still owns.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, config, protocol
from .errors import taxonomy


def _print(obj) -> None:
    sys.stdout.write(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def _schemas(check: bool) -> int:
    base = Path(__file__).resolve().parent / "schemas"
    wanted = {**{k: v for k, v in protocol.json_schemas().items()}, "errors.json": taxonomy()}
    drift = []
    for name, doc in wanted.items():
        text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
        p = base / name
        if check:
            if not p.exists() or json.loads(p.read_text()) != json.loads(text):
                drift.append(name)
        else:
            p.write_text(text)
    _print({"checked" if check else "written": sorted(wanted), "drift": drift})
    return 1 if drift else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv53", description=f"INV-53 message reliability {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version")
    sub.add_parser("errors")
    s = sub.add_parser("schemas"); s.add_argument("--write", action="store_true")
    c = sub.add_parser("config"); c.add_argument("layers", nargs="*", help="name=path.json, applied in order")
    st = sub.add_parser("store"); st.add_argument("action", choices=["inspect", "backup", "restore", "redrive", "explain", "purge"])
    st.add_argument("dir"); st.add_argument("arg", nargs="?")
    st.add_argument("--visibility", type=float, default=30.0); st.add_argument("--max-attempts", type=int, default=5)
    st.add_argument("--now", type=float, default=0.0)
    au = sub.add_parser("audit"); au.add_argument("file"); au.add_argument("--anchor", help="JSON {seq, hash}")
    b = sub.add_parser("bench"); b.add_argument("rest", nargs=argparse.REMAINDER)
    g = sub.add_parser("gate"); g.add_argument("--evidence", default=None); g.add_argument("--out", default=None)
    t = sub.add_parser("traceability"); t.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    if a.cmd == "version":
        _print({"version": __version__, "wire": protocol.SUPPORTED, "config_schema": config.CONFIG_SCHEMA_VERSION})
        return 0
    if a.cmd == "errors":
        _print(taxonomy()); return 0
    if a.cmd == "schemas":
        return _schemas(check=not a.write)
    if a.cmd == "config":
        layers = []
        for spec in a.layers:
            name, _, path = spec.partition("=")
            layers.append((name, json.loads(Path(path).read_text())))
        try:
            _print(config.layer(*layers).record()); return 0
        except config.ConfigError as exc:
            _print({"error": str(exc)}); return 1
    if a.cmd == "store":
        from .durable import DurableQueue, restore
        kw = {"visibility": a.visibility, "max_attempts": a.max_attempts}
        if a.action == "restore":
            q = restore(a.dir, a.arg, **kw); _print({"restored": a.arg, "snapshot": q.snapshot()}); q.close(); return 0
        with DurableQueue(a.dir, **kw) as q:
            if a.action == "inspect":
                _print({"snapshot": q.snapshot(), "recovery_notes": q.recovery_notes, "state_digest": q.state_digest()})
            elif a.action == "backup":
                _print(q.backup(a.arg))
            elif a.action == "explain":
                _print(q.explain(a.arg))
            elif a.action == "redrive":
                ok = q.redrive(a.arg, now=a.now); _print({"redriven": ok}); return 0 if ok else 1
            elif a.action == "purge":
                ok = q.purge_dead_letter(a.arg); _print({"purged": ok}); return 0 if ok else 1
        return 0
    if a.cmd == "audit":
        from .security import AuditLog
        ok, why = AuditLog(a.file).verify(anchored_head=json.loads(a.anchor) if a.anchor else None)
        _print({"ok": ok, "detail": why}); return 0 if ok else 1
    if a.cmd == "bench":
        from .bench import main as bench_main
        return bench_main(a.rest)
    if a.cmd == "gate":
        from .gate import evaluate
        res = evaluate(evidence_path=a.evidence)
        text = json.dumps(res, indent=1, sort_keys=True)
        if a.out:
            Path(a.out).write_text(text + "\n")
        sys.stdout.write(text + "\n")
        return 0 if res["verdict"] == "GO" else 3
    if a.cmd == "traceability":
        from .gate import traceability_markdown
        md = traceability_markdown()
        if a.out:
            Path(a.out).write_text(md)
        else:
            sys.stdout.write(md)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
