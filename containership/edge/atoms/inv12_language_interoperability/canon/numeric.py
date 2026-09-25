"""MC-008 numeric conversion policy engine.

Normative policy (profile ``exact/1``; the only profile shipped):

* Integers MUST be in the declared range; there is no wrap, saturate or clamp.
* A host bool is never an integer, and an integer is never a bool.
* A float source may become an integer only if it is finite, integral, not -0.0
  and inside the target range (JS ``Number`` also requires ``|v| <= 2**53-1``,
  i.e. a *safe* integer, so the source itself was exact).
* An integer may become ``f64``/``f32`` only if the float represents it exactly.
* ``f64 -> f32`` narrowing is permitted only when exact (NaN excepted, below).
* NaN: any NaN is accepted and canonicalized to the quiet NaN bit pattern
  (``0x7fc00000`` / ``0x7ff8000000000000``) when stored; payload bits are not
  preserved across the boundary.  +/-infinity and -0.0 are preserved exactly.
* Widening conversions that are always exact (u8 -> u32 etc.) are allowed.

Representation names: ``python-int``, ``python-float``, ``python-bool``,
``js-number``, ``js-bigint``, ``go-intN``/``go-uintN``, ``rust-iN``/``rust-uN``,
``float32``, ``float64``.
"""
from __future__ import annotations

import math
import struct

from .errors import ValidationError
from .types import INT_RANGES

POLICY_ID = "exact/1"
JS_MAX_SAFE = 2**53 - 1
CANONICAL_NAN32 = 0x7FC00000
CANONICAL_NAN64 = 0x7FF8000000000000


def _mismatch(msg, path=()):
    return ValidationError(msg, code="PK_INTEROP_TYPE_MISMATCH", path=path)


def _range(msg, path=()):
    return ValidationError(msg, code="PK_INTEROP_OUT_OF_RANGE", path=path)


def _lossy(msg, path=()):
    return ValidationError(msg, code="PK_INTEROP_LOSSY_CONVERSION", path=path)


def check_int(value, type_name: str, path=()) -> int:
    if type(value) is not int:
        raise _mismatch(f"{type(value).__name__} is not a {type_name}", path)
    lo, hi = INT_RANGES[type_name]
    if not lo <= value <= hi:
        raise _range(f"integer outside {type_name} [{lo}, {hi}]", path)
    return value


def f32_exact(value: float) -> bool:
    if math.isnan(value):
        return True
    try:
        return struct.unpack("<f", struct.pack("<f", value))[0] == value
    except OverflowError:
        return False


def check_float(value, type_name: str, path=()) -> float:
    if type(value) is not float:
        raise _mismatch(f"{type(value).__name__} is not a {type_name}", path)
    if type_name == "f32" and not f32_exact(value):
        raise _lossy("value is not exactly representable as f32", path)
    return value


def f32_bits(value: float) -> int:
    if math.isnan(value):
        return CANONICAL_NAN32
    return struct.unpack("<I", struct.pack("<f", value))[0]


def f64_bits(value: float) -> int:
    if math.isnan(value):
        return CANONICAL_NAN64
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def bits_f32(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def bits_f64(bits: int) -> float:
    return struct.unpack("<d", struct.pack("<Q", bits))[0]


def _native_range(repr_name: str):
    for prefix in ("go-", "rust-"):
        if repr_name.startswith(prefix):
            body = repr_name[len(prefix):]
            if body in ("int", "uint"):
                body += "64"
            signed = body[0] == "i"
            width = int(body.lstrip("iunt"))
            if width not in (8, 16, 32, 64, 128):
                break
            return (-(2 ** (width - 1)), 2 ** (width - 1) - 1) if signed else (0, 2 ** width - 1)
    return None


def convert(value, *, source: str, target: str, path=()):
    """Convert a host value in representation *source* to canonical *target*.

    Returns the canonical Python value or raises ``ValidationError``.  Never
    rounds, wraps, saturates or truncates.
    """
    if target in INT_RANGES:
        if source in ("python-int", "js-bigint") or _native_range(source):
            if type(value) is not int:
                raise _mismatch(f"{source} value must be an int", path)
            nr = _native_range(source)
            if nr and not nr[0] <= value <= nr[1]:
                raise _range(f"value is not a valid {source}", path)
            return check_int(value, target, path)
        if source in ("js-number", "python-float", "float64", "float32"):
            if type(value) is not float:
                raise _mismatch(f"{source} value must be a float", path)
            if not math.isfinite(value) or value != math.floor(value):
                raise _lossy("non-integral or non-finite number cannot become an integer", path)
            if value == 0 and math.copysign(1.0, value) < 0:
                raise _lossy("-0.0 cannot become an integer without losing its sign", path)
            if source == "js-number" and abs(value) > JS_MAX_SAFE:
                raise _lossy("JS Number beyond 2**53-1 is not an exact integer", path)
            return check_int(int(value), target, path)
        raise _mismatch(f"{source} cannot become {target}", path)
    if target in ("f32", "f64"):
        if source in ("python-float", "js-number", "float64", "float32"):
            if type(value) is not float:
                raise _mismatch(f"{source} value must be a float", path)
            return check_float(value, target, path)
        if source in ("python-int", "js-bigint") or _native_range(source):
            if type(value) is not int:
                raise _mismatch(f"{source} value must be an int", path)
            try:
                f = float(value)
            except OverflowError:
                raise _lossy("integer too large for a float", path) from None
            if int(f) != value or (target == "f32" and not f32_exact(f)):
                raise _lossy(f"integer is not exactly representable as {target}", path)
            return f
        raise _mismatch(f"{source} cannot become {target}", path)
    if target == "bool":
        if source not in ("python-bool", "js-boolean", "go-bool", "rust-bool") or type(value) is not bool:
            raise _mismatch("only a boolean source may become bool", path)
        return value
    raise _mismatch(f"no numeric policy for target {target}", path)
