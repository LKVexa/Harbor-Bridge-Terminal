"""Package/world identity model and use/include/import resolver (INV11-MC-03/04).

Canonical identifiers (docs/IDENTITY.md):
  package    ns:name[@ver]
  interface  ns:name/iface[@ver]
  world      ns:name/world[@ver]            (worlds and interfaces share one namespace)
  type       <interface-or-world-id>#type
  function   <interface-id>.func | <type-id>.method
A version-less reference resolves only when exactly one version of the package
is available; otherwise it is an E-RES-PACKAGE conflict (never "latest wins").
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from . import ast
from .diagnostics import DiagnosticBag, Span
from .limits import DEFAULT_LIMITS, Limits
from .parser import ParseConfig, ParseResult, parse_sources
from .source import load_path


def pkg_id(ns: str, name: str, ver: str | None) -> str:
    return f"{ns}:{name}" + (f"@{ver}" if ver else "")


def item_id(pkg: tuple[str, str, str | None], item: str) -> str:
    ns, name, ver = pkg
    return f"{ns}:{name}/{item}" + (f"@{ver}" if ver else "")


_VER = re.compile(r"@\d+\.\d+\.\d+(?:[-+][0-9A-Za-z-]+(?:\.[0-9][0-9A-Za-z-]*)*)*")


def unversioned(ident: str) -> str:
    """Strip every `@version` from an id, keeping the path and member suffix.

    Limitation (docs/IDENTITY.md): a pre-release identifier after a dot must
    start with a digit to be distinguished from a member name (`@1.0.0-rc.1.f`).
    """
    return _VER.sub("", ident)


@dataclass
class Resolved:
    packages: dict[str, dict[str, Any]] = field(default_factory=dict)
    interfaces: dict[str, dict[str, Any]] = field(default_factory=dict)
    worlds: dict[str, dict[str, Any]] = field(default_factory=dict)
    types: dict[str, dict[str, Any]] = field(default_factory=dict)
    gates: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    root_package: str | None = None
    diagnostics: DiagnosticBag = field(default_factory=DiagnosticBag)
    spans: dict[str, Span] = field(default_factory=dict, repr=False)
    cache: dict[str, str] = field(default_factory=dict, repr=False, compare=False)

    @property
    def ok(self) -> bool:
        return not self.diagnostics.errors


class _Pkg:
    def __init__(self, ident: tuple[str, str, str | None]):
        self.ident = ident
        self.interfaces: dict[str, ast.Interface] = {}
        self.worlds: dict[str, ast.World] = {}
        self.top_uses: list[ast.TopUse] = []
        self.is_dep = False


class Resolver:
    def __init__(self, diags: DiagnosticBag, limits: Limits = DEFAULT_LIMITS,
                 features: frozenset[str] = frozenset()) -> None:
        self.d, self.limits, self.features = diags, limits, frozenset(features)
        self.pkgs: dict[str, _Pkg] = {}
        self.out = Resolved(diagnostics=diags)
        self.iface_state: dict[str, str] = {}

    def active(self, gates: tuple[ast.Gate, ...]) -> bool:
        """@unstable(feature = x) items exist only when feature x is enabled."""
        return all(g.value in self.features for g in gates if g.kind == "unstable")

    # -- package grouping ---------------------------------------------
    def add_documents(self, docs: list[ast.Document], is_dep: bool = False) -> list[str]:
        flat: list[ast.Document] = []
        for doc in docs:
            flat.append(doc)
            flat.extend(doc.nested_packages)
        declared = sorted({d.package for d in docs if d.package is not None}, key=str)
        if len(declared) > 1:
            self.d.add("E-PARSE-PACKAGE", f"files declare different packages: {[pkg_id(*p) for p in declared]}",
                       next((d.package_span for d in docs if d.package_span), None))
        default = declared[0] if len(declared) == 1 else None
        touched: list[str] = []
        for doc in flat:
            ident = doc.package or (default if doc not in [n for d in docs for n in d.nested_packages] else None)
            if ident is None:
                if doc.interfaces or doc.worlds:
                    self.d.add("E-PARSE-PACKAGE", "no package declaration for these definitions", None, doc.file)
                    ident = ("local", "anonymous", None)
                else:
                    continue
            pid = pkg_id(*ident)
            pkg = self.pkgs.setdefault(pid, _Pkg(ident))
            pkg.is_dep = pkg.is_dep or is_dep
            if pid not in touched:
                touched.append(pid)
            for it in doc.interfaces:
                self._declare(pkg, it.name, it, pkg.interfaces)
            for w in doc.worlds:
                self._declare(pkg, w.name, w, pkg.worlds)
            pkg.top_uses.extend(doc.uses)
        return touched

    def _declare(self, pkg: _Pkg, name: str, node: ast.Interface | ast.World, table: dict[str, Any]) -> None:
        other = pkg.interfaces.get(name) or pkg.worlds.get(name)
        if other is not None:
            self.d.add("E-DUP-DECL", f"{name!r} declared twice in package {pkg_id(*pkg.ident)}",
                       node.span, item_id(pkg.ident, name), [other.span] if other.span else [])
            return
        table[name] = node

    # -- lookup ---------------------------------------------------------
    def find_package(self, spec: str, version: str | None, span: Span | None) -> _Pkg | None:
        cands = [p for pid, p in sorted(self.pkgs.items()) if pkg_id(p.ident[0], p.ident[1], None) == spec]
        if version is not None:
            cands = [p for p in cands if p.ident[2] == version]
        if len(cands) == 1:
            return cands[0]
        if not cands:
            self.d.add("E-RES-PACKAGE", f"package {spec}{'@' + version if version else ''} is not available", span)
        else:
            self.d.add("E-RES-PACKAGE", f"ambiguous reference to {spec}: versions {[p.ident[2] for p in cands]} available; pin one", span)
        return None

    def lookup_iface(self, here: _Pkg, path: ast.UsePath, aliases: dict[str, tuple[_Pkg, str]]) -> str | None:
        if path.package is None:
            if path.name in here.interfaces:
                return item_id(here.ident, path.name)
            if path.name in aliases:
                p, n = aliases[path.name]
                return item_id(p.ident, n)
            kind = "world" if path.name in here.worlds else None
            self.d.add("E-RES-KIND" if kind else "E-RES-UNKNOWN",
                       f"{path.name!r} is {'a world, not an interface' if kind else 'not an interface in this package'}", path.span)
            return None
        pkg = self.find_package(path.package, path.version, path.span)
        if pkg is None:
            return None
        if path.name not in pkg.interfaces:
            self.d.add("E-RES-UNKNOWN", f"interface {path.text()} not found", path.span)
            return None
        return item_id(pkg.ident, path.name)

    # -- resolution -------------------------------------------------------
    def resolve(self) -> Resolved:
        for pid in sorted(self.pkgs):
            pkg = self.pkgs[pid]
            self.out.packages[pid] = {"id": pid, "namespace": pkg.ident[0], "name": pkg.ident[1],
                                      "version": pkg.ident[2], "dependency": pkg.is_dep,
                                      "interfaces": sorted(pkg.interfaces), "worlds": sorted(pkg.worlds)}
            if not pkg.is_dep and self.out.root_package is None:
                self.out.root_package = pid
        for pid in sorted(self.pkgs):
            pkg = self.pkgs[pid]
            for name in sorted(pkg.interfaces):
                if self.active(pkg.interfaces[name].gates):
                    self.resolve_iface(pkg, name, [])
        for pid in sorted(self.pkgs):
            pkg = self.pkgs[pid]
            for name in sorted(pkg.worlds):
                if self.active(pkg.worlds[name].gates):
                    self.resolve_world(pkg, name, [])
        self.own_bare_resources()
        self.check_type_cycles()
        return self.out

    def own_bare_resources(self) -> None:
        """A bare resource name in type position means own<R> (WIT spec)."""
        types = self.out.types

        def fix(v: Any) -> Any:
            if isinstance(v, dict):
                if set(v) == {"ref"} and types.get(v["ref"], {}).get("kind") == "resource":
                    return {"own": v["ref"]}
                return {k: fix(x) for k, x in v.items()}
            if isinstance(v, list):
                return [fix(x) for x in v]
            return v

        for k in list(types):
            if types[k]["kind"] != "alias":
                types[k] = fix(types[k])
        for i in self.out.interfaces.values():
            i["functions"] = fix(i["functions"])
        for w in self.out.worlds.values():
            w["imports"], w["exports"] = fix(w["imports"]), fix(w["exports"])

    def aliases(self, pkg: _Pkg) -> dict[str, tuple[_Pkg, str]]:
        out: dict[str, tuple[_Pkg, str]] = {}
        for u in pkg.top_uses:
            if u.path.package is None:
                continue
            p = self.find_package(u.path.package, u.path.version, u.path.span)
            if p and u.path.name in p.interfaces:
                out[u.alias or u.path.name] = (p, u.path.name)
        return out

    def resolve_iface(self, pkg: _Pkg, name: str, stack: list[str]) -> str | None:
        iid = item_id(pkg.ident, name)
        state = self.iface_state.get(iid)
        if state == "done":
            return iid
        if state == "active":
            cyc = stack[stack.index(iid):] + [iid]
            self.d.add("E-RES-CYCLE", f"interface use cycle: {' -> '.join(cyc)}", pkg.interfaces[name].span, iid)
            return None
        self.iface_state[iid] = "active"
        node = pkg.interfaces[name]
        scope, uses = self.build_scope(pkg, iid, node.types, node.uses, stack + [iid])
        funcs: dict[str, Any] = {}
        for f in node.funcs:
            if not self.active(f.gates):
                continue
            if f.name in funcs or f.name in scope:
                self.d.add("E-DUP-DECL", f"duplicate item {f.name!r} in {iid}", f.span, f"{iid}.{f.name}")
                continue
            funcs[f.name] = self.func(f, scope, f"{iid}.{f.name}")
            self.record_gates(f"{iid}.{f.name}", f.gates)
            if f.span:
                self.out.spans[f"{iid}.{f.name}"] = f.span
        self.out.interfaces[iid] = {"id": iid, "package": pkg_id(*pkg.ident), "name": name,
                                    "types": sorted(k for k, v in scope.items() if v.startswith(iid + "#")),
                                    "uses": uses, "functions": funcs,
                                    "scope": dict(sorted(scope.items()))}
        self.record_gates(iid, node.gates)
        if node.span:
            self.out.spans[iid] = node.span
        self.iface_state[iid] = "done"
        return iid

    def build_scope(self, pkg: _Pkg, owner: str, types: Sequence[ast.TypeDecl],
                    uses: Sequence[ast.Use], stack: list[str]) -> tuple[dict[str, str], list[str]]:
        scope: dict[str, str] = {}
        spans: dict[str, Any] = {}
        used: list[str] = []
        aliases = self.aliases(pkg)
        for u in uses:
            target = self.lookup_iface(pkg, u.path, aliases)
            if target is None:
                continue
            # resolve target interface first (cycle detection)
            tp = self._pkg_of(target)
            self.resolve_iface(tp, target.split("/", 1)[1].split("@")[0], stack)
            used.append(target)
            titem = self.out.interfaces.get(target)
            for orig, local in u.names:
                if titem is None:
                    continue
                if orig not in titem["scope"]:
                    self.d.add("E-RES-UNKNOWN", f"{orig!r} is not a type of {target}", u.span, owner)
                    continue
                if local in scope:
                    self.d.add("E-DUP-DECL", f"name {local!r} imported twice", u.span, owner, [spans[local]] if spans.get(local) else [])
                    continue
                scope[local] = titem["scope"][orig]
                spans[local] = u.span
        types = [t for t in types if self.active(t.gates)]
        for t in types:
            if t.name in scope:
                self.d.add("E-DUP-DECL", f"type {t.name!r} declared twice", t.span, f"{owner}#{t.name}",
                           [spans[t.name]] if spans.get(t.name) else [])
                continue
            scope[t.name] = f"{owner}#{t.name}"
            spans[t.name] = t.span
        for t in types:
            key = f"{owner}#{t.name}"
            if key in self.out.types:
                continue
            self.out.types[key] = self.typedef(t, scope, key)
            self.record_gates(key, t.gates)
            if t.span:
                self.out.spans[key] = t.span
        return scope, sorted(set(used))

    def _pkg_of(self, ident: str) -> _Pkg:
        head = ident.split("/", 1)[0]
        ver = ident.split("@", 1)[1] if "@" in ident else None
        return self.pkgs[head + (f"@{ver}" if ver else "")]

    def record_gates(self, key: str, gates: tuple[ast.Gate, ...]) -> None:
        if gates:
            self.out.gates[key] = [{"kind": g.kind, "value": g.value} for g in gates]

    def typeref(self, t: ast.Type, scope: dict[str, str], where: str) -> Any:
        if isinstance(t, ast.Prim):
            return t.name
        if isinstance(t, ast.Ref):
            if t.name not in scope:
                self.d.add("E-RES-UNKNOWN", f"unknown type {t.name!r}", t.span, where)
                return {"ref": "?" + t.name}
            return {"ref": scope[t.name]}
        if isinstance(t, ast.ListT):
            out = {"list": self.typeref(t.elem, scope, where)}
            if t.size is not None:
                out["size"] = t.size
            return out
        if isinstance(t, ast.OptionT):
            return {"option": self.typeref(t.inner, scope, where)}
        if isinstance(t, ast.ResultT):
            return {"result": {"ok": self.typeref(t.ok, scope, where) if t.ok else None,
                               "err": self.typeref(t.err, scope, where) if t.err else None}}
        if isinstance(t, ast.TupleT):
            return {"tuple": [self.typeref(x, scope, where) for x in t.items]}
        if isinstance(t, ast.Handle):
            if t.resource not in scope:
                self.d.add("E-RES-UNKNOWN", f"unknown resource {t.resource!r}", t.span, where)
                return {t.mode: "?" + t.resource}
            return {t.mode: scope[t.resource]}
        if isinstance(t, ast.AsyncT):
            return {t.kind: self.typeref(t.inner, scope, where) if t.inner else None}
        raise TypeError(t)  # pragma: no cover

    def func(self, f: ast.Func, scope: dict[str, str], where: str) -> dict[str, Any]:
        return {"kind": f.kind, "async": f.is_async,
                "params": [[p.name, self.typeref(p.type, scope, where)] for p in f.params],
                "result": self.typeref(f.result, scope, where) if f.result else None}

    def typedef(self, t: ast.TypeDecl, scope: dict[str, str], key: str) -> dict[str, Any]:
        if t.kind == "alias":
            assert t.target is not None
            return {"kind": "alias", "target": self.typeref(t.target, scope, key)}
        if t.kind == "record":
            return {"kind": "record", "fields": [[m.name, self.typeref(m.type, scope, key) if m.type else None] for m in t.members]}
        if t.kind == "variant":
            return {"kind": "variant", "cases": [[m.name, self.typeref(m.type, scope, key) if m.type else None] for m in t.members]}
        if t.kind in ("enum", "flags"):
            return {"kind": t.kind, "cases": [m.name for m in t.members]}
        methods: dict[str, Any] = {}
        for f in t.funcs:
            if not self.active(f.gates):
                continue
            methods[f.name] = self.func(f, scope, f"{key}.{f.name}")
            self.record_gates(f"{key}.{f.name}", f.gates)
        for m in t.members:
            self.record_gates(f"{key}.{m.name}", m.gates)
        return {"kind": "resource", "methods": methods}

    def resolve_world(self, pkg: _Pkg, name: str, stack: list[str]) -> dict[str, Any] | None:
        wid = item_id(pkg.ident, name)
        if wid in self.out.worlds:
            return self.out.worlds[wid]
        if wid in stack:
            self.d.add("E-RES-CYCLE", f"world include cycle: {' -> '.join(stack[stack.index(wid):] + [wid])}", pkg.worlds[name].span, wid)
            return None
        node = pkg.worlds[name]
        aliases = self.aliases(pkg)
        scope, uses = self.build_scope(pkg, wid, node.types, node.uses, [])
        imports: dict[str, Any] = {}
        exports: dict[str, Any] = {}
        for it in node.items:
            if not self.active(it.gates):
                continue
            table = imports if it.direction == "import" else exports
            val: dict[str, Any]
            if it.kind == "interface-ref":
                assert it.ref is not None
                target = self.lookup_iface(pkg, it.ref, aliases)
                if target is None:
                    continue
                key, val = target, {"kind": "interface", "ref": target}
            elif it.kind == "inline-interface":
                assert it.inline is not None
                inline_id = f"{wid}/{it.direction}/{it.name}"
                iscope = dict(scope)
                for u in it.inline.uses:
                    t = self.lookup_iface(pkg, u.path, aliases)
                    if t and t in self.out.interfaces:
                        for o, local in u.names:
                            if o in self.out.interfaces[t]["scope"]:
                                iscope[local] = self.out.interfaces[t]["scope"][o]
                funcs = {f.name: self.func(f, iscope, f"{inline_id}.{f.name}") for f in it.inline.funcs}
                key, val = it.name, {"kind": "inline-interface", "functions": funcs}
            else:
                assert it.func is not None
                key, val = it.name, {"kind": "func", "sig": self.func(it.func, scope, f"{wid}.{it.name}")}
            if key in table:
                self.d.add("E-DUP-DECL", f"{key!r} imported/exported twice in world {wid}", it.span, wid)
                continue
            table[key] = val
            self.record_gates(f"{wid}:{it.direction}:{key}", it.gates)
        for inc in node.includes:
            if inc.path.package is None:
                if inc.path.name not in pkg.worlds:
                    self.d.add("E-RES-UNKNOWN", f"world {inc.path.name!r} not found", inc.span, wid)
                    continue
                other = self.resolve_world(pkg, inc.path.name, stack + [wid])
            else:
                opkg = self.find_package(inc.path.package, inc.path.version, inc.span)
                if opkg is None or inc.path.name not in opkg.worlds:
                    if opkg is not None:
                        self.d.add("E-RES-UNKNOWN", f"world {inc.path.text()} not found", inc.span, wid)
                    continue
                other = self.resolve_world(opkg, inc.path.name, stack + [wid])
            if other is None:
                continue
            ren = dict(inc.renames)
            for tgt, src_tbl in ((imports, other["imports"]), (exports, other["exports"])):
                for k, v in src_tbl.items():
                    nk = ren.get(k, k)
                    if nk in tgt and tgt[nk] != v:
                        self.d.add("E-DUP-DECL", f"include of {inc.path.text()} conflicts on {nk!r}; rename with `with {{ {nk} as ... }}`", inc.span, wid)
                        continue
                    tgt[nk] = v
        w = {"id": wid, "package": pkg_id(*pkg.ident), "name": name, "uses": uses,
             "types": sorted(k for k, v in scope.items() if v.startswith(wid + "#")),
             "imports": dict(sorted(imports.items())), "exports": dict(sorted(exports.items()))}
        self.out.worlds[wid] = w
        self.record_gates(wid, node.gates)
        return w

    def check_type_cycles(self) -> None:
        types = self.out.types
        state: dict[str, int] = {}

        def refs(v: Any) -> Any:
            if isinstance(v, dict):
                if "ref" in v and len(v) == 1:
                    yield v["ref"]
                    return
                for k, x in v.items():
                    if k in ("own", "borrow", "methods"):
                        continue  # handles/resources are nominal: they break cycles
                    yield from refs(x)
            elif isinstance(v, list):
                for x in v:
                    yield from refs(x)

        def visit(k: str, path: list[str]) -> None:
            if state.get(k) == 2 or k not in types:
                return
            if state.get(k) == 1:
                self.d.add("E-RES-TYPECYCLE", f"recursive type: {' -> '.join(path[path.index(k):] + [k])}", self.out.spans.get(k), k)
                return
            state[k] = 1
            for r in refs(types[k]):
                visit(r, path + [k])
            state[k] = 2

        for k in sorted(types):
            visit(k, [])
        # handle targets must be resources (aliases followed)
        def target(k: str, n: int = 0) -> dict[str, Any] | None:
            t = types.get(k)
            while t is not None and t["kind"] == "alias" and isinstance(t["target"], dict) and "ref" in t["target"] and n < 64:
                t, n = types.get(t["target"]["ref"]), n + 1
            return t

        def handles(v: Any) -> Any:
            if isinstance(v, dict):
                for m in ("own", "borrow"):
                    if m in v and isinstance(v[m], str):
                        yield v[m]
                for x in v.values():
                    yield from handles(x)
            elif isinstance(v, list):
                for x in v:
                    yield from handles(x)

        everything = list(types.items()) + [(k, i["functions"]) for k, i in self.out.interfaces.items()]
        for k, v in everything:
            for h in handles(v):
                t = target(h)
                if not h.startswith("?") and (t is None or t["kind"] != "resource"):
                    self.d.add("E-RES-HANDLE", f"own/borrow of non-resource {h}", self.out.spans.get(k), k)


def resolve_documents(docs: list[ast.Document], deps: Sequence[list[ast.Document]] = (),
                      diags: DiagnosticBag | None = None, limits: Limits = DEFAULT_LIMITS,
                      features: frozenset[str] = frozenset()) -> Resolved:
    diags = diags or DiagnosticBag(limits.max_diagnostics)
    r = Resolver(diags, limits, features)
    for dep in deps:
        r.add_documents(dep, is_dep=True)
    r.add_documents(docs)
    return r.resolve()


def load_package(path: str, config: ParseConfig | None = None,
                 features: frozenset[str] = frozenset()) -> tuple[ParseResult, Resolved]:
    """Load a WIT package directory (or single file) plus its `deps/` tree."""
    import os
    config = config or ParseConfig()
    diags = DiagnosticBag(config.limits.max_diagnostics)
    main = parse_sources(load_path(path, diags, config.limits), config, diags)
    dep_docs: list[list[ast.Document]] = []
    depdir = os.path.join(path, "deps") if os.path.isdir(path) else None
    if depdir and os.path.isdir(depdir):
        for entry in sorted(os.listdir(depdir)):
            p = os.path.join(depdir, entry)
            if os.path.isdir(p) or entry.endswith(".wit"):
                pr = parse_sources(load_path(p, diags, config.limits, root=depdir), config, diags)
                main.fatal = main.fatal or pr.fatal
                dep_docs.append(pr.documents)
    res = resolve_documents(main.documents, dep_docs, diags, config.limits, features)
    return main, res
