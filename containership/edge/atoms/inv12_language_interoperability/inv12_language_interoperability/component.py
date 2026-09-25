"""INV-12 - Language interoperability.

Reference model for safe, loss-aware language-boundary transfers.  Values are
validated against a canonical type, snapshotted into an isolated canonical
value, and copied out exactly once to the receiving owner.
"""
from __future__ import annotations

import math
import struct
from threading import Lock
from types import MappingProxyType
from typing import Final

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


MAX_NESTING_DEPTH: Final = 64
MAX_CONTAINER_ITEMS: Final = 100_000
MAX_TOTAL_NODES: Final = 200_000
MAX_STRING_BYTES: Final = 16 * 1024 * 1024
MAX_OWNER_BYTES: Final = 256

# What each guest language can represent exactly in the binding profile used by
# this reference model. JavaScript i64/u64 are represented with BigInt rather
# than Number, avoiding the historical 53-bit precision ceiling.
_LANGUAGE_TYPES = {
    "rust": frozenset({"bool", "u8", "u32", "u64", "s32", "s64", "f32", "f64",
                       "string", "list", "record", "variant", "option", "result"}),
    "go": frozenset({"bool", "u8", "u32", "u64", "s32", "s64", "f32", "f64",
                     "string", "list", "record", "variant", "option", "result"}),
    "python": frozenset({"bool", "u8", "u32", "u64", "s32", "s64", "f32", "f64",
                         "string", "list", "record", "variant", "option", "result"}),
    "javascript": frozenset({"bool", "u8", "u32", "u64", "s32", "s64", "f32", "f64",
                             "string", "list", "record", "variant", "option", "result"}),
}
LANGUAGE_TYPES = MappingProxyType(_LANGUAGE_TYPES)
SUPPORTED_LANGUAGES = frozenset(_LANGUAGE_TYPES)
CANONICAL_TYPES = frozenset().union(*_LANGUAGE_TYPES.values())
RANGES = MappingProxyType({
    "u8": (0, 255),
    "u32": (0, 2**32 - 1),
    "u64": (0, 2**64 - 1),
    "s32": (-2**31, 2**31 - 1),
    "s64": (-2**63, 2**63 - 1),
})


class Unrepresentable(TypeError):
    """Raised when a guest language cannot represent an interface type exactly."""

    code = "PK_INTEROP_UNREPRESENTABLE"


class OutOfRange(ValueError):
    """Raised when a value does not fit its declared canonical type."""

    code = "PK_INTEROP_OUT_OF_RANGE"


class OwnershipError(RuntimeError):
    """Raised when an owned value is accessed/transferred after it was moved."""

    code = "PK_INTEROP_OWNERSHIP"


class CanonicalizationError(ValueError):
    """Raised when a value cannot be copied safely into canonical storage."""

    code = "PK_INTEROP_CANONICALIZATION"


def _require_text(value: object, *, field_name: str, max_bytes: int, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        qualifier = "string" if allow_empty else "non-empty string"
        raise ValueError(f"{field_name} must be a {qualifier}")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError(
            f"{field_name} contains a Unicode surrogate that is not valid UTF-8") from exc
    if len(encoded) > max_bytes:
        raise CanonicalizationError(
            f"{field_name} exceeds the {max_bytes}-byte UTF-8 limit")
    return value


def _validate_owner(owner: object, *, field_name: str = "owner") -> str:
    return _require_text(owner, field_name=field_name, max_bytes=MAX_OWNER_BYTES)


def _clone_canonical_tree(value: object, *, _depth: int = 0,
                          _active: set[int] | None = None,
                          _budget: list[int] | None = None):
    """Return a safe detached copy of a canonical data tree.

    Only data-only Python primitives and containers are admitted.  Arbitrary
    objects are rejected instead of invoking user-controlled ``__deepcopy__``
    hooks. Cycles and unbounded/deep containers are rejected to make resource
    consumption explicit and deterministic.
    """
    if _depth > MAX_NESTING_DEPTH:
        raise CanonicalizationError(
            f"canonical value exceeds maximum nesting depth {MAX_NESTING_DEPTH}")
    if _active is None:
        _active = set()
    if _budget is None:
        _budget = [MAX_TOTAL_NODES]
    _budget[0] -= 1
    if _budget[0] < 0:
        raise CanonicalizationError(
            f"canonical value exceeds maximum node count {MAX_TOTAL_NODES}")

    if value is None or type(value) in (bool, int, float):
        return value
    if type(value) is str:
        _require_text(value, field_name="string value", max_bytes=MAX_STRING_BYTES, allow_empty=True)
        return value

    if type(value) in (list, tuple):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise CanonicalizationError(
                f"container exceeds maximum item count {MAX_CONTAINER_ITEMS}")
        marker = id(value)
        if marker in _active:
            raise CanonicalizationError("cyclic canonical values are not supported")
        _active.add(marker)
        try:
            values = [
                _clone_canonical_tree(v, _depth=_depth + 1, _active=_active, _budget=_budget)
                for v in value
            ]
        finally:
            _active.remove(marker)
        return values if type(value) is list else tuple(values)

    if type(value) is dict:
        if len(value) > MAX_CONTAINER_ITEMS:
            raise CanonicalizationError(
                f"container exceeds maximum item count {MAX_CONTAINER_ITEMS}")
        marker = id(value)
        if marker in _active:
            raise CanonicalizationError("cyclic canonical values are not supported")
        _active.add(marker)
        try:
            cloned = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise CanonicalizationError("canonical record keys must be strings")
                _require_text(key, field_name="record key", max_bytes=MAX_STRING_BYTES, allow_empty=True)
                cloned[key] = _clone_canonical_tree(
                    item, _depth=_depth + 1, _active=_active, _budget=_budget)
        finally:
            _active.remove(marker)
        return cloned

    raise CanonicalizationError(
        f"unsupported canonical payload object {type(value).__name__!r}; "
        "only data primitives and containers are allowed")


def _canonicalize_value(type_name: str, value: object):
    if type_name not in CANONICAL_TYPES:
        raise Unrepresentable(f"unknown canonical type: {type_name!r}")

    if type_name in RANGES:
        low, high = RANGES[type_name]
        # bool is an int subclass in Python; it is not an integer on the wire.
        if type(value) is not int:
            raise OutOfRange(f"value of type {type(value).__name__} is not a valid {type_name}")
        if not low <= value <= high:
            raise OutOfRange(f"integer is outside {type_name} [{low}, {high}]")
        return value

    if type_name == "bool":
        if type(value) is not bool:
            raise OutOfRange(f"value of type {type(value).__name__} is not a bool")
        return value

    if type_name == "string":
        if type(value) is not str:
            raise OutOfRange(f"value of type {type(value).__name__} is not a string")
        _require_text(value, field_name="string value", max_bytes=MAX_STRING_BYTES, allow_empty=True)
        return value

    if type_name in {"f32", "f64"}:
        if type(value) is not float:
            raise OutOfRange(f"value of type {type(value).__name__} is not a {type_name} floating-point value")
        if type_name == "f32":
            try:
                narrowed = struct.unpack(">f", struct.pack(">f", value))[0]
            except OverflowError as exc:
                raise OutOfRange("floating-point value is outside the f32 range") from exc
            # A declared f32 must already be exactly representable as f32. This
            # prevents an implicit, silent f64 -> f32 rounding at the boundary.
            if not (math.isnan(value) and math.isnan(narrowed)) and narrowed != value:
                raise OutOfRange(
                    "floating-point value is not exactly representable as f32; refusing silent rounding")
        return value

    # Generic composite types are intentionally data-only. Nested field type
    # validation requires a schema AST and remains a documented missing component.
    if type_name == "list" and type(value) not in (list, tuple):
        raise OutOfRange(f"value of type {type(value).__name__} is not a list value")
    if type_name == "record" and type(value) is not dict:
        raise OutOfRange(f"value of type {type(value).__name__} is not a record value")
    return _clone_canonical_tree(value)


def check_mapping(type_name: str, language: str) -> None:
    """Refuse unsupported language/type pairs without any fallback conversion."""
    if type(language) is not str or language not in LANGUAGE_TYPES:
        label = language if type(language) is str else type(language).__name__
        raise Unrepresentable(f"unsupported guest language: {label}")
    if type(type_name) is not str or type_name not in LANGUAGE_TYPES[language]:
        label = type_name if type(type_name) is str else type(type_name).__name__
        raise Unrepresentable(
            f"{language} cannot represent {label} exactly; refusing a lossy mapping")


class CanonicalValue:
    """An isolated canonical ABI snapshot, consumable by exactly one receiver."""

    __slots__ = ("_type_name", "_payload", "_owner", "_moved", "_lock")

    def __init__(self, type_name: str, value: object, owner: str):
        if type(type_name) is not str:
            raise Unrepresentable(f"unknown canonical type object: {type(type_name).__name__}")
        self._type_name = type_name
        self._owner = _validate_owner(owner)
        self._payload = _canonicalize_value(type_name, value)
        self._moved = False
        self._lock = Lock()

    @property
    def type_name(self) -> str:
        return self._type_name

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def moved(self) -> bool:
        with self._lock:
            return self._moved

    @property
    def value(self):
        """Return a detached read snapshot while this side still owns the value."""
        with self._lock:
            if self._moved:
                raise OwnershipError(
                    f"{self._type_name} value was already transferred out of {self._owner}")
            return _clone_canonical_tree(self._payload)

    def _transfer(self):
        with self._lock:
            if self._moved:
                raise OwnershipError(
                    f"{self._type_name} value was already transferred out of {self._owner}")
            payload = _clone_canonical_tree(self._payload)
            self._moved = True
            return payload

    def __repr__(self) -> str:  # pragma: no cover - diagnostic convenience
        return (f"CanonicalValue(type_name={self._type_name!r}, owner={self._owner!r}, "
                f"moved={self.moved!r})")


def lower(value, *, type_name: str, language: str, owner: str) -> CanonicalValue:
    """Validate and snapshot a guest value into isolated canonical storage."""
    check_mapping(type_name, language)
    _validate_owner(owner)
    return CanonicalValue(type_name, value, owner)


def lift(canonical: CanonicalValue, *, language: str, new_owner: str):
    """Copy a canonical value to a guest and atomically consume its ownership."""
    if type(canonical) is not CanonicalValue:
        raise TypeError("canonical must be a CanonicalValue")
    check_mapping(canonical.type_name, language)
    new_owner = _validate_owner(new_owner, field_name="new_owner")
    from_owner = canonical.owner
    payload = canonical._transfer()
    return {
        "schema": "PK_CANONICAL_LIFT/1",
        "type": canonical.type_name,
        "value": payload,
        "from_owner": from_owner,
        "to_owner": new_owner,
        "copied": True,
        "shared_memory": False,
    }


class LanguageInteroperabilityComponent(Component):
    """Master-applied component for INV-12."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        canonical = lower(42, type_name="u32", language="rust", owner="producer")
        result = lift(canonical, language="go", new_owner="consumer")
        _verify(result["value"] == 42 and not result["shared_memory"],
                "scalar boundary transfer failed")

        source = ["hello", {"nested": [1, 2, 3]}]
        canonical_list = lower(source, type_name="list", language="python", owner="a")
        source[1]["nested"][0] = 999
        transferred = lift(canonical_list, language="javascript", new_owner="b")
        _verify(transferred["value"][1]["nested"][0] == 1,
                "mutable payload remained aliased across the boundary")

        findings[5] = self.satisfied(
            items[5],
            "Scalars and nested mutable values cross by isolated canonical snapshot; mutating the "
            "source after lowering cannot change the receiver's value, and the transfer record "
            "explicitly reports no shared memory.",
            *self._evidence("component.py::CanonicalValue", "component.py::lower", "component.py::lift"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        try:
            check_mapping("u128", "javascript")
        except Unrepresentable:
            findings[6] = self.satisfied(
                items[6],
                "A canonical type without an exact target-language mapping is refused rather than "
                "falling back to a narrower or best-effort representation.",
                *self._evidence("component.py::LANGUAGE_TYPES", "component.py::check_mapping"))
        else:
            raise AssertionError(
                "expected Unrepresentable was not raised; the claimed refusal did not happen")

        try:
            lower(2**32, type_name="u32", language="rust", owner="a")
        except OutOfRange:
            findings[2] = self.satisfied(
                items[2],
                "A value outside its declared range is refused at lowering, so the boundary cannot "
                "smuggle a wrapped integer into another component.",
                *self._evidence("component.py::_canonicalize_value", "component.py::lower"))
        else:
            raise AssertionError(
                "expected OutOfRange was not raised; the claimed refusal did not happen")

        canonical = lower(1, type_name="u32", language="rust", owner="a")
        lift(canonical, language="go", new_owner="b")
        try:
            lift(canonical, language="go", new_owner="c")
        except OwnershipError:
            findings[5] = self.satisfied(
                items[5],
                "An owned value transfers exactly once; transfer state is guarded by a lock and a "
                "second lift raises instead of duplicating ownership.",
                *self._evidence("component.py::CanonicalValue._transfer", "component.py::lift"))
        else:
            raise AssertionError(
                "expected OwnershipError was not raised; the claimed refusal did not happen")
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[1] = self.satisfied(
            items[1],
            "Sharing mutable memory between components is an explicit non-goal: canonical storage "
            "snapshots data on lower and copies it again on lift.",
            *self._evidence("contract.py", "component.py::CanonicalValue", "component.py::lift"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        try:
            lower(1, type_name="u32", language="cobol", owner="a")
        except Unrepresentable:
            findings[1] = self.satisfied(
                items[1],
                "An unsupported guest language is refused by name rather than falling back to a "
                "best-effort mapping.",
                *self._evidence("component.py::check_mapping"))
        else:
            raise AssertionError(
                "expected Unrepresentable was not raised; the claimed refusal did not happen")
        return findings


COMPONENT = LanguageInteroperabilityComponent
