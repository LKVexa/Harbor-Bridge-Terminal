"""Shared test bootstrap: stdlib only, imports the package from its parent folder."""
from __future__ import annotations

import os
import pathlib
import random
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEED = int(os.environ.get("INV41_SEED", "4130"))
ITERATIONS = int(os.environ.get("INV41_ITER", "300"))


def rng(offset: int = 0) -> random.Random:
    return random.Random(SEED + offset)


def check_schema(instance, schema) -> list:
    """Minimal JSON-Schema subset validator (type/required/additionalProperties/const/minLength/enum/properties)."""
    errs = []
    t = schema.get("type")
    types = {"object": dict, "string": str, "boolean": bool, "integer": int, "array": list, "number": (int, float)}
    if t and not isinstance(instance, types[t]) or (t == "integer" and isinstance(instance, bool)):
        return [f"type {t}"]
    if "const" in schema and instance != schema["const"]:
        errs.append("const")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append("enum")
    if t == "string" and len(instance) < schema.get("minLength", 0):
        errs.append("minLength")
    if t == "object":
        for r in schema.get("required", []):
            if r not in instance:
                errs.append(f"required {r}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            errs += [f"additional {k}" for k in instance if k not in props]
        for k, sub in props.items():
            if k in instance:
                errs += [f"{k}.{e}" for e in check_schema(instance[k], sub)]
    return errs
