"""MC-07..MC-10: adjacent-layer integration ports.

INV-10 does not own module validation (INV-09), interface typing (INV-11),
language interop (INV-12) or realization (PLN-02). These are the *ports* it
consumes/produces, with fail-closed reference implementations that the real
adjacent services plug into. Each port is a small Protocol so the production
service can be substituted without touching the linker.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .composition import Unit
from .errors import InterfaceIncompatible, SchemaViolation, ValidationRequired

# --------------------------------------------------------------------- INV-09


@dataclass(frozen=True)
class ValidatedModule:
    """Attestation that INV-09 validated the module backing a unit."""

    unit: str
    module_digest: str  # sha256 hex of the module bytes
    validator: str  # e.g. "INV-09/1.x"
    profile: str  # portable-compute profile validated against


class ModuleValidator(Protocol):
    def validate(self, unit: str, module: bytes) -> ValidatedModule: ...


class ReferenceModuleValidator:
    """Stand-in INV-09 validator: checks the Wasm magic/version preamble only."""

    MAGIC = b"\x00asm"

    def __init__(self, profile: str = "wasm-component-0.2") -> None:
        self.profile = profile

    def validate(self, unit: str, module: bytes) -> ValidatedModule:
        if not isinstance(module, (bytes, bytearray)) or len(module) < 8 or module[:4] != self.MAGIC:
            raise ValidationRequired("module failed INV-09 preamble validation", unit=unit)
        return ValidatedModule(unit, hashlib.sha256(module).hexdigest(), "INV-09/reference", self.profile)


def require_validated(units: list[Unit], attestations: Mapping[str, ValidatedModule]) -> None:
    """Refuse composition unless every unit carries an INV-09 attestation."""
    for u in units:
        att = attestations.get(u.name)
        if att is None or att.unit != u.name or not re.fullmatch(r"[0-9a-f]{64}", att.module_digest):
            raise ValidationRequired("unit lacks an INV-09 validation attestation", unit=u.name)


# --------------------------------------------------------------------- INV-11

_VERSIONED = re.compile(r"^(?P<base>[^@]+)@(?P<maj>\d+)\.(?P<min>\d+)\.(?P<pat>\d+)(?P<pre>[-+][\w.\-+]*)?$")


def parse_interface(ref: str) -> tuple[str, tuple[int, int, int] | None, str | None]:
    m = _VERSIONED.match(ref)
    if not m:
        return ref, None, None
    return m["base"], (int(m["maj"]), int(m["min"]), int(m["pat"])), m["pre"]


class InterfaceResolver(Protocol):
    def compatible(self, required: str, provided: str) -> bool: ...


class SemverInterfaceResolver:
    """Reference INV-11 resolver: same base, same major, provided >= required.

    Pre-release versions only match exactly. Unversioned references only match
    unversioned references with the same base (the 4.2.0 exact-string rule).
    For 0.x, the minor is treated as the compatibility boundary.
    """

    def compatible(self, required: str, provided: str) -> bool:
        rb, rv, rp = parse_interface(required)
        pb, pv, pp = parse_interface(provided)
        if rb != pb:
            return False
        if rv is None or pv is None:
            return rv is None and pv is None
        if rp or pp:
            return required == provided
        if rv[0] != pv[0]:
            return False
        if rv[0] == 0:
            return rv[1] == pv[1] and pv[2] >= rv[2]
        return pv[1:] >= rv[1:]


def resolve_interfaces(units: list[Unit], resolver: InterfaceResolver) -> tuple[list[Unit], dict[str, dict[str, str]]]:
    """Rewrite each import to the single compatible export that satisfies it.

    Returns rewritten units and an alias map ``{consumer: {required: provided}}``
    so the rewrite is explicit in the audit trail. Ambiguity is refused.
    """
    exports = sorted({e for u in units for e in u.exports})
    rewritten: list[Unit] = []
    aliases: dict[str, dict[str, str]] = {}
    for u in units:
        new_imports = set()
        for imp in sorted(u.imports):
            if imp in exports:
                new_imports.add(imp)
                continue
            matches = [e for e in exports if resolver.compatible(imp, e)]
            if len(matches) > 1:
                raise InterfaceIncompatible("import matches several compatible exports",
                                            component=u.name, interface=imp, candidates=matches)
            if matches:
                aliases.setdefault(u.name, {})[imp] = matches[0]
                new_imports.add(matches[0])
            else:
                new_imports.add(imp)  # left for the linker: external or unsatisfied
        rewritten.append(Unit(u.name, frozenset(new_imports), u.exports))
    return rewritten, aliases


# --------------------------------------------------------------------- INV-12

# ABI families that share canonical-ABI semantics once lowered to a component.
DEFAULT_ABI_MATRIX: dict[str, set[str]] = {
    "component-model/canonical-abi": {"rust", "c", "cpp", "go", "python", "js", "csharp", "zig"},
}


@dataclass(frozen=True)
class LanguageBinding:
    unit: str
    language: str
    abi: str = "component-model/canonical-abi"
    string_encoding: str = "utf8"


def check_language_interop(bindings: list[dict[str, Any]], languages: Mapping[str, LanguageBinding],
                           matrix: Mapping[str, set[str]] = DEFAULT_ABI_MATRIX) -> list[dict[str, str]]:
    """Refuse a binding whose consumer/provider cannot share ABI semantics."""
    report = []
    for b in bindings:
        if "provider" not in b:
            continue
        c, p = languages.get(b["consumer"]), languages.get(b["provider"])
        if c is None or p is None:
            raise InterfaceIncompatible("language binding undeclared", binding=b)
        if c.abi != p.abi or c.abi not in matrix or not {c.language, p.language} <= matrix[c.abi]:
            raise InterfaceIncompatible("ABI mismatch across languages", binding=b,
                                        consumer=(c.language, c.abi), provider=(p.language, p.abi))
        report.append({"interface": b["interface"], "consumer": c.language, "provider": p.language,
                       "abi": c.abi, "string_encoding": f"{p.string_encoding}->{c.string_encoding}"})
    return report


# --------------------------------------------------------------------- PLN-02


@dataclass
class RealizationPlan:
    composition: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    externals: list[str] = field(default_factory=list)


def realization_plan(result: Mapping[str, Any]) -> RealizationPlan:
    """PLN-02 port: an instantiation plan that honours order, bindings, externals, id."""
    by_consumer: dict[str, list[dict[str, Any]]] = {}
    for b in result["bindings"]:
        by_consumer.setdefault(b["consumer"], []).append(b)
    plan = RealizationPlan(result["composition"], externals=list(result["external_imports"]))
    for name in result["order"]:
        plan.steps.append({"instantiate": name, "wire": sorted(by_consumer.get(name, []),
                                                                 key=lambda b: b["interface"])})
    return plan


def verify_realization(result: Mapping[str, Any], instantiated: list[str],
                       wired: Mapping[str, Mapping[str, str]]) -> None:
    """Check that a runtime actually honoured the composition (conformance oracle)."""
    if instantiated != list(result["order"]):
        raise SchemaViolation("runtime instantiation order diverged from composition order",
                              expected=result["order"], observed=instantiated)
    for b in result["bindings"]:
        got = wired.get(b["consumer"], {}).get(b["interface"])
        want = b.get("provider", "<external>")
        if got != want:
            raise SchemaViolation("runtime wiring diverged from binding", binding=b, observed=got)
