"""Complete structural compatibility rules (INV11-MC-08) and link checking.

The rule table POLICY is the single source of truth; docs/COMPAT_POLICY.md is
generated from it and the policy corpus (tests/fixtures/policy) exercises every
row.  Versions never influence the class: only structure does.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import POLICY_VERSION
from .limits import DEFAULT_LIMITS, Limits
from .normalize import interface_fingerprint, package_fingerprint
from .resolve import Resolved, unversioned
from .typegraph import Comparator

ADDITIVE, COMPATIBLE, BREAKING = "additive", "compatible", "breaking"
RANK = {COMPATIBLE: 0, ADDITIVE: 1, BREAKING: 2}

# code -> (class, rationale)
POLICY: dict[str, tuple[str, str]] = {
    "interface-added": (ADDITIVE, "new interface; existing consumers unaffected"),
    "interface-removed": (BREAKING, "consumers importing it can no longer link"),
    "world-added": (ADDITIVE, "new world; existing targets unaffected"),
    "world-removed": (BREAKING, "components targeting it lose their contract"),
    "func-added": (ADDITIVE, "consumers that do not call it are unaffected"),
    "func-removed": (BREAKING, "callers lose the function"),
    "func-kind-changed": (BREAKING, "method/static/constructor/freestanding changes the ABI"),
    "func-async-changed": (BREAKING, "sync/async changes the canonical ABI lowering"),
    "param-count-changed": (BREAKING, "arity is part of the lowered signature"),
    "param-renamed": (BREAKING, "parameter names are part of the WIT contract and generated bindings"),
    "param-type-changed": (BREAKING, "lowered representation changes"),
    "result-changed": (BREAKING, "lifted representation changes"),
    "type-added": (ADDITIVE, "unreferenced by existing signatures"),
    "type-removed": (BREAKING, "consumers `use`-ing the type lose it"),
    "type-kind-changed": (BREAKING, "e.g. record -> variant changes representation"),
    "record-fields-changed": (BREAKING, "records are exact: add/remove/reorder/rename changes layout"),
    "record-field-type-changed": (BREAKING, "field representation changes"),
    "variant-case-added": (BREAKING, "receivers built against the old variant cannot decode the new case"),
    "variant-cases-changed": (BREAKING, "removed/renamed/reordered cases change discriminants"),
    "variant-payload-changed": (BREAKING, "case payload representation changes"),
    "enum-case-added": (BREAKING, "receivers cannot decode the new discriminant"),
    "enum-cases-changed": (BREAKING, "discriminant assignment changes"),
    "flags-added": (BREAKING, "new bits are not understood by old receivers; flag layout may widen"),
    "flags-changed": (BREAKING, "bit assignment changes"),
    "alias-retargeted-equal": (COMPATIBLE, "alias now points at a structurally identical type"),
    "alias-retargeted": (BREAKING, "alias target structure changed"),
    "resource-method-added": (ADDITIVE, "existing handle users unaffected"),
    "resource-method-removed": (BREAKING, "callers lose the method"),
    "resource-method-changed": (BREAKING, "method signature changed"),
    "world-import-added": (BREAKING, "hosts must now supply an extra import"),
    "world-import-removed": (COMPATIBLE, "hosts may keep supplying it; nothing is lost"),
    "world-import-changed": (BREAKING, "hosts must supply a different import"),
    "world-export-added": (ADDITIVE, "hosts that ignore it are unaffected"),
    "world-export-removed": (BREAKING, "hosts lose an export they may call"),
    "world-export-changed": (BREAKING, "exported item changed"),
    "named-type-swapped": (COMPATIBLE, "value types are structural in the component model; a same-shape named type is ABI-identical (bindings may rename)"),
    "gate-changed": (COMPATIBLE, "feature gates/deprecation metadata do not change structure"),
    "version-only": (COMPATIBLE, "identical structure; version strings never decide compatibility"),
}


@dataclass(frozen=True)
class Change:
    path: str
    code: str
    detail: str

    @property
    def cls(self) -> str:
        return POLICY[self.code][0]

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "class": self.cls, "detail": self.detail}


class _Differ:
    def __init__(self, old: Resolved, new: Resolved, limits: Limits) -> None:
        self.old, self.new = old, new
        self.cmp = Comparator(old, new, limits)
        self.changes: list[Change] = []

    def add(self, path: str, code: str, detail: str = "") -> None:
        self.changes.append(Change(unversioned(path), code, detail))

    def func(self, path: str, fa: dict[str, Any], fb: dict[str, Any]) -> None:
        before = len(self.cmp.swaps)
        self._func(path, fa, fb)
        seen = set()
        for a, b in self.cmp.swaps[before:]:
            if (a, b) not in seen:
                seen.add((a, b))
                self.add(path, "named-type-swapped", f"{a} -> {b}")

    def _func(self, path: str, fa: dict[str, Any], fb: dict[str, Any]) -> None:
        if fa["kind"] != fb["kind"]:
            self.add(path, "func-kind-changed", f"{fa['kind']} -> {fb['kind']}")
            return
        if fa["async"] != fb["async"]:
            self.add(path, "func-async-changed", f"{fa['async']} -> {fb['async']}")
        pa, pb = fa["params"], fb["params"]
        if len(pa) != len(pb):
            self.add(path, "param-count-changed", f"{[p[0] for p in pa]} -> {[p[0] for p in pb]}")
        else:
            for (na, ta), (nb, tb) in zip(pa, pb, strict=True):
                if na != nb:
                    self.add(f"{path}({na})", "param-renamed", f"{na} -> {nb}")
                d = self.cmp.diff(ta, tb, f"{path}({na})")
                if d:
                    self.add(f"{path}({na})", "param-type-changed", d)
        if (fa["result"] is None) != (fb["result"] is None):
            self.add(path + "->", "result-changed", f"{fa['result']} -> {fb['result']}")
        elif fa["result"] is not None:
            d = self.cmp.diff(fa["result"], fb["result"], path + "->")
            if d:
                self.add(path + "->", "result-changed", d)

    def typedef(self, path: str, ka: str, kb: str) -> None:
        da, db = self.old.types[ka], self.new.types[kb]
        if da["kind"] != db["kind"]:
            if da["kind"] == "alias" or db["kind"] == "alias":
                d = self.cmp.diff({"ref": ka}, {"ref": kb}, path)
                self.add(path, "alias-retargeted" if d else "alias-retargeted-equal", d or "")
            else:
                self.add(path, "type-kind-changed", f"{da['kind']} -> {db['kind']}")
            return
        k = da["kind"]
        if k == "alias":
            d = self.cmp.diff(da["target"], db["target"], path)
            if d:
                self.add(path, "alias-retargeted", d)
            elif da["target"] != db["target"] and unversioned(str(da["target"])) != unversioned(str(db["target"])):
                self.add(path, "alias-retargeted-equal", f"{da['target']} -> {db['target']}")
        elif k == "record":
            na, nb = [f[0] for f in da["fields"]], [f[0] for f in db["fields"]]
            if na != nb:
                self.add(path, "record-fields-changed", f"{na} -> {nb}")
            else:
                for (n, ta), (_, tb) in zip(da["fields"], db["fields"], strict=True):
                    d = self.cmp.diff(ta, tb, f"{path}.{n}")
                    if d:
                        self.add(f"{path}.{n}", "record-field-type-changed", d)
        elif k == "variant":
            na, nb = [c[0] for c in da["cases"]], [c[0] for c in db["cases"]]
            if na != nb:
                code = "variant-case-added" if nb[: len(na)] == na else "variant-cases-changed"
                self.add(path, code, f"{na} -> {nb}")
            else:
                for (n, ta), (_, tb) in zip(da["cases"], db["cases"], strict=True):
                    d = self.cmp.diff(ta, tb, f"{path}.{n}")
                    if d:
                        self.add(f"{path}.{n}", "variant-payload-changed", d)
        elif k in ("enum", "flags"):
            ca, cb = da["cases"], db["cases"]
            if ca != cb:
                grew = cb[: len(ca)] == ca
                code = {"enum": ("enum-case-added", "enum-cases-changed"),
                        "flags": ("flags-added", "flags-changed")}[k][0 if grew else 1]
                self.add(path, code, f"{ca} -> {cb}")
        else:  # resource
            ma, mb = da["methods"], db["methods"]
            for m in sorted(set(ma) - set(mb)):
                self.add(f"{path}.{m}", "resource-method-removed")
            for m in sorted(set(mb) - set(ma)):
                self.add(f"{path}.{m}", "resource-method-added")
            for m in sorted(set(ma) & set(mb)):
                before = len(self.changes)
                self.func(f"{path}.{m}", ma[m], mb[m])
                if len(self.changes) > before:
                    self.changes[before:] = [c if c.code == "func-kind-changed" else Change(c.path, "resource-method-changed", f"{c.code}: {c.detail}") for c in self.changes[before:]]

    def interface(self, ia: str, ib: str) -> None:
        a, b = self.old.interfaces[ia], self.new.interfaces[ib]
        base = unversioned(ia)
        own_a = {t: a["scope"][t] for t in a["types"]}
        own_b = {t: b["scope"][t] for t in b["types"]}
        for t in sorted(set(own_a) - set(own_b)):
            self.add(f"{base}#{t}", "type-removed")
        for t in sorted(set(own_b) - set(own_a)):
            self.add(f"{base}#{t}", "type-added")
        for t in sorted(set(own_a) & set(own_b)):
            self.typedef(f"{base}#{t}", own_a[t], own_b[t])
        fa, fb = a["functions"], b["functions"]
        for f in sorted(set(fa) - set(fb)):
            self.add(f"{base}.{f}", "func-removed")
        for f in sorted(set(fb) - set(fa)):
            self.add(f"{base}.{f}", "func-added")
        for f in sorted(set(fa) & set(fb)):
            self.func(f"{base}.{f}", fa[f], fb[f])

    def world(self, wa: str, wb: str) -> None:
        a, b = self.old.worlds[wa], self.new.worlds[wb]
        base = unversioned(wa)
        for direction in ("imports", "exports"):
            ta = {unversioned(k): v for k, v in a[direction].items()}
            tb = {unversioned(k): v for k, v in b[direction].items()}
            word = direction[:-1]
            for k in sorted(set(ta) - set(tb)):
                self.add(f"{base}:{word}:{k}", f"world-{word}-removed")
            for k in sorted(set(tb) - set(ta)):
                self.add(f"{base}:{word}:{k}", f"world-{word}-added")
            for k in sorted(set(ta) & set(tb)):
                va, vb = ta[k], tb[k]
                if va["kind"] != vb["kind"]:
                    self.add(f"{base}:{word}:{k}", f"world-{word}-changed", f"{va['kind']} -> {vb['kind']}")
                elif va["kind"] == "func":
                    before = len(self.changes)
                    self.func(f"{base}:{word}:{k}", va["sig"], vb["sig"])
                    self.changes[before:] = [Change(c.path, f"world-{word}-changed", f"{c.code}: {c.detail}") for c in self.changes[before:]]
                elif va["kind"] == "inline-interface":
                    before = len(self.changes)
                    fa, fb = va["functions"], vb["functions"]
                    for f in sorted(set(fa) ^ set(fb)):
                        self.add(f"{base}:{word}:{k}.{f}", "func-added" if f in fb else "func-removed")
                    for f in sorted(set(fa) & set(fb)):
                        self.func(f"{base}:{word}:{k}.{f}", fa[f], fb[f])
                    if word == "import":  # an import growing obliges the host
                        self.changes[before:] = [Change(c.path, "world-import-changed", f"{c.code}: {c.detail}") if c.code == "func-added" else c for c in self.changes[before:]]

    def gates(self) -> None:
        ga = {unversioned(k): v for k, v in self.old.gates.items()}
        gb = {unversioned(k): v for k, v in self.new.gates.items()}
        for k in sorted(set(ga) | set(gb)):
            if ga.get(k) != gb.get(k):
                self.add(k, "gate-changed", f"{ga.get(k)} -> {gb.get(k)}")


def _summary(changes: list[Change]) -> str:
    if not changes:
        return COMPATIBLE
    return max((c.cls for c in changes), key=RANK.__getitem__)


def _root_items(res: Resolved, table: str) -> dict[str, str]:
    return {unversioned(k): k for k, v in getattr(res, table).items() if res.packages[v["package"]]["dependency"] is False}


def classify_packages(old: Resolved, new: Resolved, limits: Limits = DEFAULT_LIMITS) -> dict[str, Any]:
    """PK_INTERFACE_DIFF/1 for two resolved package releases (all interfaces and worlds)."""
    if not old.ok or not new.ok:
        raise ValueError("refusing to classify packages that failed resolution (fail closed)")
    d = _Differ(old, new, limits)
    ia, ib = _root_items(old, "interfaces"), _root_items(new, "interfaces")
    for k in sorted(set(ia) - set(ib)):
        d.add(k, "interface-removed")
    for k in sorted(set(ib) - set(ia)):
        d.add(k, "interface-added")
    for k in sorted(set(ia) & set(ib)):
        d.interface(ia[k], ib[k])
    wa, wb = _root_items(old, "worlds"), _root_items(new, "worlds")
    for k in sorted(set(wa) - set(wb)):
        d.add(k, "world-removed")
    for k in sorted(set(wb) - set(wa)):
        d.add(k, "world-added")
    for k in sorted(set(wa) & set(wb)):
        d.world(wa[k], wb[k])
    d.gates()
    return _report(d.changes, old.root_package, new.root_package,
                   package_fingerprint(old, True), package_fingerprint(new, True))


def classify_interface(old: Resolved, old_id: str, new: Resolved, new_id: str,
                       limits: Limits = DEFAULT_LIMITS) -> dict[str, Any]:
    if unversioned(old_id) != unversioned(new_id):
        raise ValueError("cannot compare two differently named interfaces")
    d = _Differ(old, new, limits)
    d.interface(old_id, new_id)
    return _report(d.changes, old_id, new_id, interface_fingerprint(old, old_id), interface_fingerprint(new, new_id))


def _report(changes: list[Change], a: str | None, b: str | None, fa: str, fb: str) -> dict[str, Any]:
    changes = sorted(changes, key=lambda c: (c.path, c.code, c.detail))
    cls = _summary([c for c in changes if c.code != "gate-changed"]) if changes else COMPATIBLE
    if not changes:
        changes_out = [Change(unversioned(a or ""), "version-only", "structurally identical").as_dict()]
    else:
        changes_out = [c.as_dict() for c in changes]
    return {"schema": "PK_INTERFACE_DIFF/1", "policy": POLICY_VERSION, "subject": unversioned(a or ""),
            "from": a, "to": b, "class": cls, "linkable": cls != BREAKING,
            "changes": changes_out,
            "reasons": [f"{c['path']}: {c['code']}" + (f" ({c['detail']})" if c['detail'] else "") for c in changes_out],
            "fingerprints": {"from": fa, "to": fb}}


class Incompatible(TypeError):
    pass


def check_link(producer: Resolved, prod_id: str, consumer: Resolved, cons_id: str,
               limits: Limits = DEFAULT_LIMITS) -> dict[str, Any]:
    """A producer links iff every consumer-visible function is structurally identical."""
    if unversioned(prod_id) != unversioned(cons_id):
        raise Incompatible(f"producer offers {prod_id!r} but consumer expects {cons_id!r}")
    d = _Differ(consumer, producer, limits)
    cf, pf = consumer.interfaces[cons_id]["functions"], producer.interfaces[prod_id]["functions"]
    missing = sorted(set(cf) - set(pf))
    if missing:
        raise Incompatible(f"{prod_id}: producer does not offer {missing}")
    for f in sorted(cf):
        d.func(f"{unversioned(cons_id)}.{f}", cf[f], pf[f])
    if d.changes:
        raise Incompatible("; ".join(f"{c.path}: {c.code} {c.detail}" for c in d.changes))
    return {"schema": "PK_INTERFACE/1", "interface": unversioned(cons_id), "producer": prod_id,
            "consumer": cons_id, "linked": True, "functions": sorted(cf)}
