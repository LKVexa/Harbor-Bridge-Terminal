"""Fuzz targets and mutator shared by tests/test_fuzz.py and tools/fuzz.py (MC032)."""
from __future__ import annotations

import json
import random

from . import interfaces as I
from .model import HostImage, ImportUnsatisfied, LayerMissing, WasmModule, compose
from .records import RecordInvalid, canonical, parse

ALLOWED = (RecordInvalid, ValueError, TypeError, LayerMissing, ImportUnsatisfied, I.InterfaceIncompatible)

_COMPOSITION = canonical(json.loads(json.dumps(
    compose(WasmModule("svc", frozenset({"clock"})), HostImage("h", frozenset({"clock"}))), default=list)))
_IFACE = canonical(I.to_record(I.Interface("wasi:clocks", "0.2.0", frozenset({I.Func("now", (("id", "string"),), ("u64",))}))))
_MODEL = canonical({"module": {"name": "svc", "imports": ["clock"], "hardened": True, "architecture": "wasm32"},
                    "host": {"name": "h", "exposes": ["clock"], "sealed": True, "architecture": "x86_64"},
                    "required_layers": 2})


def t_parse_composition(data: bytes):
    parse(data, schema="PK_HYBRID_COMPOSITION/1")


def t_parse_verification(data: bytes):
    parse(data, schema="PK_HYBRID_VERIFICATION/1")


def t_interface(data: bytes):
    I.from_record(parse(data))


def t_model(data: bytes):
    d = parse(data)
    m, h = d.get("module"), d.get("host")
    if not isinstance(m, dict) or not isinstance(h, dict):
        raise ValueError("shape")
    imports, exposes = m.get("imports"), h.get("exposes")
    if not isinstance(imports, list) or not isinstance(exposes, list):
        raise TypeError("shape")
    if not all(isinstance(x, str) for x in imports + exposes):
        raise TypeError("cap types")
    compose(WasmModule(m.get("name"), frozenset(imports), m.get("hardened"), m.get("architecture")),
            HostImage(h.get("name"), frozenset(exposes), h.get("sealed"), h.get("architecture")),
            required_layers=d.get("required_layers"))


TARGETS = {"parse_composition": t_parse_composition, "parse_verification": t_parse_verification,
           "interface_record": t_interface, "model_inputs": t_model}
SEEDS = {"parse_composition": [_COMPOSITION], "parse_verification": [_COMPOSITION],
         "interface_record": [_IFACE], "model_inputs": [_MODEL]}
_TOKENS = [b"{", b"}", b"[", b"]", b'"', b":", b",", b"null", b"true", b"false", b"-0", b"1e999",
           b"NaN", b"\\u0000", b"\xff", b'"layers"', b'"schema"', b"9" * 30, b" " * 64]


def mutate(r: random.Random, data: bytes) -> bytes:
    b = bytearray(data)
    for _ in range(r.randint(1, 6)):
        op = r.randrange(6)
        pos = r.randrange(len(b) + 1)
        if op == 0 and b:
            b[min(pos, len(b) - 1)] = r.randrange(256)
        elif op == 1:
            b[pos:pos] = r.choice(_TOKENS)
        elif op == 2 and b:
            del b[pos:pos + r.randint(1, 16)]
        elif op == 3 and b:
            s = r.randrange(len(b)); b[pos:pos] = b[s:s + r.randint(1, 32)]
        elif op == 4:
            b[pos:pos] = bytes(r.randrange(256) for _ in range(r.randint(1, 8)))
        else:
            b = bytearray(b[: r.randrange(len(b) + 1)])
    return bytes(b)
