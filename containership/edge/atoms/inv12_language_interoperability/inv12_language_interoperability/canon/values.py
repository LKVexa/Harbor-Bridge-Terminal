"""Host (Python) representation of canonical values.

Normative mapping (Python guest profile, see ``registry.py``)::

    bool            -> bool (exact type, never int)
    s8..u64         -> int (exact type, never bool)
    f32 / f64       -> float (exact type; f32 must be exactly representable)
    char            -> str of exactly one Unicode scalar value (no surrogates)
    string          -> str (valid Unicode scalar values only)
    list<T>         -> list (tuple accepted on input)
    tuple<...>      -> tuple
    record          -> dict whose keys are exactly the declared field names
    variant         -> Variant(case, value)   (value is None for payload-less cases)
    enum            -> str case name
    flags           -> frozenset of declared flag names (set/frozenset on input)
    option<T>       -> None | Some(value)      (Some keeps option<option<T>> unambiguous)
    result<T,E>     -> Ok(value) | Err(value)  (value None when that side has no type)
    own<R>/borrow<R>-> resources.Handle issued by a ResourceTable
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Some:
    value: Any


@dataclass(frozen=True)
class Ok:
    value: Any = None


@dataclass(frozen=True)
class Err:
    value: Any = None


@dataclass(frozen=True)
class Variant:
    case: str
    value: Any = None
