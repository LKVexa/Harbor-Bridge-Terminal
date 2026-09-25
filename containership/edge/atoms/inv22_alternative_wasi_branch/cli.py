"""Operator CLI (MC-45).  ``python -m inv22_alternative_wasi_branch.cli <command>``

Every command prints one JSON document and exits with the error registry's
exit code on failure (0 on success, 1 when a gate/check reports not-ok).
Inspection commands are local and read-only; state-changing operations go
through the authenticated ``ops`` API (see ``ops.py``) and are not exposed
here without credentials.
"""
from __future__ import annotations

import argparse
import json

from . import __version__, canonical, matrix, preflight, wit
from .errors import wrap


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def cmd_preflight(a):
    return preflight.run(strict=a.strict)


def cmd_matrix_validate(a):
    m = matrix.parse(_read(a.file))
    return {"ok": True, "revision": m.revision, "entries": len(m.entries), "digest": m.digest}


def cmd_completeness(a):
    m = matrix.parse(_read(a.matrix))
    discovered = []
    for f in a.wit:
        pkg = wit.parse(_read(f).decode("utf-8"))
        discovered += wit.workload_imports(pkg) or [i["interface"] for i in wit.inventory(pkg)]
    return matrix.completeness(m, discovered)


def cmd_wit_diff(a):
    s, f = wit.parse(_read(a.standards).decode()), wit.parse(_read(a.fork).decode())
    d = wit.diff(s, f)
    entries, blocking = wit.candidate_matrix(d)
    return {"diff": d, "auto_identical": [e["interface"] for e in entries], "needs_review": blocking,
            "ok": not blocking}


def cmd_translate(a):
    from .reference import PKG
    from .shim import ShimService, default_registry
    m = matrix.parse(_read(str(PKG / "data/matrix.json")))
    return ShimService(m, default_registry()).translate(canonical.loads(_read(a.request)))


def cmd_audit_verify(a):
    from .store import Store
    s = Store(a.store, read_only=True)
    try:
        return s.integrity_check()
    finally:
        s.close()


def cmd_evidence(a):
    from .evidence import build_bundle
    return build_bundle(out_dir=a.out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="inv22", description=f"INV-22 operator CLI v{__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    commands: dict[str, tuple] = {
        "preflight": (cmd_preflight, [("--strict", {"action": "store_true"})]),
        "matrix-validate": (cmd_matrix_validate, [("file", {})]),
        "completeness": (cmd_completeness, [("matrix", {}), ("wit", {"nargs": "+"})]),
        "wit-diff": (cmd_wit_diff, [("standards", {}), ("fork", {})]),
        "translate": (cmd_translate, [("request", {})]),
        "audit-verify": (cmd_audit_verify, [("store", {})]),
        "evidence": (cmd_evidence, [("--out", {"default": "evidence"})]),
    }
    for name, (fn, params) in commands.items():
        x = sub.add_parser(name)
        for flag, kw in params:
            x.add_argument(flag, **kw)
        x.set_defaults(fn=fn)
    a = p.parse_args(argv)
    try:
        out = a.fn(a)
    except Exception as exc:
        err = wrap(exc)
        print(json.dumps({"ok": False, "error": err.to_dict()}, indent=2, sort_keys=True))
        return err.spec.exit_code
    print(json.dumps(out, indent=2, sort_keys=True, default=str))
    if isinstance(out, dict) and (out.get("ok") is False or out.get("status") == "error"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
