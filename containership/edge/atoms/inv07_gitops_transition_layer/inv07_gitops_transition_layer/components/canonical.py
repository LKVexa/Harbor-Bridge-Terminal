"""GAP09-CSP/1 canonical signing profile (component 10).

The v5.0.0 payload used ``json.dumps(sort_keys=True)``, whose float text is
Python ``repr`` and whose key order is by Python code point rather than UTF-16 unit.
Neither is specified cross-language.  This profile pins both to RFC 8785 (JCS):

* object keys sorted by UTF-16 code units;
* strings escaped per JCS (only ``"`` ``\\`` and C0 controls escaped);
* numbers rendered by the ECMAScript Number::toString algorithm;
* no whitespace, UTF-8 output, NaN/Infinity/-0 refused (-0 renders "0" in
  JCS; GAP-09 refuses it instead so signed bytes never hide a sign).

Integers beyond 2**53 are accepted only when binary64 represents them exactly,
and are then rendered as that double (anti-confusion rule: a non-Python
reporter only ever has the double).
"""
from __future__ import annotations

import math
from typing import Any

from .errors import Malformed

PROFILE_ID = "GAP09-CSP/1"
MAX_DEPTH = 16
MAX_SAFE_INT = 2**53 - 1


def _es_number(x: float | int) -> str:
    if isinstance(x, bool):
        raise Malformed("booleans are not numbers in GAP09-CSP/1")
    if isinstance(x, int):
        if abs(x) <= MAX_SAFE_INT:
            return str(x)
        # Beyond 2**53 a JSON number is only meaningful as binary64 (that is all
        # an ECMAScript reporter has).  Accept an int only when binary64 holds it
        # exactly, and render it the way ES renders that double -- found by the
        # Node cross-language test (defect F-01: Python str(2**60) != ES text).
        try:
            f = float(x)
        except OverflowError as exc:
            raise Malformed("integer exceeds binary64") from exc
        # Accept (a) ints binary64 holds exactly, and (b) ints whose decimal text
        # IS the ES rendering of a double (what parsing canonical output yields;
        # found by the seeded round-trip property test -- defect F-04).
        if int(f) != x and str(x) != _es_number(f):
            raise Malformed("integer not representable as a binary64 value")
        x = f
    if not math.isfinite(x):
        raise Malformed("non-finite numbers are refused")
    if x == 0:
        if math.copysign(1.0, x) < 0:
            raise Malformed("negative zero is refused")
        return "0"
    sign = "-" if x < 0 else ""
    x = abs(x)
    r = repr(x)  # shortest round-trip digits
    mant, _, exp = r.partition("e")
    if "." in mant:
        ip, fp = mant.split(".")
    else:
        ip, fp = mant, ""
    fp = fp.rstrip("0")
    digits = (ip + fp).lstrip("0")
    # decimal point position n such that value = 0.digits * 10**n
    lead_zeros = len(ip + fp) - len((ip + fp).lstrip("0"))
    n = len(ip) - lead_zeros + (int(exp) if exp else 0)
    digits = digits.rstrip("0") or "0"
    k = len(digits)
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + digits
    e = n - 1
    es = ("+" if e >= 0 else "-") + str(abs(e))
    if k == 1:
        return sign + digits + "e" + es
    return sign + digits[0] + "." + digits[1:] + "e" + es


def _es_string(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 0x20:
            out.append("\\u%04x" % o)
        elif 0xD800 <= o <= 0xDFFF:
            raise Malformed("lone surrogate in string")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _utf16_key(k: str):
    return k.encode("utf-16-be")


def canonicalize(value: Any, _depth: int = 0) -> str:
    if _depth > MAX_DEPTH:
        raise Malformed("nesting exceeds GAP09-CSP/1 depth limit")
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return _es_number(value)
    if isinstance(value, str):
        return _es_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonicalize(v, _depth + 1) for v in value) + "]"
    if isinstance(value, dict):
        for k in value:
            if not isinstance(k, str):
                raise Malformed("object keys must be strings")
        items = sorted(value.items(), key=lambda kv: _utf16_key(kv[0]))
        return "{" + ",".join(_es_string(k) + ":" + canonicalize(v, _depth + 1) for k, v in items) + "}"
    raise Malformed(f"type {type(value).__name__} is not representable")


def canonical_bytes(value: Any) -> bytes:
    return canonicalize(value).encode("utf-8")


def submission_envelope(reporter: str, submission_id: str, issued_at: int, samples, key_id: str) -> dict:
    """The signed envelope: payload fields plus profile and key id (signature
    coverage includes the key id and profile, preventing key-substitution)."""
    return {
        "profile": PROFILE_ID,
        "schema": "PK_SIGNAL_SUBMISSION/2",
        "reporter": reporter,
        "submission_id": submission_id,
        "issued_at": issued_at,
        "key_id": key_id,
        "samples": [
            {"signal": s.signal, "value": s.value, "tenant": s.tenant, "environment": s.environment,
             "site": s.site, "workload": s.workload, "at": s.at}
            for s in samples
        ],
    }
