"""Shared helpers: make the package importable when tests run from any cwd."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv10_component_composition_system as pkg  # noqa: E402
from inv10_component_composition_system.composition import Unit, compose  # noqa: E402,F401

PKG_DIR = pathlib.Path(pkg.__file__).resolve().parent


def U(name, imports=(), exports=()):
    return Unit(name, frozenset(imports), frozenset(exports))


def stack():
    return [U("store", (), ["acme:kv/store@1.2.0"]),
            U("api", ["acme:kv/store@1.2.0", "wasi:http/outgoing@0.2.0"], ["acme:app/handler@1.0.0"]),
            U("gw", ["acme:app/handler@1.0.0"], ["wasi:http/incoming-handler@0.2.0"])]
