"""WIT-subset parser, interface inventory and structural diff (MC-11, MC-12).

Supports the subset needed for inventory and structural comparison:
``package ns:name@ver;``, ``interface x { ... }`` containing ``func``,
``record``, ``enum``, ``flags``, ``variant``, ``resource`` and ``type``
items, and ``world w { import ns:pkg/iface; export ...; }``.  Anything outside
the subset raises rather than being guessed at.  The diff only ever
auto-classifies *provably identical* interfaces; everything else is emitted
as ``needs_review`` for a human decision (never guessed shimmable/divergent).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import canonical
from .errors import Inv22Error

_PKG = re.compile(r"^package\s+([a-z][a-z0-9-]*):([a-z][a-z0-9-]*)(?:@([0-9A-Za-z.\-+]+))?\s*;")
_IFACE = re.compile(r"^interface\s+([a-z][a-z0-9-]*)\s*\{")
_WORLD = re.compile(r"^world\s+([a-z][a-z0-9-]*)\s*\{")
_ITEM = re.compile(r"^(record|enum|flags|variant|resource)\s+([a-z][a-z0-9-]*)\s*\{")
_TYPE = re.compile(r"^type\s+([a-z][a-z0-9-]*)\s*=\s*([^;]+);")
_FUNC = re.compile(r"^([a-z][a-z0-9-]*)\s*:\s*func\s*(\([^;]*);")
_USE = re.compile(r"^use\s+[^;]+;")
_IMPORT = re.compile(r"^(import|export)\s+([a-z][a-z0-9-]*:[a-z][a-z0-9-]*/[a-z][a-z0-9-]*)(?:@[0-9A-Za-z.\-+]+)?\s*;")


def _err(msg: str, **d) -> Inv22Error:
    return Inv22Error("INV22.VALIDATION.SCHEMA", f"WIT: {msg}", d)


def _strip(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    return re.sub(r"\s+", " ", src).strip()


def _block(text: str, start: int) -> tuple[str, int]:
    """Return body between the brace at ``start`` and its match, plus end index."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i].strip(), i + 1
    raise _err("unbalanced braces")


def _norm(sig: str) -> str:
    return re.sub(r"\s*([(),:<>{}=;-])\s*", r"\1", sig.strip()).replace("->", " -> ")


@dataclass
class Package:
    namespace: str
    name: str
    version: str | None
    interfaces: dict[str, dict[str, str]] = field(default_factory=dict)
    worlds: dict[str, list[str]] = field(default_factory=dict)

    def iface_id(self, iface: str) -> str:
        return f"{self.namespace}:{self.name}/{iface}"


def parse(src: str, *, max_bytes: int = 1_048_576) -> Package:
    if len(src.encode("utf-8")) > max_bytes:
        raise Inv22Error("INV22.VALIDATION.LIMIT", "WIT source too large")
    text = _strip(src)
    m = _PKG.match(text)
    if not m:
        raise _err("missing package declaration")
    pkg = Package(m.group(1), m.group(2), m.group(3))
    pos = m.end()
    while pos < len(text):
        rest = text[pos:].lstrip()
        pos = len(text) - len(rest)
        if not rest:
            break
        mi, mw = _IFACE.match(rest), _WORLD.match(rest)
        hit = mi or mw
        if hit is not None:
            name = hit.group(1)
            body, end = _block(text, pos + rest.index("{"))
            if mi:
                if name in pkg.interfaces:
                    raise _err("duplicate interface", interface=name)
                pkg.interfaces[name] = _items(body)
            else:
                pkg.worlds[name] = _world(body)
            pos = end
            continue
        raise _err("unsupported top-level syntax", near=rest[:40])
    return pkg


def _items(body: str) -> dict[str, str]:
    items: dict[str, str] = {}
    pos = 0
    while pos < len(body):
        rest = body[pos:].lstrip()
        pos = len(body) - len(rest)
        if not rest:
            break
        for rx, kind in ((_ITEM, None), (_TYPE, "type"), (_FUNC, "func"), (_USE, "use")):
            m = rx.match(rest)
            if not m:
                continue
            if kind is None:
                inner, end = _block(body, pos + rest.index("{"))
                key, sig = m.group(2), f"{m.group(1)}{{{_norm(inner)}}}"
                pos = end
            elif kind == "use":
                key, sig = "use:" + _norm(m.group(0)), _norm(m.group(0))
                pos += m.end()
            else:
                key = m.group(1)
                sig = ("type=" + _norm(m.group(2))) if kind == "type" else ("func" + _norm(m.group(2)))
                pos += m.end()
            if key in items:
                raise _err("duplicate item", item=key)
            items[key] = sig
            break
        else:
            raise _err("unsupported interface item", near=rest[:40])
    return items


def _world(body: str) -> list[str]:
    refs = []
    for stmt in filter(None, (s.strip() for s in body.split(";"))):
        m = _IMPORT.match(stmt + ";")
        if not m:
            raise _err("unsupported world item", near=stmt[:40])
        if m.group(1) == "import":
            refs.append(m.group(2))
    return refs


def inventory(pkg: Package) -> list[dict]:
    """Every interface defined by a package, with version and structural digest."""
    return [{"interface": pkg.iface_id(n), "version": pkg.version or "unversioned",
             "items": len(items), "digest": canonical.digest(items)}
            for n, items in sorted(pkg.interfaces.items())]


def workload_imports(pkg: Package) -> list[str]:
    """Interfaces a workload world actually imports (reachability for completeness)."""
    return sorted({ref for refs in pkg.worlds.values() for ref in refs})


def diff(standards: Package, fork: Package, aliases: dict[str, str] | None = None) -> list[dict]:
    """Structural diff.  ``aliases`` maps a fork interface name to a standards one (reviewed)."""
    aliases = dict(aliases or {})
    fork_by_std = {}
    for fname, items in fork.interfaces.items():
        target = aliases.get(fname, fname)
        if target in fork_by_std:
            raise _err("ambiguous alias mapping", interface=target)
        fork_by_std[target] = (fname, items)
    out = []
    for name in sorted(set(standards.interfaces) | set(fork_by_std)):
        s = standards.interfaces.get(name)
        f = fork_by_std.get(name)
        iid = standards.iface_id(name)
        if s is None:
            out.append({"interface": iid, "status": "needs_review", "changes": [{"kind": "added_in_fork"}]})
            continue
        if f is None:
            out.append({"interface": iid, "status": "needs_review", "changes": [{"kind": "removed_in_fork"}]})
            continue
        fitems = f[1]
        changes = []
        for key in sorted(set(s) | set(fitems)):
            if key not in fitems:
                changes.append({"kind": "item_removed", "item": key})
            elif key not in s:
                changes.append({"kind": "item_added", "item": key})
            elif s[key] != fitems[key]:
                changes.append({"kind": "signature_changed", "item": key, "standards": s[key], "fork": fitems[key]})
        if f[0] != name:
            changes.append({"kind": "renamed", "fork_name": f[0]})
        out.append({"interface": iid, "status": "identical" if not changes else "needs_review", "changes": changes})
    return out


def candidate_matrix(diffs: list[dict], overrides: dict[str, dict] | None = None) -> tuple[list[dict], list[str]]:
    """Merge the diff with reviewed overrides.  Returns (entries, blocking_ids)."""
    overrides = overrides or {}
    entries, blocking = [], []
    for d in diffs:
        iid = d["interface"]
        ov = overrides.get(iid)
        if ov is not None:
            for req in ("classification", "rationale", "reviewer", "approved"):
                if not ov.get(req):
                    raise _err("override missing field", interface=iid, field=req)
            e = {"interface": iid, "classification": ov["classification"], "rationale": ov["rationale"],
                 "source_version": ov.get("source_version", "pinned"), "target_version": ov.get("target_version", "pinned")}
            if ov["classification"] == "shimmable":
                e["shim_id"] = ov.get("shim_id", "")
                e["proof_ref"] = ov.get("proof_ref", "")
            entries.append(e)
        elif d["status"] == "identical":
            entries.append({"interface": iid, "classification": "identical", "rationale": "structurally identical (auto)",
                            "source_version": "pinned", "target_version": "pinned"})
        else:
            blocking.append(iid)
    return entries, blocking
