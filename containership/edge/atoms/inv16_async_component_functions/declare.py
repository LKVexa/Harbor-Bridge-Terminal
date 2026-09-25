"""Build-time async declaration pipeline: interface text -> PK_ASYNC_DECL/1 (closure item #3).

This is the INV-16 side of the INV-11 contract.  ``parse_interface`` is a
*reference surrogate* for the INV-11 interface-language front end: it accepts
the declaration subset INV-16 consumes and produces the canonical descriptor
that the runtime is built from (``AsyncFunctions.from_descriptor``).  When the
real INV-11 compiler is supplied it must emit a byte-identical descriptor for
the golden fixtures in ``fixtures/interfaces`` (see ``tests/test_declare.py``).

Grammar (one statement per line, ``//`` comments)::

    package <ns>:<name>@<semver>;
    interface <ident> {
        [async] func <ident>;
    }
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping

DECL_SCHEMA = "PK_ASYNC_DECL/1"
SUPPORTED_DECL_SCHEMAS = frozenset({DECL_SCHEMA})
_IDENT = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
_PKG = re.compile(rf"^package\s+({_IDENT}):({_IDENT})@(\d+\.\d+\.\d+)\s*;$")
_IFACE = re.compile(rf"^interface\s+({_IDENT})\s*\{{$")
_FUNC = re.compile(rf"^(async\s+)?func\s+({_IDENT})\s*;$")


class DeclarationError(ValueError):
    def __init__(self, message: str, line: int | None = None):
        super().__init__(f"line {line}: {message}" if line else message)
        self.line = line


def parse_interface(text: str, source: str = "<memory>") -> dict:
    """Parse interface text into a canonical, frozen-ready descriptor dict."""
    package = None
    iface = None
    functions: dict[str, dict] = {}
    seen_ifaces: set[str] = set()
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue
        if package is None:
            m = _PKG.match(line)
            if not m:
                raise DeclarationError("expected 'package ns:name@x.y.z;'", lineno)
            package = f"{m.group(1)}:{m.group(2)}@{m.group(3)}"
            continue
        if iface is None:
            m = _IFACE.match(line)
            if not m:
                raise DeclarationError("expected 'interface <name> {'", lineno)
            iface = m.group(1)
            if iface in seen_ifaces:
                raise DeclarationError(f"duplicate interface {iface!r}", lineno)
            seen_ifaces.add(iface)
            continue
        if line == "}":
            iface = None
            continue
        m = _FUNC.match(line)
        if not m:
            raise DeclarationError(f"malformed declaration {line!r}", lineno)
        qname = f"{package.split('@')[0]}/{iface}#{m.group(2)}"
        if qname in functions:
            raise DeclarationError(f"duplicate function {qname!r}", lineno)
        functions[qname] = {"async": bool(m.group(1)), "line": lineno}
    if package is None:
        raise DeclarationError("missing package declaration")
    if iface is not None:
        raise DeclarationError(f"unterminated interface {iface!r}")
    if not functions:
        raise DeclarationError("no functions declared")
    return {"schema": DECL_SCHEMA, "package": package, "source": source,
            "functions": dict(sorted(functions.items()))}


def canonical_bytes(descriptor: Mapping) -> bytes:
    """Canonical JSON of the *semantic* fields (source path and lines excluded)."""
    semantic = {
        "schema": descriptor["schema"], "package": descriptor["package"],
        "functions": {k: {"async": v["async"]} for k, v in sorted(descriptor["functions"].items())},
    }
    return json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()


def digest(descriptor: Mapping) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(descriptor)).hexdigest()


def verify_descriptor(descriptor: Mapping, expected_digest: str | None = None) -> str:
    """Validate schema/shape and (optionally) detect drift from the build artifact."""
    if not isinstance(descriptor, Mapping):
        raise DeclarationError("descriptor must be a mapping")
    if descriptor.get("schema") not in SUPPORTED_DECL_SCHEMAS:
        raise DeclarationError(f"unsupported declaration schema {descriptor.get('schema')!r}")
    fns = descriptor.get("functions")
    if not isinstance(fns, Mapping) or not fns:
        raise DeclarationError("descriptor has no functions")
    for name, meta in fns.items():
        if not isinstance(name, str) or "#" not in name or not isinstance(meta, Mapping) \
                or not isinstance(meta.get("async"), bool):
            raise DeclarationError(f"malformed function entry {name!r}")
    d = digest(descriptor)
    if expected_digest is not None and d != expected_digest:
        raise DeclarationError(f"declaration drift: built {expected_digest}, runtime sees {d}")
    return d


def compare(old: Mapping, new: Mapping) -> dict[str, list[str]]:
    """Classify interface evolution.  Anything in ``breaking`` must fail composition."""
    o, n = old["functions"], new["functions"]
    out: dict[str, list[str]] = {"added": [], "removed": [], "sync_to_async": [],
                                 "async_to_sync": [], "unchanged": []}
    for k in sorted(set(o) | set(n)):
        if k not in n:
            out["removed"].append(k)
        elif k not in o:
            out["added"].append(k)
        elif o[k]["async"] == n[k]["async"]:
            out["unchanged"].append(k)
        elif n[k]["async"]:
            out["sync_to_async"].append(k)
        else:
            out["async_to_sync"].append(k)
    out["breaking"] = out["removed"] + out["sync_to_async"] + out["async_to_sync"]
    return out
