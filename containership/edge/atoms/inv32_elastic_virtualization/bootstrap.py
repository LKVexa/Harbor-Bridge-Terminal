"""Deterministic bootstrap / preflight (WS 2, 5, 19).

    python -m inv32_elastic_virtualization.bootstrap --check [--layer site=site.json ...] [--state-dir DIR]

``--check`` performs **no mutation** (no directories created, no torn-tail repair).  Output is one JSON
document (``PK_INV32_BOOTSTRAP/1``) on stdout.  Exit codes::

    0 ready   2 config invalid   3 dependency missing/untrusted   4 integrity failure   5 state dir unusable

Without ``--check`` the same checks run and then the state directory is created (idempotently).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

from . import __version__
from . import errors as E
from .config import merge, parse_document, validate_cross_field, canonical_digest

MIN_PYTHON = (3, 10)
PK_CORE_RANGE = (">=1.0", "<2.0")  # only needed for the optional inventory adapter
PKG_DIR = Path(__file__).resolve().parent
RELEASE_DIGESTS = PKG_DIR / "RELEASE_DIGESTS.json"

EXIT_OK, EXIT_CONFIG, EXIT_DEPENDENCY, EXIT_INTEGRITY, EXIT_STATE = 0, 2, 3, 4, 5


def _check_runtime() -> dict[str, Any]:
    ok = sys.version_info[:2] >= MIN_PYTHON
    return {"name": "python_runtime", "ok": ok, "found": ".".join(map(str, sys.version_info[:3])),
            "required": ">=" + ".".join(map(str, MIN_PYTHON)), "exit": EXIT_DEPENDENCY}


def _check_integrity() -> dict[str, Any]:
    """Verify installed module digests against the release digest list when one is shipped."""
    if not RELEASE_DIGESTS.exists():
        return {"name": "package_integrity", "ok": True, "note": "no RELEASE_DIGESTS.json (source checkout)",
                "exit": EXIT_INTEGRITY}
    expected = json.loads(RELEASE_DIGESTS.read_text())
    bad = []
    for rel, digest in expected.get("files", {}).items():
        p = PKG_DIR / rel
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            bad.append(rel)
    return {"name": "package_integrity", "ok": not bad and expected.get("version") == __version__,
            "mismatched": bad[:20], "exit": EXIT_INTEGRITY}


def _check_pk_core(required: bool) -> dict[str, Any]:
    found = importlib.util.find_spec("pk_core") is not None
    return {"name": "pk_core", "ok": found or not required, "found": found, "required": required,
            "compatible_range": PK_CORE_RANGE, "exit": EXIT_DEPENDENCY}


def _check_config(layer_args: list[str]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    layers: dict[str, list[Mapping[str, Any]]] = {}
    try:
        for spec in layer_args:
            name, _, path = spec.partition("=")
            layers.setdefault(name, []).append(parse_document(Path(path).read_text(encoding="utf-8")))
        values = merge(layers)
        validate_cross_field(values)
    except (E.ConfigInvalid, OSError) as exc:
        code = getattr(exc, "code", "config_unreadable")
        return {"name": "config", "ok": False, "code": code, "details": getattr(exc, "details", {}),
                "exit": EXIT_CONFIG}, None
    return {"name": "config", "ok": True, "digest": canonical_digest(values), "exit": EXIT_CONFIG}, values


def _check_state_dir(path: str, *, mutate: bool) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        if not mutate:
            parent = p.parent
            ok = parent.exists() and os.access(parent, os.W_OK)
            return {"name": "state_dir", "ok": ok, "exists": False, "exit": EXIT_STATE}
        p.mkdir(parents=True, exist_ok=True)
        os.chmod(p, 0o700)
    ok = p.is_dir() and os.access(p, os.W_OK | os.X_OK)
    mode_ok = (p.stat().st_mode & 0o077) == 0 if ok else False
    return {"name": "state_dir", "ok": ok and mode_ok, "exists": True, "private_mode": mode_ok, "exit": EXIT_STATE}


def _check_store_readonly(path: str) -> dict[str, Any]:
    """Read-only journal/audit verification (no torn-tail repair in --check)."""
    from .model import ZERO_HASH, _canonical_hash
    from .store import _crc

    p = Path(path)
    problems = []
    if p.exists():
        prev, seq = ZERO_HASH, 0
        for seg in sorted((p / "audit").glob("seg-*.jsonl")):
            for i, line in enumerate(seg.read_bytes().split(b"\n")):
                if not line:
                    continue
                try:
                    w = json.loads(line)
                    ev = w["rec"]
                    assert _crc(ev) == w["crc"]
                    body = {k: v for k, v in ev.items() if k != "event_hash"}
                    seq += 1
                    assert body["sequence"] == seq and body["prev_hash"] == prev
                    assert _canonical_hash(body) == ev["event_hash"]
                    prev = ev["event_hash"]
                except Exception:  # noqa: BLE001
                    problems.append(f"{seg.name}:{i + 1}")
                    break
    return {"name": "store_integrity", "ok": not problems, "problems": problems[:10], "exit": EXIT_INTEGRITY}


def run(argv: list[str] | None = None) -> tuple[int, dict[str, Any]]:
    ap = argparse.ArgumentParser(prog="inv32-bootstrap")
    ap.add_argument("--check", action="store_true", help="preflight only; perform no mutation")
    ap.add_argument("--layer", action="append", default=[], metavar="LAYER=PATH")
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--require-pk-core", action="store_true")
    args = ap.parse_args(argv)
    checks = [_check_runtime(), _check_integrity(), _check_pk_core(args.require_pk_core)]
    cfg_check, values = _check_config(args.layer)
    checks.append(cfg_check)
    if values is not None:
        state_dir = args.state_dir or values["state_dir"]
        checks.append(_check_state_dir(state_dir, mutate=not args.check))
        checks.append(_check_store_readonly(state_dir))
    code = next((c["exit"] for c in checks if not c["ok"]), EXIT_OK)
    report = {"schema": "PK_INV32_BOOTSTRAP/1", "version": __version__, "mode": "check" if args.check else "apply",
              "ok": code == EXIT_OK, "exit_code": code,
              "checks": [{k: v for k, v in c.items() if k != "exit"} for c in checks]}
    return code, report


def main(argv: list[str] | None = None) -> int:
    code, report = run(argv)
    print(json.dumps(report, indent=1, sort_keys=True, default=str))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
