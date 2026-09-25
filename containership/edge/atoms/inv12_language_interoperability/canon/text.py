"""MC-009 Unicode and character transcoder.

Normative policy:

* The canonical string encoding is UTF-8 (``string-encoding=utf8``).
* A canonical string is a sequence of Unicode *scalar values*
  (U+0000..U+D7FF, U+E000..U+10FFFF).  Lone surrogates are rejected.
* Decoding is strict: overlong forms, surrogate encodings, truncated sequences
  and code points above U+10FFFF are rejected (``PK_INTEROP_ENCODING``); there
  is no U+FFFD substitution.
* No Unicode normalization (NFC/NFD) is applied: code points cross the boundary
  byte-for-byte.  Comparing strings for equality is therefore code-point
  equality; callers who need canonical equivalence must normalize explicitly.
* A ``char`` is exactly one scalar value, carried as a u32 on the wire.
* UTF-16 sources (JavaScript strings, Windows APIs) are transcoded with
  :func:`from_utf16`, which rejects unpaired surrogates.
"""
from __future__ import annotations

from .errors import ValidationError


def _enc(msg, path=()):
    return ValidationError(msg, code="PK_INTEROP_ENCODING", path=path)


def encode_utf8(s, path=()) -> bytes:
    if type(s) is not str:
        raise ValidationError(f"{type(s).__name__} is not a string", path=path)
    try:
        return s.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise _enc("string contains a lone surrogate (not a Unicode scalar value)", path) from None


def decode_utf8(b: bytes, path=()) -> str:
    try:
        return bytes(b).decode("utf-8", "strict")
    except UnicodeDecodeError:
        raise _enc("invalid UTF-8 sequence", path) from None


def check_char(c, path=()) -> str:
    if type(c) is not str or len(c) != 1:
        raise ValidationError("char must be a one-code-point str", path=path)
    cp = ord(c)
    if 0xD800 <= cp <= 0xDFFF:
        raise _enc("char is a surrogate code point", path)
    return c


def char_from_u32(v: int, path=()) -> str:
    if not (0 <= v < 0xD800 or 0xE000 <= v <= 0x10FFFF):
        raise _enc("u32 is not a Unicode scalar value", path)
    return chr(v)


def from_utf16(units, path=()) -> str:
    """Transcode a sequence of UTF-16 code units (ints 0..0xFFFF)."""
    out, i, n = [], 0, len(units)
    while i < n:
        u = units[i]
        if type(u) is not int or not 0 <= u <= 0xFFFF:
            raise _enc("invalid UTF-16 code unit", path)
        if 0xD800 <= u <= 0xDBFF:
            if i + 1 >= n or not (type(units[i + 1]) is int and 0xDC00 <= units[i + 1] <= 0xDFFF):
                raise _enc("unpaired high surrogate", path)
            out.append(chr(0x10000 + ((u - 0xD800) << 10) + (units[i + 1] - 0xDC00)))
            i += 2
            continue
        if 0xDC00 <= u <= 0xDFFF:
            raise _enc("unpaired low surrogate", path)
        out.append(chr(u))
        i += 1
    return "".join(out)


def to_utf16(s: str, path=()) -> list:
    encode_utf8(s, path)  # rejects surrogates
    b = s.encode("utf-16-le")
    return [b[i] | (b[i + 1] << 8) for i in range(0, len(b), 2)]
