"""Operator CLI (day-0/1/2 runbooks call these).

    python -m inv45_sfi_mechanisms.production.cli preflight
    python -m inv45_sfi_mechanisms.production.cli rewrite IN.wasm OUT.wasm [--config CFG.json]
    python -m inv45_sfi_mechanisms.production.cli verify FILE.wasm [--config CFG.json]
    python -m inv45_sfi_mechanisms.production.cli audit-verify AUDIT.jsonl [--checkpoint SEQ:HASH]
    python -m inv45_sfi_mechanisms.production.cli config-validate CFG.json
    python -m inv45_sfi_mechanisms.production.cli errors

Exit codes: 0 ok, 2 rejected (stable SfiError printed as JSON on stdout), 3 preflight failed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config as cfgmod
from . import engine, sfi
from .audit import verify_chain
from .errors import SfiError, registry_markdown


def _cfg(path: str | None) -> dict:
    if not path:
        return cfgmod.validate(dict(cfgmod.DEFAULTS))
    return cfgmod.validate(cfgmod.load_json_strict(Path(path).read_text(encoding="utf-8")))


def _preflight_all() -> dict:
    import importlib.util
    rep = {"python": sys.version.split()[0], "python_ok": sys.version_info >= (3, 10),
           "engine": engine.preflight(22),
           "cryptography": importlib.util.find_spec("cryptography") is not None,
           "pk_core": importlib.util.find_spec("pk_core") is not None}
    rep["ok"] = rep["python_ok"] and rep["cryptography"] and rep["engine"]["ok"]
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv45-sfi")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight")
    r = sub.add_parser("rewrite")
    r.add_argument("inp")
    r.add_argument("out")
    r.add_argument("--config")
    v = sub.add_parser("verify")
    v.add_argument("file")
    v.add_argument("--config")
    a = sub.add_parser("audit-verify")
    a.add_argument("file")
    a.add_argument("--checkpoint")
    c = sub.add_parser("config-validate")
    c.add_argument("file")
    sub.add_parser("errors")
    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "preflight":
            rep = _preflight_all()
            print(json.dumps(rep, indent=1, sort_keys=True))
            return 0 if rep["ok"] else 3
        if ns.cmd == "rewrite":
            cfg = _cfg(ns.config)
            res = sfi.rewrite(Path(ns.inp).read_bytes(), cfgmod.profile(cfg), cfgmod.limits(cfg))
            sfi.verify(res.artifact, cfgmod.profile(cfg), cfgmod.limits(cfg))  # never write unverified output
            Path(ns.out).write_bytes(res.artifact)
            print(json.dumps(res.as_dict(), indent=1, sort_keys=True))
            return 0
        if ns.cmd == "verify":
            cfg = _cfg(ns.config)
            print(json.dumps(sfi.verify(Path(ns.file).read_bytes(), cfgmod.profile(cfg), cfgmod.limits(cfg)),
                             indent=1, sort_keys=True))
            return 0
        if ns.cmd == "audit-verify":
            cp = None
            if ns.checkpoint:
                s, h = ns.checkpoint.split(":", 1)
                cp = (int(s), h)
            print(json.dumps(verify_chain(Path(ns.file), cp), sort_keys=True))
            return 0
        if ns.cmd == "config-validate":
            cfg = _cfg(ns.file)
            print(json.dumps({"ok": True, "config_sha256": cfgmod.digest(cfg)}))
            return 0
        if ns.cmd == "errors":
            print(registry_markdown())
            return 0
    except SfiError as e:
        print(json.dumps(e.as_dict(), sort_keys=True))
        return 2
    return 1  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
