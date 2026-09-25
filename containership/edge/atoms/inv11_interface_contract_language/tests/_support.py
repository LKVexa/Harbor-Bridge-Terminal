"""Shared helpers for the INV-11 WIT test suites (no pk_core required)."""
from __future__ import annotations

import glob
import json
import os
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

FIX = PKG_DIR / "tests" / "fixtures"
EXPECTED = json.loads((FIX / "EXPECTED.json").read_text())

from inv11_interface_contract_language.wit.parser import parse_text  # noqa: E402
from inv11_interface_contract_language.wit.resolve import resolve_documents  # noqa: E402


def resolve_text(text, label="t.wit", features=frozenset(), config=None):
    from inv11_interface_contract_language.wit.parser import ParseConfig
    r = parse_text(text, label, config or ParseConfig())
    res = resolve_documents(r.documents, diags=r.diagnostics, features=features)
    return r, res


def pconfig(code):
    from inv11_interface_contract_language.wit.parser import ParseConfig
    return ParseConfig(**EXPECTED["policy"].get(code, {}).get("config", {}))


def ok(text, **kw):
    r, res = resolve_text(text, **kw)
    if r.fatal or not res.ok:
        raise AssertionError([d.render() for d in res.diagnostics.sorted()])
    return res


def files(kind):
    return sorted(glob.glob(str(FIX / kind / "*.wit")))


def name(p):
    return os.path.basename(p)[:-4]


def wasm_tools():
    from inv11_interface_contract_language.wit.differential import find_tool
    return find_tool()


def rd(p):
    return pathlib.Path(p).read_bytes()
