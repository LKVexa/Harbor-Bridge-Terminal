"""Bounded, duplicate-key-safe JSON at ship-owned read boundaries.

UC-CJSON/1 is an integer-only deterministic encoding for NEW contracts. It is
not RFC 8785, does not normalize Unicode and does not change legacy seal bytes.
This module exposes the existing json read/write interface, with strict reads.
"""
from __future__ import annotations
import json as _json
import math
from typing import Any
from . import Refusal

MAX_BYTES = 32 * 1024 * 1024
MAX_DEPTH = 64
JSONDecodeError = _json.JSONDecodeError

def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refusal('duplicate JSON object key', {'key': key})
        result[key] = value
    return result

def _constant(value):
    raise Refusal('non-finite JSON number', {'value': value})

def _float(value):
    number = float(value)
    if not math.isfinite(number):
        _constant(value)
    return number

def _int(value):
    if len(value.lstrip('-')) > 1024:
        raise Refusal('JSON integer exceeds 1024-digit budget')
    return int(value)

def _depth(text, limit):
    depth = 0; quoted = False; escaped = False
    for char in text:
        if quoted:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char in '[{':
            depth += 1
            if depth > limit: raise Refusal('JSON nesting limit exceeded', {'limit': limit})
        elif char in ']}': depth -= 1

def loads(data, *, max_bytes=MAX_BYTES, max_depth=MAX_DEPTH, **kwargs):
    if kwargs:
        raise Refusal('JSON decoder overrides are not permitted', {'fields': sorted(kwargs)})
    if not isinstance(data, (str, bytes, bytearray)):
        raise Refusal('JSON input must be text or UTF-8 bytes')
    if isinstance(data, str):
        try: raw = data.encode('utf-8')
        except UnicodeError as exc: raise Refusal('JSON contains an invalid Unicode scalar') from exc
        text = data
    else:
        raw = bytes(data)
        try: text = raw.decode('utf-8')
        except UnicodeError as exc: raise Refusal('JSON must use valid UTF-8') from exc
    if len(raw) > max_bytes: raise Refusal('JSON byte budget exceeded', {'limit': max_bytes})
    _depth(text, max_depth)
    try:
        value = _json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant,
                            parse_float=_float, parse_int=_int)
        _scalars(value)
        return value
    except (ValueError, RecursionError, UnicodeError) as exc:
        raise Refusal('invalid JSON document', {'reason': str(exc)[:300]}) from exc

def load(fp, *, max_bytes=MAX_BYTES, max_depth=MAX_DEPTH, **kwargs):
    return loads(fp.read(max_bytes + 1), max_bytes=max_bytes, max_depth=max_depth, **kwargs)

def read(path, *, max_bytes=MAX_BYTES):
    from .safety import reject_link
    reject_link(str(path))
    with open(path, 'rb') as handle:
        return load(handle, max_bytes=max_bytes)

def _scalars(value, depth=0, *, integers_only=False):
    if depth > MAX_DEPTH: raise Refusal('JSON nesting limit exceeded')
    if value is None or type(value) is bool: return
    if type(value) is int:
        if value.bit_length() > 3402: raise Refusal('integer encoding budget exceeded')
        return
    if type(value) is float:
        if integers_only or not math.isfinite(value): raise Refusal('floating-point value is not permitted in this encoding')
        return
    if isinstance(value, str):
        try: value.encode('utf-8')
        except UnicodeError as exc: raise Refusal('invalid Unicode scalar') from exc
        return
    if isinstance(value, list):
        for item in value: _scalars(item, depth+1, integers_only=integers_only)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str): raise Refusal('JSON object keys must be strings')
            _scalars(key, depth+1, integers_only=integers_only)
            _scalars(item, depth+1, integers_only=integers_only)
        return
    raise Refusal('unsupported JSON value type', {'type': type(value).__name__})

def canonical_bytes(value: Any) -> bytes:
    _scalars(value, integers_only=True)
    out = _json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')
    if len(out) > MAX_BYTES: raise Refusal('canonical JSON byte budget exceeded')
    return out

def dumps(value, **kwargs):
    kwargs.setdefault('allow_nan', False)
    return _json.dumps(value, **kwargs)

def dump(value, fp, **kwargs):
    fp.write(dumps(value, **kwargs))
