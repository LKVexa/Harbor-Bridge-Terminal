"""MC-46..MC-50 (optional contract capabilities) and MC-33 (legacy migration).

* :func:`compose_extended` — aliasing (MC-47) and dead-export elimination
  (MC-48) as explicit, recorded pre-link rewrites on top of :func:`compose`.
* :class:`IncrementalLinker` — cached, change-scoped relinking (MC-46).
* :func:`as_unit` / :func:`compose_nested` — a composition is itself a unit (MC-49).
* :func:`diff` — provider/external/order/identity impact analysis (MC-50).
* :func:`migrate_legacy` — 4.1.0 -> PK_COMPOSITION_ID/2 remap tool (MC-33).

Identity rule: every rewrite is applied to the *units* before linking, so the
``composition`` id always addresses the graph actually linked; the rewrite
itself is reported in additive fields (``aliases``, ``eliminated_exports``,
``nested``) and bound into ``extension_digest``.
"""
from __future__ import annotations

import hashlib
import json
import threading
from collections import defaultdict, OrderedDict
from typing import Any, Iterable, Mapping

from .composition import (DEFAULT_LIMITS, CompositionLimits, InvalidComposition, Unit,
                          _canonical_digest, compose)

# ------------------------------------------------------------------ aliasing / DCE


def apply_aliases(units: Iterable[Unit], aliases: Mapping[str, Mapping[str, str]]) -> list[Unit]:
    """Rename consumer imports: ``{consumer: {declared_import: target_interface}}``."""
    units = list(units)
    names = {u.name for u in units}
    unknown = sorted(set(aliases) - names)
    if unknown:
        raise InvalidComposition("aliases reference unknown consumers", consumers=unknown)
    out = []
    for u in units:
        amap = aliases.get(u.name, {})
        stray = sorted(set(amap) - set(u.imports))
        if stray:
            raise InvalidComposition("alias for an import the consumer does not declare",
                                     component=u.name, imports=stray)
        new = [amap.get(i, i) for i in u.imports]
        if len(set(new)) != len(new):
            raise InvalidComposition("aliases collapse two imports onto one interface", component=u.name)
        out.append(Unit(u.name, frozenset(new), u.exports))
    return out


def eliminate_dead_exports(units: Iterable[Unit], keep: Iterable[str] = ()) -> tuple[list[Unit], list[dict[str, str]]]:
    units = list(units)
    used = {i for u in units for i in u.imports} | set(keep)
    removed = []
    out = []
    for u in units:
        dead = sorted(u.exports - used)
        removed += [{"component": u.name, "interface": d} for d in dead]
        out.append(Unit(u.name, u.imports, u.exports & used))
    return out, removed


def compose_extended(units: Iterable[Unit], *, external: Iterable[str] = frozenset(),
                     aliases: Mapping[str, Mapping[str, str]] | None = None,
                     eliminate_dead: bool = False, keep_exports: Iterable[str] = (),
                     limits: CompositionLimits = DEFAULT_LIMITS) -> dict[str, Any]:
    units = list(units)
    ext = frozenset(external)
    if aliases:
        units = apply_aliases(units, aliases)
    eliminated: list[dict[str, str]] = []
    if eliminate_dead:
        units, eliminated = eliminate_dead_exports(units, keep_exports)
    result = compose(units, external=ext, limits=limits)
    extension = {"aliases": {k: dict(sorted(v.items())) for k, v in sorted((aliases or {}).items())},
                 "eliminated_exports": eliminated, "keep_exports": sorted(keep_exports)}
    result.update(extension)
    result["extension_digest"] = _canonical_digest({"composition": result["composition"], **extension})
    return result


# ------------------------------------------------------------------ incremental


class IncrementalLinker:
    """Relinks only when the unit set changes; reports the affected subgraph.

    The full link is still executed on change (correctness first: closure and
    cycles are global properties), but unchanged requests are served from an
    LRU keyed by the canonical request, and ``affected`` lists every component
    whose transitive providers changed — the set a build system must rebuild.
    """

    def __init__(self, *, capacity: int = 256, limits: CompositionLimits = DEFAULT_LIMITS) -> None:
        self.capacity, self.limits = capacity, limits
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self.units: dict[str, Unit] = {}
        self.external: frozenset[str] = frozenset()
        self.last: dict[str, Any] | None = None
        self.hits = self.misses = 0

    @staticmethod
    def _key(units: Iterable[Unit], external: Iterable[str]) -> str:
        body = {"u": sorted([u.name, sorted(u.imports), sorted(u.exports)] for u in units),
                "x": sorted(external)}
        return hashlib.sha256(json.dumps(body, separators=(",", ":")).encode()).hexdigest()

    def link(self, units: Iterable[Unit], external: Iterable[str] = frozenset()) -> dict[str, Any]:
        units, external = list(units), frozenset(external)
        key = self._key(units, external)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self.hits += 1
                return self._cache[key]
        result = compose(units, external=external, limits=self.limits)
        with self._lock:
            self.misses += 1
            self._cache[key] = result
            while len(self._cache) > self.capacity:
                self._cache.popitem(last=False)
        return result

    def apply(self, *, upsert: Iterable[Unit] = (), remove: Iterable[str] = (),
              external: Iterable[str] | None = None) -> dict[str, Any]:
        changed = set()
        staged = dict(self.units)
        for u in upsert:
            if staged.get(u.name) != u:
                changed.add(u.name)
            staged[u.name] = u
        for name in remove:
            if staged.pop(name, None) is not None:
                changed.add(name)
        ext = self.external if external is None else frozenset(external)
        result = dict(self.link(staged.values(), ext))  # raises -> state unchanged
        dependents: dict[str, set[str]] = defaultdict(set)
        for b in result["bindings"]:
            if "provider" in b:
                dependents[b["provider"]].add(b["consumer"])
        affected, stack = set(changed), list(changed)
        while stack:
            for d in dependents.get(stack.pop(), ()):
                if d not in affected:
                    affected.add(d)
                    stack.append(d)
        self.units, self.external, self.last = staged, ext, result
        result["changed"] = sorted(changed)
        result["affected"] = sorted(a for a in affected if a in staged)
        return result


# ------------------------------------------------------------------ nesting


def as_unit(result: Mapping[str, Any], name: str, *, exports: Iterable[str] | None = None) -> Unit:
    """Present a closed composition as a component: its imports are its externals."""
    exp = set(result["exports"]) if exports is None else set(exports)
    missing = sorted(exp - set(result["exports"]))
    if missing:
        raise InvalidComposition("nested unit exports interfaces its composition lacks", missing=missing)
    return Unit(name, frozenset(result["external_imports"]), frozenset(exp))


def compose_nested(units: Iterable[Unit], nested: Mapping[str, tuple[Mapping[str, Any], Iterable[str] | None]],
                   *, external: Iterable[str] = frozenset(),
                   limits: CompositionLimits = DEFAULT_LIMITS) -> dict[str, Any]:
    """Compose units plus sub-compositions; bind inner ids into ``tree_digest``."""
    all_units = list(units) + [as_unit(res, n, exports=e) for n, (res, e) in sorted(nested.items())]
    result = compose(all_units, external=external, limits=limits)
    inner = {n: res["composition"] for n, (res, _) in sorted(nested.items())}
    result["nested"] = inner
    result["tree_digest"] = _canonical_digest({"composition": result["composition"], "nested": inner})
    return result


# ------------------------------------------------------------------ diff


def diff(active: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    ap, cp = active["providers"], candidate["providers"]
    changed_providers = [
        {"interface": i, "from": ap.get(i), "to": cp.get(i)}
        for i in sorted(set(ap) | set(cp)) if ap.get(i) != cp.get(i)
    ]
    key = lambda b: (b["consumer"], b["interface"], b.get("provider", "<external>"))
    ab, cb = {key(b) for b in active["bindings"]}, {key(b) for b in candidate["bindings"]}
    touched = {c for c, _, _ in ab ^ cb}
    return {
        "identity_changed": active["composition"] != candidate["composition"],
        "from": active["composition"], "to": candidate["composition"],
        "components_added": sorted(set(candidate["components"]) - set(active["components"])),
        "components_removed": sorted(set(active["components"]) - set(candidate["components"])),
        "externals_added": sorted(set(candidate["external_imports"]) - set(active["external_imports"])),
        "externals_removed": sorted(set(active["external_imports"]) - set(candidate["external_imports"])),
        "providers_changed": changed_providers,
        "bindings_added": [dict(zip(("consumer", "interface", "target"), k)) for k in sorted(cb - ab)],
        "bindings_removed": [dict(zip(("consumer", "interface", "target"), k)) for k in sorted(ab - cb)],
        "order_changed": active["order"] != candidate["order"],
        "impacted_consumers": sorted(touched),
    }


# ------------------------------------------------------------------ migration


def legacy_id_41(result: Mapping[str, Any]) -> str:
    """Reconstruction of the 4.1.0 identity from its documented inputs.

    The 4.1.0 source is not in the archive; AUDIT_REPORT A-02/A-03 describe the
    inputs (names, order, external imports, export names; sha256 truncated to 24
    hex). Treat matches as corroboration only — never as proof.
    """
    material = {"components": sorted(result["components"]), "order": list(result["order"]),
                "external_imports": sorted(result["external_imports"]), "exports": sorted(result["exports"])}
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]


def migrate_legacy(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Recompute PK_COMPOSITION_ID/2 for persisted 4.1.0 records.

    Each record needs ``legacy_id`` and the ``units`` (``[{name, imports,
    exports}]``) and ``external`` it was built from. Records without units are
    reported ``unrecoverable`` — a truncated legacy id cannot be inverted.
    Several legacy ids mapping to one new id, or vice versa, are reported as
    ``collisions`` (the A-02 defect made this possible).
    """
    remap, unrecoverable, failed = [], [], []
    by_new: dict[str, list[str]] = defaultdict(list)
    for rec in records:
        lid = rec.get("legacy_id")
        if not rec.get("units"):
            unrecoverable.append({"legacy_id": lid, "reason": "no unit declarations persisted"})
            continue
        try:
            units = [Unit(u["name"], frozenset(u.get("imports", [])), frozenset(u.get("exports", [])))
                     for u in rec["units"]]
            res = compose(units, external=frozenset(rec.get("external", [])))
        except Exception as exc:  # a legacy record may encode a now-refused graph (e.g. self-cycle)
            failed.append({"legacy_id": lid, "error": getattr(exc, "as_dict", lambda: {"message": str(exc)})()})
            continue
        entry = {"legacy_id": lid, "composition": res["composition"], "identity_profile": res["identity_profile"],
                 "legacy_reconstruction_matches": legacy_id_41(res) == lid}
        remap.append(entry)
        by_new[res["composition"]].append(lid)
    collisions = [{"composition": k, "legacy_ids": sorted(v)} for k, v in sorted(by_new.items()) if len(set(v)) > 1]
    return {"remap": remap, "unrecoverable": unrecoverable, "failed": failed, "collisions": collisions,
            "summary": {"remapped": len(remap), "unrecoverable": len(unrecoverable), "failed": len(failed)}}
