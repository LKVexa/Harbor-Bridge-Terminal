"""Component 19 - versioned wire schemas PK_DYN_LEASE/1, PK_DYN_SCALE/1,
PK_DYN_COST/1.

* Schemas live in ``production/schemas/*.json`` (a JSON-Schema subset:
  type, const, enum, required, properties, additionalProperties, minimum,
  maximum, minLength, maxLength, pattern, items, maxItems).
* ``validate`` is a small stdlib validator for exactly that subset; unknown
  schema keywords are rejected so the subset cannot silently widen.
* Canonical encoding = ``core.canonical`` (sorted keys, compact, UTF-8, no NaN);
  ``encode`` validates before encoding, ``decode`` validates after parsing.
* Cross-field invariants beyond JSON-Schema are in ``SEMANTIC_RULES``.
* Evolution: ``schema`` major is in the name (``/1``); ``schema_minor`` grows
  on additive optional fields.  Receivers ignore ``ext`` contents (tolerant
  reader) and accept any minor of a major they support.
* ``negotiate`` picks the highest common major per interface.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .core import canonical, digest
from .errors_catalog import error

SCHEMA_DIR = Path(__file__).parent / "schemas"
INTERFACES = ("PK_DYN_LEASE", "PK_DYN_SCALE", "PK_DYN_COST")
SUPPORTED = {"PK_DYN_LEASE": (1,), "PK_DYN_SCALE": (1,), "PK_DYN_COST": (1,)}
_KEYWORDS = {"$id", "title", "type", "const", "enum", "required", "properties",
             "additionalProperties", "minimum", "maximum", "minLength", "maxLength",
             "pattern", "items", "maxItems"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool}
MAX_DEPTH = 16


def load(name: str) -> dict:
    """``name`` like 'PK_DYN_LEASE/1'."""
    iface, _, major = name.partition("/")
    if iface not in SUPPORTED or not major.isdigit() or int(major) not in SUPPORTED[iface]:
        raise error("INV08.SCHEMA.UNSUPPORTED_VERSION", f"no schema {name!r}")
    return json.loads((SCHEMA_DIR / f"{iface}_{major}.json").read_text("utf-8"))


def _is_type(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def check_schema(s: dict, depth: int = 0) -> None:
    bad = set(s) - _KEYWORDS
    if bad:
        raise ValueError(f"unsupported schema keywords {sorted(bad)}")
    for sub in s.get("properties", {}).values():
        check_schema(sub, depth + 1)
    if "items" in s:
        check_schema(s["items"], depth + 1)


def validate(inst: Any, s: dict, path: str = "$", depth: int = 0) -> list[str]:
    errs: list[str] = []
    if depth > MAX_DEPTH:
        return [f"{path}: nesting too deep"]
    if "const" in s and inst != s["const"]:
        errs.append(f"{path}: expected const {s['const']!r}")
    if "enum" in s and inst not in s["enum"]:
        errs.append(f"{path}: {inst!r} not in enum")
    t = s.get("type")
    if t and not _is_type(inst, t):
        return errs + [f"{path}: expected {t}"]
    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if "minimum" in s and inst < s["minimum"]:
            errs.append(f"{path}: below minimum {s['minimum']}")
        if "maximum" in s and inst > s["maximum"]:
            errs.append(f"{path}: above maximum {s['maximum']}")
    if isinstance(inst, str):
        if "minLength" in s and len(inst) < s["minLength"]:
            errs.append(f"{path}: shorter than {s['minLength']}")
        if "maxLength" in s and len(inst) > s["maxLength"]:
            errs.append(f"{path}: longer than {s['maxLength']}")
        if "pattern" in s and not re.search(s["pattern"], inst):
            errs.append(f"{path}: does not match {s['pattern']}")
    if isinstance(inst, list):
        if "maxItems" in s and len(inst) > s["maxItems"]:
            errs.append(f"{path}: more than {s['maxItems']} items")
        if "items" in s:
            for i, v in enumerate(inst):
                errs += validate(v, s["items"], f"{path}[{i}]", depth + 1)
    if isinstance(inst, dict):
        for k in s.get("required", []):
            if k not in inst:
                errs.append(f"{path}: missing required {k!r}")
        props = s.get("properties", {})
        for k, v in inst.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}", depth + 1)
            elif s.get("additionalProperties", True) is False:
                errs.append(f"{path}: unexpected property {k!r}")
    return errs


SEMANTIC_RULES = {
    "PK_DYN_LEASE/1": "expires_at > issued_at",
    "PK_DYN_SCALE/1": "reclaimed and renewed each contain unique node ids",
    "PK_DYN_COST/1": "interval_end >= interval_start",
}


def _semantic(msg: dict) -> list[str]:
    name = msg.get("schema")
    if name == "PK_DYN_LEASE/1" and msg["expires_at"] <= msg["issued_at"]:
        return ["$: expires_at must be > issued_at"]
    if name == "PK_DYN_SCALE/1":
        e = []
        for f in ("reclaimed", "renewed"):
            if len(set(msg[f])) != len(msg[f]):
                e.append(f"$.{f}: duplicate node ids")
        return e
    if name == "PK_DYN_COST/1" and msg["interval_end"] < msg["interval_start"]:
        return ["$: interval_end must be >= interval_start"]
    return []


def validate_message(msg: Any) -> list[str]:
    if not isinstance(msg, dict) or not isinstance(msg.get("schema"), str):
        return ["$: message must be an object with a 'schema' string"]
    s = load(msg["schema"])
    errs = validate(msg, s)
    return errs or _semantic(msg)


def encode(msg: dict) -> bytes:
    errs = validate_message(msg)
    if errs:
        raise error("INV08.SCHEMA.INVALID", errs[0], details={"errors": errs[:20]})
    return canonical(msg)


def decode(data: bytes, *, max_bytes: int = 1 << 20) -> dict:
    if len(data) > max_bytes:
        raise error("INV08.SCHEMA.INVALID", "message exceeds max_bytes")
    try:
        msg = json.loads(data.decode("utf-8"),
                         parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except (ValueError, UnicodeDecodeError) as exc:
        raise error("INV08.SCHEMA.INVALID", f"not JSON: {exc}") from None
    errs = validate_message(msg)
    if errs:
        raise error("INV08.SCHEMA.INVALID", errs[0], details={"errors": errs[:20]})
    return msg


def negotiate(offered: list[str], supported: dict = SUPPORTED) -> dict[str, str]:
    """Pick the highest common major per interface; missing interface -> error."""
    peer: dict[str, set[int]] = {}
    for o in offered:
        iface, _, m = o.partition("/")
        if m.isdigit():
            peer.setdefault(iface, set()).add(int(m))
    out = {}
    for iface in INTERFACES:
        common = peer.get(iface, set()) & set(supported.get(iface, ()))
        if not common:
            raise error("INV08.SCHEMA.UNSUPPORTED_VERSION", f"no common version for {iface}",
                        details={"offered": sorted(offered)})
        out[iface] = f"{iface}/{max(common)}"
    return out


def fixture_digest(msg: dict) -> str:
    return digest(msg)
